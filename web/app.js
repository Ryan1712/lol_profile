const view = document.getElementById("view");
const banner = document.getElementById("banner");
const backBtn = document.getElementById("back");
const search = document.getElementById("search");
let allTeams = [];

function showBanner(msg) { banner.textContent = msg; banner.hidden = !msg; }
function api(path, opts) {
  return fetch(path, opts).then((r) => r.json());
}
function pct(x) { return Math.round((x || 0) * 100) + "%"; }
function esc(s) { return (s || "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

async function showTeams() {
  backBtn.hidden = true;
  const data = await api("/api/teams");
  allTeams = data.teams;
  search.hidden = false;
  renderTeams(allTeams);
}

function renderTeams(teams) {
  const byRegion = {};
  teams.forEach((t) => { (byRegion[t.region] = byRegion[t.region] || []).push(t); });
  view.innerHTML = Object.keys(byRegion).map((region) => `
    <div class="region-title">${esc(region)}</div>
    <div class="grid">
      ${byRegion[region].map((t) => `
        <div class="team-card" data-id="${t.id}">
          <h3>${esc(t.name)}</h3>
          <div class="meta">${t.member_count} người</div>
          <div class="meta">${t.refreshed_at
            ? "cập nhật " + new Date(t.refreshed_at).toLocaleString("vi-VN")
            : "chưa quét"}</div>
        </div>`).join("")}
    </div>`).join("");
  view.querySelectorAll(".team-card").forEach((el) =>
    el.addEventListener("click", () => showTeam(el.dataset.id)));
}

search.addEventListener("input", () => {
  const q = search.value.toLowerCase();
  renderTeams(allTeams.filter((t) => t.name.toLowerCase().includes(q)));
});

async function showTeam(teamId) {
  showBanner("");
  backBtn.hidden = false;
  search.hidden = true;
  const { team, snapshot } = await api("/api/team/" + teamId);
  renderTeam(team, snapshot);
}

function rankCell(rank) {
  if (!rank) return '<span class="muted">Chưa xếp hạng</span>';
  const total = (rank.wins || 0) + (rank.losses || 0);
  const wr = total ? rank.wins / total : 0;
  const wrClass = wr >= 0.5 ? "wr-win" : "wr-loss";
  return `<span class="rank-badge tier-${rank.tier}">${rank.tier} ${rank.rank}</span>
    · ${rank.lp} LP<br><span class="${wrClass}">${rank.wins}T/${rank.losses}B (${pct(wr)})</span>`;
}

function champCell(champs) {
  if (!champs || !champs.length) return '<span class="muted">—</span>';
  return `<div class="champs">${champs.map((c) => `
    <div class="champ" title="KDA ${c.kda.toFixed(2)} — ${c.k.toFixed(1)}/${c.d.toFixed(1)}/${c.a.toFixed(1)} · ${c.games} trận">
      <img src="/assets/champions/${esc(c.champion)}.png"
           onerror="this.style.visibility='hidden'" alt="${esc(c.champion)}" />
      <div class="c-meta">${esc(c.champion)}<br>KDA ${c.kda.toFixed(1)} · ${pct(c.winrate)}</div>
    </div>`).join("")}</div>`;
}

function laneCell(lanes) {
  if (!lanes || !lanes.length) return '<span class="muted">—</span>';
  return lanes.slice(0, 2).map((l) => `${l[0]} ${pct(l[1])}`).join(" · ");
}

function memberRow(m, res) {
  const lmss = m.game_name
    ? `https://lmssplus.org/?name=${encodeURIComponent(m.game_name)}&tag=${encodeURIComponent(m.tag_line)}`
    : "https://lmssplus.org/";
  const idCell = m.status === "ok"
    ? `${esc(m.game_name)}#${esc(m.tag_line)}`
    : `<span class="tag-warn">⚠ cần bổ sung Riot ID</span>`;
  const edit = `<div class="edit-inline">
      <input placeholder="Tên#TAG" value="${esc(m.raw_ingame)}" data-stt="${m.stt}" />
      <button data-save="${m.stt}">Lưu</button></div>`;
  if (!res || res.error === "needs_riot_id") {
    return `<tr>
      <td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}
        <a class="lmss" href="${lmss}" target="_blank">Mở LMSS+</a></td>
      <td colspan="4" class="muted">${res && res.error === "needs_riot_id"
        ? "Chưa tra được — thiếu Riot ID" : "Chưa quét"}</td></tr>`;
  }
  if (res.error === "not_found") {
    return `<tr><td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}</td>
      <td colspan="4" class="tag-warn">Không tìm thấy Riot ID này — sửa lại?</td></tr>`;
  }
  if (res.error === "network") {
    return `<tr><td><b>${esc(m.full_name)}</b><br>${idCell}</td>
      <td colspan="4" class="wr-loss">Lỗi mạng khi tra</td></tr>`;
  }
  return `<tr>
    <td><b>${esc(m.full_name)}</b><br>${idCell}<br>${edit}
      <a class="lmss" href="${lmss}" target="_blank">Mở LMSS+</a></td>
    <td>${rankCell(res.solo)}</td>
    <td>${rankCell(res.flex)}</td>
    <td>${laneCell(res.lanes)}</td>
    <td>${champCell(res.top_champions)}</td></tr>`;
}

function renderTeam(team, snapshot) {
  const results = (snapshot && snapshot.members) || {};
  view.innerHTML = `
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:12px">
      <input id="team-name" value="${esc(team.name)}" style="font-size:18px;font-weight:700" />
      <button id="save-name">Đổi tên</button>
      <button id="refresh" class="primary">⟳ Refresh</button>
      <span id="refreshed" class="muted">${snapshot
        ? "cập nhật " + new Date(snapshot.refreshed_at).toLocaleString("vi-VN") : ""}</span>
    </div>
    <table>
      <thead><tr><th>Người</th><th>Đơn/Đôi</th><th>Linh hoạt</th>
        <th>Lane</th><th>Top tướng</th></tr></thead>
      <tbody>${team.members.map((m) => memberRow(m, results[m.stt])).join("")}</tbody>
    </table>`;

  document.getElementById("refresh").addEventListener("click", async (e) => {
    e.target.disabled = true; e.target.textContent = "Đang quét…"; showBanner("");
    const out = await api("/api/team/" + team.id + "/refresh", { method: "POST" });
    if (out.error === "auth") showBanner("Không kết nối được Riot API — key sai/hết hạn. Gia hạn key ở developer.riotgames.com rồi thử lại.");
    else if (out.error === "network") showBanner("Không kết nối được Riot API — kiểm tra mạng/VPN. Đang xem dữ liệu cũ.");
    renderTeam(team, out.snapshot);
  });
  document.getElementById("save-name").addEventListener("click", async () => {
    const name = document.getElementById("team-name").value;
    await api("/api/team/" + team.id + "/rename", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }) });
    showBanner("Đã đổi tên đội.");
  });
  view.querySelectorAll("button[data-save]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const stt = btn.dataset.save;
      const input = view.querySelector(`input[data-stt="${stt}"]`);
      const r = await api("/api/member/" + stt + "/riot-id", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_ingame: input.value }) });
      renderTeam(r.team, snapshot);
      showBanner("Đã lưu Riot ID. Bấm Refresh để tra lại.");
    }));
}

backBtn.addEventListener("click", showTeams);
showTeams();
