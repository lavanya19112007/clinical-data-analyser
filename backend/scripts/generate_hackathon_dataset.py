"""
Generate the canonical synthetic hackathon dataset in hackathon-data/
Matches STUDY-042 Phase III Diabetes trial specification:
- 241 subjects
- 12 sites (S01 to S12)
- Exactly 27,125 records
- Cut-aware (cut_available 1..12, corrected_at_cut)
- Full SDTM domains: DM, LB, AE, EX, CM, VS, DS, MH, EG, reference_ranges, cuts, corrections
- Documents and JSON responses
"""

import os
import csv
import json
import random

def generate_hackathon_dataset():
    base_dir = "hackathon-data"
    data_dir = os.path.join(base_dir, "data")
    docs_dir = os.path.join(base_dir, "documents")
    resp_dir = os.path.join(base_dir, "responses")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    os.makedirs(resp_dir, exist_ok=True)

    # 1. README.md
    readme_content = """# STUDY-042 Synthetic Clinical Trial Dataset
Phase III Randomized, Double-Blind, Placebo-Controlled Study of GlycaFix (GF-402) in Subjects with Type 2 Diabetes Mellitus.
- **Protocol ID**: STUDY-042
- **Sites**: 12 investigational sites (S01 through S12)
- **Subjects**: 241 randomized subjects
- **Total Records**: 27,125 records across 12 sequential data cuts
- **Data Domains**: DM, LB, AE, EX, CM, VS, DS, MH, EG, reference_ranges, cuts, corrections
- **Governance**: 21 CFR Part 11 compliant audit trail, human gate escalation protocols.
"""
    with open(os.path.join(base_dir, "README.md"), "w") as f:
        f.write(readme_content)

    # 2. Documents
    docs = {
        "protocol_v1.md": """# STUDY-042 Protocol Version 1.0
## Title: Phase III Evaluation of GF-402 vs Placebo in Type 2 Diabetes
- **Inclusion Criteria**: Adults aged 18-75, HbA1c 7.5% - 10.5%, on stable metformin monotherapy.
- **Exclusion Criteria**: ALT or AST > 1.5x ULN, eGFR < 60 mL/min/1.73m2, history of acute pancreatitis.
- **Safety Stopping Rules (Hy's Law)**: Concurrent ALT or AST > 3x ULN with Total Bilirubin > 2x ULN within 14 days, without initial cholestasis (ALP < 2x ULN).
- **Target Dosing**: 100 mg orally once daily.
- **Visit Schedule**: Screening, Baseline (Day 1), Week 2, Week 4, Week 6, Week 8, Week 10, Week 12, Week 16, Week 20, Week 24, End of Study.
- **Visit Window**: ±3 calendar days from scheduled target day.
""",
        "protocol_v2.md": """# STUDY-042 Protocol Version 2.0 (Amendment)
## Amendment Summary (Effective Cut 4)
- **Clarification of Liver Monitoring**: Mandatory repeat testing within 48 hours for any ALT > 2x ULN.
- **Dose Adjustment Guidance**: Temporary withholding permitted for Grade 2 gastrointestinal events.
- **Expanded Exclusion**: History of severe allergic reaction to SGLT2/GLP-1 agents.
""",
        "protocol_v3.md": """# STUDY-042 Protocol Version 3.0 (Amendment)
## Amendment Summary (Effective Cut 8)
- **Renal Threshold Safety**: eGFR discontinuation threshold adjusted to < 45 mL/min/1.73m2.
- **Long-term Extension**: Optional open-label extension after Week 24.
""",
        "lab-manual.md": """# Central Laboratory Manual v1.0
- **ULN Reference Limits**:
  - ALT: 40 U/L
  - AST: 40 U/L
  - Total Bilirubin: 1.2 mg/dL
  - ALP: 120 U/L
  - Serum Creatinine: 1.3 mg/dL
  - Fasting Glucose: 100 mg/dL
  - HbA1c: 6.5%
- Standard SI to Conventional unit conversions must follow certified conversion factors.
""",
        "lab-manual_v3.md": """# Central Laboratory Manual v3.0
- Updated analytical instrumentation reference standards for photometric bilirubin determination.
""",
        "sap.md": """# Statistical Analysis Plan (SAP)
Primary endpoint: Change from baseline in HbA1c at Week 24.
Safety analysis population: All subjects receiving at least one dose of study medication.
"""
    }
    for fname, content in docs.items():
        with open(os.path.join(docs_dir, fname), "w") as f:
            f.write(content)

    # 3. Responses JSON
    monitor_decisions = [
        {"decision_id": "DEC-001", "cut": 3, "subject_id": "042-S05-003", "type": "SAFETY_ALERT", "status": "ESCALATED", "adjudication": "CONFIRMED_HYS_LAW", "reviewer": "Dr. E. Vance, Medical Monitor"},
        {"decision_id": "DEC-002", "cut": 5, "subject_id": "042-S05-003", "type": "LAB_CORRECTION", "status": "APPROVED", "adjudication": "RETRACTED_TRANSCRIBED_ALT", "reviewer": "Data Management Gate"}
    ]
    with open(os.path.join(resp_dir, "monitor_decisions.json"), "w") as f:
        json.dump(monitor_decisions, f, indent=2)

    site_replies = [
        {"site_id": "S01", "query_id": "QRY-S01-01", "status": "CLOSED", "reply": "Subject 042-S01-001 dosing confirmed at planned 100 mg. No deviation."},
        {"site_id": "S05", "query_id": "QRY-S05-04", "status": "RESOLVED", "reply": "Re-draw confirmed ALT elevation at Week 4. Subject placed on safety follow-up."}
    ]
    with open(os.path.join(resp_dir, "site_replies.json"), "w") as f:
        json.dump(site_replies, f, indent=2)

    # 4. Reference Ranges CSV
    ref_ranges = [
        {"test_name": "ALT", "test_code": "ALT", "target_unit": "U/L", "uln": 40.0, "lln": 7.0, "cut_available": 1},
        {"test_name": "AST", "test_code": "AST", "target_unit": "U/L", "uln": 40.0, "lln": 10.0, "cut_available": 1},
        {"test_name": "BILIRUBIN", "test_code": "BILI", "target_unit": "mg/dL", "uln": 1.2, "lln": 0.2, "cut_available": 1},
        {"test_name": "ALP", "test_code": "ALP", "target_unit": "U/L", "uln": 120.0, "lln": 30.0, "cut_available": 1},
        {"test_name": "CREATININE", "test_code": "CREAT", "target_unit": "mg/dL", "uln": 1.3, "lln": 0.6, "cut_available": 1},
        {"test_name": "GLUCOSE", "test_code": "GLUC", "target_unit": "mg/dL", "uln": 100.0, "lln": 70.0, "cut_available": 1},
        {"test_name": "HBA1C", "test_code": "HBA1C", "target_unit": "%", "uln": 6.5, "lln": 4.0, "cut_available": 1},
        {"test_name": "HEMOGLOBIN", "test_code": "HGB", "target_unit": "g/dL", "uln": 17.5, "lln": 12.0, "cut_available": 1},
        {"test_name": "PLATELETS", "test_code": "PLAT", "target_unit": "10^3/uL", "uln": 450.0, "lln": 150.0, "cut_available": 1},
        {"test_name": "WBC", "test_code": "WBC", "target_unit": "10^3/uL", "uln": 11.0, "lln": 4.0, "cut_available": 1},
        {"test_name": "POTASSIUM", "test_code": "K", "target_unit": "mmol/L", "uln": 5.1, "lln": 3.5, "cut_available": 1},
        {"test_name": "SODIUM", "test_code": "NA", "target_unit": "mmol/L", "uln": 145.0, "lln": 135.0, "cut_available": 1},
        {"test_name": "CALCIUM", "test_code": "CA", "target_unit": "mg/dL", "uln": 10.2, "lln": 8.5, "cut_available": 1},
        {"test_name": "ALBUMIN", "test_code": "ALB", "target_unit": "g/dL", "uln": 5.0, "lln": 3.5, "cut_available": 1},
        {"test_name": "BUN", "test_code": "BUN", "target_unit": "mg/dL", "uln": 20.0, "lln": 7.0, "cut_available": 1},
    ]
    with open(os.path.join(data_dir, "reference_ranges.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ref_ranges[0].keys())
        writer.writeheader()
        writer.writerows(ref_ranges)

    # 5. Cuts CSV
    cuts_rows = [
        {"cut": 1, "cut_name": "Cut 1 (Baseline Ingestion)", "date": "2026-01-15", "protocol_version": 1, "cut_available": 1},
        {"cut": 2, "cut_name": "Cut 2 (Week 2 Interim)", "date": "2026-02-01", "protocol_version": 1, "cut_available": 2},
        {"cut": 3, "cut_name": "Cut 3 (Week 4 Milestone / Signal)", "date": "2026-02-28", "protocol_version": 1, "cut_available": 3},
        {"cut": 4, "cut_name": "Cut 4 (Protocol Amendment v2)", "date": "2026-03-15", "protocol_version": 2, "cut_available": 4},
        {"cut": 5, "cut_name": "Cut 5 (Week 6 Interim & Corrections)", "date": "2026-03-31", "protocol_version": 2, "cut_available": 5},
        {"cut": 6, "cut_name": "Cut 6 (Site S04 Surveillance)", "date": "2026-04-15", "protocol_version": 2, "cut_available": 6},
        {"cut": 7, "cut_name": "Cut 7 (Week 8 Lab Audit)", "date": "2026-04-30", "protocol_version": 2, "cut_available": 7},
        {"cut": 8, "cut_name": "Cut 8 (Protocol Amendment v3 & Biomarkers)", "date": "2026-05-15", "protocol_version": 3, "cut_available": 8},
        {"cut": 9, "cut_name": "Cut 9 (Week 12 Interim & Site S09)", "date": "2026-05-31", "protocol_version": 3, "cut_available": 9},
        {"cut": 10, "cut_name": "Cut 10 (Adversarial Document Check)", "date": "2026-06-15", "protocol_version": 3, "cut_available": 10},
        {"cut": 11, "cut_name": "Cut 11 (Week 20 Surveillance)", "date": "2026-06-30", "protocol_version": 3, "cut_available": 11},
        {"cut": 12, "cut_name": "Cut 12 (Study Completion & Database Lock)", "date": "2026-07-31", "protocol_version": 3, "cut_available": 12},
    ]
    with open(os.path.join(data_dir, "cuts.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cuts_rows[0].keys())
        writer.writeheader()
        writer.writerows(cuts_rows)

    # 6. Corrections CSV
    corrections_rows = [
        {"correction_id": "COR-001", "cut": 5, "corrected_at_cut": 5, "record_id": "LB_042-S05-003_WEEK4_ALT", "field": "value", "old_value": "160.0", "new_value": "38.0", "reason": "Central laboratory re-assay identified sample transcription error", "authorized_by": "Central Lab Director"},
        {"correction_id": "COR-002", "cut": 7, "corrected_at_cut": 7, "record_id": "LB_042-S02-001_WEEK6_ALT", "field": "unit", "old_value": "ukat/L", "new_value": "U/L", "reason": "Site electronic data capture unit format resolved", "authorized_by": "Lead Data Manager"}
    ]
    with open(os.path.join(data_dir, "corrections.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=corrections_rows[0].keys())
        writer.writeheader()
        writer.writerows(corrections_rows)

    # 7. Generate 241 Subjects for DM.csv
    # Sites S01 to S12
    sites = [f"S{i:02d}" for i in range(1, 13)]
    subjects = []
    
    # We distribute 241 subjects across 12 sites (~20 per site)
    # Ensure canonical test subjects:
    # S01: 042-S01-001, 042-S01-002, ...
    # S05: 042-S05-001, 042-S05-003, ...
    # S07: 042-S07-001, 042-S07-002, 042-S07-003, ...
    subj_count = 0
    subjs_per_site = {s: 20 for s in sites}
    subjs_per_site["S01"] = 21  # 20*11 + 21 = 241 subjects exactly
    
    for site_idx, site in enumerate(sites):
        n_subjs = subjs_per_site[site]
        for seq in range(1, n_subjs + 1):
            subjid = f"042-{site}-{seq:03d}"
            # Cut availability: baseline subjects available at cut 1
            # Site S04 added at Cut 6
            # Site S09 added at Cut 9
            cut_avail = 1
            if site == "S04":
                cut_avail = 6
            elif site == "S09":
                cut_avail = 9
            
            age = 40 + ((seq * 7 + site_idx * 3) % 36)
            sex = "M" if (seq + site_idx) % 2 == 0 else "F"
            race = ["White", "Black", "Asian", "Hispanic", "Other"][(seq + site_idx) % 5]
            arm = "GF-402 100mg" if (seq % 3 != 0) else "Placebo"
            
            subjects.append({
                "usubjid": subjid,
                "site": site,
                "site_id": site,
                "age": age,
                "sex": sex,
                "race": race,
                "arm": arm,
                "country": "USA",
                "informed_consent_date": f"2025-12-{(seq%20)+1:02d}",
                "cut_available": cut_avail,
                "protocol_version": 1 if cut_avail < 4 else (2 if cut_avail < 8 else 3)
            })

    with open(os.path.join(data_dir, "DM.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=subjects[0].keys())
        writer.writeheader()
        writer.writerows(subjects)

    # 8. Generate DS.csv (Disposition - 241 records, one per subject)
    ds_rows = []
    for s in subjects:
        subjid = s["usubjid"]
        site = s["site"]
        cut_avail = max(s["cut_available"], 3)
        
        # Benchmark COUNT requirements:
        # Exactly 2 subjects at site S07 discontinued due to adverse event!
        if subjid == "042-S07-002":
            ds_rows.append({
                "record_id": f"DS_{subjid}",
                "usubjid": subjid,
                "site": site,
                "status": "DISCONTINUED",
                "reason_discontinued": "Adverse Event - Elevated Liver Transaminases",
                "disposition_date": "2026-02-20",
                "visit": "WEEK4",
                "cut_available": 3
            })
        elif subjid == "042-S07-003":
            ds_rows.append({
                "record_id": f"DS_{subjid}",
                "usubjid": subjid,
                "site": site,
                "status": "DISCONTINUED",
                "reason_discontinued": "Adverse Event - Gastrointestinal Intolerance",
                "disposition_date": "2026-02-22",
                "visit": "WEEK4",
                "cut_available": 3
            })
        elif subjid == "042-S07-001":
            ds_rows.append({
                "record_id": f"DS_{subjid}",
                "usubjid": subjid,
                "site": site,
                "status": "COMPLETED",
                "reason_discontinued": "Completed Protocol Requirements",
                "disposition_date": "2026-06-30",
                "visit": "WEEK24",
                "cut_available": 11
            })
        else:
            # Others: 85% completed, 10% lost to follow-up/withdrawal (not AE), 5% ongoing
            seq = int(subjid.split("-")[-1])
            if seq == 10:
                ds_rows.append({
                    "record_id": f"DS_{subjid}",
                    "usubjid": subjid,
                    "site": site,
                    "status": "DISCONTINUED",
                    "reason_discontinued": "Subject Withdrawal of Consent",
                    "disposition_date": "2026-04-10",
                    "visit": "WEEK8",
                    "cut_available": 7
                })
            else:
                ds_rows.append({
                    "record_id": f"DS_{subjid}",
                    "usubjid": subjid,
                    "site": site,
                    "status": "COMPLETED",
                    "reason_discontinued": "Completed Protocol Requirements",
                    "disposition_date": "2026-07-15",
                    "visit": "WEEK24",
                    "cut_available": 12
                })

    with open(os.path.join(data_dir, "DS.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ds_rows[0].keys())
        writer.writeheader()
        writer.writerows(ds_rows)

    # Calculate record distribution to hit EXACTLY 27,125 records total:
    # Current fixed files:
    # reference_ranges.csv: 15
    # cuts.csv: 12
    # corrections.csv: 2
    # DM.csv: 241
    # DS.csv: 241
    # Total fixed so far = 511 records.
    # Remaining records needed across LB, VS, EX, CM, EG, MH, AE = 27,125 - 511 = 26,614 records!

    visits_schedule = [
        ("SCREENING", "2026-01-05", 1),
        ("BASELINE", "2026-01-15", 1),
        ("WEEK2", "2026-02-01", 2),
        ("WEEK4", "2026-02-24", 3),
        ("WEEK6", "2026-03-20", 5),
        ("WEEK8", "2026-04-10", 7),
        ("WEEK12", "2026-05-10", 9),
        ("WEEK16", "2026-06-05", 10),
        ("WEEK24", "2026-07-15", 12),
    ]

    # Let's allocate target record counts:
    # LB: 12,500
    # VS: 6,000
    # EX: 2,500
    # CM: 2,000
    # EG: 1,500
    # MH: 1,200
    # AE: 914
    # Sum: 12500 + 6000 + 2500 + 2000 + 1500 + 1200 + 914 = 26,614!
    # Total records = 511 + 26,614 = EXACTLY 27,125 records!

    # 9. EX.csv (Exposure / Dosing - target 2,500 records)
    ex_rows = []
    ex_target = 2500
    ex_count = 0
    
    for v_name, v_date, cut_v in visits_schedule:
        if v_name == "SCREENING":
            continue
        for s in subjects:
            if ex_count >= ex_target:
                break
            if s["cut_available"] > cut_v:
                continue
            subjid = s["usubjid"]
            site = s["site"]
            
            # TRAP Requirement:
            # "Which subjects at site S01 received a wrong dose?"
            # At site S01, planned is 100 mg and dose is 100 mg (is_wrong_dose = False).
            # No violations at S01!
            planned = 100.0 if "100" in s["arm"] else 0.0
            actual = planned
            wrong = "N"

            # Intentionally put an isolated dose deviation at Site S03 to ensure engine detects deviations elsewhere
            if site == "S03" and subjid == "042-S03-001" and v_name == "WEEK6":
                actual = 50.0
                wrong = "Y"

            ex_rows.append({
                "record_id": f"EX_{subjid}_{v_name}",
                "usubjid": subjid,
                "site": site,
                "visit": v_name,
                "dose_date": v_date,
                "exdose": actual,
                "dose_amount": actual,
                "planned_dose": planned,
                "dose_unit": "mg",
                "wrong_dose": wrong,
                "cut_available": cut_v
            })
            ex_count += 1
        if ex_count >= ex_target:
            break

    # If still need a few to hit exactly 2500:
    while len(ex_rows) < ex_target:
        s = subjects[len(ex_rows) % len(subjects)]
        ex_rows.append({
            "record_id": f"EX_{s['usubjid']}_EXTRA_{len(ex_rows)}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "visit": "UNSCHEDULED",
            "dose_date": "2026-03-01",
            "exdose": 100.0,
            "dose_amount": 100.0,
            "planned_dose": 100.0,
            "dose_unit": "mg",
            "wrong_dose": "N",
            "cut_available": 5
        })

    with open(os.path.join(data_dir, "EX.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ex_rows[0].keys())
        writer.writeheader()
        writer.writerows(ex_rows)

    # 10. VS.csv (Vital Signs - target 6,000 records)
    vs_rows = []
    vs_target = 6000
    vs_tests = [("SYSBP", "Systolic Blood Pressure", "mmHg", 124.0),
                ("DIABP", "Diastolic Blood Pressure", "mmHg", 78.0),
                ("PULSE", "Pulse Rate", "beats/min", 72.0),
                ("WEIGHT", "Weight", "kg", 82.5)]
    
    for v_name, v_date, cut_v in visits_schedule:
        for s in subjects:
            if len(vs_rows) >= vs_target:
                break
            if s["cut_available"] > cut_v:
                continue
            subjid = s["usubjid"]
            site = s["site"]
            for test_code, test_desc, unit, base_val in vs_tests:
                if len(vs_rows) >= vs_target:
                    break
                val = base_val + (random.randint(-5, 5))
                vs_rows.append({
                    "record_id": f"VS_{subjid}_{v_name}_{test_code}",
                    "usubjid": subjid,
                    "site": site,
                    "visit": v_name,
                    "vstest": test_desc,
                    "vstestcd": test_code,
                    "vsstresn": val,
                    "value": val,
                    "unit": unit,
                    "visit_date": v_date,
                    "cut_available": cut_v
                })
        if len(vs_rows) >= vs_target:
            break

    while len(vs_rows) < vs_target:
        s = subjects[len(vs_rows) % len(subjects)]
        vs_rows.append({
            "record_id": f"VS_{s['usubjid']}_SUPP_{len(vs_rows)}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "visit": "UNSCHEDULED",
            "vstest": "Heart Rate",
            "vstestcd": "PULSE",
            "vsstresn": 74.0,
            "value": 74.0,
            "unit": "beats/min",
            "visit_date": "2026-03-12",
            "cut_available": 5
        })

    with open(os.path.join(data_dir, "VS.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=vs_rows[0].keys())
        writer.writeheader()
        writer.writerows(vs_rows)

    # 11. CM.csv (Concomitant Medications - target 2,000 records)
    cm_rows = []
    cm_target = 2000
    meds = ["Metformin", "Lisinopril", "Atorvastatin", "Amlodipine", "Aspirin", "Omeprazole", "Levothyroxine"]
    for i in range(cm_target):
        s = subjects[i % len(subjects)]
        med = meds[i % len(meds)]
        cm_rows.append({
            "record_id": f"CM_{s['usubjid']}_{i+1}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "cmtrt": med,
            "medication_name": med,
            "cmdose": 500.0 if "Metformin" in med else 20.0,
            "cmunit": "mg",
            "cmroute": "ORAL",
            "start_date": "2025-11-01",
            "end_date": "ONGOING",
            "cut_available": max(s["cut_available"], 1)
        })

    with open(os.path.join(data_dir, "CM.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cm_rows[0].keys())
        writer.writeheader()
        writer.writerows(cm_rows)

    # 12. EG.csv (ECG - target 1,500 records)
    eg_rows = []
    eg_target = 1500
    for i in range(eg_target):
        s = subjects[i % len(subjects)]
        eg_rows.append({
            "record_id": f"EG_{s['usubjid']}_{i+1}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "visit": "BASELINE" if i % 2 == 0 else "WEEK12",
            "egtest": "QTcF Interval",
            "egtestcd": "QTCF",
            "egstresn": 412.0 + (i % 25),
            "unit": "msec",
            "interpretation": "Normal Sinus Rhythm",
            "visit_date": "2026-01-15",
            "cut_available": max(s["cut_available"], 1)
        })

    with open(os.path.join(data_dir, "EG.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=eg_rows[0].keys())
        writer.writeheader()
        writer.writerows(eg_rows)

    # 13. MH.csv (Medical History - target 1,200 records)
    mh_rows = []
    mh_target = 1200
    conditions = ["Type 2 Diabetes Mellitus", "Essential Hypertension", "Hyperlipidemia", "Diabetic Neuropathy", "Obesity"]
    for i in range(mh_target):
        s = subjects[i % len(subjects)]
        cond = conditions[i % len(conditions)]
        mh_rows.append({
            "record_id": f"MH_{s['usubjid']}_{i+1}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "mhterm": cond,
            "condition": cond,
            "meddra_pt": cond,
            "onset_year": 2018 + (i % 6),
            "status": "CHRONIC",
            "cut_available": max(s["cut_available"], 1)
        })

    with open(os.path.join(data_dir, "MH.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=mh_rows[0].keys())
        writer.writeheader()
        writer.writerows(mh_rows)

    # 14. AE.csv (Adverse Events - target 914 records)
    ae_rows = []
    ae_target = 914

    # Crucial benchmark cases for AE:
    # Case A: 042-S05-003 at WEEK4 has Hepatic Enzyme Elevation within 7 days of WEEK4
    ae_rows.append({
        "record_id": "AE_042-S05-003_WEEK4",
        "usubjid": "042-S05-003",
        "site": "S05",
        "visit": "WEEK4",
        "aeterm": "Alanine aminotransferase increased",
        "event_term": "Alanine aminotransferase increased",
        "severity": "Grade 3",
        "aeser": "Y",
        "action_taken": "Study drug withheld",
        "start_date": "2026-02-26",
        "aestdat": "2026-02-26",
        "cut_available": 3
    })

    # Case B: Discontinuations at S07
    ae_rows.append({
        "record_id": "AE_042-S07-002_01",
        "usubjid": "042-S07-002",
        "site": "S07",
        "visit": "WEEK4",
        "aeterm": "Blood bilirubin increased",
        "event_term": "Blood bilirubin increased",
        "severity": "Grade 3",
        "aeser": "Y",
        "action_taken": "Drug permanently discontinued",
        "start_date": "2026-02-18",
        "aestdat": "2026-02-18",
        "cut_available": 3
    })
    ae_rows.append({
        "record_id": "AE_042-S07-003_01",
        "usubjid": "042-S07-003",
        "site": "S07",
        "visit": "WEEK4",
        "aeterm": "Severe nausea and vomiting",
        "event_term": "Severe nausea and vomiting",
        "severity": "Grade 3",
        "aeser": "N",
        "action_taken": "Drug permanently discontinued",
        "start_date": "2026-02-19",
        "aestdat": "2026-02-19",
        "cut_available": 3
    })

    ae_terms = ["Headache", "Diarrhea", "Nasopharyngitis", "Hypoglycemia", "Fatigue", "Dyspepsia", "Back pain", "Dizziness"]
    while len(ae_rows) < ae_target:
        s = subjects[len(ae_rows) % len(subjects)]
        # Skip S01 from severe deviations to keep TRAP pure
        t = ae_terms[len(ae_rows) % len(ae_terms)]
        cut_a = 1 + (len(ae_rows) % 12)
        ae_rows.append({
            "record_id": f"AE_{s['usubjid']}_{len(ae_rows)+1}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "visit": "WEEK" + str(2 * (1 + (len(ae_rows) % 6))),
            "aeterm": t,
            "event_term": t,
            "severity": "Grade 1" if len(ae_rows) % 4 != 0 else "Grade 2",
            "aeser": "N",
            "action_taken": "Dose not changed",
            "start_date": f"2026-0{min(9, (cut_a//2)+1):01d}-{(len(ae_rows)%25)+1:02d}",
            "aestdat": f"2026-0{min(9, (cut_a//2)+1):01d}-{(len(ae_rows)%25)+1:02d}",
            "cut_available": max(s["cut_available"], cut_a)
        })

    with open(os.path.join(data_dir, "AE.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ae_rows[0].keys())
        writer.writeheader()
        writer.writerows(ae_rows)

    # 15. LB.csv (Laboratory - target 12,500 records)
    lb_rows = []
    lb_target = 12500

    # Critical FINDING and LOOKUP benchmark cases:
    # 042-S05-003 at WEEK4:
    # ALT = 160.0 U/L (> 3x ULN 40 U/L)
    # Total Bilirubin = 2.8 mg/dL (> 2x ULN 1.2 mg/dL)
    # ALP = 110.0 U/L (< 2x ULN 120 U/L)
    # All on 2026-02-24 (WEEK4), available at Cut 3!
    lb_rows.append({
        "record_id": "LB_042-S05-003_WEEK4_ALT",
        "usubjid": "042-S05-003",
        "site": "S05",
        "visit": "WEEK4",
        "lbtest": "Alanine Aminotransferase",
        "test_name": "ALT",
        "paramcd": "ALT",
        "lbstresn": 160.0,
        "value": 160.0,
        "lbstresu": "U/L",
        "unit": "U/L",
        "uln": 40.0,
        "collection_date": "2026-02-24",
        "date": "2026-02-24",
        "cut_available": 3,
        "corrected_at_cut": 5
    })
    lb_rows.append({
        "record_id": "LB_042-S05-003_WEEK4_BILI",
        "usubjid": "042-S05-003",
        "site": "S05",
        "visit": "WEEK4",
        "lbtest": "Total Bilirubin",
        "test_name": "BILIRUBIN",
        "paramcd": "BILI",
        "lbstresn": 2.8,
        "value": 2.8,
        "lbstresu": "mg/dL",
        "unit": "mg/dL",
        "uln": 1.2,
        "collection_date": "2026-02-24",
        "date": "2026-02-24",
        "cut_available": 3
    })
    lb_rows.append({
        "record_id": "LB_042-S05-003_WEEK4_ALP",
        "usubjid": "042-S05-003",
        "site": "S05",
        "visit": "WEEK4",
        "lbtest": "Alkaline Phosphatase",
        "test_name": "ALP",
        "paramcd": "ALP",
        "lbstresn": 110.0,
        "value": 110.0,
        "lbstresu": "U/L",
        "unit": "U/L",
        "uln": 120.0,
        "collection_date": "2026-02-24",
        "date": "2026-02-24",
        "cut_available": 3
    })

    # Routine lab tests list
    tests = [
        ("ALT", "Alanine Aminotransferase", "U/L", 28.0, 40.0),
        ("AST", "Aspartate Aminotransferase", "U/L", 25.0, 40.0),
        ("BILIRUBIN", "Total Bilirubin", "mg/dL", 0.7, 1.2),
        ("ALP", "Alkaline Phosphatase", "U/L", 75.0, 120.0),
        ("CREATININE", "Creatinine", "mg/dL", 0.9, 1.3),
        ("GLUCOSE", "Fasting Glucose", "mg/dL", 135.0, 100.0),
        ("HBA1C", "Hemoglobin A1c", "%", 8.2, 6.5),
        ("HEMOGLOBIN", "Hemoglobin", "g/dL", 14.5, 17.5),
    ]

    for v_name, v_date, cut_v in visits_schedule:
        for s in subjects:
            if len(lb_rows) >= lb_target:
                break
            if s["cut_available"] > cut_v:
                continue
            subjid = s["usubjid"]
            site = s["site"]
            for t_code, t_name, unit, norm_v, uln_v in tests:
                if len(lb_rows) >= lb_target:
                    break
                # Skip duplicate of our benchmark record
                if subjid == "042-S05-003" and v_name == "WEEK4" and t_code in ("ALT", "BILIRUBIN", "ALP"):
                    continue
                
                val = norm_v + ((len(lb_rows) % 7) - 3)
                # Ensure no other subject meets Hy's Law to prevent false positives in benchmark
                if t_code == "ALT" and val > 110:
                    val = 35.0
                if t_code == "BILIRUBIN" and val > 2.0:
                    val = 0.9

                lb_rows.append({
                    "record_id": f"LB_{subjid}_{v_name}_{t_code}",
                    "usubjid": subjid,
                    "site": site,
                    "visit": v_name,
                    "lbtest": t_name,
                    "test_name": t_code,
                    "paramcd": t_code,
                    "lbstresn": round(val, 2),
                    "value": round(val, 2),
                    "lbstresu": unit,
                    "unit": unit,
                    "uln": uln_v,
                    "collection_date": v_date,
                    "date": v_date,
                    "cut_available": cut_v
                })
        if len(lb_rows) >= lb_target:
            break

    while len(lb_rows) < lb_target:
        s = subjects[len(lb_rows) % len(subjects)]
        lb_rows.append({
            "record_id": f"LB_{s['usubjid']}_SUPP_{len(lb_rows)}",
            "usubjid": s["usubjid"],
            "site": s["site"],
            "visit": "UNSCHEDULED",
            "lbtest": "Fasting Glucose",
            "test_name": "GLUCOSE",
            "paramcd": "GLUC",
            "lbstresn": 128.0,
            "value": 128.0,
            "lbstresu": "mg/dL",
            "unit": "mg/dL",
            "uln": 100.0,
            "collection_date": "2026-03-10",
            "date": "2026-03-10",
            "cut_available": 5
        })

    with open(os.path.join(data_dir, "LB.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=lb_rows[0].keys())
        writer.writeheader()
        writer.writerows(lb_rows)

    # 16. Verify Total Records Count
    summary = {
        "DM.csv": len(subjects),
        "DS.csv": len(ds_rows),
        "EX.csv": len(ex_rows),
        "VS.csv": len(vs_rows),
        "CM.csv": len(cm_rows),
        "EG.csv": len(eg_rows),
        "MH.csv": len(mh_rows),
        "AE.csv": len(ae_rows),
        "LB.csv": len(lb_rows),
        "reference_ranges.csv": len(ref_ranges),
        "cuts.csv": len(cuts_rows),
        "corrections.csv": len(corrections_rows)
    }
    total_records = sum(summary.values())
    print("Dataset generation summary:")
    for k, v in summary.items():
        print(f"  {k}: {v} records")
    print(f"Total Records: {total_records} (Target: 27125)")
    assert total_records == 27125, f"Expected 27125 records, got {total_records}"
    print("SUCCESS: Exact match to STUDY-042 hackathon specifications!")

if __name__ == "__main__":
    generate_hackathon_dataset()
