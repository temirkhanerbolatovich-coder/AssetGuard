const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("assetguard-admin-token") || "";
let state = {assets: [], endpoints: [], devices: [], changes: [], incidents: [], visionRooms: [], selectedAsset: null, linkingEndpoint: null, visionRoomId: null, visionScan: null, visionImageUrl: null};
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
const statusLabels = {OK:"В норме",ATTENTION:"Требует внимания",ANOMALY:"Обнаружено расхождение",OFFLINE:"Не в сети",UNCHECKED:"Не проверено",WARNING:"Требует внимания",NOT_CHECKED:"Не проверено",ONLINE:"В норме",REQUIRES_VERIFICATION:"Требует проверки",IDENTITY_CONFLICT:"Конфликт идентификации",OPEN:"Открыто",UNDER_REVIEW:"На проверке",RESOLVED:"Закрыто",DISMISSED:"Не подтверждено",ACTIVE:"Активен"};
const componentLabels = {RAM:"Оперативная память",STORAGE:"Физические накопители",DRIVE:"Разделы дисков",CONTROLLER:"Контроллеры",CPU:"Процессор",GPU:"Видеокарта",MOTHERBOARD:"Материнская плата",NETWORK:"Сетевые интерфейсы",MONITOR:"Мониторы",ENDPOINT:"Устройство"};
const eventLabels = {COMPONENT_ADDED:"Компонент добавлен",COMPONENT_REMOVED:"Компонент отсутствует",COMPONENT_CHANGED:"Характеристики изменились",COMPONENT_REPLACED:"Компонент заменён",HOSTNAME_CHANGED:"Изменилось имя компьютера",DEVICE_IDENTITY_CHANGED:"Изменился идентификатор устройства",INVENTORY_COMPLETED:"Инвентаризация завершена",BASELINE_ACCEPTED:"Эталон подтверждён",HARDWARE_CHANGE_DETECTED:"Обнаружено изменение оборудования",INCIDENT_CREATED:"Создано обращение",INCIDENT_CLASSIFIED:"Обращение классифицировано",INCIDENT_RESOLVED:"Обращение закрыто",ASSET_CREATED:"Актив добавлен",ASSET_UPDATED:"Карточка обновлена",ENDPOINT_LINKED:"Устройство связано с активом",ENDPOINT_UNLINKED:"Устройство отвязано"};
const classForStatus = (value) => ({OK:"ok",ONLINE:"ok",ACTIVE:"ok",RESOLVED:"ok",ATTENTION:"attention",WARNING:"warning",OPEN:"warning",UNDER_REVIEW:"warning",ANOMALY:"anomaly",IDENTITY_CONFLICT:"danger",OFFLINE:"offline",UNCHECKED:"unchecked",NOT_CHECKED:"unchecked",REQUIRES_VERIFICATION:"unchecked"}[value] || "neutral");
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
function deviceStatus(endpoint) {
  if (!endpoint?.current_snapshot) return "UNCHECKED";
  if (endpoint.status === "IDENTITY_CONFLICT") return "ANOMALY";
  if (endpoint.status !== "ONLINE") return "UNCHECKED";
  if (endpoint.open_changes > 0 || endpoint.open_incidents > 0) return "ATTENTION";
  return "OK";
}
function buildDevices() {
  const linkedEndpointIds = new Set();
  const devices = state.assets.map((asset) => {
    const endpoint = asset.endpoint;
    if (endpoint) linkedEndpointIds.add(endpoint.id);
    return {kind:"asset",assetId:asset.id,endpointId:endpoint?.id || null,name:asset.name,inventoryNumber:asset.inventory_number,hostname:endpoint?.hostname || null,room:asset.room,organization:asset.organization,endpoint,status:deviceStatus(endpoint)};
  });
  state.endpoints.filter((endpoint) => !linkedEndpointIds.has(endpoint.id)).forEach((endpoint) => devices.push({kind:"endpoint",assetId:null,endpointId:endpoint.id,name:endpoint.hostname || "Непривязанное устройство",inventoryNumber:null,hostname:endpoint.hostname,room:null,organization:null,endpoint,status:deviceStatus(endpoint)}));
  state.devices = devices;
}
function deviceForEndpoint(endpointId) { return state.devices.find((device) => device.endpointId === endpointId); }
function renderDashboard() {
  const devices = state.devices;
  const online = devices.filter((item) => item.status === "OK").length;
  const attention = devices.filter((item) => ["ATTENTION","ANOMALY"].includes(item.status));
  const unchecked = devices.filter((item) => item.status === "UNCHECKED");
  $("devices-count").textContent = devices.length; $("online-count").textContent = online; $("attention-count").textContent = attention.length; $("unchecked-count").textContent = unchecked.length;
  const banner = $("attention-banner");
  if (!attention.length && !unchecked.length) {
    banner.className = "attention-banner ok"; banner.innerHTML = '<span class="attention-icon">✓</span><div><strong>Все устройства работают штатно</strong><p>Открытых изменений и устройств без актуальной проверки нет.</p></div>';
  } else {
    banner.className = "attention-banner"; banner.innerHTML = `<span class="attention-icon">!</span><div><strong>${attention.length ? `${attention.length} ${attention.length === 1 ? "устройство требует" : "устройства требуют"} внимания` : "Есть устройства без актуальной проверки"}</strong><p>${unchecked.length ? `Без актуальных данных: ${unchecked.length}. ` : ""}Откройте карточку, чтобы увидеть причину и сравнение с эталоном.</p></div>`;
  }
  const priority = [...attention, ...unchecked].slice(0, 6);
  $("attention-badge").textContent = priority.length ? String(priority.length) : "Всё спокойно"; $("attention-badge").className = `status-pill ${priority.length ? "warning" : "ok"}`;
  $("attention-list").innerHTML = priority.length ? priority.map((item) => `<div class="attention-item"><span class="attention-dot"></span><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.room || item.hostname || "Расположение не указано")} · ${escapeHtml(statusLabels[item.status])}${item.endpoint?.open_changes ? ` · изменений: ${item.endpoint.open_changes}` : ""}</small></div>${item.assetId ? `<button class="open-device button-secondary" data-id="${item.assetId}">Открыть</button>` : `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать</button>`}</div>`).join("") : '<p class="empty">Ничего не требует внимания.</p>';
  const activity = state.changes.slice(0, 5);
  $("activity-list").innerHTML = activity.length ? activity.map((change) => { const device = deviceForEndpoint(change.endpoint_id); return `<article><time>${dateTime(change.detected_at)}</time><div><b>${escapeHtml(eventLabels[change.type] || change.type)}</b><p>${escapeHtml(device?.name || "Устройство")} · ${escapeHtml(componentLabels[change.component_type] || change.component_type)}</p></div></article>`; }).join("") : '<p class="empty">Изменений не обнаружено. Последние проверки завершились штатно.</p>';
  const latest = devices.map((item) => item.endpoint?.last_seen_at).filter(Boolean).sort().at(-1); $("last-activity").textContent = latest ? `Последняя проверка ${relativeTime(latest)}` : "Проверок пока нет";
  const locations = new Map(); devices.forEach((item) => { const key = [item.organization, item.room].filter(Boolean).join(" · ") || "Расположение не указано"; locations.set(key, (locations.get(key) || 0) + 1); });
  $("location-summary").innerHTML = [...locations.entries()].map(([name,count]) => `<span class="tag">${escapeHtml(name)} <strong>${count}</strong></span>`).join("") || '<p class="empty">Добавьте кабинет в карточке актива.</p>';
  const full = devices.filter((item) => item.endpoint?.current_snapshot?.type === "FULL").length;
  $("inventory-summary").innerHTML = `<div class="summary-line"><span>Успешно обработано</span><strong>${devices.filter((item) => item.endpoint?.current_snapshot).length} из ${devices.length}</strong></div><div class="summary-line"><span>Полная инвентаризация</span><strong>${full}</strong></div><div class="summary-line"><span>Последняя активность</span><strong>${latest ? relativeTime(latest) : "—"}</strong></div>`;
  bindDynamicActions();
}
function hardwareBrief(endpoint) {
  const summary = endpoint?.hardware_summary; if (!summary) return "Нет данных";
  return [summary.ram_bytes ? `${bytes(summary.ram_bytes)} RAM` : null, summary.storage_devices ? `${summary.storage_devices} накоп.` : null, summary.cpu].filter(Boolean).join(" · ") || "Состав не определён";
}
function filteredDevices() {
  const query = $("device-search").value.trim().toLocaleLowerCase("ru"); const status = $("device-status-filter").value; const room = $("device-room-filter").value; const changed = $("device-change-filter").checked;
  const result = state.devices.filter((item) => {
    const haystack = [item.name,item.inventoryNumber,item.hostname,item.room,item.organization].filter(Boolean).join(" ").toLocaleLowerCase("ru");
    const matchesStatus = !status || item.status === status || (status === "ATTENTION" && item.status === "ANOMALY");
    return (!query || haystack.includes(query)) && matchesStatus && (!room || item.room === room) && (!changed || (item.endpoint?.open_changes || 0) > 0);
  });
  const sort = $("device-sort").value;
  return result.sort((a,b) => sort === "name" ? a.name.localeCompare(b.name,"ru") : sort === "attention" ? (["ANOMALY","ATTENTION","UNCHECKED","OK"].indexOf(a.status) - ["ANOMALY","ATTENTION","UNCHECKED","OK"].indexOf(b.status)) : (new Date(b.endpoint?.last_seen_at || 0) - new Date(a.endpoint?.last_seen_at || 0)));
}
function renderDevices() {
  const rooms = [...new Set(state.devices.map((item) => item.room).filter(Boolean))].sort(); const selectedRoom = $("device-room-filter").value;
  $("device-room-filter").innerHTML = '<option value="">Все кабинеты</option>' + rooms.map((room) => `<option value="${escapeHtml(room)}">${escapeHtml(room)}</option>`).join(""); $("device-room-filter").value = rooms.includes(selectedRoom) ? selectedRoom : "";
  const devices = filteredDevices();
  $("assets").innerHTML = devices.length ? devices.map((item) => `<tr class="device-row" data-asset-id="${item.assetId || ""}"><td data-label="Устройство"><div class="device-name"><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml([item.inventoryNumber,item.hostname].filter(Boolean).join(" · ") || "Не связано с Agent")}</small></div></td><td data-label="Расположение">${escapeHtml([item.organization,item.room].filter(Boolean).join(" · ") || "Не указано")}</td><td data-label="Состояние">${pill(item.status)}${item.endpoint?.open_changes ? `<small>${item.endpoint.open_changes} откр. изм.</small>` : ""}</td><td data-label="Последняя проверка"><strong>${escapeHtml(relativeTime(item.endpoint?.last_seen_at))}</strong><small>${dateTime(item.endpoint?.last_seen_at)}</small></td><td data-label="Оборудование"><span class="hardware-brief">${escapeHtml(hardwareBrief(item.endpoint))}</span></td><td data-label="Действие">${item.assetId ? '<button class="row-action" aria-label="Открыть карточку">→</button>' : `<button class="link-endpoint button-secondary" data-id="${item.endpointId}" data-name="${escapeHtml(item.hostname || "")}">Связать</button>`}</td></tr>`).join("") : '<tr><td colspan="6"><p class="empty">По заданным условиям устройства не найдены.</p></td></tr>';
  $("device-result-count").textContent = `Показано ${devices.length} из ${state.devices.length}`;
  document.querySelectorAll("tr.device-row[data-asset-id]").forEach((row) => { if (row.dataset.assetId) row.onclick = () => detail(row.dataset.assetId); }); bindDynamicActions();
}
function bindDynamicActions() {
  document.querySelectorAll(".open-device").forEach((button) => button.onclick = () => detail(button.dataset.id));
  document.querySelectorAll(".link-endpoint").forEach((button) => button.onclick = (event) => { event.stopPropagation(); openLink(button.dataset.id, button.dataset.name); });
}
function factRows(items) { const rows = items.filter(([,value]) => value !== null && value !== undefined && value !== ""); return rows.length ? rows.map(([label,value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`).join("") : '<p class="empty">Данные пока не получены.</p>'; }
function rawValue(raw, keys) { for (const key of keys) if (raw?.[key] !== undefined && raw[key] !== "") return raw[key]; return null; }
function componentPrimary(item) { const raw = item.raw_data || {}; return item.model || rawValue(raw,["name","description","caption","chipset"]) || "Модель не определена"; }
function componentMeta(item) {
  const raw = item.raw_data || {}; const values = [];
  if (item.type === "RAM") values.push(item.capacity ? bytes(item.capacity) : null, raw.speed ? `${raw.speed} МГц` : null, item.slot, item.manufacturer, item.part_number ? `P/N ${item.part_number}` : null, item.serial ? `S/N ${item.serial}` : null, raw.type);
  else if (item.type === "STORAGE") values.push(raw.disksize != null ? storageSize(raw.disksize) : null, raw.type, raw.interface, raw.firmware ? `FW ${raw.firmware}` : null, item.serial ? `S/N ${item.serial}` : null);
  else if (item.type === "CPU") values.push(raw.core ? `${raw.core} ядер` : null, raw.thread ? `${raw.thread} потоков` : null, raw.speed ? `${raw.speed} МГц` : null, raw.manufacturer, raw.id);
  else if (item.type === "GPU") values.push(raw.memory ? `${raw.memory} МБ памяти` : null, raw.resolution, raw.chipset, raw.pcislot);
  else if (item.type === "NETWORK") values.push(raw.macaddr || raw.mac, raw.ipaddress || raw.ip, raw.status, raw.speed, raw.type);
  else if (item.type === "DRIVE") values.push(raw.letter || raw.label, raw.filesystem, raw.total != null ? `Всего ${bytes(raw.total)}` : null, raw.free != null ? `Свободно ${bytes(raw.free)}` : null, raw.systemdrive ? "Системный" : null);
  else if (item.type === "CONTROLLER") values.push(raw.manufacturer, raw.type, raw.pcislot, raw.vendorid && raw.productid ? `${raw.vendorid}:${raw.productid}` : null);
  else if (item.type === "MOTHERBOARD") values.push(item.manufacturer, item.part_number, item.serial ? `S/N ${item.serial}` : null);
  else values.push(item.manufacturer, item.serial ? `S/N ${item.serial}` : null, item.slot);
  return values.filter(Boolean);
}
function hardware(items) {
  if (!items?.length) return '<div class="panel"><p class="empty">Agent пока не передал сведения об оборудовании.</p></div>';
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
    const asset = await api(`/admin/assets/${assetId}`); state.selectedAsset = assetId; const endpoint = asset.endpoint; const status = deviceStatus(endpoint);
    $("detail-title").textContent = asset.name; $("detail-status").innerHTML = pill(status);
    $("detail-meta").textContent = [asset.inventory_number,endpoint?.hostname,asset.organization,asset.room].filter(Boolean).join(" · ") || "Карточка актива";
    $("detail-actions").innerHTML = '<button id="edit-asset" class="button-secondary">Редактировать</button>';
    $("edit-asset").onclick = async () => { const name = prompt("Название устройства",asset.name); if(name && name !== asset.name) await sendAction(`/admin/assets/${asset.id}`,{name},"PATCH","Название обновлено"); };
    const hardwareInfo = asset.system?.hardware || {}, bios = asset.system?.bios || {}, os = asset.system?.operating_system || {};
    $("device-general").innerHTML = factRows([["Название",asset.name],["Hostname",endpoint?.hostname],["Тип",asset.asset_type],["Организация",asset.organization],["Кабинет",asset.room],["Статус",statusLabels[status]],["Последнее подключение",dateTime(endpoint?.last_seen_at)],["Последняя проверка",dateTime(asset.latest_inventory?.received_at)]]);
    $("device-system").innerHTML = factRows([["Операционная система",os.full_name || os.name],["Версия",os.version],["Сборка / ядро",os.kernel_version],["Архитектура",os.arch],["BIOS",bios.bversion],["Дата BIOS",bios.bdate],["Производитель",bios.smanufacturer || bios.bmanufacturer],["Модель",bios.smodel || bios.mmodel],["Серийный номер",bios.ssn || bios.msn],["Корпус",hardwareInfo.chassis_type],["Рабочая группа",hardwareInfo.workgroup]]);
    $("device-identifiers").innerHTML = factRows((endpoint?.identifiers || []).map((item) => [({SMBIOS_UUID:"Device UUID",CHASSIS_SERIAL:"Серийный номер корпуса",MOTHERBOARD_SERIAL:"Серийный номер платы",BIOS_SERIAL:"Серийный номер BIOS",AGENT_DEVICE_ID:"ID агента",MAC:"MAC-адрес"}[item.type] || item.type),item.value]));
    $("snapshot-meta").textContent = asset.current_snapshot ? `${asset.current_snapshot.type === "FULL" ? "Полная" : "Частичная"} проверка · ${dateTime(asset.current_snapshot.captured_at)}` : "Данных пока нет";
    const supplemental = [...(asset.system?.drives || []).map((raw_data) => ({type:"DRIVE",raw_data,model:raw_data.description || raw_data.label})),...(asset.system?.controllers || []).map((raw_data) => ({type:"CONTROLLER",raw_data,model:raw_data.name || raw_data.caption}))];
    $("current-hardware").innerHTML = hardware([...asset.current_hardware,...supplemental]); $("baseline-hardware").innerHTML = hardware(asset.baseline_hardware);
    $("baseline-summary").textContent = asset.baseline ? `Эталон подтверждён ${dateTime(asset.baseline.accepted_at)}${asset.baseline.reason ? ` · ${asset.baseline.reason}` : ""}` : "Эталонное состояние ещё не подтверждено.";
    $("baseline-action").innerHTML = asset.recommended_baseline_snapshot_id ? `<button id="accept-baseline">${asset.baseline ? "Обновить эталон" : "Подтвердить как эталон"}</button>` : "";
    if ($("accept-baseline")) $("accept-baseline").onclick = async () => { if (confirm("Подтвердить последний наблюдавшийся состав оборудования как новый эталон? Это действие не удаляет историю изменений.")) await sendAction(`/admin/snapshots/${asset.recommended_baseline_snapshot_id}/baseline`,{reason:"Подтверждено оператором в карточке устройства"},"POST","Эталонное состояние подтверждено"); };
    $("detail-changes").innerHTML = asset.baseline ? changeCards(asset.changes) : '<div class="attention-banner"><span class="attention-icon">!</span><div><strong>Эталон ещё не создан</strong><p>Подтвердите текущий состав, чтобы AssetGuard начал показывать изменения по принципу «Было → Стало».</p></div></div>';
    $("detail-incidents").innerHTML = asset.incidents.length ? asset.incidents.map((incident) => `<article class="row-card"><div class="row-title"><b>${escapeHtml((componentLabels[incident.title.split(":")[0]] || incident.title.split(":")[0]) + ": " + (eventLabels[incident.title.split(":")[1]?.trim()] || incident.title.split(":")[1]?.trim() || "изменение"))}</b>${pill(incident.status)}</div><div class="meta">${dateTime(incident.created_at)}</div>${["OPEN","UNDER_REVIEW"].includes(incident.status) ? `<div class="actions"><button class="classify button-secondary" data-id="${incident.id}">Взять на проверку</button><button class="resolve" data-id="${incident.id}">Подтвердить решение</button></div>` : ""}</article>`).join("") : '<p class="empty">Открытых обращений нет.</p>';
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
function openLink(endpointId,hostname) { state.linkingEndpoint=endpointId; $("link-target").textContent=`Устройство: ${hostname || endpointId}`; $("link-asset").innerHTML=state.assets.filter((asset) => !asset.endpoint_id).map((asset) => `<option value="${asset.id}">${escapeHtml(asset.inventory_number)} — ${escapeHtml(asset.name)}</option>`).join(""); if(!$("link-asset").options.length){showToast("Сначала добавьте свободный актив",true);return;} $("link-dialog").showModal(); }

function visionCountRows(counts) { const entries=Object.entries(counts||{}); return entries.length ? entries.map(([name,count]) => `<div class="count-row"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>`).join("") : '<p class="empty">Объекты выбранных классов не найдены.</p>'; }
async function renderVisionScan(scan,roomName) {
  state.visionScan=scan; state.visionRoomId=scan.room_id; $("vision-result").hidden=false; $("vision-room-title").textContent=roomName||"Кабинет"; $("vision-status-badge").innerHTML=statusLabels[scan.status]||scan.status; $("vision-status-badge").className=`status-pill ${classForStatus(scan.status)}`; $("vision-counts").innerHTML=visionCountRows(scan.counts);
  const differences=scan.comparison?.differences||[]; $("vision-comparison").innerHTML=scan.status==="NOT_CHECKED" ? '<p class="empty">Эталон ещё не подтверждён.</p>' : differences.length ? differences.map((item)=>`<div class="comparison-row warning"><span>${escapeHtml(item.class_name)}</span><span>ожидалось ${item.expected}, найдено ${item.detected}</span><strong>${item.difference>0?"+":""}${item.difference}</strong></div>`).join("") : '<div class="comparison-ok">Количество объектов соответствует эталону.</div>';
  $("vision-baseline").textContent=scan.status==="NOT_CHECKED"?"Подтвердить как эталон":"Обновить эталон"; if(state.visionImageUrl) URL.revokeObjectURL(state.visionImageUrl); const blob=await apiBlob(scan.annotated_image_url); state.visionImageUrl=URL.createObjectURL(blob); $("vision-image").src=state.visionImageUrl;
}
async function loadVisionHistory(roomId) { if(!roomId){$("vision-history").innerHTML='<p class="empty">Загрузите первое фото помещения.</p>';return;} const scans=await api(`/admin/vision/rooms/${roomId}/scans`); const room=state.visionRooms.find((item)=>item.id===roomId); $("vision-history").innerHTML=scans.map((scan)=>`<button class="vision-history-item" data-id="${scan.id}"><span><b>${dateTime(scan.created_at)}</b><small>${Object.entries(scan.counts).map(([name,count])=>`${escapeHtml(name)}: ${count}`).join(" · ")||"Объекты не найдены"}</small></span>${pill(scan.status)}</button>`).join("")||'<p class="empty">История проверок пуста.</p>'; document.querySelectorAll(".vision-history-item").forEach((button)=>button.onclick=async()=>renderVisionScan(await api(`/admin/vision/scans/${button.dataset.id}`),room?.name)); }
function renderVisionRooms(rooms) { state.visionRooms=rooms; $("vision-room-select").innerHTML=rooms.length?rooms.map((room)=>`<option value="${room.id}">${escapeHtml(room.name)}</option>`).join(""):'<option value="">Проверок пока нет</option>'; if(rooms.length){const selected=rooms.find((room)=>room.id===state.visionRoomId)||rooms[0];state.visionRoomId=selected.id;$("vision-room-select").value=selected.id;loadVisionHistory(selected.id);if(!state.visionScan&&selected.latest_scan)renderVisionScan(selected.latest_scan,selected.name);}else loadVisionHistory(null); }

async function load(showLoading=true) {
  if(showLoading){$("status").textContent="Обновляем данные…";$("attention-banner").className="attention-banner is-loading";}
  try { const [assets,endpoints,changes,incidents,visionRooms]=await Promise.all([api("/admin/assets"),api("/admin/endpoints"),api("/admin/changes"),api("/admin/incidents"),api("/admin/vision/rooms")]); state={...state,assets,endpoints,changes,incidents,visionRooms}; buildDevices(); renderDashboard(); renderDevices(); renderVisionRooms(visionRooms); $("status").textContent=`Данные актуальны · ${dateTime(new Date())}`; }
  catch(error){$("status").textContent=error.message;$("attention-banner").className="attention-banner error";$("attention-banner").innerHTML=`<span class="attention-icon">!</span><div><strong>Не удалось загрузить Dashboard</strong><p>${escapeHtml(error.message)}</p></div>`;showToast(error.message,true);}
}

$("token-form").addEventListener("submit",async(event)=>{event.preventDefault();const username=$("username").value.trim(),secret=$("token").value;try{if(username){const response=await fetch("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password:secret})});if(!response.ok)throw new Error("Неверный логин или пароль");token=(await response.json()).access_token;}else token=secret;sessionStorage.setItem("assetguard-admin-token",token);$("token").value="";await load();showToast("Вход выполнен");}catch(error){$("status").textContent=error.message;showToast(error.message,true);}});
$("logout").onclick=async()=>{if(token)await fetch("/auth/logout",{method:"POST",headers:{"X-AssetGuard-Admin-Token":token}}).catch(()=>{});token="";sessionStorage.removeItem("assetguard-admin-token");state={...state,assets:[],endpoints:[],devices:[],changes:[],incidents:[]};$("status").textContent="Сессия завершена.";showToast("Вы вышли из системы");};
$("show-create").onclick=()=>{$("create-asset").hidden=!$("create-asset").hidden;};
$("create-asset").addEventListener("submit",async(event)=>{event.preventDefault();const form=event.currentTarget;try{await api("/admin/assets",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(new FormData(form).entries()))});form.reset();form.hidden=true;showToast("Актив добавлен");await load(false);}catch(error){showToast(error.message,true);}});
$("link-form").addEventListener("submit",async(event)=>{event.preventDefault();if(!state.linkingEndpoint||!$("link-asset").value)return;try{await api(`/admin/endpoints/${state.linkingEndpoint}/asset/${$("link-asset").value}`,{method:"POST"});$("link-dialog").close();showToast("Устройство связано с активом");await load(false);}catch(error){showToast(error.message,true);}});$("link-cancel").onclick=()=>$("link-dialog").close();
[$("device-search"),$("device-status-filter"),$("device-room-filter"),$("device-change-filter"),$("device-sort")].forEach((control)=>control.addEventListener(control.type==="search"?"input":"change",renderDevices));
$("detail-back").onclick=()=>{location.hash="devices";};
$("vision-upload").addEventListener("submit",async(event)=>{event.preventDefault();const button=$("vision-run");button.disabled=true;$("vision-progress").textContent="Анализируем фото… Первый запуск может занять несколько минут.";try{const form=new FormData(event.currentTarget);const scan=await api("/admin/vision/scans",{method:"POST",body:form});state.visionRoomId=scan.room_id;const rooms=await api("/admin/vision/rooms");renderVisionRooms(rooms);await renderVisionScan(scan,rooms.find((item)=>item.id===scan.room_id)?.name||form.get("room_name"));await loadVisionHistory(scan.room_id);$("vision-progress").textContent=`Анализ завершён: найдено объектов — ${scan.detections.length}. Проверьте результат.`;}catch(error){$("vision-progress").textContent=error.message;showToast(error.message,true);}finally{button.disabled=false;}});
$("vision-baseline").onclick=async()=>{if(!state.visionScan)return;if(!confirm("Подтвердить результат этой проверки как эталон кабинета?"))return;try{await api(`/admin/vision/rooms/${state.visionScan.room_id}/baseline`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scan_id:state.visionScan.id})});const scan=await api(`/admin/vision/scans/${state.visionScan.id}`);await renderVisionScan(scan,state.visionRooms.find((room)=>room.id===scan.room_id)?.name);await loadVisionHistory(scan.room_id);$("vision-progress").textContent="Эталон подтверждён. Следующее фото будет сравнено с ним.";showToast("Эталон помещения сохранён");}catch(error){showToast(error.message,true);}};
$("vision-room-select").onchange=async(event)=>{state.visionRoomId=event.target.value;const room=state.visionRooms.find((item)=>item.id===state.visionRoomId);state.visionScan=room?.latest_scan||null;if(state.visionScan)await renderVisionScan(state.visionScan,room.name);await loadVisionHistory(state.visionRoomId);};
if(token)load();
