// ISO 29110 DocGen — vanilla JS single-page UI
const $app = document.getElementById("app");
const STATUS_TH = { missing: "ยังไม่มี", draft: "ร่าง", verified: "Ver แล้ว", validated: "Val แล้ว", baseline: "Baseline" };
let catalog = null;

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(msg, isErr = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  t.hidden = false;
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.hidden = true), isErr ? 7000 : 3000);
}

async function api(path, opts = {}) {
  const init = { ...opts };
  if (opts.body && !(opts.body instanceof FormData)) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && !path.startsWith("/api/auth/") && me) {
    me = null; authState = null;
    toast("หมดเวลาเข้าสู่ระบบ กรุณาเข้าสู่ระบบใหม่", true);
    route();
  }
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function busy(btn, fn) {
  const label = btn.innerHTML;  // innerHTML keeps button icons
  btn.disabled = true;
  btn.textContent = "กำลังทำงาน…";
  try { return await fn(); }
  catch (e) { toast(e.message, true); }
  finally { btn.disabled = false; btn.innerHTML = label; }
}

// ── Icons (inline SVG, stroke = currentColor) ───────────────────────────────
const svg = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICON = {
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  edit: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
  upload: svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>'),
  download: svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>'),
  trash: svg('<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>'),
  doc: svg('<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h5"/>'),
  folder: svg('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
  sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  moon: svg('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>'),
  building: svg('<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1M10 21v-3h4v3"/>'),
  user: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  shield: svg('<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>'),
  gear: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>'),
  logout: svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>'),
  spark: svg('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>'),
};

// ── Router ──────────────────────────────────────────────────────────────────
let me = null;          // logged-in user (null = guest)
let authState = null;   // {user, needs_setup, registration_mode}

async function refreshAuth() {
  authState = await api("/api/auth/state");
  me = authState.user;
  return me;
}

async function route() {
  if (!authState) await refreshAuth();
  const parts = location.hash.replace(/^#\/?/, "").split("/");
  document.body.classList.toggle("guest", !me);
  if (!me) {
    renderUserMenu();
    return parts[0] === "register" || authState.needs_setup ? viewRegister() : viewLogin();
  }
  if (parts[0] === "login" || parts[0] === "register") { location.hash = "#/"; return; }
  document.body.dataset.role = me.role;
  if (!catalog) catalog = await api("/api/catalog");
  renderUserMenu();
  const section = ["settings", "admin", "profile"].includes(parts[0]) ? parts[0] : "home";
  document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === section));
  if (branding && parts[0] !== "settings") applyBranding(branding);
  try {
    if (parts[0] === "settings") return await viewSettings(parts[1]);
    if (parts[0] === "admin") return await viewAdmin(parts[1]);
    if (parts[0] === "profile") return await viewProfile();
    if (parts[0] === "p" && parts[1]) return await viewProject(+parts[1], parts[2] || "interview", parts[3]);
    return await viewProjects();
  } catch (e) {
    $app.innerHTML = `<div class="card"><b>เกิดข้อผิดพลาด:</b> ${esc(e.message)}</div>`;
  }
}
window.addEventListener("hashchange", route);
route();

// ── Account UI ──────────────────────────────────────────────────────────────
const initials = (name) => (name || "?").trim().split(/\s+/).map((w) => [...w][0]).slice(0, 2).join("").toUpperCase();
const ROLE_BADGE = { admin: "info", editor: "ok", viewer: "" };
const STATUS_BADGE = { active: ["ok", "ใช้งาน"], pending: ["warn", "รออนุมัติ"], disabled: ["err", "ระงับ"] };

function renderUserMenu() {
  const box = document.getElementById("userMenu");
  document.querySelectorAll(".admin-only").forEach((e) => (e.hidden = !me || me.role !== "admin"));
  document.querySelectorAll(".member-only").forEach((e) => (e.hidden = !me));
  if (!me) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <button type="button" class="user-btn" id="userBtn" aria-haspopup="menu">
      <span class="avatar">${esc(initials(me.name))}</span><span class="uname">${esc(me.name)}</span></button>
    <div class="menu" id="userDrop" hidden>
      <div class="menu-head"><b>${esc(me.name)}</b><span class="muted small">${esc(me.email)}</span>
        <span class="badge ${ROLE_BADGE[me.role]}">${esc(me.role_th)}</span></div>
      <a href="#/profile">${ICON.user} โปรไฟล์ของฉัน</a>
      ${me.role === "admin" ? `<a href="#/admin">${ICON.shield} จัดการระบบ</a><a href="#/settings">${ICON.gear} ตั้งค่า</a>` : ""}
      <button type="button" class="menu-item" id="logoutBtn">${ICON.logout} ออกจากระบบ</button>
    </div>`;
  const drop = document.getElementById("userDrop");
  document.getElementById("userBtn").onclick = (e) => { e.stopPropagation(); drop.hidden = !drop.hidden; };
  drop.onclick = () => (drop.hidden = true);
  document.getElementById("logoutBtn").onclick = async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => {});
    me = null; authState = null; catalog = null;
    if (location.hash !== "#/login") location.hash = "#/login";  // hashchange runs route()
    else route();
  };
}
document.addEventListener("click", () => { const d = document.getElementById("userDrop"); if (d) d.hidden = true; });

function authShell(title, sub, inner) {
  const b = branding || {};
  $app.innerHTML = `
    <div class="auth-wrap">
      <div class="auth-card card">
        <div class="auth-brand"><span class="logo big">${b.logo_url ? `<img alt="" src="${esc(b.logo_url)}">` : DEFAULT_LOGO}</span>
          <div><b>${esc(b.site_name || "ISO 29110 DocGen")}</b><div class="muted small">${esc(b.site_description || "")}</div></div></div>
        <h1 style="font-size:22px">${title}</h1>
        <p class="muted" style="margin:6px 0 4px">${sub}</p>
        ${inner}
      </div>
    </div>`;
  const img = $app.querySelector(".auth-brand img");
  if (img) img.onerror = () => (img.parentElement.innerHTML = DEFAULT_LOGO);
}

function viewLogin() {
  authShell("เข้าสู่ระบบ", "ใช้ชื่อผู้ใช้หรืออีเมลที่ลงทะเบียนไว้", `
    <form id="loginForm">
      <label>ชื่อผู้ใช้ หรือ อีเมล</label><input name="login" autocomplete="username" required autofocus>
      <label>รหัสผ่าน</label><input name="password" type="password" autocomplete="current-password" required>
      <div class="row" style="margin-top:14px"><label class="inline small"><input type="checkbox" name="remember"> จดจำการเข้าสู่ระบบ 30 วัน</label></div>
      <button style="width:100%;margin-top:18px" id="loginBtn">เข้าสู่ระบบ</button>
      ${authState.registration_mode !== "closed" ? `<p class="center small muted" style="margin-top:18px">ยังไม่มีบัญชี? <a href="#/register">สมัครสมาชิก</a></p>`
        : `<p class="center small muted" style="margin-top:18px">ต้องการบัญชี ติดต่อผู้ดูแลระบบ</p>`}
    </form>`);
  document.getElementById("loginForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = ev.target;
    busy(document.getElementById("loginBtn"), async () => {
      await api("/api/auth/login", { method: "POST", body: { login: f.login.value, password: f.password.value, remember: f.remember.checked } });
      await refreshAuth();
      const target = location.hash.startsWith("#/login") || location.hash.startsWith("#/register") || !location.hash ? "#/" : location.hash;
      if (location.hash !== target) location.hash = target;  // hashchange runs route()
      else route();
    });
  };
}

function viewRegister() {
  const setup = authState.needs_setup;
  if (!setup && authState.registration_mode === "closed") return viewLogin();
  authShell(setup ? "สร้างบัญชีผู้ดูแลระบบ" : "สมัครสมาชิก",
    setup ? "ยังไม่มีผู้ใช้ในระบบ บัญชีแรกจะเป็นผู้ดูแลระบบ" :
      authState.registration_mode === "approval" ? "หลังสมัคร ผู้ดูแลระบบต้องอนุมัติก่อนจึงจะเข้าใช้งานได้" : "สมัครแล้วเข้าใช้งานได้ทันที", `
    <form id="regForm">
      <label>ชื่อ-นามสกุล</label><input name="name" required autocomplete="name">
      <div class="grid2">
        <div><label>อีเมล</label><input name="email" type="email" required autocomplete="email"></div>
        <div><label>ชื่อผู้ใช้ <span class="muted small">(ไม่บังคับ)</span></label><input name="username" autocomplete="username" pattern="[A-Za-z0-9][A-Za-z0-9._-]{2,31}" title="3-32 ตัว a-z 0-9 . _ -"></div>
      </div>
      <div class="grid2">
        <div><label>ตำแหน่ง</label><input name="position" placeholder="เช่น PM, Developer"></div>
        <div><label>โทรศัพท์</label><input name="phone" autocomplete="tel"></div>
      </div>
      <div class="grid2">
        <div><label>รหัสผ่าน</label><input name="password" type="password" required minlength="8" autocomplete="new-password"></div>
        <div><label>ยืนยันรหัสผ่าน</label><input name="password2" type="password" required autocomplete="new-password"></div>
      </div>
      <div class="hint">อย่างน้อย 8 ตัว มีทั้งตัวอักษรและตัวเลข</div>
      <button style="width:100%;margin-top:18px" id="regBtn">${setup ? "สร้างบัญชีผู้ดูแลระบบ" : "สมัครสมาชิก"}</button>
      ${setup ? "" : `<p class="center small muted" style="margin-top:18px">มีบัญชีแล้ว? <a href="#/login">เข้าสู่ระบบ</a></p>`}
    </form>`);
  document.getElementById("regForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    if (f.password !== f.password2) return toast("รหัสผ่านทั้งสองช่องไม่ตรงกัน", true);
    busy(document.getElementById("regBtn"), async () => {
      const r = await api("/api/auth/register", { method: "POST", body: f });
      if (r.active) {
        await api("/api/auth/login", { method: "POST", body: { login: f.email, password: f.password } });
        await refreshAuth();
        if (location.hash !== "#/") { location.hash = "#/"; return; }
        return route();
      }
      authShell("สมัครเรียบร้อย", "บัญชีของคุณรอผู้ดูแลระบบอนุมัติ เมื่ออนุมัติแล้วจะเข้าสู่ระบบได้",
        `<a class="btn" href="#/login" style="width:100%;margin-top:18px">กลับไปหน้าเข้าสู่ระบบ</a>`);
    });
  };
}

// ── Profile ─────────────────────────────────────────────────────────────────
function uaShort(ua) {
  const os = /Windows/.test(ua) ? "Windows" : /Mac OS/.test(ua) ? "macOS" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Linux/.test(ua) ? "Linux" : "";
  const br = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : (ua || "").slice(0, 30);
  return [br, os].filter(Boolean).join(" · ") || "ไม่ทราบ";
}

function logTable(rows, showUser) {
  if (!rows.length) return '<p class="muted small">ไม่มีรายการ</p>';
  return `<div class="table-wrap"><table class="list logs">
    <tr><th>เวลา</th>${showUser ? "<th>ผู้ใช้</th>" : ""}<th>กิจกรรม</th><th>รายละเอียด</th><th>สถานะ</th><th>IP</th></tr>
    ${rows.map((r) => `<tr data-log='${esc(JSON.stringify(r))}'>
      <td class="nowrap small">${esc(r.ts)}</td>
      ${showUser ? `<td class="small">${esc(r.user_name || r.user_email || "—")}</td>` : ""}
      <td><span class="chip mono">${esc(r.action)}</span></td>
      <td class="small clip">${esc(r.target ? `${r.target}` : "")} ${r.method ? `<span class="muted">${esc(r.method)} ${esc(r.path)}</span>` : ""}</td>
      <td>${r.status ? `<span class="badge ${r.status >= 500 ? "err" : r.status >= 400 ? "warn" : "ok"}">${r.status}</span>` : ""}</td>
      <td class="small mono">${esc(r.ip)}</td></tr>`).join("")}
  </table></div>`;
}

function bindLogRows(root) {
  root.querySelectorAll("tr[data-log]").forEach((tr) => (tr.onclick = () => {
    const r = JSON.parse(tr.dataset.log);
    const dlg = document.createElement("dialog");
    dlg.className = "dlg wide";
    dlg.innerHTML = `<h2>${esc(r.action)} <span class="muted small">#${r.id}</span></h2>
      <table class="list kv">${Object.entries(r).map(([k, v]) => `<tr><th>${esc(k)}</th><td class="mono small">${esc(v ?? "")}</td></tr>`).join("")}</table>
      <div class="row" style="margin-top:14px"><span class="spacer"></span><button type="button" class="ghost" id="dlgClose">ปิด</button></div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => dlg.remove());
    dlg.querySelector("#dlgClose").onclick = () => dlg.close();
    dlg.showModal();
  }));
}

async function viewProfile() {
  const d = await api("/api/profile");
  const u = d.user;
  $app.innerHTML = `
    <div class="page-head"><div class="row" style="gap:16px"><span class="avatar xl">${esc(initials(u.name))}</span>
      <div><h1>${esc(u.name)}</h1><div class="sub">${esc(u.email)}${u.username ? ` · @${esc(u.username)}` : ""}
        <span class="badge ${ROLE_BADGE[u.role]}">${esc(u.role_th)}</span></div></div></div></div>
    <div class="grid2">
      <form class="card" id="pfForm">
        <h2>ข้อมูลส่วนตัว</h2>
        <label>ชื่อ-นามสกุล</label><input name="name" value="${esc(u.name)}" required>
        <div class="grid2">
          <div><label>ตำแหน่ง</label><input name="position" value="${esc(u.position || "")}"></div>
          <div><label>โทรศัพท์</label><input name="phone" value="${esc(u.phone || "")}"></div>
        </div>
        <p class="hint">สมัครเมื่อ ${esc(u.created_at)} · เข้าระบบล่าสุด ${esc(u.last_login_at || "-")} จาก ${esc(u.last_login_ip || "-")}</p>
        <div class="row" style="margin-top:14px"><button>บันทึก</button></div>
      </form>
      <form class="card" id="pwForm">
        <h2>เปลี่ยนรหัสผ่าน</h2>
        <label>รหัสผ่านปัจจุบัน</label><input name="current" type="password" required autocomplete="current-password">
        <label>รหัสผ่านใหม่</label><input name="new" type="password" required minlength="8" autocomplete="new-password">
        <label>ยืนยันรหัสผ่านใหม่</label><input name="new2" type="password" required autocomplete="new-password">
        <p class="hint">เปลี่ยนแล้ว เครื่องอื่นที่ล็อกอินไว้จะถูกออกจากระบบ</p>
        <div class="row" style="margin-top:14px"><button>เปลี่ยนรหัสผ่าน</button></div>
      </form>
    </div>
    <div class="card">
      <h2>เครื่องที่เข้าสู่ระบบอยู่</h2>
      <div class="table-wrap"><table class="list">
        <tr><th>อุปกรณ์</th><th>IP</th><th>เริ่ม</th><th>ใช้งานล่าสุด</th><th></th></tr>
        ${d.sessions.map((s) => `<tr><td>${esc(uaShort(s.user_agent))} ${s.id === d.current_session ? '<span class="badge ok">เครื่องนี้</span>' : ""}</td>
          <td class="mono small">${esc(s.ip)}</td><td class="small">${esc(s.created_at)}</td><td class="small">${esc(s.last_seen_at)}</td>
          <td>${s.id === d.current_session ? "" : `<button class="danger sm" data-revoke="${s.id}">ออกจากระบบ</button>`}</td></tr>`).join("")}
      </table></div>
    </div>
    <div class="card"><h2>กิจกรรมล่าสุดของฉัน</h2>${logTable(d.activity, false)}</div>`;
  bindLogRows($app);
  document.getElementById("pfForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    busy(ev.submitter, async () => { await api("/api/profile", { method: "PATCH", body: f }); toast("บันทึกแล้ว"); await refreshAuth(); renderUserMenu(); });
  };
  document.getElementById("pwForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    if (f.new !== f.new2) return toast("รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน", true);
    busy(ev.submitter, async () => {
      await api("/api/profile/password", { method: "POST", body: { current: f.current, new: f.new } });
      ev.target.reset(); toast("เปลี่ยนรหัสผ่านแล้ว"); viewProfile();
    });
  };
  $app.querySelectorAll("[data-revoke]").forEach((b) => (b.onclick = () => busy(b, async () => {
    await api(`/api/profile/sessions/${b.dataset.revoke}`, { method: "DELETE" }); viewProfile();
  })));
}

// ── Admin ───────────────────────────────────────────────────────────────────
const ADMIN_TABS = [["overview", "ภาพรวม"], ["users", "ผู้ใช้"], ["logs", "Logs"], ["sessions", "Sessions"], ["policy", "นโยบายบัญชีและ log"]];

async function viewAdmin(tab = "overview") {
  if (!ADMIN_TABS.some(([k]) => k === tab)) tab = "overview";
  $app.innerHTML = `
    <div class="page-head"><div><h1>จัดการระบบ</h1><div class="sub">ผู้ใช้ สิทธิ์ และบันทึกการใช้งานทั้งหมด</div></div></div>
    <div class="tabs">${ADMIN_TABS.map(([k, l]) => `<a href="#/admin/${k}" class="${k === tab ? "active" : ""}">${l}</a>`).join("")}</div>
    <div id="atab"></div>`;
  const el = document.getElementById("atab");
  return ({ overview: adminOverview, users: adminUsers, logs: adminLogs, sessions: adminSessions, policy: adminPolicy })[tab](el);
}

async function adminOverview(el) {
  const o = await api("/api/admin/overview");
  const count = (st) => o.users.filter((u) => u.status === st).reduce((a, u) => a + u.n, 0);
  el.innerHTML = `
    <div class="stats">
      <div class="stat"><div class="label">ผู้ใช้ที่ใช้งานได้</div><div class="value">${count("active")}</div></div>
      <div class="stat ${o.pending ? "warn" : ""}"><div class="label">รออนุมัติ</div><div class="value">${o.pending}</div></div>
      <div class="stat"><div class="label">Session ที่เปิดอยู่</div><div class="value">${o.sessions}</div></div>
      <div class="stat ${o.failed_logins_today ? "err" : ""}"><div class="label">Login ผิดวันนี้</div><div class="value">${o.failed_logins_today}</div></div>
    </div>
    ${o.pending ? `<div class="finding warn"><span>มีผู้สมัคร ${o.pending} คนรออนุมัติ · <a href="#/admin/users">ไปที่หน้าผู้ใช้</a></span></div>` : ""}
    <div class="grid2">
      <div class="card"><h2>ใช้งานมากที่สุดวันนี้</h2>
        ${o.top_users.length ? `<table class="list">${o.top_users.map((u) => `<tr><td>${esc(u.user_name || u.user_email)}</td><td class="muted small">${esc(u.user_email)}</td><td style="text-align:right">${u.n}</td></tr>`).join("")}</table>` : '<p class="muted small">ยังไม่มี</p>'}
        <p class="hint">กิจกรรมวันนี้ ${o.events_today} รายการ · error ${o.errors_today} · log ทั้งหมด ${o.logs_total} รายการ</p></div>
      <div class="card"><h2>กิจกรรมล่าสุด</h2>${logTable(o.recent.slice(0, 8), true)}</div>
    </div>`;
  bindLogRows(el);
}

async function adminUsers(el) {
  const users = await api("/api/admin/users");
  el.innerHTML = `
    <div class="card toolbar static"><b>ผู้ใช้ ${users.length} คน</b><span class="spacer"></span>
      <button id="addUser" class="sm">${ICON.plus} เพิ่มผู้ใช้</button></div>
    <div class="card flush"><div class="table-wrap"><table class="list users">
      <tr><th>ผู้ใช้</th><th>บทบาท</th><th>สถานะ</th><th>เข้าระบบล่าสุด</th><th></th></tr>
      ${users.map((u) => `<tr>
        <td><div class="row" style="gap:10px;flex-wrap:nowrap"><span class="avatar">${esc(initials(u.name))}</span>
          <div><b>${esc(u.name)}</b>${u.id === me.id ? ' <span class="badge info">คุณ</span>' : ""}
          <div class="muted small">${esc(u.email)}${u.username ? ` · @${esc(u.username)}` : ""}${u.position ? ` · ${esc(u.position)}` : ""}</div></div></div></td>
        <td><select data-u="${u.id}" data-f="role" ${u.id === me.id ? "disabled" : ""}>
          ${["admin", "editor", "viewer"].map((r) => `<option value="${r}" ${r === u.role ? "selected" : ""}>${{ admin: "ผู้ดูแลระบบ", editor: "ผู้จัดทำเอกสาร", viewer: "ผู้ดูอย่างเดียว" }[r]}</option>`).join("")}</select></td>
        <td><span class="badge ${STATUS_BADGE[u.status][0]}">${STATUS_BADGE[u.status][1]}</span></td>
        <td class="small">${esc(u.last_login_at || "ยังไม่เคย")}<div class="muted">${esc(u.last_login_ip || "")}</div></td>
        <td class="nowrap">
          ${u.status === "pending" ? `<button class="sm" data-act="approve" data-u="${u.id}">อนุมัติ</button>` : ""}
          ${u.id !== me.id && u.status === "active" ? `<button class="ghost sm" data-act="disable" data-u="${u.id}">ระงับ</button>` : ""}
          ${u.status === "disabled" ? `<button class="ghost sm" data-act="enable" data-u="${u.id}">เปิดใช้</button>` : ""}
          <button class="ghost sm" data-act="reset" data-u="${u.id}" title="รีเซ็ตรหัสผ่าน">รีเซ็ตรหัส</button>
          <a class="btn ghost sm" href="#/admin/logs" data-logs="${u.id}">Logs</a>
          ${u.id !== me.id ? `<button class="icon danger" data-act="delete" data-u="${u.id}" title="ลบผู้ใช้">${ICON.trash}</button>` : ""}
        </td></tr>`).join("")}
    </table></div></div>`;
  const byId = Object.fromEntries(users.map((u) => [u.id, u]));
  const patch = (id, body) => api(`/api/admin/users/${id}`, { method: "PATCH", body });
  el.querySelectorAll("select[data-f=role]").forEach((s) => (s.onchange = async () => {
    try { await patch(s.dataset.u, { role: s.value }); toast("เปลี่ยนบทบาทแล้ว"); } catch (e) { toast(e.message, true); adminUsers(el); }
  }));
  el.querySelectorAll("[data-logs]").forEach((a) => (a.onclick = () => (adminLogFilter = { user_id: a.dataset.logs })));
  el.querySelectorAll("button[data-act]").forEach((b) => (b.onclick = () => busy(b, async () => {
    const u = byId[b.dataset.u];
    if (b.dataset.act === "approve") await patch(u.id, { status: "active" });
    if (b.dataset.act === "enable") await patch(u.id, { status: "active" });
    if (b.dataset.act === "disable") { if (!confirm(`ระงับบัญชี ${u.name}? จะถูกออกจากระบบทันที`)) return; await patch(u.id, { status: "disabled" }); }
    if (b.dataset.act === "delete") { if (!confirm(`ลบบัญชี ${u.name} (${u.email}) ถาวร?\nประวัติใน log ยังคงอยู่`)) return; await api(`/api/admin/users/${u.id}`, { method: "DELETE" }); }
    if (b.dataset.act === "reset") {
      if (!confirm(`รีเซ็ตรหัสผ่านของ ${u.name}? ระบบจะสร้างรหัสชั่วคราวและออกจากระบบทุกเครื่อง`)) return;
      const r = await api(`/api/admin/users/${u.id}/reset-password`, { method: "POST" });
      await dialogForm(`รหัสผ่านชั่วคราวของ ${u.name}`, [{ name: "pw", label: "แจ้งรหัสนี้ให้ผู้ใช้ แล้วให้เปลี่ยนที่หน้าโปรไฟล์ (แสดงครั้งเดียว)", value: r.temporary_password, mono: true }], "ปิด");
    }
    toast("เรียบร้อย");
    adminUsers(el);
  })));
  document.getElementById("addUser").onclick = async () => {
    const v = await dialogForm("เพิ่มผู้ใช้", [
      { name: "name", label: "ชื่อ-นามสกุล" }, { name: "email", label: "อีเมล" }, { name: "username", label: "ชื่อผู้ใช้ (ไม่บังคับ)" },
      { name: "position", label: "ตำแหน่ง" }, { name: "role", label: "บทบาท: admin / editor / viewer", value: "editor", mono: true },
      { name: "password", label: "รหัสผ่านเริ่มต้น (≥ 8 ตัว มีตัวอักษรและตัวเลข)", mono: true },
    ], "สร้างผู้ใช้");
    if (!v) return;
    try { await api("/api/admin/users", { method: "POST", body: v }); toast("สร้างผู้ใช้แล้ว"); adminUsers(el); }
    catch (e) { toast(e.message, true); }
  };
}

let adminLogFilter = {};
async function adminLogs(el) {
  const users = await api("/api/admin/users");
  const f = { q: "", user_id: "", action: "", date_from: "", date_to: "", status: "", reads: true, offset: 0, ...adminLogFilter };
  adminLogFilter = {};
  el.innerHTML = `
    <form class="card filters" id="logFilter">
      <input name="q" value="${esc(f.q)}" placeholder="ค้นหา path, ข้อมูล, IP, อีเมล…">
      <select name="user_id"><option value="">ผู้ใช้ทั้งหมด</option>${users.map((u) => `<option value="${u.id}" ${String(u.id) === String(f.user_id) ? "selected" : ""}>${esc(u.name)}</option>`).join("")}</select>
      <select name="action">
        ${[["", "ทุกกิจกรรม"], ["auth", "เข้า/ออกระบบ"], ["project", "โครงการ"], ["interview", "สัมภาษณ์"], ["document", "เอกสาร"], ["evidence", "หลักฐาน"],
          ["settings", "ตั้งค่า"], ["admin", "ผู้ดูแลระบบ"], ["profile", "โปรไฟล์"], ["api", "request อื่น ๆ"]].map(([v, l]) => `<option value="${v}" ${v === f.action ? "selected" : ""}>${l}</option>`).join("")}</select>
      <input type="date" name="date_from" value="${esc(f.date_from)}" title="ตั้งแต่วันที่">
      <input type="date" name="date_to" value="${esc(f.date_to)}" title="ถึงวันที่">
      <select name="status"><option value="">ทุกผลลัพธ์</option><option value="error" ${f.status === "error" ? "selected" : ""}>เฉพาะผิดพลาด</option></select>
      <label class="inline small"><input type="checkbox" name="reads" ${f.reads ? "checked" : ""}> รวมการเปิดดู (GET)</label>
      <button class="sm">ค้นหา</button><a class="btn ghost sm" id="csvBtn">${ICON.download} CSV</a>
    </form>
    <div class="card flush" id="logBox"></div>`;
  const form = document.getElementById("logFilter");
  const params = (offset = 0) => {
    const v = Object.fromEntries(new FormData(form));
    v.reads = form.reads.checked; v.offset = offset; v.limit = 100;
    return new URLSearchParams(Object.entries(v).filter(([, x]) => x !== "" && x !== undefined)).toString();
  };
  const load = async (offset = 0) => {
    const r = await api(`/api/admin/logs?${params(offset)}`);
    const box = document.getElementById("logBox");
    box.innerHTML = logTable(r.rows, true) + `<div class="row pager"><span class="muted small">${r.total ? offset + 1 : 0}–${Math.min(offset + 100, r.total)} จาก ${r.total} รายการ · คลิกแถวเพื่อดูรายละเอียดทั้งหมด</span>
      <span class="spacer"></span>${offset ? '<button class="ghost sm" id="prev">← ก่อนหน้า</button>' : ""}${offset + 100 < r.total ? '<button class="ghost sm" id="next">ถัดไป →</button>' : ""}</div>`;
    bindLogRows(box);
    const p = document.getElementById("prev"), n = document.getElementById("next");
    if (p) p.onclick = () => load(Math.max(0, offset - 100));
    if (n) n.onclick = () => load(offset + 100);
    document.getElementById("csvBtn").href = `/api/admin/logs.csv?${params(0)}`;
  };
  form.onsubmit = (ev) => { ev.preventDefault(); load(0); };
  await load(0);
}

async function adminSessions(el) {
  const ss = await api("/api/admin/sessions");
  el.innerHTML = `<div class="card flush"><div class="table-wrap"><table class="list">
    <tr><th>ผู้ใช้</th><th>อุปกรณ์</th><th>IP</th><th>เริ่ม</th><th>ใช้งานล่าสุด</th><th>หมดอายุ</th><th></th></tr>
    ${ss.map((s) => `<tr><td><b>${esc(s.name)}</b><div class="muted small">${esc(s.email)}</div></td><td class="small">${esc(uaShort(s.user_agent))}</td>
      <td class="mono small">${esc(s.ip)}</td><td class="small">${esc(s.created_at)}</td><td class="small">${esc(s.last_seen_at)}</td>
      <td class="small">${esc(s.expires_at)}</td><td><button class="danger sm" data-s="${s.id}">บังคับออก</button></td></tr>`).join("")}
  </table></div></div>`;
  el.querySelectorAll("[data-s]").forEach((b) => (b.onclick = () => busy(b, async () => {
    await api(`/api/admin/sessions/${b.dataset.s}`, { method: "DELETE" }); toast("บังคับออกจากระบบแล้ว"); adminSessions(el);
  })));
}

async function adminPolicy(el) {
  const s = await api("/api/settings");
  el.innerHTML = `
    <form class="card" id="polForm" style="max-width:760px">
      <h2>การสมัครสมาชิก</h2>
      ${[["approval", "ต้องอนุมัติ", "สมัครได้ แต่ผู้ดูแลระบบต้องอนุมัติก่อนใช้งาน (แนะนำ)"], ["open", "เปิดรับทันที", "สมัครแล้วใช้งานได้เลยในบทบาทผู้จัดทำเอกสาร"],
        ["closed", "ปิดรับสมัคร", "เฉพาะผู้ดูแลระบบสร้างบัญชีให้"]].map(([v, t, d]) => `
        <label class="radio-card ${s.registration_mode === v ? "on" : ""}"><input type="radio" name="registration_mode" value="${v}" ${s.registration_mode === v ? "checked" : ""}>
          <span><b>${t}</b><span class="hint">${d}</span></span></label>`).join("")}
      <h2 style="margin-top:26px">บันทึกการใช้งาน (Logs)</h2>
      <label class="inline"><input type="checkbox" name="log_reads" ${s.log_reads ? "checked" : ""}> บันทึกการเปิดดูข้อมูล (GET) ด้วย</label>
      <p class="hint">การเปลี่ยนแปลงข้อมูล การเข้าระบบ และการดาวน์โหลดบันทึกเสมอ · รหัสผ่านและ key ถูกปิดทับก่อนบันทึก</p>
      <label>เก็บ log ย้อนหลัง (วัน) <span class="muted small">0 = เก็บตลอด · ลบส่วนที่เก่ากว่านี้ทุกครั้งที่เริ่มโปรแกรม</span></label>
      <input name="log_retention_days" type="number" min="0" value="${s.log_retention_days}" style="max-width:200px">
      <div class="row" style="margin-top:18px"><button>บันทึก</button></div>
    </form>`;
  const form = document.getElementById("polForm");
  form.querySelectorAll('input[name="registration_mode"]').forEach((r) => (r.onchange = () =>
    form.querySelectorAll(".radio-card").forEach((c) => c.classList.toggle("on", c.querySelector("input").checked))));
  form.onsubmit = (ev) => {
    ev.preventDefault();
    const v = Object.fromEntries(new FormData(form));
    v.log_reads = form.log_reads.checked;
    v.log_retention_days = parseInt(v.log_retention_days || "0", 10);
    busy(ev.submitter, async () => { await api("/api/settings", { method: "POST", body: v }); toast("บันทึกแล้ว"); authState = null; });
  };
}

// ── Projects dashboard ──────────────────────────────────────────────────────
const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);

function meter(label, done, total, ok) {
  return `<div class="meter"><span>${label}</span>
    <div class="bar"><span class="${ok && done >= total ? "ok" : ""}" style="width:${pct(done, total)}%"></span></div>
    <span class="num">${done}/${total}</span></div>`;
}

function timeAgo(s) {
  const d = new Date(String(s).replace(" ", "T"));
  const mins = Math.round((Date.now() - d) / 60000);
  if (isNaN(mins)) return esc(s);
  if (mins < 1) return "เมื่อสักครู่";
  if (mins < 60) return `${mins} นาทีที่แล้ว`;
  if (mins < 1440) return `${Math.round(mins / 60)} ชั่วโมงที่แล้ว`;
  return d.toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric" });
}

async function viewProjects() {
  const list = await api("/api/projects");
  const sum = (k) => list.reduce((a, p) => a + (p[k] || 0), 0);
  const docsTotal = sum("docs_total");
  $app.innerHTML = `
    <div class="page-head">
      <div><h1>โครงการ</h1><div class="sub">จัดทำและติดตามเอกสารตามมาตรฐาน ISO/IEC 29110 Basic Profile</div></div>
      <span class="spacer"></span>
      <button id="newBtn">${ICON.plus} โครงการใหม่</button>
    </div>
    ${list.length ? `
    <div class="stats">
      <div class="stat"><div class="label">โครงการ</div><div class="value">${list.length}</div></div>
      <div class="stat"><div class="label">เอกสารที่จัดทำแล้ว</div><div class="value">${sum("docs_made")}<small> / ${docsTotal}</small></div></div>
      <div class="stat"><div class="label">ไฟล์ทั้งหมด</div><div class="value">${sum("files")}</div></div>
      <div class="stat ${sum("errors") ? "err" : ""}"><div class="label">ประเด็นที่ต้องแก้ก่อน audit</div><div class="value">${sum("errors")}</div></div>
    </div>
    <div class="section-title">${ICON.folder} โครงการทั้งหมด</div>
    <div class="projects">
      ${list.map((p) => `
        <a class="pcard" href="#/p/${p.id}">
          <div>
            <span class="chip mono">${esc(p.code)}</span>
            <div class="title" style="margin-top:10px">${esc(p.name)}</div>
            <div class="customer">${esc(p.customer || "—")}</div>
          </div>
          <div class="meters">
            ${meter("สัมภาษณ์", p.stages_done, p.stages_total, true)}
            ${meter("เอกสาร", p.docs_made, p.docs_total, true)}
          </div>
          <div class="foot">
            ${p.errors ? `<span class="badge err">ต้องแก้ ${p.errors}</span>` : '<span class="badge ok">ไม่มีประเด็นร้ายแรง</span>'}
            ${p.warnings ? `<span class="badge warn">ควรแก้ ${p.warnings}</span>` : ""}
            <span class="spacer"></span>แก้ไข ${timeAgo(p.updated_at)}
          </div>
        </a>`).join("")}
      <button class="pcard new-card" id="newCard"><div><div class="plus">${ICON.plus}</div><b>เริ่มโครงการใหม่</b>
        <div class="small">AI จะสัมภาษณ์ทีละขั้นแล้วจัดทำเอกสารให้</div></div></button>
    </div>` : `
    <div class="card empty">
      <div class="icon">${ICON.doc}</div>
      <h2>ยังไม่มีโครงการ</h2>
      <p class="muted">สร้างโครงการแรก แล้ว AI จะถามข้อมูลทีละขั้นตาม ISO 29110 และจัดทำเอกสารให้</p>
      <button id="newEmpty">${ICON.plus} สร้างโครงการแรก</button>
    </div>`}`;
  ["newBtn", "newCard", "newEmpty"].forEach((id) => {
    const b = document.getElementById(id);
    if (b) b.onclick = newProjectDialog;
  });
}

function newProjectDialog() {
  const dlg = document.createElement("dialog");
  dlg.className = "dlg";
  dlg.innerHTML = `<form id="npForm">
      <h2>โครงการใหม่</h2>
      <label>ชื่อโครงการ</label>
      <input name="name" required placeholder="เช่น พัฒนาระบบ Call Center Toyota จาก Nuance NLU เป็น LLM Intent Classification">
      <div class="grid2">
        <div><label>รหัสโครงการ</label><input name="code" required class="mono" placeholder="Toyota_LLMIntent-2026-001"></div>
        <div><label>ลูกค้า</label><input name="customer" placeholder="เช่น AIS"></div>
      </div>
      <div class="muted small" style="margin-top:6px">รหัสใช้ตั้งชื่อไฟล์ เช่น SUN_&lt;รหัส&gt;_SOW_v1.0.docx และแก้ภายหลังไม่ได้</div>
      <label>เล่าโครงการคร่าว ๆ</label>
      <textarea name="summary" rows="4" placeholder="ทำอะไร ระยะเวลาเท่าไหร่ เทคโนโลยีอะไร สถานะตอนนี้"></textarea>
      <div class="row" style="margin-top:18px"><span class="spacer"></span>
        <button type="button" class="ghost" id="npCancel">ยกเลิก</button><button id="npOk">สร้างโครงการ</button></div>
    </form>`;
  document.body.appendChild(dlg);
  dlg.addEventListener("close", () => dlg.remove());
  dlg.querySelector("#npCancel").onclick = () => dlg.close();
  dlg.querySelector("#npForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    busy(dlg.querySelector("#npOk"), async () => {
      const p = await api("/api/projects", { method: "POST", body: f });
      dlg.close();
      location.hash = `#/p/${p.id}`;
    });
  };
  dlg.showModal();
}

// ── Project ─────────────────────────────────────────────────────────────────
async function viewProject(pid, tab, stageKey) {
  const p = await api(`/api/projects/${pid}`);
  const tabs = [["interview", "สัมภาษณ์"], ["docs", "เอกสาร"], ["audit", "ความพร้อม Audit"], ["facts", "ข้อมูลที่บันทึก"], ["info", "ข้อมูลโครงการ"]];
  const done = p.stages.filter((s) => s.done).length;
  $app.innerHTML = `
    <div class="crumbs"><a href="#/">โครงการ</a> / ${esc(p.code)}</div>
    <div class="page-head">
      <div style="min-width:0">
        <h1>${esc(p.name)}</h1>
        <div class="sub"><span class="chip mono">${esc(p.code)}</span>${esc(p.customer)}
          <span class="badge ${done === p.stages.length ? "ok" : "info"}">สัมภาษณ์ ${done}/${p.stages.length} ขั้น</span></div>
      </div>
    </div>
    <div class="tabs">${tabs.map(([k, l]) => `<a href="#/p/${pid}/${k}" class="${k === tab || (tab === "gen" && k === "docs") ? "active" : ""}">${l}</a>`).join("")}</div>
    <div id="tab"></div>`;
  const el = document.getElementById("tab");
  if (tab === "docs") return tabDocs(el, p);
  if (tab === "audit") return tabAudit(el, p);
  if (tab === "facts") return tabFacts(el, p);
  if (tab === "info") return tabInfo(el, p);
  if (tab === "gen") return tabGenerate(el, p, stageKey);
  return tabInterview(el, p, stageKey || firstOpenStage(p));
}

function firstOpenStage(p) {
  const s = p.stages.find((s) => !s.done);
  return (s || p.stages[0]).key;
}

// Interview
async function tabInterview(el, p, stageKey) {
  const stage = p.stages.find((s) => s.key === stageKey) || p.stages[0];
  el.innerHTML = `
    <div class="interview">
      <div class="card stages">
        ${p.stages.map((s, i) => `<a href="#/p/${p.id}/interview/${s.key}" class="${s.key === stage.key ? "active" : ""} ${s.done ? "done" : ""}">
          <span class="dot">${s.done ? "✓" : i + 1}</span>
          <span><div class="name">${esc(s.title.replace(/^\d+\.\s*/, ""))}</div>
          <div class="meta">${esc(s.iso)} · ${s.complete}/${s.topics} หัวข้อ</div></span></a>`).join("")}
      </div>
      <div class="card chat">
        <div class="chat-head"><h2 style="margin:0">${esc(stage.title)}</h2><span class="spacer"></span>
          <a class="btn ghost sm" href="#/p/${p.id}/docs">${ICON.doc} เอกสาร</a></div>
        <div class="msgs" id="msgs"></div>
        <ul class="gaps" id="gaps"></ul>
        <div class="composer">
          <textarea id="answer" placeholder="ตอบเป็นภาษาพูดได้เลย หรือแปะอีเมล/แชท/บันทึกที่เกี่ยวข้อง (Ctrl+Enter เพื่อส่ง)"></textarea>
          <div class="btns">
            <button id="send">ส่ง</button>
            <button id="ask" class="ghost">ให้ถามต่อ</button>
          </div>
        </div>
      </div>
    </div>`;
  const msgsEl = document.getElementById("msgs");
  const render = (msgs, gaps) => {
    msgsEl.innerHTML = msgs.length
      ? msgs.map((m) => `<div class="msg ${m.role}">${m.role === "user" && m.user_name ? `<div class="by">${esc(m.user_name)}</div>` : ""}${esc(m.content)}</div>`).join("")
      : `<div class="empty"><div class="icon">${ICON.spark}</div><b>เริ่มสัมภาษณ์ขั้นนี้</b>
          <p class="muted small">กด "ให้ถามต่อ" แล้ว AI จะถามคำถามแรก</p></div>`;
    msgsEl.scrollTop = msgsEl.scrollHeight;
    document.getElementById("gaps").innerHTML = (gaps || []).map((g) => `<li>${esc(g)}</li>`).join("");
  };
  render(await api(`/api/projects/${p.id}/messages?stage=${stage.key}`), stage.gaps);

  const send = async (btn, text) => busy(btn, async () => {
    const r = await api(`/api/projects/${p.id}/interview`, { method: "POST", body: { stage: stage.key, text } });
    document.getElementById("answer").value = "";
    render(await api(`/api/projects/${p.id}/messages?stage=${stage.key}`), r.gaps);
    if (r.stage_complete) toast("ข้อมูลขั้นนี้ครบแล้ว ไปสร้างเอกสารได้");
  });
  document.getElementById("send").onclick = (e) => {
    const text = document.getElementById("answer").value.trim();
    if (!text) return toast("พิมพ์คำตอบก่อน", true);
    send(e.currentTarget, text);
  };
  document.getElementById("ask").onclick = (e) => send(e.currentTarget, null);
  document.getElementById("answer").onkeydown = (e) => {
    if (e.key === "Enter" && e.ctrlKey) document.getElementById("send").click();
  };
}

// Documents
const selectedFiles = new Set();   // document ids ticked for zip download (kept across re-renders)

async function tabDocs(el, p) {
  const docs = await api(`/api/projects/${p.id}/documents`);
  const byStage = {};
  docs.forEach((d) => (byStage[d.stage] ??= []).push(d));
  const latestIds = docs.flatMap((d) => latestFiles(d).map((f) => f.id));
  const made = docs.filter((d) => d.files.length).length;
  el.innerHTML = `
    <div class="card toolbar">
      <span class="badge info">${made}/${docs.length} เอกสาร</span>
      <button id="selLatest" class="ghost sm">เลือกฉบับล่าสุดทั้งหมด (${latestIds.length})</button>
      <button id="selNone" class="ghost sm">ล้าง</button>
      <label class="inline small"><input type="checkbox" id="withEvidence" checked> รวม Evidence List</label>
      <span class="spacer"></span>
      <span class="muted small" id="selCount"></span>
      <button id="dlZip" class="sm">${ICON.download} ดาวน์โหลด .zip</button>
    </div>
    <p class="muted small" style="margin:0 4px 16px">ช่อง <b>[ต้องระบุ]</b> คือข้อมูลที่ยังขาด ·
      เปลี่ยนสถานะเป็น Val/Baseline เมื่อมีหลักฐานจริงแล้วเท่านั้น</p>
    ${catalog.stages.map((s, i) => (byStage[s.key] || []).length ? `
      <section class="stage-block">
        <h3><span class="n">${i + 1}</span>${esc(s.title.replace(/^\d+\.\s*/, ""))}<span class="muted small" style="font-weight:400">${esc(s.iso)}</span></h3>
        <div class="card flush">${byStage[s.key].map((d) => docRow(d, p)).join("")}</div>
      </section>` : "").join("")}`;

  const refreshCount = () => {
    document.getElementById("selCount").textContent = selectedFiles.size ? `เลือก ${selectedFiles.size} ไฟล์` : "";
    el.querySelectorAll("[data-pick]").forEach((cb) => (cb.checked = selectedFiles.has(+cb.dataset.pick)));
  };
  el.querySelectorAll("[data-pick]").forEach((cb) => (cb.onchange = () => {
    cb.checked ? selectedFiles.add(+cb.dataset.pick) : selectedFiles.delete(+cb.dataset.pick);
    refreshCount();
  }));
  document.getElementById("selLatest").onclick = () => { latestIds.forEach((id) => selectedFiles.add(id)); refreshCount(); };
  document.getElementById("selNone").onclick = () => { selectedFiles.clear(); refreshCount(); };
  document.getElementById("dlZip").onclick = (e) => busy(e.target, async () => {
    const include = document.getElementById("withEvidence").checked;
    if (!selectedFiles.size && !include) throw new Error("ยังไม่ได้เลือกไฟล์");
    const res = await fetch(`/api/projects/${p.id}/download-zip`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [...selectedFiles], include_evidence_list: include }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
    const disposition = res.headers.get("Content-Disposition") || "";
    const name = decodeURIComponent(disposition.split("UTF-8''")[1] || "documents.zip");
    const url = URL.createObjectURL(await res.blob());
    Object.assign(document.createElement("a"), { href: url, download: name }).click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  });
  refreshCount();
  el.querySelectorAll("[data-act]").forEach((btn) => (btn.onclick = () =>
    fileAction(btn, p, el).catch((e) => toast(e.message, true))));

  el.querySelectorAll("[data-ev]").forEach((inp) => (inp.onchange = async () => {
    const key = inp.dataset.ev;
    try {
      await api(`/api/projects/${p.id}/evidence/${key}`, { method: "PATCH", body: { [inp.dataset.field]: inp.value } });
      if (inp.dataset.field === "status") inp.className = `s-${inp.value}`;
      toast("บันทึกแล้ว");
    } catch (e) { toast(e.message, true); }
  }));
}

// files arrive newest-first; the first file of each item is its latest version
function latestFiles(d) {
  const seen = new Set();
  return d.files.filter((f) => !seen.has(f.item_index) && seen.add(f.item_index));
}

function fileLine(f) {
  const attrs = `data-id="${f.id}" data-name="${esc(f.filename)}" data-ver="${esc(f.version)}"`;
  return `<div class="file-line"><input type="checkbox" data-pick="${f.id}" title="เลือกเพื่อดาวน์โหลดรวม">
    <a class="fname" href="/api/documents/${f.id}/download" title="${esc(f.filename)}${f.created_by_name ? `\n${f.source === "upload" ? "อัปโหลดโดย" : "สร้างโดย"} ${esc(f.created_by_name)} · ${esc(f.created_at)}` : ""}">${esc(f.filename)}</a>
    ${f.placeholders ? `<span class="badge warn" title="ช่อง [ต้องระบุ] ที่ยังขาด">ขาด ${f.placeholders}</span>` : '<span class="badge ok">ครบ</span>'}
    <span class="file-acts">
      <button type="button" class="icon" data-act="edit" ${attrs} title="แก้ชื่อไฟล์/ฉบับที่">${ICON.edit}</button>
      <button type="button" class="icon" data-act="upload" ${attrs} title="อัปโหลดไฟล์ที่แก้แล้วเป็นฉบับใหม่">${ICON.upload}</button>
      <button type="button" class="icon danger" data-act="delete" ${attrs} title="ลบไฟล์นี้">${ICON.trash}</button>
    </span></div>`;
}

// small modal form; resolves with the field values or null when cancelled
function dialogForm(title, fields, okLabel = "บันทึก") {
  return new Promise((resolve) => {
    const dlg = document.createElement("dialog");
    dlg.className = "dlg";
    dlg.innerHTML = `<form method="dialog"><h2>${esc(title)}</h2>
      ${fields.map((f) => `<label>${esc(f.label)}</label>
        ${f.type === "file" ? `<input type="file" name="${f.name}" accept="${f.accept || ""}" required>`
          : `<input name="${f.name}" value="${esc(f.value || "")}" class="${f.mono ? "mono" : ""}" placeholder="${esc(f.placeholder || "")}">`}
        ${f.hint ? `<div class="muted small">${esc(f.hint)}</div>` : ""}`).join("")}
      <div class="row" style="margin-top:14px"><button value="ok">${esc(okLabel)}</button>
      <button value="cancel" class="ghost" formnovalidate>ยกเลิก</button></div></form>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("close", () => {
      const ok = dlg.returnValue === "ok";
      const form = dlg.querySelector("form");
      const out = {};
      fields.forEach((f) => (out[f.name] = f.type === "file" ? form[f.name].files[0] : form[f.name].value.trim()));
      dlg.remove();
      resolve(ok ? out : null);
    });
    dlg.showModal();
  });
}

async function fileAction(btn, p, el) {
  const id = btn.dataset.id, name = btn.dataset.name;
  if (btn.dataset.act === "delete") {
    if (!confirm(`ลบไฟล์ ${name} ถาวร?\nไฟล์และประวัติของฉบับนี้จะหายไป กู้คืนไม่ได้`)) return;
    await api(`/api/documents/${id}`, { method: "DELETE" });
    selectedFiles.delete(+id);
    toast(`ลบ ${name} แล้ว`);
  } else if (btn.dataset.act === "edit") {
    const v = await dialogForm("แก้ไขไฟล์", [
      { name: "filename", label: "ชื่อไฟล์", value: name, mono: true },
      { name: "version", label: "ฉบับที่", value: btn.dataset.ver, mono: true, hint: "แก้เฉพาะข้อมูลในระบบ เนื้อหาในไฟล์ไม่เปลี่ยน" },
    ]);
    if (!v) return;
    await api(`/api/documents/${id}`, { method: "PATCH", body: v });
    toast("แก้ไขแล้ว");
  } else if (btn.dataset.act === "upload") {
    const ext = name.split(".").pop();
    const v = await dialogForm(`อัปโหลดฉบับแก้ของ ${name}`, [
      { name: "file", label: `ไฟล์ .${ext} ที่แก้แล้ว`, type: "file", accept: `.${ext}` },
      { name: "version", label: "ฉบับที่ (เว้นว่าง = ฉบับถัดไปอัตโนมัติ)", mono: true },
    ], "อัปโหลด");
    if (!v || !v.file) return;
    const fd = new FormData();
    fd.append("file", v.file);
    if (v.version) fd.append("version", v.version);
    const r = await api(`/api/documents/${id}/upload`, { method: "POST", body: fd });
    toast(`บันทึกเป็น ${r.filename}` + (r.placeholders ? ` (ยังมี [ต้องระบุ] ${r.placeholders} จุด)` : ""));
  }
  tabDocs(el, p);
}

function docRow(d, p) {
  const kindLabel = { report: "Word", form: "Word (แบบฟอร์ม)", memo: "บันทึกข้อความ", sheet: "Excel" }[d.kind];
  const latest = latestFiles(d);
  const older = d.files.filter((f) => !latest.includes(f));
  const files = latest.map(fileLine).join("") + (older.length ? `
    <details><summary>ฉบับก่อนหน้า (${older.length})</summary>${older.map(fileLine).join("")}</details>` : "");
  const hasEvidence = d.links || d.remark;
  return `<div class="doc">
    <div>
      <div><span class="seq">${esc(d.seq)}</span><span class="dname">${esc(d.name_th)}</span></div>
      <div class="dmeta"><span class="chip">${esc(d.owner)}</span><span class="chip">${kindLabel}</span>
        <span class="chip">${esc(d.deliver)}</span>${d.val ? '<span class="chip">ต้องมี Val</span>' : ""}</div>
      <div class="actions"><a class="btn sm ${d.files.length ? "ghost" : ""}" href="#/p/${p.id}/gen/${d.key}">
        ${d.files.length ? `${ICON.spark} สร้างฉบับใหม่` : `${ICON.plus} สร้างเอกสาร`}</a></div>
    </div>
    <div class="files-col">${files || '<div class="none">ยังไม่มีไฟล์</div>'}</div>
    <div class="status-col">
      <select data-ev="${d.key}" data-field="status" class="s-${d.status}">
        ${catalog.statuses.map((s) => `<option value="${s}" ${s === d.status ? "selected" : ""}>${STATUS_TH[s]}</option>`).join("")}</select>
      ${d.remark ? `<div class="remark">${esc(d.remark)}</div>` : ""}
      <details><summary>${hasEvidence ? "แก้ไขหลักฐาน/หมายเหตุ" : "+ ลิงก์หลักฐาน / หมายเหตุ"}</summary>
        <textarea rows="2" data-ev="${d.key}" data-field="links" placeholder="ลิงก์ Drive / path">${esc(d.links)}</textarea>
        <input data-ev="${d.key}" data-field="remark" value="${esc(d.remark)}" placeholder="หมายเหตุ"></details>
    </div>
  </div>`;
}

// Create-document page: filename, version, date, signers, extra instructions
async function tabGenerate(el, p, docKey) {
  const doc = catalog.documents.find((d) => d.key === docKey);
  if (!doc) return (el.innerHTML = `<div class="card">ไม่รู้จักเอกสาร ${esc(docKey)}</div>`);
  const items = doc.per_item ? (Array.isArray(p.facts[doc.per_item]) ? p.facts[doc.per_item] : []) : [];
  const today = new Date().toISOString().slice(0, 10);
  el.innerHTML = `
    <div class="card">
      <a href="#/p/${p.id}/docs">← กลับไปหน้าเอกสาร</a>
      <h2 style="margin-top:12px">สร้างเอกสาร: ${esc(doc.seq)} ${esc(doc.name_th)}</h2>
      <p class="muted small" style="margin-bottom:0">${esc(doc.name)} · ผู้รับผิดชอบ ${esc(doc.owner)} · ${esc(doc.deliver)}</p>
    </div>
    <form class="card" id="genForm">
      ${doc.per_item ? `<label>รายการ (${esc(doc.per_item)})</label>
        <select name="item_index" id="itemSel">${items.length ? items.map((it, i) =>
          `<option value="${i}">#${i + 1} ${esc(it.date || "")} ${esc(it.phase || it.type || it.id || "")}</option>`).join("")
          : `<option value="">ยังไม่มีรายการ — สัมภาษณ์ขั้นที่ 7 ก่อน</option>`}</select>` : ""}
      <div class="grid2">
        <div><label>ชื่อไฟล์</label><input name="filename" id="fName" class="mono" required></div>
        <div><label>รหัสเอกสาร <span class="muted small">(แสดงในหัวเอกสาร)</span></label><input name="doc_no" id="fDocNo" class="mono"></div>
      </div>
      <div class="grid2">
        <div><label>ฉบับที่</label><input name="version" id="fVer" class="mono" placeholder="1.0"></div>
        <div><label>วันที่จัดทำเอกสาร <span class="muted small">(วันนี้หรือวันที่จะลงนาม — ย้อนหลังไม่ได้)</span></label>
          <input type="date" name="prepared_date" id="fDate" min="${today}"></div>
      </div>
      <label>ผู้ลงนาม <span class="muted small">(ลบออกทั้งหมด = ให้ AI เลือกจากข้อมูลโครงการ)</span></label>
      <table class="list" id="sigTable"><tr><th>ตำแหน่งในเอกสาร</th><th>ชื่อ</th><th>ตำแหน่งงาน</th><th></th></tr></table>
      <button type="button" class="ghost" id="addSig" style="margin-top:6px">+ เพิ่มผู้ลงนาม</button>
      <label>คำสั่งเพิ่มเติมถึง AI <span class="muted small">(ไม่บังคับ เช่น "เน้นส่วน fallback", "เขียนสั้นไม่เกิน 3 หน้า")</span></label>
      <textarea name="instructions" rows="3"></textarea>
      <div class="row" style="margin-top:14px"><button id="genBtn">สร้างเอกสาร</button><span class="spacer"></span>
        <span class="muted small">AI ใช้เวลาประมาณ 20–40 วินาที</span></div>
      <div id="genResult"></div>
    </form>`;

  const sigTable = document.getElementById("sigTable");
  const addSig = (s = {}) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><input data-s="label" value="${esc(s.label || "")}" placeholder="ผู้จัดทำ"></td>
      <td><input data-s="name" value="${esc(s.name || "")}"></td>
      <td><input data-s="position" value="${esc(s.position || "")}"></td>
      <td><button type="button" class="danger" title="ลบ">✕</button></td>`;
    tr.querySelector("button").onclick = () => tr.remove();
    sigTable.appendChild(tr);
  };
  document.getElementById("addSig").onclick = () => addSig();

  const itemSel = document.getElementById("itemSel");
  const loadPlan = async () => {
    if (itemSel && itemSel.value === "") return;
    const q = itemSel ? `?item_index=${itemSel.value}` : "";
    const pl = await api(`/api/projects/${p.id}/documents/${docKey}/plan${q}`);
    document.getElementById("fName").value = pl.filename;
    document.getElementById("fDocNo").value = pl.doc_no;
    document.getElementById("fVer").value = pl.version;
    document.getElementById("fDate").value = pl.prepared_date;
    sigTable.querySelectorAll("tr:not(:first-child)").forEach((tr) => tr.remove());
    pl.signatures.forEach(addSig);
  };
  if (itemSel) itemSel.onchange = () => loadPlan().catch((e) => toast(e.message, true));
  await loadPlan().catch((e) => toast(e.message, true));

  document.getElementById("genForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    const body = {
      filename: f.filename, doc_no: f.doc_no, version: f.version, prepared_date: f.prepared_date,
      instructions: f.instructions || null,
      signatures: [...sigTable.querySelectorAll("tr:not(:first-child)")].map((tr) => ({
        label: tr.querySelector('[data-s="label"]').value.trim(),
        name: tr.querySelector('[data-s="name"]').value.trim(),
        position: tr.querySelector('[data-s="position"]').value.trim(),
      })).filter((s) => s.label || s.name),
    };
    if (doc.per_item) {
      if (!f.item_index) return toast("ยังไม่มีรายการให้สร้าง", true);
      body.item_index = +f.item_index;
    }
    busy(document.getElementById("genBtn"), async () => {
      const r = await api(`/api/projects/${p.id}/documents/${docKey}/generate`, { method: "POST", body });
      document.getElementById("genResult").innerHTML = `<div class="finding info" style="margin-top:14px">
        สร้างแล้ว: <a href="/api/documents/${r.id}/download">${esc(r.filename)}</a>
        ${r.placeholders ? `<span class="badge warn">ยังขาดข้อมูล ${r.placeholders} จุด</span>` : '<span class="badge ok">ครบ</span>'}
        · <a href="#/p/${p.id}/docs">กลับไปหน้าเอกสาร</a></div>`;
      await loadPlan();  // next version / filename ready if they generate again
    });
  };
}

// Audit readiness
async function tabAudit(el, p) {
  const findings = await api(`/api/projects/${p.id}/checks`);
  const count = (lv) => findings.filter((f) => f.level === lv).length;
  el.innerHTML = `
    <div class="card">
      <div class="row">
        <span class="badge err">ต้องแก้ ${count("error")}</span>
        <span class="badge warn">ควรแก้ ${count("warn")}</span>
        <span class="badge">ข้อสังเกต ${count("info")}</span>
        <span class="spacer"></span>
        <button id="export">Export Evidence List + Doc Mapping (.xlsx)</button>
      </div>
    </div>
    <div class="card">${findings.length ? findings.map((f) => `<div class="finding ${f.level}"><b>${esc(f.doc)}</b> — ${esc(f.message)}</div>`).join("")
      : '<p>ไม่พบประเด็น 🎉</p>'}</div>`;
  document.getElementById("export").onclick = (e) => busy(e.target, async () => {
    const r = await api(`/api/projects/${p.id}/export`, { method: "POST" });
    location.href = r.url;
  });
}

// Facts editor
function tabFacts(el, p) {
  const pub = Object.fromEntries(Object.entries(p.facts).filter(([k]) => !k.startsWith("_")));
  el.innerHTML = `
    <div class="card">
      <p class="muted small" style="margin-top:0">ข้อเท็จจริงทั้งหมดที่ AI บันทึกจากการสัมภาษณ์ (JSON) — แก้ไขตรงนี้ได้ถ้าบันทึกผิด</p>
      <textarea id="facts" rows="28" class="mono">${esc(JSON.stringify(pub, null, 2))}</textarea>
      <div class="row" style="margin-top:10px"><button id="saveFacts">บันทึก</button></div>
    </div>`;
  document.getElementById("saveFacts").onclick = (e) => busy(e.target, async () => {
    let data;
    try { data = JSON.parse(document.getElementById("facts").value); }
    catch { throw new Error("JSON ไม่ถูกต้อง"); }
    await api(`/api/projects/${p.id}/facts`, { method: "PUT", body: data });
    toast("บันทึกแล้ว");
  });
}

// Project info
function tabInfo(el, p) {
  el.innerHTML = `
    <form class="card" id="info">
      <label>ชื่อโครงการ</label><input name="name" value="${esc(p.name)}" required>
      <label>รหัสโครงการ</label><input value="${esc(p.code)}" disabled class="mono">
      <label>ลูกค้า</label><input name="customer" value="${esc(p.customer)}">
      <label>สรุปโครงการ</label><textarea name="summary" rows="6">${esc(p.summary)}</textarea>
      <div class="row" style="margin-top:12px"><button>บันทึก</button><span class="spacer"></span>
        <button type="button" class="danger" id="del">ลบโครงการ</button></div>
    </form>`;
  document.getElementById("info").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    busy(ev.submitter, async () => {
      await api(`/api/projects/${p.id}`, { method: "PATCH", body: { ...f, code: p.code } });
      toast("บันทึกแล้ว");
    });
  };
  document.getElementById("del").onclick = (e) => {
    if (!confirm(`ลบโครงการ ${p.code} และประวัติทั้งหมด? (ไฟล์ใน storage จะยังอยู่)`)) return;
    busy(e.target, async () => {
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      location.hash = "#/";
    });
  };
}

// ── Branding & theme ────────────────────────────────────────────────────────
const DEFAULT_LOGO = svg('<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="m9 15 2 2 4-4"/>');
const BRAND_SWATCHES = ["#3b5bdb", "#1971c2", "#0c8599", "#2f9e44", "#e8590c", "#c92a2a", "#7048e8", "#364152"];
let branding = null;  // last saved branding from the server

function isDarkColor(hex) {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.6;
}

function applyBranding(b) {
  const root = document.documentElement;
  root.style.setProperty("--brand-base", b.brand_color || "#3b5bdb");
  if (b.topbar_color) {
    root.style.setProperty("--topbar-custom", b.topbar_color);
    root.dataset.topbar = isDarkColor(b.topbar_color) ? "dark" : "light";
  } else {
    root.style.removeProperty("--topbar-custom");
    delete root.dataset.topbar;
  }
  document.title = b.site_name || "ISO 29110 DocGen";
  document.getElementById("siteName").textContent = b.site_name || "ISO 29110 DocGen";
  const desc = document.getElementById("siteDesc");
  desc.textContent = b.site_description || "";
  desc.hidden = !b.site_description;
  const logo = document.getElementById("siteLogo");
  if (b.logo_url) {
    logo.className = "logo img";
    logo.innerHTML = `<img alt="" src="${esc(b.logo_url)}">`;
    logo.querySelector("img").onerror = () => { logo.className = "logo"; logo.innerHTML = DEFAULT_LOGO; };
  } else {
    logo.className = "logo";
    logo.innerHTML = DEFAULT_LOGO;
  }
}

async function loadBranding() {
  branding = await api("/api/branding");
  try { localStorage.setItem("branding", JSON.stringify(branding)); } catch (e) { /* storage blocked */ }
  applyBranding(branding);
  return branding;
}

const prefersDark = () => window.matchMedia("(prefers-color-scheme: dark)").matches;
const effectiveTheme = () => document.documentElement.dataset.theme || (prefersDark() ? "dark" : "light");

function renderThemeBtn() {
  const btn = document.getElementById("themeBtn");
  const dark = effectiveTheme() === "dark";
  btn.innerHTML = dark ? ICON.sun : ICON.moon;
  btn.title = dark ? "เปลี่ยนเป็นโหมดสว่าง" : "เปลี่ยนเป็นโหมดมืด";
}
document.getElementById("themeBtn").onclick = () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) { /* storage blocked */ }
  renderThemeBtn();
};
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderThemeBtn);
renderThemeBtn();
applyBranding((() => { try { return JSON.parse(localStorage.getItem("branding") || "{}"); } catch (e) { return {}; } })());
loadBranding().catch(() => {});

// ── Settings ────────────────────────────────────────────────────────────────
const SETTINGS_TABS = [
  ["site", "เว็บไซต์", "globe"], ["ai", "AI (Gemini)", "spark"], ["company", "ข้อมูลบริษัท", "building"], ["format", "รูปแบบเอกสาร", "doc"],
];

async function viewSettings(tab = "site") {
  if (!SETTINGS_TABS.some(([k]) => k === tab)) tab = "site";
  await loadBranding();
  const s = await api("/api/settings");
  $app.innerHTML = `
    <div class="page-head"><div><h1>ตั้งค่า</h1><div class="sub">ค่าที่ใช้ร่วมกันทุกโครงการ</div></div></div>
    <div class="tabs">${SETTINGS_TABS.map(([k, l, ic]) =>
      `<a href="#/settings/${k}" class="${k === tab ? "active" : ""}">${ICON[ic]} ${l}</a>`).join("")}</div>
    <div id="stab"></div>`;
  const el = document.getElementById("stab");
  ({ site: settingsSite, ai: settingsAI, company: settingsCompany, format: settingsFormat })[tab](el, s);
}

async function saveSettings(btn, body, after) {
  return busy(btn, async () => {
    await api("/api/settings", { method: "POST", body });
    toast("บันทึกแล้ว");
    if (after) await after();
  });
}

function settingsSite(el, s) {
  el.innerHTML = `
    <form class="card" id="siteForm" style="max-width:760px">
      <h2>ชื่อและโลโก้</h2>
      <div class="grid2">
        <div><label>ชื่อเว็บไซต์</label><input name="site_name" value="${esc(s.site_name)}" required maxlength="60"></div>
        <div><label>คำอธิบาย <span class="muted small">(บรรทัดเล็กใต้ชื่อ เว้นว่างได้)</span></label>
          <input name="site_description" value="${esc(s.site_description)}" maxlength="80"></div>
      </div>
      <label>URL โลโก้ <span class="muted small">(PNG/SVG/JPG แนะนำสี่เหลี่ยมจัตุรัส · เว้นว่าง = ใช้ไอคอนเริ่มต้น)</span></label>
      <div class="row" style="flex-wrap:nowrap">
        <span class="logo-preview" id="logoPreview"></span>
        <input name="logo_url" value="${esc(s.logo_url)}" placeholder="https://example.com/logo.png" class="mono">
      </div>
      <div class="hint" id="logoHint"></div>

      <h2 style="margin-top:26px">สี</h2>
      <label>สีหลัก <span class="muted small">(ปุ่ม ลิงก์ แท็บที่เลือก)</span></label>
      <div class="row">
        <input type="color" id="brandPick" value="${esc(s.brand_color)}" class="swatch-input">
        <input name="brand_color" value="${esc(s.brand_color)}" class="mono" style="width:120px" pattern="#[0-9a-fA-F]{6}">
        <span class="swatches">${BRAND_SWATCHES.map((c) => `<button type="button" class="swatch" data-c="${c}" style="background:${c}" title="${c}"></button>`).join("")}</span>
      </div>
      <label>สีแถบด้านบน</label>
      <label class="inline"><input type="checkbox" id="topAuto" ${s.topbar_color ? "" : "checked"}> ใช้สีตามธีม (สว่าง/มืด)</label>
      <div class="row" id="topRow" style="margin-top:8px">
        <input type="color" id="topPick" value="${esc(s.topbar_color || "#1f2a48")}" class="swatch-input">
        <input id="topText" value="${esc(s.topbar_color || "#1f2a48")}" class="mono" style="width:120px">
        <span class="swatches">${["#1f2a48", "#0b1f3a", "#3b5bdb", "#0c8599", "#2f9e44", "#ffffff"].map((c) =>
          `<button type="button" class="swatch" data-top="${c}" style="background:${c}" title="${c}"></button>`).join("")}</span>
      </div>
      <p class="hint">การเปลี่ยนแปลงแสดงตัวอย่างที่แถบด้านบนทันที กด "บันทึก" เพื่อใช้กับทุกคน · โหมดมืด/สว่างเลือกได้เองที่ปุ่มมุมขวาบน (จำแยกแต่ละเครื่อง)</p>
      <div class="row" style="margin-top:16px"><button>บันทึก</button>
        <button type="button" class="ghost" id="siteReset">คืนค่าเริ่มต้น</button></div>
    </form>`;

  const f = document.getElementById("siteForm");
  const topRow = document.getElementById("topRow");
  const current = () => ({
    site_name: f.site_name.value.trim(), site_description: f.site_description.value.trim(), logo_url: f.logo_url.value.trim(),
    brand_color: f.brand_color.value.trim().toLowerCase(),
    topbar_color: document.getElementById("topAuto").checked ? "" : document.getElementById("topText").value.trim().toLowerCase(),
  });
  const valid = (c) => /^#[0-9a-f]{6}$/i.test(c);
  const preview = () => {
    const b = current();
    topRow.style.display = document.getElementById("topAuto").checked ? "none" : "";
    if (!valid(b.brand_color)) b.brand_color = branding.brand_color;
    if (b.topbar_color && !valid(b.topbar_color)) b.topbar_color = branding.topbar_color;
    applyBranding(b);
    const lp = document.getElementById("logoPreview");
    lp.innerHTML = b.logo_url ? `<img alt="" src="${esc(b.logo_url)}">` : DEFAULT_LOGO;
    document.getElementById("logoHint").textContent = "";
    const img = lp.querySelector("img");
    if (img) img.onerror = () => (document.getElementById("logoHint").textContent = "โหลดรูปจาก URL นี้ไม่ได้ — จะใช้ไอคอนเริ่มต้นแทน");
  };
  f.querySelectorAll("input").forEach((i) => (i.oninput = preview));
  document.getElementById("brandPick").oninput = (e) => { f.brand_color.value = e.target.value; preview(); };
  document.getElementById("topPick").oninput = (e) => { document.getElementById("topText").value = e.target.value; preview(); };
  document.getElementById("topAuto").onchange = preview;
  f.querySelectorAll("[data-c]").forEach((b) => (b.onclick = () => {
    f.brand_color.value = b.dataset.c; document.getElementById("brandPick").value = b.dataset.c; preview();
  }));
  f.querySelectorAll("[data-top]").forEach((b) => (b.onclick = () => {
    document.getElementById("topText").value = b.dataset.top; document.getElementById("topPick").value = b.dataset.top; preview();
  }));
  document.getElementById("siteReset").onclick = () => {
    f.site_name.value = "ISO 29110 DocGen"; f.site_description.value = "ระบบจัดทำเอกสารโครงการ"; f.logo_url.value = "";
    f.brand_color.value = "#3b5bdb"; document.getElementById("brandPick").value = "#3b5bdb";
    document.getElementById("topAuto").checked = true;
    preview();
  };
  f.onsubmit = (ev) => { ev.preventDefault(); saveSettings(ev.submitter, current(), loadBranding); };
  preview();
}

function settingsAI(el, s) {
  const sa = s.service_account_status, key = s.api_key_status;
  el.innerHTML = `
    <div class="grid2">
      <form class="card" id="aiForm">
        <h2>การเชื่อมต่อ Gemini</h2>
        <label class="radio-card ${s.ai_mode === "api_key" ? "on" : ""}"><input type="radio" name="ai_mode" value="api_key" ${s.ai_mode === "api_key" ? "checked" : ""}>
          <span><b>Developer API</b><span class="hint">ใช้ <code>GEMINI_API_KEY</code> หรือ <code>GEMINI_LIVE_API_KEY</code> จาก .env</span>
          ${key.present ? `<span class="badge ok">พบ ${esc(key.source)} (${esc(key.masked)})</span>` : '<span class="badge err">ไม่พบ key ใน .env</span>'}</span></label>
        <label class="radio-card ${s.ai_mode === "vertex" ? "on" : ""}"><input type="radio" name="ai_mode" value="vertex" ${s.ai_mode === "vertex" ? "checked" : ""}>
          <span><b>Vertex AI</b><span class="hint">service account · คิดค่าใช้จ่ายที่ GCP project</span>
          ${sa.uploaded ? `<span class="badge ok">${esc(sa.client_email)}</span>` : '<span class="badge err">ยังไม่มีไฟล์ service account</span>'}</span></label>
        <div class="grid2">
          <div><label>Model</label><input name="model" value="${esc(s.model)}" list="models" class="mono">
            <datalist id="models"><option value="gemini-2.5-flash"><option value="gemini-2.5-pro"><option value="gemini-2.5-flash-lite"></datalist></div>
          <div><label>Temperature <span class="muted small">(ตอนสัมภาษณ์)</span></label>
            <input name="temperature" type="number" step="0.1" min="0" max="1" value="${s.temperature}"></div>
        </div>
        <div class="grid2">
          <div><label>Vertex location</label><input name="vertex_location" value="${esc(s.vertex_location)}" class="mono"></div>
          <div><label>Vertex project ID</label><input name="vertex_project" value="${esc(s.vertex_project)}" class="mono"
            placeholder="${esc(sa.project_id || "ใช้จากไฟล์ service account")}"></div>
        </div>
        <div class="row" style="margin-top:16px"><button>บันทึก</button><button type="button" class="ghost" id="test">ทดสอบการเชื่อมต่อ</button></div>
      </form>
      <div class="card">
        <h2>Service account (Vertex AI)</h2>
        <p class="small muted">อัปโหลดไฟล์ JSON ของ service account ที่มีสิทธิ์ <code>roles/aiplatform.user</code> ระบบเก็บไว้ที่ <code>secrets/gcp-service-account.json</code></p>
        ${sa.uploaded ? `<div class="finding info"><span>ใช้อยู่: <b>${esc(sa.client_email)}</b><br><span class="small muted">project ${esc(sa.project_id)}</span></span></div>` : ""}
        <input type="file" id="saFile" accept=".json,application/json" style="margin-top:8px">
        <div class="row" style="margin-top:12px"><button id="saUpload">${ICON.upload} อัปโหลด</button>
          ${sa.uploaded ? `<button class="danger" id="saDelete">${ICON.trash} ลบไฟล์</button>` : ""}</div>
      </div>
    </div>`;
  const form = document.getElementById("aiForm");
  form.querySelectorAll('input[name="ai_mode"]').forEach((r) => (r.onchange = () =>
    form.querySelectorAll(".radio-card").forEach((c) => c.classList.toggle("on", c.querySelector("input").checked))));
  form.onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(form));
    f.temperature = parseFloat(f.temperature);
    saveSettings(ev.submitter, f, () => viewSettings("ai"));
  };
  document.getElementById("test").onclick = (e) => busy(e.currentTarget, async () => {
    const r = await api("/api/settings/test", { method: "POST" });
    toast(`เชื่อมต่อสำเร็จ (${r.mode}, ${r.model}): ${r.reply}`);
  });
  document.getElementById("saUpload").onclick = (e) => busy(e.currentTarget, async () => {
    const file = document.getElementById("saFile").files[0];
    if (!file) throw new Error("เลือกไฟล์ก่อน");
    const fd = new FormData();
    fd.append("file", file);
    await api("/api/settings/service-account", { method: "POST", body: fd });
    toast("อัปโหลดแล้ว");
    viewSettings("ai");
  });
  const del = document.getElementById("saDelete");
  if (del) del.onclick = (e) => confirm("ลบไฟล์ service account?") && busy(e.currentTarget, async () => {
    await api("/api/settings/service-account", { method: "DELETE" });
    viewSettings("ai");
  });
}

function settingsCompany(el, s) {
  el.innerHTML = `
    <form class="card" id="coForm" style="max-width:760px">
      <h2>ข้อมูลบริษัท</h2>
      <p class="small muted" style="margin-top:-6px">ใช้ในหัวเอกสาร หน้าปก บันทึกข้อความ และชื่อไฟล์</p>
      <label>ชื่อบริษัท</label><input name="company_name" value="${esc(s.company_name)}">
      <div class="grid2">
        <div><label>ชื่อย่อ <span class="muted small">(ตัวแปร {company} ในชื่อไฟล์)</span></label><input name="company_short" value="${esc(s.company_short)}" class="mono"></div>
        <div><label>ส่วนงาน <span class="muted small">(บันทึกข้อความ)</span></label><input name="department" value="${esc(s.department)}"></div>
      </div>
      <label class="inline" style="margin-top:16px"><input type="checkbox" name="thai_digits" ${s.thai_digits ? "checked" : ""}> ใช้เลขไทยในเลขหน้าและวันที่</label>
      <div class="row" style="margin-top:16px"><button>บันทึก</button></div>
    </form>`;
  document.getElementById("coForm").onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(ev.target));
    f.thai_digits = ev.target.thai_digits.checked;
    saveSettings(ev.submitter, f);
  };
}

function settingsFormat(el, s) {
  el.innerHTML = `
    <form class="card" id="fmtForm">
      <h2>ชื่อไฟล์และรหัสเอกสาร</h2>
      <p class="small muted" style="margin-top:-6px">ตัวแปร: <code>{company}</code> ชื่อย่อบริษัท · <code>{project}</code> รหัสโครงการ ·
        <code>{doc}</code> รหัสเอกสาร (SOW, SRS…) · <code>{item}</code> ลำดับรายการ · <code>{version}</code> ฉบับที่ ·
        <code>{date}</code> วันที่จัดทำ · <code>{stage}</code> ขั้น — มีผลกับเอกสารที่สร้างใหม่ และแก้รายไฟล์ได้ในหน้าสร้างเอกสาร</p>
      <div class="grid2">
        <div><label>รูปแบบชื่อไฟล์ <span class="muted small">(ไม่ต้องใส่ .docx/.xlsx)</span></label>
          <input name="filename_pattern" value="${esc(s.filename_pattern)}" class="mono" data-preview></div>
        <div><label>รูปแบบรหัสเอกสาร <span class="muted small">(แสดงในหัวเอกสาร)</span></label>
          <input name="doc_no_pattern" value="${esc(s.doc_no_pattern)}" class="mono" data-preview></div>
      </div>
      <div class="preview-box">ตัวอย่าง &nbsp;<code id="pvFile"></code>.docx &nbsp;·&nbsp; รหัส <code id="pvDocNo"></code></div>
      <div class="grid2">
        <div><label>รูปแบบ {date} <span class="muted small">(%d วัน %m เดือน %b เดือนย่อ %y/%Y ปี)</span></label>
          <input name="file_date_format" value="${esc(s.file_date_format)}" class="mono" data-preview></div>
        <div><label>ฉบับเริ่มต้น</label><input name="version_first" value="${esc(s.version_first)}" class="mono" data-preview></div>
      </div>
      <label>การนับฉบับเมื่อสร้างซ้ำ</label>
      <select name="version_scheme" style="max-width:380px">
        <option value="minor" ${s.version_scheme === "minor" ? "selected" : ""}>ฉบับย่อย: 1.0 → 1.1 → 1.2</option>
        <option value="major" ${s.version_scheme === "major" ? "selected" : ""}>ฉบับหลัก: 1.0 → 2.0 → 3.0</option>
      </select>

      <h2 style="margin-top:28px">หน้าตาเอกสาร</h2>
      <div class="grid2">
        <div><label>ฟอนต์</label><input name="font_name" value="${esc(s.font_name)}" list="fonts">
          <datalist id="fonts"><option value="TH Sarabun New"><option value="TH SarabunPSK"><option value="Angsana New"><option value="Cordia New"></datalist></div>
        <div><label>ขนาดตัวอักษรเนื้อหา (pt)</label><input name="font_size" type="number" min="10" max="24" value="${s.font_size}"></div>
      </div>
      <label class="inline" style="margin-top:14px"><input type="checkbox" name="cover_page" ${s.cover_page ? "checked" : ""}> มีหน้าปกในเอกสาร Word (รายงาน)</label>

      <h2 style="margin-top:28px">AI ตอนเขียนเอกสาร</h2>
      <label>Temperature <span class="muted small">(ต่ำ = ผลคงที่ระหว่างการสร้างซ้ำ แนะนำ 0.1)</span></label>
      <input name="gen_temperature" type="number" step="0.05" min="0" max="1" value="${s.gen_temperature}" style="max-width:200px">
      <div class="row" style="margin-top:18px"><button>บันทึก</button></div>
    </form>`;

  const fmt = document.getElementById("fmtForm");
  const strftime = (fmtStr, d) => fmtStr
    .replace(/%d/g, String(d.getDate()).padStart(2, "0")).replace(/%m/g, String(d.getMonth() + 1).padStart(2, "0"))
    .replace(/%b/g, d.toLocaleString("en", { month: "short" })).replace(/%Y/g, d.getFullYear())
    .replace(/%y/g, String(d.getFullYear()).slice(-2));
  const preview = () => {
    const tokens = { company: s.company_short, project: "Toyota_LLMIntent-2025-001", doc: "SOW", item: "",
      version: fmt.version_first.value, date: strftime(fmt.file_date_format.value, new Date()), stage: "s1_planning" };
    const fill = (pat) => pat.replace(/\{(\w+)\}/g, (m, k) => (k in tokens ? tokens[k] : m));
    document.getElementById("pvFile").textContent = fill(fmt.filename_pattern.value);
    document.getElementById("pvDocNo").textContent = fill(fmt.doc_no_pattern.value);
  };
  fmt.querySelectorAll("[data-preview]").forEach((i) => (i.oninput = preview));
  preview();
  fmt.onsubmit = (ev) => {
    ev.preventDefault();
    const f = Object.fromEntries(new FormData(fmt));
    f.cover_page = fmt.cover_page.checked;
    f.font_size = parseInt(f.font_size, 10);
    f.gen_temperature = parseFloat(f.gen_temperature);
    saveSettings(ev.submitter, f);
  };
}
