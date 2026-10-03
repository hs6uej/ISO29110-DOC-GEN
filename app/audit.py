"""Activity log: every API request plus named events (who, when, where, what, result)."""
import csv
import io
import json
import re

from . import db

SECRET_KEYS = re.compile(r"pass(word)?|secret|token|api[_-]?key|private[_-]?key|authorization|cookie|^current$|^new$", re.I)
MAX_BODY = 8000  # characters of request body kept per log row


def redact(value):
    """Mask secrets anywhere in a JSON-like structure."""
    if isinstance(value, dict):
        return {k: ("***" if SECRET_KEYS.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def body_for_log(raw: bytes, content_type: str) -> str:
    if not raw:
        return ""
    if "multipart/form-data" in content_type:
        names = re.findall(rb'name="([^"]+)"(?:; filename="([^"]*)")?', raw[:20000])
        parts = [f"{n.decode(errors='replace')}={f.decode(errors='replace')!r}" if f else n.decode(errors="replace")
                 for n, f in names]
        return f"[multipart {len(raw)} bytes] " + ", ".join(parts)
    try:
        data = json.loads(raw)
        text = json.dumps(redact(data), ensure_ascii=False)
    except (ValueError, UnicodeDecodeError):
        text = raw[:MAX_BODY].decode("utf-8", errors="replace")
        text = re.sub(r'("?(password|token|secret)"?\s*[:=]\s*)("[^"]*"|\S+)', r"\1***", text, flags=re.I)
    return text[:MAX_BODY] + ("…" if len(text) > MAX_BODY else "")


def log(action: str, *, user=None, ip="", user_agent="", method="", path="", query="", status=None,
        duration_ms=None, target="", detail=None, body="", forwarded_for="", session_id=None):
    db.execute(
        "INSERT INTO activity_logs(user_id, user_email, user_name, ip, forwarded_for, user_agent, session_id, method, path, "
        "query, status, duration_ms, action, target, detail, body) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((user or {}).get("id"), (user or {}).get("email", ""), (user or {}).get("name", ""), ip, forwarded_for,
         (user_agent or "")[:400], session_id, method, path, query[:1000], status, duration_ms, action, str(target)[:300],
         json.dumps(redact(detail), ensure_ascii=False) if detail is not None else "", body),
    )


def describe(method: str, path: str) -> str:
    """Readable action name for a request path."""
    p = re.sub(r"/\d+", "/:id", path)
    table = {
        ("POST", "/api/projects"): "project.create", ("PATCH", "/api/projects/:id"): "project.update",
        ("DELETE", "/api/projects/:id"): "project.delete", ("PUT", "/api/projects/:id/facts"): "facts.edit",
        ("POST", "/api/projects/:id/interview"): "interview.turn", ("POST", "/api/projects/:id/export"): "evidence.export",
        ("POST", "/api/projects/:id/download-zip"): "document.download_zip", ("GET", "/api/documents/:id/download"): "document.download",
        ("PATCH", "/api/documents/:id"): "document.rename", ("DELETE", "/api/documents/:id"): "document.delete",
        ("POST", "/api/documents/:id/upload"): "document.upload_version", ("POST", "/api/settings"): "settings.update",
        ("POST", "/api/settings/service-account"): "settings.sa_upload", ("DELETE", "/api/settings/service-account"): "settings.sa_delete",
        ("POST", "/api/settings/test"): "settings.ai_test",
    }
    if (method, p) in table:
        return table[(method, p)]
    if re.fullmatch(r"/api/projects/:id/documents/\w+/generate", p) and method == "POST":
        return "document.generate"
    if re.fullmatch(r"/api/projects/:id/evidence/\w+", p) and method == "PATCH":
        return "evidence.update"
    if p.startswith("/files/"):
        return "file.download"
    return f"api.{method.lower()}"


def query(q: str = "", user_id=None, action: str = "", date_from: str = "", date_to: str = "", status: str = "",
          include_reads: bool = True, limit: int = 100, offset: int = 0) -> dict:
    where, args = [], []
    if q:
        where.append("(path LIKE ? OR target LIKE ? OR detail LIKE ? OR body LIKE ? OR user_email LIKE ? OR ip LIKE ? OR action LIKE ?)")
        args += [f"%{q}%"] * 7
    if user_id:
        where.append("user_id=?")
        args.append(int(user_id))
    if action:
        where.append("action LIKE ?")
        args.append(action.rstrip("*") + "%")
    if date_from:
        where.append("ts>=?")
        args.append(date_from)
    if date_to:
        where.append("ts<=?")
        args.append(date_to + " 23:59:59")
    if status == "error":
        where.append("(status>=400 OR action LIKE '%failed%')")
    if not include_reads:
        where.append("NOT (method='GET' AND action LIKE 'api.%')")
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.row(f"SELECT COUNT(*) n FROM activity_logs{clause}", tuple(args))["n"]
    rows = db.rows(f"SELECT * FROM activity_logs{clause} ORDER BY id DESC LIMIT ? OFFSET ?", (*args, limit, offset))
    return {"total": total, "rows": rows}


def to_csv(rows: list[dict]) -> str:
    cols = ["id", "ts", "user_email", "user_name", "action", "target", "method", "path", "query", "status",
            "duration_ms", "ip", "forwarded_for", "user_agent", "session_id", "detail", "body"]
    buf = io.StringIO()
    buf.write("﻿")  # Excel opens UTF-8 Thai correctly with a BOM
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
