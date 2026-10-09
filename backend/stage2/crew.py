"""
Stage 2: MONITOR
Multi-agent clinical review workflow:
Nodes: Detect -> Medical Review -> Data Manager -> Compliance -> Human Gate -> Execute.
Human escalations require real decisions; maintains an auditable review trace.
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from starter.schemas import Question, Answer, Evidence, Calculation
from stage1.atlas import Atlas


class ReviewReport:
    """Structured report produced by ReviewCrew cycle."""
    def __init__(
        self,
        cut: int,
        protocol_version: int,
        detected_findings: List[Dict[str, Any]],
        medical_assessments: List[Dict[str, Any]],
        data_queries: List[Dict[str, Any]],
        compliance_results: List[Dict[str, Any]],
        escalations: List[Dict[str, Any]],
        monitor_decisions: List[Dict[str, Any]],
        executed_actions: List[Dict[str, Any]],
        unresolved_items: List[Dict[str, Any]],
        audit_trace: List[Dict[str, Any]]
    ):
        self.cut = cut
        self.protocol_version = protocol_version
        self.detected_findings = detected_findings
        self.medical_assessments = medical_assessments
        self.data_queries = data_queries
        self.compliance_results = compliance_results
        self.escalations = escalations
        self.monitor_decisions = monitor_decisions
        self.executed_actions = executed_actions
        self.unresolved_items = unresolved_items
        self.audit_trace = audit_trace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cut": self.cut,
            "protocol_version": self.protocol_version,
            "detected_findings": self.detected_findings,
            "medical_assessments": self.medical_assessments,
            "data_queries": self.data_queries,
            "compliance_results": self.compliance_results,
            "escalations": self.escalations,
            "monitor_decisions": self.monitor_decisions,
            "executed_actions": self.executed_actions,
            "unresolved_items": self.unresolved_items,
            "audit_trace": self.audit_trace
        }


class ReviewCrew:
    """
    Orchestrates the 6-stage clinical review cycle:
    1. detect
    2. medical review
    3. data manager
    4. compliance
    5. human gate
    6. execute
    """

    def __init__(self, hub_url: str = "", gateway_url: str = "", team_key: str = "", atlas: Optional[Atlas] = None):
        self.hub_url = hub_url
        self.gateway_url = gateway_url
        self.team_key = team_key
        self.atlas = atlas
        self.existing_queries: Dict[str, Dict[str, Any]] = {}
        self.escalations_store: Dict[str, Dict[str, Any]] = {}
        self.rejected_findings_history: set = set()
        self.audit_log: List[Dict[str, Any]] = []

    def _log_audit(self, action: str, cut: int, actor: str, details: Dict[str, Any]):
        event = {
            "event_id": f"EVT_{cut}_{len(self.audit_log) + 1}_{uuid.uuid4().hex[:6]}",
            "timestamp": datetime.now().isoformat(),
            "cut": cut,
            "actor": actor,
            "action": action,
            "details": details
        }
        self.audit_log.append(event)
        return event

    def run_cycle(self, cut: int, protocol_version: int) -> ReviewReport:
        """Executes nodes 1 to 6 in exact deterministic sequence."""
        if not self.atlas:
            raise ValueError("Atlas instance must be configured on ReviewCrew")

        cycle_audit: List[Dict[str, Any]] = []

        # NODE 1: DETECT
        # Uses Atlas unchanged through its interface
        detected_findings = self.node_1_detect(cut, protocol_version)
        cycle_audit.append(self._log_audit(
            "DETECT_FINDINGS", cut, "AtlasEngine",
            {"count": len(detected_findings), "cut": cut}
        ))

        # NODE 2: MEDICAL REVIEW
        # Separates clinical signals vs data-quality problems
        medical_assessments = self.node_2_medical_review(detected_findings, cut)
        cycle_audit.append(self._log_audit(
            "MEDICAL_REVIEW", cut, "MedicalReviewer",
            {"assessed": len(medical_assessments)}
        ))

        # NODE 3: DATA MANAGER
        # Deduplicated query generation for data-quality problems
        data_queries = self.node_3_data_manager(medical_assessments, cut)
        cycle_audit.append(self._log_audit(
            "DATA_QUERIES_DISPATCHED", cut, "DataManager",
            {"new_queries": len(data_queries)}
        ))

        # NODE 4: COMPLIANCE
        # Evaluates subjects against active protocol rules
        compliance_results = self.node_4_compliance(cut, protocol_version)
        cycle_audit.append(self._log_audit(
            "COMPLIANCE_CHECK", cut, "ComplianceOfficer",
            {"rules_checked": len(compliance_results)}
        ))

        # NODE 5: HUMAN GATE
        # Evaluates escalations; never auto-approves; handles pending/approved/rejected
        escalations, monitor_decisions = self.node_5_human_gate(medical_assessments, cut)
        cycle_audit.append(self._log_audit(
            "HUMAN_GATE_EVALUATION", cut, "HumanMedicalMonitor",
            {"escalations_count": len(escalations), "decisions": len(monitor_decisions)}
        ))

        # NODE 6: EXECUTE
        # Executes approved actions only
        executed_actions, unresolved_items = self.node_6_execute(monitor_decisions, escalations, cut)
        cycle_audit.append(self._log_audit(
            "EXECUTION_CYCLE", cut, "ExecutionEngine",
            {"executed": len(executed_actions), "unresolved": len(unresolved_items)}
        ))

        return ReviewReport(
            cut=cut,
            protocol_version=protocol_version,
            detected_findings=detected_findings,
            medical_assessments=medical_assessments,
            data_queries=data_queries,
            compliance_results=compliance_results,
            escalations=escalations,
            monitor_decisions=monitor_decisions,
            executed_actions=executed_actions,
            unresolved_items=unresolved_items,
            audit_trace=cycle_audit
        )

    # 1. DETECT NODE
    def node_1_detect(self, cut: int, protocol_version: int) -> List[Dict[str, Any]]:
        findings = []

        # Question 1: Check Hy's Law via Atlas interface
        q_hys = Question(text="Which subjects meet the Hy's law criteria?", category="FINDING")
        ans_hys = self.atlas.answer(q_hys)

        for subj_finding in ans_hys.result:
            findings.append({
                "finding_id": f"FND_HYS_{subj_finding['subject_id']}_{cut}",
                "type": "CLINICAL_SAFETY_HYS_LAW",
                "category": "CLINICAL_SIGNAL",
                "subject_id": subj_finding["subject_id"],
                "site": subj_finding.get("site"),
                "description": f"Potential Hy's law criteria: {subj_finding['transaminase']}; Bilirubin: {subj_finding['bilirubin']}",
                "evidence_record_ids": subj_finding.get("evidence_record_ids", []),
                "cut": cut,
                "protocol_version": protocol_version
            })

        # Question 2: Check for Dosing Deviations via Atlas interface
        q_dose = Question(text="Which subjects received a wrong dose?", category="TRAP")
        ans_dose = self.atlas.answer(q_dose)
        for d in ans_dose.result:
            findings.append({
                "finding_id": f"FND_DOSE_{d['subject_id']}_{cut}",
                "type": "DOSING_DEVIATION",
                "category": "COMPLIANCE_SIGNAL",
                "subject_id": d["subject_id"],
                "site": d.get("site"),
                "description": f"Wrong dose: administered {d.get('dose_amount')} mg vs planned {d.get('planned_dose')} mg",
                "evidence_record_ids": [d.get("record_id")],
                "cut": cut,
                "protocol_version": protocol_version
            })

        # Check for Lab Unit Corruption / Flags in Atlas records
        for rec_id, rec in self.atlas.graph.records_by_id.items():
            if rec.get("cut") == cut and rec.get("unit_flag"):
                findings.append({
                    "finding_id": f"FND_UNIT_{rec_id}_{cut}",
                    "type": "LAB_UNIT_AMBIGUITY",
                    "category": "DATA_QUALITY",
                    "subject_id": rec.get("subject_id"),
                    "site": rec.get("site"),
                    "description": f"Unrecognized or corrupted unit '{rec.get('original_unit')}' for {rec.get('test_name')} (raw value: {rec.get('original_value')})",
                    "evidence_record_ids": [rec_id],
                    "cut": cut,
                    "protocol_version": protocol_version
                })

        return findings

    # 2. MEDICAL REVIEW NODE
    def node_2_medical_review(self, findings: List[Dict[str, Any]], cut: int) -> List[Dict[str, Any]]:
        assessments = []

        for f in findings:
            cat = f.get("category")
            f_type = f.get("type")
            rec_ids = f.get("evidence_record_ids", [])
            subj_id = f.get("subject_id")

            # Check if this exact finding was previously rejected and has no new evidence
            finding_sig = f"{f_type}_{subj_id}_{''.join(sorted(rec_ids))}"
            if finding_sig in self.rejected_findings_history:
                assessments.append({
                    "finding_id": f["finding_id"],
                    "seriousness": "LOW",
                    "plausibility": "PREVIOUSLY_REJECTED",
                    "clinical_relevance": "DOWNGRADED_TO_MONITORING",
                    "requires_escalation": False,
                    "is_data_quality": False,
                    "explanation": "Previously rejected by Medical Monitor; retained in routine surveillance without re-escalation.",
                    "evidence_records": rec_ids
                })
                continue

            if cat == "DATA_QUALITY" or f_type == "LAB_UNIT_AMBIGUITY":
                # Data-quality problem: must NOT automatically become a medical emergency
                assessments.append({
                    "finding_id": f["finding_id"],
                    "seriousness": "DATA_QUALITY_ISSUE",
                    "plausibility": "SUSPECTED_LABORATORY_UNIT_ERROR",
                    "clinical_relevance": "NON_EMERGENCY_DATA_DEFECT",
                    "requires_escalation": False,
                    "is_data_quality": True,
                    "explanation": "Laboratory measurement contains anomalous unit notation. Classified as data-quality defect for site query rather than drug-induced liver injury.",
                    "evidence_records": rec_ids,
                    "site": f.get("site"),
                    "subject_id": subj_id
                })

            elif f_type == "CLINICAL_SAFETY_HYS_LAW":
                # True potential clinical signal
                assessments.append({
                    "finding_id": f["finding_id"],
                    "seriousness": "CRITICAL",
                    "plausibility": "HIGH",
                    "clinical_relevance": "POTENTIAL_SEVERE_DRUG_INDUCED_LIVER_INJURY",
                    "requires_escalation": True,
                    "is_data_quality": False,
                    "explanation": "Subject exhibits concurrent transaminase >3x ULN with bilirubin >2x ULN and normal ALP. Meets Hy's law criteria. Urgent escalation to Medical Monitor required.",
                    "evidence_records": rec_ids,
                    "site": f.get("site"),
                    "subject_id": subj_id
                })

            else:
                # Dosing / compliance
                assessments.append({
                    "finding_id": f["finding_id"],
                    "seriousness": "MODERATE",
                    "plausibility": "MODERATE",
                    "clinical_relevance": "PROTOCOL_DOSING_NONCOMPLIANCE",
                    "requires_escalation": True,
                    "is_data_quality": False,
                    "explanation": "Dosing deviation recorded against planned protocol regimen.",
                    "evidence_records": rec_ids,
                    "site": f.get("site"),
                    "subject_id": subj_id
                })

        return assessments

    # 3. DATA MANAGER NODE
    def node_3_data_manager(self, assessments: List[Dict[str, Any]], cut: int) -> List[Dict[str, Any]]:
        new_queries = []

        for ass in assessments:
            if not ass.get("is_data_quality"):
                continue

            site = ass.get("site") or "UNKNOWN_SITE"
            subj = ass.get("subject_id")
            rec_ids = ass.get("evidence_records", [])

            # Deterministic Deduplication Signature
            dedup_key = f"{site}_{subj}_{ass.get('finding_id')}"
            if dedup_key in self.existing_queries:
                continue

            query = {
                "query_id": f"QRY_{cut}_{len(self.existing_queries) + 1}",
                "site": site,
                "subject_id": subj,
                "domain": "laboratory",
                "record_ids": rec_ids,
                "specific_question": f"Please verify the reported measurement unit and calibration for record(s) {', '.join(rec_ids)}. Anomalous unit detected.",
                "reason": ass.get("explanation"),
                "priority": "HIGH",
                "status": "OPEN",
                "created_cut": cut,
                "created_at": datetime.now().isoformat()
            }

            self.existing_queries[dedup_key] = query
            new_queries.append(query)

        return new_queries

    # 4. COMPLIANCE NODE
    def node_4_compliance(self, cut: int, protocol_version: int) -> List[Dict[str, Any]]:
        compliance_results = []

        # Check visit window compliance
        visits = self.atlas.graph.records_by_domain.get("visits", [])
        for v in visits:
            if v.get("cut") == cut:
                raw = v.get("raw_data", {})
                target_day = raw.get("target_day")
                actual_day = raw.get("actual_day")
                if target_day is not None and actual_day is not None:
                    try:
                        deviation = abs(float(actual_day) - float(target_day))
                        allowed_window = 3.0  # +/- 3 days per protocol
                        is_compliant = deviation <= allowed_window
                        compliance_results.append({
                            "protocol_version": protocol_version,
                            "rule_id": "RULE_VISIT_WINDOW_01",
                            "rule_description": "Visits must occur within +/- 3 days of target protocol schedule",
                            "subject_id": v.get("subject_id"),
                            "effective_cut": cut,
                            "evidence": [v.get("record_id")],
                            "result": "PASS" if is_compliant else "DEVIATION",
                            "details": f"Target: Day {target_day}, Actual: Day {actual_day} (delta: {deviation} days)"
                        })
                    except (ValueError, TypeError):
                        pass

        # Check laboratory safety thresholds per protocol version
        alt_threshold_multiplier = 5.0 if protocol_version >= 2 else 3.0
        for subj_id, recs in self.atlas.graph.records_by_subject.items():
            labs = [r for r in recs if r.get("domain") == "laboratory" and r.get("cut") == cut]
            for l in labs:
                if l.get("test_name") == "ALT" and l.get("normalized_value") and l.get("uln"):
                    val = l["normalized_value"]
                    uln = l["uln"]
                    if val > alt_threshold_multiplier * uln:
                        compliance_results.append({
                            "protocol_version": protocol_version,
                            "rule_id": "RULE_LAB_ALT_STOPPING",
                            "rule_description": f"ALT > {alt_threshold_multiplier}x ULN triggers mandatory safety review (Protocol v{protocol_version})",
                            "subject_id": subj_id,
                            "effective_cut": cut,
                            "evidence": [l["record_id"]],
                            "result": "STOPPING_CRITERIA_TRIGGERED",
                            "details": f"ALT {val} U/L vs threshold {alt_threshold_multiplier * uln} U/L"
                        })

        return compliance_results

    # 5. HUMAN GATE NODE
    def node_5_human_gate(self, assessments: List[Dict[str, Any]], cut: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        current_escalations = []
        monitor_decisions = []

        for ass in assessments:
            if not ass.get("requires_escalation"):
                continue

            esc_id = f"ESC_{cut}_{len(self.escalations_store) + 1}"
            subj_id = ass.get("subject_id")
            finding_id = ass.get("finding_id")

            # Check if this escalation already exists in store
            existing = None
            for e in self.escalations_store.values():
                if e.get("finding_id") == finding_id:
                    existing = e
                    break

            if not existing:
                esc = {
                    "escalation_id": esc_id,
                    "finding_id": finding_id,
                    "subject_id": subj_id,
                    "site": ass.get("site"),
                    "cut": cut,
                    "clinical_relevance": ass.get("clinical_relevance"),
                    "explanation": ass.get("explanation"),
                    "evidence_records": ass.get("evidence_records"),
                    "status": "PENDING",  # Default: PENDING. Never auto-approved!
                    "decision": None,
                    "decision_reason": None,
                    "decision_timestamp": None,
                    "created_at": datetime.now().isoformat()
                }
                self.escalations_store[esc_id] = esc
                current_escalations.append(esc)
            else:
                current_escalations.append(existing)

        # Check for any decisions registered in the store for current or past escalations
        for esc in self.escalations_store.values():
            if esc.get("status") in ("APPROVED", "REJECTED"):
                monitor_decisions.append({
                    "escalation_id": esc["escalation_id"],
                    "decision": esc["status"],
                    "reason": esc.get("decision_reason"),
                    "timestamp": esc.get("decision_timestamp"),
                    "finding_id": esc.get("finding_id")
                })

        return current_escalations, monitor_decisions

    # 6. EXECUTE NODE
    def node_6_execute(
        self,
        monitor_decisions: List[Dict[str, Any]],
        escalations: List[Dict[str, Any]],
        cut: int
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        executed = []
        unresolved = []

        for esc in escalations:
            status = esc.get("status")
            esc_id = esc.get("escalation_id")

            if status == "APPROVED":
                executed.append({
                    "action_id": f"ACT_{esc_id}",
                    "escalation_id": esc_id,
                    "action_type": "CLINICAL_HOLD_AND_IMMEDIATE_SITE_AUDIT",
                    "subject_id": esc.get("subject_id"),
                    "executed_at": datetime.now().isoformat(),
                    "evidence": esc.get("evidence_records"),
                    "status": "EXECUTED"
                })
            elif status == "REJECTED":
                # Downgrade to routine monitoring; record in history
                self.rejected_findings_history.add(
                    f"{esc.get('finding_id')}_{esc.get('subject_id')}_{''.join(sorted(esc.get('evidence_records', [])))}"
                )
                executed.append({
                    "action_id": f"ACT_DOWNGRADE_{esc_id}",
                    "escalation_id": esc_id,
                    "action_type": "DOWNGRADE_TO_MONITORING",
                    "subject_id": esc.get("subject_id"),
                    "reason": esc.get("decision_reason", "Medical Monitor rejected escalation"),
                    "executed_at": datetime.now().isoformat(),
                    "status": "MONITORING_ONLY"
                })
            else:
                # PENDING / UNRESOLVED
                unresolved.append({
                    "escalation_id": esc_id,
                    "subject_id": esc.get("subject_id"),
                    "status": "PENDING_MONITOR_DECISION",
                    "explanation": "Human medical monitor decision has not yet been rendered. Strict safety protocol prevents automated approval."
                })

        return executed, unresolved
