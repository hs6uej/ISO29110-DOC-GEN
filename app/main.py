"""ISO 29110 DocGen — FastAPI entrypoint."""
import io
import json
import os
import re
import time
import zipfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import audit, auth, db, evidence, files, generator, interview, llm, settings
from .catalog import DOC_BY_KEY, DOCUMENTS, EVIDENCE_STATUSES, STAGE_BY_KEY, STAGES

app = FastAPI(title="ISO 29110 DocGen")
db.init()
print("[auth] bootstrap admin:", auth.bootstrap_admin(
    os.getenv("ADMIN_USERNAME", ""), os.getenv("ADMIN_PASSWORD", ""), os.getenv("ADMIN_EMAIL", ""), os.getenv("ADMIN_NAME", "")))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
_keep_days = int(settings.load_config().get("log_retention_days") or 0)
if _keep_days > 0:
    db.execute("DELETE FROM activity_logs WHERE ts < datetime('now','localtime', ?)", (f"-{_keep_days} days",))
db.execute("DELETE FROM sessions WHERE expires_at < datetime('now','localtime')")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def current_user(request: Request) -> dict:
    return getattr(request.state, "user", None) or {}


@app.middleware("http")
async def auth_and_audit(request: Request, call_next):
    """Resolve the session, enforce role permissions, and log every API/file request."""
    started = time.perf_counter()
    path, method = request.url.path, request.method
    user, sess = auth.session_user(request.cookies.get(auth.SESSION_COOKIE))
    request.state.user, request.state.session = user, sess
    tracked = path.startswith(("/api/", "/files/"))
    body = b""
    if tracked and method in ("POST", "PUT", "PATCH", "DELETE"):
        body = await request.body()  # cached by Starlette, the endpoint still receives it

    needed = auth.required_role(method, path)
    if needed and not user:
        response = JSONResponse({"detail": "กรุณาเข้าสู่ระบบ"}, status_code=401)
    elif needed and not auth.has_role(user, needed):
        response = JSONResponse({"detail": "ไม่มีสิทธิ์ใช้งานส่วนนี้"}, status_code=403)
    else:
        response = await call_next(request)

    if not tracked:
        response.headers["Cache-Control"] = "no-cache"  # UI files change with each update
        return response
    cfg = settings.load_config()
    action = audit.describe(method, path)
    if method == "GET" and action.startswith("api.") and not cfg.get("log_reads", True):
        return response
    try:
        audit.log(
            action, user=getattr(request.state, "user", None) or user, ip=client_ip(request),
            forwarded_for=request.headers.get("x-forwarded-for", ""), user_agent=request.headers.get("user-agent", ""),
            session_id=(getattr(request.state, "session", None) or sess or {}).get("id"),
            method=method, path=path, query=request.url.query, status=response.status_code,
            duration_ms=int((time.perf_counter() - started) * 1000), target=path.rsplit("/", 1)[-1],
            # whole body hidden for anything password-related, field-level redaction elsewhere
            body="[redacted]" if body and "password" in path else audit.body_for_log(body, request.headers.get("content-type", "")),
        )
    except Exception as e:  # logging must never break the request
        print("[audit] failed:", e)
    return response


def event(request: Request, action: str, target="", detail=None, user=None):
    """Named domain event in the activity log (in addition to the request row)."""
    audit.log(action, user=user or current_user(request), ip=client_ip(request),
              forwarded_for=request.headers.get("x-forwarded-for", ""), user_agent=request.headers.get("user-agent", ""),
              method=request.method, path=request.url.path, target=target, detail=detail,
              session_id=(getattr(request.state, "session", None) or {}).get("id"))


# ── Auth ────────────────────────────────────────────────────────────────────

class LoginIn(BaseModel):
    login: str
    password: str
    remember: bool = False


class RegisterIn(BaseModel):
    email: str
    password: str
    name: str
    username: str = ""
    position: str = ""
    phone: str = ""


def _set_session_cookie(response: Response, token: str, expires, remember: bool):
    response.set_cookie(auth.SESSION_COOKIE, token, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/",
                        max_age=int((expires - datetime.now()).total_seconds()) if remember else None)


@app.get("/api/auth/state")
def auth_state(request: Request):
    """Who is logged in (or null) and whether this is a fresh install / registration is open."""
    return {"user": auth.public_user(current_user(request) or None), "needs_setup": auth.user_count() == 0,
            "registration_mode": settings.load_config().get("registration_mode", "approval")}


@app.get("/api/branding")
def branding():
    cfg = settings.load_config()
    return {k: cfg[k] for k in ("site_name", "site_description", "logo_url", "brand_color", "topbar_color")}


@app.post("/api/auth/register")
def register(body: RegisterIn, request: Request):
    mode = settings.load_config().get("registration_mode", "approval")
    try:
        u = auth.register(body.email, body.password, body.name, body.position, body.phone, mode, body.username)
    except auth.AuthError as e:
        event(request, "auth.register_failed", body.email, {"reason": str(e)})
        raise HTTPException(e.status, str(e))
    event(request, "auth.register", u["email"], {"role": u["role"], "status": u["status"]}, user=u)
    return {"user": auth.public_user(u), "active": u["status"] == "active"}


@app.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    ip = client_ip(request)
    try:
        u = auth.authenticate(body.login, body.password, ip)
    except auth.AuthError as e:
        event(request, "auth.login_failed", body.login.strip().lower(), {"reason": str(e)})
        raise HTTPException(e.status, str(e))
    token, expires = auth.create_session(u["id"], ip, request.headers.get("user-agent", ""), body.remember)
    _set_session_cookie(response, token, expires, body.remember)
    request.state.user = u
    event(request, "auth.login", u["email"], {"remember": body.remember}, user=u)
    return {"user": auth.public_user(u)}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    if current_user(request):
        event(request, "auth.logout", current_user(request).get("email", ""))
    auth.end_session(request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


# ── Profile ─────────────────────────────────────────────────────────────────

class ProfileIn(BaseModel):
    name: str | None = None
    position: str | None = None
    phone: str | None = None


class PasswordIn(BaseModel):
    current: str
    new: str


@app.get("/api/profile")
def profile(request: Request):
    u = current_user(request)
    return {"user": auth.public_user(u), "sessions": auth.list_sessions(u["id"]),
            "current_session": (request.state.session or {}).get("id"),
            "activity": audit.query(user_id=u["id"], include_reads=False, limit=50)["rows"]}


@app.patch("/api/profile")
def update_profile(body: ProfileIn, request: Request):
    try:
        u = auth.update_profile(current_user(request)["id"], body.name, body.position, body.phone)
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e))
    event(request, "profile.update", u["email"], body.model_dump(exclude_none=True))
    return auth.public_user(u)


@app.post("/api/profile/password")
def change_password(body: PasswordIn, request: Request):
    u = current_user(request)
    try:
        auth.change_password(u["id"], body.current, body.new)
    except auth.AuthError as e:
        event(request, "profile.password_failed", u["email"], {"reason": str(e)})
        raise HTTPException(e.status, str(e))
    auth.revoke_user_sessions(u["id"], keep_session_id=(request.state.session or {}).get("id"))
    event(request, "profile.password_changed", u["email"])
    return {"ok": True}


@app.delete("/api/profile/sessions/{session_id}")
def revoke_my_session(session_id: int, request: Request):
    auth.revoke_session(session_id, current_user(request)["id"])
    event(request, "profile.session_revoked", session_id)
    return {"ok": True}


# ── Admin ───────────────────────────────────────────────────────────────────

class AdminUserIn(BaseModel):
    role: str | None = None
    status: str | None = None
    name: str | None = None
    position: str | None = None


class AdminCreateIn(RegisterIn):
    role: str = "editor"


@app.get("/api/admin/overview")
def admin_overview():
    today = date.today().isoformat()
    return {
        "users": db.rows("SELECT status, role, COUNT(*) n FROM users GROUP BY status, role"),
        "pending": db.row("SELECT COUNT(*) n FROM users WHERE status='pending'")["n"],
        "sessions": len(auth.list_sessions()),
        "events_today": db.row("SELECT COUNT(*) n FROM activity_logs WHERE ts>=?", (today,))["n"],
        "failed_logins_today": db.row("SELECT COUNT(*) n FROM activity_logs WHERE action='auth.login_failed' AND ts>=?", (today,))["n"],
        "errors_today": db.row("SELECT COUNT(*) n FROM activity_logs WHERE status>=500 AND ts>=?", (today,))["n"],
        "logs_total": db.row("SELECT COUNT(*) n FROM activity_logs")["n"],
        "top_users": db.rows("SELECT user_email, user_name, COUNT(*) n FROM activity_logs WHERE ts>=? AND user_email<>'' "
                             "GROUP BY user_email ORDER BY n DESC LIMIT 5", (today,)),
        "recent": audit.query(include_reads=False, limit=12)["rows"],
    }


@app.get("/api/admin/users")
def admin_users():
    rows = db.rows("SELECT * FROM users ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, created_at DESC")
    return [auth.public_user(u) for u in rows]


@app.post("/api/admin/users")
def admin_create_user(body: AdminCreateIn, request: Request):
    if body.role not in auth.ROLES:
        raise HTTPException(400, "บทบาทไม่ถูกต้อง")
    try:
        u = auth.register(body.email, body.password, body.name, body.position, body.phone, "open", body.username)
        u = auth.admin_update(u["id"], current_user(request)["id"], role=body.role, status="active")
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e))
    event(request, "admin.user_create", u["email"], {"role": u["role"]})
    return auth.public_user(u)


@app.patch("/api/admin/users/{uid}")
def admin_update_user(uid: int, body: AdminUserIn, request: Request):
    before = auth.public_user(auth.get_user(uid))
    try:
        u = auth.admin_update(uid, current_user(request)["id"], body.role, body.status, body.name, body.position)
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e))
    event(request, "admin.user_update", u["email"], {"before": {k: before[k] for k in ("role", "status")},
                                                     "after": body.model_dump(exclude_none=True)})
    return auth.public_user(u)


@app.post("/api/admin/users/{uid}/reset-password")
def admin_reset_password(uid: int, request: Request):
    try:
        temp = auth.admin_reset_password(uid)
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e))
    event(request, "admin.password_reset", auth.get_user(uid)["email"])
    return {"temporary_password": temp}


@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: int, request: Request):
    u = auth.get_user(uid)
    try:
        auth.delete_user(uid, current_user(request)["id"])
    except auth.AuthError as e:
        raise HTTPException(e.status, str(e))
    event(request, "admin.user_delete", (u or {}).get("email", uid))
    return {"ok": True}


@app.get("/api/admin/sessions")
def admin_sessions():
    return auth.list_sessions()


@app.delete("/api/admin/sessions/{session_id}")
def admin_revoke_session(session_id: int, request: Request):
    auth.revoke_session(session_id)
    event(request, "admin.session_revoked", session_id)
    return {"ok": True}


@app.get("/api/admin/logs")
def admin_logs(q: str = "", user_id: int | None = None, action: str = "", date_from: str = "", date_to: str = "",
               status: str = "", reads: bool = True, limit: int = 100, offset: int = 0):
    return audit.query(q, user_id, action, date_from, date_to, status, reads, min(max(limit, 1), 500), max(offset, 0))


@app.get("/api/admin/logs.csv")
def admin_logs_csv(request: Request, q: str = "", user_id: int | None = None, action: str = "", date_from: str = "",
                   date_to: str = "", status: str = "", reads: bool = True):
    rows = audit.query(q, user_id, action, date_from, date_to, status, reads, limit=100000)["rows"]
    event(request, "admin.logs_export", f"{len(rows)} rows")
    name = f"activity_logs_{date.today():%Y%m%d}.csv"
    return Response(audit.to_csv(rows), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={name}"})


# ── Settings ────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    return settings.public_config()


@app.post("/api/settings")
def post_settings(body: dict):
    if body.get("ai_mode") not in (None, "api_key", "vertex"):
        raise HTTPException(400, "ai_mode ต้องเป็น api_key หรือ vertex")
    if body.get("version_scheme") not in (None, "minor", "major"):
        raise HTTPException(400, "version_scheme ต้องเป็น minor หรือ major")
    if body.get("registration_mode") not in (None, "open", "approval", "closed"):
        raise HTTPException(400, "registration_mode ต้องเป็น open, approval หรือ closed")
    if "log_retention_days" in body:
        try:
            body["log_retention_days"] = max(0, int(body["log_retention_days"]))
        except (TypeError, ValueError):
            raise HTTPException(400, "จำนวนวันเก็บ log ต้องเป็นตัวเลข")
    if "log_reads" in body:
        body["log_reads"] = bool(body["log_reads"])
    try:
        for key, cast in (("font_size", int), ("temperature", float), ("gen_temperature", float)):
            if key in body:
                body[key] = cast(body[key])
        if "version_first" in body and not generator.VERSION_RE.match(str(body["version_first"])):
            raise ValueError("ฉบับเริ่มต้นต้องเป็นตัวเลข เช่น 1.0")
        for key in ("filename_pattern", "doc_no_pattern"):
            if key in body:
                unknown = set(re.findall(r"\{(\w+)\}", body[key])) - set(settings.FILENAME_TOKENS)
                if unknown:
                    raise ValueError(f"ไม่รู้จักตัวแปร {', '.join('{' + u + '}' for u in sorted(unknown))}")
        if "file_date_format" in body:
            date.today().strftime(body["file_date_format"])
        for key, required in (("brand_color", True), ("topbar_color", False)):
            if key in body:
                body[key] = str(body[key]).strip().lower()
                if (required or body[key]) and not re.fullmatch(r"#[0-9a-f]{6}", body[key]):
                    raise ValueError("สีต้องอยู่ในรูปแบบ #RRGGBB เช่น #3b5bdb")
        if "logo_url" in body:
            body["logo_url"] = str(body["logo_url"]).strip()
            if body["logo_url"] and not re.match(r"^(https?://|/)", body["logo_url"]):
                raise ValueError("URL โลโก้ต้องขึ้นต้นด้วย http://, https:// หรือ /")
        if "site_name" in body and not str(body["site_name"]).strip():
            raise ValueError("ต้องมีชื่อเว็บไซต์")
    except (TypeError, ValueError) as e:
        raise HTTPException(400, str(e))
    settings.save_config(body)
    return settings.public_config()


@app.post("/api/settings/service-account")
async def upload_service_account(file: UploadFile = File(...)):
    content = await file.read()
    try:
        creds = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "ไฟล์ไม่ใช่ JSON")
    missing = [k for k in ("type", "project_id", "private_key", "client_email") if k not in creds]
    if missing or creds.get("type") != "service_account":
        raise HTTPException(400, f"ไม่ใช่ service account key ที่ถูกต้อง (ขาด: {', '.join(missing) or 'type'})")
    tmp = settings.SA_PATH.with_suffix(".tmp")
    tmp.write_bytes(content)
    os.chmod(tmp, 0o600)
    os.replace(tmp, settings.SA_PATH)
    return settings.public_config()


@app.delete("/api/settings/service-account")
def delete_service_account():
    settings.SA_PATH.unlink(missing_ok=True)
    return settings.public_config()


@app.post("/api/settings/test")
def test_ai():
    try:
        return llm.test_connection()
    except llm.LLMError as e:
        raise HTTPException(400, str(e))


# ── Catalog ─────────────────────────────────────────────────────────────────

@app.get("/api/catalog")
def catalog():
    return {"stages": STAGES, "documents": DOCUMENTS, "statuses": EVIDENCE_STATUSES}


# ── Projects ────────────────────────────────────────────────────────────────

class ProjectIn(BaseModel):
    name: str
    code: str
    customer: str = ""
    summary: str = ""


def _clean_code(code: str) -> str:
    code = re.sub(r"[^\w\-]+", "_", code.strip())
    if not code:
        raise HTTPException(400, "ต้องระบุรหัสโครงการ")
    return code


@app.get("/api/projects")
def list_projects():
    out = []
    for p in db.rows("SELECT id, name, code, customer, created_at, updated_at FROM projects ORDER BY updated_at DESC"):
        facts = db.get_project(p["id"])["facts"]
        stages = interview.stage_progress(facts)
        made = db.row("SELECT COUNT(DISTINCT doc_key) n, COUNT(*) files FROM documents WHERE project_id=?", (p["id"],))
        findings = evidence.checks(p["id"])
        p.update(
            stages_done=sum(s["done"] for s in stages), stages_total=len(stages),
            docs_made=made["n"], docs_total=len(DOCUMENTS), files=made["files"],
            errors=sum(f["level"] == "error" for f in findings), warnings=sum(f["level"] == "warn" for f in findings),
        )
        out.append(p)
    return out


@app.post("/api/projects")
def create_project(p: ProjectIn, request: Request):
    code = _clean_code(p.code)
    if db.row("SELECT id FROM projects WHERE code=?", (code,)):
        raise HTTPException(400, f"รหัสโครงการ {code} มีอยู่แล้ว")
    uid = current_user(request).get("id")
    pid = db.execute("INSERT INTO projects(name, code, customer, summary, created_by, updated_by) VALUES (?,?,?,?,?,?)",
                     (p.name.strip(), code, p.customer.strip(), p.summary.strip(), uid, uid))
    for d in DOCUMENTS:
        db.execute("INSERT INTO evidence(project_id, doc_key) VALUES (?,?)", (pid, d["key"]))
    return db.get_project(pid)


def _project(pid: int) -> dict:
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "ไม่พบโครงการ")
    return p


@app.get("/api/projects/{pid}")
def get_project(pid: int):
    p = _project(pid)
    p["stages"] = interview.stage_progress(p["facts"])
    return p


@app.patch("/api/projects/{pid}")
def update_project(pid: int, p: ProjectIn, request: Request):
    _project(pid)
    db.execute("UPDATE projects SET name=?, customer=?, summary=?, updated_by=?, updated_at=datetime('now','localtime') WHERE id=?",
               (p.name.strip(), p.customer.strip(), p.summary.strip(), current_user(request).get("id"), pid))
    return get_project(pid)


@app.delete("/api/projects/{pid}")
def delete_project(pid: int):
    _project(pid)
    db.execute("DELETE FROM projects WHERE id=?", (pid,))
    return {"ok": True}


@app.put("/api/projects/{pid}/facts")
def put_facts(pid: int, facts: dict):
    p = _project(pid)
    # keep internal bookkeeping (_coverage, _gaps ...) unless explicitly provided
    merged = {k: v for k, v in p["facts"].items() if k.startswith("_")}
    merged.update(facts)
    db.save_facts(pid, merged)
    return get_project(pid)


# ── Interview ───────────────────────────────────────────────────────────────

class AnswerIn(BaseModel):
    stage: str
    text: str | None = None


@app.get("/api/projects/{pid}/messages")
def messages(pid: int, stage: str):
    _project(pid)
    return interview.history(pid, stage)


@app.post("/api/projects/{pid}/interview")
def interview_turn(pid: int, body: AnswerIn, request: Request):
    _project(pid)
    if body.stage not in STAGE_BY_KEY:
        raise HTTPException(400, "ไม่รู้จักขั้นนี้")
    try:
        out = interview.turn(pid, body.stage, (body.text or "").strip() or None)
        # the answer and the AI reply of this turn belong to whoever pressed send
        db.execute("UPDATE messages SET user_id=? WHERE project_id=? AND stage=? AND user_id IS NULL",
                   (current_user(request).get("id"), pid, body.stage))
        db.execute("UPDATE projects SET updated_by=?, updated_at=datetime('now','localtime') WHERE id=?",
                   (current_user(request).get("id"), pid))
        return out
    except llm.LLMError as e:
        raise HTTPException(502, str(e))


# ── Documents & evidence ────────────────────────────────────────────────────

class Signer(BaseModel):
    label: str = ""
    name: str = ""
    position: str = ""


class GenerateIn(BaseModel):
    item_index: int | None = None
    filename: str | None = None
    version: str | None = None
    doc_no: str | None = None
    prepared_date: str | None = None
    signatures: list[Signer] | None = None
    instructions: str | None = None


@app.get("/api/projects/{pid}/documents")
def documents(pid: int):
    _project(pid)
    return evidence.overview(pid)


@app.get("/api/projects/{pid}/documents/{doc_key}/plan")
def plan(pid: int, doc_key: str, item_index: int | None = None):
    _project(pid)
    if doc_key not in DOC_BY_KEY:
        raise HTTPException(404, "ไม่รู้จักเอกสารนี้")
    try:
        p = generator.plan(pid, doc_key, item_index)
    except ValueError as e:
        raise HTTPException(400, str(e))
    p.pop("item", None)
    return p


@app.post("/api/projects/{pid}/documents/{doc_key}/generate")
def generate(pid: int, doc_key: str, body: GenerateIn, request: Request):
    _project(pid)
    if doc_key not in DOC_BY_KEY:
        raise HTTPException(404, "ไม่รู้จักเอกสารนี้")
    opts = body.model_dump(exclude={"item_index"}, exclude_none=True)
    try:
        out = generator.generate(pid, doc_key, body.item_index, opts)
        db.execute("UPDATE documents SET created_by=?, source='ai' WHERE id=?", (current_user(request).get("id"), out["id"]))
        event(request, "document.generated", out["filename"], {"doc_key": doc_key, "version": out["version"],
                                                              "placeholders": out["placeholders"]})
        return out
    except ValueError as e:
        raise HTTPException(400, str(e))
    except llm.LLMError as e:
        raise HTTPException(502, str(e))


class ZipIn(BaseModel):
    ids: list[int] = []
    include_evidence_list: bool = False


@app.post("/api/projects/{pid}/download-zip")
def download_zip(pid: int, body: ZipIn):
    """Selected generated files (+ optional Evidence List) as one zip, kept in stage folders."""
    p = _project(pid)
    if not body.ids and not body.include_evidence_list:
        raise HTTPException(400, "ยังไม่ได้เลือกไฟล์")
    rows = db.rows(
        f"SELECT * FROM documents WHERE project_id=? AND id IN ({','.join('?' * len(body.ids)) or 'NULL'})",
        (pid, *body.ids),
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in rows:
            path = settings.STORAGE_DIR / d["rel_path"]
            if path.exists():
                stage = DOC_BY_KEY[d["doc_key"]]["stage"] if d["doc_key"] in DOC_BY_KEY else "other"
                zf.write(path, f"{stage}/{d['filename']}")
        if body.include_evidence_list:
            rel = evidence.export(pid)
            zf.write(settings.STORAGE_DIR / rel, Path(rel).name)
    cfg = settings.load_config()
    name = f"{cfg['company_short']}_{p['code']}_documents_{date.today():%Y%m%d}.zip"
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


class EvidenceIn(BaseModel):
    status: str | None = None
    links: str | None = None
    remark: str | None = None


@app.patch("/api/projects/{pid}/evidence/{doc_key}")
def patch_evidence(pid: int, doc_key: str, body: EvidenceIn, request: Request):
    _project(pid)
    if doc_key not in DOC_BY_KEY:
        raise HTTPException(404, "ไม่รู้จักเอกสารนี้")
    if body.status and body.status not in EVIDENCE_STATUSES:
        raise HTTPException(400, "สถานะไม่ถูกต้อง")
    evidence.update(pid, doc_key, body.status, body.links, body.remark)
    db.execute("UPDATE evidence SET updated_by=? WHERE project_id=? AND doc_key=?", (current_user(request).get("id"), pid, doc_key))
    return {"ok": True}


@app.get("/api/projects/{pid}/checks")
def checks(pid: int):
    _project(pid)
    return evidence.checks(pid)


@app.post("/api/projects/{pid}/export")
def export(pid: int):
    _project(pid)
    rel = evidence.export(pid)
    return {"path": rel, "url": f"/files/{rel}"}


class RenameIn(BaseModel):
    filename: str | None = None
    version: str | None = None


@app.patch("/api/documents/{doc_id}")
def rename_document(doc_id: int, body: RenameIn):
    try:
        return files.rename(doc_id, body.filename, body.version)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    try:
        return files.delete(doc_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.post("/api/documents/{doc_id}/upload")
async def upload_document_version(request: Request, doc_id: int, file: UploadFile = File(...), version: str | None = Form(None)):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "ไฟล์ใหญ่เกิน 50 MB")
    try:
        out = files.upload_version(doc_id, file.filename or "", content, version or None)
        db.execute("UPDATE documents SET created_by=?, source='upload' WHERE id=?", (current_user(request).get("id"), out["id"]))
        return out
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/documents/{doc_id}/download")
def download(doc_id: int):
    d = db.row("SELECT * FROM documents WHERE id=?", (doc_id,))
    if not d:
        raise HTTPException(404, "ไม่พบไฟล์")
    path = settings.STORAGE_DIR / d["rel_path"]
    if not path.exists():
        raise HTTPException(404, "ไฟล์ถูกลบออกจาก storage แล้ว")
    return FileResponse(path, filename=d["filename"])


@app.get("/files/{rel_path:path}")
def storage_file(rel_path: str):
    root = settings.STORAGE_DIR.resolve()
    path = (root / rel_path).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "ไม่พบไฟล์")
    return FileResponse(path, filename=path.name)


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
