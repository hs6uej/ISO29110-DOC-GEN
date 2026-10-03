"""Step-by-step interview: AI asks, user answers, AI records facts and asks next."""
import json

from . import db, llm
from .catalog import STAGE_BY_KEY, STAGES

SYSTEM = """คุณคือที่ปรึกษาด้านเอกสาร ISO/IEC 29110 (Basic Profile) ที่กำลังสัมภาษณ์ผู้จัดการโครงการ
เพื่อเก็บข้อเท็จจริงของโครงการซอฟต์แวร์ที่เกิดขึ้นจริง แล้วนำไปจัดทำเอกสารตามมาตรฐาน

กติกา:
1. บันทึกเฉพาะข้อเท็จจริงที่ผู้ใช้บอกเท่านั้น ห้ามแต่งเติม ห้ามเดาชื่อคน วันที่ ตัวเลข
   ห้ามอนุมานบทบาท/อำนาจ (เช่น อย่าสรุปเองว่าใครเป็น "ผู้อนุมัติ") บันทึกชื่อ-นามสกุลเต็มตามที่ให้มา
1.1 ถามแค่ระดับที่พอใช้จัดทำเอกสาร ไม่ต้องเจาะรายละเอียดปลีกย่อย ถ้าผู้ใช้ตอบสั้นแต่ใช้ได้ ให้ถือว่า complete
2. ถามทีละขั้น ไม่เกิน 4 คำถามต่อรอบ แต่ละคำถามสั้น 1 บรรทัด ภาษาพูดง่าย ๆ ไม่ใช้ศัพท์ทางการ
   ให้ตัวอย่างคำตอบสั้น ๆ ในวงเล็บได้ เรียงจากเรื่องสำคัญที่สุดก่อน
2.1 ถ้าผู้ใช้ตอบว่า "ไม่รู้" "ไม่มี" หรือข้ามคำถาม ให้ตั้ง coverage ของหัวข้อนั้นเป็น "unknown"
    บันทึกเป็น gaps แล้ว**ห้ามถามเรื่องนั้นซ้ำ** ยกเว้นผู้ใช้กลับมาให้ข้อมูลเอง
    ข้อที่ถามไปในรอบก่อนแต่ผู้ใช้ไม่ได้ตอบ ถือว่าผู้ใช้ข้าม: ห้ามถามซ้ำด้วยคำถามเดิมหรือคล้ายเดิม
    ให้ไปถามหัวข้อที่ยังไม่เคยถามแทน ถ้าทุกหัวข้อถูกถามแล้ว ให้ stage_complete = true
    ไม่ต้องขอรายละเอียดเพิ่มในหัวข้อที่ได้คำตอบแล้ว (เช่น ได้ระดับเดือนแล้ว ไม่ต้องขอวันที่)
    ตัวอย่างคำถามที่ดี: "ฝั่งเรามีใครทำบ้าง แต่ละคนทำหน้าที่อะไร (เช่น A เป็น PM, B เขียนโค้ด)"
    ตัวอย่างคำถามที่ไม่ดี: "รบกวนแจ้งรายละเอียดทีมงานโครงการพร้อมบทบาทและความรับผิดชอบของแต่ละท่านด้วยครับ"
3. หากคำตอบกำกวม ขัดแย้งกับข้อมูลเดิม หรือไม่ครบตามรายการหัวข้อ ให้ถามต่อ
4. วันที่ต้องเป็นวันที่เกิดเหตุการณ์จริง ถ้าผู้ใช้ไม่แน่ใจให้บันทึกว่า "ประมาณ" และถามหาหลักฐาน (อีเมล ปฏิทิน แชท)
5. ถ้าสิ่งใดไม่ได้เกิดขึ้นจริง (เช่น ไม่ได้ประชุมทบทวน ลูกค้ายังไม่ได้ลงนาม) ให้บันทึกตามจริงว่า "ยังไม่มี"
   และใส่ใน gaps พร้อมแนะนำวิธีแก้ที่ถูกต้อง (เช่น จัดทบทวนตอนนี้และบันทึกวันที่จริง) ห้ามแนะนำให้สร้างหลักฐานย้อนหลังที่ไม่จริง
6. ผู้ใช้อาจแปะอีเมล แชท หรือบันทึก ให้สกัดข้อเท็จจริงจากข้อความนั้น
7. หัวข้อแบบ list ให้ส่งค่าเป็น list ของ object ทั้งชุดที่อัปเดตแล้ว (รวมรายการเดิม) โดยใช้ชื่อฟิลด์ตามที่กำหนด
8. หัวข้อที่เป็นข้อความ ให้ส่งเป็นข้อความสรุปที่ครบถ้วน (รวมข้อมูลเดิมที่ยังถูกต้อง)

ตอบเป็น JSON เท่านั้น ตามโครงสร้าง:
{
  "facts_update": { "<topic_key>": <ค่า> },
  "coverage": { "<topic_key>": "complete" | "partial" | "missing" | "unknown" },
  "gaps": ["หลักฐาน/สิ่งที่ยังขาดในขั้นนี้ พร้อมวิธีแก้ที่ถูกต้อง"],
  "message": "สรุปสั้นมาก 1 บรรทัดว่ารอบนี้บันทึกอะไร",
  "questions": ["คำถามถัดไป"],
  "stage_complete": true | false
}
coverage ต้องครอบคลุมทุก topic ของขั้นนี้ ถ้า stage_complete เป็น true ให้ questions เป็น [] ได้"""


def _topics_text(stage: dict) -> str:
    lines = []
    for t in stage["topics"]:
        kind = "list" if t.get("type") == "list" else "text"
        extra = f" | ฟิลด์: {t['item']}" if t.get("item") else ""
        lines.append(f"- {t['key']} ({kind}): {t['desc']}{extra}")
    return "\n".join(lines)


def _public_facts(facts: dict) -> dict:
    return {k: v for k, v in facts.items() if not k.startswith("_")}


def history(pid: int, stage_key: str) -> list[dict]:
    return db.rows(
        "SELECT m.role, m.content, m.created_at, u.name AS user_name FROM messages m LEFT JOIN users u ON u.id=m.user_id "
        "WHERE m.project_id=? AND m.stage=? ORDER BY m.id",
        (pid, stage_key),
    )


def turn(pid: int, stage_key: str, answer: str | None) -> dict:
    project = db.get_project(pid)
    stage = STAGE_BY_KEY[stage_key]
    facts = project["facts"]

    convo = history(pid, stage_key)[-14:]
    convo_text = "\n".join(f"[{m['role']}] {m['content']}" for m in convo) or "(ยังไม่มีบทสนทนา เริ่มถามคำถามแรก)"
    cov = facts.get("_coverage", {})
    unknown = [t["key"] for t in stage["topics"] if cov.get(t["key"]) == "unknown"]

    prompt = f"""โครงการ: {project['name']} (รหัส {project['code']})
ลูกค้า: {project['customer']}
สรุปโครงการจากผู้ใช้: {project['summary']}

ขั้นที่กำลังสัมภาษณ์: {stage['title']} ({stage['iso']})
หัวข้อที่ต้องเก็บในขั้นนี้:
{_topics_text(stage)}

ข้อเท็จจริงที่บันทึกแล้วทั้งโครงการ (JSON):
{json.dumps(_public_facts(facts), ensure_ascii=False, indent=1)}

หัวข้อที่ผู้ใช้ตอบแล้วว่าไม่รู้/ไม่มี (ห้ามถามซ้ำ): {', '.join(unknown) or '-'}

บทสนทนาในขั้นนี้:
{convo_text}

คำตอบล่าสุดของผู้ใช้: {answer or '(ยังไม่มี — ให้เริ่มถาม)'}"""

    out = llm.generate_json(SYSTEM, prompt)
    # store the answer only after the AI call succeeded, so a retry doesn't duplicate it
    if answer:
        db.execute("INSERT INTO messages(project_id, stage, role, content) VALUES (?,?,?,?)",
                   (pid, stage_key, "user", answer))

    valid_keys = {t["key"] for t in stage["topics"]}
    for k, v in (out.get("facts_update") or {}).items():
        if k not in valid_keys:
            continue
        if v in (None, "", [], {}):
            # an explicit "none" answer must be kept, otherwise documents show [ต้องระบุ]
            if (out.get("coverage") or {}).get(k) in ("complete", "unknown") and k not in facts:
                facts[k] = "ไม่มี"
            continue
        facts[k] = v
    facts.setdefault("_coverage", {}).update(
        {k: v for k, v in (out.get("coverage") or {}).items() if k in valid_keys}
    )
    facts.setdefault("_gaps", {})[stage_key] = out.get("gaps") or []
    if out.get("stage_complete"):
        facts.setdefault("_completed_stages", [])
        if stage_key not in facts["_completed_stages"]:
            facts["_completed_stages"].append(stage_key)
    db.save_facts(pid, facts)

    questions = out.get("questions") or []
    text = (out.get("message") or "").strip()
    if questions:
        text += ("\n\n" if text else "") + "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))
    if out.get("stage_complete"):
        text += "\n\n✅ ข้อมูลขั้นนี้ครบพอสำหรับจัดทำเอกสารแล้ว"
    db.execute("INSERT INTO messages(project_id, stage, role, content) VALUES (?,?,?,?)",
               (pid, stage_key, "assistant", text or "(ไม่มีข้อความ)"))

    return {"message": text, "gaps": facts["_gaps"][stage_key], "stage_complete": bool(out.get("stage_complete"))}


def stage_progress(facts: dict) -> list[dict]:
    cov = facts.get("_coverage", {})
    done = set(facts.get("_completed_stages", []))
    out = []
    for s in STAGES:
        keys = [t["key"] for t in s["topics"]]
        complete = sum(1 for k in keys if cov.get(k) == "complete")
        out.append({
            "key": s["key"], "title": s["title"], "iso": s["iso"],
            "topics": len(keys), "complete": complete,
            "done": s["key"] in done,
            "gaps": facts.get("_gaps", {}).get(s["key"], []),
        })
    return out
