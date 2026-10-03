"""Gemini client supporting Developer API (api key) and Vertex AI (service account)."""
import json
import re

from google import genai
from google.genai import types

from . import settings


class LLMError(RuntimeError):
    pass


def _client():
    cfg = settings.load_config()
    if cfg["ai_mode"] == "vertex":
        sa = settings.service_account_info()
        if not sa or "error" in sa:
            raise LLMError("ยังไม่ได้อัปโหลด service account JSON (โหมด Vertex AI)")
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            str(settings.SA_PATH), scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return genai.Client(
            vertexai=True,
            project=cfg.get("vertex_project") or sa.get("project_id"),
            location=cfg.get("vertex_location") or "asia-southeast1",
            credentials=creds,
        )
    key = settings.api_key()
    if not key:
        raise LLMError("ไม่พบ GEMINI_API_KEY หรือ GEMINI_LIVE_API_KEY ในไฟล์ .env")
    return genai.Client(api_key=key)


def _parse_json(text: str):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise LLMError("AI ตอบกลับมาไม่ใช่ JSON ที่อ่านได้")


def generate_json(system: str, prompt: str, temperature: float | None = None) -> dict:
    cfg = settings.load_config()
    # keep the client referenced for the whole call: google-genai closes its
    # HTTP session when the client object is garbage-collected
    client = _client()
    try:
        resp = client.models.generate_content(
            model=cfg["model"],
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=cfg["temperature"] if temperature is None else temperature,
                response_mime_type="application/json",
            ),
        )
    except LLMError:
        raise
    except Exception as e:  # SDK raises many types; surface a readable message
        raise LLMError(f"เรียก Gemini ไม่สำเร็จ: {e}") from e
    return _parse_json(resp.text)


def test_connection() -> dict:
    cfg = settings.load_config()
    out = generate_json("Reply with JSON only.", 'Return {"ok": true, "reply": "สวัสดี"}', temperature=0)
    return {"ok": bool(out.get("ok")), "mode": cfg["ai_mode"], "model": cfg["model"], "reply": out.get("reply")}
