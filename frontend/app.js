const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("assetguard-admin-token") || "";
let state = {assets: [], endpoints: [], changes: [], incidents: [], visionRooms: [], selectedAsset: null, linkingEndpoint: null, visionRoomId: null, visionScan: null, visionImageUrl: null};
$("token").value = token;

const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => (
  {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]
));
const dateTime = (value) => value ? new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "short", timeStyle: "medium"
}).format(new Date(value)) : "—";
const capacity = (value) => {
  if (value == null) return "";
  if (value >= 1073741824) return `${(value / 1073741824).toFixed(1)} ГБ`;
  if (value >= 1048576) return `${(value / 1048576).toFixed(1)} МБ`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} КБ`;
  return `${value} Б`;
};
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {...options.headers, "X-AssetGuard-Admin-Token": token}});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(response.status === 401 ? "Неверный admin token" : body.detail || `Ошибка API: ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}
async function apiBlob(path) {
  const response = await fetch(path, {headers: {"X-AssetGuard-Admin-Token": token}});
  if (!response.ok) throw new Error(`Ошибка загрузки изображения: ${response.status}`);
  return response.blob();
}
const labels = {RAM:"Оперативная память", STORAGE:"Накопители", CPU:"Процессор", GPU:"Видеокарта", MOTHERBOARD:"Материнская плата", NETWORK:"Сетевые интерфейсы", MONITOR:"Мониторы", ENDPOINT:"Endpoint"};
const badge = (value) => `<span class="badge badge-${String(value).toLowerCase()}">${escapeHtml(value)}</span>`;
function hardware(items) {
  if (!items.length) return '<p class="empty">Нет наблюдаемых данных.</p>';
  const grouped = items.reduce((result, item) => { (result[item.type] ||= []).push(item); return result; }, {});
  return Object.entries(grouped).map(([type, group]) => `
    <div class="hardware-group"><h4>${escapeHtml(labels[type] || type)}</h4>
    ${group.map((item) => `<div class="hardware-row"><b>${escapeHtml(item.model || "Модель не определена")}</b><span>${[capacity(item.capacity), item.slot, item.serial, item.confidence].filter(Boolean).map(escapeHtml).join(" · ") || "Нет дополнительных данных"}</span></div>`).join("")}</div>`).join("");
}
async function sendAction(path, payload, method = "POST") {
  await api(path, {method, headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
  $("status").textContent = "Действие сохранено.";
  await load();
  if (state.selectedAsset) await detail(state.selectedAsset);
}
async function detail(assetId) {
  try {
    const asset = await api(`/admin/assets/${assetId}`);
    state.selectedAsset = assetId;
    $("detail").hidden = false;
    $("detail-title").textContent = `${asset.inventory_number} — ${asset.name}`;
    $("detail-meta").textContent = asset.endpoint
      ? `${asset.endpoint.hostname || "Без hostname"} · ${asset.endpoint.status} · last seen ${dateTime(asset.endpoint.last_seen_at)}` : "Endpoint не связан";
    $("current-hardware").innerHTML = hardware(asset.current_hardware);
    $("baseline-hardware").innerHTML = hardware(asset.baseline_hardware);
    $("detail-actions").innerHTML = `<button id="edit-asset" class="secondary">Редактировать</button>${asset.current_snapshot_id ? '<button id="accept-baseline">Принять current как baseline</button>' : ""}`;
    $("edit-asset").onclick = async () => {
      const name = prompt("Название актива", asset.name);
      if (name && name !== asset.name) await sendAction(`/admin/assets/${asset.id}`, {name}, "PATCH");
    };
    const accept = $("accept-baseline");
    if (accept) accept.onclick = () => sendAction(`/admin/snapshots/${asset.current_snapshot_id}/baseline`, {reason: "Accepted from Asset card"});
    $("detail-changes").innerHTML = asset.changes.map((change) => `
      <details class="row-card"><summary><b>${escapeHtml(labels[change.component_type] || change.component_type)} · ${escapeHtml(change.type)}</b>${badge(change.status)}</summary>
      <div class="meta">${escapeHtml(change.confidence)} · ${escapeHtml(change.severity)} · ${dateTime(change.detected_at)}</div>
      <pre>${escapeHtml(JSON.stringify(change.evidence, null, 2))}</pre></details>`).join("") || '<p class="empty">Изменений нет.</p>';
    $("detail-incidents").innerHTML = asset.incidents.map((incident) => `
      <article class="row-card"><div class="row-title"><b>${escapeHtml(incident.title)}</b>${badge(incident.status)}</div>
      <div class="meta">${escapeHtml(incident.severity)} · ${dateTime(incident.created_at)}</div>
      ${["OPEN","UNDER_REVIEW"].includes(incident.status) ? `<div class="actions"><button class="classify secondary" data-id="${incident.id}">Классифицировать</button><button class="resolve" data-id="${incident.id}">Закрыть</button></div>` : ""}</article>`).join("") || '<p class="empty">Incident’ов нет.</p>';
    document.querySelectorAll(".classify").forEach((button) => button.onclick = () => incidentAction(button.dataset.id, false));
    document.querySelectorAll(".resolve").forEach((button) => button.onclick = () => incidentAction(button.dataset.id, true));
    $("detail-history").innerHTML = asset.history.map((entry) => `<article><time>${dateTime(entry.occurred_at)}</time><div><b>${escapeHtml(entry.type)}</b><p>${escapeHtml(entry.message)}</p></div></article>`).join("") || '<p class="empty">Истории пока нет.</p>';
    $("detail").scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) { $("status").textContent = error.message; }
}
async function incidentAction(id, resolve) {
  const classification = prompt("Classification", resolve ? "AUTHORIZED_CHANGE" : "REQUIRES_INVESTIGATION");
  if (!classification) return;
  const comment = prompt("Комментарий", "") || null;
  await sendAction(`/admin/incidents/${id}/${resolve ? "resolve" : "decision"}`, {classification, actor: "admin", comment});
}
function openLink(endpointId, hostname) {
  state.linkingEndpoint = endpointId;
  $("link-target").textContent = hostname || endpointId;
  $("link-asset").innerHTML = state.assets.map((asset) => `<option value="${asset.id}">${escapeHtml(asset.inventory_number)} — ${escapeHtml(asset.name)}</option>`).join("");
  $("link-dialog").showModal();
}
function visionCountRows(counts) {
  const entries = Object.entries(counts || {});
  return entries.length ? entries.map(([name, count]) => `<div class="count-row"><span>${escapeHtml(name)}</span><strong>${count}</strong></div>`).join("") : '<p class="empty">Объекты выбранных классов не найдены.</p>';
}
async function renderVisionScan(scan, roomName) {
  state.visionScan = scan;
  state.visionRoomId = scan.room_id;
  $("vision-result").hidden = false;
  $("vision-room-title").textContent = roomName || "Помещение";
  $("vision-status-badge").textContent = scan.status;
  $("vision-status-badge").className = `badge badge-${scan.status.toLowerCase()}`;
  $("vision-counts").innerHTML = visionCountRows(scan.counts);
  const differences = scan.comparison?.differences || [];
  $("vision-comparison").innerHTML = scan.status === "NOT_CHECKED"
    ? '<p class="empty">Baseline ещё не сохранён.</p>'
    : differences.length
      ? differences.map((item) => `<div class="comparison-row warning"><span>${escapeHtml(item.class_name)}</span><span>expected ${item.expected} · detected ${item.detected}</span><strong>${item.difference > 0 ? "+" : ""}${item.difference}</strong></div>`).join("")
      : '<div class="comparison-ok">Counts соответствуют baseline.</div>';
  $("vision-baseline").textContent = scan.status === "NOT_CHECKED" ? "Save as baseline" : "Update baseline";
  if (state.visionImageUrl) URL.revokeObjectURL(state.visionImageUrl);
  const blob = await apiBlob(scan.annotated_image_url);
  state.visionImageUrl = URL.createObjectURL(blob);
  $("vision-image").src = state.visionImageUrl;
}
async function loadVisionHistory(roomId) {
  if (!roomId) {
    $("vision-history").innerHTML = '<p class="empty">Загрузите первое фото помещения.</p>';
    return;
  }
  const scans = await api(`/admin/vision/rooms/${roomId}/scans`);
  const room = state.visionRooms.find((item) => item.id === roomId);
  $("vision-history").innerHTML = scans.map((scan) => `
    <button class="vision-history-item secondary" data-id="${scan.id}">
      <span><b>${dateTime(scan.created_at)}</b><small>${Object.entries(scan.counts).map(([name,count]) => `${escapeHtml(name)}: ${count}`).join(" · ") || "0 detections"}</small></span>
      ${badge(scan.status)}
    </button>`).join("") || '<p class="empty">Scan history пуста.</p>';
  document.querySelectorAll(".vision-history-item").forEach((button) => button.onclick = async () => {
    const scan = await api(`/admin/vision/scans/${button.dataset.id}`);
    await renderVisionScan(scan, room?.name);
  });
}
function renderVisionRooms(rooms) {
  state.visionRooms = rooms;
  $("vision-room-select").innerHTML = rooms.length
    ? rooms.map((room) => `<option value="${room.id}">${escapeHtml(room.name)}</option>`).join("")
    : '<option value="">Помещения пока не проверялись</option>';
  if (rooms.length) {
    const selected = rooms.find((room) => room.id === state.visionRoomId) || rooms[0];
    state.visionRoomId = selected.id;
    $("vision-room-select").value = selected.id;
    loadVisionHistory(selected.id);
    if (!state.visionScan && selected.latest_scan) renderVisionScan(selected.latest_scan, selected.name);
  } else {
    loadVisionHistory(null);
  }
}
async function load() {
  try {
    const [assets, endpoints, changes, incidents, visionRooms] = await Promise.all([api("/admin/assets"), api("/admin/endpoints"), api("/admin/changes"), api("/admin/incidents"), api("/admin/vision/rooms")]);
    state = {...state, assets, endpoints, changes, incidents, visionRooms};
    $("assets-count").textContent = assets.length; $("endpoints-count").textContent = endpoints.length;
    $("changes-count").textContent = changes.length;
    $("incidents-count").textContent = incidents.filter((item) => ["OPEN","UNDER_REVIEW"].includes(item.status)).length;
    $("assets").innerHTML = assets.map((asset) => `<tr data-id="${asset.id}" class="asset-row"><td><b>${escapeHtml(asset.inventory_number)}</b></td><td>${escapeHtml(asset.name)}</td><td>${escapeHtml(asset.asset_type)}</td><td>${badge(asset.status)}</td><td>${asset.endpoint_id ? "Связан" : '<span class="muted">Не связан</span>'}</td></tr>`).join("") || '<tr><td colspan="5" class="empty">Активов пока нет</td></tr>';
    document.querySelectorAll(".asset-row").forEach((row) => row.onclick = () => detail(row.dataset.id));
    $("endpoints").innerHTML = endpoints.map((endpoint) => `<tr><td><b>${escapeHtml(endpoint.hostname || "Без hostname")}</b><small>${escapeHtml(endpoint.source_agent_id)}</small></td><td>${badge(endpoint.status)}</td><td>${dateTime(endpoint.last_seen_at)}</td><td>${endpoint.asset_id ? "Связан" : `<button class="link-endpoint secondary" data-id="${endpoint.id}" data-name="${escapeHtml(endpoint.hostname || "")}">Связать</button>`}</td></tr>`).join("") || '<tr><td colspan="4" class="empty">Endpoints пока не наблюдались</td></tr>';
    document.querySelectorAll(".link-endpoint").forEach((button) => button.onclick = () => openLink(button.dataset.id, button.dataset.name));
    $("changes").innerHTML = changes.slice(0, 8).map((item) => `<article class="row-card"><div class="row-title"><b>${escapeHtml(item.component_type)} · ${escapeHtml(item.type)}</b>${badge(item.status)}</div><div class="meta">${escapeHtml(item.confidence)} / ${escapeHtml(item.severity)} · ${dateTime(item.detected_at)}</div></article>`).join("") || '<p class="empty">Изменений нет.</p>';
    $("incidents").innerHTML = incidents.slice(0, 8).map((item) => `<article class="row-card"><div class="row-title"><b>${escapeHtml(item.title)}</b>${badge(item.status)}</div><div class="meta">${escapeHtml(item.severity)} · ${dateTime(item.created_at)}</div></article>`).join("") || '<p class="empty">Incident’ов нет.</p>';
    renderVisionRooms(visionRooms);
    $("status").textContent = `Данные обновлены · ${dateTime(new Date())}`;
  } catch (error) { $("status").textContent = error.message; }
}
$("token-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = $("username").value.trim();
  const secret = $("token").value;
  try {
    if (username) {
      const response = await fetch("/auth/login", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password: secret}),
      });
      if (!response.ok) throw new Error("Неверный username или password");
      token = (await response.json()).access_token;
    } else {
      token = secret;
    }
    sessionStorage.setItem("assetguard-admin-token", token);
    $("token").value = "";
    await load();
  } catch (error) {
    $("status").textContent = error.message;
  }
});
$("logout").onclick = async () => {
  if (token) await fetch("/auth/logout", {method: "POST", headers: {"X-AssetGuard-Admin-Token": token}}).catch(() => {});
  token = "";
  sessionStorage.removeItem("assetguard-admin-token");
  $("status").textContent = "Сессия завершена.";
};
$("show-create").onclick = () => $("create-asset").hidden = !$("create-asset").hidden;
$("create-asset").addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendAction("/admin/assets", Object.fromEntries(new FormData(event.currentTarget).entries()));
  event.currentTarget.reset(); event.currentTarget.hidden = true;
});
$("link-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.linkingEndpoint || !$("link-asset").value) return;
  await api(`/admin/endpoints/${state.linkingEndpoint}/asset/${$("link-asset").value}`, {method: "POST"});
  $("link-dialog").close(); await load();
});
$("link-cancel").onclick = () => $("link-dialog").close();
$("vision-upload").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("vision-run");
  button.disabled = true;
  $("vision-progress").textContent = "Выполняется object detection… первый запуск включает загрузку модели.";
  try {
    const form = new FormData(event.currentTarget);
    const scan = await api("/admin/vision/scans", {method: "POST", body: form});
    state.visionRoomId = scan.room_id;
    const rooms = await api("/admin/vision/rooms");
    renderVisionRooms(rooms);
    const room = rooms.find((item) => item.id === scan.room_id);
    await renderVisionScan(scan, room?.name || form.get("room_name"));
    await loadVisionHistory(scan.room_id);
    $("vision-progress").textContent = `Готово: ${scan.detections.length} detections · ${scan.model_id}`;
  } catch (error) {
    $("vision-progress").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
$("vision-baseline").onclick = async () => {
  if (!state.visionScan) return;
  try {
    await api(`/admin/vision/rooms/${state.visionScan.room_id}/baseline`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({scan_id: state.visionScan.id}),
    });
    const scan = await api(`/admin/vision/scans/${state.visionScan.id}`);
    await renderVisionScan(scan, state.visionRooms.find((room) => room.id === scan.room_id)?.name);
    await loadVisionHistory(scan.room_id);
    $("vision-progress").textContent = "Baseline сохранён. Загрузите повторное фото для сравнения.";
  } catch (error) {
    $("vision-progress").textContent = error.message;
  }
};
$("vision-room-select").onchange = async (event) => {
  state.visionRoomId = event.target.value;
  const room = state.visionRooms.find((item) => item.id === state.visionRoomId);
  state.visionScan = room?.latest_scan || null;
  if (state.visionScan) await renderVisionScan(state.visionScan, room.name);
  await loadVisionHistory(state.visionRoomId);
};
if (token) load();
