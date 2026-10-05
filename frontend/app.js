const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("assetguard-admin-token") || "";
function emptyState() {
  return {assets: [], endpoints: [], devices: [], changes: [], incidents: [], physicalIncidents: [], devicePage: 1, incidentPage: 1, registryScrollY: 0, registryView: "all", guideExpanded: false, operations: null, locations: [], users: [], locationAccess: [], organizations: [], agentCredentials: [], agentReenrolments: [], agentPage: 1, currentUser: null, visionRooms: [], selectedAsset: null, selectedComputer: null, assetTab: "overview", selectedIncident: null, incidentDecisionMode: null, linkingEndpoint: null, visionRoomId: null, visionScan: null, visionImageUrl: null, assetQrUrl: null, roomWorkspace: null, inspectionDraft: null, inspectionReceipt: null, roomTab: "overview", physicalIncidentId: null};
}
let state = emptyState();
let sessionGeneration = 0;
let viewGeneration = 0;
let loadGeneration = 0;
let loginMode = "password";
let loginInProgress = false;
const pendingReadControllers = new Set();
const readTimeoutMs = 20_000;
let confirmationAction = null;
let confirmationBusy = false;
let notificationGeneration = 0;
let notificationOffset = 0;
let adminAccessGeneration = 0;
const dialogFocusOrigins = new WeakMap();
const routeDataCache = new Map();
const routeRequestCache = new Map();
const routeCacheLifetimeMs = 15_000;

function openDialog(dialogId, focusTarget = null) {
  const dialog = $(dialogId);
  const origin = document.activeElement;
  if (origin instanceof HTMLElement && !dialog.contains(origin)) dialogFocusOrigins.set(dialog, origin);
  dialog.showModal();
  const target = typeof focusTarget === "string" ? $(focusTarget) : focusTarget;
  target?.focus();
}

function clearFormError(form) {
  form.querySelectorAll('.form-error,.field-error').forEach(element => { element.hidden = true; });
  form.querySelectorAll('[aria-invalid="true"]').forEach(element => element.removeAttribute('aria-invalid'));
}

let fieldErrorSequence = 0;

function fieldValidationMessage(field) {
  if (field.validity.valueMissing) return 'Заполните это поле.';
  if (field.validity.tooShort) return `Введите не менее ${field.minLength} символов.`;
  if (field.validity.tooLong) return `Допустимо не более ${field.maxLength} символов.`;
  if (field.validity.rangeUnderflow) return `Укажите значение не меньше ${field.min}.`;
  if (field.validity.rangeOverflow) return `Укажите значение не больше ${field.max}.`;
  if (field.validity.typeMismatch) return field.type === 'url' ? 'Укажите полный адрес, например https://example.org.' : 'Проверьте формат значения.';
  return 'Проверьте значение этого поля.';
}
function showFormError(form, message) {
  let error = form.querySelector('.form-error');
  if (!error) {
    error = document.createElement('p');
    error.className = 'form-error'; error.setAttribute('role', 'alert'); error.tabIndex = -1;
    form.append(error);
  }
  error.textContent = message; error.hidden = false; error.focus();
}

async function submitFormAction(event, buttonId, action) {
  event.preventDefault();
  const form = event.currentTarget;
  if (form.getAttribute('aria-busy') === 'true') return;
  const button = $(buttonId), label = button.textContent;
  const controls = [...form.querySelectorAll('button')].map(control => [control,control.disabled]);
  clearFormError(form); form.setAttribute('aria-busy','true');
  controls.forEach(([control]) => { control.disabled = true; });
  button.textContent = 'Сохраняем…';
  try { await action(form); }
  catch (error) { if (!error.stale && token) showFormError(form,error.message); }
  finally {
    form.removeAttribute('aria-busy'); button.textContent = label;
    controls.forEach(([control,disabled]) => { control.disabled = disabled; });
  }
}

document.querySelectorAll('input[required],select[required],textarea[required]').forEach(field => {
  const label = field.labels?.[0];
  if (!label || label.querySelector('.required-marker')) return;
  const text = [...label.childNodes].find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
  const marker = document.createElement('span'); marker.className = 'required-marker';
  marker.textContent = ' *'; marker.setAttribute('aria-hidden','true'); marker.title = 'Обязательное поле';
  if (text) {
    text.textContent = text.textContent.replace(/\s*\*\s*$/,'');
    const caption = document.createElement('span'); caption.className = 'field-caption';
    text.before(caption); caption.append(text,marker);
  }
  else label.querySelector('span')?.append(marker);
});

// Native validity remains authoritative; show its explanation beside the affected field.
document.addEventListener('invalid', event => {
  const field = event.target;
  if (!field.labels?.length) return;
  event.preventDefault();
  field.setAttribute('aria-invalid', 'true');
  let error = field.labels[0].querySelector('.field-error');
  if (!error) {
    error = document.createElement('span'); error.className = 'field-error';
    error.id = `field-error-${++fieldErrorSequence}`;
    field.labels[0].append(error);
    field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'),error.id].filter(Boolean).join(' '));
  }
  error.textContent = fieldValidationMessage(field); error.hidden = false;
  if (field.form?.querySelector(':invalid') === field) field.focus();
}, true);
document.addEventListener('input', event => {
  const field = event.target;
  if (field.getAttribute('aria-invalid') === 'true' && field.validity.valid) {
    field.removeAttribute('aria-invalid');
    field.labels?.[0]?.querySelector('.field-error')?.setAttribute('hidden','');
  }
});

function installAccessibleDialogs() {
  const focusable = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      const items = [...dialog.querySelectorAll(focusable)].filter((item) => !item.hidden && item.getClientRects().length);
      if (!items.length) { event.preventDefault(); return; }
      const first = items[0], last = items.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    dialog.addEventListener("close", () => {
      const origin = dialogFocusOrigins.get(dialog);
      dialogFocusOrigins.delete(dialog);
      if (origin?.isConnected && !origin.disabled && !origin.hidden) origin.focus({preventScroll: true});
    });
  });
}
installAccessibleDialogs();

const routeMeta = {
  overview: ["Рабочее пространство", "Обзор"],
  devices: ["Учёт имущества", "Имущество"],
  "data-exchange": ["Данные реестра", "Импорт и экспорт"],
  incidents: ["Контроль изменений", "Инциденты"],
  locations: ["Размещение", "Кабинеты"],
  vision: ["Физическая инвентаризация", "Проверка по фото"],
  "location-access": ["Администрирование", "Сотрудники и доступ"],
  "agent-credentials": ["Администрирование", "Подключение Agent"],
  "agent-workflow": ["Справка", "Как работает Agent"],
};
const primaryRoutes = new Set(Object.keys(routeMeta));

function setPageHeading(route) {
  const meta = routeMeta[route] || routeMeta.overview;
  document.querySelector(".page-intro .eyebrow").textContent = meta[0];
  document.querySelector(".page-intro h1").textContent = meta[1];
  document.title = `${meta[1]} — AssetGuard`;
  document.querySelectorAll("#main-nav a").forEach((link) => link.removeAttribute("aria-current"));
  document.querySelector(`#main-nav a[href="#${CSS.escape(route)}"]`)?.setAttribute("aria-current", "page");
  closeNavigation();
}

function showPrimaryRoute(route) {
  viewGeneration += 1;
  let target = primaryRoutes.has(route) ? route : "overview";
  if(target === "location-access" && !state.currentUser) target = "overview";
  if(target === "agent-credentials" && state.currentUser?.role !== "ADMIN") target = "overview";
  if(target === "data-exchange" && state.currentUser?.role !== "ADMIN") target = "devices";
  document.querySelectorAll("main > .page-section").forEach((section) => { section.hidden = section.id !== target; });
  const returningToRegistry = target === "devices" && Boolean(state.selectedAsset || state.selectedComputer);
  state.selectedAsset = null;
  state.selectedComputer = null;
  state.assetTab = "overview";
  state.selectedIncident = null;
  state.roomWorkspace = null;
  document.querySelectorAll("#main-nav a").forEach((link) => link.removeAttribute("aria-current"));
  document.querySelector(`#main-nav a[href="#${CSS.escape(target)}"]`)?.setAttribute("aria-current", "page");
  setPageHeading(target);
  document.querySelector(".app-header").classList.remove("nav-open");
  $("nav-toggle").setAttribute("aria-expanded", "false");
  $("nav-toggle").setAttribute("aria-label", "Открыть меню");
  window.scrollTo({top: 0, behavior: "instant"});
  const heading = document.querySelector(".page-intro h1");
  heading.tabIndex = -1;
  heading.focus({preventScroll: true});
  if (returningToRegistry) window.scrollTo({top: state.registryScrollY, behavior: "instant"});
}

function navigateToAsset(assetId) {
  if (!$("devices").hidden) state.registryScrollY = window.scrollY;
  if (location.hash !== `#asset=${assetId}`) location.hash = `asset=${assetId}`;
  else detail(assetId, true, "overview");
}

function navigateToIncident(incidentId) {
  if (location.hash !== `#incident=${incidentId}`) location.hash = `incident=${incidentId}`;
  else openIncidentDetail(incidentId);
}

function navigateToComputer(endpointId) {
  if (!$("devices").hidden) state.registryScrollY = window.scrollY;
  location.hash = `computer=${endpointId}`;
}

async function openComputerDetail(endpointId) {
  const requestView = ++viewGeneration;
  state.selectedAsset = null;
  state.selectedComputer = endpointId;
  document.querySelectorAll('main > .page-section').forEach(section => { section.hidden = section.id !== 'computer-detail'; });
  setPageHeading('devices');
  $("computer-title").textContent = 'Загрузка…';
  $("computer-actions").replaceChildren(); $("computer-meta").textContent = '';
  $("computer-content").hidden = true; $("computer-error").hidden = true;
  try {
    const endpoint = await readRouteData('endpoint',endpointId,`/admin/endpoints/${endpointId}`);
    const [snapshot,historyItems] = await Promise.all([
      endpoint.current_snapshot_id ? readRouteData('snapshot',endpoint.current_snapshot_id,`/admin/snapshots/${endpoint.current_snapshot_id}`) : Promise.resolve(null),
      readRouteData('endpoint-history',endpointId,`/admin/endpoints/${endpointId}/history`),
    ]);
    if (requestView !== viewGeneration) return;
    $("computer-title").textContent = endpoint.hostname || 'Компьютер без имени';
    $("computer-meta").textContent = endpoint.asset_id ? 'Связан с учётной записью имущества' : 'Обнаружен Agent. Учётная запись имущества ещё не связана.';
    $("computer-actions").innerHTML = endpoint.asset_id ? `<a class="button-anchor button-secondary" href="#asset=${endpoint.asset_id}">Карточка имущества</a>` : state.currentUser?.role === 'ADMIN' ? `<button type="button" class="link-endpoint" data-id="${endpointId}" data-name="${escapeHtml(endpoint.hostname)}">Связать с имуществом</button>` : '';
    const summary = state.endpoints.find(item => item.id === endpointId) || endpoint;
    $("computer-key-facts").innerHTML = `<div><span>Состояние</span>${pill(deviceStatus(summary))}</div><div><span>Последняя связь</span><strong>${escapeHtml(dateTime(endpoint.last_seen_at))}</strong></div><div><span>Проверок в истории</span><strong>${endpoint.snapshot_count}</strong></div>`;
    $("computer-hardware").innerHTML = snapshot ? hardware((snapshot.components || []).map(item => item.type === "RAM" ? {...item,capacity:memoryCapacityBytes(item.capacity)} : item)) : '<p class="empty">Состав оборудования появится после первого отчёта Agent.</p>';
    $("computer-identifiers").innerHTML = factRows([['ID компьютера',endpoint.id],...(endpoint.identifiers || []).map(item => [identifierLabels[item.type] || item.type,item.value])]);
    const incidents = state.incidents.filter(item => item.endpoint_id === endpointId);
    $("computer-incidents").innerHTML = incidents.length ? incidents.map(item => `<div class="attention-item"><div><a href="#incident=${item.id}">${escapeHtml(incidentLabel(item,state.changes.find(change => change.id === item.change_event_id)))}</a><small>${escapeHtml(dateTime(item.created_at))}</small></div>${pill(item.status)}</div>`).join('') : '<p class="empty">Инцидентов нет.</p>';
    $("computer-history").innerHTML = historyItems.length ? historyItems.map(item => `<article><time>${escapeHtml(dateTime(item.occurred_at))}</time><div><b>${escapeHtml(eventLabels[item.type] || item.type)}</b><p>${escapeHtml(historyMessage(item))}</p></div></article>`).join('') : '<p class="empty">Проверок пока нет.</p>';
    $("computer-content").hidden = false; bindDynamicActions();
    $("computer-title").tabIndex = -1; $("computer-title").focus({preventScroll:true});
  } catch (error) {
    if (requestView !== viewGeneration || error.stale) return;
    $("computer-title").textContent = 'Не удалось открыть компьютер';
    $("computer-error").textContent = error.message; $("computer-error").hidden = false;
    const retry = document.createElement('button'); retry.textContent = 'Повторить'; retry.type = 'button';
    retry.onclick = () => openComputerDetail(endpointId); $("computer-actions").append(retry);
  }
}

function navigateToRoom(roomId) {
  if (location.hash !== `#room=${roomId}`) location.hash = `room=${roomId}`;
  else openRoomWorkspace(roomId, false);
}

const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const dateTime = (value) => value ? new Intl.DateTimeFormat("ru-RU", {dateStyle: "medium", timeStyle: "short"}).format(new Date(value)) : "—";
const relativeTime = (value) => {
  if (!value) return "Проверок ещё не было";
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("ru", {numeric: "auto"});
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60); if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60); if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
};
const bytes = (value) => {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const number = Number(value);
  if (number >= 1073741824) return `${(number / 1073741824).toFixed(number % 1073741824 ? 1 : 0)} ГБ`;
  if (number >= 1048576) return `${(number / 1048576).toFixed(1)} МБ`;
  return `${Math.round(number / 1024)} КБ`;
};
const storageSize = (value) => value == null ? "—" : `${(Number(value) / 1024).toFixed(Number(value) % 1024 ? 1 : 0)} ГБ`;
// Match the existing transport compatibility rule: Agent MiB and legacy byte values.
const memoryCapacityBytes = (value) => value == null ? null : (Number(value) < 1048576 ? Number(value) * 1048576 : Number(value));
const statusLabels = {OK:"В норме",ATTENTION:"Требует внимания",ANOMALY:"Обнаружено расхождение",OFFLINE:"Не в сети",UNCHECKED:"Нет данных Agent",MANUAL:"Ручной учёт",WARNING:"Требует внимания",NOT_CHECKED:"Не проверено",ONLINE:"В норме",REQUIRES_VERIFICATION:"Требует проверки",IDENTITY_CONFLICT:"Конфликт идентификации",OPEN:"Открыто",UNDER_REVIEW:"На проверке",RESOLVED:"Закрыто",DISMISSED:"Не подтверждено",ACTIVE:"Активен",WRITTEN_OFF:"Списан",REVOKED:"Отозван",PENDING:"Ожидает решения",APPROVED:"Подтверждён",REJECTED:"Отклонён",EXPIRED:"Истёк"};
const assetTypeLabels = {Desktop:"Стационарный компьютер",Laptop:"Ноутбук",Printer:"Принтер",Projector:"Проектор",Network:"Сетевое оборудование",Furniture:"Мебель",Sports:"Спортинвентарь",Educational:"Учебное оборудование",Other:"Другое имущество"};
const categoryLabels = {IT:"IT-оборудование",FURNITURE:"Мебель",SPORTS:"Спортинвентарь",EDUCATIONAL:"Учебное оборудование",OTHER:"Другое имущество"};
const identifierLabels = {SMBIOS_UUID:"Аппаратный UUID",CHASSIS_SERIAL:"Серийный номер корпуса",MOTHERBOARD_SERIAL:"Серийный номер платы",BIOS_SERIAL:"Серийный номер BIOS",AGENT_DEVICE_ID:"ID Agent",MAC:"MAC-адрес"};
const componentLabels = {RAM:"Оперативная память",STORAGE:"Физические накопители",DRIVE:"Разделы дисков",CONTROLLER:"Контроллеры",CPU:"Процессор",GPU:"Видеокарта",MOTHERBOARD:"Материнская плата",NETWORK:"Сетевые интерфейсы",MONITOR:"Мониторы",ENDPOINT:"Устройство"};
const eventLabels = {COMPONENT_ADDED:"Компонент добавлен",COMPONENT_REMOVED:"Компонент не обнаружен в снимке",COMPONENT_CHANGED:"Характеристики изменились",COMPONENT_REPLACED:"Изменился состав компонента",HOSTNAME_CHANGED:"Изменилось имя компьютера",DEVICE_IDENTITY_CHANGED:"Изменился идентификатор устройства",INVENTORY_COMPLETED:"Инвентаризация завершена",BASELINE_ACCEPTED:"Эталон подтверждён",HARDWARE_CHANGE_DETECTED:"Обнаружено изменение оборудования",INCIDENT_CREATED:"Создан инцидент",INCIDENT_CLASSIFIED:"Инцидент проверен",INCIDENT_RESOLVED:"Инцидент закрыт",ASSET_CREATED:"Имущество добавлено",ASSET_UPDATED:"Карточка обновлена",ASSET_MOVED:"Имущество перемещено",ASSET_WRITTEN_OFF:"Имущество списано",ENDPOINT_LINKED:"Компьютер связан с имуществом",ENDPOINT_UNLINKED:"Устройство отвязано",VISION_SCAN_COMPLETED:"Фотопроверка завершена",PHYSICAL_INSPECTION_COMPLETED:"Физический обход завершён",PHYSICAL_INCIDENT_CREATED:"Создан физический инцидент",PHYSICAL_INCIDENT_CLASSIFIED:"Физический инцидент взят на проверку",PHYSICAL_INCIDENT_RESOLVED:"Физический инцидент закрыт"};
const inspectionLabels = {PRESENT:"На месте",MISSING:"Отсутствует",DAMAGED:"Повреждено"};
const physicalActionLabels = {INVESTIGATE:"Дополнительная проверка",MOVE:"Перемещение",REPAIR:"Ремонт",WRITE_OFF:"Списание",FALSE_POSITIVE:"Расхождение не подтвердилось"};
const incidentClassificationLabels = {PLANNED_MAINTENANCE:"Плановое обслуживание",UPGRADE:"Модернизация",REPAIR:"Ремонт",AUTHORIZED_CHANGE:"Разрешённое изменение",COMPONENT_TRANSFER:"Перемещение компонента",UNKNOWN:"Причина не установлена",REQUIRES_INVESTIGATION:"Требуется дополнительная проверка",FALSE_POSITIVE:"Расхождение не подтвердилось"};
const classForStatus = (value) => ({OK:"ok",ONLINE:"ok",ACTIVE:"ok",RESOLVED:"ok",ATTENTION:"attention",WARNING:"warning",OPEN:"warning",UNDER_REVIEW:"warning",ANOMALY:"anomaly",IDENTITY_CONFLICT:"danger",REVOKED:"danger",OFFLINE:"offline",UNCHECKED:"unchecked",NOT_CHECKED:"unchecked",REQUIRES_VERIFICATION:"unchecked"}[value] || "neutral");
const pill = (value) => `<span class="status-pill ${classForStatus(value)}">${escapeHtml(statusLabels[value] || value || "Не проверено")}</span>`;

function showToast(message, error = false) {
  const toast = $("toast"); toast.textContent = message; toast.className = `toast${error ? " error" : ""}`; toast.hidden = false;
  clearTimeout(showToast.timer); showToast.timer = setTimeout(() => { toast.hidden = true; }, 3500);
}
function openConfirmation({title,description,confirmLabel="Подтвердить",reasonLabel=null,reasonPlaceholder="",onConfirm}) {
  confirmationAction=onConfirm;
  $("confirmation-title").textContent=title;
  $("confirmation-description").textContent=description;
  $("confirmation-submit").textContent=confirmLabel;
  $("confirmation-reason-field").hidden=!reasonLabel;
  $("confirmation-reason-label").textContent=reasonLabel||"Причина";
  $("confirmation-reason").required=Boolean(reasonLabel);
  $("confirmation-reason").placeholder=reasonPlaceholder;
  $("confirmation-reason").value="";
  $("confirmation-error").hidden=true;
  openDialog("confirmation-dialog", reasonLabel ? "confirmation-reason" : "confirmation-submit");
}
function setAuthenticatedUi() {
  const signedIn = Boolean(state.currentUser);
  $("auth-screen").hidden = signedIn;
  $("app-header").hidden = !signedIn;
  $("app-main").hidden = !signedIn;
  $("skip-navigation").hidden = !signedIn;
  $("session-state").textContent = signedIn ? state.currentUser.username || "Администратор" : "";
  $("session-role").textContent = signedIn ? userRoleLabel(state.currentUser.role) : "";
  const organization = state.organizations.find((item) => item.id === state.currentUser?.organization_id);
  $("organization-context").textContent = organization?.name || (state.currentUser?.organization_id ? "Назначенная организация" : "Все организации");
}

function setLoginBusy(busy, message = "Проверяем данные входа…") {
  loginInProgress = busy;
  ["login", "username", "token", "login-mode", "retry-session", "toggle-password"].forEach((id) => $(id).disabled = busy);
  $("login").textContent = busy ? "Входим…" : "Войти";
  $("token-form").setAttribute("aria-busy", String(busy));
  $("login-progress").hidden = !busy;
  $("login-progress").textContent = busy ? message : "";
}

function showLoginError(message, field = "token") {
  $("login-error-text").textContent = message;
  $("login-error-field").href = `#${field}`;
  $("login-error").hidden = false;
  $(field).setAttribute("aria-invalid", "true");
  $(field).setAttribute("aria-describedby", "login-error-text");
  $("login-error").focus();
}

function clearLoginError() {
  $("login-error").hidden = true;
  ["username", "token"].forEach((id) => { $(id).removeAttribute("aria-invalid"); $(id).removeAttribute("aria-describedby"); });
}

function setLoadState(phase, message = "") {
  $("app-main").dataset.loadState = phase;
  $("app-main").setAttribute("aria-busy", String(phase === "loading"));
  $("app-feedback").hidden = phase === "ready";
  $("feedback-symbol").textContent = phase === "error" ? "!" : "…";
  $("feedback-title").textContent = phase === "error" ? "Не удалось загрузить данные" : "Загружаем рабочее пространство";
  $("feedback-description").textContent = message || "Получаем реестр, кабинеты и актуальное состояние. Это займёт несколько секунд.";
  $("retry-load").hidden = phase !== "error";
  $("refresh-data").disabled = phase === "loading";
  if (phase === "error") $("app-feedback").focus();
}

function endSession(message = "") {
  sessionGeneration += 1;
  viewGeneration += 1;
  loadGeneration += 1;
  pendingReadControllers.forEach((controller) => controller.abort());
  pendingReadControllers.clear();
  clearRouteDataCache();
  token = "";
  sessionStorage.removeItem("assetguard-admin-token");
  if (state.visionImageUrl) URL.revokeObjectURL(state.visionImageUrl);
  if (state.assetQrUrl) URL.revokeObjectURL(state.assetQrUrl);
  state = emptyState();
  confirmationAction = null;
  notificationGeneration += 1; notificationOffset = 0;
  adminAccessGeneration += 1;
  $("agent-search").value = ""; $("agent-status-filter").value = ""; $("notification-status-filter").value = "";
  ["device-search", "device-status-filter", "device-category-filter", "device-room-filter", "incident-search", "incident-severity-filter", "incident-type-filter", "incident-room-filter", "incident-date-from", "incident-date-to"].forEach(id => $(id).value = "");
  $("device-change-filter").checked = false;
  $("device-sort").value = "recent";
  $("incident-status-filter").value = "ACTIVE";
  ["computer-title", "computer-meta", "computer-actions", "computer-key-facts", "computer-identifiers", "computer-hardware", "computer-history", "computer-incidents", "detail-key-facts", "assets", "incident-center-list", "incident-detail-facts", "incident-detail-actions", "incident-device-action", "device-pagination", "incident-pagination", "device-selected-filters", "incident-selected-filters", "attention-list", "activity-list", "location-tree", "agent-credentials-list", "agent-reenrolments-list", "agent-fleet-list", "agent-fleet-pagination", "notification-list", "notification-pagination", "notification-summary", "users-list", "current-hardware", "baseline-hardware", "detail-changes", "detail-history", "detail-incidents", "device-general", "device-system", "device-identifiers", "incident-detail-evidence", "incident-detail-comparison", "incident-detail-decisions", "room-tab-content", "room-inspection-items", "inspection-review-items", "import-preview-samples", "import-result", "import-file-errors", "import-preview-error", "import-preview-file", "import-preview-scope", "import-selection-summary", "inspection-context", "inspection-error", "inspection-review-comment", "vision-history", "vision-counts", "vision-comparison"].forEach((id) => $(id)?.replaceChildren());
  ["inspection-review-counts", "import-preview-note", "inspection-progress-text"].forEach(id => $(id).textContent = "");
  $("data-exchange-status").textContent = "PDF-сканы могут использовать OCR. Всегда сверяйте результат с оригиналом.";
  $("import-result").hidden = true;
  $("import-file-errors").hidden = true;
  ["detail-title", "detail-meta", "incident-detail-title", "incident-detail-meta", "room-detail-title", "room-detail-path"].forEach((id) => $(id).textContent = "");
  document.querySelectorAll("#app-main form, dialog form").forEach((form) => form.reset());
  document.querySelectorAll("dialog[open]").forEach((dialog) => dialog.close());
  document.querySelectorAll("#app-main > .page-section").forEach((section) => section.hidden = true);
  $("token").value = "";
  $("token").type = "password";
  $("toggle-password").textContent = "Показать";
  $("toggle-password").setAttribute("aria-label", "Показать пароль");
  $("toggle-password").setAttribute("aria-pressed", "false");
  $("agent-credential-secret").value = "";
  setLoginBusy(false);
  clearLoginError();
  $("retry-session").hidden = true;
  setAuthenticatedUi();
  if (message) showLoginError(message);
  else $(loginMode === "password" ? "username" : "token").focus();
}

async function requestJson(path, options = {}, credential = token) {
  const generation = sessionGeneration;
  // Bound reads and authentication only; long-running Vision writes retain their existing behavior.
  const bounded = !options.method || options.method === "GET" || path === "/auth/login" || path === "/auth/logout";
  const controller = bounded ? new AbortController() : null;
  const timer = controller ? setTimeout(() => controller.abort(), readTimeoutMs) : null;
  if (controller) pendingReadControllers.add(controller);
  try {
    const response = await fetch(path, {...options, signal: controller?.signal, headers: {...options.headers, ...(credential ? {"X-AssetGuard-Admin-Token": credential} : {})}});
    let body = null;
    if (response.status !== 204) {
      try { body = await response.json(); }
      catch (error) {
        if (error.name === "AbortError") throw error;
        if (response.ok) throw new Error("Сервер вернул некорректный ответ. Повторите загрузку.");
      }
    }
    if (generation !== sessionGeneration) throw Object.assign(new Error("Сессия изменилась."), {stale: true});
    if (!response.ok) {
      const messages = {401: "Сессия истекла или данные входа неверны. Войдите снова.", 403: "У вас нет доступа к этому действию.", 404: "Запись не найдена или недоступна вам.", 429: "Слишком много запросов. Подождите немного и повторите попытку."};
      const message = messages[response.status] || (response.status >= 500 ? "Сервер временно не может обработать запрос. Повторите попытку." : typeof body?.detail === "string" ? body.detail : typeof body?.detail?.message === "string" ? body.detail.message : "Проверьте заполненные поля и повторите попытку.");
      if (response.status === 401 && state.currentUser && credential === token) endSession(messages[401]);
      throw Object.assign(new Error(message), {status: response.status, detail: body?.detail});
    }
    return body;
  } catch (error) {
    if (generation !== sessionGeneration) throw Object.assign(new Error("Сессия изменилась."), {stale: true});
    if (error.name === "AbortError") throw new Error("Сервер не ответил за 20 секунд. Проверьте подключение и повторите попытку.");
    if (error instanceof TypeError) throw new Error("Нет связи с сервером. Проверьте подключение и повторите попытку.");
    throw error;
  } finally {
    if (timer) clearTimeout(timer);
    if (controller) pendingReadControllers.delete(controller);
  }
}
async function api(path, options = {}) { return requestJson(path, options); }

function clearRouteDataCache() {
  routeDataCache.clear();
  routeRequestCache.clear();
}

function readRouteData(kind, id, path) {
  const generation = sessionGeneration;
  const key = `${kind}:${id}`;
  const cached = routeDataCache.get(key);
  if (cached && Date.now() - cached.loadedAt < routeCacheLifetimeMs) return Promise.resolve(cached.value);
  const pending = routeRequestCache.get(key);
  if (pending) return pending;
  const request = api(path).then((value) => {
    if (generation !== sessionGeneration) throw Object.assign(new Error("Сессия изменилась."), {stale: true});
    routeDataCache.set(key, {value, loadedAt: Date.now()});
    if (routeRequestCache.get(key) === request) routeRequestCache.delete(key);
    return value;
  }).catch((error) => {
    if (routeRequestCache.get(key) === request) routeRequestCache.delete(key);
    throw error;
  });
  routeRequestCache.set(key, request);
  return request;
}
async function apiBlob(path) {
  const generation = sessionGeneration;
  const response = await fetch(path, {headers: {"X-AssetGuard-Admin-Token": token}});
  const blob = response.ok ? await response.blob() : null;
  if (generation !== sessionGeneration) throw Object.assign(new Error("Сессия изменилась."), {stale: true});
  if (!response.ok) throw new Error("Не удалось загрузить изображение результата.");
  return blob;
}
async function copyAgentCredential(fieldId) {
  const field=$(fieldId), value=field.value;
  if(!value) return;
  try { await navigator.clipboard.writeText(value); }
  catch { field.focus(); field.select(); if(!document.execCommand("copy")) throw new Error("Не удалось скопировать. Выделите значение и скопируйте вручную."); }
  showToast("Скопировано в буфер обмена");
}
function deviceStatus(endpoint, asset = null) {
  if (asset?.status === "WRITTEN_OFF") return "WRITTEN_OFF";
  if (!endpoint && asset && !["Desktop", "Laptop"].includes(asset.asset_type)) return "MANUAL";
  if (!endpoint?.current_snapshot) return "UNCHECKED";
  if (endpoint.status === "IDENTITY_CONFLICT") return "ANOMALY";
  if (agentConnection(endpoint) !== "ONLINE") return "UNCHECKED";
  if (endpoint.open_changes > 0 || endpoint.open_incidents > 0) return "ATTENTION";
  return "OK";
}
function locationLabel(item) { return [item.organization,item.building,item.floor && `этаж ${item.floor}`,item.room && `каб. ${item.room}`].filter(Boolean).join(" · "); }
function buildDevices() {
  const linkedEndpointIds = new Set();
  const devices = state.assets.map((asset) => {
    const endpoint = asset.endpoint;
    if (endpoint) linkedEndpointIds.add(endpoint.id);
    return {kind:"asset",assetId:asset.id,endpointId:endpoint?.id || null,name:asset.name,inventoryNumber:asset.inventory_number,hostname:endpoint?.hostname || null,building:asset.building,floor:asset.floor,room:asset.room,organization:asset.organization,category:asset.category,assetType:asset.asset_type,roomId:asset.room_id,trackingMode:asset.tracking_mode,quantity:asset.quantity,unit:asset.unit,endpoint,status:deviceStatus(endpoint,asset)};
  });
  state.endpoints.filter((endpoint) => !linkedEndpointIds.has(endpoint.id)).forEach((endpoint) => devices.push({kind:"endpoint",assetId:null,endpointId:endpoint.id,name:endpoint.hostname || "Непривязанное устройство",inventoryNumber:null,hostname:endpoint.hostname,building:null,floor:null,room:null,organization:null,endpoint,status:deviceStatus(endpoint)}));
  state.devices = devices;
}
function deviceForEndpoint(endpointId) { return state.devices.find((device) => device.endpointId === endpointId); }
function incidentLabel(incident, change = null) {
  const evidence = change?.evidence || incident?.evidence;
  const type = change?.component_type || incident?.component_type;
  if (type === 'RAM' && evidence?.previous && evidence?.current) {
    if (evidence.previous.capacity !== evidence.current.capacity) return 'Изменился объём оперативной памяти';
    return 'Изменились сведения о модуле памяти';
  }
  if (type === 'CPU') return 'Изменились сведения о процессоре';
  if (type === 'STORAGE') return evidence?.previous && !evidence.current ? 'Накопитель не представлен в новом снимке' : 'Изменились сведения о накопителе';
  const parts = (incident?.title || "").split(":");
  const component = componentLabels[change?.component_type || parts[0]] || change?.component_type || parts[0] || "Оборудование";
  const event = eventLabels[change?.type || parts[1]?.trim()] || change?.type || parts[1]?.trim() || "обнаружено изменение";
  return `${component}: ${event}`;
}
function renderDashboard() {
  const devices = state.devices;
  renderSetupGuide();
  const online = devices.filter((item) => item.status === "OK").length;
  const attention = devices.filter((item) => ["ATTENTION","ANOMALY"].includes(item.status));
  const unchecked = devices.filter((item) => item.status === "UNCHECKED");
  const openIncidents = incidentItems().filter((item) => ["OPEN","UNDER_REVIEW"].includes(item.status));
  $("devices-count").textContent = state.assets.length; $("online-count").textContent = online; $("attention-count").textContent = attention.length; $("unchecked-count").textContent = unchecked.length; $("open-incidents-count").textContent = openIncidents.length;
  $("nav-incident-count").textContent = openIncidents.length; $("nav-incident-count").hidden = !openIncidents.length;
  const banner = $("attention-banner");
  if (!devices.length) {
    banner.className = "attention-banner is-loading"; banner.innerHTML = '<span class="attention-icon">1</span><div><strong>Начните с настройки школы</strong><p>Создайте кабинеты и добавьте имущество. Agent подключайте, если нужно автоматически следить за компьютерами.</p></div>';
  } else if (!attention.length && !unchecked.length && !openIncidents.length) {
    banner.className = "attention-banner ok"; banner.innerHTML = '<span class="attention-icon">✓</span><div><strong>Новых проблем не обнаружено</strong><p>У компьютеров с Agent нет открытых изменений. Остальное имущество учитывается в реестре вручную.</p></div>';
  } else {
    banner.className = "attention-banner"; banner.innerHTML = `<span class="attention-icon">!</span><div><strong>${openIncidents.length ? `Открытых инцидентов: ${openIncidents.length}` : attention.length ? `Компьютеров с проблемами: ${attention.length}` : "Есть компьютеры без свежих данных Agent"}</strong><p>${unchecked.length ? `Без свежих данных Agent: ${unchecked.length}. ` : ""}Проверьте задачи в списке ниже.</p></div>`;
  }
  const priorityIncidents = incidentItems().filter(item => ["OPEN","UNDER_REVIEW"].includes(item.status)).sort((a,b) => ["HIGH","MEDIUM","LOW"].indexOf(a.severity)-["HIGH","MEDIUM","LOW"].indexOf(b.severity) || new Date(b.created_at)-new Date(a.created_at)).slice(0,6);
  const unlinked = devices.filter(item => item.kind === "endpoint");
  const priorityCandidates = [...new Map([...attention,...unchecked,...unlinked].map(item => [item.endpointId || item.assetId,item])).values()];
  const priority = priorityCandidates.filter(item => !priorityIncidents.some(incident => incident.endpoint_id && incident.endpoint_id === item.endpointId)).slice(0, Math.max(0,6-priorityIncidents.length));
  const priorityRows = priorityIncidents.map(incident => `<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(incident.kind === "PHYSICAL" ? `${incident.asset_name} · ${inspectionLabels[incident.issue_type] || "Расхождение обхода"}` : incidentLabel(incident,state.changes.find(change => change.id === incident.change_event_id)))}</strong><small>${escapeHtml(incident.kind === "PHYSICAL" ? "Обход" : deviceForEndpoint(incident.endpoint_id)?.name || "Компьютер")} · ${escapeHtml(statusLabels[incident.status])} · ${relativeTime(incident.created_at)}</small></div><a class="button-anchor button-secondary" href="#${incident.kind === "PHYSICAL" ? "physical-incident" : "incident"}=${incident.id}">Открыть</a></div>`).join("");
  $("attention-badge").textContent = priority.length+priorityIncidents.length ? String(priority.length+priorityIncidents.length) : "Всё спокойно"; $("attention-badge").className = `status-pill ${priority.length+priorityIncidents.length ? "warning" : "ok"}`;
  $("attention-list").innerHTML = priorityRows + (priority.length ? priority.map((item) => `<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.room || item.hostname || "Расположение не указано")} · Agent · ${relativeTime(item.endpoint?.last_seen_at)} · ${escapeHtml(statusLabels[item.status])}${item.endpoint?.open_changes ? ` · изменений: ${item.endpoint.open_changes}` : ""}</small></div>${item.assetId ? `<button class="open-device button-secondary" data-id="${item.assetId}">Открыть</button>` : `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать</button>`}</div>`).join("") : priorityIncidents.length ? "" : '<p class="empty">Ничего не требует внимания.</p>');
  $("overview-unlinked").hidden = !unlinked.length;
  $("overview-unlinked").textContent = `Компьютеры без связи с имуществом: ${unlinked.length} →`;
  const activity = state.changes.slice(0, 5);
  $("activity-list").innerHTML = activity.length ? activity.map((change) => { const device = deviceForEndpoint(change.endpoint_id); return `<article><time>${dateTime(change.detected_at)}</time><div><b>${escapeHtml(eventLabels[change.type] || change.type)}</b><p>${escapeHtml(device?.name || "Устройство")} · ${escapeHtml(componentLabels[change.component_type] || change.component_type)}</p></div></article>`; }).join("") : '<p class="empty">История изменений пока пуста.</p>';
  const latest = devices.map((item) => item.endpoint?.last_seen_at).filter(Boolean).sort().at(-1); $("last-activity").textContent = latest ? `Последняя проверка ${relativeTime(latest)}` : "Проверок пока нет";
  renderIncidentCenter();
  const reporting = state.endpoints.filter((item) => agentConnection(item) === "ONLINE").length;
  $("agent-online-badge").textContent = state.endpoints.length ? `${reporting} компьютеров с Agent на связи` : "Agent не подключён"; $("agent-online-badge").className = `status-pill ${reporting ? "ok" : "neutral"}`;
  $("agent-last-signal").textContent = latest ? `Инвентаризация получена ${relativeTime(latest)}` : "Ожидаем данные Agent";
  $("agent-proof-text").textContent = latest ? `${dateTime(latest)} · отчёт принят, нормализован и сохранён в истории.` : "После первой отправки здесь появится фактическое время последней инвентаризации.";
  bindDynamicActions();
}

function incidentItems() {
  return [...state.incidents.map((item) => ({...item, kind: "TECHNICAL", room_id: deviceForEndpoint(item.endpoint_id)?.roomId})),
    ...state.physicalIncidents.map((item) => ({...item, kind: "PHYSICAL"}))].sort((a,b) => new Date(b.created_at)-new Date(a.created_at) || a.id.localeCompare(b.id));
}

const listPageSize = 20;
function renderSelectedFilters(id, controls, onClear) {
  const values = controls.filter(([controlId, defaultValue = ""]) => {
    const control = $(controlId);
    return control.type === "checkbox" ? control.checked : control.value && control.value !== defaultValue;
  }).map(([controlId]) => {
    const control = $(controlId);
    return control.tagName === "SELECT" ? control.selectedOptions[0].textContent : control.type === "checkbox" ? "С изменениями" : control.value;
  });
  $(id).innerHTML = values.map(value => `<span class="tag">${escapeHtml(value)}</span>`).join("") + (values.length ? '<button type="button" class="button-link">Сбросить всё</button>' : "");
  $(id).querySelector("button")?.addEventListener("click", onClear);
  return values.length;
}

function renderListPagination(id, page, total, onChange) {
  const container = $(id), pages = Math.max(1, Math.ceil(total / listPageSize));
  container.hidden = total <= listPageSize;
  container.innerHTML = `<button type="button" class="button-secondary" data-step="-1" ${page === 1 ? "disabled" : ""}>Предыдущая</button><span role="status">Страница ${page} из ${pages}</span><button type="button" class="button-secondary" data-step="1" ${page === pages ? "disabled" : ""}>Следующая</button>`;
  container.querySelectorAll("button").forEach(button => button.onclick = () => {
    onChange(page + Number(button.dataset.step));
    container.scrollIntoView({block: "nearest"});
    (container.querySelector(`[data-step="${button.dataset.step}"]:not([disabled])`) || container.querySelector("button:not([disabled])"))?.focus({preventScroll: true});
  });
}

function filteredIncidents() {
  const status = $("incident-status-filter").value;
  const severity = $("incident-severity-filter").value;
  const query = $("incident-search").value.trim().toLocaleLowerCase("ru");
  const kind = $("incident-type-filter").value, room = $("incident-room-filter").value;
  const from = $("incident-date-from").value, to = $("incident-date-to").value;
  const invalidDates = Boolean(from && to && from > to);
  $("incident-filter-error").hidden = !invalidDates;
  return incidentItems().filter((incident) => {
    const change = state.changes.find((item) => item.id === incident.change_event_id);
    const device = deviceForEndpoint(incident.endpoint_id);
    const active = ["OPEN","UNDER_REVIEW"].includes(incident.status);
    const statusMatch = !status || (status === "ACTIVE" ? active : incident.status === status);
    const text = [incident.title, incidentLabel(incident, change), device?.name, device?.hostname, device?.inventoryNumber, device?.room, incident.asset_name, incident.inventory_number, incident.room, inspectionLabels[incident.issue_type]].filter(Boolean).join(" ").toLocaleLowerCase("ru");
    const date = new Date(incident.created_at);
    const localDate = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;
    return !invalidDates && statusMatch && (!severity || incident.severity === severity) && (!query || text.includes(query)) && (!kind || incident.kind === kind) && (!room || incident.room_id === room) && (!from || localDate >= from) && (!to || localDate <= to);
  });
}

function renderIncidentCenter() {
  const selectedRoom = $("incident-room-filter").value;
  const rooms = availableRoomOptions();
  $("incident-room-filter").innerHTML = '<option value="">Все кабинеты</option>' + rooms.map(room => `<option value="${room.id}">${escapeHtml(room.label)}</option>`).join("");
  $("incident-room-filter").value = rooms.some(room => room.id === selectedRoom) ? selectedRoom : "";
  const incidents = filteredIncidents();
  const activeFilters = renderSelectedFilters("incident-selected-filters", [["incident-search"], ["incident-status-filter", "ACTIVE"], ["incident-severity-filter"], ["incident-type-filter"], ["incident-room-filter"], ["incident-date-from"], ["incident-date-to"]], clearIncidentFilters);
  $("incident-active-filter-count").hidden = !activeFilters;
  $("incident-active-filter-count").textContent = activeFilters || "";
  const openCount = incidentItems().filter((item) => ["OPEN","UNDER_REVIEW"].includes(item.status)).length;
  $("incident-center-count").textContent = `${incidents.length} из ${incidentItems().length}`;
  $("incident-center-count").className = `status-pill ${openCount ? "warning" : "ok"}`;
  state.incidentPage = Math.min(state.incidentPage, Math.max(1, Math.ceil(incidents.length / listPageSize)));
  renderListPagination("incident-pagination", state.incidentPage, incidents.length, page => {state.incidentPage = page; renderIncidentCenter();});
  const list = $("incident-center-list");
  if (!incidents.length) {
    const hasAny = incidentItems().length > 0;
    list.innerHTML = `<div class="panel empty-state"><strong>${hasAny ? "По выбранным фильтрам ничего не найдено" : "Открытых инцидентов нет"}</strong><p>${hasAny ? "Измените статус, приоритет или поисковый запрос." : "В доступной вам области нет инцидентов с выбранным статусом."}</p>${hasAny ? '<button type="button" class="button-secondary clear-incident-filters-inline">Сбросить фильтры</button>' : '<a class="button-anchor" href="#devices">Открыть реестр</a>'}</div>`;
    list.querySelector(".clear-incident-filters-inline")?.addEventListener("click", clearIncidentFilters);
    return;
  }
  list.innerHTML = incidents.slice((state.incidentPage-1)*listPageSize, state.incidentPage*listPageSize).map((incident) => {
    if (incident.kind === "PHYSICAL") return `<article class="panel incident-card"><div class="incident-card-head"><div><span class="eyebrow">Обход · физический · ${escapeHtml(incident.severity === "HIGH" ? "Высокий" : incident.severity === "LOW" ? "Низкий" : "Средний")} приоритет</span><h3>${escapeHtml(incident.asset_name)}</h3><p>${escapeHtml(incident.inventory_number)} · каб. ${escapeHtml(incident.room)} · ${dateTime(incident.created_at)}</p></div>${pill(incident.status)}</div><p><strong>${escapeHtml(inspectionLabels[incident.issue_type])}</strong> · проблемных единиц: ${incident.affected_quantity}</p><div class="incident-card-actions"><button type="button" class="open-physical-incident" data-id="${incident.id}">Открыть инцидент</button></div></article>`;
    const change = state.changes.find((item) => item.id === incident.change_event_id);
    const device = deviceForEndpoint(incident.endpoint_id);
    const location = device ? locationLabel(device) : "Расположение не указано";
    const comparison = change ? `<div class="incident-comparison"><div><span>Было</span><strong>${escapeHtml(componentSummary(change.component_type, change.evidence?.previous))}</strong></div><b aria-hidden="true">→</b><div><span>Стало</span><strong>${escapeHtml(componentSummary(change.component_type, change.evidence?.current))}</strong></div></div>` : '<p class="meta">Подробное доказательство доступно в карточке устройства.</p>';
    const deviceAction = `<button type="button" class="open-incident" data-id="${incident.id}">Открыть инцидент</button>`;
    const decisions = state.currentUser?.role === "ADMIN" && ["OPEN","UNDER_REVIEW"].includes(incident.status) ? `<button type="button" class="incident-review button-secondary" data-id="${incident.id}">Взять на проверку</button><button type="button" class="incident-resolve" data-id="${incident.id}">Зафиксировать решение</button>` : "";
    return `<article class="panel incident-card"><div class="incident-card-head"><div><span class="eyebrow">Agent · технический · ${escapeHtml(incident.severity === "HIGH" ? "Высокий приоритет" : incident.severity === "LOW" ? "Низкий приоритет" : "Средний приоритет")}</span><h3>${escapeHtml(device?.name || device?.hostname || "Устройство")}</h3><p>${escapeHtml(location)} · ${dateTime(incident.created_at)}</p></div>${pill(incident.status)}</div><div class="incident-card-body"><div><strong>${escapeHtml(incidentLabel(incident, change))}</strong><p>AssetGuard обнаружил расхождение с подтверждённым эталоном. Окончательное решение принимает ответственный сотрудник.</p></div>${comparison}</div><div class="incident-card-actions">${deviceAction}${decisions}</div></article>`;
  }).join("");
  bindDynamicActions();
  list.querySelectorAll(".open-physical-incident").forEach(button => button.onclick = () => {location.hash = `physical-incident=${button.dataset.id}`;});
  document.querySelectorAll(".incident-review").forEach((button) => button.onclick = () => openIncidentDecisionDialog(button.dataset.id, false));
  document.querySelectorAll(".incident-resolve").forEach((button) => button.onclick = () => openIncidentDecisionDialog(button.dataset.id, true));
}

function clearIncidentFilters() {
  state.incidentPage = 1;
  ["incident-type-filter", "incident-room-filter", "incident-date-from", "incident-date-to"].forEach(id => $(id).value = "");
  $("incident-status-filter").value = "ACTIVE";
  $("incident-severity-filter").value = "";
  $("incident-search").value = "";
  renderIncidentCenter();
}
function renderSetupGuide() {
  const guide = $("setup-guide");
  if (!state.currentUser || state.currentUser.role !== "ADMIN") { guide.hidden = true; $("setup-help").hidden = true; return; }
  const hasRooms = state.locations.some((building) => building.floors?.some((floor) => floor.rooms?.length));
  const hasAssets = state.assets.length > 0;
  const hasAgent = state.endpoints.length > 0;
  const complete = Number(hasRooms) + Number(hasAssets);
  const steps = [
    {done:hasRooms, title:"Создайте кабинеты", text:hasRooms ? "Структура школы готова для размещения имущества." : "Добавьте корпус, этаж и хотя бы один кабинет.", href:"#locations", action:hasRooms ? "Открыть кабинеты" : "Создать кабинеты"},
    {done:hasAssets, title:"Добавьте имущество", text:hasAssets ? `В реестре уже ${state.assets.length} ${state.assets.length === 1 ? "запись" : "записей"}.` : "Загрузите школьную ведомость или добавьте первую запись вручную.", href:"#devices", action:hasAssets ? "Открыть реестр" : "Добавить имущество"},
    {done:hasAgent, optional:true, title:"Подключите компьютеры (по желанию)", text:hasAgent ? `AssetGuard получает данные от ${state.endpoints.length} компьютеров.` : "Установите Agent на компьютеры, чтобы видеть их состояние и изменения.", href:"#agent-workflow", action:hasAgent ? "Посмотреть компьютеры" : "Как подключить Agent"},
  ];
  $("setup-progress").textContent = `${complete} из 2 основных шагов`;
  $("setup-progress").className = `status-pill ${complete === 2 ? "ok" : "neutral"}`;
  $("setup-steps").innerHTML = steps.map((step) => `<article class="setup-step ${step.done ? "is-done" : ""} ${step.optional ? "is-optional" : ""}"><span class="setup-check" aria-hidden="true">${step.done ? "✓" : step.optional ? "↗" : "○"}</span><div><strong>${escapeHtml(step.title)}</strong><p>${escapeHtml(step.text)}</p><a href="${step.href}">${escapeHtml(step.action)} →</a></div></article>`).join("");
  $("setup-help").hidden = false;
  guide.hidden = complete === 2 && !state.guideExpanded;
  $("setup-help").setAttribute("aria-expanded", String(!guide.hidden));
}
function renderOperations(operations) {
  const status = $("operations-status"), summary = $("operations-summary");
  if (!operations) { status.textContent = "Нет данных"; status.className = "status-pill neutral"; summary.innerHTML = '<p class="empty">Операционные данные недоступны.</p>'; return; }
  const failed = Number(operations.ingest?.failed || 0), offline = Number(operations.agents?.offline || 0) + Number(operations.agents?.stale || 0), conflicts = Number(operations.agents?.identity_conflicts || 0);
  const attention = failed + offline + conflicts + Number(operations.notifications?.retrying || 0);
  status.textContent = attention ? "Требует внимания" : "В норме"; status.className = `status-pill ${attention ? "warning" : "ok"}`;
  summary.innerHTML = [
    ["Agent на связи", `${operations.agents?.online || 0} из ${operations.agents?.total || 0}`],
    ["Нет связи / устарели", offline],
    ["Ошибки приёма данных", failed],
    ["Конфликты идентификации", conflicts],
    ["Уведомления в очереди / повтор", `${operations.notifications?.pending || 0} / ${operations.notifications?.retrying || 0}`],
    ["Последний отчёт Agent", operations.agents?.last_inventory_at ? relativeTime(operations.agents.last_inventory_at) : "—"],
    ["Свободно для Vision", bytes(operations.storage?.free_bytes)],
    ["Размер базы", bytes(operations.database?.bytes)],
  ].map(([label,value]) => `<div class="summary-line"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
}
function locationContact(item) { return [item.responsible_name, item.responsible_contact].filter(Boolean).join(" · "); }
function roomMetric(label,value,help) { return `<article><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(help)}</small></article>`; }
function roomCountRows(counts) { return counts && Object.keys(counts).length ? Object.entries(counts).map(([name,count])=>`<div class="summary-line"><span>${escapeHtml(name)}</span><strong>${escapeHtml(count)}</strong></div>`).join("") : '<p class="empty">Подтверждённых объектов пока нет.</p>'; }
function canEditRoom(roomId) { return state.currentUser?.role==="ADMIN"||Boolean(roomId&&state.currentUser?.editable_room_ids?.includes(roomId)); }
function inspectionSummary(inspection) {
  if(!inspection)return '<p class="empty">Физических обходов пока не было.</p>';
  const counts=inspection.counts||{};
  return `<div class="inspection-summary"><div><strong>${dateTime(inspection.completed_at)}</strong><small>${escapeHtml(inspection.inspector_name)}</small></div><div class="inspection-counts"><span class="inspection-present">На месте: ${counts.PRESENT||0}</span><span class="inspection-missing">Отсутствует: ${counts.MISSING||0}</span><span class="inspection-damaged">Повреждено: ${counts.DAMAGED||0}</span></div>${inspection.comment?`<p>${escapeHtml(inspection.comment)}</p>`:""}</div>`;
}
function renderInspectionTab(workspace) {
  const inventory=workspace.inventory, latest=workspace.latest_inspection;
  const canStart=canEditRoom(workspace.room.id)&&inventory.assets.length>0;
  const launch=canStart?'<button type="button" class="room-inspection-launch">Начать новый обход</button>':"";
  const heading=`<div class="section-heading"><div><span class="eyebrow">Физическая инвентаризация</span><h3>Обход кабинета</h3><p>Результат фиксируется от имени вошедшего сотрудника и остаётся в истории.</p></div>${launch}</div>`;
  if(!latest) {
    const nextStep=canStart?'<button type="button" class="room-inspection-launch">Начать обход</button>':!inventory.assets.length?'<p>Сначала добавьте имущество в кабинет.</p>':"";
    return `${heading}<div class="empty-state"><strong>Кабинет ещё не обходили</strong><p>Проверьте каждую позицию и зафиксируйте отсутствующее или повреждённое имущество.</p>${nextStep}</div>`;
  }
  const items=latest.items.map((item)=>{
    const affected=item.affected_quantity?` · ${item.affected_quantity}`:"";
    const comment=item.comment?`<p>${escapeHtml(item.comment)}</p>`:"";
    return `<article><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.inventory_number)} · ожидалось ${item.expected_quantity}</small></div><span class="inspection-result ${item.result.toLowerCase()}">${escapeHtml(inspectionLabels[item.result])}${affected}</span>${comment}</article>`;
  }).join("");
  const previous=(workspace.inspections||[]).slice(1);
  const history=previous.map(inspectionSummary).join("")||'<p class="empty">Это первый обход кабинета.</p>';
  return `${heading}${inspectionSummary(latest)}<div class="inspection-result-list">${items}</div><details class="inspection-history"><summary>Предыдущие обходы (${previous.length})</summary>${history}</details>`;
}
function renderPhysicalIncident(incident, roomId) {
  const active=["OPEN","UNDER_REVIEW"].includes(incident.status), latest=incident.decisions?.at(-1);
  const act=latest?.has_act?`<button type="button" class="button-link physical-incident-act" data-id="${incident.id}" data-number="${escapeHtml(latest.document_number)}">Скачать акт PDF</button>`:"";
  const operation=latest?.quantity?`<small>${latest.quantity} ${escapeHtml(latest.operation_snapshot?.unit||"")} · акт ${escapeHtml(latest.document_number)}</small>`:"";
  const decision=latest?`<div class="physical-decision"><p><strong>${escapeHtml(physicalActionLabels[latest.action]||latest.action)}</strong> · ${escapeHtml(latest.actor)}<br>${escapeHtml(latest.comment)}</p>${operation}${act}</div>`:"";
  const action=active&&canEditRoom(roomId)?`<button type="button" class="physical-incident-action" data-id="${incident.id}">Принять решение</button>`:"";
  return `<article class="physical-incident"><div class="physical-incident-main"><div><strong>${escapeHtml(incident.title)}</strong><small>${escapeHtml(incident.inventory_number)} · ${dateTime(incident.created_at)}</small></div>${pill(incident.status)}</div><p>${escapeHtml(incident.description)}</p><p class="meta">Проблемных единиц: ${incident.affected_quantity} · Приоритет: ${incident.severity==="HIGH"?"высокий":"средний"}</p>${decision}${action}</article>`;
}
function renderRoomTab() {
  const workspace=state.roomWorkspace;
  if(!workspace)return;
  const tab=state.roomTab, inventory=workspace.inventory, agents=workspace.agents, vision=workspace.vision;
  document.querySelectorAll("[data-room-tab]").forEach((button)=>button.setAttribute("aria-selected",String(button.dataset.roomTab===tab)));
  let html="";
  if(tab==="overview") {
    const ready=workspace.baseline.agent_ready+(workspace.baseline.vision_ready?1:0), total=workspace.baseline.agent_total+1;
    html=`<div class="metrics room-metrics">${roomMetric("Позиций",inventory.positions,"записей в реестре")}${roomMetric("Количество",inventory.quantity,"единиц имущества")}${roomMetric("Agent",`${agents.filter((item)=>item.status==="ONLINE").length} из ${agents.length}`,"компьютеров на связи")}${roomMetric("Эталоны",`${ready} из ${total}`,"Agent и фото помещения")}</div><div class="room-overview-grid"><section><span class="eyebrow">Ответственный</span><h3>${escapeHtml(workspace.room.responsible_name||"Не назначен")}</h3><p class="meta">${escapeHtml(workspace.room.responsible_contact||"Контакт не указан")}</p><p>${escapeHtml(workspace.room.purpose||"Назначение кабинета не указано")}</p></section><section><span class="eyebrow">Состав</span><div class="summary-lines">${inventory.categories.map((item)=>`<div class="summary-line"><span>${escapeHtml(categoryLabels[item.category]||item.category)}</span><strong>${item.quantity}</strong></div>`).join("")||'<p class="empty">Имущество ещё не добавлено.</p>'}</div></section></div>`;
  } else if(tab==="baseline") {
    html=`<div class="room-two-columns"><section><span class="eyebrow">Компьютеры Agent</span><h3>Подтверждённый состав</h3>${agents.length?agents.map((item)=>`<div class="room-status-row"><div><strong>${escapeHtml(item.hostname||"Компьютер")}</strong><small>${item.has_baseline?"Эталон оборудования подтверждён":"Нужно открыть компьютер и подтвердить эталон"}</small></div>${pill(item.has_baseline?"OK":"NOT_CHECKED")}</div>`).join(""):'<p class="empty">В кабинете нет связанных компьютеров Agent.</p>'}</section><section><span class="eyebrow">Vision</span><h3>Эталон помещения</h3>${workspace.baseline.vision_ready?`<div class="attention-banner ok"><span class="attention-icon">✓</span><div><strong>Фото-эталон подтверждён</strong><p>Следующая проверка будет сравнена с этим составом.</p></div></div><div class="summary-lines">${roomCountRows(vision?.baseline_counts)}</div>`:'<div class="empty-state"><strong>Фото-эталона ещё нет</strong><p>Откройте Vision, загрузите исходное фото кабинета и подтвердите результат.</p><button type="button" class="button-anchor room-vision-launch">Создать эталон</button></div>'}</section></div>`;
  } else if(tab==="current") {
    html=`<div class="room-two-columns"><section><span class="eyebrow">Последние сигналы Agent</span><h3>Компьютеры</h3>${agents.length?agents.map((item)=>`<div class="room-status-row"><div><strong>${escapeHtml(item.hostname||"Компьютер")}</strong><small>Последний отчёт: ${escapeHtml(relativeTime(item.last_seen_at))}</small></div>${pill(item.status)}</div>`).join(""):'<p class="empty">Agent-компьютеры не привязаны к имуществу этого кабинета.</p>'}</section><section><span class="eyebrow">Последнее фото</span><h3>Vision</h3>${vision?.latest_scan?`${pill(vision.latest_scan.status)}<p class="meta">${dateTime(vision.latest_scan.created_at)}</p><div class="summary-lines">${roomCountRows(vision.latest_scan.counts)}</div>`:'<p class="empty">Фотопроверок этого кабинета пока нет.</p>'}</section></div>`;
  } else if(tab==="inventory") {
    html=inventory.assets.length?`<div class="table-wrap"><table><thead><tr><th>Имущество</th><th>Категория</th><th>Учёт</th><th>Количество</th><th></th></tr></thead><tbody>${inventory.assets.map((asset)=>`<tr><td data-label="Имущество"><strong>${escapeHtml(asset.name)}</strong><small>${escapeHtml(asset.inventory_number)}</small></td><td data-label="Категория">${escapeHtml(categoryLabels[asset.category]||asset.category)}</td><td data-label="Учёт">${asset.tracking_mode==="GROUPED"?"Групповой":"Поштучный"}</td><td data-label="Количество">${asset.quantity} ${escapeHtml(asset.unit)}</td><td><button class="button-secondary open-room-asset" data-id="${asset.id}">Открыть</button></td></tr>`).join("")}</tbody></table></div>`:'<div class="empty-state"><strong>В кабинете пока нет имущества</strong><p>Добавьте запись вручную или импортируйте школьную ведомость.</p><a class="button-anchor" href="#devices">Открыть реестр</a></div>';
  } else if(tab==="inspection") {
    html=renderInspectionTab(workspace);
  } else if(tab==="vision") {
    html=vision?`<div class="room-two-columns"><section><span class="eyebrow">Эталон</span><h3>${vision.has_baseline?"Подтверждён":"Не создан"}</h3><div class="summary-lines">${roomCountRows(vision.baseline_counts)}</div></section><section><span class="eyebrow">Текущая проверка</span><h3>${vision.latest_scan?dateTime(vision.latest_scan.created_at):"Проверок нет"}</h3>${vision.latest_scan?`${pill(vision.latest_scan.status)}<div class="summary-lines">${roomCountRows(vision.latest_scan.counts)}</div>`:""}<button type="button" class="button-anchor room-vision-launch">Открыть Vision</button></section></div>`:'<div class="empty-state"><strong>Кабинет ещё не проверялся по фото</strong><p>Vision найдёт объекты, сохранит доказательство и сравнит следующий кадр с эталоном.</p><button type="button" class="button-anchor room-vision-launch">Провести проверку</button></div>';
  } else if(tab==="incidents") {
    const physical=workspace.physical_incidents||[], hasActive=workspace.incidents.length||physical.some((item)=>["OPEN","UNDER_REVIEW"].includes(item.status));
    html=`${hasActive?'':'<div class="attention-banner ok"><span class="attention-icon">✓</span><div><strong>Открытых инцидентов нет</strong><p>Текущие данные не требуют решения ответственного.</p></div></div>'}<div class="room-two-columns"><section><span class="eyebrow">Физическая проверка</span><h3>Расхождения обходов</h3>${physical.length?`<div class="stack-list">${physical.map((item)=>renderPhysicalIncident(item,workspace.room.id)).join("")}</div>`:'<p class="empty">Физических расхождений не зафиксировано.</p>'}</section><section><span class="eyebrow">Agent</span><h3>Изменения компьютеров</h3>${workspace.incidents.length?`<div class="stack-list">${workspace.incidents.map((item)=>`<article class="room-incident"><div><strong>${escapeHtml(item.title)}</strong><small>${dateTime(item.created_at)}</small></div>${pill(item.status)}</article>`).join("")}</div>`:'<p class="empty">Открытых технических инцидентов нет.</p>'}</section></div>`;
  } else {
    html=workspace.history.length?`<div class="timeline">${workspace.history.map((item)=>`<article><time>${dateTime(item.occurred_at)}</time><div><b>${escapeHtml(eventLabels[item.type]||item.type)}</b><p>${escapeHtml(item.message)}</p><small>${item.source==="AGENT"?"Agent":item.source==="VISION"?"Vision":item.source==="PHYSICAL"?"Физический обход":"Реестр имущества"}</small></div></article>`).join("")}</div>`:'<p class="empty">История кабинета появится после добавления имущества или первой проверки.</p>';
  }
  const receipt = state.inspectionReceipt;
  if (tab === "inspection" && receipt?.roomId === workspace.room.id) html = `<div class="workflow-receipt" role="status"><strong>Обход сохранён</strong><p>${dateTime(receipt.inspection.completed_at)} · ${escapeHtml(receipt.inspection.inspector_name)} · ${receipt.inspection.items.length} позиций. Расхождения доступны во вкладке «Инциденты».</p></div>` + html;
  $("room-tab-content").innerHTML=html;
  document.querySelectorAll(".open-room-asset").forEach((button)=>button.onclick=()=>{$("room-detail").hidden=true;detail(button.dataset.id);});
  document.querySelectorAll(".room-vision-launch").forEach((button)=>button.onclick=()=>launchRoomVision(workspace.room.id));
  document.querySelectorAll(".room-inspection-launch").forEach((button)=>button.onclick=openRoomInspectionDialog);
  document.querySelectorAll(".physical-incident-action").forEach((button)=>button.onclick=()=>openPhysicalIncidentDialog(button.dataset.id));
  document.querySelectorAll(".physical-incident-act").forEach((button)=>button.onclick=()=>downloadPhysicalIncidentAct(button.dataset.id,button.dataset.number));
}
async function openRoomWorkspace(roomId, scroll = true) {
  const requestView = ++viewGeneration;
  state.roomWorkspace = null;
  $("room-detail").dataset.loadState = "loading";
  $("room-detail-path").textContent = "";
  $("room-detail-state").textContent = "Загрузка…";
  ["room-inspection-action", "room-edit-action", "room-vision-action"].forEach(id => $(id).hidden = true);
  $("room-tabs").querySelectorAll("button").forEach(button => button.disabled = true);
  document.querySelectorAll("main > .page-section").forEach((section) => { section.hidden = section.id !== "room-detail"; });
  setPageHeading("locations");
  $("room-detail").hidden=false; $("room-detail-title").textContent="Загрузка кабинета…"; $("room-detail-error").hidden=true; $("room-tab-content").innerHTML='<div class="skeleton"></div>';
  try {
    const workspace=await readRouteData("room",roomId,`/admin/locations/rooms/${roomId}/workspace`);
    if (requestView !== viewGeneration) return;
    state.roomWorkspace=workspace; state.roomTab="overview";
    $("room-detail").dataset.loadState = "ready";
    $("room-tabs").querySelectorAll("button").forEach(button => button.disabled = false);
    $("room-detail-title").textContent=`Кабинет ${workspace.room.name}`; $("room-detail-path").textContent=[workspace.path.building,workspace.path.floor&&`этаж ${workspace.path.floor}`,workspace.room.purpose].filter(Boolean).join(" · ");
    $("room-edit-action").hidden=state.currentUser?.role!=="ADMIN"; $("room-vision-action").hidden=state.currentUser?.role!=="ADMIN"; $("room-inspection-action").hidden=!canEditRoom(workspace.room.id)||!workspace.inventory.assets.length;
    const attention=workspace.incidents.length||(workspace.physical_incidents||[]).some((item)=>["OPEN","UNDER_REVIEW"].includes(item.status))||workspace.agents.some((item)=>item.status!=="ONLINE")||workspace.vision?.latest_scan?.status==="WARNING"; $("room-detail-state").textContent=attention?"Требует внимания":"В норме"; $("room-detail-state").className=`status-pill ${attention?"warning":"ok"}`;
    renderRoomTab(); if(scroll)window.scrollTo({top:0,behavior:"smooth"});
  } catch(error) {
    if (requestView !== viewGeneration || error.stale) return;
    $("room-detail").dataset.loadState = "error";
    $("room-detail-title").textContent="Не удалось открыть кабинет";
    $("room-detail-error").innerHTML=`<span class="attention-icon">!</span><div><strong>Ошибка загрузки</strong><p>${escapeHtml(error.message)}</p><button type="button" class="button-secondary retry-route">Повторить</button></div>`;
    $("room-detail-error").hidden=false;
    $("room-detail-error").querySelector(".retry-route").onclick=()=>openRoomWorkspace(roomId,false);
    $("room-tab-content").innerHTML='<div class="empty-state"><strong>Данные кабинета не загружены</strong><p>Проверьте подключение и повторите попытку.</p></div>';
    showToast(error.message,true);
  }
}
function openRoomEditDialog() {
  const room=state.roomWorkspace?.room;if(!room)return;
  $("room-edit-purpose").value=room.purpose||"";$("room-edit-responsible").value=room.responsible_name||"";$("room-edit-contact").value=room.responsible_contact||"";$("room-edit-notes").value=room.notes||"";
  openDialog("room-edit-dialog", "room-edit-purpose");
}
function openRoomInspectionDialog() {
  const workspace = state.roomWorkspace;
  if (!workspace || !canEditRoom(workspace.room.id)) return;
  if (!workspace.inventory.assets.length) { showToast("Сначала добавьте имущество в кабинет", true); return; }
  state.inspectionDraft = {roomId: workspace.room.id, assets: workspace.inventory.assets.map(asset => ({...asset})), review: null};
  $("room-inspection-comment").value = "";
  $("inspection-context").textContent = `Кабинет ${workspace.room.name} · ${workspace.path.building || ""} · ${workspace.inventory.assets.length} позиций · ${state.currentUser.username}`;
  $("inspection-error").hidden = true;
  $("room-inspection-items").innerHTML = state.inspectionDraft.assets.map((asset, index) => `<article class="inspection-item" data-asset="${asset.id}" data-quantity="${asset.quantity}">
    <div class="inspection-item-title"><strong>${escapeHtml(asset.name)}</strong><small>${escapeHtml(asset.inventory_number)} · ожидалось ${asset.quantity} ${escapeHtml(asset.unit)}</small></div>
    <label>Результат<select id="inspection-result-${index}" class="inspection-result-input"><option value="">Не проверено</option><option value="PRESENT">На месте</option><option value="MISSING">Отсутствует</option><option value="DAMAGED">Повреждено</option></select></label>
    <label class="inspection-affected" hidden>Проблемных единиц<input id="inspection-quantity-${index}" class="inspection-affected-input" type="number" min="1" max="${asset.quantity}" step="1" value="1" disabled></label>
    <label>Комментарий<input class="inspection-item-comment" maxlength="2000" placeholder="Необязательно"></label><p id="inspection-item-error-${index}" class="form-error inspection-item-error" hidden></p>
  </article>`).join("");
  $("room-inspection-items").onchange = event => {
    const item = event.target.closest(".inspection-item");
    if (!item) return;
    const result = item.querySelector(".inspection-result-input").value;
    const affected = ["MISSING", "DAMAGED"].includes(result);
    item.querySelector(".inspection-affected").hidden = !affected;
    item.querySelector(".inspection-affected-input").disabled = !affected;
    updateInspectionProgress();
  };
  setInspectionStep(false);
  updateInspectionProgress();
  openDialog("room-inspection-dialog", "inspection-result-0");
}
function updateInspectionProgress() {
  const controls = [...$("room-inspection-items").querySelectorAll(".inspection-result-input")];
  const checked = controls.filter(control => control.value).length;
  $("inspection-progress-text").textContent = `Проверено ${checked} из ${controls.length} позиций`;
  $("inspection-progress").max = Math.max(1, controls.length);
  $("inspection-progress").value = checked;
}
function setInspectionStep(review) {
  $("room-inspection-form").dataset.step = review ? "review" : "check";
  $("inspection-check-step").hidden = review;
  $("inspection-review-step").hidden = !review;
  $("inspection-review-back").hidden = !review;
  $("room-inspection-submit").textContent = review ? "Сохранить обход" : "Проверить итог";
}
function reviewRoomInspection() {
  const errors = [], items = [];
  $("room-inspection-items").querySelectorAll(".inspection-item").forEach((row, index) => {
    const result = row.querySelector(".inspection-result-input"), quantity = row.querySelector(".inspection-affected-input");
    [result, quantity].forEach(control => { control.removeAttribute("aria-invalid"); control.removeAttribute("aria-describedby"); });
    const message = !result.value ? "Отметьте результат проверки." : result.value !== "PRESENT" && (!quantity.value || !Number.isInteger(Number(quantity.value)) || Number(quantity.value) < 1 || Number(quantity.value) > Number(row.dataset.quantity)) ? `Укажите целое число от 1 до ${row.dataset.quantity}.` : "";
    const field = !result.value ? result : quantity, error = $("inspection-item-error-" + index);
    error.hidden = !message; error.textContent = message;
    if (message) {
      field.setAttribute("aria-invalid", "true"); field.setAttribute("aria-describedby", error.id);
      errors.push(`<li><a href="#${field.id}">${escapeHtml(state.inspectionDraft.assets[index].name)}: ${escapeHtml(message)}</a></li>`);
    }
    items.push({asset_id: row.dataset.asset, result: result.value, affected_quantity: result.value === "PRESENT" ? 0 : Number(quantity.value), comment: row.querySelector(".inspection-item-comment").value.trim() || null});
  });
  if (errors.length) {
    $("inspection-error").innerHTML = `<strong>Проверьте ${errors.length} позиций перед итогом</strong><ul>${errors.join("")}</ul>`;
    $("inspection-error").querySelectorAll("a").forEach(link => link.onclick = event => { event.preventDefault(); $(link.getAttribute("href").slice(1)).focus(); });
    $("inspection-error").hidden = false; $("inspection-error").focus(); return;
  }
  $("inspection-error").hidden = true;
  state.inspectionDraft.review = {comment: $("room-inspection-comment").value.trim() || null, items};
  const missing = items.filter(item => item.result === "MISSING").length, damaged = items.filter(item => item.result === "DAMAGED").length;
  $("inspection-review-counts").textContent = `Позиций на месте: ${items.length-missing-damaged} · отсутствует: ${missing} · повреждено: ${damaged}`;
  $("inspection-review-items").innerHTML = items.map((item, index) => {
    const asset = state.inspectionDraft.assets[index];
    return `<article><div><strong>${escapeHtml(asset.name)}</strong><small>${escapeHtml(asset.inventory_number)} · ожидалось ${asset.quantity} ${escapeHtml(asset.unit)}</small></div><span class="inspection-result ${item.result.toLowerCase()}">${escapeHtml(inspectionLabels[item.result])}${item.affected_quantity ? ` · ${item.affected_quantity} ${escapeHtml(asset.unit)}` : ""}</span>${item.comment ? `<p>${escapeHtml(item.comment)}</p>` : ""}</article>`;
  }).join("");
  $("inspection-review-comment").textContent = state.inspectionDraft.review.comment || "Общих замечаний нет.";
  setInspectionStep(true); $("inspection-review-step").focus();
}
async function saveRoomInspection(event) {
  event.preventDefault();
  const draft = state.inspectionDraft, button = $("room-inspection-submit");
  if (!draft || button.disabled) return;
  if ($("room-inspection-form").dataset.step !== "review") { reviewRoomInspection(); return; }
  const generation = sessionGeneration;
  button.disabled = true; button.textContent = "Сохраняем…";
  $("room-inspection-form").setAttribute("aria-busy", "true");
  ["room-inspection-cancel", "inspection-review-back"].forEach(id => $(id).disabled = true);
  $("inspection-error").hidden = true;
  try {
    const inspection = await api(`/admin/locations/rooms/${draft.roomId}/inspections`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(draft.review)});
    if (generation !== sessionGeneration) return;
    state.inspectionReceipt = {roomId: draft.roomId, inspection};
    $("room-inspection-dialog").close();
    const refreshed = await load(false);
    if (refreshed && location.hash === `#room=${draft.roomId}`) {
      await openRoomWorkspace(draft.roomId, false);
      if (generation === sessionGeneration && location.hash === `#room=${draft.roomId}` && state.roomWorkspace?.room.id === draft.roomId) {
        state.roomTab = "inspection"; renderRoomTab();
      }
    }
    showToast(refreshed ? "Обход сохранён; результат и инциденты доступны в кабинете" : "Обход сохранён. Повторите загрузку данных, чтобы увидеть результат.");
  } catch (error) {
    if (error.stale) return;
    $("inspection-error").textContent = `Не удалось подтвердить сохранение. ${error.message} Результаты оставлены в форме. При потере связи проверьте историю кабинета перед повторной отправкой.`;
    $("inspection-error").hidden = false; $("inspection-error").focus();
  } finally {
    button.disabled = false;
    button.textContent = $("room-inspection-form").dataset.step === "review" ? "Сохранить обход" : "Проверить итог";
    $("room-inspection-form").setAttribute("aria-busy", "false");
    ["room-inspection-cancel", "inspection-review-back"].forEach(id => $(id).disabled = false);
  }
}
function openPhysicalIncidentDialog(incidentId) {
  const incident=state.roomWorkspace?.physical_incidents?.find((item)=>item.id===incidentId);if(!incident)return;
  state.physicalIncidentId=incidentId;
  $("physical-incident-target").textContent=`${incident.asset_name} · ${incident.inventory_number} · ${inspectionLabels[incident.issue_type]}`;
  $("physical-incident-action-select").value="INVESTIGATE";
  $("physical-incident-comment").value="";
  $("physical-incident-quantity").value=incident.affected_quantity;
  $("physical-incident-document-number").value=`AG-${new Date().toISOString().slice(0,10).replaceAll("-","")}-${incident.id.slice(0,8).toUpperCase()}`;
  $("physical-incident-inventory-number").value="";
  syncPhysicalOperationFields();
  openDialog("physical-incident-dialog", "physical-incident-action-select");
}
function availableRoomOptions(excludedRoomId) {
  return state.locations.flatMap((building)=>building.floors.flatMap((floor)=>floor.rooms.filter((room)=>room.id!==excludedRoomId).map((room)=>({id:room.id,label:`${building.name} · этаж ${floor.name} · каб. ${room.name}`}))));
}
function syncPhysicalOperationFields() {
  const incident=state.roomWorkspace?.physical_incidents?.find((item)=>item.id===state.physicalIncidentId), action=$("physical-incident-action-select").value;
  if(!incident)return;
  const asset=state.roomWorkspace.inventory.assets.find((item)=>item.id===incident.asset_id), operation=["MOVE","WRITE_OFF"].includes(action), moving=action==="MOVE";
  $("physical-operation-fields").hidden=!operation;
  $("physical-destination-field").hidden=!moving;
  $("physical-incident-destination").required=moving;
  $("physical-incident-quantity").required=operation;
  $("physical-incident-document-number").required=operation;
  const max=Math.min(incident.affected_quantity,asset?.quantity||incident.affected_quantity);
  $("physical-incident-quantity").max=max; if(Number($("physical-incident-quantity").value)>max)$("physical-incident-quantity").value=max;
  if(moving){const previous=$("physical-incident-destination").value,rooms=availableRoomOptions(incident.room_id);$("physical-incident-destination").innerHTML='<option value="">Выберите кабинет</option>'+rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join("");if(rooms.some((room)=>room.id===previous))$("physical-incident-destination").value=previous;}
  const partial=moving&&asset?.tracking_mode==="GROUPED"&&Number($("physical-incident-quantity").value)<Number(asset.quantity);
  $("physical-inventory-field").hidden=!partial;$("physical-incident-inventory-number").required=partial;
  $("physical-incident-operation-note").textContent=operation?(moving?"После подтверждения карточка будет перемещена в выбранный кабинет. Для части групповой позиции система создаст отдельную карточку.":"После подтверждения остаток уменьшится, а полностью списанная карточка покинет активный кабинет. PDF-акт будет доступен сразу."):"Решение и исполнитель сохранятся в неизменяемой истории.";
}
async function downloadPhysicalIncidentAct(incidentId,documentNumber) {
  try{const blob=await apiBlob(`/admin/locations/physical-incidents/${incidentId}/act.pdf`),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=`assetguard-act-${documentNumber||incidentId}.pdf`;link.click();URL.revokeObjectURL(url);}catch(error){showToast(error.message,true);}
}
function syncVisionAssetsForRoom(roomId) {
  const select=$("vision-asset-id"),previous=select.value,assets=state.assets.filter((asset)=>!roomId||asset.room_id===roomId);
  select.innerHTML='<option value="">Без связи с имуществом</option>'+assets.map((asset)=>`<option value="${asset.id}">${escapeHtml(asset.name)} · ${escapeHtml(asset.inventory_number)}</option>`).join("");
  if(assets.some((asset)=>asset.id===previous))select.value=previous;
}
function launchRoomVision(roomId) {
  if(!roomId||state.currentUser?.role!=="ADMIN")return;
  $("vision-location-room").value=roomId;syncVisionAssetsForRoom(roomId);location.hash="vision";$("vision").scrollIntoView({behavior:"smooth",block:"start"});$("vision-file").focus({preventScroll:true});
}
function renderLocations(locations) {
  state.locations=locations;
  const canManage=state.currentUser?.role==="ADMIN";
  $("location-tree").innerHTML=locations.length ? locations.map((building)=>`<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(building.name)}</strong><small>${escapeHtml(locationContact(building)||"Ответственный не назначен")}</small>${building.floors.length ? building.floors.map((floor)=>`<div class="location-floor"><b>Этаж ${escapeHtml(floor.name)}</b> ${canManage?`<button class="button-link add-room" data-floor="${floor.id}">+ кабинет</button>`:""}${floor.rooms.length ? floor.rooms.map((room)=>`<div class="location-room"><span>каб. ${escapeHtml(room.name)}${room.purpose?` · ${escapeHtml(room.purpose)}`:""}</span><small>${room.asset_count} позиций · ${escapeHtml(locationContact(room)||"ответственный не назначен")}</small><button class="button-link room-report" data-room="${room.id}">Открыть кабинет</button></div>`).join("") : '<p class="empty">Кабинетов пока нет.</p>'}</div>`).join("") : '<p class="empty">Этажей пока нет.</p>'}${canManage?`<button class="button-link add-floor" data-building="${building.id}">+ этаж</button>`:""}</div></div>`).join("") : '<p class="empty">Структура пока не создана. Добавьте корпус справа, затем создайте для него этажи и кабинеты.</p>';
  document.querySelectorAll(".add-floor").forEach((button)=>button.onclick=()=>openLocationDialog("floor",button.dataset.building));
  document.querySelectorAll(".add-room").forEach((button)=>button.onclick=()=>openLocationDialog("room",button.dataset.floor));
  document.querySelectorAll(".room-report").forEach((button)=>button.onclick=()=>navigateToRoom(button.dataset.room));
}
let locationDialogTarget=null;
function openLocationDialog(kind,parentId) {
  locationDialogTarget={kind,parentId};
  const isRoom=kind==="room";
  $("location-create-eyebrow").textContent=isRoom?"Шаг 3 · кабинет":"Шаг 2 · этаж";
  $("location-create-title").textContent=isRoom?"Добавить кабинет":"Добавить этаж";
  $("location-create-help").textContent=isRoom?"Укажите номер кабинета. Ответственного можно назначить сразу или позже.":"Укажите номер или название этажа в выбранном корпусе.";
  $("location-create-name").placeholder=isRoom?"Например, 205":"Например, 2";
  $("location-responsible-field").hidden=!isRoom;
  $("location-contact-field").hidden=!isRoom;
  $("location-create-submit").textContent=isRoom?"Добавить кабинет":"Добавить этаж";
  $("location-create-form").reset(); openDialog("location-create-dialog", "location-create-name");
}
function locationScopes() {
  const scopes=[];
  state.locations.forEach((building)=>{scopes.push({type:"BUILDING",id:building.id,organization_id:building.organization_id,label:`Корпус · ${building.name}`});building.floors.forEach((floor)=>{scopes.push({type:"FLOOR",id:floor.id,organization_id:building.organization_id,label:`${building.name} · этаж ${floor.name}`});floor.rooms.forEach((room)=>scopes.push({type:"ROOM",id:room.id,organization_id:building.organization_id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`}));});});
  return scopes;
}
function userRoleLabel(role) { return ({ADMIN:"Администратор школы",LOCATION_MANAGER:"Менеджер локации",INVENTORY_CLERK:"Ответственный за инвентаризацию",VIEWER:"Наблюдатель"})[role]||role; }
function renderAdminAccessVisibility() {
  const signedIn=Boolean(state.currentUser), isAdmin=state.currentUser?.role==="ADMIN";
  $("location-access-nav").hidden=!signedIn; $("location-access").hidden=!signedIn;
  $("agent-operations-action").hidden=!isAdmin;
  $("agent-credentials-nav").hidden=!isAdmin; $("agent-credentials").hidden=!isAdmin;
  $("access-admin-content").hidden=!isAdmin; $("access-role-notice").hidden=!signedIn||isAdmin;
  if(signedIn&&!isAdmin)$("access-role-notice").textContent=`Вы вошли как «${userRoleLabel(state.currentUser.role)}». Создавать учётные записи и назначать доступы может администратор школы.`;
}
function renderAgentCredentials() {
  if(state.currentUser?.role!=="ADMIN") return;
  const select=$("agent-organization"), field=$("agent-organization-field"), tenantOrganizationId=state.currentUser.organization_id;
  field.hidden=Boolean(tenantOrganizationId);
  select.innerHTML=state.organizations.map((item)=>`<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")||'<option value="">Школа ещё не создана</option>';
  if(tenantOrganizationId) select.value=tenantOrganizationId;
  const rows=state.agentCredentials.map((item)=>{
    const bound=Boolean(item.endpoint_id), revoked=item.status==="REVOKED";
    const connection=revoked?"Отозван":bound?"Подключён к компьютеру":"Ожидает установку";
    const status=revoked?"REVOKED":"ACTIVE";
    const endpoint=state.endpoints.find((endpoint)=>endpoint.id===item.endpoint_id);
    return `<div class="credential-row"><div><strong>${escapeHtml(item.username)}</strong><small>${connection}${endpoint?` · ${escapeHtml(endpoint.hostname)}`:""} · создан ${escapeHtml(dateTime(item.issued_at))}${item.revoked_at?` · отозван ${escapeHtml(dateTime(item.revoked_at))}`:""}</small></div>${pill(status)}${!revoked?`<button type="button" class="button-secondary revoke-agent-credential" data-id="${item.id}">Отозвать ключ</button>`:""}</div>`;
  }).join("");
  $("agent-credentials-list").innerHTML=rows||'<p class="empty">Ключей пока нет. Создайте первый перед установкой Agent.</p>';
  // A bootstrap administrator may legitimately create a platform-scoped key before
  // the first school is configured; tenant administrators are scoped automatically.
  $("create-agent-credential").querySelector("button[type=submit]").disabled=$("create-agent-credential").dataset.busy==="true";
  document.querySelectorAll(".revoke-agent-credential").forEach((button)=>button.onclick=()=>openConfirmation({title:"Отозвать ключ Agent?",description:`Ключ ${state.agentCredentials.find((item)=>item.id===button.dataset.id)?.username}. Компьютер больше не сможет отправлять инвентаризацию с этим ключом. Для возобновления работы понадобится новый ключ.`,confirmLabel:"Отозвать ключ",onConfirm:async()=>{await api(`/admin/agent-credentials/${button.dataset.id}/revoke`,{method:"POST"});showToast("Ключ Agent отозван");await loadAdminAccess();}}));
}
function renderAgentReenrolments() {
  if(state.currentUser?.role!=="ADMIN") return;
  const rows=(state.agentReenrolments||[]).map((item)=>{
    const pending=item.status==="PENDING"&&new Date(item.expires_at)>new Date(), matched=Boolean(item.endpoint_id);
    const target=matched?`${item.endpoint_hostname||item.computer_name} · ${item.identifier_value}`:`${item.computer_name} · совпадение не найдено`;
    const actions=pending?`<div class="actions">${matched?`<button type="button" class="approve-agent-reenrolment" data-id="${item.id}">Подтвердить</button>`:""}<button type="button" class="button-secondary reject-agent-reenrolment" data-id="${item.id}">Отклонить</button></div>`:"";
    return `<div class="credential-row"><div><strong>${escapeHtml(target)}</strong><small>Installer ${escapeHtml(item.installer_version)} · ${escapeHtml(dateTime(item.requested_at))} · срок до ${escapeHtml(dateTime(item.expires_at))}${item.decided_by?` · решил ${escapeHtml(item.decided_by)}`:""}</small></div>${pill(item.status==="PENDING"&&!pending?"EXPIRED":item.status)}${actions}</div>`;
  }).join("");
  $("agent-reenrolments-list").innerHTML=rows||'<p class="empty">Запросов на восстановление пока нет.</p>';
  document.querySelectorAll(".approve-agent-reenrolment").forEach((button)=>button.onclick=()=>openConfirmation({title:"Восстановить Agent?",description:`${state.agentReenrolments.find((item)=>item.id===button.dataset.id)?.endpoint_hostname || "Компьютер"} · ${state.agentReenrolments.find((item)=>item.id===button.dataset.id)?.identifier_value}. Сверьте имя и UUID. Прежний ключ будет сразу отозван.`,confirmLabel:"Отозвать старый ключ и восстановить",onConfirm:async()=>{await api(`/admin/agent-re-enrolments/${button.dataset.id}/approve`,{method:"POST"});showToast("Agent подтверждён и получил новый ключ");await loadAdminAccess();}}));
  document.querySelectorAll(".reject-agent-reenrolment").forEach((button)=>button.onclick=()=>openConfirmation({title:"Отклонить запрос?",description:`Запрос компьютера ${state.agentReenrolments.find((item)=>item.id===button.dataset.id)?.computer_name} будет отклонён. Установка завершится ошибкой. Действующие ключи не изменятся.`,confirmLabel:"Отклонить",onConfirm:async()=>{await api(`/admin/agent-re-enrolments/${button.dataset.id}/reject`,{method:"POST"});showToast("Запрос отклонён");await loadAdminAccess();}}));
}
function syncRoleControls() {
  const user=state.currentUser, isAdmin=user?.role==="ADMIN", editableRooms=new Set(user?.editable_room_ids||[]), canEditAssets=isAdmin||editableRooms.size>0;
  $("room-edit-action").hidden=!isAdmin||!state.roomWorkspace;$("room-vision-action").hidden=!isAdmin||!state.roomWorkspace;$("room-inspection-action").hidden=!state.roomWorkspace||!canEditRoom(state.roomWorkspace.room.id)||!state.roomWorkspace.inventory.assets.length;
  $("show-create").hidden=!canEditAssets;
  if(!canEditAssets)$("create-asset").hidden=true;
  ["export-assets","export-assets-pdf","import-assets","import-assets-pdf","create-building","vision-upload","vision-baseline"].forEach((id)=>$(id).hidden=!isAdmin);
  $("import-assets-file").hidden=true;
  $("import-assets-pdf-file").hidden=true;
  $("data-exchange-nav").hidden=!isAdmin;
  $("data-exchange-shortcut").hidden=!isAdmin;
  const assetOrganizationId=user?.organization_id||state.organizations[0]?.id;
  const rooms=state.locations.filter((building)=>!assetOrganizationId||building.organization_id===assetOrganizationId).flatMap((building)=>building.floors.flatMap((floor)=>floor.rooms.map((room)=>({id:room.id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`})))).filter((room)=>isAdmin||editableRooms.has(room.id));
  const roomSelect=$("create-asset-room");
  roomSelect.innerHTML=`<option value="" ${isAdmin?"":"disabled selected"}>${rooms.length?"Выберите кабинет из структуры школы":isAdmin?"Кабинеты ещё не созданы":"Вам пока не назначен кабинет"}</option>`+rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join("");
  roomSelect.required=!isAdmin;
  roomSelect.disabled=!rooms.length;
  $("asset-tracking-mode").dispatchEvent(new Event("change"));
  setAuthenticatedUi();
}
function canEditAsset(asset) { return state.currentUser?.role==="ADMIN"||Boolean(asset?.room_id&&state.currentUser?.editable_room_ids?.includes(asset.room_id)); }
function renderAdminAccess() {
  const allScopes=locationScopes(), scopeLabels=new Map(allScopes.map((item)=>[`${item.type}:${item.id}`,item.label]));
  const selectedOrganization=$("user-organization").value, selectedScope=$("access-scope").value;
  $("users-list").innerHTML=state.users.map((user)=>`<div class="access-row"><div><strong>${escapeHtml(user.username)}</strong><small>${escapeHtml(userRoleLabel(user.role))}</small></div><span class="status-pill ${user.active?"ok":"neutral"}">${user.active?"Активен":"Вход отключён"}</span></div>`).join("")||'<p class="empty">Сотрудников пока нет.</p>';
  $("user-organization").innerHTML=state.organizations.map((item)=>`<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")||'<option value="">Сначала создайте организацию</option>';
  if(state.organizations.some((item)=>item.id===selectedOrganization))$("user-organization").value=selectedOrganization;
  const currentUserId=$("access-user").value;
  $("access-user").innerHTML=state.users.filter((item)=>item.role!=="ADMIN"&&item.active).map((item)=>`<option value="${item.id}">${escapeHtml(item.username)} · ${escapeHtml(userRoleLabel(item.role))}</option>`).join("")||'<option value="">Создайте пользователя</option>';
  if(state.users.some((item)=>item.id===currentUserId&&item.active&&item.role!=="ADMIN"))$("access-user").value=currentUserId;
  const grantUser=state.users.find((item)=>item.id===$("access-user").value), allowedScopes=allScopes.filter((item)=>!grantUser?.organization_id||item.organization_id===grantUser.organization_id);
  $("access-scope").innerHTML=allowedScopes.map((item)=>`<option value="${item.type}:${item.id}">${escapeHtml(item.label)}</option>`).join("")||'<option value="">Для сотрудника пока нет доступных локаций</option>';
  if(allowedScopes.some((item)=>`${item.type}:${item.id}`===selectedScope))$("access-scope").value=selectedScope;
  const accessRows=state.locationAccess.map((item)=>`<div class="access-row"><div><strong>${escapeHtml(item.username)}</strong><small>${escapeHtml(userRoleLabel(state.users.find((user)=>user.id===item.user_id)?.role||"Сотрудник"))} · ${escapeHtml(scopeLabels.get(`${item.scope_type}:${item.scope_id}`)||"Локация удалена")}</small></div><span class="status-pill ${item.permission==="EDITOR"?"warning":"neutral"}">${item.permission==="EDITOR"?"Редактирование":"Только просмотр"}</span><button type="button" class="button-secondary revoke-location-access" data-id="${item.id}">Отозвать</button></div>`).join("");
  const withoutAccess=state.users.filter((user)=>user.role!=="ADMIN"&&!state.locationAccess.some((item)=>item.user_id===user.id));
  $("location-access-list").innerHTML=accessRows+(withoutAccess.length?`<p class="access-unassigned"><strong>Пока нет назначения:</strong> ${withoutAccess.map((user)=>escapeHtml(user.username)).join(", ")} — эти пользователи не видят реестр.</p>`:"")||'<p class="empty">Назначений пока нет. Сотрудники без назначения не имеют доступа к локациям.</p>';
  document.querySelectorAll(".revoke-location-access").forEach((button)=>button.onclick=()=>openConfirmation({title:"Отозвать доступ?",description:`${state.locationAccess.find((item)=>item.id===button.dataset.id)?.username} · ${scopeLabels.get(`${state.locationAccess.find((item)=>item.id===button.dataset.id)?.scope_type}:${state.locationAccess.find((item)=>item.id===button.dataset.id)?.scope_id}`)}. Доступ к этой области будет отозван; другие назначения сохранятся.`,confirmLabel:"Отозвать доступ",onConfirm:async()=>{await api(`/admin/locations/access/${button.dataset.id}`,{method:"DELETE"});showToast("Доступ отозван");await loadAdminAccess();}}));
  const grantButton=$("grant-location-access").querySelector("button[type=submit]"), createButton=$("create-user").querySelector("button[type=submit]");
  if(grantButton)grantButton.disabled=!state.users.some((user)=>user.role!=="ADMIN"&&user.active)||!allowedScopes.length||$("grant-location-access").dataset.busy==="true";
  if(createButton)createButton.disabled=!state.organizations.length||$("create-user").dataset.busy==="true";
  $("user-organization-hint").hidden=Boolean(state.organizations.length);
}
async function loadAdminAccess() {
  renderAdminAccessVisibility();
  if(state.currentUser?.role!=="ADMIN")return false;
  const request=++adminAccessGeneration, generation=sessionGeneration;
  $("access-load-error").hidden=true; $("agent-load-error").hidden=true;
  try {
    const [users,locationAccess,organizations,agentCredentials,agentReenrolments]=await Promise.all([
      api("/admin/users"),api("/admin/locations/access"),api("/admin/locations/organizations"),api("/admin/agent-credentials"),api("/admin/agent-re-enrolments"),
    ]);
    if(request!==adminAccessGeneration||generation!==sessionGeneration)return false;
    state={...state,users,locationAccess,organizations,agentCredentials,agentReenrolments};
    renderAdminAccess();renderAgentCredentials();renderAgentReenrolments();renderAgentFleet();syncRoleControls();
    return true;
  } catch(error) {
    if(error.stale||request!==adminAccessGeneration||generation!==sessionGeneration)return false;
    $("agent-load-error").hidden=false;$("agent-load-error").textContent=`Не удалось обновить ключи и запросы: ${error.message}. Нажмите «Обновить».`;
    $("access-load-error").hidden=false;$("access-load-error").textContent=`Не удалось обновить сотрудников и назначения: ${error.message}. Нажмите «Обновить».`;
    return false;
  }
}
function hardwareBrief(endpoint) {
  const summary = endpoint?.hardware_summary; if (!summary) return "Нет данных";
  return [summary.ram_bytes ? `${bytes(summary.ram_bytes)} RAM` : null, summary.storage_devices ? `${summary.storage_devices} накоп.` : null, summary.cpu].filter(Boolean).join(" · ") || "Состав не определён";
}

function agentConnection(endpoint) {
  if(["IDENTITY_CONFLICT","OFFLINE"].includes(endpoint.status))return endpoint.status;
  const hours=state.operations?.agents?.stale_after_hours;
  if(hours && endpoint.last_seen_at && Date.now()-new Date(endpoint.last_seen_at).getTime()>hours*3600000)return "STALE";
  return endpoint.status;
}
const agentConnectionLabels={ONLINE:"На связи",STALE:"Давно нет данных",OFFLINE:"Не в сети",IDENTITY_CONFLICT:"Конфликт идентификации",REQUIRES_VERIFICATION:"Требует проверки"};
function renderAgentFleet() {
  if(state.currentUser?.role!=="ADMIN")return;
  const hours=state.operations?.agents?.stale_after_hours;
  $("agent-freshness-help").textContent=hours?`Данные устаревают через ${hours} ч. без отчёта. Это не подтверждает пропажу компьютера. Привязка ключа не означает, что Agent сейчас на связи.`:"Порог устаревания недоступен: обновите данные.";
  const query=$("agent-search").value.trim().toLocaleLowerCase("ru"), status=$("agent-status-filter").value;
  const endpoints=state.endpoints.filter((item)=>(!status||agentConnection(item)===status)&&[item.hostname,item.asset?.name,item.asset?.inventory_number].filter(Boolean).join(" ").toLocaleLowerCase("ru").includes(query));
  const pages=Math.max(1,Math.ceil(endpoints.length/20));state.agentPage=Math.min(state.agentPage,pages);
  $("agent-fleet-summary").textContent=`Найдено ${endpoints.length} из ${state.endpoints.length} · страница ${state.agentPage} из ${pages}`;
  $("agent-fleet-list").innerHTML=endpoints.slice((state.agentPage-1)*20,state.agentPage*20).map((item)=>{
    const status=agentConnection(item), label=agentConnectionLabels[status]||status;
    const reason=status==="STALE"?"Нет свежей инвентаризации: проверьте компьютер, сеть и службу Agent.":status==="IDENTITY_CONFLICT"?"Сверьте аппаратные идентификаторы; не восстанавливайте ключ до проверки.":status==="OFFLINE"?"Компьютер отмечен как недоступный.":status==="REQUIRES_VERIFICATION"?"Нужна проверка идентификации компьютера.":"Свежий отчёт получен.";
    return `<div class="admin-record"><div><strong>${escapeHtml(item.hostname||"Без имени")}</strong><small>Последняя связь: ${escapeHtml(dateTime(item.last_seen_at))} · ${escapeHtml(relativeTime(item.last_seen_at))}</small><small>${escapeHtml(reason)}</small><small>${escapeHtml(hardwareBrief(item))}</small></div><span class="status-pill ${status==="ONLINE"?"ok":status==="IDENTITY_CONFLICT"?"danger":"warning"}">${escapeHtml(label)}</span>${item.asset_id?`<a class="button-anchor button-secondary" href="#asset=${item.asset_id}">Карточка имущества</a>`:'<span class="meta">Не связан с имуществом</span>'}</div>`;
  }).join("")||'<p class="empty">Компьютеры с такими условиями не найдены.</p>';
  $("agent-fleet-pagination").innerHTML=pages>1?`<button type="button" id="agent-page-prev" class="button-secondary" ${state.agentPage===1?"disabled":""}>Назад</button><span>${state.agentPage} / ${pages}</span><button type="button" id="agent-page-next" class="button-secondary" ${state.agentPage===pages?"disabled":""}>Далее</button>`:"";
  if($("agent-page-prev"))$("agent-page-prev").onclick=()=>{state.agentPage--;renderAgentFleet();};
  if($("agent-page-next"))$("agent-page-next").onclick=()=>{state.agentPage++;renderAgentFleet();};
}
const deliveryLabels={PENDING:"Ожидает отправки",RETRYING:"Повтор",SENT:"Принято Telegram"};
function renderNotifications(data) {
  $("notification-summary").textContent=`Ожидают: ${data.summary.pending} · повтор: ${data.summary.retrying} · принято Telegram: ${data.summary.sent}`;
  $("notification-list").innerHTML=data.items.map((item)=>`<div class="admin-record"><div><strong>${escapeHtml(dateTime(item.created_at))}</strong><small>Попыток: ${item.attempts}${item.sent_at?` · принято ${escapeHtml(dateTime(item.sent_at))}`:` · следующая попытка ${escapeHtml(dateTime(item.next_attempt_at))}`}</small>${item.last_error_code?`<small>Причина: ${escapeHtml(item.last_error_code)}</small>`:""}</div><span class="status-pill ${item.status==="SENT"?"ok":item.status==="RETRYING"?"warning":"neutral"}">${deliveryLabels[item.status]}</span>${item.route?`<a href="${escapeHtml(item.route)}" class="button-anchor button-secondary">Открыть источник</a>`:'<span class="meta">Служебное событие</span>'}</div>`).join("")||'<p class="empty">Уведомлений с таким состоянием пока нет. Новые события появятся после создания инцидента имущества.</p>';
  $("notification-pagination").innerHTML=data.total?`<button id="notification-prev" type="button" class="button-secondary" ${data.offset===0?"disabled":""}>Назад</button><span>${Math.min(data.offset+1,data.total)}–${Math.min(data.offset+data.limit,data.total)} из ${data.total}</span><button id="notification-next" type="button" class="button-secondary" ${data.offset+data.limit>=data.total?"disabled":""}>Далее</button>`:"";
  if($("notification-prev"))$("notification-prev").onclick=()=>{notificationOffset=Math.max(0,notificationOffset-20);loadNotifications();};
  if($("notification-next"))$("notification-next").onclick=()=>{notificationOffset+=20;loadNotifications();};
}
async function loadNotifications() {
  if(state.currentUser?.role!=="ADMIN")return;
  const request=++notificationGeneration, generation=sessionGeneration, status=$("notification-status-filter").value;
  $("notification-load-error").hidden=true;$("notification-list").innerHTML='<p class="empty">Загрузка доставки…</p>';$("notification-pagination").replaceChildren();
  $("refresh-notifications").disabled=true;
  try {
    const data=await api(`/admin/notifications?limit=20&offset=${notificationOffset}${status?`&status=${status}`:""}`);
    if(request!==notificationGeneration||generation!==sessionGeneration)return;
    renderNotifications(data);
  } catch(error) {
    if(request!==notificationGeneration||generation!==sessionGeneration||error.stale)return;
    $("notification-list").replaceChildren();$("notification-summary").textContent="Данные доставки недоступны";
    $("notification-load-error").textContent=`${error.message}. Нажмите «Обновить доставку».`;$("notification-load-error").hidden=false;
  } finally { if(request===notificationGeneration)$("refresh-notifications").disabled=false; }
}
document.querySelectorAll("[data-admin-panel]").forEach((button)=>button.onclick=()=>{
  const panel=$(button.dataset.adminPanel);panel.tabIndex=-1;panel.scrollIntoView({block:"start",behavior:"instant"});panel.focus({preventScroll:true});
});
$("agent-search").addEventListener("input",()=>{state.agentPage=1;renderAgentFleet();});
$("agent-status-filter").addEventListener("change",()=>{state.agentPage=1;renderAgentFleet();});
$("refresh-agent-fleet").onclick=async()=>{if(await load(false)){renderAgentFleet();await openRouteFromHash();}};
$("notification-status-filter").addEventListener("change",()=>{notificationOffset=0;loadNotifications();});
$("refresh-notifications").onclick=()=>loadNotifications();
function filteredDevices() {
  const query = $("device-search").value.trim().toLocaleLowerCase("ru"); const status = $("device-status-filter").value; const category = $("device-category-filter").value; const room = $("device-room-filter").value; const changed = $("device-change-filter").checked;
  const result = state.devices.filter((item) => {
    const view = state.registryView;
    if (view === "assets" && item.kind !== "asset") return false;
    if (view === "computers" && !item.endpointId && !["Desktop","Laptop"].includes(item.assetType)) return false;
    if (view === "unlinked" && item.kind !== "endpoint") return false;
    const haystack = [item.name,item.inventoryNumber,item.hostname,item.building,item.floor,item.room,item.organization].filter(Boolean).join(" ").toLocaleLowerCase("ru");
    const matchesStatus = !status || item.status === status || (status === "ATTENTION" && item.status === "ANOMALY");
    return (!query || haystack.includes(query)) && matchesStatus && (!category || item.category === category) && (!room || item.roomId === room) && (!changed || (item.endpoint?.open_changes || 0) > 0);
  });
  const sort = $("device-sort").value;
  return result.sort((a,b) => sort === "name" ? a.name.localeCompare(b.name,"ru") : sort === "attention" ? (["ANOMALY","ATTENTION","UNCHECKED","OK","MANUAL","WRITTEN_OFF"].indexOf(a.status) - ["ANOMALY","ATTENTION","UNCHECKED","OK","MANUAL","WRITTEN_OFF"].indexOf(b.status)) : (new Date(b.endpoint?.last_seen_at || 0) - new Date(a.endpoint?.last_seen_at || 0)));
}
function renderDevices() {
  const rooms = availableRoomOptions(), selectedRoom = $("device-room-filter").value;
  $("device-room-filter").innerHTML = '<option value="">Все кабинеты</option>' + rooms.map(room => `<option value="${room.id}">${escapeHtml(room.label)}</option>`).join("");
  $("device-room-filter").value = rooms.some(room => room.id === selectedRoom) ? selectedRoom : "";
  const devices = filteredDevices();
  const counts = {all:state.devices.length, assets:state.assets.length, computers:state.devices.filter(item => item.endpointId || ["Desktop","Laptop"].includes(item.assetType)).length, unlinked:state.devices.filter(item => item.kind === "endpoint").length};
  Object.entries(counts).forEach(([view,count]) => { $(view === "all" ? "registry-all-count" : `registry-${view}-count`).textContent = count; });
  document.querySelectorAll("[data-registry-view]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.registryView === state.registryView)));
  state.devicePage = Math.min(state.devicePage, Math.max(1, Math.ceil(devices.length / listPageSize)));
  const pageDevices = devices.slice((state.devicePage-1)*listPageSize, state.devicePage*listPageSize);
  renderListPagination("device-pagination", state.devicePage, devices.length, page => {state.devicePage = page; renderDevices();});
  const activeFilters = renderSelectedFilters("device-selected-filters", [["device-search"], ["device-status-filter"], ["device-category-filter"], ["device-room-filter"], ["device-change-filter"], ["device-sort", "recent"]], clearDeviceFilters);
  $("device-active-filter-count").hidden = !activeFilters; $("device-active-filter-count").textContent = activeFilters || "";
  const empty = state.devices.length ? `<div class="empty-state"><strong>Ничего не найдено</strong><p>Измените запрос или сбросьте фильтры.</p><button id="empty-reset" class="button-secondary" type="button">Сбросить фильтры</button></div>` : `<div class="empty-state"><strong>Здесь будет ваше имущество</strong><p>${state.currentUser?.role === "ADMIN" ? "Добавьте первую запись или загрузите ведомость." : "Попросите администратора проверить назначение кабинетов."}</p>${state.currentUser?.role === "ADMIN" ? '<button id="empty-add" type="button">Добавить имущество</button> <a class="button-anchor button-secondary" href="#data-exchange">Импорт</a>' : ''}</div>`;
  $("assets").innerHTML = devices.length ? pageDevices.map(item => {
    const lastCheck = item.endpoint ? relativeTime(item.endpoint.last_seen_at) : "По обходу";
    const type = item.kind === "endpoint" ? "Обнаружен Agent" : `${assetTypeLabels[item.assetType] || item.assetType || categoryLabels[item.category] || "Имущество"}${item.trackingMode === "GROUPED" ? ` · ${item.quantity} ${item.unit || "шт."}` : ""}`;
    const relation = item.kind === "endpoint" && state.currentUser?.role === "ADMIN" ? `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать с имуществом</button>` : item.kind === "endpoint" ? '<span class="relation-label">Не связан</span>' : item.endpoint ? '<span class="relation-label linked">Связан с Agent</span>' : item.category === "IT" ? '<span class="relation-label">Без Agent</span>' : '<span class="relation-label" title="Компьютер для этого имущества не требуется">Не требуется</span>';
    return `<tr class="device-row" data-asset-id="${item.assetId || ""}"><td data-label="Название"><div class="device-name">${item.assetId ? `<a class="device-open-link open-device" href="#asset=${item.assetId}" data-id="${item.assetId}">${escapeHtml(item.name)}</a>` : `<a class="device-open-link open-computer" href="#computer=${item.endpointId}" data-id="${item.endpointId}">${escapeHtml(item.name)}</a>`}<small>${escapeHtml(type)}</small></div></td><td data-label="Инв. номер"><span class="inventory-number" title="${escapeHtml(item.inventoryNumber || "Нет учётной записи")}">${escapeHtml(item.inventoryNumber || "—")}</span></td><td data-label="Кабинет"><span title="${escapeHtml(locationLabel(item) || "Размещение не указано")}">${item.room ? `Каб. ${escapeHtml(item.room)}` : "Не назначен"}</span></td><td data-label="Состояние">${pill(item.status)}</td><td data-label="Проверка"><span title="${escapeHtml(item.endpoint ? dateTime(item.endpoint.last_seen_at) : "Проверяется физическим обходом")}">${escapeHtml(lastCheck)}</span></td><td data-label="Связь с компьютером">${relation}</td></tr>`;
  }).join("") : `<tr><td colspan="6">${empty}</td></tr>`;
  $("registry-count").textContent = `${devices.length} записей${activeFilters || state.registryView !== "all" ? " по выбранным условиям" : " в реестре"}`;
  $("device-result-count").textContent = `Показано ${devices.length ? (state.devicePage-1)*listPageSize+1 : 0}–${Math.min(state.devicePage*listPageSize,devices.length)} из ${devices.length}`;
  bindDynamicActions();
  $("empty-add")?.addEventListener("click", openAssetCreateForm);
  $("empty-reset")?.addEventListener("click", () => {state.registryView="all";clearDeviceFilters();});
}
function clearDeviceFilters() { state.devicePage=1; $("device-sort").value="recent"; $("device-search").value=""; $("device-status-filter").value=""; $("device-category-filter").value=""; $("device-room-filter").value=""; $("device-change-filter").checked=false; renderDevices(); }
function openAssetCreateForm() {
  $("create-asset").hidden = false;
  clearFormError($("create-asset"));
  openDialog("asset-create-dialog", $("create-asset").querySelector('[name="inventory_number"]'));
}
function bindDynamicActions() {
  document.querySelectorAll(".open-computer").forEach(link => link.onclick = event => { if(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return;event.preventDefault();navigateToComputer(link.dataset.id); });
  document.querySelectorAll(".open-device").forEach((button) => button.onclick = (event) => { if(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)return; event.preventDefault(); event.stopPropagation(); navigateToAsset(button.dataset.id); });
  document.querySelectorAll(".open-incident").forEach((button) => button.onclick = (event) => { event.stopPropagation(); navigateToIncident(button.dataset.id); });
  document.querySelectorAll(".link-endpoint").forEach((button) => button.onclick = (event) => { event.stopPropagation(); openLink(button.dataset.id, button.dataset.name); });
}
function factRows(items, emptyMessage = "В последнем отчёте этих сведений нет.") {
  const rows = items.filter(([,value]) => value !== null && value !== undefined && value !== "");
  return rows.length ? rows.map(([label,value]) => {
    const copy = typeof value === 'string' && value.length >= 24 && /серийн|uuid|идентификатор|\bID\b/i.test(label);
    return `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}${copy ? `<button type="button" class="button-link copy-value" data-value="${escapeHtml(value)}" aria-label="Копировать: ${escapeHtml(label)}">Копировать</button>` : ''}</dd>`;
  }).join('') : `<p class="empty">${escapeHtml(emptyMessage)}</p>`;
}
function rawValue(raw, keys) { for (const key of keys) if (raw?.[key] !== undefined && raw[key] !== "") return raw[key]; return null; }
function componentPrimary(item) { const raw = item.raw_data || {}; return item.model || rawValue(raw,["name","description","caption","chipset"]) || "Модель не определена"; }
function componentMeta(item) {
  const raw = item.raw_data || {}; const values = [];
  if (item.type === "RAM") values.push(item.capacity ? bytes(item.capacity) : null, raw.speed ? `${raw.speed} МГц` : null, item.slot, item.manufacturer, item.part_number ? `P/N ${item.part_number}` : null, item.serial ? `S/N ${item.serial}` : null, raw.type);
  else if (item.type === "STORAGE") values.push(raw.disksize != null ? storageSize(raw.disksize) : null, raw.type, raw.interface, raw.firmware ? `FW ${raw.firmware}` : null, item.serial ? `S/N ${item.serial}` : null);
  else if (item.type === "CPU") values.push(raw.core ? `${raw.core} ядер` : null, raw.thread ? `${raw.thread} потоков` : null, raw.speed ? `${raw.speed} МГц` : null, raw.manufacturer, raw.id);
  else if (item.type === "GPU") values.push(Number(raw.memory) > 0 ? `${bytes(memoryCapacityBytes(raw.memory))} памяти` : null, raw.resolution, raw.chipset, raw.pcislot);
  else if (item.type === "NETWORK") values.push(raw.macaddr || raw.mac, raw.ipaddress || raw.ip, raw.status, raw.speed, raw.type);
  else if (item.type === "DRIVE") values.push(raw.letter || raw.label, raw.filesystem, raw.total != null ? `Всего ${storageSize(raw.total)}` : null, raw.free != null ? `Свободно ${storageSize(raw.free)}` : null, raw.systemdrive ? "Системный" : null);
  else if (item.type === "CONTROLLER") values.push(raw.manufacturer, raw.type, raw.pcislot, raw.vendorid && raw.productid ? `${raw.vendorid}:${raw.productid}` : null);
  else if (item.type === "MOTHERBOARD") values.push(item.manufacturer, item.part_number, item.serial ? `S/N ${item.serial}` : null);
  else values.push(item.manufacturer, item.serial ? `S/N ${item.serial}` : null, item.slot);
  return values.filter(Boolean);
}
function hardware(items, emptyMessage = "В отчёте Agent пока нет сведений о составе оборудования.") {
  if (!items?.length) return `<div class="panel"><p class="empty">${escapeHtml(emptyMessage)}</p></div>`;
  const grouped = items.reduce((result,item) => { (result[item.type] ||= []).push(item); return result; }, {});
  const order = ["CPU","RAM","STORAGE","DRIVE","GPU","MOTHERBOARD","CONTROLLER","NETWORK","MONITOR"];
  const row = (item) => `<div class="component"><strong>${escapeHtml(componentPrimary(item))}</strong><div class="component-meta">${componentMeta(item).map((value) => `<span>${escapeHtml(value)}</span>`).join("") || '<span>Дополнительных характеристик нет</span>'}</div></div>`;
  return order.filter((type) => grouped[type]?.length).map((type) => {
    const group = grouped[type], visible = type === "CONTROLLER" ? group.slice(0,5) : group, remaining = group.slice(visible.length);
    return `<article class="hardware-card ${["RAM","STORAGE","NETWORK"].includes(type) && group.length > 1 ? "span-2" : ""}"><div class="hardware-card-header"><div><span class="eyebrow">${escapeHtml(type)}</span><h3>${escapeHtml(componentLabels[type])}</h3></div><span class="hardware-icon">${group.length}</span></div>${visible.map(row).join("")}${remaining.length ? `<details class="component-more"><summary>Показать ещё ${remaining.length}</summary>${remaining.map(row).join("")}</details>` : ""}</article>`;
  }).join("");
}
function componentSummary(type, raw) {
  if (!raw) return "Нет данных в снимке";
  if (type === "RAM") return [raw.description || raw.caption || raw.model || raw.manufacturer || "Модуль RAM", raw.capacity != null ? bytes(memoryCapacityBytes(raw.capacity)) : null, raw.numslots, raw.speed ? `${raw.speed} МГц` : null].filter(Boolean).join(" · ");
  if (type === "STORAGE") return [raw.model || raw.description || raw.name || "Накопитель", raw.disksize != null ? storageSize(raw.disksize) : null, raw.interface, raw.serial ? `S/N ${raw.serial}` : null].filter(Boolean).join(" · ");
  if (type === "ENDPOINT") return raw.hostname || raw.value || "Идентификатор устройства";
  return raw.model || raw.name || raw.description || raw.value || "Данные получены";
}

function comparisonFields(type) {
  const common = [['Модель',['model','name']],['Описание',['description','caption']],['Производитель',['manufacturer']],['Серийный номер',['serial']]];
  if (type === 'RAM') return [['Объём',['capacity'],value => Number(value) > 0 ? bytes(memoryCapacityBytes(value)) : 'Не указан'],['Тип памяти',['type','description','caption']],['Частота',['speed'],value => Number(value) > 0 ? `${value} МГц` : 'Не указана'],['Слот',['numslots','slot']],['Производитель',['manufacturer']],['Серийный номер',['serial']],['Модель',['model']]];
  if (type === 'STORAGE') return [...common,['Объём',['disksize'],value => Number(value) > 0 ? storageSize(value) : 'Не указан'],['Интерфейс',['interface']]];
  if (type === 'CPU') return [...common,['Ядра',['core']],['Потоки',['thread']],['Частота',['speed'],value => Number(value) > 0 ? `${value} МГц` : 'Не указана']];
  if (type === 'ENDPOINT') return [['Имя компьютера',['hostname','value']]];
  return common;
}

function renderFieldComparison(type, evidence) {
  const previous = evidence.previous, current = evidence.current;
  const rows = comparisonFields(type).map(([label,keys,format]) => {
    const before = rawValue(previous,keys), after = rawValue(current,keys);
    if (before === null && after === null) return '';
    const display = value => value === null ? 'Нет данных' : format ? format(value) : String(value);
    const changed = String(before) !== String(after);
    return `<tr><td>${escapeHtml(label)}</td><td>${escapeHtml(display(before))}</td><td${changed ? ' class="changed-value"' : ''}>${escapeHtml(display(after))}</td></tr>`;
  }).filter(Boolean);
  if (!rows.length) return '<p class="empty">Для сравнения нет подробных данных. Откройте технические сведения ниже.</p>';
  return `<table class="comparison-table"><caption class="sr-only">Сравнение сведений оборудования</caption><thead><tr><th scope="col">Характеристика</th><th scope="col">Было</th><th scope="col">Стало</th></tr></thead><tbody>${rows.join('')}</tbody></table><p class="comparison-note">${!previous || !current ? 'Компонент не представлен в одном из снимков. Проверьте полный отчёт и сам компьютер.' : 'Расхождение в сведениях Agent требует проверки. Название или описание само по себе не подтверждает замену оборудования.'}</p>`;
}
function changeCards(changes) {
  if (!changes.length) return '<div class="attention-banner ok"><span class="attention-icon">✓</span><div><strong>Изменений оборудования не обнаружено</strong><p>Текущий состав соответствует подтверждённому эталону.</p></div></div>';
  return changes.map((change) => `<article class="change-card"><div><h4>${escapeHtml(componentLabels[change.component_type] || change.component_type)}</h4><span class="meta">${escapeHtml(eventLabels[change.type] || change.type)} · ${dateTime(change.detected_at)}</span></div>${renderFieldComparison(change.component_type,change.evidence || {})}${pill(change.status === "OPEN" ? "ATTENTION" : change.status)}</article>`).join("");
}
async function sendAction(path, payload, method = "POST", message = "Изменения сохранены") {
  await api(path,{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); showToast(message); await load(false); if (state.selectedAsset) await detail(state.selectedAsset,false);
}
const assetTabNames = new Set(["overview","hardware","baseline","incidents","history","technical"]);
function selectAssetTab(requestedTab, updateHash = false) {
  const requested = assetTabNames.has(requestedTab) ? requestedTab : "overview";
  const requestedButton = document.querySelector(`[data-asset-tab="${requested}"]`);
  const tab = requestedButton && !requestedButton.hidden ? requested : "overview";
  state.assetTab = tab;
  document.querySelectorAll("[data-asset-tab]").forEach((button) => {
    const selected = button.dataset.assetTab === tab;
    button.setAttribute("aria-selected",String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
  document.querySelectorAll(".asset-tab-panel").forEach((panel) => { panel.hidden = panel.id !== `asset-tab-${tab}`; panel.setAttribute("aria-labelledby",`asset-tab-button-${panel.id.replace("asset-tab-","")}`); });
  if(updateHash && state.selectedAsset) {
    const nextHash = tab === "overview" ? `#asset=${state.selectedAsset}` : `#asset=${state.selectedAsset}&tab=${tab}`;
    if(location.hash !== nextHash) location.hash = nextHash;
  } else if(requested !== tab && state.selectedAsset && location.hash.startsWith(`#asset=${state.selectedAsset}`)) {
    history.replaceState(null,"",`#asset=${state.selectedAsset}`);
  }
}
async function detail(assetId, scroll = true, requestedTab = state.assetTab || "overview") {
  const requestView = ++viewGeneration;
  state.selectedComputer = null;
  $("detail").dataset.loadState = "loading";
  ["detail-meta", "detail-status", "detail-actions", "detail-key-facts"].forEach((id) => $(id).replaceChildren());
  try {
    document.querySelectorAll("main > .page-section").forEach((section) => { section.hidden = section.id !== "detail"; });
    setPageHeading("devices");
    $("detail").hidden = false; $("detail-title").textContent = "Загрузка…"; $("detail-error").hidden=true;
    const asset = await readRouteData("asset",assetId,`/admin/assets/${assetId}`);
    if (requestView !== viewGeneration) return;
    $("detail").dataset.loadState = "ready";
    state.selectedAsset = assetId; const endpoint = asset.endpoint; const status = deviceStatus(endpoint,asset);
    $("detail-title").textContent = asset.name; $("detail-status").innerHTML = pill(status);
    $("detail-meta").textContent = asset.inventory_number ? `Инв. № ${asset.inventory_number}` : "Инвентарный номер не задан";
    $("detail-key-facts").innerHTML = `<div><span>Размещение</span><strong>${escapeHtml(asset.room ? `Кабинет ${asset.room}` : "Кабинет не назначен")}</strong><small>${escapeHtml([asset.building,asset.floor && `Этаж ${asset.floor}`].filter(Boolean).join(" · "))}</small></div>${asset.category === "IT" || endpoint ? `<div><span>Компьютер</span><strong>${escapeHtml(endpoint?.hostname || "Agent не связан")}</strong></div><div><span>Последняя проверка Agent</span><strong>${escapeHtml(endpoint ? relativeTime(endpoint.last_seen_at) : "Нет данных Agent")}</strong></div>` : `<div><span>Количество</span><strong>${asset.quantity} ${escapeHtml(asset.unit || "шт.")}</strong></div><div><span>Проверка</span><strong>По обходам кабинета</strong>${asset.room_id ? `<a href="#room=${asset.room_id}">Открыть кабинет</a>` : ''}</div>`}`;
    $("detail-actions").innerHTML = `${canEditAsset(asset)?'<button id="edit-asset" class="button-secondary">Редактировать</button>':""}<button id="show-asset-qr" class="button-secondary">QR для обхода</button>`;
    if(canEditAsset(asset))$("edit-asset").onclick = () => openAssetEditDialog(asset);
    $("show-asset-qr").onclick = () => openAssetQrDialog(asset);
    const hasAgentSnapshot = Boolean(asset.current_snapshot || endpoint?.current_snapshot), usesAgent = asset.category === "IT";
    const showAgentDetails = usesAgent && Boolean(endpoint && hasAgentSnapshot);
    ["hardware","baseline","technical"].forEach((tab) => { document.querySelector(`[data-asset-tab="${tab}"]`).hidden = !showAgentDetails; });
    $("system-detail-panel").hidden = !showAgentDetails; $("identifiers-detail-panel").hidden = !showAgentDetails;
    $("agent-inventory-heading").hidden = !showAgentDetails; $("current-hardware").hidden = !showAgentDetails; $("agent-change-control").hidden = !showAgentDetails;
    const guidance = $("detail-agent-guidance");
    if (!usesAgent) {
      guidance.hidden=true;
    } else if (!endpoint) {
      guidance.className="attention-banner detail-guidance"; guidance.innerHTML='<span class="attention-icon">!</span><div><strong>Компьютер пока не связан с Agent</strong><p>Установите Agent и дождитесь первого отчёта. Когда компьютер появится в реестре как непривязанный, нажмите «Связать с имуществом».</p><a href="#agent-workflow">Как работает Agent →</a></div>'; guidance.hidden=false;
    } else if (!hasAgentSnapshot) {
      guidance.className="attention-banner detail-guidance"; guidance.innerHTML='<span class="attention-icon">!</span><div><strong>Компьютер связан, но отчёт ещё не получен</strong><p>Проверьте, включён ли компьютер, запущена ли служба Agent и настроен ли адрес сервера. После первой отправки здесь появятся Windows, BIOS и состав оборудования.</p><a href="#agent-workflow">Посмотреть путь данных Agent →</a></div>'; guidance.hidden=false;
    } else if (asset.latest_inventory?.agent_version_status === "UNSUPPORTED") {
      const supportedVersions = (asset.latest_inventory.supported_agent_versions || []).join(", ") || "не указаны";
      guidance.className="attention-banner detail-guidance"; guidance.innerHTML=`<span class="attention-icon">!</span><div><strong>Версия Agent ${escapeHtml(asset.latest_inventory.source_version)} не поддерживается</strong><p>Проверенные версии: ${escapeHtml(supportedVersions)}. Не меняйте эталон до отката Agent или отдельной проверки новой версии.</p></div>`; guidance.hidden=false;
    } else { guidance.hidden=true; }
    const hardwareInfo = asset.system?.hardware || {}, bios = asset.system?.bios || {}, os = asset.system?.operating_system || {}, network = asset.system?.network_quality || {};
    const emptySystemMessage = endpoint && hasAgentSnapshot ? "Последний отчёт не содержит этих сведений." : "Сведения появятся после первого отчёта Agent.";
    $("device-general").innerHTML = factRows([["Инвентарный номер",asset.inventory_number],["Категория",categoryLabels[asset.category]],["Тип",assetTypeLabels[asset.asset_type] || asset.asset_type],["Учёт",asset.tracking_mode === "GROUPED" ? "Групповой" : "Поштучный"],["Количество", `${asset.quantity} ${asset.unit || "шт."}`],["Организация",asset.organization],["Корпус",asset.building],["Этаж",asset.floor],["Кабинет",asset.room],["Статус",statusLabels[status]],["Примечание",asset.notes]],"Заполните карточку или выберите кабинет, чтобы найти имущество в реестре.");
    $("device-system").innerHTML = factRows([["Версия Agent",asset.latest_inventory?.source_version],["Версия установщика",asset.latest_inventory?.installer_version],["Получено от Agent",dateTime(asset.latest_inventory?.received_at)],["Операционная система",os.full_name || os.name],["Версия",os.version],["Сборка / ядро",os.kernel_version],["Архитектура",os.arch],["BIOS",bios.bversion],["Дата BIOS",bios.bdate],["Производитель",bios.smanufacturer || bios.bmanufacturer],["Модель",bios.smodel || bios.mmodel],["Серийный номер",bios.ssn || bios.msn],["Корпус",hardwareInfo.chassis_type],["Рабочая группа",hardwareInfo.workgroup],["Сеть: цель",network.target],["Сеть: доступность",network.packet_loss_percent != null ? `${network.packet_loss_percent}% потерь` : null],["Сеть: средняя задержка",network.average_latency_ms != null ? `${network.average_latency_ms} мс` : null],["Сеть: измерено",network.measured_at]],emptySystemMessage);
    $("device-identifiers").innerHTML = factRows((endpoint?.identifiers || []).map((item) => [(identifierLabels[item.type] || item.type),item.value]),emptySystemMessage);
    $("snapshot-meta").textContent = asset.current_snapshot ? `${asset.current_snapshot.type === "FULL" ? "Полная" : "Частичная"} проверка · ${dateTime(asset.current_snapshot.captured_at)}` : "Данных пока нет";
    const supplemental = [...(asset.system?.drives || []).map((raw_data) => ({type:"DRIVE",raw_data,model:raw_data.description || raw_data.label})),...(asset.system?.controllers || []).map((raw_data) => ({type:"CONTROLLER",raw_data,model:raw_data.name || raw_data.caption}))];
    $("current-hardware").innerHTML = hardware([...asset.current_hardware,...supplemental],"Отчёт Agent получен, но компоненты оборудования в нём не найдены."); $("baseline-hardware").innerHTML = hardware(asset.baseline_hardware,"Эталон ещё не подтверждён. Сначала проверьте данные Agent и сохраните их как эталон.");
    $("baseline-summary").textContent = asset.baseline ? `Эталон подтверждён ${dateTime(asset.baseline.accepted_at)}${asset.baseline.reason ? ` · ${asset.baseline.reason}` : ""}` : "Эталонное состояние ещё не подтверждено.";
    $("baseline-action").innerHTML = asset.recommended_baseline_snapshot_id ? `<button id="accept-baseline">${asset.baseline ? "Обновить эталон" : "Подтвердить как эталон"}</button>` : "";
    if ($("accept-baseline")) $("accept-baseline").onclick = () => openConfirmation({title:asset.baseline?"Обновить эталонный состав?":"Подтвердить эталонный состав?",description:"Последняя полная инвентаризация станет эталоном для следующих сравнений. История и доказательства не удаляются.",confirmLabel:asset.baseline?"Обновить эталон":"Подтвердить эталон",reasonLabel:"Основание для изменения эталона",reasonPlaceholder:"Например, первичная проверка или согласованная модернизация",onConfirm:async(reason)=>sendAction(`/admin/snapshots/${asset.recommended_baseline_snapshot_id}/baseline`,{reason},"POST","Эталонное состояние подтверждено")});
    $("detail-changes").innerHTML = asset.baseline ? changeCards(asset.changes) : '<div class="attention-banner"><span class="attention-icon">!</span><div><strong>Эталон ещё не создан</strong><p>Подтвердите текущий состав, чтобы AssetGuard начал показывать изменения по принципу «Было → Стало».</p></div></div>';
    $("detail-incidents").innerHTML = asset.incidents.length ? asset.incidents.map((incident) => `<article class="row-card"><div class="row-title"><b>${escapeHtml(incidentLabel(incident))}</b>${pill(incident.status)}</div><div class="meta">${dateTime(incident.created_at)}</div><div class="actions"><button class="open-incident button-secondary" data-id="${incident.id}">Открыть инцидент</button>${state.currentUser?.role === "ADMIN" && ["OPEN","UNDER_REVIEW"].includes(incident.status) ? `<button class="resolve" data-id="${incident.id}">Зафиксировать решение</button>` : ""}</div></article>`).join("") : '<p class="empty">Открытых обращений нет.</p>';
    const physical = state.physicalIncidents.filter(incident => incident.asset_id === asset.id);
    if (physical.length) {
      if (!asset.incidents.length) $("detail-incidents").replaceChildren();
      $("detail-incidents").insertAdjacentHTML("beforeend", physical.map(incident => `<article class="row-card"><div class="row-title"><b>Обход · ${escapeHtml(inspectionLabels[incident.issue_type])}</b>${pill(incident.status)}</div><p class="meta">${dateTime(incident.created_at)} · проблемных единиц: ${incident.affected_quantity}</p><a class="button-anchor button-secondary" href="#physical-incident=${incident.id}">Открыть инцидент</a></article>`).join(""));
    }

    bindDynamicActions();
    document.querySelectorAll(".resolve").forEach((button) => button.onclick = () => openIncidentDecisionDialog(button.dataset.id,true));
    $("detail-history").innerHTML = asset.history.length ? asset.history.map((entry) => `<article><time>${dateTime(entry.occurred_at)}</time><div><b>${escapeHtml(eventLabels[entry.type] || entry.type)}</b><p>${escapeHtml(historyMessage(entry))}</p></div></article>`).join("") : '<p class="empty">История появится после первой проверки или действия с устройством.</p>';
    selectAssetTab(requestedTab);
    if(scroll) $("detail").scrollIntoView({behavior:"smooth",block:"start"});
  } catch(error) {
    if (requestView !== viewGeneration || error.stale) return;
    $("detail").dataset.loadState = "error";
    $("detail-title").textContent="Не удалось открыть карточку";
    $("detail-status").innerHTML=""; $("detail-meta").textContent=""; $("detail-actions").innerHTML=""; $("detail-agent-guidance").hidden=true;
    $("detail-error").innerHTML=`<span class="attention-icon">!</span><div><strong>Ошибка загрузки</strong><p>${escapeHtml(error.message)}</p><button type="button" class="button-secondary retry-route">Повторить</button></div>`;
    $("detail-error").hidden=false;
    $("detail-error").querySelector(".retry-route").onclick=()=>detail(assetId,false,requestedTab);
    document.querySelectorAll(".asset-tab-panel").forEach((panel)=>panel.hidden=true);
    showToast(error.message,true);
  }
}
function assetCategoryForType(type) { return ({Desktop:"IT",Laptop:"IT",Printer:"IT",Projector:"IT",Network:"IT",Furniture:"FURNITURE",Sports:"SPORTS",Educational:"EDUCATIONAL",Other:"OTHER"})[type] || "OTHER"; }
function managedRoomsForAsset(asset) {
  const organizationId = state.currentUser?.organization_id || state.organizations.find((item) => item.name === asset.organization)?.id;
  return state.locations.filter((building) => !organizationId || building.organization_id === organizationId).flatMap((building) => building.floors.flatMap((floor) => floor.rooms.map((room) => ({id:room.id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`}))));
}
function syncAssetEditTrackingMode() { const grouped=$("asset-edit-tracking-mode").value === "GROUPED"; $("asset-edit-quantity-field").hidden=!grouped; $("asset-edit-quantity").disabled=!grouped; $("asset-edit-quantity").required=grouped; }
function openAssetEditDialog(asset) {
  state.editingAsset = asset;
  $("asset-edit-inventory-number").value=asset.inventory_number || ""; $("asset-edit-name").value=asset.name || ""; $("asset-edit-type").value=asset.asset_type || "Other"; $("asset-edit-tracking-mode").value=asset.tracking_mode || "INDIVIDUAL"; $("asset-edit-quantity").value=asset.quantity || 1; $("asset-edit-unit").value=asset.unit || "шт."; $("asset-edit-notes").value=asset.notes || "";
  const rooms=managedRoomsForAsset(asset); $("asset-edit-room").innerHTML='<option value="">Не назначать кабинет</option>'+rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join(""); if(asset.room_id && rooms.some((room)=>room.id===asset.room_id))$("asset-edit-room").value=asset.room_id;
  syncAssetEditTrackingMode(); openDialog("asset-edit-dialog", "asset-edit-name");
}
async function printAssetQr(asset, publicUrl) {
  const popup=window.open("", "assetguard-qr", "width=520,height=620"); if(!popup) throw new Error("Разрешите всплывающее окно для QR-кода и повторите попытку.");
  popup.document.write('<title>AssetGuard QR</title><main style="font-family:system-ui;text-align:center;padding:24px"><p>Готовим QR-код…</p></main>'); popup.document.close();
  try { const suffix=publicUrl?`?public_url=${encodeURIComponent(publicUrl)}`:""; const blob=await apiBlob(`/admin/assets/${asset.id}/qr.svg${suffix}`); if(state.assetQrUrl)URL.revokeObjectURL(state.assetQrUrl);state.assetQrUrl=URL.createObjectURL(blob); popup.document.body.innerHTML=`<main style="font-family:system-ui;text-align:center;padding:24px"><h1>${escapeHtml(asset.name)}</h1><p>${escapeHtml(asset.inventory_number)}</p><img style="width:320px;height:320px" src="${state.assetQrUrl}" alt="QR"><p>Отсканируйте код, чтобы открыть карточку имущества.</p><button onclick="print()">Печать</button></main>`; }
  catch(error) { popup.close(); throw error; }
}
function openAssetQrDialog(asset) {
  state.qrAsset=asset; $("asset-qr-title").textContent=`QR · ${asset.name}`; let saved=localStorage.getItem("assetguardPublicUrl") || ""; if(!saved && !["localhost","127.0.0.1"].includes(location.hostname))saved=location.origin; $("asset-qr-public-url").value=saved; $("asset-qr-help").textContent=saved ? "Этот адрес будет записан в QR-код." : "Сейчас вы работаете локально: QR можно напечатать, но телефон его не откроет без публичного HTTPS-адреса."; openDialog("asset-qr-dialog", "asset-qr-public-url");
}
function historyMessage(entry) {
  if(entry.type === "INVENTORY_COMPLETED") return `${entry.metadata?.inventory_type === "FULL" ? "Полная" : "Частичная"} проверка завершена, данные сохранены.`;
  if(entry.type === "HARDWARE_CHANGE_DETECTED") return `${componentLabels[entry.metadata?.component_type] || "Состав оборудования"}: требуется проверка.`;
  if(entry.type === "BASELINE_ACCEPTED") return "Текущее состояние сохранено как эталон.";
  if(entry.type === "INCIDENT_RESOLVED") return `Решение зафиксировано: ${incidentClassificationLabels[entry.metadata?.classification] || entry.metadata?.classification || "проверено"}.`;
  return entry.message;
}
async function openIncidentDetail(id, scroll = true, physical = false) {
  const requestView = ++viewGeneration;
  $("incident-detail").dataset.loadState = "loading";
  ["incident-detail-meta", "incident-detail-status"].forEach((id) => $(id).replaceChildren());
  document.querySelectorAll("main > .page-section").forEach((section) => { section.hidden = section.id !== "incident-detail"; });
  setPageHeading("incidents");
  state.selectedIncident = id;
  $("incident-detail-title").textContent = "Загрузка инцидента…";
  $("incident-detail-actions").innerHTML = "";
  $("incident-detail-error").hidden = true;
  $("incident-detail-comparison").innerHTML = '<div class="skeleton"></div>';
  $("incident-detail-decisions").innerHTML = '<div class="skeleton short"></div>';
  try {
    const incident = await readRouteData(physical ? "physical-incident" : "incident",id,physical ? `/admin/locations/physical-incidents/${id}` : `/admin/incidents/${id}`);
    if (requestView !== viewGeneration || state.selectedIncident !== id) return;
    $("incident-detail").dataset.loadState = "ready";
    if (physical) { renderPhysicalIncidentDetail(incident); return; }
    $("incident-evidence-heading").textContent = "Было → Стало";
    const summary = state.incidents.find((item) => item.id === id);
    const change = state.changes.find((item) => item.id === incident.change_event_id);
    const endpointId = summary?.endpoint_id || incident.endpoint_id || change?.endpoint_id;
    const device = deviceForEndpoint(endpointId);
    const componentType = change?.component_type || incident.component_type || (summary?.title || incident.title || "").split(":")[0];
    const evidence = incident.evidence || change?.evidence || {};
    const active = ["OPEN","UNDER_REVIEW"].includes(incident.status);
    $("incident-detail-title").textContent = incidentLabel(summary || incident, change);
    $("incident-detail-status").innerHTML = pill(incident.status);
    $("incident-detail-meta").textContent = [device?.name || device?.hostname, device && locationLabel(device), dateTime(summary?.created_at || incident.created_at)].filter((value) => value && value !== "—").join(" · ") || "Технический инцидент";
    $("incident-detail-actions").innerHTML = state.currentUser?.role === "ADMIN" && active ? `<button type="button" id="incident-detail-review" class="button-secondary">Взять на проверку</button><button type="button" id="incident-detail-resolve">Зафиксировать решение</button>` : "";
    $("incident-detail-review")?.addEventListener("click", () => openIncidentDecisionDialog(id, false));
    $("incident-detail-resolve")?.addEventListener("click", () => openIncidentDecisionDialog(id, true));
    $("incident-detail-comparison").innerHTML = renderFieldComparison(componentType, evidence);
    $("incident-detail-evidence").textContent = Object.keys(evidence).length ? JSON.stringify(evidence, null, 2) : "Технические evidence для этого инцидента не приложены.";
    $("incident-detail-facts").innerHTML = factRows([["Устройство",device?.name || device?.hostname],["Инвентарный номер",device?.inventoryNumber],["Расположение",device && locationLabel(device)],["Приоритет",incident.severity === "HIGH" ? "Высокий" : incident.severity === "LOW" ? "Низкий" : "Средний"],["Обнаружено",dateTime(summary?.created_at || incident.created_at)],["Закрыто",dateTime(incident.resolved_at)],["Описание",incident.description === "Automatically created from an explainable inventory change." ? null : incident.description]],"Контекст устройства появится после его привязки к реестру.");
    $("incident-device-action").innerHTML = device?.assetId ? `<button type="button" class="open-device button-secondary" data-id="${device.assetId}">Карточка имущества</button>` : device ? `<a class="button-anchor button-secondary" href="#computer=${device.endpointId}">Карточка компьютера</a>${state.currentUser?.role === "ADMIN" ? `<button type="button" class="link-endpoint button-secondary" data-id="${device.endpointId}" data-name="${escapeHtml(device.hostname || "")}">Связать с имуществом</button>` : ""}` : "";
    bindDynamicActions();
    $("incident-detail-decisions").innerHTML = incident.decisions.length ? incident.decisions.slice().reverse().map((decision) => `<article><time>${dateTime(decision.created_at)}</time><div><b>${escapeHtml(incidentClassificationLabels[decision.classification] || decision.classification)}</b><p>${escapeHtml(decision.comment || "Без комментария")} · ${escapeHtml(decision.actor || "Оператор")}</p></div></article>`).join("") : '<div class="empty-state"><strong>Решений пока нет</strong><p>Возьмите инцидент на проверку или зафиксируйте итог.</p></div>';
    if (scroll) $("incident-detail").scrollIntoView({behavior:"smooth",block:"start"});
  } catch (error) {
    if (requestView !== viewGeneration || error.stale) return;
    $("incident-detail").dataset.loadState = "error";
    $("incident-detail-title").textContent = "Не удалось открыть инцидент";
    $("incident-detail-error").innerHTML = `<span class="attention-icon">!</span><div><strong>Ошибка загрузки</strong><p>${escapeHtml(error.message)}</p><button type="button" class="button-secondary retry-route">Повторить</button></div>`;
    $("incident-detail-error").hidden = false;
    $("incident-detail-error").querySelector(".retry-route").onclick=()=>openIncidentDetail(id,false,physical);
    showToast(error.message,true);
  }
}

function renderPhysicalIncidentDetail(incident) {
  const evidence = incident.evidence || {};
  $("incident-evidence-heading").textContent = "Результат физического обхода";
  $("incident-detail-title").textContent = `${incident.asset_name} · ${inspectionLabels[incident.issue_type] || incident.issue_type}`;
  $("incident-detail-status").innerHTML = pill(incident.status);
  $("incident-detail-meta").textContent = `Обход · ${incident.room_path} · ${dateTime(incident.created_at)}`;
  $("incident-detail-comparison").innerHTML = '<dl class="facts">' + factRows([["Ожидалось", evidence.expected_quantity], ["Проблемных единиц", evidence.affected_quantity], ["Результат", inspectionLabels[evidence.result]], ["Проверил", evidence.inspector_name], ["Дата обхода", dateTime(evidence.completed_at)], ["Комментарий", evidence.comment]]) + "</dl>";
  $("incident-detail-evidence").textContent = JSON.stringify(evidence, null, 2);
  $("incident-detail-facts").innerHTML = factRows([["Имущество", incident.asset_name], ["Инвентарный номер", incident.inventory_number], ["Кабинет", incident.room_path], ["Приоритет", incident.severity === "HIGH" ? "Высокий" : incident.severity === "LOW" ? "Низкий" : "Средний"], ["Закрыто", dateTime(incident.resolved_at)], ["Описание", incident.description]]);
  $("incident-device-action").innerHTML = `<button type="button" class="open-device button-secondary" data-id="${incident.asset_id}">Карточка имущества</button>`;
  $("incident-detail-decisions").innerHTML = incident.decisions.length ? incident.decisions.slice().reverse().map(decision => `<article><time>${dateTime(decision.created_at)}</time><div><b>${escapeHtml(physicalActionLabels[decision.action] || decision.action)}</b><p>${escapeHtml(decision.comment || "Без комментария")} · ${escapeHtml(decision.actor)}</p>${decision.has_act ? `<button type="button" class="button-secondary physical-act-download" data-document="${escapeHtml(decision.document_number)}">Скачать акт ${escapeHtml(decision.document_number)}</button>` : ""}</div></article>`).join("") : '<p class="empty">Решений пока нет.</p>';
  $("incident-detail-decisions").querySelectorAll(".physical-act-download").forEach(button => button.onclick = () => downloadPhysicalIncidentAct(incident.id,button.dataset.document));
  const active = ["OPEN", "UNDER_REVIEW"].includes(incident.status);
  $("incident-detail-actions").innerHTML = active && canEditRoom(incident.room_id) ? '<button id="physical-detail-decision" type="button">Зафиксировать решение</button>' : "";
  $("physical-detail-decision")?.addEventListener("click", async () => {
    const generation = viewGeneration, button = $("physical-detail-decision");
    button.disabled = true;
    try {
      const workspace = await readRouteData("room",incident.room_id,`/admin/locations/rooms/${incident.room_id}/workspace`);
      if (generation !== viewGeneration) return;
      state.roomWorkspace = workspace;
      openPhysicalIncidentDialog(incident.id);
    } catch (error) { if (!error.stale && generation === viewGeneration) showToast(error.message,true); }
    finally { button.disabled = false; }
  });
  bindDynamicActions();
}

function openIncidentDecisionDialog(id, resolve) {
  const incident = state.incidents.find((item) => item.id === id);
  state.selectedIncident = id;
  state.incidentDecisionMode = resolve ? "resolve" : "review";
  $("incident-decision-title").textContent = resolve ? "Зафиксировать решение" : "Взять на проверку";
  $("incident-decision-target").textContent = incident ? incidentLabel(incident, state.changes.find((item) => item.id === incident.change_event_id)) : "Укажите, что нужно проверить.";
  $("incident-classification-field").hidden = !resolve;
  $("incident-decision-classification").disabled = !resolve;
  $("incident-decision-classification").value = "AUTHORIZED_CHANGE";
  $("incident-decision-comment").value = "";
  $("incident-decision-note").textContent = resolve ? "После сохранения инцидент будет закрыт, а решение останется в истории." : "Инцидент перейдёт в статус «На проверке» и останется открытым.";
  $("incident-decision-submit").textContent = resolve ? "Сохранить решение" : "Взять на проверку";
  openDialog("incident-decision-dialog", "incident-decision-comment");
}
function openLink(endpointId,hostname) { state.linkingEndpoint=endpointId; $("link-target").textContent=`Найденный компьютер: ${hostname || endpointId}`; $("link-asset").innerHTML=state.assets.filter((asset) => asset.category === "IT" && asset.tracking_mode !== "GROUPED" && !asset.endpoint_id).map((asset) => `<option value="${asset.id}">${escapeHtml(asset.inventory_number)} — ${escapeHtml(asset.name)}${asset.room ? ` · каб. ${escapeHtml(asset.room)}` : " · без кабинета"}</option>`).join(""); renderLinkChoice(); clearFormError($("link-form")); if(!$("link-asset").options.length){showToast("Добавьте в реестр свободную запись компьютера, чтобы связать с ней Agent.",true);return;} openDialog("link-dialog", "link-asset"); }
function renderLinkChoice() {
  const asset = state.assets.find(item => item.id === $("link-asset").value);
  $("link-choice-details").innerHTML = asset ? factRows([['Имущество',asset.name],['Инвентарный номер',asset.inventory_number],['Размещение',locationLabel(asset) || 'Не назначено']]) : '';
}

function visionCountRows(counts) { const entries=Object.entries(counts||{}); return entries.length ? entries.map(([name,count]) => `<div class="count-row"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>`).join("") : '<p class="empty">Объекты выбранных классов не найдены.</p>'; }
async function renderVisionScan(scan,roomName) {
  state.visionScan=scan; state.visionRoomId=scan.room_id; $("vision-result").hidden=false; $("vision-room-title").textContent=roomName||"Кабинет"; $("vision-status-badge").innerHTML=statusLabels[scan.status]||scan.status; $("vision-status-badge").className=`status-pill ${classForStatus(scan.status)}`; $("vision-counts").innerHTML=`${scan.asset ? `<p class="meta">Связанное имущество: <button class="link-button" id="vision-asset-link">${escapeHtml(scan.asset.name)} · ${escapeHtml(scan.asset.inventory_number)}</button></p>` : ""}${visionCountRows(scan.counts)}`;
  if(scan.asset) $("vision-asset-link").onclick=()=>detail(scan.asset.id);
  const differences=scan.comparison?.differences||[]; $("vision-comparison").innerHTML=scan.status==="NOT_CHECKED" ? '<p class="empty">Эталон ещё не подтверждён.</p>' : differences.length ? differences.map((item)=>`<div class="comparison-row warning"><span>${escapeHtml(item.class_name)}</span><span>ожидалось ${item.expected}, найдено ${item.detected}</span><strong>${item.difference>0?"+":""}${item.difference}</strong></div>`).join("") : '<div class="comparison-ok">Количество объектов соответствует эталону.</div>';
  $("vision-baseline").textContent=scan.status==="NOT_CHECKED"?"Подтвердить как эталон":"Обновить эталон"; if(state.visionImageUrl) URL.revokeObjectURL(state.visionImageUrl); const blob=await apiBlob(scan.annotated_image_url); state.visionImageUrl=URL.createObjectURL(blob); $("vision-image").src=state.visionImageUrl;
}
async function loadVisionHistory(roomId) { if(!roomId){$("vision-history").innerHTML='<p class="empty">Загрузите первое фото помещения.</p>';return;} const scans=await api(`/admin/vision/rooms/${roomId}/scans`); const room=state.visionRooms.find((item)=>item.id===roomId); $("vision-history").innerHTML=scans.map((scan)=>`<button class="vision-history-item" data-id="${scan.id}"><span><b>${dateTime(scan.created_at)}</b><small>${Object.entries(scan.counts).map(([name,count])=>`${escapeHtml(name)}: ${count}`).join(" · ")||"Объекты не найдены"}</small></span>${pill(scan.status)}</button>`).join("")||'<p class="empty">История проверок пуста.</p>'; document.querySelectorAll(".vision-history-item").forEach((button)=>button.onclick=async()=>renderVisionScan(await api(`/admin/vision/scans/${button.dataset.id}`),room?.name)); }
function renderVisionRooms(rooms) { state.visionRooms=rooms; const locationRooms=state.locations.flatMap((building)=>building.floors.flatMap((floor)=>floor.rooms.map((room)=>({id:room.id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`})))); const locationSelect=$("vision-location-room"),selectedLocation=locationSelect.value; locationSelect.innerHTML=locationRooms.length?'<option value="">Выберите кабинет</option>'+locationRooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join(""):'<option value="">Сначала создайте корпус, этаж и кабинет</option>'; if(locationRooms.some((room)=>room.id===selectedLocation))locationSelect.value=selectedLocation;locationSelect.disabled=!locationRooms.length; $("vision-run").disabled=!locationRooms.length; $("vision-room-select").innerHTML=rooms.length?rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.name)}</option>`).join(""):'<option value="">Проверок пока нет</option>'; syncVisionAssetsForRoom(locationSelect.value); if(rooms.length){const selected=rooms.find((room)=>room.id===state.visionRoomId)||rooms[0];state.visionRoomId=selected.id;$("vision-room-select").value=selected.id;loadVisionHistory(selected.id);if(!state.visionScan&&selected.latest_scan)renderVisionScan(selected.latest_scan,selected.name);}else loadVisionHistory(null); }

async function load(showLoading=true) {
  if (!token) return false;
  const generation = sessionGeneration;
  const requestLoad = ++loadGeneration;
  if (showLoading || !state.currentUser) setLoadState("loading");
  $("status").textContent = "Обновляем данные…";
  $("refresh-data").disabled = true;
  clearRouteDataCache();
  try {
    const currentUser = await api("/auth/me");
    if (!currentUser || typeof currentUser.username !== "string" || !["ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"].includes(currentUser.role)) throw new Error("Сервер не подтвердил учётную запись. Повторите вход.");
    if (generation !== sessionGeneration || requestLoad !== loadGeneration) return false;
    state.currentUser = currentUser;
    sessionStorage.setItem("assetguard-admin-token", token);
    setAuthenticatedUi();
    const [assets,endpoints,changes,incidents,visionRooms,operations,locations,physicalIncidents] = await Promise.all([
      api("/admin/assets"),api("/admin/endpoints"),api("/admin/changes"),api("/admin/incidents"),
      api("/admin/vision/rooms"),api("/admin/operations/status"),api("/admin/locations/tree"),api("/admin/locations/physical-incidents"),
    ]);
    if (generation !== sessionGeneration || requestLoad !== loadGeneration) return false;
    state = {...state,assets,endpoints,changes,incidents,visionRooms,operations,locations,physicalIncidents};
    syncRoleControls(); buildDevices(); renderDashboard(); renderOperations(operations); renderLocations(locations); renderDevices(); renderVisionRooms(visionRooms);
    await loadAdminAccess();
    if (generation !== sessionGeneration || requestLoad !== loadGeneration) return false;
    setLoadState("ready");
    $("status").textContent = `Данные актуальны · ${dateTime(new Date())}`;
    return true;
  } catch (error) {
    if (generation !== sessionGeneration || requestLoad !== loadGeneration || error.stale) return false;
    if (error.status === 401) endSession("Данные входа недействительны или сессия истекла. Войдите снова.");
    else if (!state.currentUser) { showLoginError(error.message); $("retry-session").hidden = false; }
    else { $("status").textContent = "Данные не обновлены"; setLoadState("error", error.message); }
    return false;
  } finally {
    if (requestLoad === loadGeneration) $("refresh-data").disabled = false;
  }
}
async function openRouteFromHash() {
  if (!state.currentUser || $("app-main").dataset.loadState !== "ready") return;
  const computerMatch = location.hash.match(/^#computer=([0-9a-f-]{36})$/i);
  if (computerMatch) { await openComputerDetail(computerMatch[1]); return; }
  const assetMatch = location.hash.match(/^#asset=([0-9a-f-]{36})(?:&tab=([a-z-]+))?$/i);
  const roomMatch = location.hash.match(/^#room=([0-9a-f-]{36})$/i);
  const physicalMatch = location.hash.match(/^#physical-incident=([0-9a-f-]{36})$/i);
  if(physicalMatch){await openIncidentDetail(physicalMatch[1],false,true);return;}
  const incidentMatch = location.hash.match(/^#incident=([0-9a-f-]{36})$/i);
  if(assetMatch){const tab=assetMatch[2]||"overview";if(state.selectedAsset===assetMatch[1]&&!$("detail").hidden)selectAssetTab(tab);else await detail(assetMatch[1],false,tab);return;}
  if(roomMatch){await openRoomWorkspace(roomMatch[1],false);return;}
  if(incidentMatch){await openIncidentDetail(incidentMatch[1],false);return;}
  showPrimaryRoute(location.hash.slice(1)||"overview");
  if(!$("agent-credentials").hidden) { renderAgentFleet(); await loadNotifications(); }
}

$("token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loginInProgress) return;
  clearLoginError();
  $("retry-session").hidden = true;
  const username = $("username").value.trim(), secret = $("token").value;
  if (loginMode === "password" && !username) { showLoginError("Введите логин сотрудника.", "username"); return; }
  if (!secret) { showLoginError(loginMode === "password" ? "Введите пароль." : "Введите ключ администратора."); return; }
  let attemptGeneration = sessionGeneration;
  setLoginBusy(true);
  try {
    const credential = loginMode === "password" ? (await requestJson("/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({username,password:secret})}, "")).access_token : secret;
    if (typeof credential !== "string" || !credential) throw new Error("Сервер не подтвердил вход. Повторите попытку.");
    sessionGeneration += 1;
    attemptGeneration = sessionGeneration;
    token = credential;
    $("token").value = "";
    if (await load()) {
      await openRouteFromHash();
      if (attemptGeneration === sessionGeneration && state.currentUser) { $("app-main").focus(); showToast("Вход выполнен"); }
    }
  } catch (error) {
    if (!error.stale && attemptGeneration === sessionGeneration) showLoginError(error.status === 401 ? "Неверный логин или пароль. Проверьте данные и повторите вход." : error.message);
  } finally { if (attemptGeneration === sessionGeneration) setLoginBusy(false); }
});

$("login-mode").onclick = () => {
  loginMode = loginMode === "password" ? "key" : "password";
  const keyMode = loginMode === "key";
  clearLoginError();
  $("username-field").hidden = keyMode;
  $("username").required = !keyMode;
  $("secret-label").textContent = keyMode ? "Ключ администратора" : "Пароль";
  $("token").placeholder = keyMode ? "Введите ключ администратора" : "Введите пароль";
  $("token").autocomplete = keyMode ? "off" : "current-password";
  $("token").value = "";
  $("token").type = "password";
  $("toggle-password").textContent = "Показать";
  $("toggle-password").setAttribute("aria-label", "Показать пароль");
  $("toggle-password").setAttribute("aria-pressed", "false");
  $("login-mode").textContent = keyMode ? "Вход по логину и паролю" : "Вход по ключу администратора";
  $("login-description").textContent = keyMode ? "Этот вариант предназначен для первичной настройки администратором. Используйте защищённый ключ вашего сервера." : "Используйте учётную запись, которую выдал администратор вашей организации.";
  $("login-help").textContent = keyMode ? "Не передавайте ключ сотрудникам. Для ежедневной работы создайте именованную учётную запись." : "Нет учётной записи? Обратитесь к администратору школы.";
  $(keyMode ? "token" : "username").focus();
};
$("toggle-password").onclick = () => {
  const visible = $("token").type === "password";
  $("token").type = visible ? "text" : "password";
  $("toggle-password").textContent = visible ? "Скрыть" : "Показать";
  $("toggle-password").setAttribute("aria-label", visible ? "Скрыть пароль" : "Показать пароль");
  $("toggle-password").setAttribute("aria-pressed", String(visible));
};
$("login-error-field").onclick = (event) => { event.preventDefault(); $($("login-error-field").hash.slice(1)).focus(); };
$("skip-navigation").onclick = (event) => { event.preventDefault(); $("app-main").focus(); };
async function reloadWorkspace() { if (await load()) await openRouteFromHash(); }
$("refresh-data").onclick = reloadWorkspace;
$("retry-load").onclick = reloadWorkspace;
$("retry-session").onclick = async () => { const generation = sessionGeneration; clearLoginError(); setLoginBusy(true,"Восстанавливаем сессию…"); try { await reloadWorkspace(); } finally { if (generation === sessionGeneration) setLoginBusy(false); } };
function closeNavigation(returnFocus = false) {
  const wasOpen = $("app-header").classList.contains("nav-open");
  $("app-header").classList.remove("nav-open");
  $("nav-toggle").setAttribute("aria-expanded", "false");
  $("nav-toggle").setAttribute("aria-label", "Открыть меню");
  if (wasOpen && returnFocus) $("nav-toggle").focus();
}
$("nav-toggle").addEventListener("click",()=>{const header=document.querySelector(".app-header"),open=header.classList.toggle("nav-open");$("nav-toggle").setAttribute("aria-expanded",String(open));$("nav-toggle").setAttribute("aria-label",open?"Закрыть меню":"Открыть меню");});
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeNavigation(true); });
document.addEventListener("click", (event) => { if (!$("app-header").contains(event.target)) closeNavigation(); });
document.querySelectorAll("#main-nav a").forEach((link)=>link.addEventListener("click",()=>{document.querySelector(".app-header").classList.remove("nav-open");$("nav-toggle").setAttribute("aria-expanded","false");$("nav-toggle").setAttribute("aria-label","Открыть меню");document.querySelectorAll("#main-nav a").forEach((item)=>item.removeAttribute("aria-current"));link.setAttribute("aria-current","location");}));
function syncTrackingMode() { const grouped=$("asset-tracking-mode").value==="GROUPED", field=$("asset-quantity-field"), input=field.querySelector("input");field.hidden=!grouped;input.disabled=!grouped;input.required=grouped; }
$("asset-tracking-mode").addEventListener("change",syncTrackingMode);
$("asset-edit-tracking-mode").addEventListener("change",syncAssetEditTrackingMode);
$("asset-edit-cancel").onclick=()=>$("asset-edit-dialog").close();
$("asset-edit-form").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget,asset=state.editingAsset;if(!asset || $("asset-edit-submit").disabled)return;clearFormError(form);const button=$("asset-edit-submit"),trackingMode=$("asset-edit-tracking-mode").value,roomId=$("asset-edit-room").value||null;const body={inventory_number:$("asset-edit-inventory-number").value.trim(),name:$("asset-edit-name").value.trim(),asset_type:$("asset-edit-type").value,category:assetCategoryForType($("asset-edit-type").value),tracking_mode:trackingMode,quantity:trackingMode==="GROUPED"?Number($("asset-edit-quantity").value):1,unit:$("asset-edit-unit").value.trim()||"шт.",room_id:roomId,notes:$("asset-edit-notes").value.trim()||null};button.disabled=true;button.textContent="Сохраняем…";try{await sendAction(`/admin/assets/${asset.id}`,body,"PATCH","Карточка имущества обновлена");$("asset-edit-dialog").close();}catch(error){showFormError(form,error.message);}finally{button.disabled=false;button.textContent="Сохранить изменения";}});
$("asset-qr-cancel").onclick=()=>$("asset-qr-dialog").close();
$("asset-qr-form").addEventListener("submit", event => submitFormAction(event,"asset-qr-submit",async () => {
  const asset=state.qrAsset; if (!asset) return;
  const raw=$("asset-qr-public-url").value.trim(); let publicUrl="";
  if (raw) {
    const normalized=new URL(raw);
    if (normalized.protocol !== "https:") throw new Error("Для печати нужен HTTPS-адрес.");
    publicUrl=normalized.origin; localStorage.setItem("assetguardPublicUrl",publicUrl);
  }
  await printAssetQr(asset,publicUrl); $("asset-qr-dialog").close();
}));
$("clear-device-filters").addEventListener("click",clearDeviceFilters);
$("logout").onclick = async () => {
  const previousToken = token, isNamedSession = Boolean(state.currentUser?.id);
  endSession();
  closeNavigation();
  history.replaceState(null, "", "#overview");
  document.title = "Вход — AssetGuard";
  showToast("Вы вышли из системы");
  if (previousToken && isNamedSession) {
    try { await requestJson("/auth/logout", {method: "POST"}, previousToken); }
    catch (error) { if (!error.stale && error.status !== 401) showToast("Выход на этом устройстве выполнен. Сервер не подтвердил отзыв сессии; она завершится по сроку действия.", true); }
  }
};
$("show-create").onclick = openAssetCreateForm;
$("cancel-create").onclick=()=>$("asset-create-dialog").close();
$("create-building").addEventListener("submit", event => submitFormAction(event,"building-create-submit",async form => {
  await api("/admin/locations/buildings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(new FormData(form).entries()))});
  form.reset(); showToast("Корпус создан"); await load(false);
}));
$("location-create-form").addEventListener("submit", event => submitFormAction(event,"location-create-submit",async () => {
  if (!locationDialogTarget) return;
  const {kind,parentId}=locationDialogTarget, isRoom=kind === "room";
  const body={name:$("location-create-name").value.trim()};
  if (isRoom) { body.responsible_name=$("location-create-responsible").value.trim()||null; body.responsible_contact=$("location-create-contact").value.trim()||null; }
  await api(isRoom ? `/admin/locations/floors/${parentId}/rooms` : `/admin/locations/buildings/${parentId}/floors`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  $("location-create-dialog").close(); showToast(isRoom ? "Кабинет добавлен" : "Этаж добавлен"); await load(false);
}));
$("location-create-cancel").onclick=()=>$("location-create-dialog").close();
async function submitAdminForm(event, action) {
  event.preventDefault();
  const form=event.currentTarget;
  if(form.dataset.busy==="true")return;
  const button=form.querySelector("button[type=submit]"), label=button.textContent;
  const error=form.querySelector(".form-error"), generation=sessionGeneration;
  form.dataset.busy="true"; button.disabled=true; button.textContent="Сохраняем…"; error.hidden=true;
  try { await action(form); }
  catch(failure) { if(generation!==sessionGeneration||failure.stale)return; error.textContent=failure.message;error.hidden=false;error.focus(); }
  finally { form.dataset.busy="false";button.disabled=false;button.textContent=label; if(generation===sessionGeneration)renderAdminAccess(); }
}
$("create-user").addEventListener("submit",(event)=>submitAdminForm(event,async(form)=>{
  const generation=sessionGeneration;
  const body=Object.fromEntries(new FormData(form).entries());body.organization_id=body.organization_id||null;
  const created=await api("/admin/users",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  form.reset();const loaded=await loadAdminAccess();
  if(generation!==sessionGeneration)return;
  if(!loaded){showToast("Учётная запись создана. Список недоступен: обновите его перед назначением прав.");return;}
  if(created.role!=="ADMIN"){$("access-user").value=created.id;renderAdminAccess();showToast("Пользователь создан. Теперь назначьте ему кабинет и права.");$("assign-user-panel").scrollIntoView({behavior:"smooth",block:"center"});$("access-scope").focus({preventScroll:true});}
  else showToast("Учётная запись администратора создана.");
}));
$("grant-location-access").addEventListener("submit",(event)=>submitAdminForm(event,async(form)=>{
  const body=Object.fromEntries(new FormData(form).entries());const [scope_type,scope_id]=body.scope.split(":");
  await api("/admin/locations/access",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:body.user_id,scope_type,scope_id,permission:body.permission})});
  showToast("Назначение сохранено");await loadAdminAccess();
}));
$("access-user").addEventListener("change",renderAdminAccess);
$("refresh-access").onclick=loadAdminAccess;
$("create-agent-credential").addEventListener("submit",(event)=>submitAdminForm(event,async()=>{
  const organizationId=state.currentUser?.organization_id||$("agent-organization").value||null;
  const credential=await api("/admin/agent-credentials",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({organization_id:organizationId})});
  $("agent-credential-username").value=credential.username;$("agent-credential-secret").value=credential.secret;
  openDialog("agent-credential-dialog", "agent-credential-username");showToast("Ключ для компьютера создан. Скопируйте его сейчас.");
  await loadAdminAccess();
}));
$("refresh-agent-credentials").onclick=loadAdminAccess;
$("refresh-agent-reenrolments").onclick=loadAdminAccess;
document.querySelectorAll(".copy-agent-credential").forEach((button)=>button.onclick=async()=>{try{await copyAgentCredential(button.dataset.field);}catch(error){showToast(error.message,true);}});
$("agent-credential-result").addEventListener("submit",()=>{$("agent-credential-username").value="";$("agent-credential-secret").value="";});
$("agent-credential-dialog").addEventListener("close",()=>{$("agent-credential-username").value="";$("agent-credential-secret").value="";});
async function downloadAssetExport(format) {
  const button=$(format==="xlsx"?"export-assets":"export-assets-pdf"), original=button.innerHTML;
  button.disabled=true;button.textContent="Формируем файл…";
  try { const blob=await apiBlob(`/admin/assets/export.${format}`),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=`assetguard-assets.${format}`;link.click();URL.revokeObjectURL(url);showToast(`Экспорт ${format.toUpperCase()} готов`); }
  catch(error){showToast(error.message,true);}
  finally{button.disabled=false;button.innerHTML=original;}
}
$("export-assets").onclick=()=>downloadAssetExport("xlsx");
$("export-assets-pdf").onclick=()=>downloadAssetExport("pdf");
function showImportError(id, error) {
  const container = $(id), detail = error.detail;
  const rows = Array.isArray(detail?.errors) ? detail.errors.slice(0, 50) : [];
  container.innerHTML = `<strong>${escapeHtml(error.message)}</strong>` + (rows.length ? `<ul>${rows.map(item => `<li>${item.page ? `Страница ${escapeHtml(item.page)}, ` : ""}строка ${escapeHtml(item.row)}: ${escapeHtml(item.message)}</li>`).join("")}</ul>${detail.error_count > rows.length ? `<p>Всего проблемных строк: ${detail.error_count}; показаны первые ${rows.length}.</p>` : ""}` : "") + '<p>Проверьте файл и повторите загрузку. При потере ответа на сохранение сначала проверьте реестр.</p>';
  container.hidden = false; container.focus();
}
function confirmAssetImport(file, format, preview) {
  const generation = sessionGeneration, dialog = $("import-preview-dialog");
  $("import-preview-file").textContent = `${file.name} · ${format.toUpperCase()} · ${(file.size/1024).toLocaleString("ru-RU", {maximumFractionDigits: 1})} КБ`;
  $("import-preview-scope").textContent = preview.scope?.organization_name ? `Область импорта: ${preview.scope.organization_name}` : "Область администратора платформы: организация берётся из каждой строки; без неё — Default Organization.";
  $("import-preview-error").hidden = true;
  const items = preview.items || preview.samples || [], selected = new Set(items.map((item, index) => item.quantity != null ? index : null).filter(index => index !== null)), pageSize = 25;
  const table = $("import-preview-samples"), search = $("import-preview-search"), selectPage = $("import-preview-select-page"), applyButton = $("apply-import-preview");
  let busy = false, saved = null, attempted = false;
  const filteredRows = () => {
    const query = search.value.trim().toLocaleLowerCase("ru"), filter = $("import-preview-filter").value;
    return items.map((item, index) => ({item, index})).filter(({item}) => (!query || [item.inventory_number, item.name, item.asset_type, item.building, item.floor, item.room].some(value => String(value || "").toLocaleLowerCase("ru").includes(query))) && (!filter || (filter === "warning" ? item.quantity == null || item.accounting_preserved || item.quantity_unverified : item.action === filter)));
  };
  const update = () => {
    const filtered = filteredRows(), pageCount = Math.max(1, Math.ceil(filtered.length/pageSize));
    state.importPreviewPage = Math.min(Math.max(state.importPreviewPage || 0, 0), pageCount-1);
    const start = state.importPreviewPage*pageSize, visible = filtered.slice(start, start+pageSize);
    const chosen = items.filter((_, index) => selected.has(index));
    $("import-preview-rows").textContent = chosen.length;
    $("import-preview-creates").textContent = chosen.filter(item => item.action !== "update").length;
    $("import-preview-updates").textContent = chosen.filter(item => item.action === "update").length;
    $("import-preview-page-info").textContent = filtered.length ? `Позиции ${start+1}–${start+visible.length} из ${filtered.length} · всего в файле ${items.length}` : `Совпадений нет · всего в файле ${items.length}`;
    $("import-preview-prev").disabled = busy || state.importPreviewPage === 0;
    $("import-preview-next").disabled = busy || state.importPreviewPage >= pageCount-1;
    const available = visible.filter(({item}) => item.quantity != null), checked = available.filter(({index}) => selected.has(index)).length;
    selectPage.checked = available.length > 0 && checked === available.length;
    selectPage.indeterminate = checked > 0 && checked < available.length;
    selectPage.disabled = busy || !available.length;
    applyButton.disabled = busy || !chosen.length;
    applyButton.textContent = busy ? "Сохраняем…" : `Импортировать ${chosen.length} позиций`;
    $("import-selection-summary").textContent = `Выбрано ${chosen.length} из ${items.length} · исключено ${items.length-chosen.length}. Поиск и страницы не меняют выбор остальных строк.`;
    table.innerHTML = visible.length ? '<table><thead><tr><th scope="col">В импорт</th><th scope="col">Строка</th><th scope="col">Инв. №</th><th scope="col">Наименование</th><th scope="col">Тип</th><th scope="col">Количество / учёт</th><th scope="col">Кабинет</th><th scope="col">Действие</th><th scope="col">OCR</th></tr></thead><tbody>' + visible.map(({item, index}) => `<tr>
      <td data-label="В импорт"><label class="import-row-choice"><input type="checkbox" data-import-row="${index}" aria-label="Импортировать строку ${index+1}" ${selected.has(index) ? "checked" : ""} ${busy || item.quantity == null ? "disabled" : ""}><span class="sr-only">Выбрать позицию</span></label></td>
      <td data-label="Строка">${item.source_page ? `стр. ${item.source_page} · ` : ""}${item.source_row || item.row || index+1}</td>
      <td data-label="Инв. №">${escapeHtml(item.inventory_number || "—")}</td><td data-label="Наименование">${escapeHtml(item.name || "—")}<small>${escapeHtml(item.organization || "")}</small></td>
      <td data-label="Тип">${escapeHtml(assetTypeLabels[item.asset_type] || item.asset_type || "—")}</td>
      <td data-label="Количество / учёт">${item.quantity == null ? "Уточните в Excel; строка исключена" : `${item.quantity} ${escapeHtml(item.unit || "шт.")}`}<small>${item.tracking_mode === "GROUPED" ? "Групповой" : "Индивидуальный"}${item.accounting_preserved ? " · сохранён остаток по акту" : ""}${item.quantity_unverified ? " · сверьте количество" : ""}</small>${item.accounting_preserved && item.source_quantity != null ? `<small>В файле: ${item.source_quantity}</small>` : ""}</td>
      <td data-label="Кабинет">${escapeHtml([item.building, item.floor, item.room].filter(Boolean).join(" · ") || "Не указан")}</td>
      <td data-label="Действие"><span class="import-action ${item.action === "update" ? "is-update" : "is-create"}">${item.action === "update" ? "Обновится" : "Новая"}</span></td><td data-label="OCR">${Number.isFinite(item.confidence) ? `${item.confidence}%` : "—"}</td></tr>`).join("") + '</tbody></table>' : '<p class="empty">' + (items.length ? "По этому запросу ничего не найдено." : "Строки для импорта не найдены.") + '</p>';
  };
  state.importPreviewPage = 0; search.value = ""; $("import-preview-filter").value = "";
  const blocked = items.filter(item => item.quantity == null).length;
  $("import-preview-note").textContent = `${(preview.source || "").toLowerCase().includes("ocr") ? "Распознано OCR: процент не гарантирует точность. Сверьте номера и количество с оригиналом." : "Сопоставление с реестром — по организации и инвентарному номеру. Снимите выбор с ненужных строк."} ${blocked ? `Не выбрано позиций без количества: ${blocked}. Исправьте их в Excel для отдельной загрузки.` : ""} Остатки и кабинеты после актов сохраняются.`;
  search.oninput = $("import-preview-filter").onchange = () => {state.importPreviewPage = 0; update();};
  $("import-preview-prev").onclick = () => {state.importPreviewPage--; update();};
  $("import-preview-next").onclick = () => {state.importPreviewPage++; update();};
  selectPage.onchange = () => {filteredRows().slice(state.importPreviewPage*pageSize, (state.importPreviewPage+1)*pageSize).filter(({item}) => item.quantity != null).forEach(({index}) => selectPage.checked ? selected.add(index) : selected.delete(index)); update();};
  table.onchange = event => {const checkbox = event.target.closest("[data-import-row]"); if (!checkbox || busy) return; const index = Number(checkbox.dataset.importRow); checkbox.checked ? selected.add(index) : selected.delete(index); update();};
  $("import-preview-form").setAttribute("aria-busy", "false");
  $("cancel-import-preview").disabled = search.disabled = $("import-preview-filter").disabled = false;
  $("import-preview-form").onsubmit = async event => {
    event.preventDefault();
    if (busy) return;
    if (event.submitter?.id === "cancel-import-preview") {dialog.close("cancel"); return;}
    if (!selected.size) return;
    busy = true; attempted = true; $("import-preview-form").setAttribute("aria-busy", "true");
    $("cancel-import-preview").disabled = search.disabled = $("import-preview-filter").disabled = true;
    $("import-preview-error").hidden = true; update();
    try {
      const form = new FormData(); form.append("file", file);
      items.forEach((_, index) => {if (!selected.has(index)) form.append("exclude_row", String(index));});
      const result = await api(`/admin/assets/import.${format}?apply=true`, {method: "POST", body: form});
      if (generation !== sessionGeneration) return;
      if (result.applied !== true) throw new Error("Сервер не подтвердил применение. Проверьте реестр перед повтором.");
      saved = {...result, excluded: items.length-selected.size, total: items.length};
      dialog.close("applied");
    } catch (error) { if (generation === sessionGeneration && !error.stale) showImportError("import-preview-error", error); }
    finally {
      busy = false;
      if (generation === sessionGeneration) {
        $("import-preview-form").setAttribute("aria-busy", "false");
        $("cancel-import-preview").disabled = search.disabled = $("import-preview-filter").disabled = false;
        update();
      }
    }
  };
  update(); dialog.returnValue = "";
  return new Promise(resolve => {dialog.addEventListener("close", () => resolve(saved || {cancelled: true, attempted}), {once: true}); openDialog("import-preview-dialog", "import-preview-heading");});
}
async function importAssetFile(file, format) {
  const generation = sessionGeneration, limit = (format === "xlsx" ? 5 : 10)*1024*1024;
  $("import-file-errors").hidden = $("import-result").hidden = true;
  if (file.size > limit) throw new Error(`Файл больше ${format === "xlsx" ? 5 : 10} МБ. Разделите ведомость на меньшие файлы.`);
  $("data-exchange-status").textContent = `Анализируем ${file.name} · ${(file.size/1024).toLocaleString("ru-RU", {maximumFractionDigits: 1})} КБ…`;
  const form = new FormData(); form.append("file", file);
  const preview = await api(`/admin/assets/import.${format}`, {method: "POST", body: form});
  $("data-exchange-status").textContent = `Проверьте ${(preview.items || preview.samples || []).length} найденных позиций. Реестр пока не изменён.`;
  const result = await confirmAssetImport(file, format, preview);
  if (generation !== sessionGeneration) return;
  if (result.cancelled) {$("data-exchange-status").textContent = result.attempted ? `Импорт ${file.name} закрыт; сохранение не подтверждено. Проверьте реестр перед повтором.` : `Импорт ${file.name} отменён. Изменения не отправлены.`; return;}
  $("data-exchange-status").textContent = `Импорт завершён: новых — ${result.creates}, обновлено — ${result.updates}, исключено — ${result.excluded}.`;
  $("import-result").innerHTML = `<span class="eyebrow">Результат импорта</span><h3>Файл обработан</h3><p>${escapeHtml(file.name)} · ${dateTime(new Date())}</p><div class="summary-lines"><div class="summary-line"><span>Новые позиции</span><strong>${result.creates}</strong></div><div class="summary-line"><span>Обновлённые позиции</span><strong>${result.updates}</strong></div><div class="summary-line"><span>Исключено из ${result.total}</span><strong>${result.excluded}</strong></div></div><p>В реестр записаны только выбранные позиции. Повторная загрузка сопоставляет существующие записи по организации и инвентарному номеру.</p><div class="actions"><a class="button-anchor" href="#devices">Открыть реестр</a><a class="button-anchor button-secondary" href="#locations">Открыть кабинеты</a></div>`;
  $("import-result").hidden = false;
  const refreshed = await load(false);
  if (!refreshed) showToast("Импорт сохранён. Повторите загрузку данных.");
}
$("import-assets").onclick = () => $("import-assets-file").click();
$("import-assets-pdf").onclick = () => $("import-assets-pdf-file").click();
async function handleAssetImportInput(event, format) {
  const input = event.target, file = input.files?.[0]; if (!file) return;
  const generation = sessionGeneration, buttons = [$("import-assets"), $("import-assets-pdf")];
  buttons.forEach(button => button.disabled = true);
  try { await importAssetFile(file, format); }
  catch (error) { if (!error.stale && generation === sessionGeneration) {$("data-exchange-status").textContent = `Не удалось обработать ${file.name}.`; showImportError("import-file-errors", error);} }
  finally { buttons.forEach(button => button.disabled = false); input.value = ""; if (generation === sessionGeneration && state.currentUser) $(format === "xlsx" ? "import-assets" : "import-assets-pdf").focus({preventScroll: true}); }
}
$("import-assets-file").onchange=(event)=>handleAssetImportInput(event,"xlsx");
$("import-assets-pdf-file").onchange=(event)=>handleAssetImportInput(event,"pdf");
$("create-asset").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget, button = form.querySelector('[type="submit"]');
  if (button.disabled) return;
  button.disabled = true; button.textContent = "Сохраняем…"; clearFormError(form);
  try {
    const body = Object.fromEntries(new FormData(form).entries());
    body.room_id = body.room_id || null; body.quantity = body.quantity || 1;
    body.category = assetCategoryForType(body.asset_type);
    await api("/admin/assets", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
    form.reset(); $("asset-create-dialog").close(); syncTrackingMode();
    showToast("Имущество добавлено в реестр"); await load(false);
  } catch (error) { showFormError(form, error.message); }
  finally { button.disabled = false; button.textContent = "Сохранить имущество"; }
});
$("link-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget, button = $("link-confirm");
  if (button.disabled || !state.linkingEndpoint || !$("link-asset").value) return;
  button.disabled = true; button.textContent = "Связываем…"; clearFormError(form);
  try {
    await api(`/admin/endpoints/${state.linkingEndpoint}/asset/${$("link-asset").value}`, {method:"POST"});
    $("link-dialog").close(); showToast("Компьютер связан с имуществом"); await load(false);
    if (state.selectedComputer) await openComputerDetail(state.selectedComputer);
  } catch (error) { showFormError(form, error.message); }
  finally { button.disabled = false; button.textContent = "Связать"; }
});
$("link-cancel").onclick = () => $("link-dialog").close();
[$("device-search"),$("device-status-filter"),$("device-category-filter"),$("device-room-filter"),$("device-change-filter"),$("device-sort")].forEach((control)=>control.addEventListener(control.type==="search"?"input":"change",()=>{state.devicePage=1;renderDevices();}));
document.querySelector('.metrics a[href="#incidents"]').addEventListener("click",clearIncidentFilters);
document.querySelectorAll("[data-device-filter]").forEach((link)=>link.addEventListener("click",()=>{state.registryView=link.dataset.deviceFilter ? "computers" : "assets";clearDeviceFilters();$("device-status-filter").value=link.dataset.deviceFilter;renderDevices();}));
[$("incident-status-filter"),$("incident-severity-filter"),$("incident-type-filter"),$("incident-room-filter"),$("incident-date-from"),$("incident-date-to")].forEach(control=>control.addEventListener("change",()=>{state.incidentPage=1;renderIncidentCenter();}));
$("incident-search").addEventListener("input",()=>{state.incidentPage=1;renderIncidentCenter();});
$("clear-incident-filters").onclick=clearIncidentFilters;
$("detail-back").onclick=()=>{$("detail").hidden=true;location.hash="devices";};
$("asset-tabs").addEventListener("click",(event)=>{const button=event.target.closest("[data-asset-tab]");if(!button||button.hidden)return;selectAssetTab(button.dataset.assetTab,true);});
$("asset-tabs").addEventListener("keydown",(event)=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;const tabs=[...document.querySelectorAll("[data-asset-tab]:not([hidden])")],current=tabs.indexOf(document.activeElement);if(current<0)return;event.preventDefault();const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(current+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;tabs[next].focus();selectAssetTab(tabs[next].dataset.assetTab,true);});
$("incident-detail-back").onclick=()=>{state.selectedIncident=null;$("incident-detail").hidden=true;location.hash="incidents";};
$("incident-decision-cancel").onclick=()=>$("incident-decision-dialog").close();
$("incident-decision-form").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;clearFormError(form);const id=state.selectedIncident,resolve=state.incidentDecisionMode==="resolve";if(!id)return;const button=$("incident-decision-submit"),comment=$("incident-decision-comment").value.trim(),classification=resolve?$("incident-decision-classification").value:"REQUIRES_INVESTIGATION";if(button.disabled)return;button.disabled=true;button.textContent="Сохраняем…";try{await api(`/admin/incidents/${id}/${resolve?"resolve":"decision"}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({classification,comment})});await load(false);$("incident-decision-dialog").close();showToast(resolve?"Решение сохранено":"Инцидент взят на проверку");if(location.hash===`#incident=${id}`)await openIncidentDetail(id,false);}catch(error){showFormError(form,error.message);}finally{button.disabled=false;button.textContent=resolve?"Сохранить решение":"Взять на проверку";}});
$("confirmation-cancel").onclick=()=>$("confirmation-dialog").close();
$("confirmation-dialog").addEventListener("cancel",(event)=>{if(confirmationBusy)event.preventDefault();});
$("confirmation-form").addEventListener("submit",async(event)=>{
  event.preventDefault();if(!confirmationAction||confirmationBusy)return;
  const action=confirmationAction, generation=sessionGeneration, button=$("confirmation-submit"), label=button.textContent;
  confirmationBusy=true;button.disabled=true;$("confirmation-cancel").disabled=true;button.textContent="Выполняем…";$("confirmation-error").hidden=true;
  try{await action($("confirmation-reason").value.trim());if(generation===sessionGeneration){$("confirmation-dialog").close();confirmationAction=null;}}
  catch(error){if(generation!==sessionGeneration||error.stale)return;$("confirmation-error").textContent=error.message;$("confirmation-error").hidden=false;showToast(error.message,true);}
  finally{confirmationBusy=false;button.disabled=false;$("confirmation-cancel").disabled=false;if(generation===sessionGeneration)button.textContent=label;}
});
$("room-tabs").addEventListener("click",(event)=>{const button=event.target.closest("[data-room-tab]");if(!button)return;state.roomTab=button.dataset.roomTab;renderRoomTab();});
$("room-detail-back").onclick=()=>{state.roomWorkspace=null;$("room-detail").hidden=true;location.hash="locations";};
$("room-edit-action").onclick=openRoomEditDialog;
$("room-vision-action").onclick=()=>launchRoomVision(state.roomWorkspace?.room.id);
$("room-inspection-action").onclick=openRoomInspectionDialog;
$("room-edit-cancel").onclick=()=>$("room-edit-dialog").close();
$("room-edit-form").addEventListener("submit", event => submitFormAction(event,"room-edit-submit",async () => {
  const roomId=state.roomWorkspace?.room.id; if (!roomId) return;
  const body={purpose:$("room-edit-purpose").value.trim()||null,responsible_name:$("room-edit-responsible").value.trim()||null,responsible_contact:$("room-edit-contact").value.trim()||null,notes:$("room-edit-notes").value.trim()||null};
  await api(`/admin/locations/rooms/${roomId}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  await load(false); await openRoomWorkspace(roomId); $("room-edit-dialog").close(); showToast("Данные кабинета сохранены");
}));
$("room-inspection-cancel").onclick=()=>$("room-inspection-dialog").close();
$("room-inspection-form").addEventListener("submit", saveRoomInspection);
$("inspection-review-back").onclick = () => { $("inspection-error").hidden = true; setInspectionStep(false); $("inspection-result-0").focus(); };
$("room-inspection-dialog").addEventListener("cancel", event => { if ($("room-inspection-submit").disabled) event.preventDefault(); });
$("import-preview-dialog").addEventListener("cancel", event => { if ($("import-preview-form").getAttribute("aria-busy") === "true") event.preventDefault(); });
$("physical-incident-cancel").onclick=()=>$("physical-incident-dialog").close();
$("physical-incident-action-select").addEventListener("change",syncPhysicalOperationFields);
$("physical-incident-quantity").addEventListener("input",syncPhysicalOperationFields);
$("physical-incident-form").addEventListener("submit", event => submitFormAction(event,"physical-incident-submit",async () => {
  const incidentId=state.physicalIncidentId,roomId=state.roomWorkspace?.room.id;
  if (!incidentId || !roomId) return;
  const action=$("physical-incident-action-select").value;
  const body={action,comment:$("physical-incident-comment").value.trim()};
  if (["MOVE","WRITE_OFF"].includes(action)) {
    body.quantity=Number($("physical-incident-quantity").value);
    body.document_number=$("physical-incident-document-number").value.trim();
    if (action === "MOVE") {
      body.destination_room_id=$("physical-incident-destination").value;
      const inventory=$("physical-incident-inventory-number").value.trim();
      if (inventory) body.destination_inventory_number=inventory;
    }
  }
  await api(`/admin/locations/physical-incidents/${incidentId}/decision`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  await load(false); $("physical-incident-dialog").close();
  if (location.hash === `#physical-incident=${incidentId}`) await openIncidentDetail(incidentId,false,true);
  else { await openRoomWorkspace(roomId); state.roomTab="incidents"; renderRoomTab(); }
  showToast(action === "INVESTIGATE" ? "Инцидент взят на проверку" : action === "MOVE" ? "Имущество перемещено, акт готов" : action === "WRITE_OFF" ? "Имущество списано, акт готов" : "Решение по инциденту сохранено");
}));
$("vision-location-room").addEventListener("change",(event)=>syncVisionAssetsForRoom(event.target.value));
$("vision-upload").addEventListener("submit",async(event)=>{event.preventDefault();const button=$("vision-run"),selectedRoomName=$("vision-location-room").selectedOptions[0]?.textContent||"Кабинет";button.disabled=true;$("vision-progress").textContent="Анализируем фото… Первый запуск может занять несколько минут.";try{const form=new FormData(event.currentTarget);const scan=await api("/admin/vision/scans",{method:"POST",body:form});state.visionRoomId=scan.room_id;const rooms=await api("/admin/vision/rooms");renderVisionRooms(rooms);await renderVisionScan(scan,selectedRoomName);await loadVisionHistory(scan.room_id);$("vision-progress").textContent=`Анализ завершён: найдено объектов — ${scan.detections.length}. Проверьте результат.`;}catch(error){$("vision-progress").textContent=error.message;showToast(error.message,true);}finally{button.disabled=!state.locations.some((building)=>building.floors.some((floor)=>floor.rooms.length));}});
$("vision-baseline").onclick=()=>{if(!state.visionScan)return;const scanId=state.visionScan.id,roomId=state.visionScan.room_id;openConfirmation({title:"Подтвердить фото-эталон",description:"Текущий результат Vision станет эталоном кабинета. Следующие проверки будут сравниваться с этим составом.",confirmLabel:"Подтвердить эталон",onConfirm:async()=>{await api(`/admin/vision/rooms/${roomId}/baseline`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scan_id:scanId})});const scan=await api(`/admin/vision/scans/${scanId}`);await renderVisionScan(scan,state.visionRooms.find((room)=>room.id===scan.room_id)?.name);await loadVisionHistory(scan.room_id);$("vision-progress").textContent="Эталон подтверждён. Следующее фото будет сравнено с ним.";showToast("Эталон помещения сохранён");}});};
$("vision-room-select").onchange=async(event)=>{state.visionRoomId=event.target.value;const room=state.visionRooms.find((item)=>item.id===state.visionRoomId);state.visionScan=room?.latest_scan||null;if(state.visionScan)await renderVisionScan(state.visionScan,room.name);await loadVisionHistory(state.visionRoomId);};
$("registry-views").addEventListener("click", event => {
  const button = event.target.closest('[data-registry-view]');
  if (!button) return;
  state.registryView = button.dataset.registryView; state.devicePage = 1; renderDevices();
});
$("overview-unlinked").onclick = () => { state.registryView="unlinked"; clearDeviceFilters(); location.hash="devices"; };
$("setup-help").onclick = () => { state.guideExpanded = !state.guideExpanded; renderSetupGuide(); };
$("link-asset").addEventListener('change', renderLinkChoice);
document.addEventListener('click', async event => {
  const button = event.target.closest('.copy-value');
  if (!button) return;
  try { await navigator.clipboard.writeText(button.dataset.value); showToast('Скопировано в буфер обмена'); }
  catch { showToast('Не удалось скопировать. Выделите значение и скопируйте вручную.',true); }
});
$("asset-create-dialog").addEventListener('cancel', event => {
  if ($("create-asset").querySelector('[type="submit"]').disabled) event.preventDefault();
});
$("collapse-navigation").onclick = () => {
  const collapsed = document.body.classList.toggle('navigation-collapsed');
  $("collapse-navigation").setAttribute('aria-expanded',String(!collapsed));
  $("collapse-navigation").setAttribute('aria-label',collapsed ? 'Развернуть навигацию' : 'Свернуть навигацию');
  $("collapse-navigation").title = collapsed ? 'Развернуть навигацию' : 'Свернуть навигацию';
};
document.querySelectorAll('#main-nav a').forEach(link => { link.title = link.textContent.trim(); });
window.addEventListener("hashchange",openRouteFromHash);
syncRoleControls();
renderAdminAccessVisibility();
if(!location.hash)history.replaceState(null,"","#overview");
openRouteFromHash();
if (token) {
  const generation = sessionGeneration;
  setLoginBusy(true, "Восстанавливаем сессию…");
  reloadWorkspace().finally(() => { if (generation === sessionGeneration) setLoginBusy(false); });
} else document.title = "Вход — AssetGuard";

for (const dialogId of ['location-create-dialog','room-edit-dialog','physical-incident-dialog']) {
  $(dialogId).addEventListener('cancel',event => {
    if ($(dialogId).querySelector('form').getAttribute('aria-busy') === 'true') event.preventDefault();
  });
}
