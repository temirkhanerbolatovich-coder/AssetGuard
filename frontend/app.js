const $ = (id) => document.getElementById(id);
let token = sessionStorage.getItem("assetguard-admin-token") || "";
$("token").value = token;
const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
async function api(path, options = {}) { const response = await fetch(path, {...options, headers: {...options.headers, "X-AssetGuard-Admin-Token": token}}); if (!response.ok) throw new Error(response.status === 401 ? "Неверный admin token" : `Ошибка API: ${response.status}`); return response.json(); }
const hardware = (items) => items.length ? items.map((item) => `<div class="row"><b>${escapeHtml(item.type)} ${escapeHtml(item.model)}</b><span>${escapeHtml(item.serial)} · ${escapeHtml(item.slot)} · ${escapeHtml(item.confidence)}</span></div>`).join("") : "<p>Нет данных.</p>";
async function sendAction(path, payload) { await api(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)}); $("status").textContent = "Действие сохранено."; await load(); }
async function detail(assetId) {
  try {
    const asset = await api(`/admin/assets/${assetId}`); $("detail").hidden = false;
    $("detail-title").textContent = `${asset.inventory_number} — ${asset.name}`;
    $("detail-meta").textContent = asset.endpoint ? `${asset.endpoint.hostname || "—"} · ${asset.endpoint.status}` : "Endpoint не связан";
    $("current-hardware").innerHTML = hardware(asset.current_hardware); $("baseline-hardware").innerHTML = hardware(asset.baseline_hardware);
    $("detail-actions").innerHTML = asset.current_snapshot_id ? `<button id="accept-baseline">Принять current state как baseline</button>` : "";
    const button = $("accept-baseline"); if (button) button.onclick = () => sendAction(`/admin/snapshots/${asset.current_snapshot_id}/baseline`, {reason:"Accepted from Asset card"});
    $("detail-actions").innerHTML += asset.incidents.map((incident) => `<button class="classify" data-id="${incident.id}">Classify ${escapeHtml(incident.title)}</button><button class="resolve" data-id="${incident.id}">Resolve</button>`).join("");
    document.querySelectorAll(".classify").forEach((button) => button.onclick = () => { const classification = prompt("Classification", "REQUIRES_INVESTIGATION"); if (classification) sendAction(`/admin/incidents/${button.dataset.id}/decision`, {classification, actor:"admin", comment:"Classified from Asset card"}); });
    document.querySelectorAll(".resolve").forEach((button) => button.onclick = () => { const classification = prompt("Resolution classification", "AUTHORIZED_CHANGE"); if (classification) sendAction(`/admin/incidents/${button.dataset.id}/resolve`, {classification, actor:"admin", comment:"Resolved from Asset card"}); });
    $("detail-changes").innerHTML = asset.changes.map((change) => `<article class="row"><b>${escapeHtml(change.component_type)} · ${escapeHtml(change.type)}</b><span>${escapeHtml(change.confidence)} · evidence available</span></article>`).join("") || "<p>Изменений нет.</p>";
    $("detail-incidents").innerHTML = asset.incidents.map((incident) => `<article class="row"><b>${escapeHtml(incident.title)}</b><span>${escapeHtml(incident.status)} · ${escapeHtml(incident.severity)}</span></article>`).join("") || "<p>Incident’ов нет.</p>";
    $("detail-history").innerHTML = asset.history.map((entry) => `<article class="row"><b>${escapeHtml(entry.type)}</b><span>${escapeHtml(entry.message)}</span></article>`).join("") || "<p>Истории пока нет.</p>";
    $("detail").scrollIntoView({behavior:"smooth"});
  } catch (error) { $("status").textContent = error.message; }
}
async function load() {
  try { const [assets, changes, incidents] = await Promise.all([api("/admin/assets"), api("/admin/changes"), api("/admin/incidents")]); $("assets-count").textContent = assets.length; $("changes-count").textContent = changes.length; $("incidents-count").textContent = incidents.filter((item) => ["OPEN","UNDER_REVIEW"].includes(item.status)).length; $("assets").innerHTML = assets.map((asset) => `<tr data-id="${asset.id}" class="asset-row"><td>${escapeHtml(asset.inventory_number)}</td><td>${escapeHtml(asset.name)}</td><td>${escapeHtml(asset.asset_type)}</td><td>${escapeHtml(asset.status)}</td><td>${escapeHtml(asset.endpoint_id || "не связан")}</td></tr>`).join("") || "<tr><td colspan=\"5\">Активов пока нет</td></tr>"; document.querySelectorAll(".asset-row").forEach((row) => row.onclick = () => detail(row.dataset.id)); $("changes").innerHTML = changes.map((item) => `<article class="row"><b>${escapeHtml(item.component_type)} · ${escapeHtml(item.type)}</b><span>${escapeHtml(item.confidence)} / ${escapeHtml(item.severity)}</span></article>`).join("") || "<p>Изменений нет.</p>"; $("incidents").innerHTML = incidents.map((item) => `<article class="row"><b>${escapeHtml(item.title)}</b><span>${escapeHtml(item.status)} · ${escapeHtml(item.severity)}</span></article>`).join("") || "<p>Incident’ов нет.</p>"; $("status").textContent = "Данные обновлены."; } catch (error) { $("status").textContent = error.message; }
}
$("token-form").addEventListener("submit", (event) => { event.preventDefault(); token = $("token").value; sessionStorage.setItem("assetguard-admin-token", token); load(); });
if (token) load();
