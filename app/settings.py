"""Runtime settings: paths, persisted config (data/config.json), secrets."""
import json
import os
from pathlib import Path

BASE_DIR = Path(os.getenv("APP_BASE_DIR", Path(__file__).resolve().parent.parent))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
SECRETS_DIR = Path(os.getenv("SECRETS_DIR", BASE_DIR / "secrets"))
CONFIG_PATH = DATA_DIR / "config.json"
SA_PATH = SECRETS_DIR / "gcp-service-account.json"

for d in (DATA_DIR, STORAGE_DIR, SECRETS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# docker-compose injects .env via env_file; when run directly, read it here
_ENV_FILE = BASE_DIR / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _k, _sep, _v = _line.strip().partition("=")
        if _sep and _k and not _k.startswith("#"):
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

DEFAULTS = {
    # "api_key"  -> GEMINI_API_KEY / GEMINI_LIVE_API_KEY from .env (Developer API)
    # "vertex"   -> service-account JSON in secrets/ (billed to the GCP project)
    "ai_mode": "api_key",
    "model": "gemini-2.5-flash",
    "vertex_location": "asia-southeast1",
    "vertex_project": "",
    "temperature": 0.3,
    # ── website branding ──
    "site_name": "ISO 29110 DocGen",
    "site_description": "ระบบจัดทำเอกสารโครงการ",
    "logo_url": "",                      # empty = built-in icon
    "brand_color": "#3b5bdb",            # buttons, links, active tabs
    "topbar_color": "",                  # empty = follow light/dark theme
    # ── accounts ──
    "registration_mode": "approval",     # open: active immediately | approval: admin approves | closed
    "log_reads": True,                   # also log GET requests (page loads, downloads are always logged)
    "log_retention_days": 365,           # 0 = keep forever
    "company_name": "บริษัท ซัน ซิสเต็มส์ จำกัด",
    "company_short": "SUN",
    "department": "ฝ่ายพัฒนาระบบ",
    "thai_digits": False,
    # ── document output ──
    # tokens: {company} {project} {doc} {item} {version} {date} {stage}
    "filename_pattern": "{company}_{project}_{doc}{item}_v{version}",
    "doc_no_pattern": "{company}_{project}_{doc}{item}",
    "file_date_format": "%d-%b-%y",      # how {date} is written, e.g. 03-Oct-26
    "version_first": "1.0",
    "version_scheme": "minor",           # minor: 1.0→1.1→1.2   major: 1.0→2.0→3.0
    "font_name": "TH Sarabun New",
    "font_size": 16,
    "cover_page": True,                  # Word reports start with a cover page
    "gen_temperature": 0.1,              # AI temperature when writing documents
}

FILENAME_TOKENS = ("company", "project", "doc", "item", "version", "date", "stage")


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return cfg


def save_config(updates: dict) -> dict:
    cfg = load_config()
    cfg.update({k: v for k, v in updates.items() if k in DEFAULTS})
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_PATH)
    return cfg


def api_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_LIVE_API_KEY") or ""


def service_account_info() -> dict | None:
    if not SA_PATH.exists():
        return None
    try:
        return json.loads(SA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"error": "อ่านไฟล์ service account ไม่ได้"}


def public_config() -> dict:
    """Config plus credential status, safe to send to the browser (no secrets)."""
    cfg = load_config()
    key = api_key()
    sa = service_account_info()
    cfg["api_key_status"] = {
        "present": bool(key),
        "source": "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else ("GEMINI_LIVE_API_KEY" if key else None),
        "masked": (key[:4] + "…" + key[-4:]) if len(key) > 8 else None,
    }
    cfg["service_account_status"] = {
        "uploaded": sa is not None and "error" not in sa,
        "project_id": (sa or {}).get("project_id"),
        "client_email": (sa or {}).get("client_email"),
        "error": (sa or {}).get("error"),
    }
    return cfg
