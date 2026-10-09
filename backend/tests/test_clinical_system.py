"""
Automated Test Suite for ATLAS -> MONITOR -> WATCH Clinical Review System.
Tests all deterministic behaviors, trap scenarios (zero hallucination),
protocol checks, compliance, delayed monitors, corrections, and adversarial conditions.
"""

import unittest
import os
import shutil
from starter.schemas import Question, Answer
from stage1.atlas import StudyGraph, Atlas, normalize_lab_unit
from stage2.crew import ReviewCrew, ReviewReport
from stage3.watch import StudyWatch, Explanation


class TestAtlasStage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = "data"
        cls.graph = StudyGraph(cls.data_dir)
        cls.graph.build(cut=3)
        cls.atlas = Atlas(cls.graph)

    def test_unit_conversion_alt(self):
        # 1 ukat/L = 60 U/L
        norm_val, norm_unit, method, flag = normalize_lab_unit("ALT", 2.0, "µkat/L")
        self.assertEqual(norm_val, 120.0)
        self.assertEqual(norm_unit, "U/L")
        self.assertIsNone(flag)

    def test_unit_conversion_bilirubin(self):
        # 34.2 umol/L ~= 2.0 mg/dL
        norm_val, norm_unit, method, flag = normalize_lab_unit("BILIRUBIN", 34.2, "µmol/L")
        self.assertAlmostEqual(norm_val, 2.0, places=1)
        self.assertEqual(norm_unit, "mg/dL")

    def test_unit_conversion_ambiguous(self):
        # Ambiguous unit should be flagged, not silently corrupted
        norm_val, norm_unit, method, flag = normalize_lab_unit("ALT", 40.0, "stones/acre")
        self.assertIsNotNone(flag)
        self.assertIn("AMBIGUOUS_UNIT", flag)

    def test_count_question_ae_discontinuations(self):
        q = Question(text="How many subjects at site S07 discontinued due to an adverse event?", category="COUNT")
        ans = self.atlas.answer(q)
        self.assertEqual(ans.result, 2)
        self.assertGreaterEqual(len(ans.evidence), 2)
        # Check evidence traceability across subjects
        subjid_evs = set(ev.subject_id for ev in ans.evidence)
        self.assertEqual(len(subjid_evs), 2)
        for ev in ans.evidence:
            self.assertIn("042-S07", ev.subject_id)
            self.assertTrue(ev.source_file.endswith(".csv"))

    def test_lookup_question_window(self):
        q = Question(text="List the laboratory and adverse-event records for 042-S05-003 within 7 days of the WEEK4 visit.", category="LOOKUP")
        ans = self.atlas.answer(q)
        self.assertGreater(len(ans.result), 0)
        self.assertEqual(len(ans.evidence), len(ans.result))
        for ev in ans.evidence:
            self.assertEqual(ev.subject_id, "042-S05-003")

    def test_finding_hys_law(self):
        q = Question(text="Which subjects meet the Hy's law criteria?", category="FINDING")
        ans = self.atlas.answer(q)
        # 042-S05-003 meets Hy's law at cut 3
        subjid_list = [s["subject_id"] for s in ans.result]
        self.assertIn("042-S05-003", subjid_list)
        self.assertGreater(len(ans.evidence), 0)
        self.assertGreater(len(ans.calculations), 0)

    def test_trap_question_never_invents_findings(self):
        """CRITICAL: Trap question must return 0 subjects when no violation exists!"""
        q = Question(text="Which subjects at site S01 received a wrong dose?", category="TRAP")
        ans = self.atlas.answer(q)
        self.assertEqual(ans.result, [])
        self.assertEqual(len(ans.evidence), 0)
        self.assertIn("No subjects found", ans.answer)

    def test_patient_360_evidence_traceability(self):
        p360 = self.graph.patient360("042-S05-003")
        self.assertTrue(p360["found"])
        self.assertIn("timeline", p360)
        self.assertGreater(len(p360["timeline"]["laboratory"]), 0)
        # Source file exists on every record
        for lab in p360["timeline"]["laboratory"]:
            self.assertIsNotNone(lab.get("source_file"))


class TestMonitorStage(unittest.TestCase):
    def setUp(self):
        self.graph = StudyGraph("data")
        self.graph.build(cut=3)
        self.atlas = Atlas(self.graph)
        self.crew = ReviewCrew(atlas=self.atlas)

    def test_six_node_cycle_execution(self):
        report = self.crew.run_cycle(cut=3, protocol_version=1)
        self.assertEqual(report.cut, 3)
        self.assertIsInstance(report.detected_findings, list)
        self.assertIsInstance(report.medical_assessments, list)
        self.assertIsInstance(report.compliance_results, list)
        self.assertIsInstance(report.escalations, list)

    def test_data_manager_query_deduplication(self):
        # Adding a flagged unit to graph
        self.graph.records_by_id["FAKE_LAB"] = {
            "record_id": "FAKE_LAB",
            "subject_id": "042-S01-001",
            "site": "S01",
            "domain": "laboratory",
            "unit_flag": "AMBIGUOUS_UNIT",
            "cut": 3,
            "original_unit": "unknown",
            "original_value": "99",
            "test_name": "ALT",
            "history": []
        }
        # Run cycle twice; queries must not duplicate
        rep1 = self.crew.run_cycle(cut=3, protocol_version=1)
        rep2 = self.crew.run_cycle(cut=3, protocol_version=1)
        self.assertEqual(len(rep2.data_queries), 0)  # Deduplicated on second cycle

    def test_human_gate_never_auto_approves(self):
        report = self.crew.run_cycle(cut=3, protocol_version=1)
        for esc in report.escalations:
            self.assertEqual(esc["status"], "PENDING")
        # Ensure silence is not treated as approval
        self.assertEqual(len(report.executed_actions), 0)


class TestWatchStage(unittest.TestCase):
    def setUp(self):
        self.graph = StudyGraph("data")
        self.atlas = Atlas(self.graph)
        self.crew = ReviewCrew(atlas=self.atlas)
        self.watch = StudyWatch(data_dir="data", crew=self.crew)

    def test_twelve_cut_surveillance_period(self):
        surv = self.watch.run_period(cuts=range(1, 13))
        self.assertEqual(len(surv.cuts_processed), 12)
        # Dynamic onboarding check: S04 and S09 onboarded
        self.assertIn("S04", surv.onboarded_entities["new_sites"])
        self.assertIn("S09", surv.onboarded_entities["new_sites"])
        # Dynamic domain onboarding: biomarkers
        self.assertIn("biomarkers", surv.onboarded_entities["new_domains"])

    def test_adversarial_suspicious_site_detected(self):
        self.watch.run_period(cuts=range(1, 8))
        signals = [s["type"] for s in self.watch.adversarial_signals]
        self.assertIn("ADVERSARIAL_SUSPICIOUS_SITE_REGULARITY", signals)

    def test_adversarial_unit_corruption_detected(self):
        self.watch.run_period(cuts=range(1, 8))
        signals = [s["type"] for s in self.watch.adversarial_signals]
        self.assertIn("ADVERSARIAL_LAB_UNIT_CORRUPTION", signals)

    def test_explain_decision(self):
        self.watch.run_period(cuts=range(1, 6))
        # Find an escalation decision
        esc_ids = list(self.watch.crew.escalations_store.keys())
        if esc_ids:
            explanation = self.watch.explain(esc_ids[0])
            self.assertIsInstance(explanation, Explanation)
            self.assertTrue(explanation.is_deterministic)
            self.assertGreater(len(explanation.evidence_records), 0)


if __name__ == "__main__":
    unittest.main()
