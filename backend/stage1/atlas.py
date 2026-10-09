"""
Stage 1: ATLAS
Clinical Trial Knowledge Graph, Patient 360, Unit Normalization, and Deterministic Question Engine.
"""

import os
import json
import csv
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from starter.schemas import Question, Answer, Evidence, Calculation

# Standard lab conversion reference tables and clinical limits
LAB_CONVERSIONS = {
    "ALT": {
        "target_unit": "U/L",
        "ULN": 45.0,  # Upper Limit of Normal
        "conversions": {
            "u/l": (1.0, "identity"),
            "iu/l": (1.0, "identity"),
            "ukat/l": (60.0, "ukat_to_u_l"),
            "µkat/l": (60.0, "ukat_to_u_l"),
            "nkat/l": (0.06, "nkat_to_u_l"),
        }
    },
    "AST": {
        "target_unit": "U/L",
        "ULN": 40.0,
        "conversions": {
            "u/l": (1.0, "identity"),
            "iu/l": (1.0, "identity"),
            "ukat/l": (60.0, "ukat_to_u_l"),
            "µkat/l": (60.0, "ukat_to_u_l"),
            "nkat/l": (0.06, "nkat_to_u_l"),
        }
    },
    "BILIRUBIN": {
        "target_unit": "mg/dL",
        "ULN": 1.2,
        "conversions": {
            "mg/dl": (1.0, "identity"),
            "umol/l": (1.0 / 17.1, "umol_to_mgdl"),
            "µmol/l": (1.0 / 17.1, "umol_to_mgdl"),
            "micromol/l": (1.0 / 17.1, "umol_to_mgdl"),
        }
    },
    "ALP": {
        "target_unit": "U/L",
        "ULN": 120.0,
        "conversions": {
            "u/l": (1.0, "identity"),
            "iu/l": (1.0, "identity"),
            "ukat/l": (60.0, "ukat_to_u_l"),
            "µkat/l": (60.0, "ukat_to_u_l"),
        }
    },
    "CREATININE": {
        "target_unit": "mg/dL",
        "ULN": 1.3,
        "conversions": {
            "mg/dl": (1.0, "identity"),
            "umol/l": (1.0 / 88.4, "umol_to_mgdl"),
            "µmol/l": (1.0 / 88.4, "umol_to_mgdl"),
        }
    },
    "HEMOGLOBIN": {
        "target_unit": "g/dL",
        "ULN": 17.5,
        "conversions": {
            "g/dl": (1.0, "identity"),
            "g/l": (0.1, "g_l_to_g_dl"),
            "mmol/l": (1.611, "mmol_to_gdl"),
        }
    },
    "GLUCOSE": {
        "target_unit": "mg/dL",
        "ULN": 100.0,
        "conversions": {
            "mg/dl": (1.0, "identity"),
            "mmol/l": (18.0182, "mmol_to_mgdl"),
        }
    }
}


def normalize_lab_unit(test_name: str, value: Any, unit: str) -> Tuple[Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    Deterministically normalizes lab values.
    Returns: (normalized_value, normalized_unit, conversion_method, flag)
    Preserves raw measurement without silently fabricating.
    """
    if value is None or str(value).strip() == "":
        return None, unit, None, "MISSING_VALUE"

    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return None, unit, None, f"INVALID_NUMERIC_{value}"

    clean_test = test_name.strip().upper()
    clean_unit = (unit or "").strip().lower()

    # Find matching test in reference table
    matched_test = None
    for k in LAB_CONVERSIONS:
        if k in clean_test or clean_test in k:
            matched_test = k
            break

    if not matched_test:
        return val_float, unit, "passthrough_unmapped_test", None

    test_cfg = LAB_CONVERSIONS[matched_test]
    target_unit = test_cfg["target_unit"]

    if clean_unit in test_cfg["conversions"]:
        multiplier, method = test_cfg["conversions"][clean_unit]
        norm_val = round(val_float * multiplier, 4)
        return norm_val, target_unit, method, None

    # Ambiguous or unexpected unit
    return val_float, unit, "unrecognized_unit", f"AMBIGUOUS_UNIT_{unit}"


def parse_date(date_str: Any) -> Optional[datetime]:
    if not date_str:
        return None
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.split(" ")[0], fmt)
        except ValueError:
            pass
    return None


class StudyGraph:
    """
    Knowledge graph storing connected clinical trial records:
    Subject -> Visits -> Lab Results -> Adverse Events -> Doses -> Medications -> Medical History -> Disposition
    Also connects protocol versions, rules, amendments, and source provenance.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self.subjects: Dict[str, Dict[str, Any]] = {}
        self.records_by_id: Dict[str, Dict[str, Any]] = {}
        self.records_by_subject: Dict[str, List[Dict[str, Any]]] = {}
        self.records_by_domain: Dict[str, List[Dict[str, Any]]] = {}
        self.corrections_applied: List[Dict[str, Any]] = []
        self.current_cut: int = 1
        self.active_protocol_version: int = 1
        self.protocol_rules: List[Dict[str, Any]] = []
        self.documents: Dict[str, Dict[str, Any]] = []
        self.discovered_domains: set = set()
        self.discovered_sites: set = set()

    def _discover_files_for_cut(self, cut: int) -> List[str]:
        """Dynamically discovers files in cut directory or root data_dir."""
        cut_dir = os.path.join(self.data_dir, f"cut_{cut}")
        if os.path.exists(cut_dir) and os.path.isdir(cut_dir):
            return [os.path.join(cut_dir, f) for f in os.listdir(cut_dir) if f.endswith(('.csv', '.json'))]
        if os.path.exists(self.data_dir):
            files = []
            for root, _, filenames in os.walk(self.data_dir):
                for f in filenames:
                    if f.endswith(('.csv', '.json')):
                        files.append(os.path.join(root, f))
            return files
        return []

    def _infer_domain_from_filename_or_columns(self, filename: str, columns: List[str]) -> str:
        """Dynamically identifies clinical domain without hardcoded assumptions."""
        base_name = os.path.basename(filename).lower()
        fn, ext = os.path.splitext(base_name)
        cols_lower = [c.lower() for c in columns]

        # Use tokens/substrings of filename stem (excluding .csv / .json)
        if "subj" in fn or fn == "dm" or ("age" in cols_lower and "sex" in cols_lower):
            return "subjects"
        if "visit" in fn or fn == "sv" or ("visit_name" in cols_lower and "visit_date" in cols_lower):
            return "visits"
        if "lab" in fn or fn == "lb" or "laboratory" in cols_lower or ("param" in cols_lower and "aval" in cols_lower) or "test_name" in cols_lower:
            return "laboratory"
        if "ae" in fn or "adverse" in fn or "aeterm" in cols_lower or "event_term" in cols_lower:
            return "adverse_events"
        if "dose" in fn or "exposure" in fn or fn == "ex" or "dosing" in fn or "dose_amount" in cols_lower or "exdose" in cols_lower:
            return "doses"
        if "med" in fn or fn == "cm" or "concomitant" in fn or "medication_name" in cols_lower or "cmtrt" in cols_lower:
            return "medications"
        if "history" in fn or fn == "mh" or "medical_history" in fn or "condition" in cols_lower or "mhterm" in cols_lower:
            return "medical_history"
        if "disp" in fn or fn == "ds" or "disposition" in fn or "completion_status" in cols_lower or "reason_discontinued" in cols_lower:
            return "disposition"
        if fn == "vs" or "vital" in fn or "vstest" in cols_lower or "vsstresn" in cols_lower:
            return "vital_signs"
        if "ecg" in fn or fn == "eg" or "egtest" in cols_lower:
            return "ecg"
        if "protocol" in fn or "rule" in fn:
            return "protocol_rules"
        if "correction" in fn:
            return "corrections"
        if "reference" in fn or "range" in fn:
            return "reference_ranges"
        if "cut" in fn:
            return "cuts"
        if "amend" in fn:
            return "amendments"
        if "biomarker" in fn or "genom" in fn:
            return "biomarkers"

        # General domain from filename stem
        stem = re.sub(r'[^a-z0-9_]', '', fn)
        return stem or "unknown_domain"

    def _canonicalize_record(self, raw: Dict[str, Any], domain: str, source_file: str, cut: int) -> Dict[str, Any]:
        """Maps any ingested record into the canonical graph node model."""
        clean = {k.strip(): v for k, v in raw.items() if k is not None}
        lower_keys = {k.lower(): k for k in clean}

        # Subject ID discovery
        subj_candidates = ["usubjid", "subject_id", "subjid", "id", "participant_id", "patient_id"]
        subject_id = None
        for cand in subj_candidates:
            if cand in lower_keys:
                subject_id = str(clean[lower_keys[cand]]).strip()
                break

        # Record ID
        rec_candidates = ["record_id", "rec_id", "id", "seq", "lbseq", "aeseq", "exseq"]
        record_id = None
        for cand in rec_candidates:
            if cand in lower_keys and (cand != "id" or domain != "subjects"):
                record_id = str(clean[lower_keys[cand]]).strip()
                break
        if not record_id:
            record_id = f"{domain.upper()[:3]}_{subject_id or 'GEN'}_{len(self.records_by_id) + 1}"

        # Site discovery
        site = None
        for cand in ["site", "site_id", "siteid", "center", "center_id"]:
            if cand in lower_keys:
                site = str(clean[lower_keys[cand]]).strip()
                break
        if not site and subject_id and "-" in subject_id:
            # Infer site from standard format e.g. 042-S05-003 -> S05
            parts = subject_id.split("-")
            for p in parts:
                if p.upper().startswith("S"):
                    site = p.upper()
                    break

        # Date discovery
        date_str = None
        for cand in ["collection_date", "visit_date", "start_date", "dose_date", "event_date", "date", "aestdat", "lbdt"]:
            if cand in lower_keys:
                date_str = clean[lower_keys[cand]]
                break

        # Visit
        visit = None
        for cand in ["visit", "visit_name", "visitnum", "timepoint"]:
            if cand in lower_keys:
                visit = str(clean[lower_keys[cand]]).strip()
                break

        record = {
            "record_id": record_id,
            "subject_id": subject_id,
            "site": site,
            "domain": domain,
            "visit": visit,
            "date": date_str,
            "parsed_date": parse_date(date_str).isoformat() if parse_date(date_str) else None,
            "source_file": os.path.basename(source_file),
            "cut": cut,
            "protocol_version": self.active_protocol_version,
            "raw_data": clean,
            "is_valid": True,
            "history": []
        }

        # Domain specific canonical variables
        if domain == "laboratory":
            test_candidates = ["test_name", "param", "paramcd", "lbtest", "test", "analyte"]
            val_candidates = ["value", "aval", "lbstresn", "result", "val"]
            unit_candidates = ["unit", "aval_unit", "lbstresu", "units"]
            ref_candidates = ["uln", "ref_high", "normal_high", "reference_range_high"]

            test_name = next((clean[lower_keys[c]] for c in test_candidates if c in lower_keys), "UNKNOWN_TEST")
            raw_val = next((clean[lower_keys[c]] for c in val_candidates if c in lower_keys), None)
            raw_unit = next((clean[lower_keys[c]] for c in unit_candidates if c in lower_keys), "")
            uln_val = next((clean[lower_keys[c]] for c in ref_candidates if c in lower_keys), None)

            norm_val, norm_unit, method, flag = normalize_lab_unit(str(test_name), raw_val, str(raw_unit))

            record.update({
                "test_name": str(test_name).upper(),
                "original_value": raw_val,
                "original_unit": str(raw_unit),
                "normalized_value": norm_val,
                "normalized_unit": norm_unit,
                "conversion_method": method,
                "unit_flag": flag,
                "uln": float(uln_val) if uln_val not in (None, "") else LAB_CONVERSIONS.get(str(test_name).upper(), {}).get("ULN")
            })

        elif domain == "adverse_events":
            term_candidates = ["event_term", "aeterm", "term", "adverse_event", "ae_desc"]
            sev_candidates = ["severity", "aesev", "grade", "ctcae_grade"]
            ser_candidates = ["serious", "aeser", "is_serious", "sae"]
            rel_candidates = ["related", "aerel", "causality", "relationship"]

            record.update({
                "term": next((str(clean[lower_keys[c]]).strip() for c in term_candidates if c in lower_keys), "Unknown AE"),
                "severity": next((str(clean[lower_keys[c]]).strip() for c in sev_candidates if c in lower_keys), "Grade 1"),
                "is_serious": str(next((clean[lower_keys[c]] for c in ser_candidates if c in lower_keys), "N")).upper() in ["Y", "YES", "TRUE", "1"],
                "relationship": next((str(clean[lower_keys[c]]).strip() for c in rel_candidates if c in lower_keys), "Possible")
            })

        elif domain == "doses":
            amount_candidates = ["dose_amount", "exdose", "amount", "dose_mg"]
            planned_candidates = ["planned_dose", "target_dose", "protocol_dose"]
            wrong_dose_candidates = ["wrong_dose", "dose_deviation", "deviation"]

            dose_val = next((clean[lower_keys[c]] for c in amount_candidates if c in lower_keys), None)
            plan_val = next((clean[lower_keys[c]] for c in planned_candidates if c in lower_keys), None)
            dev_val = next((clean[lower_keys[c]] for c in wrong_dose_candidates if c in lower_keys), None)

            try:
                dose_num = float(dose_val) if dose_val is not None else None
            except (ValueError, TypeError):
                dose_num = None
            try:
                plan_num = float(plan_val) if plan_val is not None else None
            except (ValueError, TypeError):
                plan_num = None

            is_wrong = False
            if dev_val is not None and str(dev_val).strip().upper() in ["Y", "YES", "TRUE", "1"]:
                is_wrong = True
            elif dose_num is not None and plan_num is not None and abs(dose_num - plan_num) > 0.001:
                is_wrong = True

            record.update({
                "dose_amount": dose_num,
                "planned_dose": plan_num,
                "is_wrong_dose": is_wrong,
                "deviation_reason": clean.get("deviation_reason")
            })

        elif domain == "disposition":
            status_candidates = ["completion_status", "status", "dsstatus", "dispositioned"]
            reason_candidates = ["reason_discontinued", "dsreason", "reason", "discontinuation_reason"]

            status = next((str(clean[lower_keys[c]]).strip() for c in status_candidates if c in lower_keys), "Completed")
            reason = next((str(clean[lower_keys[c]]).strip() for c in reason_candidates if c in lower_keys), "")

            record.update({
                "status": status,
                "reason_discontinued": reason,
                "is_discontinued": "DISCONTINUED" in status.upper() or "EARLY TERMINATION" in status.upper() or bool(reason and "COMPLETED" not in reason.upper())
            })

        return record

    def build(self, cut: int | None = None) -> dict:
        """
        Builds or incrementally updates the study graph for the specified cut.
        Connects Subject -> Visits -> Labs -> AEs -> Doses -> Meds -> History -> Disposition.
        """
        target_cut = cut if cut is not None else 1
        self.current_cut = target_cut

        # Track new sites & domains discovered in this cut
        discovered_new_domains = []
        discovered_new_sites = []

        files = self._discover_files_for_cut(target_cut)
        for filepath in files:
            ext = os.path.splitext(filepath)[1].lower()
            rows: List[Dict[str, Any]] = []

            try:
                if ext == '.csv':
                    with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                elif ext == '.json':
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        rows = data if isinstance(data, list) else [data]
            except Exception as e:
                print(f"Warning: Failed reading {filepath}: {e}")
                continue

            if not rows:
                continue

            domain = self._infer_domain_from_filename_or_columns(filepath, list(rows[0].keys()))
            if domain not in self.discovered_domains:
                self.discovered_domains.add(domain)
                discovered_new_domains.append(domain)

            for raw_row in rows:
                cut_avail = raw_row.get("cut_available")
                if cut_avail is not None and str(cut_avail).strip() != "":
                    try:
                        if int(cut_avail) > target_cut:
                            continue
                    except (ValueError, TypeError):
                        pass

                record = self._canonicalize_record(raw_row, domain, filepath, target_cut)
                rec_id = record["record_id"]
                subj_id = record["subject_id"]
                site = record["site"]

                if site and site not in self.discovered_sites:
                    self.discovered_sites.add(site)
                    discovered_new_sites.append(site)

                # Store in graph indices
                self.records_by_id[rec_id] = record

                if subj_id:
                    if subj_id not in self.subjects:
                        self.subjects[subj_id] = {
                            "subject_id": subj_id,
                            "site": site,
                            "records_count": 0,
                            "first_seen_cut": target_cut,
                            "demographics": {}
                        }
                    if site and not self.subjects[subj_id].get("site"):
                        self.subjects[subj_id]["site"] = site

                    self.records_by_subject.setdefault(subj_id, []).append(record)
                    self.subjects[subj_id]["records_count"] += 1

                    if domain == "subjects":
                        self.subjects[subj_id]["demographics"] = record["raw_data"]

                self.records_by_domain.setdefault(domain, []).append(record)

                # Add Graph Node
                self.nodes[rec_id] = {
                    "id": rec_id,
                    "type": domain,
                    "subject_id": subj_id,
                    "site": site,
                    "visit": record.get("visit"),
                    "date": record.get("date"),
                    "cut": target_cut,
                    "label": f"{domain.capitalize()}: {rec_id}"
                }

                # Add Edge to Subject if applicable
                if subj_id:
                    self.edges.append({
                        "source": f"SUBJ_{subj_id}",
                        "target": rec_id,
                        "relationship": f"HAS_{domain.upper()}",
                        "cut": target_cut
                    })

        # Process corrections if present for this cut
        self._apply_corrections_for_cut(target_cut)

        return {
            "cut": target_cut,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "total_subjects": len(self.subjects),
            "total_records": len(self.records_by_id),
            "discovered_new_domains": discovered_new_domains,
            "discovered_new_sites": discovered_new_sites,
            "domains": list(self.discovered_domains),
            "sites": list(self.discovered_sites)
        }

    def _apply_corrections_for_cut(self, cut: int):
        """Applies deterministic corrections from corrections.csv or cut-specific files."""
        corrections_file = os.path.join(self.data_dir, "corrections.csv")
        cut_corrections = os.path.join(self.data_dir, f"cut_{cut}", "corrections.csv")
        files_to_check = [f for f in (corrections_file, cut_corrections) if os.path.exists(f)]

        for c_file in files_to_check:
            try:
                with open(c_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        eff_cut = int(row.get("cut") or row.get("effective_cut") or cut)
                        if eff_cut != cut:
                            continue
                        target_rec_id = row.get("record_id") or row.get("target_record_id")
                        if target_rec_id and target_rec_id in self.records_by_id:
                            orig = self.records_by_id[target_rec_id]
                            field = row.get("field") or row.get("variable")
                            old_val = orig["raw_data"].get(field)
                            new_val = row.get("corrected_value") or row.get("new_value")

                            # Preserve history for auditability
                            orig["history"].append({
                                "cut": cut,
                                "field": field,
                                "old_value": old_val,
                                "new_value": new_val,
                                "reason": row.get("reason", "Data correction from site / lab"),
                                "timestamp": datetime.now().isoformat()
                            })

                            # Apply correction
                            orig["raw_data"][field] = new_val
                            if orig["domain"] == "laboratory" and field in ("value", "aval", "unit"):
                                test_n = orig.get("test_name", "")
                                v = new_val if field != "unit" else orig["raw_data"].get("value")
                                u = new_val if field == "unit" else orig["raw_data"].get("unit")
                                norm_val, norm_unit, method, flag = normalize_lab_unit(test_n, v, u)
                                orig["normalized_value"] = norm_val
                                orig["normalized_unit"] = norm_unit
                                orig["conversion_method"] = method
                                orig["unit_flag"] = flag

                            self.corrections_applied.append({
                                "cut": cut,
                                "record_id": target_rec_id,
                                "field": field,
                                "old_value": old_val,
                                "new_value": new_val,
                                "reason": row.get("reason", "Lab correction"),
                                "applied_at": datetime.now().isoformat()
                            })
            except Exception as e:
                print(f"Notice: corrections parsing {e}")

    def patient360(self, usubjid: str) -> dict:
        """
        Returns a complete, connected Patient 360 view for one subject.
        Returns structured evidence first and narrative second.
        """
        subj = self.subjects.get(usubjid)
        if not subj:
            # Try case-insensitive or partial match
            for s_id, s_data in self.subjects.items():
                if usubjid.lower() == s_id.lower() or usubjid in s_id:
                    subj = s_data
                    usubjid = s_id
                    break

        if not subj:
            return {
                "subject_id": usubjid,
                "found": False,
                "error": f"Subject {usubjid} not found in study graph.",
                "evidence": []
            }

        recs = self.records_by_subject.get(usubjid, [])

        # Partition records by domain
        by_domain: Dict[str, List[Dict[str, Any]]] = {}
        for r in recs:
            by_domain.setdefault(r["domain"], []).append(r)

        # Build chronological visit timeline
        visits = []
        for v_rec in by_domain.get("visits", []):
            visits.append({
                "record_id": v_rec["record_id"],
                "visit_name": v_rec.get("visit") or v_rec["raw_data"].get("visit_name"),
                "date": v_rec.get("date"),
                "cut": v_rec.get("cut"),
                "source_file": v_rec.get("source_file")
            })
        visits.sort(key=lambda x: str(x.get("date") or ""))

        # Labs structured
        labs = []
        for l_rec in by_domain.get("laboratory", []):
            labs.append({
                "record_id": l_rec["record_id"],
                "test": l_rec.get("test_name"),
                "visit": l_rec.get("visit"),
                "date": l_rec.get("date"),
                "original_value": l_rec.get("original_value"),
                "original_unit": l_rec.get("original_unit"),
                "normalized_value": l_rec.get("normalized_value"),
                "normalized_unit": l_rec.get("normalized_unit"),
                "conversion_method": l_rec.get("conversion_method"),
                "unit_flag": l_rec.get("unit_flag"),
                "uln": l_rec.get("uln"),
                "source_file": l_rec.get("source_file"),
                "history": l_rec.get("history", [])
            })
        labs.sort(key=lambda x: str(x.get("date") or ""))

        # Adverse Events structured
        aes = []
        for a_rec in by_domain.get("adverse_events", []):
            aes.append({
                "record_id": a_rec["record_id"],
                "term": a_rec.get("term"),
                "severity": a_rec.get("severity"),
                "is_serious": a_rec.get("is_serious"),
                "relationship": a_rec.get("relationship"),
                "date": a_rec.get("date"),
                "source_file": a_rec.get("source_file")
            })

        # Dosing records
        doses = []
        for d_rec in by_domain.get("doses", []):
            doses.append({
                "record_id": d_rec["record_id"],
                "visit": d_rec.get("visit"),
                "date": d_rec.get("date"),
                "dose_amount": d_rec.get("dose_amount"),
                "planned_dose": d_rec.get("planned_dose"),
                "is_wrong_dose": d_rec.get("is_wrong_dose"),
                "source_file": d_rec.get("source_file")
            })

        # Disposition
        dispositions = by_domain.get("disposition", [])
        disp_summary = None
        if dispositions:
            last_disp = dispositions[-1]
            disp_summary = {
                "record_id": last_disp["record_id"],
                "status": last_disp.get("status"),
                "reason_discontinued": last_disp.get("reason_discontinued"),
                "is_discontinued": last_disp.get("is_discontinued"),
                "source_file": last_disp.get("source_file")
            }

        # Protocol findings for this patient
        findings = []
        # Check Hy's Law criteria for this subject
        alt_records = [l for l in labs if l.get("test") == "ALT" and l.get("normalized_value") is not None and l.get("uln")]
        bili_records = [l for l in labs if l.get("test") == "BILIRUBIN" and l.get("normalized_value") is not None and l.get("uln")]
        for a in alt_records:
            if a["normalized_value"] > 3.0 * a["uln"]:
                # Check concurrent bilirubin
                for b in bili_records:
                    if b["normalized_value"] > 2.0 * b["uln"]:
                        a_dt = parse_date(a.get("date"))
                        b_dt = parse_date(b.get("date"))
                        if a_dt and b_dt and abs((a_dt - b_dt).days) <= 14:
                            findings.append({
                                "rule": "HYS_LAW_POTENTIAL",
                                "description": f"Concurrent ALT > 3x ULN ({a['normalized_value']} U/L) and Bilirubin > 2x ULN ({b['normalized_value']} mg/dL)",
                                "evidence_records": [a["record_id"], b["record_id"]],
                                "severity": "HIGH"
                            })

        # Check for wrong doses
        for d in doses:
            if d.get("is_wrong_dose"):
                findings.append({
                    "rule": "DOSING_DEVIATION",
                    "description": f"Administered dose {d.get('dose_amount')} mg differs from protocol planned dose {d.get('planned_dose')} mg",
                    "evidence_records": [d["record_id"]],
                    "severity": "MEDIUM"
                })

        return {
            "subject_id": usubjid,
            "site": subj.get("site"),
            "found": True,
            "demographics": subj.get("demographics", {}),
            "timeline": {
                "visits": visits,
                "laboratory": labs,
                "adverse_events": aes,
                "doses": doses,
                "medications": by_domain.get("medications", []),
                "medical_history": by_domain.get("medical_history", []),
                "disposition": disp_summary,
            },
            "findings": findings,
            "source_records_count": len(recs),
            "latest_data_cut": self.current_cut
        }


class Atlas:
    """
    Atlas Question Engine supporting deterministic COUNT, LOOKUP, FINDING, and TRAP queries.
    Never invents data; provides exact evidence citations for every answer.
    """

    def __init__(self, graph: StudyGraph):
        self.graph = graph

    def answer(self, question: Question) -> Answer:
        """Evaluates reviewer questions deterministically against graph evidence."""
        text = question.text.strip()
        q_lower = text.lower()
        cat_input = (question.category or "").strip().upper()

        # Infer natural category from question text
        detected_category = "LOOKUP"
        if any(kw in q_lower for kw in ("how many", "count ", "total subjects", "total records", "number of ", "how much")):
            detected_category = "COUNT"
        elif any(kw in q_lower for kw in ("wrong dose", "trap", "dose deviation", "dose error")):
            detected_category = "TRAP"
        elif any(kw in q_lower for kw in ("hy's law", "hys law", "which subjects", "who met", "who had", "abnormal", "criteria", "safety signal", "sae", "serious adverse")):
            detected_category = "FINDING"
        elif any(kw in q_lower for kw in ("list ", "lookup", "within ", "records for", "show records", "what are the records", "vitals for", "labs for", "medications for", "visits for", "details for", "demographics for")):
            detected_category = "LOOKUP"

        # Determine effective category intelligently:
        if not cat_input or cat_input == "AUTO":
            effective_cat = detected_category
        elif cat_input in ("FINDING", "COUNT", "TRAP") and any(kw in q_lower for kw in ("list ", "within ", "records for", "records of", "show records", "what are the records")):
            # User query is specifically a LOOKUP even if previous category was left in UI dropdown
            effective_cat = "LOOKUP"
        elif cat_input == "FINDING" and any(kw in q_lower for kw in ("how many", "count ", "total subjects")):
            effective_cat = "COUNT"
        elif cat_input == "COUNT" and any(kw in q_lower for kw in ("hy's law", "hys law", "which subjects")):
            effective_cat = "FINDING"
        else:
            effective_cat = cat_input

        if effective_cat == "COUNT":
            ans = self._handle_count(text, q_lower)
        elif effective_cat == "LOOKUP":
            ans = self._handle_lookup(text, q_lower)
        elif effective_cat == "FINDING":
            ans = self._handle_finding(text, q_lower)
        elif effective_cat == "TRAP":
            ans = self._handle_trap(text, q_lower)
        else:
            ans = self._handle_lookup(text, q_lower)

        ans.category = effective_cat
        return ans

    def _handle_count(self, text: str, q_lower: str) -> Answer:
        """
        COUNT question handler:
        Supports:
        - Adverse event discontinuations (e.g. S07 AE discontinuations)
        - Subject enrollment by site or study
        - Adverse events totals
        - Records totals
        """
        site_match = re.search(r'\b(s\d{2,3})\b', q_lower)
        target_site = site_match.group(1).upper() if site_match else None

        # Check if asking about discontinuations
        is_disc_query = any(k in q_lower for k in ("discontinu", "withdr", "drop out", "terminate"))

        if is_disc_query:
            evidence_list: List[Evidence] = []
            matching_subjid_set = set()

            disp_records = self.graph.records_by_domain.get("disposition", [])
            for r in disp_records:
                subj_id = r.get("subject_id")
                site = r.get("site")
                if target_site and site != target_site:
                    continue

                reason = str(r.get("reason_discontinued", "")).lower()
                status = str(r.get("status", "")).lower()
                is_ae_disc = "adverse event" in reason or "ae" in reason or "toxicity" in reason

                # If query specifically mentions AE or general discontinuation
                if ("adverse event" in q_lower or "ae" in q_lower):
                    if is_ae_disc and (r.get("is_discontinued") or "discontinued" in status):
                        matching_subjid_set.add(subj_id)
                        evidence_list.append(Evidence(
                            record_id=r["record_id"],
                            subject_id=subj_id,
                            domain="disposition",
                            source_file=r["source_file"],
                            reason=f"Subject at {site or 'Unknown site'} discontinued: '{r.get('reason_discontinued')}'",
                            variable="reason_discontinued",
                            value=r.get("reason_discontinued"),
                            visit=r.get("visit"),
                            date=r.get("date")
                        ))
                else:
                    if r.get("is_discontinued") or "discontinued" in status or reason:
                        matching_subjid_set.add(subj_id)
                        evidence_list.append(Evidence(
                            record_id=r["record_id"],
                            subject_id=subj_id,
                            domain="disposition",
                            source_file=r["source_file"],
                            reason=f"Subject at {site or 'Unknown site'} discontinued: '{r.get('reason_discontinued') or status}'",
                            variable="status",
                            value=r.get("reason_discontinued") or status,
                            visit=r.get("visit"),
                            date=r.get("date")
                        ))

            # Also cross-reference adverse events if AE discontinuation is requested
            if "adverse event" in q_lower or "ae" in q_lower:
                ae_records = self.graph.records_by_domain.get("adverse_events", [])
                for a in ae_records:
                    subj_id = a.get("subject_id")
                    site = a.get("site")
                    if target_site and site != target_site:
                        continue
                    action = str(a["raw_data"].get("action_taken", "")).lower()
                    if "discontinued" in action or "withdrawn" in action:
                        matching_subjid_set.add(subj_id)
                        evidence_list.append(Evidence(
                            record_id=a["record_id"],
                            subject_id=subj_id,
                            domain="adverse_events",
                            source_file=a["source_file"],
                            reason=f"Adverse event '{a.get('term')}' caused action: '{action}'",
                            variable="action_taken",
                            value=action,
                            visit=a.get("visit"),
                            date=a.get("date")
                        ))

            count = len(matching_subjid_set)
            site_str = f"at site {target_site}" if target_site else "across all sites"
            qualifier = "due to an adverse event" if ("adverse event" in q_lower or "ae" in q_lower) else "overall"
            ans_text = f"Exactly {count} subject{'s' if count != 1 else ''} {site_str} discontinued {qualifier}."
            if count > 0:
                ans_text += f" Matching subject ID(s): {', '.join(sorted(matching_subjid_set))}."

            calc = Calculation(
                name="Deterministic Count of Discontinuations",
                formula="COUNT(DISTINCT subject_id WHERE site = target_site AND is_discontinued == TRUE)",
                inputs={"target_site": target_site, "disposition_records_evaluated": len(disp_records)},
                result=count
            )

            return Answer(
                answer=ans_text,
                result=count,
                evidence=evidence_list,
                calculations=[calc],
                data_cut=self.graph.current_cut
            )

        # Check if asking about enrolled subjects
        if any(k in q_lower for k in ("subject", "patient", "enrolled", "participants")):
            matching_subjs = []
            evidence_list = []
            for s_id, s_data in self.graph.subjects.items():
                if target_site and s_data.get("site") != target_site:
                    continue
                matching_subjs.append(s_id)
                # Add one demographic or summary evidence item per subject (up to 20 for preview)
                if len(evidence_list) < 20:
                    evidence_list.append(Evidence(
                        record_id=f"SUBJ_{s_id}",
                        subject_id=s_id,
                        domain="subjects",
                        source_file="DM.csv",
                        reason=f"Enrolled subject at {s_data.get('site')}",
                        variable="site",
                        value=s_data.get("site")
                    ))

            count = len(matching_subjs)
            site_str = f"at site {target_site}" if target_site else "in the study"
            ans_text = f"Exactly {count} subject{'s' if count != 1 else ''} are enrolled {site_str}."

            calc = Calculation(
                name="Deterministic Subject Count",
                formula="COUNT(DISTINCT subject_id WHERE site = target_site)",
                inputs={"target_site": target_site, "total_study_subjects": len(self.graph.subjects)},
                result=count
            )

            return Answer(
                answer=ans_text,
                result=count,
                evidence=evidence_list,
                calculations=[calc],
                data_cut=self.graph.current_cut
            )

        # Check if asking about adverse events count
        if "adverse" in q_lower or "ae" in q_lower:
            ae_recs = self.graph.records_by_domain.get("adverse_events", [])
            matching_aes = []
            evidence_list = []
            for a in ae_recs:
                if target_site and a.get("site") != target_site:
                    continue
                matching_aes.append(a)
                if len(evidence_list) < 25:
                    evidence_list.append(Evidence(
                        record_id=a["record_id"],
                        subject_id=a.get("subject_id"),
                        domain="adverse_events",
                        source_file=a.get("source_file"),
                        reason=f"Adverse event: {a.get('term')} ({a.get('severity')})",
                        variable="term",
                        value=a.get("term"),
                        visit=a.get("visit"),
                        date=a.get("date")
                    ))

            count = len(matching_aes)
            site_str = f"at site {target_site}" if target_site else "across the study"
            ans_text = f"Exactly {count} adverse event record{'s' if count != 1 else ''} reported {site_str}."

            calc = Calculation(
                name="Deterministic Adverse Event Count",
                formula="COUNT(adverse_events WHERE site = target_site)",
                inputs={"target_site": target_site},
                result=count
            )

            return Answer(
                answer=ans_text,
                result=count,
                evidence=evidence_list,
                calculations=[calc],
                data_cut=self.graph.current_cut
            )

        # Default count: total records or nodes
        count = len(self.graph.records_by_id)
        return Answer(
            answer=f"The active study knowledge graph contains {count} verified records at Cut {self.graph.current_cut}.",
            result=count,
            evidence=[],
            calculations=[Calculation(name="Total Graph Records", formula="COUNT(records)", inputs={"cut": self.graph.current_cut}, result=count)],
            data_cut=self.graph.current_cut
        )

    def _handle_lookup(self, text: str, q_lower: str) -> Answer:
        """
        LOOKUP question handler:
        Handles deterministic temporal and subject lookups:
        e.g. "List the laboratory and adverse-event records for 042-S01-001 within 7 days of the BASELINE visit."
        or "List the laboratory and adverse-event records for 042-S05-003 within 7 days of the WEEK4 visit."
        or any general query for a subject's labs, AEs, vitals, meds, or history.
        """
        # Discover subject ID
        subj_match = re.search(r'\b(\d{3}-[A-Z0-9]+-\d{3}|[A-Z0-9]+-\d{3}|SUBJ[A-Z0-9_-]+)\b', text, re.IGNORECASE)
        target_subj = subj_match.group(1).upper() if subj_match else None

        # Discover target visit (e.g., BASELINE, SCREENING, WEEK4, WEEK2, DAY1, etc.)
        visit_match = re.search(r'\b(week\s*\d+|screening|baseline|day\s*\d+)\b', q_lower)
        target_visit = visit_match.group(1).upper().replace(" ", "") if visit_match else None

        # Discover day window e.g. "within 7 days"
        window_match = re.search(r'within\s*(\d+)\s*days', q_lower)
        days_window = int(window_match.group(1)) if window_match else 7

        if not target_subj:
            # Fallback to general lookup of requested subject
            for s in self.graph.subjects:
                if s.lower() in q_lower:
                    target_subj = s
                    break

        if not target_subj:
            available_preview = ", ".join(list(self.graph.subjects.keys())[:5])
            return Answer(
                answer=f"Lookup query requires a valid Subject ID (e.g., 042-S01-001 or 042-S05-003). Available examples: {available_preview}...",
                result=[],
                evidence=[],
                calculations=[],
                data_cut=self.graph.current_cut
            )

        subj_records = self.graph.records_by_subject.get(target_subj, [])
        if not subj_records:
            return Answer(
                answer=f"No records found for subject {target_subj} in Data Cut {self.graph.current_cut}.",
                result=[],
                evidence=[],
                calculations=[],
                data_cut=self.graph.current_cut
            )

        # Locate target visit date if a visit was requested
        target_date = None
        if target_visit:
            # Check visit records first
            for r in subj_records:
                v_name = (r.get("visit") or r.get("raw_data", {}).get("visit_name") or "").upper().replace(" ", "")
                if target_visit in v_name:
                    p_dt = parse_date(r.get("date"))
                    if p_dt:
                        target_date = p_dt
                        break

            # If not yet found, check any domain record at that visit
            if not target_date:
                for r in subj_records:
                    v_name = (r.get("visit") or "").upper().replace(" ", "")
                    if target_visit in v_name:
                        p_dt = parse_date(r.get("date"))
                        if p_dt:
                            target_date = p_dt
                            break

        # Check domain filters requested in query
        filter_domains = set()
        if "lab" in q_lower or "laboratory" in q_lower:
            filter_domains.add("laboratory")
        if "adverse" in q_lower or "ae" in q_lower:
            filter_domains.add("adverse_events")
        if "medication" in q_lower or "concomitant" in q_lower or "cm" in q_lower:
            filter_domains.add("medications")
        if "vital" in q_lower or "vs" in q_lower:
            filter_domains.add("vital_signs")
        if "dose" in q_lower or "ex" in q_lower:
            filter_domains.add("doses")

        evidence_list: List[Evidence] = []
        matching_records = []

        for r in subj_records:
            domain = r.get("domain")

            # Apply domain filter if user specified domains
            if filter_domains and domain not in filter_domains:
                continue

            r_dt = parse_date(r.get("date"))
            in_window = True

            if target_date:
                if r_dt:
                    delta = abs((r_dt - target_date).days)
                    if delta > days_window:
                        in_window = False
                else:
                    in_window = False

            if in_window:
                matching_records.append(r)
                var_name = r.get("test_name") or r.get("term") or r.get("med_name") or r.get("test") or domain
                val = r.get("normalized_value") if r.get("normalized_value") is not None else (r.get("severity") or r.get("dose_amount") or r.get("original_value") or r.get("value"))
                evidence_list.append(Evidence(
                    record_id=r["record_id"],
                    subject_id=target_subj,
                    domain=domain,
                    source_file=r.get("source_file"),
                    reason=f"{domain.replace('_', ' ').title()} record: {var_name} at visit {r.get('visit') or 'N/A'} on {r.get('date') or 'N/A'}",
                    variable=var_name,
                    value=val,
                    unit=r.get("normalized_unit") or r.get("original_unit"),
                    visit=r.get("visit"),
                    date=r.get("date")
                ))

        ans_msg = f"Retrieved {len(matching_records)} records for subject {target_subj}"
        if target_visit and target_date:
            ans_msg += f" within {days_window} days of {target_visit} ({target_date.strftime('%Y-%m-%d')})."
        elif target_visit:
            ans_msg += f" for visit {target_visit}."
        else:
            ans_msg += f" across requested domains."

        calc = Calculation(
            name="Date Window Filter",
            formula=f"ABS(record_date - visit_date) <= {days_window} days" if target_date else "SELECT records WHERE subject_id = target_subj",
            inputs={
                "target_subject": target_subj,
                "target_visit": target_visit,
                "target_date": target_date.strftime('%Y-%m-%d') if target_date else None,
                "days_window": days_window if target_date else None,
                "filtered_domains": list(filter_domains) if filter_domains else ["all"]
            },
            result=len(matching_records)
        )

        return Answer(
            answer=ans_msg,
            result=matching_records,
            evidence=evidence_list,
            calculations=[calc],
            data_cut=self.graph.current_cut
        )

    def _handle_finding(self, text: str, q_lower: str) -> Answer:
        """
        FINDING question handler:
        Supports:
        - FDA Hy's law criteria:
          1. ALT or AST > 3x ULN
          2. Total Bilirubin > 2x ULN
          3. Concurrently within 14 days
          4. ALP < 2x ULN (no initial cholestasis)
        - Serious adverse events (SAE)
        - Specific AE terms (e.g., Hypoglycemia)
        - Elevated transaminases
        - Protocol deviations
        """
        # If query is specifically about Serious Adverse Events (SAE)
        if any(k in q_lower for k in ("serious", "sae")):
            evidence_list: List[Evidence] = []
            matching_subjs = set()
            ae_records = self.graph.records_by_domain.get("adverse_events", [])
            for a in ae_records:
                is_serious = a.get("is_serious") or str(a.get("severity", "")).upper() == "SEVERE"
                if is_serious:
                    subj_id = a.get("subject_id")
                    matching_subjs.add(subj_id)
                    evidence_list.append(Evidence(
                        record_id=a["record_id"],
                        subject_id=subj_id,
                        domain="adverse_events",
                        source_file=a.get("source_file"),
                        reason=f"Serious AE: {a.get('term')} (Severity: {a.get('severity')}) on {a.get('date')}",
                        variable="term",
                        value=a.get("term"),
                        visit=a.get("visit"),
                        date=a.get("date")
                    ))

            ans_text = f"Identified {len(matching_subjs)} subject(s) with Serious Adverse Events (SAE): {', '.join(sorted(matching_subjs))}." if matching_subjs else "No subjects experienced serious adverse events in this data cut."
            calc = Calculation(
                name="Serious Adverse Event Evaluation",
                formula="is_serious == TRUE OR severity == 'SEVERE'",
                inputs={"ae_records_evaluated": len(ae_records)},
                result=len(matching_subjs)
            )
            return Answer(
                answer=ans_text,
                result=list(matching_subjs),
                evidence=evidence_list,
                calculations=[calc],
                data_cut=self.graph.current_cut
            )

        # Default / Primary finding: Hy's Law criteria evaluation
        evidence_list: List[Evidence] = []
        matching_subjects = []
        calculations: List[Calculation] = []

        for subj_id, subj_recs in self.graph.records_by_subject.items():
            labs = [r for r in subj_recs if r.get("domain") == "laboratory" and r.get("is_valid", True)]

            alt_records = [l for l in labs if l.get("test_name") in ("ALT", "ALANINE AMINOTRANSFERASE") and l.get("normalized_value") is not None and l.get("uln")]
            ast_records = [l for l in labs if l.get("test_name") in ("AST", "ASPARTATE AMINOTRANSFERASE") and l.get("normalized_value") is not None and l.get("uln")]
            bili_records = [l for l in labs if l.get("test_name") in ("BILIRUBIN", "TOTAL BILIRUBIN") and l.get("normalized_value") is not None and l.get("uln")]
            alp_records = [l for l in labs if l.get("test_name") in ("ALP", "ALKALINE PHOSPHATASE") and l.get("normalized_value") is not None and l.get("uln")]

            transaminases = alt_records + ast_records

            for t in transaminases:
                t_val = t["normalized_value"]
                t_uln = t["uln"]
                if t_val > 3.0 * t_uln:
                    t_date = parse_date(t.get("date"))

                    for b in bili_records:
                        b_val = b["normalized_value"]
                        b_uln = b["uln"]
                        if b_val > 2.0 * b_uln:
                            b_date = parse_date(b.get("date"))
                            days_diff = abs((t_date - b_date).days) if t_date and b_date else 0

                            if days_diff <= 14:
                                # Check ALP cholestasis criteria
                                cholestatic = False
                                for a in alp_records:
                                    a_date = parse_date(a.get("date"))
                                    if a_date and t_date and abs((a_date - t_date).days) <= 14:
                                        if a["normalized_value"] >= 2.0 * a["uln"]:
                                            cholestatic = True
                                            break

                                if not cholestatic:
                                    evidence_list.append(Evidence(
                                        record_id=t["record_id"],
                                        subject_id=subj_id,
                                        domain="laboratory",
                                        source_file=t["source_file"],
                                        reason=f"{t['test_name']} value {t_val} {t['normalized_unit']} exceeds 3x ULN ({t_uln}) on {t.get('date')}",
                                        variable=t["test_name"],
                                        value=t_val,
                                        unit=t["normalized_unit"],
                                        date=t.get("date")
                                    ))
                                    evidence_list.append(Evidence(
                                        record_id=b["record_id"],
                                        subject_id=subj_id,
                                        domain="laboratory",
                                        source_file=b["source_file"],
                                        reason=f"Bilirubin value {b_val} {b['normalized_unit']} exceeds 2x ULN ({b_uln}) on {b.get('date')}",
                                        variable="BILIRUBIN",
                                        value=b_val,
                                        unit=b["normalized_unit"],
                                        date=b.get("date")
                                    ))

                                    calc = Calculation(
                                        name=f"Hy's Law Deterministic Evaluation for {subj_id}",
                                        formula="(ALT_or_AST > 3x ULN) AND (Bilirubin > 2x ULN) WITHIN 14 days AND (ALP < 2x ULN)",
                                        inputs={
                                            "subject_id": subj_id,
                                            "transaminase_test": t["test_name"],
                                            "transaminase_val": t_val,
                                            "transaminase_uln": t_uln,
                                            "transaminase_ratio": round(t_val / t_uln, 2),
                                            "bili_val": b_val,
                                            "bili_uln": b_uln,
                                            "bili_ratio": round(b_val / b_uln, 2),
                                            "days_difference": days_diff
                                        },
                                        result="CRITERIA_MET"
                                    )
                                    calculations.append(calc)

                                    if subj_id not in [s["subject_id"] for s in matching_subjects]:
                                        matching_subjects.append({
                                            "subject_id": subj_id,
                                            "site": t.get("site"),
                                            "transaminase": f"{t['test_name']}: {t_val} {t['normalized_unit']} ({round(t_val/t_uln, 1)}x ULN)",
                                            "bilirubin": f"{b_val} {b['normalized_unit']} ({round(b_val/b_uln, 1)}x ULN)",
                                            "evidence_record_ids": [t["record_id"], b["record_id"]]
                                        })

        count = len(matching_subjects)
        if count == 0:
            ans_text = "No subjects in the current data cut meet the protocol-defined Hy's law criteria."
        else:
            subj_strs = [f"{s['subject_id']} ({s['transaminase']}, Bilirubin: {s['bilirubin']})" for s in matching_subjects]
            ans_text = f"Identified {count} subject{'s' if count != 1 else ''} meeting protocol Hy's law criteria: " + "; ".join(subj_strs) + "."

        return Answer(
            answer=ans_text,
            result=matching_subjects,
            evidence=evidence_list,
            calculations=calculations,
            data_cut=self.graph.current_cut
        )

    def _handle_trap(self, text: str, q_lower: str) -> Answer:
        """
        TRAP question handler:
        e.g. "Which subjects at site S01 received a wrong dose?"
        CRITICAL: If there are no matching records, returns empty result set and "No subjects found."
        NEVER invents a positive finding merely because question expects one!
        """
        site_match = re.search(r'\b(s\d{2,3})\b', q_lower)
        target_site = site_match.group(1).upper() if site_match else None

        doses = self.graph.records_by_domain.get("doses", [])
        evidence_list: List[Evidence] = []
        matching_subjects = []

        for d in doses:
            site = d.get("site")
            if target_site and site != target_site:
                continue

            if d.get("is_wrong_dose"):
                subj_id = d.get("subject_id")
                matching_subjects.append({
                    "subject_id": subj_id,
                    "site": site,
                    "dose_amount": d.get("dose_amount"),
                    "planned_dose": d.get("planned_dose"),
                    "record_id": d.get("record_id")
                })
                evidence_list.append(Evidence(
                    record_id=d["record_id"],
                    subject_id=subj_id,
                    domain="doses",
                    source_file=d["source_file"],
                    reason=f"Wrong dose administered: {d.get('dose_amount')} mg vs planned {d.get('planned_dose')} mg",
                    variable="dose_amount",
                    value=d.get("dose_amount"),
                    visit=d.get("visit"),
                    date=d.get("date")
                ))

        calc = Calculation(
            name="Deterministic Dose Verification",
            formula="dose_amount != planned_dose OR is_wrong_dose == TRUE",
            inputs={"target_site": target_site, "doses_evaluated": len(doses)},
            result=len(matching_subjects)
        )

        site_label = f"at site {target_site}" if target_site else "in the dataset"
        if not matching_subjects:
            # Deterministic negative result without hallucination
            return Answer(
                answer=f"No subjects found. Zero subjects {site_label} received a wrong dose based on verified clinical dosing records.",
                result=[],
                evidence=[],
                calculations=[calc],
                data_cut=self.graph.current_cut
            )

        return Answer(
            answer=f"Identified {len(matching_subjects)} subject(s) {site_label} with dosing deviations: {', '.join([s['subject_id'] for s in matching_subjects])}.",
            result=matching_subjects,
            evidence=evidence_list,
            calculations=[calc],
            data_cut=self.graph.current_cut
        )
