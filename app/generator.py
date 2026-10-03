"""Generate a work product: facts -> Gemini (structured content) -> docx/xlsx file."""
import json
import re
from datetime import date

from . import db, llm, render_docx, render_xlsx, settings
from .catalog import DOC_BY_KEY, STAGE_BY_KEY
from .render_docx import render_form, render_memo, render_report
from .render_xlsx import render_workbook
from .thai import thai_date

PLACEHOLDER = "[ต้องระบุ:"

SYSTEM = """คุณคือผู้จัดทำเอกสารโครงการตามมาตรฐาน ISO/IEC 29110 Basic Profile สำหรับบริษัทไทย
เขียนด้วยภาษาไทยแบบทางการ (ภาษาราชการ) กระชับ ชัดเจน ศัพท์เทคนิคใช้ภาษาอังกฤษได้

กติกาสำคัญ:
1. ใช้เฉพาะข้อเท็จจริงที่ให้มาเท่านั้น ห้ามแต่งชื่อคน วันที่ ตัวเลข ผลทดสอบ หรือเหตุการณ์ที่ไม่มีในข้อมูล
2. ข้อมูลที่จำเป็นแต่ไม่มี ให้ใส่ "[ต้องระบุ: <สิ่งที่ต้องระบุ>]" แทน
   แต่ถ้าหาได้จากข้อเท็จจริงส่วนอื่นของโครงการ ให้ใช้ข้อมูลนั้น (เช่น ที่เก็บโค้ด = repository,
   ระยะงาน/phase จากชื่องาน: วิเคราะห์=Requirements, dev=Construction, เทส=Testing) ห้ามใส่ [ต้องระบุ] ในช่องที่ตอบได้
   ห้ามเพิ่มรายการ (แถว) ที่ไม่มีที่มาจากข้อมูล เพื่อให้ตารางมีแต่ช่องว่างรอกรอก
3. ตารางที่มาจากข้อมูลแบบ list ให้ใส่ครบทุกรายการตามข้อมูล
4. ช่องลงนาม: ใส่ชื่อ/ตำแหน่งได้เฉพาะเมื่อมีในข้อมูล ห้ามใส่วันที่ลงนาม (ให้ลงนามจริงภายหลัง)
5. เอกสารผลการทวนสอบ (checklist) ใช้รายการตรวจมาตรฐานได้ แต่ผลตรวจ/ข้อบกพร่องต้องมาจากข้อมูลจริงเท่านั้น
6. event_date_text = วันที่เกิดเหตุการณ์ที่เอกสารนี้บันทึก (ถ้ามี) เขียนแบบไทย เช่น "9 มิถุนายน 2568"
7. ชื่อบุคคลในเอกสาร: ตัดคำเรียกไม่เป็นทางการ เช่น "พี่" "น้อง" ออก ห้ามเติมคำนำหน้า (นาย/นาง/นางสาว)
   หรือนามสกุลเองถ้าไม่มีในข้อมูล ในช่องลงนามถ้ามีแค่ชื่อเล่น/ชื่อต้น ให้ใส่ "<ชื่อ> [ต้องระบุ: นามสกุล]"
8. คัดลอกชื่อคน อีเมล เลขที่ และรหัสต่าง ๆ ตามข้อมูลทุกตัวอักษร ห้ามแปล/ทับศัพท์ชื่อข้ามภาษา
   (ชื่ออังกฤษคงเป็นอังกฤษ) ผู้ว่าจ้าง/ลูกค้า ใช้ตามข้อมูลโครงการเสมอ
   fields ของแบบฟอร์ม: ไม่ต้องใส่ชื่อโครงการ รหัส ลูกค้า วันที่จัดทำ (ระบบพิมพ์หัวเอกสารให้แล้ว) ถ้าไม่มีข้อมูลอื่นให้เป็น []
9. เขียนกระชับ ไม่ทวนข้อมูลซ้ำในหลายส่วน ใส่เฉพาะเนื้อหาที่เอกสารประเภทนี้ต้องมี
10. หัวข้อที่ข้อมูลระบุว่า "ไม่มี" ให้เขียนว่าไม่มีตามจริง (ไม่ใช่ [ต้องระบุ])
11. ห้ามย้อนวันที่เอกสาร: วันที่ออกบันทึก/วันที่ลงนาม ใส่ได้เฉพาะเมื่อข้อมูลระบุวันที่ของเอกสารนั้นโดยตรง
    ห้ามใช้วันเริ่มโครงการหรือวันอื่นแทน ถ้าไม่มีให้ date_text เป็น "" (ระบบจะเว้นช่องให้เขียนตอนลงนาม)
12. ถ้าข้อมูล signatories กำหนดผู้ลงนามของเอกสารนี้ไว้ ให้ใช้ตามนั้นทุกตำแหน่ง ห้ามเพิ่ม/สลับเอง
    (ช่อง "ผู้แทนลูกค้า" ใส่เฉพาะเอกสารที่ต้องให้ลูกค้ายืนยัน)
13. เอกสารผลการทวนสอบ/ยืนยัน ที่ข้อมูลระบุว่า "ยังไม่มี" ให้จัดทำเป็นแบบฟอร์มพร้อมใช้:
    รายการตรวจครบ แต่ช่องผล วันที่ ผู้ทบทวน เว้นว่าง ("") เพื่อกรอกตอนทบทวนจริง ห้ามใส่ผลตรวจเอง
    ช่องลงนามของผู้ทบทวน/ผู้ยืนยันที่ยังไม่ได้ทำ ให้ name เป็น "" (ห้ามเลือกคนให้เอง)
    แบบฟอร์มยืนยันจากลูกค้า ให้มีตัวเลือก "☐ ยืนยัน  ☐ ยืนยันโดยมีข้อแก้ไข  ☐ ไม่ยืนยัน" และตารางข้อแก้ไขว่างให้กรอก
14. ถ้าข้อมูลระบุว่าเหตุการณ์เกิดด้วยวาจา/ไม่มีเอกสาร (เช่น แต่งตั้งด้วยวาจา) เอกสารนี้ต้องเขียนเป็น
    "การยืนยัน/บันทึกเหตุการณ์ที่เกิดขึ้นแล้ว" ตามจริง ห้ามเขียนให้ดูเหมือนเป็นเอกสารที่ออกในวันนั้น
15. ถ้ารายการมี record_type (เช่น "จัดทำย้อนหลัง") ต้องแสดงข้อความนั้นครบทุกคำเป็นบรรทัด/แถวแรกของเอกสาร
ตอบเป็น JSON เท่านั้น"""

SCHEMAS = {
    "report": """{
  "event_date_text": "string",
  "sections": [ { "heading": "string", "blocks": [
      { "type": "paragraph", "text": "string" },
      { "type": "bullets", "items": ["string"] },
      { "type": "numbered", "items": ["string"] },
      { "type": "table", "caption": "string", "columns": ["string"], "rows": [["string"]] } ] } ],
  "signatures": [ { "label": "ผู้จัดทำ|ผู้ทบทวน|ผู้อนุมัติ|ผู้แทนลูกค้า", "name": "string", "position": "string" } ]
}""",
    "form": """{
  "event_date_text": "string",
  "fields": [ { "label": "string", "value": "string" } ],
  "sections": [ { "heading": "string", "blocks": [ ...เหมือน report... ] } ],
  "signatures": [ { "label": "string", "name": "string", "position": "string" } ]
}""",
    "memo": """{
  "event_date_text": "string",
  "memo": { "to": "string", "subject": "string", "date_text": "วันที่ของบันทึกตามข้อเท็จจริง หรือ [ต้องระบุ: วันที่]", "body": ["ย่อหน้า 2-4 ย่อหน้า สั้น กระชับ แบบหนังสือราชการ (ด้วย... / จึง... / จึงเรียนมาเพื่อโปรดทราบ)"] },
  "sections": [ { "heading": "string", "blocks": [ { "type": "table", "columns": ["string"], "rows": [["string"]] } ] } ],
  หมายเหตุ: บันทึกข้อความต้องยาวไม่เกิน 1 หน้า ไม่ต้องทวนรายละเอียดโครงการ ใส่ sections เฉพาะตารางที่จำเป็น
  "signatures": [ { "label": "", "name": "string", "position": "string" } ]
}""",
    "sheet": """{
  "event_date_text": "string",
  "sheets": [ { "name": "ชื่อชีตสั้นภาษาอังกฤษ", "title": "string", "columns": ["string"], "rows": [["string"]] } ],
  "signatures": [ { "label": "string", "name": "string", "position": "string" } ]
}""",
}


def _public_facts(facts: dict) -> dict:
    return {k: v for k, v in facts.items() if not k.startswith("_")}


def items_for(doc: dict, facts: dict) -> list:
    if not doc.get("per_item"):
        return []
    v = facts.get(doc["per_item"])
    return v if isinstance(v, list) else []


def _slug(text: str) -> str:
    # ฀-๿ keeps Thai vowels/tone marks, which \w alone drops
    return re.sub(r"[^\w฀-๿\-.]+", "_", str(text)).strip("_.")[:40].rstrip("_.")


VERSION_RE = re.compile(r"^\d+(\.\d+){0,3}$")


def _next_version(pid: int, doc_key: str, item_index, cfg: dict) -> str:
    last = db.row(
        "SELECT version FROM documents WHERE project_id=? AND doc_key=? AND item_index IS ? ORDER BY id DESC LIMIT 1",
        (pid, doc_key, item_index),
    )
    if not last or not VERSION_RE.match(last["version"]):
        return cfg.get("version_first") or "1.0"
    parts = [int(x) for x in last["version"].split(".")]
    if cfg.get("version_scheme") == "major":
        return f"{parts[0] + 1}.0"
    if len(parts) == 1:
        parts.append(0)
    parts[-1] += 1
    return ".".join(map(str, parts))


def _apply_pattern(pattern: str, tokens: dict) -> str:
    out = pattern
    for k, v in tokens.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _clean_filename(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name).strip().strip(".")
    return name[:180]


def _parse_signer(label: str, value) -> dict:
    """'นภพล (DEV)' -> {label, name: 'นภพล', position: 'DEV'}"""
    if isinstance(value, dict):
        return {"label": label, "name": value.get("name", ""), "position": value.get("position", "")}
    m = re.match(r"^\s*(.*?)\s*(?:\((.*)\))?\s*$", str(value))
    return {"label": label, "name": m.group(1) if m else str(value), "position": (m.group(2) or "") if m else ""}


def default_signatures(doc: dict, facts: dict) -> list[dict]:
    sig = (facts.get("signatories") or {}).get(doc["code"]) or {}
    return [_parse_signer(label, value) for label, value in sig.items()]


def plan(pid: int, doc_key: str, item_index: int | None = None) -> dict:
    """Suggested filename / version / doc number / signers for the next generation."""
    project = db.get_project(pid)
    doc = DOC_BY_KEY[doc_key]
    cfg = settings.load_config()
    facts = project["facts"]

    item = None
    if doc.get("per_item"):
        items = items_for(doc, facts)
        if item_index is None or not (0 <= item_index < len(items)):
            raise ValueError(f"ต้องเลือกรายการใน '{doc['per_item']}' (มี {len(items)} รายการ)")
        item = items[item_index]

    item_part = f"_{item_index + 1:02d}" if item is not None else ""
    if isinstance(item, dict):
        label = item.get("phase") or item.get("type") or item.get("id") or ""
        if label:
            item_part += f"_{_slug(label)}"
    version = _next_version(pid, doc_key, item_index, cfg)
    today = date.today()
    tokens = {
        "company": cfg["company_short"], "project": project["code"], "doc": doc["code"], "item": item_part,
        "version": version, "date": today.strftime(cfg.get("file_date_format") or "%d-%b-%y"), "stage": doc["stage"],
    }
    ext = "xlsx" if doc["kind"] == "sheet" else "docx"
    return {
        "doc_key": doc_key, "item_index": item_index, "item": item, "ext": ext, "version": version,
        "filename": _clean_filename(_apply_pattern(cfg["filename_pattern"], tokens)) + "." + ext,
        "doc_no": _clean_filename(_apply_pattern(cfg["doc_no_pattern"], tokens)),
        "prepared_date": today.isoformat(),
        "signatures": default_signatures(doc, facts),
    }


def generate(pid: int, doc_key: str, item_index: int | None = None, opts: dict | None = None) -> dict:
    """opts (all optional): filename, version, doc_no, prepared_date (YYYY-MM-DD, not in the past),
    signatures [{label,name,position}], instructions (extra guidance for the AI)."""
    opts = opts or {}
    project = db.get_project(pid)
    doc = DOC_BY_KEY[doc_key]
    cfg = settings.load_config()
    facts = project["facts"]
    p = plan(pid, doc_key, item_index)
    item = p["item"]

    version = (opts.get("version") or p["version"]).strip()
    if not VERSION_RE.match(version):
        raise ValueError("รูปแบบฉบับที่ต้องเป็นตัวเลข เช่น 1.0 หรือ 2.1")
    filename = _clean_filename(opts.get("filename") or p["filename"])
    if not filename.lower().endswith("." + p["ext"]):
        filename = filename.rsplit(".", 1)[0] if filename.lower().endswith((".docx", ".xlsx")) else filename
        filename += "." + p["ext"]
    doc_no = _clean_filename(opts.get("doc_no") or p["doc_no"])
    prepared = opts.get("prepared_date") or p["prepared_date"]
    try:
        prepared_d = date.fromisoformat(prepared)
    except ValueError:
        raise ValueError("วันที่จัดทำต้องอยู่ในรูปแบบ YYYY-MM-DD")
    if prepared_d < date.today():
        # the prepared date is when the file is produced/signed; never earlier (no backdating)
        raise ValueError("วันที่จัดทำย้อนหลังไม่ได้ ใช้วันนี้หรือวันที่จะลงนามจริง")
    signatures = [s for s in (opts.get("signatures") or []) if isinstance(s, dict) and (s.get("label") or s.get("name"))]

    stage = STAGE_BY_KEY[doc["stage"]]
    prompt = f"""จัดทำเอกสาร: {doc['name_th']} ({doc['name']}) — ISO 29110 ขั้น {stage['iso']}
ประเภทเอกสาร: {doc['kind']}
โครงสร้างที่ต้องมี:
{chr(10).join('- ' + o for o in doc['outline'])}

ข้อมูลบริษัท: {cfg['company_name']} ({cfg['department']})
โครงการ: {project['name']} รหัส {project['code']} ลูกค้า {project['customer']}
สรุปโครงการ: {project['summary']}

ข้อเท็จจริงทั้งหมดของโครงการ (JSON):
{json.dumps(_public_facts(facts), ensure_ascii=False, indent=1)}
"""
    if item is not None:
        prompt += f"""
เอกสารฉบับนี้สำหรับรายการที่ {item_index + 1} ของ '{doc['per_item']}' เท่านั้น:
{json.dumps(item, ensure_ascii=False, indent=1)}
"""
    # list already-generated documents so cross references (code/version/date) are real
    existing = db.rows(
        "SELECT doc_key, filename, version, created_at FROM documents WHERE project_id=? "
        "AND id IN (SELECT MAX(id) FROM documents WHERE project_id=? GROUP BY doc_key, item_index)",
        (pid, pid),
    )
    if existing:
        prompt += "\nเอกสารที่จัดทำแล้วในระบบ (ใช้อ้างอิงรหัส/ฉบับ/วันที่ได้):\n" + "\n".join(
            f"- {DOC_BY_KEY[e['doc_key']]['name_th']}: รหัส {e['filename'].rsplit('_v', 1)[0]} "
            f"ฉบับ {e['version']} จัดทำวันที่ {thai_date(e['created_at'][:10])}"
            for e in existing if e["doc_key"] in DOC_BY_KEY)
    if signatures:
        prompt += "\nผู้ลงนามของเอกสารฉบับนี้ (ใช้ตามนี้เท่านั้น):\n" + "\n".join(
            f"- {s.get('label', '')}: {s.get('name', '')} {s.get('position', '')}".rstrip() for s in signatures)
    if (opts.get("instructions") or "").strip():
        prompt += ("\nคำสั่งเพิ่มเติมจากผู้ใช้ (ทำตามได้เท่าที่ไม่ขัดกับกติกาข้างต้น โดยเฉพาะห้ามแต่งข้อเท็จจริง):\n"
                   + opts["instructions"].strip())
    prompt += f"\nตอบเป็น JSON ตามโครงสร้าง:\n{SCHEMAS[doc['kind']]}"

    out_dir = settings.STORAGE_DIR / _slug(project["code"]) / doc["stage"]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    if path.exists():
        raise ValueError(f"มีไฟล์ชื่อ {filename} อยู่แล้ว เปลี่ยนชื่อไฟล์หรือฉบับที่")

    # low temperature: documents must be stable between regenerations
    content = llm.generate_json(SYSTEM, prompt, temperature=float(cfg.get("gen_temperature", 0.1)))
    if signatures:
        content["signatures"] = signatures  # the user's list wins over whatever the model wrote

    meta = {
        "company": cfg["company_name"],
        "department": cfg["department"],
        "title_th": doc["name_th"],
        "title_en": doc["name"],
        "project_name": project["name"],
        "project_code": project["code"],
        "customer": project["customer"],
        "doc_no": doc_no,
        "version": version,
        "prepared_date": prepared_d.isoformat(),
        "prepared_by": "",
        "cover": bool(cfg.get("cover_page", True)),
    }

    render_docx.configure(cfg.get("font_name"), cfg.get("font_size"))
    render_xlsx.configure(cfg.get("font_name"))
    digits = bool(cfg.get("thai_digits"))
    if doc["kind"] == "sheet":
        render_workbook(path, meta, content)
    elif doc["kind"] == "memo":
        render_memo(path, meta, content, digits)
    elif doc["kind"] == "form":
        render_form(path, meta, content, digits)
    else:
        render_report(path, meta, content, digits)

    # keep the raw AI output next to the DB for troubleshooting layout issues
    raw_dir = settings.DATA_DIR / "content"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / f"{path.stem}.json").write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")

    placeholders = json.dumps(content, ensure_ascii=False).count(PLACEHOLDER)
    rel = path.relative_to(settings.STORAGE_DIR).as_posix()
    doc_id = db.execute(
        "INSERT INTO documents(project_id, doc_key, item_index, filename, rel_path, version, placeholders) "
        "VALUES (?,?,?,?,?,?,?)",
        (pid, doc_key, item_index, filename, rel, version, placeholders),
    )
    # a generated file moves the evidence slot from 'missing' to 'draft'
    db.execute(
        "INSERT INTO evidence(project_id, doc_key, status) VALUES (?,?, 'draft') "
        "ON CONFLICT(project_id, doc_key) DO UPDATE SET status=CASE WHEN status='missing' THEN 'draft' ELSE status END, "
        "updated_at=datetime('now','localtime')",
        (pid, doc_key),
    )
    return {"id": doc_id, "filename": filename, "version": version, "placeholders": placeholders, "path": rel}
