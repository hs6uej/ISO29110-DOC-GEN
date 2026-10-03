"""ISO/IEC 29110 Basic Profile catalog.

Defines the interview stages (what to ask) and the work products (what to generate).
Mirrors the company's ISO29110 Doc Mapping / Evidence List so every new project
starts with the full checklist.
"""

# ── Interview stages ─────────────────────────────────────────────────────────
# Each topic is a fact key the interviewer must fill. type "list" topics hold a
# list of objects; `item` describes the fields of each object.

STAGES = [
    {
        "key": "s1_planning",
        "title": "1. เริ่มโครงการและขอบเขตงาน",
        "iso": "PM.1 Project Planning",
        "topics": [
            {"key": "project_name", "desc": "ชื่อโครงการทางการ (ไทย/อังกฤษ)"},
            {"key": "contract", "desc": "เลขที่สัญญา / ใบเสนอราคา / PO และวันที่ลงนาม"},
            {"key": "customer", "desc": "ชื่อองค์กรลูกค้า หน่วยงานที่ใช้งาน"},
            {"key": "customer_contacts", "type": "list", "desc": "ผู้ติดต่อฝั่งลูกค้า",
             "item": "name, position, role (เช่น ผู้อนุมัติ/ผู้ประสานงาน/ผู้ทดสอบ UAT), contact"},
            {"key": "period", "desc": "วันเริ่ม-วันสิ้นสุดตามสัญญา ระยะเวลา และสถานะปัจจุบันของงาน"},
            {"key": "background", "desc": "ที่มา ปัญหาของระบบเดิม และเหตุผลที่ทำโครงการ"},
            {"key": "objectives", "type": "list", "desc": "วัตถุประสงค์ของโครงการ"},
            {"key": "scope_in", "type": "list", "desc": "ขอบเขตงานที่อยู่ในโครงการ"},
            {"key": "scope_out", "type": "list", "desc": "สิ่งที่อยู่นอกขอบเขต"},
            {"key": "deliverables", "type": "list", "desc": "สิ่งส่งมอบ",
             "item": "name, description, due_date"},
            {"key": "success_criteria", "type": "list", "desc": "เกณฑ์ความสำเร็จที่วัดผลได้ (ตัวเลข)"},
            {"key": "team", "type": "list", "desc": "ทีมงานฝั่งบริษัท",
             "item": "name, role (Sale/PM/SA/DEV/Tester/CM), responsibility, email"},
            {"key": "pm_assignment", "desc": "ผู้แต่งตั้ง PM วันที่แต่งตั้ง และวิธีแต่งตั้ง (อีเมล/บันทึก/ประชุม)"},
            {"key": "estimation", "desc": "ประมาณการ man-day/effort ต่อเฟส ต้นทุน งบประมาณ และสมมติฐานการประเมิน"},
            {"key": "infrastructure", "desc": "สินค้า บริการ และโครงสร้างพื้นฐานที่ใช้ (server, cloud, license, LLM ฯลฯ) และผู้จัดหา"},
        ],
    },
    {
        "key": "s2_plan",
        "title": "2. แผนโครงการและ Kick-off",
        "iso": "PM.1 Project Plan",
        "topics": [
            {"key": "wbs", "type": "list", "desc": "แผนงาน/WBS",
             "item": "phase, task, owner, start, end, effort_md, output"},
            {"key": "milestones", "type": "list", "desc": "Milestone สำคัญ", "item": "name, date, deliverable"},
            {"key": "risks", "type": "list", "desc": "ความเสี่ยง",
             "item": "id, description, probability, impact, mitigation, owner, status"},
            {"key": "environment", "desc": "สภาพแวดล้อมการทำงาน: เครื่องมือพัฒนา ภาษา ระบบ dev/test/prod"},
            {"key": "repository", "desc": "ที่เก็บเอกสารและซอร์สโค้ด (path/URL) วิธีและความถี่การสำรองข้อมูล"},
            {"key": "config_items", "type": "list", "desc": "รายการ Configuration Item / Baseline",
             "item": "name, type (document/software), baseline_point"},
            {"key": "communication", "desc": "รูปแบบการสื่อสาร ความถี่การประชุมภายในและกับลูกค้า ช่องทาง"},
            {"key": "kickoff", "desc": "การประชุม Kick-off: วันที่ สถานที่/ช่องทาง ผู้เข้าร่วม หัวข้อ ข้อตกลง และลูกค้ายอมรับแผนอย่างไร"},
            {"key": "plan_review", "desc": "การทบทวนแผนโดยทีม (Ver Plan): วันที่ ผู้ทบทวน ข้อบกพร่องที่พบและการแก้ไข"},
        ],
    },
    {
        "key": "s3_requirements",
        "title": "3. ความต้องการของระบบ (Requirements)",
        "iso": "SI.2 Software Requirements Analysis",
        "topics": [
            {"key": "current_system", "desc": "ระบบเดิม/AS-IS และขั้นตอนการทำงานปัจจุบัน"},
            {"key": "functional_requirements", "type": "list", "desc": "ความต้องการเชิงฟังก์ชัน",
             "item": "id (FR-01...), title, description, priority, source"},
            {"key": "nonfunctional_requirements", "type": "list", "desc": "ความต้องการที่ไม่ใช่ฟังก์ชัน (performance, security, PDPA, availability)",
             "item": "id (NFR-01...), category, description, measure"},
            {"key": "interfaces", "type": "list", "desc": "ระบบที่เชื่อมต่อภายใน/ภายนอก", "item": "name, direction, protocol, description"},
            {"key": "constraints_assumptions", "desc": "ข้อจำกัดและสมมติฐาน"},
            {"key": "srs_verification", "desc": "การทบทวน SRS ภายในทีม: วันที่ ผู้ทบทวน ข้อบกพร่องที่พบ การแก้ไข"},
            {"key": "srs_validation", "desc": "การยืนยัน SRS กับลูกค้า: วันที่ วิธี (ประชุม/อีเมล/ลงนาม) ผู้ยืนยัน ข้อแก้ไข"},
        ],
    },
    {
        "key": "s4_design",
        "title": "4. การออกแบบ (Design)",
        "iso": "SI.3 Software Architectural and Detailed Design",
        "topics": [
            {"key": "architecture", "desc": "สถาปัตยกรรมระบบ องค์ประกอบหลัก และลำดับการทำงาน (flow)"},
            {"key": "components", "type": "list", "desc": "องค์ประกอบ/โมดูลซอฟต์แวร์",
             "item": "id (C-01...), name, responsibility, technology, related_requirements"},
            {"key": "api_specs", "type": "list", "desc": "API / interface",
             "item": "name, method, endpoint, request, response, description"},
            {"key": "data_design", "desc": "ข้อมูล/การตั้งค่า/ฐานข้อมูลที่ใช้"},
            {"key": "design_decisions", "type": "list", "desc": "การตัดสินใจเชิงออกแบบและเหตุผล"},
            {"key": "design_verification", "desc": "การทบทวนการออกแบบ: วันที่ ผู้ทบทวน ข้อบกพร่อง การแก้ไข"},
            {"key": "design_validation", "desc": "การยืนยันการออกแบบกับลูกค้า (ถ้ามี): วันที่ วิธี ผู้ยืนยัน"},
        ],
    },
    {
        "key": "s5_construction",
        "title": "5. การพัฒนา (Construction)",
        "iso": "SI.4 Software Construction",
        "topics": [
            {"key": "source_repository", "desc": "ที่เก็บซอร์สโค้ด (URL), branch strategy, การตั้งเวอร์ชัน"},
            {"key": "releases", "type": "list", "desc": "เวอร์ชัน/release ที่ออก", "item": "version, date, changes"},
            {"key": "unit_test", "desc": "วิธีการทดสอบระดับหน่วย/โมดูลและผลลัพธ์ (หรือเหตุผลที่ N/A)"},
            {"key": "component_trace", "type": "list", "desc": "การเชื่อมโยง requirement → component → ไฟล์/โมดูลโค้ด",
             "item": "requirement_id, component_id, source_path"},
        ],
    },
    {
        "key": "s6_testing",
        "title": "6. การทดสอบและ UAT",
        "iso": "SI.5 Software Integration and Tests",
        "topics": [
            {"key": "test_environment", "desc": "สภาพแวดล้อมการทดสอบ ข้อมูลทดสอบ เครื่องมือ"},
            {"key": "test_cases", "type": "list", "desc": "กรณีทดสอบภายใน",
             "item": "id (TC-01...), requirement_id, title, steps, expected_result"},
            {"key": "test_results", "type": "list", "desc": "ผลการทดสอบ",
             "item": "test_case_id, date, tester, result (Pass/Fail), defect_id, remark"},
            {"key": "defects", "type": "list", "desc": "ข้อบกพร่องจากการ Ver/Val/Test",
             "item": "id, source, description, severity, found_date, fixed_date, status"},
            {"key": "uat_plan", "desc": "แผน UAT: วันที่ ผู้ทดสอบฝั่งลูกค้า สถานที่ เกณฑ์ผ่าน"},
            {"key": "uat_cases", "type": "list", "desc": "กรณีทดสอบ UAT",
             "item": "id (UAT-01...), requirement_id, scenario, expected_result"},
            {"key": "uat_result", "desc": "ผล UAT: วันที่ ผลแต่ละกรณี ข้อบกพร่อง ผู้ลงนามรับรอง"},
        ],
    },
    {
        "key": "s7_monitoring",
        "title": "7. การติดตามโครงการ (ประชุม/ความคืบหน้า/CR)",
        "iso": "PM.2 Project Plan Execution / PM.3 Assessment and Control",
        "topics": [
            {"key": "meetings", "type": "list", "desc": "การประชุมทั้งหมดที่เกิดขึ้นจริง",
             "item": "no, date, type (internal/customer), phase, attendees, agenda, discussion, decisions, action_items, evidence"},
            {"key": "progress_reports", "type": "list", "desc": "รายงานความคืบหน้าแต่ละช่วง/เฟส",
             "item": "no, date, phase, planned_percent, actual_percent, completed_tasks, next_tasks, issues, risk_updates"},
            {"key": "change_requests", "type": "list", "desc": "คำขอเปลี่ยนแปลง",
             "item": "id, date, requester, description, reason, impact_cost, impact_schedule, impact_technical, decision, approved_by, approved_date"},
            {"key": "corrections", "type": "list", "desc": "ปัญหา/การแก้ไข (Correction Register)",
             "item": "id, date, problem, cause, corrective_action, owner, due_date, closed_date, status"},
        ],
    },
    {
        "key": "s8_delivery",
        "title": "8. ส่งมอบและปิดโครงการ",
        "iso": "SI.6 Product Delivery / PM.4 Project Closure",
        "topics": [
            {"key": "deployment", "desc": "การติดตั้งขึ้นระบบจริง: วันที่ สภาพแวดล้อม ขั้นตอน ผู้ดำเนินการ"},
            {"key": "operation_guide", "desc": "ขั้นตอนการติดตั้ง/ดูแลระบบ การเริ่ม/หยุดบริการ การตรวจสอบ log การแก้ปัญหาเบื้องต้น"},
            {"key": "user_guide", "desc": "วิธีใช้งานสำหรับผู้ใช้ (หน้าจอ/ฟังก์ชันที่ผู้ใช้ต้องรู้) และการอบรม"},
            {"key": "maintenance", "desc": "ข้อมูลสำหรับการบำรุงรักษา: โครงสร้างโค้ด การ build/deploy ใหม่ การ backup/restore ผู้ติดต่อ"},
            {"key": "acceptance", "desc": "การตรวจรับงาน: วันที่ ผู้ตรวจรับ รายการที่ส่งมอบ เงื่อนไข"},
            {"key": "closure", "desc": "การปิดโครงการ: วันที่ สรุปผลเทียบแผน บทเรียนที่ได้ การสำรองข้อมูลโครงการ"},
        ],
    },
]

STAGE_BY_KEY = {s["key"]: s for s in STAGES}

# ── Work products ────────────────────────────────────────────────────────────
# kind: "report" (docx with cover + sections), "memo" (บันทึกข้อความ),
#       "form" (docx sign-off form), "sheet" (xlsx)
# per_item: generate one file per element of that fact list.
# deliver: Baseline / NonBaseline (as in Doc Mapping)
# val: needs customer validation evidence

DOCUMENTS = [
    # Stage 1
    {"key": "sow", "seq": "1", "name": "Statement of Work", "name_th": "ขอบเขตของงาน (SOW)",
     "code": "SOW", "kind": "report", "stage": "s1_planning", "owner": "Sale/PM", "deliver": "Baseline", "val": True,
     "outline": ["ที่มาและความสำคัญ", "วัตถุประสงค์", "ขอบเขตของงาน", "นอกขอบเขตงาน", "สิ่งส่งมอบ",
                 "ระยะเวลาดำเนินงาน", "เกณฑ์การตรวจรับ", "ผู้เกี่ยวข้อง"]},
    {"key": "estimation", "seq": "1.1", "name": "Project Estimation", "name_th": "ประมาณการโครงการ",
     "code": "Estimation", "kind": "sheet", "stage": "s1_planning", "owner": "Sale", "deliver": "NonBaseline",
     "outline": ["Sheet 'Effort' : phase, task, role, man-day", "Sheet 'Cost' : item, qty, unit cost, total",
                 "Sheet 'Assumptions' : no, assumption"]},
    {"key": "pm_assign", "seq": "2", "name": "Project Manager Assignment", "name_th": "บันทึกแต่งตั้งผู้จัดการโครงการ",
     "code": "AssignPM", "kind": "memo", "stage": "s1_planning", "owner": "Management", "deliver": "NonBaseline",
     "outline": ["แต่งตั้งผู้จัดการโครงการและทีมงาน พร้อมหน้าที่ความรับผิดชอบ"]},
    # Stage 2
    {"key": "project_plan", "seq": "3", "name": "Project Plan", "name_th": "แผนโครงการ",
     "code": "PJM", "kind": "sheet", "stage": "s2_plan", "owner": "PM", "deliver": "Baseline", "val": True,
     "outline": ["Sheet 'Schedule' : WBS phase, task, owner, start, end, effort", "Sheet 'Team' : name, role, responsibility",
                 "Sheet 'Risks' : id, description, probability, impact, mitigation, owner, status",
                 "Sheet 'Environment' : item, detail", "Sheet 'ConfigItems' : CI, type, baseline point, location",
                 "Sheet 'Milestones' : milestone, date, deliverable", "Sheet 'Revision' : version, date, description, by"]},
    {"key": "kickoff_mom", "seq": "3.1", "name": "Kick-off Meeting Record", "name_th": "บันทึกการประชุมเริ่มโครงการ",
     "code": "MOM_Kickoff", "kind": "report", "stage": "s2_plan", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["ข้อมูลการประชุม (วันที่ เวลา สถานที่)", "ผู้เข้าร่วมประชุม", "วาระการประชุม", "สรุปการนำเสนอแผนโครงการ",
                 "ข้อตกลง/มติที่ประชุม", "รายการติดตาม (Action Items)"]},
    {"key": "ver_plan", "seq": "3.2", "name": "Verification Result - Project Plan", "name_th": "ผลการทวนสอบแผนโครงการ",
     "code": "VerPlan", "kind": "sheet", "stage": "s2_plan", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["Sheet 'Checklist' : no, check item, result (Yes/No), comment",
                 "Sheet 'Defects' : no, defect, action, status, closed date"]},
    # Stage 3
    {"key": "srs", "seq": "4", "name": "Requirements Specification", "name_th": "ข้อกำหนดความต้องการซอฟต์แวร์ (SRS)",
     "code": "SRS", "kind": "report", "stage": "s3_requirements", "owner": "SA", "deliver": "Baseline", "val": True,
     "outline": ["บทนำ (วัตถุประสงค์ ขอบเขต คำนิยาม)", "ภาพรวมระบบเดิมและระบบใหม่", "ความต้องการเชิงฟังก์ชัน (ตาราง FR)",
                 "ความต้องการที่ไม่ใช่ฟังก์ชัน (ตาราง NFR)", "การเชื่อมต่อระบบ", "ข้อจำกัดและสมมติฐาน"]},
    {"key": "ver_srs", "seq": "4.1", "name": "Verification Result - Requirements", "name_th": "ผลการทวนสอบ SRS",
     "code": "Ver_SRS", "kind": "sheet", "stage": "s3_requirements", "owner": "CM", "deliver": "NonBaseline",
     "outline": ["Sheet 'Checklist' : no, check item, result, comment", "Sheet 'Defects' : no, defect, action, status"]},
    {"key": "val_srs", "seq": "4.2", "name": "Validation / Sign-off - Requirements", "name_th": "แบบยืนยันความต้องการ (SRS Sign-off)",
     "code": "SRS_Signoff", "kind": "form", "stage": "s3_requirements", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["รายการเอกสารที่ขอยืนยัน", "ผลการยืนยัน/ข้อแก้ไข", "ช่องลงนามลูกค้าและผู้จัดการโครงการ"]},
    # Stage 4
    {"key": "design", "seq": "5", "name": "Software Design", "name_th": "เอกสารการออกแบบซอฟต์แวร์ (Architecture & Detailed Design)",
     "code": "FDD", "kind": "report", "stage": "s4_design", "owner": "SA", "deliver": "Baseline", "val": True,
     "outline": ["บทนำ", "สถาปัตยกรรมระบบ", "ลำดับการทำงาน (Flow)", "องค์ประกอบซอฟต์แวร์ (ตาราง)",
                 "การออกแบบการเชื่อมต่อ/API", "การออกแบบข้อมูลและการตั้งค่า", "การตัดสินใจเชิงออกแบบ"]},
    {"key": "api_spec", "seq": "5.1", "name": "Interface Specification", "name_th": "ข้อกำหนดการเชื่อมต่อ (API Spec)",
     "code": "API", "kind": "sheet", "stage": "s4_design", "owner": "SA", "deliver": "Baseline",
     "outline": ["Sheet 'API' : name, method, endpoint, request, response, description"]},
    {"key": "ver_design", "seq": "5.2", "name": "Verification Result - Design", "name_th": "ผลการทวนสอบการออกแบบ",
     "code": "Ver_FDD", "kind": "sheet", "stage": "s4_design", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["Sheet 'Checklist' : no, check item, result, comment", "Sheet 'Defects' : no, defect, action, status"]},
    # Stage 6 (testing) – before RTM
    {"key": "tctp", "seq": "6", "name": "Test Cases and Test Procedures", "name_th": "กรณีทดสอบและขั้นตอนการทดสอบ",
     "code": "TPTC", "kind": "report", "stage": "s6_testing", "owner": "Tester", "deliver": "Baseline",
     "outline": ["บทนำ", "สภาพแวดล้อมการทดสอบ", "ขั้นตอนการทดสอบ", "กรณีทดสอบ (ตาราง TC)"]},
    {"key": "ver_tctp", "seq": "6.1", "name": "Verification Result - Test Cases", "name_th": "ผลการทวนสอบกรณีทดสอบ",
     "code": "Ver_TPTC", "kind": "sheet", "stage": "s6_testing", "owner": "SA", "deliver": "NonBaseline",
     "outline": ["Sheet 'Checklist' : no, check item, result, comment", "Sheet 'Defects' : no, defect, action, status"]},
    {"key": "test_report", "seq": "6.2", "name": "Test Report", "name_th": "รายงานผลการทดสอบ",
     "code": "TestReport", "kind": "report", "stage": "s6_testing", "owner": "Tester", "deliver": "NonBaseline",
     "outline": ["สรุปผลการทดสอบ", "ผลการทดสอบรายกรณี (ตาราง)", "ข้อบกพร่องที่พบและการแก้ไข (ตาราง)", "ข้อสรุป"]},
    {"key": "uatp", "seq": "6.3", "name": "Acceptance Test Cases & Procedures", "name_th": "แผนและกรณีทดสอบการยอมรับ (UAT Plan)",
     "code": "UATP", "kind": "report", "stage": "s6_testing", "owner": "SA", "deliver": "Baseline",
     "outline": ["วัตถุประสงค์", "ผู้ทดสอบและกำหนดการ", "เกณฑ์การยอมรับ", "กรณีทดสอบ UAT (ตาราง)"]},
    {"key": "uat_report", "seq": "6.4", "name": "UAT Report & Sign-off", "name_th": "รายงานผลการทดสอบการยอมรับและการลงนาม",
     "code": "UATReport_Signoff", "kind": "form", "stage": "s6_testing", "owner": "Tester", "deliver": "NonBaseline", "val": True,
     "outline": ["ข้อมูลการทดสอบ", "ผลการทดสอบรายกรณี (ตาราง)", "ข้อบกพร่องคงค้าง", "ผลการรับรอง", "ช่องลงนาม"]},
    {"key": "rtm", "seq": "7", "name": "Traceability Record", "name_th": "ตารางการตรวจสอบย้อนกลับ (RTM)",
     "code": "RTM", "kind": "sheet", "stage": "s6_testing", "owner": "SA/DEV", "deliver": "NonBaseline",
     "outline": ["Sheet 'RTM' : SOW item, requirement id, requirement, design component, source code, test case, UAT case, status"]},
    # Stage 7 (monitoring)
    {"key": "meeting_record", "seq": "8", "name": "Meeting Record", "name_th": "บันทึกการประชุม",
     "code": "MOM", "kind": "report", "stage": "s7_monitoring", "owner": "PM", "deliver": "NonBaseline", "per_item": "meetings",
     "outline": ["ข้อมูลการประชุม", "ผู้เข้าร่วม", "วาระ", "สาระการประชุม", "มติ/ข้อตกลง", "Action Items (ตาราง)"]},
    {"key": "progress_report", "seq": "9", "name": "Progress Status Record", "name_th": "รายงานความคืบหน้าโครงการ",
     "code": "ProgressReport", "kind": "sheet", "stage": "s7_monitoring", "owner": "PM", "deliver": "NonBaseline", "per_item": "progress_reports",
     "outline": ["Sheet 'Progress' : item, planned, actual, status, remark", "Sheet 'Tasks' : task, owner, status, due",
                 "Sheet 'Issues&Risks' : id, description, action, owner, status"]},
    {"key": "change_request", "seq": "10", "name": "Change Request", "name_th": "แบบคำขอเปลี่ยนแปลง",
     "code": "CR", "kind": "form", "stage": "s7_monitoring", "owner": "PM", "deliver": "NonBaseline", "per_item": "change_requests",
     "outline": ["รายละเอียดคำขอ", "เหตุผล", "การวิเคราะห์ผลกระทบ (ค่าใช้จ่าย ระยะเวลา เทคนิค)", "ผลการพิจารณา", "ช่องลงนามอนุมัติ"]},
    {"key": "correction_register", "seq": "11", "name": "Correction Register", "name_th": "ทะเบียนการแก้ไขปัญหา",
     "code": "CorrectionRegister", "kind": "sheet", "stage": "s7_monitoring", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["Sheet 'Corrections' : id, date, problem, cause, corrective action, owner, due, closed, status"]},
    # Stage 8
    {"key": "operation_guide", "seq": "12", "name": "Product Operation Guide", "name_th": "คู่มือการติดตั้งและดูแลระบบ",
     "code": "Installation_Manual", "kind": "report", "stage": "s8_delivery", "owner": "SA", "deliver": "Baseline",
     "outline": ["ภาพรวมระบบ", "ความต้องการฮาร์ดแวร์/ซอฟต์แวร์", "ขั้นตอนการติดตั้ง", "การเริ่ม/หยุดบริการ",
                 "การตรวจสอบสถานะและ log", "การแก้ไขปัญหาเบื้องต้น"]},
    {"key": "user_doc", "seq": "13", "name": "Software User Documentation", "name_th": "คู่มือผู้ใช้งาน",
     "code": "UM", "kind": "report", "stage": "s8_delivery", "owner": "SA", "deliver": "Baseline",
     "outline": ["บทนำ", "การเข้าใช้งาน", "ฟังก์ชันการใช้งาน", "คำถามที่พบบ่อย"]},
    {"key": "maintenance_doc", "seq": "14", "name": "Maintenance Documentation", "name_th": "เอกสารการบำรุงรักษา",
     "code": "Maintenance", "kind": "report", "stage": "s8_delivery", "owner": "DEV", "deliver": "Baseline",
     "outline": ["โครงสร้างซอฟต์แวร์และซอร์สโค้ด", "การ build และ deploy", "การสำรองและกู้คืนข้อมูล", "ผู้ติดต่อ"]},
    {"key": "acceptance", "seq": "15", "name": "Acceptance Record", "name_th": "บันทึกการตรวจรับงาน",
     "code": "Acceptance_Signoff", "kind": "form", "stage": "s8_delivery", "owner": "PM", "deliver": "Baseline", "val": True,
     "outline": ["รายละเอียดโครงการ", "รายการสิ่งส่งมอบ (ตาราง)", "ผลการตรวจรับ", "ช่องลงนามผู้ตรวจรับและผู้ส่งมอบ"]},
    {"key": "closure", "seq": "16", "name": "Project Closure Report", "name_th": "รายงานปิดโครงการ",
     "code": "ProgressReport_Closed", "kind": "report", "stage": "s8_delivery", "owner": "PM", "deliver": "NonBaseline",
     "outline": ["สรุปโครงการ", "ผลการดำเนินงานเทียบแผน (ตาราง)", "สิ่งส่งมอบ", "ปัญหาและบทเรียนที่ได้รับ", "การสำรองข้อมูลโครงการ"]},
]

DOC_BY_KEY = {d["key"]: d for d in DOCUMENTS}

EVIDENCE_STATUSES = ["missing", "draft", "verified", "validated", "baseline"]
EVIDENCE_STATUS_TH = {
    "missing": "ยังไม่มี",
    "draft": "ร่าง",
    "verified": "ทวนสอบแล้ว (Ver)",
    "validated": "ลูกค้ายืนยันแล้ว (Val)",
    "baseline": "Baseline แล้ว",
}
