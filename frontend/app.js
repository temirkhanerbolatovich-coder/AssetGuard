const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("assetguard-admin-token") || "";
let state = {assets: [], endpoints: [], devices: [], changes: [], incidents: [], operations: null, locations: [], users: [], locationAccess: [], organizations: [], agentCredentials: [], currentUser: null, visionRooms: [], selectedAsset: null, linkingEndpoint: null, visionRoomId: null, visionScan: null, visionImageUrl: null, assetQrUrl: null, roomWorkspace: null, roomTab: "overview", physicalIncidentId: null};
$("token").value = token;

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
const ramBytes = (value) => value == null ? null : (Number(value) < 1048576 ? Number(value) * 1048576 : Number(value));
const statusLabels = {OK:"В норме",ATTENTION:"Требует внимания",ANOMALY:"Обнаружено расхождение",OFFLINE:"Не в сети",UNCHECKED:"Нет данных Agent",MANUAL:"Ручной учёт",WARNING:"Требует внимания",NOT_CHECKED:"Не проверено",ONLINE:"В норме",REQUIRES_VERIFICATION:"Требует проверки",IDENTITY_CONFLICT:"Конфликт идентификации",OPEN:"Открыто",UNDER_REVIEW:"На проверке",RESOLVED:"Закрыто",DISMISSED:"Не подтверждено",ACTIVE:"Активен",WRITTEN_OFF:"Списан",REVOKED:"Отозван"};
const categoryLabels = {IT:"IT-оборудование",FURNITURE:"Мебель",SPORTS:"Спортинвентарь",EDUCATIONAL:"Учебное оборудование",OTHER:"Другое имущество"};
const componentLabels = {RAM:"Оперативная память",STORAGE:"Физические накопители",DRIVE:"Разделы дисков",CONTROLLER:"Контроллеры",CPU:"Процессор",GPU:"Видеокарта",MOTHERBOARD:"Материнская плата",NETWORK:"Сетевые интерфейсы",MONITOR:"Мониторы",ENDPOINT:"Устройство"};
const eventLabels = {COMPONENT_ADDED:"Компонент добавлен",COMPONENT_REMOVED:"Компонент отсутствует",COMPONENT_CHANGED:"Характеристики изменились",COMPONENT_REPLACED:"Компонент заменён",HOSTNAME_CHANGED:"Изменилось имя компьютера",DEVICE_IDENTITY_CHANGED:"Изменился идентификатор устройства",INVENTORY_COMPLETED:"Инвентаризация завершена",BASELINE_ACCEPTED:"Эталон подтверждён",HARDWARE_CHANGE_DETECTED:"Обнаружено изменение оборудования",INCIDENT_CREATED:"Создано обращение",INCIDENT_CLASSIFIED:"Обращение классифицировано",INCIDENT_RESOLVED:"Обращение закрыто",ASSET_CREATED:"Актив добавлен",ASSET_UPDATED:"Карточка обновлена",ASSET_MOVED:"Имущество перемещено",ASSET_WRITTEN_OFF:"Имущество списано",ENDPOINT_LINKED:"Устройство связано с активом",ENDPOINT_UNLINKED:"Устройство отвязано",VISION_SCAN_COMPLETED:"Фотопроверка завершена",PHYSICAL_INSPECTION_COMPLETED:"Физический обход завершён",PHYSICAL_INCIDENT_CREATED:"Создан физический инцидент",PHYSICAL_INCIDENT_CLASSIFIED:"Физический инцидент взят на проверку",PHYSICAL_INCIDENT_RESOLVED:"Физический инцидент закрыт"};
const inspectionLabels = {PRESENT:"На месте",MISSING:"Отсутствует",DAMAGED:"Повреждено"};
const physicalActionLabels = {INVESTIGATE:"Дополнительная проверка",MOVE:"Перемещение",REPAIR:"Ремонт",WRITE_OFF:"Списание",FALSE_POSITIVE:"Расхождение не подтвердилось"};
const classForStatus = (value) => ({OK:"ok",ONLINE:"ok",ACTIVE:"ok",RESOLVED:"ok",ATTENTION:"attention",WARNING:"warning",OPEN:"warning",UNDER_REVIEW:"warning",ANOMALY:"anomaly",IDENTITY_CONFLICT:"danger",REVOKED:"danger",OFFLINE:"offline",UNCHECKED:"unchecked",NOT_CHECKED:"unchecked",REQUIRES_VERIFICATION:"unchecked"}[value] || "neutral");
const pill = (value) => `<span class="status-pill ${classForStatus(value)}">${escapeHtml(statusLabels[value] || value || "Не проверено")}</span>`;

function showToast(message, error = false) {
  const toast = $("toast"); toast.textContent = message; toast.className = `toast${error ? " error" : ""}`; toast.hidden = false;
  clearTimeout(showToast.timer); showToast.timer = setTimeout(() => { toast.hidden = true; }, 3500);
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {...options.headers, "X-AssetGuard-Admin-Token": token}});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(response.status === 401 ? "Не удалось войти. Проверьте логин, пароль или токен." : body.detail || `Ошибка API: ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}
async function apiBlob(path) {
  const response = await fetch(path, {headers: {"X-AssetGuard-Admin-Token": token}});
  if (!response.ok) throw new Error("Не удалось загрузить изображение результата.");
  return response.blob();
}
async function copyAgentCredential(fieldId) {
  const field=$(fieldId), value=field.value;
  if(!value) return;
  try { await navigator.clipboard.writeText(value); }
  catch { field.focus(); field.select(); if(!document.execCommand("copy")) throw new Error("Не удалось скопировать. Выделите значение и скопируйте вручную."); }
  showToast("Скопировано в буфер обмена");
}
function deviceStatus(endpoint, asset = null) {
  if (!endpoint && asset && asset.category !== "IT") return "MANUAL";
  if (!endpoint?.current_snapshot) return "UNCHECKED";
  if (endpoint.status === "IDENTITY_CONFLICT") return "ANOMALY";
  if (endpoint.status !== "ONLINE") return "UNCHECKED";
  if (endpoint.open_changes > 0 || endpoint.open_incidents > 0) return "ATTENTION";
  return "OK";
}
function locationLabel(item) { return [item.organization,item.building,item.floor && `этаж ${item.floor}`,item.room && `каб. ${item.room}`].filter(Boolean).join(" · "); }
function buildDevices() {
  const linkedEndpointIds = new Set();
  const devices = state.assets.map((asset) => {
    const endpoint = asset.endpoint;
    if (endpoint) linkedEndpointIds.add(endpoint.id);
    return {kind:"asset",assetId:asset.id,endpointId:endpoint?.id || null,name:asset.name,inventoryNumber:asset.inventory_number,hostname:endpoint?.hostname || null,building:asset.building,floor:asset.floor,room:asset.room,organization:asset.organization,category:asset.category,trackingMode:asset.tracking_mode,quantity:asset.quantity,unit:asset.unit,endpoint,status:deviceStatus(endpoint,asset)};
  });
  state.endpoints.filter((endpoint) => !linkedEndpointIds.has(endpoint.id)).forEach((endpoint) => devices.push({kind:"endpoint",assetId:null,endpointId:endpoint.id,name:endpoint.hostname || "Непривязанное устройство",inventoryNumber:null,hostname:endpoint.hostname,building:null,floor:null,room:null,organization:null,endpoint,status:deviceStatus(endpoint)}));
  state.devices = devices;
}
function deviceForEndpoint(endpointId) { return state.devices.find((device) => device.endpointId === endpointId); }
function incidentLabel(incident, change = null) {
  const parts = (incident?.title || "").split(":");
  const component = componentLabels[change?.component_type || parts[0]] || change?.component_type || parts[0] || "Оборудование";
  const event = eventLabels[change?.type || parts[1]?.trim()] || change?.type || parts[1]?.trim() || "обнаружено изменение";
  return `${component}: ${event}`;
}
function renderIncidentSpotlight() {
  const incident = state.incidents.find((item) => ["OPEN","UNDER_REVIEW"].includes(item.status)) || state.incidents[0];
  const body = $("incident-spotlight-body"), status = $("incident-spotlight-status");
  if (!incident) {
    status.textContent = "Нет инцидентов"; status.className = "status-pill ok";
    body.innerHTML = state.endpoints.length ? '<div class="spotlight-empty"><div><strong>Новых расхождений пока нет</strong><p>Если состав компьютера изменится относительно подтверждённого эталона, здесь появятся причина и доказательства.</p></div><a href="#agent-workflow">Как это работает →</a></div>' : '<div class="spotlight-empty"><div><strong>Компьютеры с Agent пока не подключены</strong><p>После первого отчёта и подтверждения эталона AssetGuard сможет показывать реальные изменения.</p></div><a href="#agent-workflow">Посмотреть, как подключить →</a></div>';
    return;
  }
  const device = deviceForEndpoint(incident.endpoint_id), change = state.changes.find((item) => item.id === incident.change_event_id);
  status.outerHTML = pill(incident.status); const newStatus = $("incident-spotlight").querySelector(".status-pill"); if (newStatus) newStatus.id = "incident-spotlight-status";
  const comparison = change ? `<div class="spotlight-comparison"><span><small>Было</small>${escapeHtml(componentSummary(change.component_type,change.evidence?.previous))}</span><b>→</b><span><small>Стало</small>${escapeHtml(componentSummary(change.component_type,change.evidence?.current))}</span></div>` : "";
  const action = device?.assetId ? `<button class="open-device" data-id="${device.assetId}">Открыть карточку и доказательства</button>` : device ? `<button class="link-endpoint button-secondary" data-id="${device.endpointId}" data-name="${escapeHtml(device.hostname || "")}">Сначала связать с активом</button>` : "";
  body.innerHTML = `<div class="spotlight-main"><div><strong>${escapeHtml(incidentLabel(incident,change))}</strong><p>${escapeHtml(device?.name || "Устройство")} · Agent сообщил ${relativeTime(incident.created_at)}</p></div>${action}</div>${comparison}<ol class="incident-path"><li class="done">Agent прислал снимок</li><li class="done">AssetGuard сравнил с эталоном</li><li class="active">Создан инцидент</li><li>Решение оператора</li></ol>`;
}
function renderDashboard() {
  const devices = state.devices;
  renderSetupGuide();
  const online = devices.filter((item) => item.status === "OK").length;
  const attention = devices.filter((item) => ["ATTENTION","ANOMALY"].includes(item.status));
  const unchecked = devices.filter((item) => item.status === "UNCHECKED");
  $("devices-count").textContent = state.assets.length; $("online-count").textContent = online; $("attention-count").textContent = attention.length; $("unchecked-count").textContent = unchecked.length;
  const banner = $("attention-banner");
  if (!devices.length) {
    banner.className = "attention-banner is-loading"; banner.innerHTML = '<span class="attention-icon">1</span><div><strong>Начните с настройки школы</strong><p>Создайте кабинеты и добавьте имущество. Agent подключайте, если нужно автоматически следить за компьютерами.</p></div>';
  } else if (!attention.length && !unchecked.length) {
    banner.className = "attention-banner ok"; banner.innerHTML = '<span class="attention-icon">✓</span><div><strong>Новых проблем не обнаружено</strong><p>У компьютеров с Agent нет открытых изменений. Остальное имущество учитывается в реестре вручную.</p></div>';
  } else {
    banner.className = "attention-banner"; banner.innerHTML = `<span class="attention-icon">!</span><div><strong>${attention.length ? `${attention.length} ${attention.length === 1 ? "компьютер требует" : "компьютера требуют"} внимания` : "Есть компьютеры без данных Agent"}</strong><p>${unchecked.length ? `Без отчёта или эталона: ${unchecked.length}. ` : ""}Откройте карточку компьютера — там будет причина и следующий шаг.</p></div>`;
  }
  const priority = [...attention, ...unchecked].slice(0, 6);
  $("attention-badge").textContent = priority.length ? String(priority.length) : "Всё спокойно"; $("attention-badge").className = `status-pill ${priority.length ? "warning" : "ok"}`;
  $("attention-list").innerHTML = priority.length ? priority.map((item) => `<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.room || item.hostname || "Расположение не указано")} · ${escapeHtml(statusLabels[item.status])}${item.endpoint?.open_changes ? ` · изменений: ${item.endpoint.open_changes}` : ""}</small></div>${item.assetId ? `<button class="open-device button-secondary" data-id="${item.assetId}">Открыть</button>` : `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать</button>`}</div>`).join("") : '<p class="empty">Ничего не требует внимания.</p>';
  const activity = state.changes.slice(0, 5);
  $("activity-list").innerHTML = activity.length ? activity.map((change) => { const device = deviceForEndpoint(change.endpoint_id); return `<article><time>${dateTime(change.detected_at)}</time><div><b>${escapeHtml(eventLabels[change.type] || change.type)}</b><p>${escapeHtml(device?.name || "Устройство")} · ${escapeHtml(componentLabels[change.component_type] || change.component_type)}</p></div></article>`; }).join("") : '<p class="empty">Изменений не обнаружено. Последние проверки завершились штатно.</p>';
  const latest = devices.map((item) => item.endpoint?.last_seen_at).filter(Boolean).sort().at(-1); $("last-activity").textContent = latest ? `Последняя проверка ${relativeTime(latest)}` : "Проверок пока нет";
  const locations = new Map(); state.assets.forEach((item) => { const key = locationLabel(item) || "Расположение не указано"; locations.set(key, (locations.get(key) || 0) + 1); });
  $("location-summary").innerHTML = [...locations.entries()].map(([name,count]) => `<span class="tag">${escapeHtml(name)} <strong>${count}</strong></span>`).join("") || '<p class="empty">Создайте кабинеты в разделе «Кабинеты», затем выберите их в карточках имущества.</p>';
  const full = state.endpoints.filter((item) => item.current_snapshot?.type === "FULL").length;
  $("inventory-summary").innerHTML = state.endpoints.length ? `<div class="summary-line"><span>Компьютеры с отчётом</span><strong>${state.endpoints.filter((item) => item.current_snapshot).length} из ${state.endpoints.length}</strong></div><div class="summary-line"><span>Полная инвентаризация</span><strong>${full}</strong></div><div class="summary-line"><span>Последняя активность Agent</span><strong>${latest ? relativeTime(latest) : "—"}</strong></div>` : '<p class="empty">Agent пока не подключён. Мебель и прочее имущество учитываются в реестре отдельно.</p>';
  renderIncidentSpotlight();
  const reporting = state.endpoints.filter((item) => item.last_seen_at).length;
  $("agent-online-badge").textContent = state.endpoints.length ? `${reporting} компьютеров с Agent на связи` : "Agent не подключён"; $("agent-online-badge").className = `status-pill ${reporting ? "ok" : "neutral"}`;
  $("agent-last-signal").textContent = latest ? `Инвентаризация получена ${relativeTime(latest)}` : "Ожидаем данные Agent";
  $("agent-proof-text").textContent = latest ? `${dateTime(latest)} · отчёт принят, нормализован и сохранён в истории.` : "После первой отправки здесь появится фактическое время последней инвентаризации.";
  bindDynamicActions();
}
function renderSetupGuide() {
  const guide = $("setup-guide");
  if (!state.currentUser || state.currentUser.role !== "ADMIN") { guide.hidden = true; return; }
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
  guide.hidden = false;
}
function renderOperations(operations) {
  const status = $("operations-status"), summary = $("operations-summary");
  if (!operations) { status.textContent = "Нет данных"; status.className = "status-pill neutral"; summary.innerHTML = '<p class="empty">Операционные данные недоступны.</p>'; return; }
  const failed = Number(operations.ingest?.failed || 0), offline = Number(operations.agents?.offline || 0) + Number(operations.agents?.stale || 0), conflicts = Number(operations.agents?.identity_conflicts || 0);
  const attention = failed + offline + conflicts;
  status.textContent = attention ? "Требует внимания" : "В норме"; status.className = `status-pill ${attention ? "warning" : "ok"}`;
  summary.innerHTML = [
    ["Agent на связи", `${operations.agents?.online || 0} из ${operations.agents?.total || 0}`],
    ["Нет связи / устарели", offline],
    ["Ошибки приёма данных", failed],
    ["Конфликты идентификации", conflicts],
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
  $("room-tab-content").innerHTML=html;
  document.querySelectorAll(".open-room-asset").forEach((button)=>button.onclick=()=>{$("room-detail").hidden=true;detail(button.dataset.id);});
  document.querySelectorAll(".room-vision-launch").forEach((button)=>button.onclick=()=>launchRoomVision(workspace.room.id));
  document.querySelectorAll(".room-inspection-launch").forEach((button)=>button.onclick=openRoomInspectionDialog);
  document.querySelectorAll(".physical-incident-action").forEach((button)=>button.onclick=()=>openPhysicalIncidentDialog(button.dataset.id));
  document.querySelectorAll(".physical-incident-act").forEach((button)=>button.onclick=()=>downloadPhysicalIncidentAct(button.dataset.id,button.dataset.number));
}
async function openRoomWorkspace(roomId) {
  $("room-detail").hidden=false; $("room-detail-title").textContent="Загрузка кабинета…"; $("room-tab-content").innerHTML='<div class="skeleton"></div>';
  try {
    const workspace=await api(`/admin/locations/rooms/${roomId}/workspace`); state.roomWorkspace=workspace; state.roomTab="overview";
    $("room-detail-title").textContent=`Кабинет ${workspace.room.name}`; $("room-detail-path").textContent=[workspace.path.building,workspace.path.floor&&`этаж ${workspace.path.floor}`,workspace.room.purpose].filter(Boolean).join(" · ");
    $("room-edit-action").hidden=state.currentUser?.role!=="ADMIN"; $("room-vision-action").hidden=state.currentUser?.role!=="ADMIN"; $("room-inspection-action").hidden=!canEditRoom(workspace.room.id)||!workspace.inventory.assets.length;
    const attention=workspace.incidents.length||(workspace.physical_incidents||[]).some((item)=>["OPEN","UNDER_REVIEW"].includes(item.status))||workspace.agents.some((item)=>item.status!=="ONLINE")||workspace.vision?.latest_scan?.status==="WARNING"; $("room-detail-state").textContent=attention?"Требует внимания":"В норме"; $("room-detail-state").className=`status-pill ${attention?"warning":"ok"}`;
    renderRoomTab(); $("room-detail").scrollIntoView({behavior:"smooth",block:"start"});
  } catch(error) { $("room-detail").hidden=true; showToast(error.message,true); }
}
function openRoomEditDialog() {
  const room=state.roomWorkspace?.room;if(!room)return;
  $("room-edit-purpose").value=room.purpose||"";$("room-edit-responsible").value=room.responsible_name||"";$("room-edit-contact").value=room.responsible_contact||"";$("room-edit-notes").value=room.notes||"";
  $("room-edit-dialog").showModal();$("room-edit-purpose").focus();
}
function openRoomInspectionDialog() {
  const workspace=state.roomWorkspace;if(!workspace||!canEditRoom(workspace.room.id))return;
  if(!workspace.inventory.assets.length){showToast("Сначала добавьте имущество в кабинет",true);return;}
  $("room-inspection-comment").value="";
  $("room-inspection-items").innerHTML=workspace.inventory.assets.map((asset)=>`<article class="inspection-item" data-asset="${asset.id}" data-quantity="${asset.quantity}"><div class="inspection-item-title"><strong>${escapeHtml(asset.name)}</strong><small>${escapeHtml(asset.inventory_number)} · ${asset.quantity} ${escapeHtml(asset.unit)}</small></div><label>Результат<select class="inspection-result-input"><option value="PRESENT">На месте</option><option value="MISSING">Отсутствует</option><option value="DAMAGED">Повреждено</option></select></label><label class="inspection-affected" hidden>Проблемных единиц<input class="inspection-affected-input" type="number" min="1" max="${asset.quantity}" value="1"></label><label>Комментарий<input class="inspection-item-comment" maxlength="2000" placeholder="Необязательно"></label></article>`).join("");
  $("room-inspection-items").querySelectorAll(".inspection-result-input").forEach((select)=>select.onchange=()=>{const item=select.closest(".inspection-item"),affected=item.querySelector(".inspection-affected"),input=item.querySelector(".inspection-affected-input"),present=select.value==="PRESENT";affected.hidden=present;input.disabled=present;});
  $("room-inspection-dialog").showModal();$("room-inspection-items").querySelector("select")?.focus();
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
  $("physical-incident-dialog").showModal();$("physical-incident-action-select").focus();
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
  select.innerHTML='<option value="">Не привязывать к устройству</option>'+assets.map((asset)=>`<option value="${asset.id}">${escapeHtml(asset.name)} · ${escapeHtml(asset.inventory_number)}</option>`).join("");
  if(assets.some((asset)=>asset.id===previous))select.value=previous;
}
function launchRoomVision(roomId) {
  if(!roomId||state.currentUser?.role!=="ADMIN")return;
  $("vision-location-room").value=roomId;syncVisionAssetsForRoom(roomId);location.hash="vision";$("vision").scrollIntoView({behavior:"smooth",block:"start"});$("vision-file").focus({preventScroll:true});
}
function renderLocations(locations) {
  state.locations=locations;
  const canManage=state.currentUser?.role==="ADMIN";
  $("location-tree").innerHTML=locations.length ? locations.map((building)=>`<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(building.name)}</strong><small>${escapeHtml(locationContact(building)||"Ответственный не назначен")}</small>${building.floors.length ? building.floors.map((floor)=>`<div class="location-floor"><b>Этаж ${escapeHtml(floor.name)}</b> ${canManage?`<button class="button-link add-room" data-floor="${floor.id}">+ кабинет</button>`:""}${floor.rooms.length ? floor.rooms.map((room)=>`<div class="location-room"><span>каб. ${escapeHtml(room.name)}${room.purpose?` · ${escapeHtml(room.purpose)}`:""}</span><small>${room.asset_count} активов · ${escapeHtml(locationContact(room)||"ответственный не назначен")}</small><button class="button-link room-report" data-room="${room.id}">Открыть кабинет</button></div>`).join("") : '<p class="empty">Кабинетов пока нет.</p>'}</div>`).join("") : '<p class="empty">Этажей пока нет.</p>'}${canManage?`<button class="button-link add-floor" data-building="${building.id}">+ этаж</button>`:""}</div></div>`).join("") : '<p class="empty">Структура пока не создана. Добавьте корпус справа, затем создайте для него этажи и кабинеты.</p>';
  document.querySelectorAll(".add-floor").forEach((button)=>button.onclick=()=>openLocationDialog("floor",button.dataset.building));
  document.querySelectorAll(".add-room").forEach((button)=>button.onclick=()=>openLocationDialog("room",button.dataset.floor));
  document.querySelectorAll(".room-report").forEach((button)=>button.onclick=()=>openRoomWorkspace(button.dataset.room));
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
  $("location-create-form").reset(); $("location-create-dialog").showModal(); $("location-create-name").focus();
}
function locationScopes() {
  const scopes=[];
  state.locations.forEach((building)=>{scopes.push({type:"BUILDING",id:building.id,organization_id:building.organization_id,label:`Корпус · ${building.name}`});building.floors.forEach((floor)=>{scopes.push({type:"FLOOR",id:floor.id,organization_id:building.organization_id,label:`${building.name} · этаж ${floor.name}`});floor.rooms.forEach((room)=>scopes.push({type:"ROOM",id:room.id,organization_id:building.organization_id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`}));});});
  return scopes;
}
function userRoleLabel(role) { return ({ADMIN:"Администратор школы",LOCATION_MANAGER:"Менеджер локации",INVENTORY_CLERK:"Ответственный за инвентаризацию",VIEWER:"Наблюдатель"})[role]||role; }
function renderAdminAccessVisibility() {
  const signedIn=Boolean(state.currentUser), isAdmin=state.currentUser?.role==="ADMIN";
  $("location-access-nav").hidden=!signedIn; $("location-access-shortcut").hidden=!signedIn; $("location-access").hidden=!signedIn;
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
    const status=revoked?"REVOKED":bound?"ONLINE":"ACTIVE";
    return `<div class="credential-row"><div><strong>${escapeHtml(item.username)}</strong><small>${connection} · создан ${escapeHtml(dateTime(item.issued_at))}${item.revoked_at?` · отозван ${escapeHtml(dateTime(item.revoked_at))}`:""}</small></div>${pill(status)}${!revoked?`<button type="button" class="button-secondary revoke-agent-credential" data-id="${item.id}">Отозвать ключ</button>`:""}</div>`;
  }).join("");
  $("agent-credentials-list").innerHTML=rows||'<p class="empty">Ключей пока нет. Создайте первый перед установкой Agent.</p>';
  // A bootstrap administrator may legitimately create a platform-scoped key before
  // the first school is configured; tenant administrators are scoped automatically.
  $("create-agent-credential").querySelector("button[type=submit]").disabled=false;
  document.querySelectorAll(".revoke-agent-credential").forEach((button)=>button.onclick=async()=>{if(!confirm("Отозвать ключ? Этот компьютер больше не сможет отправлять инвентаризацию."))return;try{await api(`/admin/agent-credentials/${button.dataset.id}/revoke`,{method:"POST"});showToast("Ключ Agent отозван");await loadAdminAccess();}catch(error){showToast(error.message,true);}});
}
function syncRoleControls() {
  const user=state.currentUser, isAdmin=user?.role==="ADMIN", editableRooms=new Set(user?.editable_room_ids||[]), canEditAssets=isAdmin||editableRooms.size>0;
  $("room-edit-action").hidden=!isAdmin;$("room-vision-action").hidden=!isAdmin;$("room-inspection-action").hidden=!state.roomWorkspace||!canEditRoom(state.roomWorkspace.room.id)||!state.roomWorkspace.inventory.assets.length;
  $("show-create").hidden=!canEditAssets;
  if(!canEditAssets)$("create-asset").hidden=true;
  ["export-assets","export-assets-pdf","import-assets","import-assets-file","import-assets-pdf","import-assets-pdf-file","create-building","vision-upload","vision-baseline"].forEach((id)=>$(id).hidden=!isAdmin);
  $("registry-tools").hidden=!isAdmin;
  const assetOrganizationId=user?.organization_id||state.organizations[0]?.id;
  const rooms=state.locations.filter((building)=>!assetOrganizationId||building.organization_id===assetOrganizationId).flatMap((building)=>building.floors.flatMap((floor)=>floor.rooms.map((room)=>({id:room.id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`})))).filter((room)=>isAdmin||editableRooms.has(room.id));
  const roomSelect=$("create-asset-room");
  roomSelect.innerHTML=`<option value="" ${isAdmin?"":"disabled selected"}>${rooms.length?"Выберите кабинет из структуры школы":isAdmin?"Кабинеты ещё не созданы":"Вам пока не назначен кабинет"}</option>`+rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join("");
  roomSelect.required=!isAdmin;
  roomSelect.disabled=!rooms.length;
  $("asset-tracking-mode").dispatchEvent(new Event("change"));
}
function canEditAsset(asset) { return state.currentUser?.role==="ADMIN"||Boolean(asset?.room_id&&state.currentUser?.editable_room_ids?.includes(asset.room_id)); }
function renderAdminAccess() {
  const allScopes=locationScopes(), scopeLabels=new Map(allScopes.map((item)=>[`${item.type}:${item.id}`,item.label]));
  $("user-organization").innerHTML=state.organizations.map((item)=>`<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")||'<option value="">Сначала создайте организацию</option>';
  const currentUserId=$("access-user").value;
  $("access-user").innerHTML=state.users.filter((item)=>item.role!=="ADMIN").map((item)=>`<option value="${item.id}">${escapeHtml(item.username)} · ${escapeHtml(userRoleLabel(item.role))}</option>`).join("")||'<option value="">Создайте пользователя</option>';
  if(state.users.some((item)=>item.id===currentUserId))$("access-user").value=currentUserId;
  const grantUser=state.users.find((item)=>item.id===$("access-user").value), allowedScopes=allScopes.filter((item)=>!grantUser?.organization_id||item.organization_id===grantUser.organization_id);
  $("access-scope").innerHTML=allowedScopes.map((item)=>`<option value="${item.type}:${item.id}">${escapeHtml(item.label)}</option>`).join("")||'<option value="">Для сотрудника пока нет доступных локаций</option>';
  const accessRows=state.locationAccess.map((item)=>`<div class="access-row"><div><strong>${escapeHtml(item.username)}</strong><small>${escapeHtml(userRoleLabel(state.users.find((user)=>user.id===item.user_id)?.role||"Сотрудник"))} · ${escapeHtml(scopeLabels.get(`${item.scope_type}:${item.scope_id}`)||"Локация удалена")}</small></div><span class="status-pill ${item.permission==="EDITOR"?"warning":"neutral"}">${item.permission==="EDITOR"?"Редактирование":"Только просмотр"}</span><button type="button" class="button-secondary revoke-location-access" data-id="${item.id}">Отозвать</button></div>`).join("");
  const withoutAccess=state.users.filter((user)=>user.role!=="ADMIN"&&!state.locationAccess.some((item)=>item.user_id===user.id));
  $("location-access-list").innerHTML=accessRows+(withoutAccess.length?`<p class="access-unassigned"><strong>Пока нет назначения:</strong> ${withoutAccess.map((user)=>escapeHtml(user.username)).join(", ")} — эти пользователи не видят реестр.</p>`:"")||'<p class="empty">Назначений пока нет. Сотрудники без назначения не имеют доступа к локациям.</p>';
  document.querySelectorAll(".revoke-location-access").forEach((button)=>button.onclick=async()=>{if(!confirm("Отозвать доступ этого сотрудника к локации?"))return;try{await api(`/admin/locations/access/${button.dataset.id}`,{method:"DELETE"});showToast("Доступ отозван");await loadAdminAccess();}catch(error){showToast(error.message,true);}});
  const grantButton=$("grant-location-access").querySelector("button[type=submit]"), createButton=$("create-user").querySelector("button[type=submit]");
  if(grantButton)grantButton.disabled=!state.users.some((user)=>user.role!=="ADMIN")||!allowedScopes.length;
  if(createButton)createButton.disabled=!state.organizations.length;
  $("user-organization-hint").hidden=Boolean(state.organizations.length);
}
async function loadAdminAccess() {
  renderAdminAccessVisibility();
  if(state.currentUser?.role!=="ADMIN")return;
  $("access-load-error").hidden=true;
  try { const [users,locationAccess,organizations,agentCredentials]=await Promise.all([api("/admin/users"),api("/admin/locations/access"),api("/admin/locations/organizations"),api("/admin/agent-credentials")]);state={...state,users,locationAccess,organizations,agentCredentials};renderAdminAccess();renderAgentCredentials();syncRoleControls(); }
  catch(error) { $("access-load-error").hidden=false;$("access-load-error").textContent=`Не удалось загрузить управление пользователями: ${error.message}. Проверьте вход именно под администратором школы.`; }
}
function hardwareBrief(endpoint) {
  const summary = endpoint?.hardware_summary; if (!summary) return "Нет данных";
  return [summary.ram_bytes ? `${bytes(summary.ram_bytes)} RAM` : null, summary.storage_devices ? `${summary.storage_devices} накоп.` : null, summary.cpu].filter(Boolean).join(" · ") || "Состав не определён";
}
function filteredDevices() {
  const query = $("device-search").value.trim().toLocaleLowerCase("ru"); const status = $("device-status-filter").value; const category = $("device-category-filter").value; const room = $("device-room-filter").value; const changed = $("device-change-filter").checked;
  const result = state.devices.filter((item) => {
    const haystack = [item.name,item.inventoryNumber,item.hostname,item.building,item.floor,item.room,item.organization].filter(Boolean).join(" ").toLocaleLowerCase("ru");
    const matchesStatus = !status || item.status === status || (status === "ATTENTION" && item.status === "ANOMALY");
    return (!query || haystack.includes(query)) && matchesStatus && (!category || item.category === category) && (!room || item.room === room) && (!changed || (item.endpoint?.open_changes || 0) > 0);
  });
  const sort = $("device-sort").value;
  return result.sort((a,b) => sort === "name" ? a.name.localeCompare(b.name,"ru") : sort === "attention" ? (["ANOMALY","ATTENTION","UNCHECKED","OK"].indexOf(a.status) - ["ANOMALY","ATTENTION","UNCHECKED","OK"].indexOf(b.status)) : (new Date(b.endpoint?.last_seen_at || 0) - new Date(a.endpoint?.last_seen_at || 0)));
}
function renderDevices() {
  const rooms = [...new Set(state.devices.map((item) => item.room).filter(Boolean))].sort(); const selectedRoom = $("device-room-filter").value;
  $("device-room-filter").innerHTML = '<option value="">Все кабинеты</option>' + rooms.map((room) => `<option value="${escapeHtml(room)}">${escapeHtml(room)}</option>`).join(""); $("device-room-filter").value = rooms.includes(selectedRoom) ? selectedRoom : "";
  const devices = filteredDevices();
  const activeFilters = Number(Boolean($("device-search").value.trim())) + Number(Boolean($("device-status-filter").value)) + Number(Boolean($("device-category-filter").value)) + Number(Boolean($("device-room-filter").value)) + Number($("device-change-filter").checked);
  $("device-active-filter-count").hidden=!activeFilters; $("device-active-filter-count").textContent=activeFilters || "";
  const empty = state.devices.length ? `<div class="empty-state"><strong>По этим условиям ничего не найдено</strong><p>Измените поиск или сбросьте фильтры, чтобы увидеть остальные записи.</p><button id="empty-reset" class="button-secondary" type="button">Сбросить фильтры</button></div>` : state.currentUser?.role === "ADMIN" ? `<div class="empty-state"><strong>Реестр пока пуст</strong><p>Загрузите ведомость Excel/PDF или внесите первую запись. Установленные Agent-компьютеры появятся здесь автоматически.</p><button id="empty-add" type="button">Добавить имущество</button> <button id="empty-import" class="button-secondary" type="button">Открыть импорт</button></div>` : `<div class="empty-state"><strong>В доступных вам кабинетах пока нет записей</strong><p>Если вы ожидали увидеть имущество, попросите администратора проверить назначение кабинета.</p></div>`;
  $("assets").innerHTML = devices.length ? devices.map((item) => {
    const lastCheck = item.trackingMode === "GROUPED" ? `${item.quantity} ${item.unit || "шт."}` : !item.endpoint && item.category !== "IT" ? "Ручной учёт" : relativeTime(item.endpoint?.last_seen_at);
    const hardwareSummary = item.trackingMode === "GROUPED" ? "Групповой учёт" : item.endpoint ? hardwareBrief(item.endpoint) : item.category === "IT" ? "Agent не подключён" : "Без Agent — физическое имущество";
    return `<tr class="device-row" data-asset-id="${item.assetId || ""}"><td data-label="Устройство"><div class="device-name">${item.assetId ? `<button class="device-open-link open-device" data-id="${item.assetId}">${escapeHtml(item.name)}</button>` : `<strong>${escapeHtml(item.name)}</strong>`}<small>${escapeHtml([item.inventoryNumber,item.hostname].filter(Boolean).join(" · ") || (item.kind === "endpoint" ? "Нужно связать с записью учёта" : "Инвентарный номер не задан"))}</small></div></td><td data-label="Расположение">${escapeHtml(locationLabel(item) || "Не указано")}</td><td data-label="Состояние">${pill(item.status)}${item.endpoint?.open_changes ? `<small>${item.endpoint.open_changes} откр. изм.</small>` : ""}</td><td data-label="Последняя проверка"><strong>${escapeHtml(lastCheck)}</strong><small>${escapeHtml(categoryLabels[item.category] || (item.kind === "endpoint" ? "Компьютер Agent" : "Имущество"))}</small></td><td data-label="Оборудование"><span class="hardware-brief">${escapeHtml(hardwareSummary)}</span></td><td data-label="Действие">${item.assetId ? `<button class="row-action open-device" data-id="${item.assetId}">Открыть карточку</button>` : `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать с имуществом</button>`}</td></tr>`;
  }).join("") : `<tr><td colspan="6">${empty}</td></tr>`;
  $("device-result-count").textContent = `Показано ${devices.length} из ${state.devices.length}`;
  document.querySelectorAll("tr.device-row[data-asset-id]").forEach((row) => { if (row.dataset.assetId) row.onclick = () => detail(row.dataset.assetId); }); bindDynamicActions();
  $("empty-add")?.addEventListener("click", openAssetCreateForm);
  $("empty-import")?.addEventListener("click", () => { $("registry-tools").open=true; $("registry-tools").scrollIntoView({behavior:"smooth",block:"center"}); });
  $("empty-reset")?.addEventListener("click", clearDeviceFilters);
}
function clearDeviceFilters() { $("device-search").value=""; $("device-status-filter").value=""; $("device-category-filter").value=""; $("device-room-filter").value=""; $("device-change-filter").checked=false; renderDevices(); }
function openAssetCreateForm() { const form=$("create-asset"); form.hidden=false; form.scrollIntoView({behavior:"smooth",block:"center"}); form.querySelector('[name="inventory_number"]').focus({preventScroll:true}); }
function bindDynamicActions() {
  document.querySelectorAll(".open-device").forEach((button) => button.onclick = (event) => { event.stopPropagation(); detail(button.dataset.id); });
  document.querySelectorAll(".link-endpoint").forEach((button) => button.onclick = (event) => { event.stopPropagation(); openLink(button.dataset.id, button.dataset.name); });
}
function factRows(items, emptyMessage = "В последнем отчёте этих сведений нет.") { const rows = items.filter(([,value]) => value !== null && value !== undefined && value !== ""); return rows.length ? rows.map(([label,value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`).join("") : `<p class="empty">${escapeHtml(emptyMessage)}</p>`; }
function rawValue(raw, keys) { for (const key of keys) if (raw?.[key] !== undefined && raw[key] !== "") return raw[key]; return null; }
function componentPrimary(item) { const raw = item.raw_data || {}; return item.model || rawValue(raw,["name","description","caption","chipset"]) || "Модель не определена"; }
function componentMeta(item) {
  const raw = item.raw_data || {}; const values = [];
  if (item.type === "RAM") values.push(item.capacity ? bytes(item.capacity) : null, raw.speed ? `${raw.speed} МГц` : null, item.slot, item.manufacturer, item.part_number ? `P/N ${item.part_number}` : null, item.serial ? `S/N ${item.serial}` : null, raw.type);
  else if (item.type === "STORAGE") values.push(raw.disksize != null ? storageSize(raw.disksize) : null, raw.type, raw.interface, raw.firmware ? `FW ${raw.firmware}` : null, item.serial ? `S/N ${item.serial}` : null);
  else if (item.type === "CPU") values.push(raw.core ? `${raw.core} ядер` : null, raw.thread ? `${raw.thread} потоков` : null, raw.speed ? `${raw.speed} МГц` : null, raw.manufacturer, raw.id);
  else if (item.type === "GPU") values.push(raw.memory ? `${raw.memory} МБ памяти` : null, raw.resolution, raw.chipset, raw.pcislot);
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
  if (!raw) return "Отсутствует";
  if (type === "RAM") return [raw.description || raw.caption || raw.model || raw.manufacturer || "Модуль RAM", raw.capacity != null ? bytes(ramBytes(raw.capacity)) : null, raw.numslots, raw.speed ? `${raw.speed} МГц` : null].filter(Boolean).join(" · ");
  if (type === "STORAGE") return [raw.model || raw.description || raw.name || "Накопитель", raw.disksize != null ? storageSize(raw.disksize) : null, raw.interface, raw.serial ? `S/N ${raw.serial}` : null].filter(Boolean).join(" · ");
  if (type === "ENDPOINT") return raw.hostname || raw.value || "Идентификатор устройства";
  return raw.model || raw.name || raw.description || raw.value || "Данные получены";
}
function changeCards(changes) {
  if (!changes.length) return '<div class="attention-banner ok"><span class="attention-icon">✓</span><div><strong>Изменений оборудования не обнаружено</strong><p>Текущий состав соответствует подтверждённому эталону.</p></div></div>';
  return changes.map((change) => `<article class="change-card"><div><h4>${escapeHtml(componentLabels[change.component_type] || change.component_type)}</h4><span class="meta">${escapeHtml(eventLabels[change.type] || change.type)} · ${dateTime(change.detected_at)}</span></div><div class="change-comparison"><div class="change-side"><span>Было</span><strong>${escapeHtml(componentSummary(change.component_type, change.evidence?.previous))}</strong></div><span class="change-arrow">→</span><div class="change-side"><span>Стало</span><strong>${escapeHtml(componentSummary(change.component_type, change.evidence?.current))}</strong></div></div>${pill(change.status === "OPEN" ? "ATTENTION" : change.status)}</article>`).join("");
}
async function sendAction(path, payload, method = "POST", message = "Изменения сохранены") {
  await api(path,{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); showToast(message); await load(false); if (state.selectedAsset) await detail(state.selectedAsset,false);
}
async function detail(assetId, scroll = true) {
  try {
    $("detail").hidden = false; $("detail-title").textContent = "Загрузка…";
    const asset = await api(`/admin/assets/${assetId}`); state.selectedAsset = assetId; const endpoint = asset.endpoint; const status = deviceStatus(endpoint,asset);
    $("detail-title").textContent = asset.name; $("detail-status").innerHTML = pill(status);
    $("detail-meta").textContent = [asset.inventory_number,endpoint?.hostname,locationLabel(asset)].filter(Boolean).join(" · ") || "Карточка актива";
    $("detail-actions").innerHTML = `${canEditAsset(asset)?'<button id="edit-asset" class="button-secondary">Редактировать</button>':""}<button id="show-asset-qr" class="button-secondary">QR для обхода</button>`;
    if(canEditAsset(asset))$("edit-asset").onclick = async () => { const name = prompt("Название устройства",asset.name); if(name && name !== asset.name) await sendAction(`/admin/assets/${asset.id}`,{name},"PATCH","Название обновлено"); };
    $("show-asset-qr").onclick = async () => { try { let publicUrl=localStorage.getItem("assetguardPublicUrl")||""; if (!publicUrl && !["localhost","127.0.0.1"].includes(location.hostname)) publicUrl=location.origin; if (!publicUrl || ["localhost","127.0.0.1"].includes(new URL(publicUrl).hostname)) { publicUrl=prompt("Вставьте временный HTTPS URL Cloudflare (trycloudflare.com), чтобы QR открылся на телефоне. Для локальной печати оставьте пустым.",publicUrl)||""; } if(publicUrl){ const normalized=new URL(publicUrl); if(normalized.protocol!=="https:") throw new Error("Для QR на телефоне нужен HTTPS URL."); publicUrl=normalized.origin;localStorage.setItem("assetguardPublicUrl",publicUrl); } const suffix=publicUrl?`?public_url=${encodeURIComponent(publicUrl)}`:""; const blob = await apiBlob(`/admin/assets/${asset.id}/qr.svg${suffix}`); if (state.assetQrUrl) URL.revokeObjectURL(state.assetQrUrl); state.assetQrUrl = URL.createObjectURL(blob); const popup = window.open("", "assetguard-qr", "width=480,height=560"); if (!popup) { showToast("Разрешите всплывающее окно для QR-кода", true); return; } popup.document.write(`<title>AssetGuard QR</title><main style="font-family:system-ui;text-align:center;padding:24px"><h1>${escapeHtml(asset.name)}</h1><p>${escapeHtml(asset.inventory_number)}</p><img style="width:320px;height:320px" src="${state.assetQrUrl}" alt="QR"><p>Отсканируйте код, чтобы открыть карточку устройства.</p></main>`); popup.document.close(); } catch (error) { showToast(error.message, true); } };
    const hasAgentSnapshot = Boolean(asset.current_snapshot || endpoint?.current_snapshot), usesAgent = asset.category === "IT";
    const showAgentDetails = usesAgent && Boolean(endpoint && hasAgentSnapshot);
    $("system-detail-panel").hidden = !showAgentDetails; $("identifiers-detail-panel").hidden = !showAgentDetails;
    $("agent-inventory-heading").hidden = !showAgentDetails; $("current-hardware").hidden = !showAgentDetails; $("agent-change-control").hidden = !showAgentDetails;
    const guidance = $("detail-agent-guidance");
    if (!usesAgent) {
      guidance.className="panel detail-guidance"; guidance.innerHTML='<strong>Это имущество учитывается без Agent</strong><p>Agent собирает технические сведения только с компьютеров. Эту запись используйте для школьного учёта и проверки в кабинете.</p>'; guidance.hidden=false;
    } else if (!endpoint) {
      guidance.className="attention-banner detail-guidance"; guidance.innerHTML='<span class="attention-icon">!</span><div><strong>Компьютер пока не связан с Agent</strong><p>Установите Agent и дождитесь первого отчёта. Когда компьютер появится в реестре как непривязанный, нажмите «Связать с имуществом».</p><a href="#agent-workflow">Как работает Agent →</a></div>'; guidance.hidden=false;
    } else if (!hasAgentSnapshot) {
      guidance.className="attention-banner detail-guidance"; guidance.innerHTML='<span class="attention-icon">!</span><div><strong>Компьютер связан, но отчёт ещё не получен</strong><p>Проверьте, включён ли компьютер, запущена ли служба Agent и настроен ли адрес сервера. После первой отправки здесь появятся Windows, BIOS и состав оборудования.</p><a href="#agent-workflow">Посмотреть путь данных Agent →</a></div>'; guidance.hidden=false;
    } else { guidance.hidden=true; }
    const hardwareInfo = asset.system?.hardware || {}, bios = asset.system?.bios || {}, os = asset.system?.operating_system || {}, network = asset.system?.network_quality || {};
    const emptySystemMessage = endpoint && hasAgentSnapshot ? "Последний отчёт не содержит этих сведений." : "Сведения появятся после первого отчёта Agent.";
    $("device-general").innerHTML = factRows([["Инвентарный номер",asset.inventory_number],["Категория",categoryLabels[asset.category]],["Тип",asset.asset_type],["Учёт",asset.tracking_mode === "GROUPED" ? `Групповой · ${asset.quantity} ${asset.unit || "шт."}` : "Поштучный"],["Hostname",endpoint?.hostname],["Организация",asset.organization],["Корпус",asset.building],["Этаж",asset.floor],["Кабинет",asset.room],["Статус",statusLabels[status]],["Последнее подключение",dateTime(endpoint?.last_seen_at)],["Последняя проверка",dateTime(asset.latest_inventory?.received_at)]],"Заполните карточку или выберите кабинет, чтобы найти имущество в реестре.");
    $("device-system").innerHTML = factRows([["Операционная система",os.full_name || os.name],["Версия",os.version],["Сборка / ядро",os.kernel_version],["Архитектура",os.arch],["BIOS",bios.bversion],["Дата BIOS",bios.bdate],["Производитель",bios.smanufacturer || bios.bmanufacturer],["Модель",bios.smodel || bios.mmodel],["Серийный номер",bios.ssn || bios.msn],["Корпус",hardwareInfo.chassis_type],["Рабочая группа",hardwareInfo.workgroup],["Сеть: цель",network.target],["Сеть: доступность",network.packet_loss_percent != null ? `${network.packet_loss_percent}% потерь` : null],["Сеть: средняя задержка",network.average_latency_ms != null ? `${network.average_latency_ms} мс` : null],["Сеть: измерено",network.measured_at]],emptySystemMessage);
    $("device-identifiers").innerHTML = factRows((endpoint?.identifiers || []).map((item) => [({SMBIOS_UUID:"Device UUID",CHASSIS_SERIAL:"Серийный номер корпуса",MOTHERBOARD_SERIAL:"Серийный номер платы",BIOS_SERIAL:"Серийный номер BIOS",AGENT_DEVICE_ID:"ID агента",MAC:"MAC-адрес"}[item.type] || item.type),item.value]),emptySystemMessage);
    $("snapshot-meta").textContent = asset.current_snapshot ? `${asset.current_snapshot.type === "FULL" ? "Полная" : "Частичная"} проверка · ${dateTime(asset.current_snapshot.captured_at)}` : "Данных пока нет";
    const supplemental = [...(asset.system?.drives || []).map((raw_data) => ({type:"DRIVE",raw_data,model:raw_data.description || raw_data.label})),...(asset.system?.controllers || []).map((raw_data) => ({type:"CONTROLLER",raw_data,model:raw_data.name || raw_data.caption}))];
    $("current-hardware").innerHTML = hardware([...asset.current_hardware,...supplemental],"Отчёт Agent получен, но компоненты оборудования в нём не найдены."); $("baseline-hardware").innerHTML = hardware(asset.baseline_hardware,"Эталон ещё не подтверждён. Сначала проверьте данные Agent и сохраните их как эталон.");
    $("baseline-summary").textContent = asset.baseline ? `Эталон подтверждён ${dateTime(asset.baseline.accepted_at)}${asset.baseline.reason ? ` · ${asset.baseline.reason}` : ""}` : "Эталонное состояние ещё не подтверждено.";
    $("baseline-action").innerHTML = asset.recommended_baseline_snapshot_id ? `<button id="accept-baseline">${asset.baseline ? "Обновить эталон" : "Подтвердить как эталон"}</button>` : "";
    if ($("accept-baseline")) $("accept-baseline").onclick = async () => { if (confirm("Подтвердить последний наблюдавшийся состав оборудования как новый эталон? Это действие не удаляет историю изменений.")) await sendAction(`/admin/snapshots/${asset.recommended_baseline_snapshot_id}/baseline`,{reason:"Подтверждено оператором в карточке устройства"},"POST","Эталонное состояние подтверждено"); };
    $("detail-changes").innerHTML = asset.baseline ? changeCards(asset.changes) : '<div class="attention-banner"><span class="attention-icon">!</span><div><strong>Эталон ещё не создан</strong><p>Подтвердите текущий состав, чтобы AssetGuard начал показывать изменения по принципу «Было → Стало».</p></div></div>';
    $("detail-incidents").innerHTML = asset.incidents.length ? asset.incidents.map((incident) => `<article class="row-card"><div class="row-title"><b>${escapeHtml(incidentLabel(incident))}</b>${pill(incident.status)}</div><div class="meta">${dateTime(incident.created_at)}</div>${["OPEN","UNDER_REVIEW"].includes(incident.status) ? `<div class="actions"><button class="classify button-secondary" data-id="${incident.id}">Взять на проверку</button><button class="resolve" data-id="${incident.id}">Подтвердить решение</button></div>` : ""}</article>`).join("") : '<p class="empty">Открытых обращений нет.</p>';
    document.querySelectorAll(".classify").forEach((button) => button.onclick = () => incidentAction(button.dataset.id,false)); document.querySelectorAll(".resolve").forEach((button) => button.onclick = () => incidentAction(button.dataset.id,true));
    $("detail-history").innerHTML = asset.history.length ? asset.history.map((entry) => `<article><time>${dateTime(entry.occurred_at)}</time><div><b>${escapeHtml(eventLabels[entry.type] || entry.type)}</b><p>${escapeHtml(historyMessage(entry))}</p></div></article>`).join("") : '<p class="empty">История появится после первой проверки или действия с устройством.</p>';
    if(scroll) $("detail").scrollIntoView({behavior:"smooth",block:"start"});
  } catch(error) { showToast(error.message,true); $("detail").hidden = true; }
}
function historyMessage(entry) {
  if(entry.type === "INVENTORY_COMPLETED") return `${entry.metadata?.inventory_type === "FULL" ? "Полная" : "Частичная"} проверка завершена, данные сохранены.`;
  if(entry.type === "HARDWARE_CHANGE_DETECTED") return `${componentLabels[entry.metadata?.component_type] || "Состав оборудования"}: требуется проверка.`;
  if(entry.type === "BASELINE_ACCEPTED") return "Текущее состояние сохранено как эталон.";
  if(entry.type === "INCIDENT_RESOLVED") return `Решение зафиксировано: ${entry.metadata?.classification || "проверено"}.`;
  return entry.message;
}
async function incidentAction(id,resolve) {
  const classification = resolve ? "AUTHORIZED_CHANGE" : "REQUIRES_INVESTIGATION";
  if(resolve && !confirm("Закрыть обращение и зафиксировать изменение как проверенное?")) return;
  const comment = prompt(resolve ? "Комментарий к решению" : "Что необходимо проверить?","") || null;
  await sendAction(`/admin/incidents/${id}/${resolve ? "resolve" : "decision"}`,{classification,comment},"POST",resolve ? "Решение сохранено" : "Обращение взято на проверку");
}
function openLink(endpointId,hostname) { state.linkingEndpoint=endpointId; $("link-target").textContent=`Найденный компьютер: ${hostname || endpointId}`; $("link-asset").innerHTML=state.assets.filter((asset) => asset.category === "IT" && !asset.endpoint_id).map((asset) => `<option value="${asset.id}">${escapeHtml(asset.inventory_number)} — ${escapeHtml(asset.name)}</option>`).join(""); if(!$("link-asset").options.length){showToast("Добавьте в реестр свободную запись компьютера, чтобы связать с ней Agent.",true);return;} $("link-dialog").showModal(); }

function visionCountRows(counts) { const entries=Object.entries(counts||{}); return entries.length ? entries.map(([name,count]) => `<div class="count-row"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>`).join("") : '<p class="empty">Объекты выбранных классов не найдены.</p>'; }
async function renderVisionScan(scan,roomName) {
  state.visionScan=scan; state.visionRoomId=scan.room_id; $("vision-result").hidden=false; $("vision-room-title").textContent=roomName||"Кабинет"; $("vision-status-badge").innerHTML=statusLabels[scan.status]||scan.status; $("vision-status-badge").className=`status-pill ${classForStatus(scan.status)}`; $("vision-counts").innerHTML=`${scan.asset ? `<p class="meta">Связанный актив: <button class="link-button" id="vision-asset-link">${escapeHtml(scan.asset.name)} · ${escapeHtml(scan.asset.inventory_number)}</button></p>` : ""}${visionCountRows(scan.counts)}`;
  if(scan.asset) $("vision-asset-link").onclick=()=>detail(scan.asset.id);
  const differences=scan.comparison?.differences||[]; $("vision-comparison").innerHTML=scan.status==="NOT_CHECKED" ? '<p class="empty">Эталон ещё не подтверждён.</p>' : differences.length ? differences.map((item)=>`<div class="comparison-row warning"><span>${escapeHtml(item.class_name)}</span><span>ожидалось ${item.expected}, найдено ${item.detected}</span><strong>${item.difference>0?"+":""}${item.difference}</strong></div>`).join("") : '<div class="comparison-ok">Количество объектов соответствует эталону.</div>';
  $("vision-baseline").textContent=scan.status==="NOT_CHECKED"?"Подтвердить как эталон":"Обновить эталон"; if(state.visionImageUrl) URL.revokeObjectURL(state.visionImageUrl); const blob=await apiBlob(scan.annotated_image_url); state.visionImageUrl=URL.createObjectURL(blob); $("vision-image").src=state.visionImageUrl;
}
async function loadVisionHistory(roomId) { if(!roomId){$("vision-history").innerHTML='<p class="empty">Загрузите первое фото помещения.</p>';return;} const scans=await api(`/admin/vision/rooms/${roomId}/scans`); const room=state.visionRooms.find((item)=>item.id===roomId); $("vision-history").innerHTML=scans.map((scan)=>`<button class="vision-history-item" data-id="${scan.id}"><span><b>${dateTime(scan.created_at)}</b><small>${Object.entries(scan.counts).map(([name,count])=>`${escapeHtml(name)}: ${count}`).join(" · ")||"Объекты не найдены"}</small></span>${pill(scan.status)}</button>`).join("")||'<p class="empty">История проверок пуста.</p>'; document.querySelectorAll(".vision-history-item").forEach((button)=>button.onclick=async()=>renderVisionScan(await api(`/admin/vision/scans/${button.dataset.id}`),room?.name)); }
function renderVisionRooms(rooms) { state.visionRooms=rooms; const locationRooms=state.locations.flatMap((building)=>building.floors.flatMap((floor)=>floor.rooms.map((room)=>({id:room.id,label:`${building.name} · этаж ${floor.name} · кабинет ${room.name}`})))); const locationSelect=$("vision-location-room"),selectedLocation=locationSelect.value; locationSelect.innerHTML=locationRooms.length?'<option value="">Выберите кабинет</option>'+locationRooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.label)}</option>`).join(""):'<option value="">Сначала создайте корпус, этаж и кабинет</option>'; if(locationRooms.some((room)=>room.id===selectedLocation))locationSelect.value=selectedLocation;locationSelect.disabled=!locationRooms.length; $("vision-run").disabled=!locationRooms.length; $("vision-room-select").innerHTML=rooms.length?rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.name)}</option>`).join(""):'<option value="">Проверок пока нет</option>'; syncVisionAssetsForRoom(locationSelect.value); if(rooms.length){const selected=rooms.find((room)=>room.id===state.visionRoomId)||rooms[0];state.visionRoomId=selected.id;$("vision-room-select").value=selected.id;loadVisionHistory(selected.id);if(!state.visionScan&&selected.latest_scan)renderVisionScan(selected.latest_scan,selected.name);}else loadVisionHistory(null); }

async function load(showLoading=true) {
  if(showLoading){$("status").textContent="Обновляем данные…";$("attention-banner").className="attention-banner is-loading";}
  try { const [assets,endpoints,changes,incidents,visionRooms,operations,locations,currentUser]=await Promise.all([api("/admin/assets"),api("/admin/endpoints"),api("/admin/changes"),api("/admin/incidents"),api("/admin/vision/rooms"),api("/admin/operations/status"),api("/admin/locations/tree"),api("/auth/me")]); state={...state,assets,endpoints,changes,incidents,visionRooms,operations,locations,currentUser}; syncRoleControls(); buildDevices(); renderDashboard(); renderOperations(operations); renderLocations(locations); renderDevices(); renderVisionRooms(visionRooms); await loadAdminAccess(); $("status").textContent=`Данные актуальны · ${dateTime(new Date())}`; }
  catch(error){$("status").textContent=error.message;$("attention-banner").className="attention-banner error";$("attention-banner").innerHTML=`<span class="attention-icon">!</span><div><strong>Не удалось загрузить Dashboard</strong><p>${escapeHtml(error.message)}</p></div>`;showToast(error.message,true);}
}
function openAssetFromHash() { const match = location.hash.match(/^#asset=([0-9a-f-]{36})$/i); if (match && token) detail(match[1]); }

$("token-form").addEventListener("submit",async(event)=>{event.preventDefault();const username=$("username").value.trim(),secret=$("token").value;try{if(username){const response=await fetch("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password:secret})});if(!response.ok)throw new Error("Неверный логин или пароль");token=(await response.json()).access_token;}else token=secret;sessionStorage.setItem("assetguard-admin-token",token);$("token").value="";await load();openAssetFromHash();showToast("Вход выполнен");}catch(error){$("status").textContent=error.message;showToast(error.message,true);}});
$("nav-toggle").addEventListener("click",()=>{const header=document.querySelector(".app-header"),open=header.classList.toggle("nav-open");$("nav-toggle").setAttribute("aria-expanded",String(open));$("nav-toggle").setAttribute("aria-label",open?"Закрыть меню":"Открыть меню");});
document.querySelectorAll("#main-nav a").forEach((link)=>link.addEventListener("click",()=>{document.querySelector(".app-header").classList.remove("nav-open");$("nav-toggle").setAttribute("aria-expanded","false");document.querySelectorAll("#main-nav a").forEach((item)=>item.removeAttribute("aria-current"));link.setAttribute("aria-current","location");}));
function syncTrackingMode() { const grouped=$("asset-tracking-mode").value==="GROUPED", field=$("asset-quantity-field"), input=field.querySelector("input");field.hidden=!grouped;input.disabled=!grouped;input.required=grouped; }
$("asset-tracking-mode").addEventListener("change",syncTrackingMode);
$("clear-device-filters").addEventListener("click",clearDeviceFilters);
$("logout").onclick=async()=>{if(token)await fetch("/auth/logout",{method:"POST",headers:{"X-AssetGuard-Admin-Token":token}}).catch(()=>{});token="";sessionStorage.removeItem("assetguard-admin-token");state={...state,assets:[],endpoints:[],devices:[],changes:[],incidents:[],currentUser:null};syncRoleControls();renderAdminAccessVisibility();$("status").textContent="Сессия завершена.";showToast("Вы вышли из системы");};
$("show-create").onclick=()=>{if(!$("create-asset").hidden){$("create-asset").hidden=true;return;}openAssetCreateForm();};
$("cancel-create").onclick=()=>{$("create-asset").hidden=true;};
$("create-building").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;try{await api("/admin/locations/buildings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(new FormData(form).entries()))});form.reset();showToast("Корпус создан");await load(false);}catch(error){showToast(error.message,true);}});
$("location-create-form").addEventListener("submit",async(event)=>{event.preventDefault();if(!locationDialogTarget)return;const button=$("location-create-submit"),{kind,parentId}=locationDialogTarget;const isRoom=kind==="room",body={name:$("location-create-name").value.trim()};if(isRoom){body.responsible_name=$("location-create-responsible").value.trim()||null;body.responsible_contact=$("location-create-contact").value.trim()||null;}button.disabled=true;try{const path=isRoom?`/admin/locations/floors/${parentId}/rooms`:`/admin/locations/buildings/${parentId}/floors`;await api(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});$("location-create-dialog").close();showToast(isRoom?"Кабинет добавлен":"Этаж добавлен");await load(false);}catch(error){showToast(error.message,true);}finally{button.disabled=false;}});
$("location-create-cancel").onclick=()=>$("location-create-dialog").close();
$("create-user").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;try{const body=Object.fromEntries(new FormData(form).entries());body.organization_id=body.organization_id||null;const created=await api("/admin/users",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});form.reset();await loadAdminAccess();if(created.role!=="ADMIN"){$("access-user").value=created.id;renderAdminAccess();showToast("Пользователь создан. Теперь назначьте ему кабинет и права.");$("assign-user-panel").scrollIntoView({behavior:"smooth",block:"center"});$("access-scope").focus({preventScroll:true});}else showToast("Учётная запись администратора создана.");}catch(error){showToast(error.message,true);}});
$("grant-location-access").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;try{const body=Object.fromEntries(new FormData(form).entries());const [scope_type,scope_id]=body.scope.split(":");await api("/admin/locations/access",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:body.user_id,scope_type,scope_id,permission:body.permission})});showToast("Назначение сохранено");await loadAdminAccess();}catch(error){showToast(error.message,true);}});
$("access-user").addEventListener("change",renderAdminAccess);
$("refresh-access").onclick=loadAdminAccess;
$("create-agent-credential").addEventListener("submit",async(event)=>{event.preventDefault();try{const organizationId=state.currentUser?.organization_id||$("agent-organization").value||null;const credential=await api("/admin/agent-credentials",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({organization_id:organizationId})});await loadAdminAccess();$("agent-credential-username").value=credential.username;$("agent-credential-secret").value=credential.secret;$("agent-credential-dialog").showModal();showToast("Ключ для компьютера создан. Скопируйте его сейчас.");}catch(error){showToast(error.message,true);}});
$("refresh-agent-credentials").onclick=loadAdminAccess;
document.querySelectorAll(".copy-agent-credential").forEach((button)=>button.onclick=async()=>{try{await copyAgentCredential(button.dataset.field);}catch(error){showToast(error.message,true);}});
$("agent-credential-result").addEventListener("submit",()=>{$("agent-credential-username").value="";$("agent-credential-secret").value="";});
$("agent-credential-dialog").addEventListener("close",()=>{$("agent-credential-username").value="";$("agent-credential-secret").value="";});
$("export-assets").onclick = async () => { try { const blob = await apiBlob("/admin/assets/export.xlsx"); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "assetguard-assets.xlsx"; link.click(); URL.revokeObjectURL(url); } catch (error) { showToast(error.message, true); } };
$("export-assets-pdf").onclick = async () => { try { const blob = await apiBlob("/admin/assets/export.pdf"); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "assetguard-assets.pdf"; link.click(); URL.revokeObjectURL(url); } catch (error) { showToast(error.message, true); } };
function confirmAssetImport(file,format,preview) {
  $("import-preview-file").textContent=`${file.name} · ${format.toUpperCase()}`;
  const items=preview.items||preview.samples||[], selected=new Set(items.map((_,index)=>index)), pageSize=25;
  const table=$("import-preview-samples"), search=$("import-preview-search"), selectPage=$("import-preview-select-page"), applyButton=$("apply-import-preview");
  const update=()=>{
    const query=search.value.trim().toLocaleLowerCase("ru"), filtered=items.map((item,index)=>({item,index})).filter(({item})=>!query||[item.inventory_number,item.name,item.asset_type,item.building,item.floor,item.room].some((value)=>String(value||"").toLocaleLowerCase("ru").includes(query)));
    const pageCount=Math.max(1,Math.ceil(filtered.length/pageSize));state.importPreviewPage=Math.min(Math.max(state.importPreviewPage||0,0),pageCount-1);
    const start=state.importPreviewPage*pageSize, visible=filtered.slice(start,start+pageSize), visibleIndices=visible.map(({index})=>index);
    const chosen=items.map((item,index)=>selected.has(index)?item:null).filter(Boolean);
    $("import-preview-rows").textContent=chosen.length;
    $("import-preview-creates").textContent=chosen.filter((item)=>item.action!=="update").length;
    $("import-preview-updates").textContent=chosen.filter((item)=>item.action==="update").length;
    $("import-preview-page-info").textContent=filtered.length?`Позиции ${start+1}–${start+visible.length} из ${filtered.length} · всего в файле ${items.length}`:`Совпадений нет · всего в файле ${items.length}`;
    $("import-preview-prev").disabled=state.importPreviewPage===0;$("import-preview-next").disabled=state.importPreviewPage>=pageCount-1;
    const checkedCount=visibleIndices.filter((index)=>selected.has(index)).length;selectPage.checked=visibleIndices.length>0&&checkedCount===visibleIndices.length;selectPage.indeterminate=checkedCount>0&&checkedCount<visibleIndices.length;
    applyButton.disabled=chosen.length===0;
    table.innerHTML=visible.length?'<table><thead><tr><th scope="col">В импорт</th><th scope="col">№</th><th scope="col">Инв. №</th><th scope="col">Наименование</th><th scope="col">Тип</th><th scope="col">Кабинет</th><th scope="col">Действие</th><th scope="col">OCR</th></tr></thead><tbody>'+visible.map(({item,index})=>`<tr><td><input type="checkbox" data-import-row="${index}" aria-label="Импортировать строку ${index+1}" ${selected.has(index)?"checked":""}></td><td>${index+1}</td><td>${escapeHtml(item.inventory_number||"—")}</td><td>${escapeHtml(item.name||"—")}</td><td>${escapeHtml(item.asset_type||"—")}</td><td>${escapeHtml([item.building,item.floor,item.room].filter(Boolean).join(" · ")||"—")}</td><td><span class="import-action ${item.action==="update"?"is-update":"is-create"}">${item.action==="update"?"Обновится":"Новая"}</span></td><td>${Number.isFinite(item.confidence)?`${item.confidence}%`:"—"}</td></tr>`).join("")+'</tbody></table>':'<p class="empty">'+(items.length?"По этому запросу ничего не найдено.":"Строки для импорта не найдены.")+'</p>';
  };
  state.importPreviewPage=0;search.value="";
  $("import-preview-note").textContent=(preview.source||"").toLowerCase().includes("ocr")?"Это скан: текст распознан OCR, процент — ориентир, а не гарантия точности. Сверьте названия и номера с оригиналом и снимите галочку у ошибочных строк.":"Сопоставление с реестром выполняется по инвентарному номеру. Все строки включены по умолчанию: снимите галочку у тех, которые не нужно добавлять или обновлять.";
  search.oninput=()=>{state.importPreviewPage=0;update();};
  $("import-preview-prev").onclick=()=>{state.importPreviewPage--;update();};$("import-preview-next").onclick=()=>{state.importPreviewPage++;update();};
  selectPage.onchange=()=>{const query=search.value.trim().toLocaleLowerCase("ru"), filtered=items.map((item,index)=>({item,index})).filter(({item})=>!query||[item.inventory_number,item.name,item.asset_type,item.building,item.floor,item.room].some((value)=>String(value||"").toLocaleLowerCase("ru").includes(query))),start=(state.importPreviewPage||0)*pageSize;filtered.slice(start,start+pageSize).forEach(({index})=>selectPage.checked?selected.add(index):selected.delete(index));update();};
  table.onchange=(event)=>{const checkbox=event.target.closest("[data-import-row]");if(!checkbox)return;const index=Number(checkbox.dataset.importRow);checkbox.checked?selected.add(index):selected.delete(index);update();};
  update();
  const dialog=$("import-preview-dialog");
  dialog.returnValue="";
  return new Promise((resolve)=>{dialog.addEventListener("close",()=>{applyButton.disabled=false;resolve(dialog.returnValue==="apply"?{excludedRows:items.map((_,index)=>index).filter((index)=>!selected.has(index))}:null);},{once:true});dialog.showModal();});
}
async function importAssetFile(file,format) {
  const previewForm=new FormData(); previewForm.append("file",file);
  const preview=await api(`/admin/assets/import.${format}`,{method:"POST",body:previewForm});
  const selection=await confirmAssetImport(file,format,preview);if(!selection)return;
  const applyForm=new FormData(); applyForm.append("file",file);
  selection.excludedRows.forEach((index)=>applyForm.append("exclude_row",String(index)));
  const result=await api(`/admin/assets/import.${format}?apply=true`,{method:"POST",body:applyForm});
  showToast(`Импорт завершён: новых записей — ${result.creates}, обновлено — ${result.updates}.`);
  await load(false);
}
$("import-assets").onclick = () => $("import-assets-file").click();
$("import-assets-file").onchange = async (event) => { const input=event.target,file=input.files?.[0];if(!file)return;try{await importAssetFile(file,"xlsx");}catch(error){showToast(error.message,true);}finally{input.value="";}};
$("import-assets-pdf").onclick = () => $("import-assets-pdf-file").click();
$("import-assets-pdf-file").onchange = async (event) => { const input=event.target,file=input.files?.[0];if(!file)return;try{await importAssetFile(file,"pdf");}catch(error){showToast(error.message,true);}finally{input.value="";}};
$("create-asset").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;try{const body=Object.fromEntries(new FormData(form).entries());body.room_id=body.room_id||null;body.quantity=body.quantity||1;body.category=({Desktop:"IT",Laptop:"IT",Printer:"IT",Projector:"IT",Network:"IT",Furniture:"FURNITURE",Sports:"SPORTS",Educational:"EDUCATIONAL",Other:"OTHER"})[body.asset_type]||"OTHER";await api("/admin/assets",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});form.reset();form.hidden=true;syncTrackingMode();showToast("Имущество добавлено в реестр");await load(false);}catch(error){showToast(error.message,true);}});
$("link-form").addEventListener("submit",async(event)=>{event.preventDefault();if(!state.linkingEndpoint||!$("link-asset").value)return;try{await api(`/admin/endpoints/${state.linkingEndpoint}/asset/${$("link-asset").value}`,{method:"POST"});$("link-dialog").close();showToast("Устройство связано с активом");await load(false);}catch(error){showToast(error.message,true);}});$("link-cancel").onclick=()=>$("link-dialog").close();
[$("device-search"),$("device-status-filter"),$("device-category-filter"),$("device-room-filter"),$("device-change-filter"),$("device-sort")].forEach((control)=>control.addEventListener(control.type==="search"?"input":"change",renderDevices));
$("detail-back").onclick=()=>{state.selectedAsset=null;$("detail").hidden=true;location.hash="devices";$("devices").scrollIntoView({behavior:"smooth",block:"start"});};
$("room-tabs").addEventListener("click",(event)=>{const button=event.target.closest("[data-room-tab]");if(!button)return;state.roomTab=button.dataset.roomTab;renderRoomTab();});
$("room-detail-back").onclick=()=>{state.roomWorkspace=null;$("room-detail").hidden=true;location.hash="locations";$("locations").scrollIntoView({behavior:"smooth",block:"start"});};
$("room-edit-action").onclick=openRoomEditDialog;
$("room-vision-action").onclick=()=>launchRoomVision(state.roomWorkspace?.room.id);
$("room-inspection-action").onclick=openRoomInspectionDialog;
$("room-edit-cancel").onclick=()=>$("room-edit-dialog").close();
$("room-edit-form").addEventListener("submit",async(event)=>{event.preventDefault();const roomId=state.roomWorkspace?.room.id;if(!roomId)return;const button=$("room-edit-submit"),body={purpose:$("room-edit-purpose").value.trim()||null,responsible_name:$("room-edit-responsible").value.trim()||null,responsible_contact:$("room-edit-contact").value.trim()||null,notes:$("room-edit-notes").value.trim()||null};button.disabled=true;try{await api(`/admin/locations/rooms/${roomId}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});await load(false);await openRoomWorkspace(roomId);$("room-edit-dialog").close();showToast("Данные кабинета сохранены");}catch(error){showToast(error.message,true);}finally{button.disabled=false;}});
$("room-inspection-cancel").onclick=()=>$("room-inspection-dialog").close();
$("room-inspection-form").addEventListener("submit",async(event)=>{event.preventDefault();const roomId=state.roomWorkspace?.room.id;if(!roomId)return;const button=$("room-inspection-submit"),items=[...$("room-inspection-items").querySelectorAll(".inspection-item")].map((row)=>{const result=row.querySelector(".inspection-result-input").value;return {asset_id:row.dataset.asset,result,affected_quantity:result==="PRESENT"?0:Number(row.querySelector(".inspection-affected-input").value),comment:row.querySelector(".inspection-item-comment").value.trim()||null};}),body={comment:$("room-inspection-comment").value.trim()||null,items};button.disabled=true;try{await api(`/admin/locations/rooms/${roomId}/inspections`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});await load(false);await openRoomWorkspace(roomId);state.roomTab="inspection";renderRoomTab();$("room-inspection-dialog").close();showToast("Обход кабинета сохранён");}catch(error){showToast(error.message,true);}finally{button.disabled=false;}});
$("physical-incident-cancel").onclick=()=>$("physical-incident-dialog").close();
$("physical-incident-action-select").addEventListener("change",syncPhysicalOperationFields);
$("physical-incident-quantity").addEventListener("input",syncPhysicalOperationFields);
$("physical-incident-form").addEventListener("submit",async(event)=>{event.preventDefault();const incidentId=state.physicalIncidentId,roomId=state.roomWorkspace?.room.id;if(!incidentId||!roomId)return;const button=$("physical-incident-submit"),action=$("physical-incident-action-select").value,body={action,comment:$("physical-incident-comment").value.trim()};if(["MOVE","WRITE_OFF"].includes(action)){body.quantity=Number($("physical-incident-quantity").value);body.document_number=$("physical-incident-document-number").value.trim();if(action==="MOVE"){body.destination_room_id=$("physical-incident-destination").value;const inventory=$("physical-incident-inventory-number").value.trim();if(inventory)body.destination_inventory_number=inventory;}}button.disabled=true;try{await api(`/admin/locations/physical-incidents/${incidentId}/decision`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});await load(false);await openRoomWorkspace(roomId);state.roomTab="incidents";renderRoomTab();$("physical-incident-dialog").close();showToast(action==="INVESTIGATE"?"Инцидент взят на проверку":action==="MOVE"?"Имущество перемещено, акт готов":action==="WRITE_OFF"?"Имущество списано, акт готов":"Решение по инциденту сохранено");}catch(error){showToast(error.message,true);}finally{button.disabled=false;}});
$("vision-location-room").addEventListener("change",(event)=>syncVisionAssetsForRoom(event.target.value));
$("vision-upload").addEventListener("submit",async(event)=>{event.preventDefault();const button=$("vision-run"),selectedRoomName=$("vision-location-room").selectedOptions[0]?.textContent||"Кабинет";button.disabled=true;$("vision-progress").textContent="Анализируем фото… Первый запуск может занять несколько минут.";try{const form=new FormData(event.currentTarget);const scan=await api("/admin/vision/scans",{method:"POST",body:form});state.visionRoomId=scan.room_id;const rooms=await api("/admin/vision/rooms");renderVisionRooms(rooms);await renderVisionScan(scan,selectedRoomName);await loadVisionHistory(scan.room_id);$("vision-progress").textContent=`Анализ завершён: найдено объектов — ${scan.detections.length}. Проверьте результат.`;}catch(error){$("vision-progress").textContent=error.message;showToast(error.message,true);}finally{button.disabled=!state.locations.some((building)=>building.floors.some((floor)=>floor.rooms.length));}});
$("vision-baseline").onclick=async()=>{if(!state.visionScan)return;if(!confirm("Подтвердить результат этой проверки как эталон кабинета?"))return;try{await api(`/admin/vision/rooms/${state.visionScan.room_id}/baseline`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scan_id:state.visionScan.id})});const scan=await api(`/admin/vision/scans/${state.visionScan.id}`);await renderVisionScan(scan,state.visionRooms.find((room)=>room.id===scan.room_id)?.name);await loadVisionHistory(scan.room_id);$("vision-progress").textContent="Эталон подтверждён. Следующее фото будет сравнено с ним.";showToast("Эталон помещения сохранён");}catch(error){showToast(error.message,true);}};
$("vision-room-select").onchange=async(event)=>{state.visionRoomId=event.target.value;const room=state.visionRooms.find((item)=>item.id===state.visionRoomId);state.visionScan=room?.latest_scan||null;if(state.visionScan)await renderVisionScan(state.visionScan,room.name);await loadVisionHistory(state.visionRoomId);};
window.addEventListener("hashchange",()=>{openAssetFromHash();const target=location.hash.slice(1),link=document.querySelector(`#main-nav a[href="#${CSS.escape(target)}"]`);document.querySelectorAll("#main-nav a").forEach((item)=>item.removeAttribute("aria-current"));link?.setAttribute("aria-current","location");if(target==="devices"&&state.selectedAsset){$("detail").hidden=true;state.selectedAsset=null;}document.querySelector(".app-header").classList.remove("nav-open");$("nav-toggle").setAttribute("aria-expanded","false");});
syncRoleControls();
renderAdminAccessVisibility();
if(token)load().then(openAssetFromHash);
