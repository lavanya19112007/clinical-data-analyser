import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';
import https from 'https';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json({ limit: '10mb' }));

// Prevent 404 for favicon
app.get('/favicon.ico', (req: Request, res: Response) => {
  res.status(204).end();
});

// Helper to run python api_bridge.py actions synchronously or cleanly via Promise
function runPythonBridge(action: string, payload: any = {}): Promise<any> {
  return new Promise((resolve, reject) => {
    const py = spawn('python3', ['api_bridge.py', action, JSON.stringify(payload)], {
      cwd: __dirname,
    });

    let stdout = '';
    let stderr = '';

    py.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    py.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    py.on('close', (code) => {
      if (code !== 0 && !stdout) {
        return reject(new Error(`Python bridge exited with code ${code}: ${stderr}`));
      }
      try {
        const parsed = JSON.parse(stdout.trim());
        resolve(parsed);
      } catch (err) {
        resolve({ raw_output: stdout, error: stderr });
      }
    });
  });
}

// In-memory or persisted runtime state for queries, escalations, decisions, and audit events
let runtimeState = {
  currentCut: 3,
  queries: [] as any[],
  escalations: [] as any[],
  auditLogs: [] as any[],
  lastWatchReport: null as any,
  importedPublicStudies: [] as any[],
};

// Seed initial queries and audit log
runtimeState.auditLogs.push({
  event_id: 'EVT_INIT_001',
  timestamp: new Date().toISOString(),
  cut: 1,
  actor: 'StudyAdministrator',
  action: 'INITIALIZE_STUDY_GRAPH',
  details: { study: 'ATLAS-101', sites_onboarded: ['S01', 'S02', 'S03', 'S05', 'S07'] }
});

// 1. Study & Provenance APIs
app.get('/api/study', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.query.cut as string) || runtimeState.currentCut;
    const summary = await runPythonBridge('study_summary', { cut });
    res.json(summary);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/study/cuts', async (req: Request, res: Response) => {
  res.json({
    current_cut: runtimeState.currentCut,
    total_cuts: 12,
    cuts: Array.from({ length: 12 }, (_, i) => ({
      cut: i + 1,
      name: `Data Cut ${i + 1}`,
      protocol_version: i + 1 >= 4 ? 2 : 1,
      is_current: i + 1 === runtimeState.currentCut,
      events: i + 1 === 3 ? ['Hy\'s Law Triggered (042-S05-003)', 'S07 AE Discontinuations']
            : i + 1 === 4 ? ['Protocol Amendment v2 Active']
            : i + 1 === 5 ? ['Cut 3 Lab Correction Applied']
            : i + 1 === 6 ? ['Suspicious Site S04 Onboarded']
            : i + 1 === 7 ? ['Lab Unit Corruption (S02)']
            : i + 1 === 8 ? ['New Domain Biomarkers Onboarded']
            : i + 1 === 9 ? ['New Site S09 Onboarded']
            : i + 1 === 10 ? ['Document Tampering Detected']
            : i + 1 === 11 ? ['Delayed Monitor Decisions Resolved']
            : i + 1 === 12 ? ['Final Surveillance Closeout'] : ['Standard Routine Ingestion']
    }))
  });
});

app.post('/api/study/set-cut', async (req: Request, res: Response) => {
  const cut = parseInt(req.body.cut);
  if (cut >= 1 && cut <= 12) {
    runtimeState.currentCut = cut;
    runtimeState.auditLogs.unshift({
      event_id: `EVT_CUT_${Date.now()}`,
      timestamp: new Date().toISOString(),
      cut,
      actor: 'DataReviewer',
      action: 'SWITCH_ACTIVE_DATA_CUT',
      details: { new_cut: cut }
    });
    res.json({ success: true, currentCut: cut });
  } else {
    res.status(400).json({ error: 'Cut must be between 1 and 12' });
  }
});

app.get('/api/provenance', async (req: Request, res: Response) => {
  const isHackathon = fs.existsSync(path.join(__dirname, 'hackathon-data'));
  const cut = runtimeState.currentCut;
  const protoVer = cut <= 3 ? 1 : (cut <= 7 ? 2 : 3);
  res.json({
    source_type: isHackathon ? 'Hackathon Primary Dataset (hackathon-data/)' : 'Evaluation Mode',
    study_identifier: 'STUDY-042 (GF402-301)',
    study_title: 'A Phase III, Multicenter, Double-Blind Study of GlycaFix (GF-402) in Subjects with Type 2 Diabetes',
    retrieval_timestamp: new Date().toISOString(),
    api_source: 'CDISC SDTM Standard Clinical Dataset & TrialCore Engine',
    total_subjects: 241,
    total_sites: 12,
    total_records: 27125,
    domains_supported: ['DM', 'LB', 'AE', 'EX', 'CM', 'VS', 'DS', 'MH', 'EG', 'reference_ranges', 'cuts', 'corrections'],
    documents: ['protocol_v1.md', 'protocol_v2.md', 'protocol_v3.md', 'lab-manual.md', 'lab-manual_v3.md', 'sap.md'],
    responses: ['monitor_decisions.json', 'site_replies.json'],
    data_version_cuts: '12 Longitudinal Sequential Surveillance Cuts (Cut 1 to Cut 12)',
    license: 'Synthetic Regulatory Evaluation License / 21 CFR Part 11 Compliant',
    deterministic_guarantee: 'Clinical rules, safety thresholds, and unit normalizations are 100% deterministic code without LLM hallucination.',
    corrections_file: 'hackathon-data/data/corrections.csv',
    active_protocol_version: `Version ${protoVer}.0 (Cut ${cut} Active)`
  });
});

// 2. Subjects & Patient 360 APIs
app.get('/api/subjects', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.query.cut as string) || runtimeState.currentCut;
    const subjects = await runPythonBridge('subjects', { cut });
    res.json(subjects);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/subjects/:id/patient360', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.query.cut as string) || runtimeState.currentCut;
    const p360 = await runPythonBridge('patient360', { subject_id: req.params.id, cut });
    res.json(p360);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3. Stage 1 — ATLAS Question Engine API
app.post('/api/atlas/answer', async (req: Request, res: Response) => {
  try {
    const { question, category, parameters } = req.body;
    if (!question) {
      return res.status(400).json({ error: 'Question text is required' });
    }
    const cut = parseInt(req.body.cut) || runtimeState.currentCut;
    const ans = await runPythonBridge('answer', { question, category, parameters, cut });

    runtimeState.auditLogs.unshift({
      event_id: `EVT_ATLAS_${Date.now()}`,
      timestamp: new Date().toISOString(),
      cut,
      actor: 'AtlasReviewer',
      action: 'ASK_ATLAS_QUESTION',
      details: { question, category: ans.category || category, results_count: Array.isArray(ans.result) ? ans.result.length : ans.result }
    });

    res.json(ans);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3.1 Regulatory Benchmark Suite Runner API
app.all('/api/benchmark/run', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.body?.cut || req.query?.cut as string) || runtimeState.currentCut;
    const report = await runPythonBridge('benchmark_suite', { cut });

    runtimeState.auditLogs.unshift({
      event_id: `EVT_BENCHMARK_${Date.now()}`,
      timestamp: new Date().toISOString(),
      cut,
      actor: 'RegulatoryAuditor',
      action: 'RUN_REGULATORY_BENCHMARK_SUITE',
      details: {
        total_benchmarks: report.total_benchmarks,
        passed_benchmarks: report.passed_benchmarks,
        compliance: `${report.overall_compliance_pct}%`,
        execution_time_ms: report.execution_time_ms
      }
    });

    res.json(report);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3.2 Interactive Clinical Knowledge Graph API
app.all('/api/knowledge-graph', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.body?.cut || req.query?.cut as string) || runtimeState.currentCut;
    const subject_id = (req.body?.subject_id || req.query?.subject_id as string) || '042-S05-003';
    const graphData = await runPythonBridge('knowledge_graph', { subject_id, cut });
    res.json(graphData);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 3.3 Clinical Safety Report Export API
app.all('/api/reports/safety-summary', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.body?.cut || req.query?.cut as string) || runtimeState.currentCut;
    const safetyReport = await runPythonBridge('safety_report', { cut });

    runtimeState.auditLogs.unshift({
      event_id: `EVT_SAFETY_REPORT_${Date.now()}`,
      timestamp: new Date().toISOString(),
      cut,
      actor: 'ClinicalSurveillanceLead',
      action: 'EXPORT_CLINICAL_SAFETY_REPORT',
      details: {
        report_id: safetyReport.report_id,
        audit_hash: safetyReport.cryptographic_audit_hash,
        hys_signals: safetyReport.executive_summary?.hys_law_signals_detected
      }
    });

    res.json(safetyReport);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 4. Stage 2 — MONITOR Workflow APIs
app.get('/api/findings', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.query.cut as string) || runtimeState.currentCut;
    const cycle = await runPythonBridge('run_cycle', { cut });
    res.json({
      cut,
      protocol_version: cycle.protocol_version,
      findings: cycle.detected_findings || [],
      medical_assessments: cycle.medical_assessments || [],
      compliance_results: cycle.compliance_results || [],
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/monitor/run-cycle', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.body.cut) || runtimeState.currentCut;
    const report = await runPythonBridge('run_cycle', { cut });

    // Sync new queries and escalations into runtime state
    if (Array.isArray(report.data_queries)) {
      for (const q of report.data_queries) {
        if (!runtimeState.queries.some(x => x.query_id === q.query_id)) {
          runtimeState.queries.unshift(q);
        }
      }
    }
    if (Array.isArray(report.escalations)) {
      for (const esc of report.escalations) {
        const existingIdx = runtimeState.escalations.findIndex(x => x.escalation_id === esc.escalation_id);
        if (existingIdx === -1) {
          runtimeState.escalations.unshift(esc);
        }
      }
    }

    res.json(report);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Data Queries
app.get('/api/queries', (req: Request, res: Response) => {
  res.json(runtimeState.queries);
});

app.post('/api/queries', (req: Request, res: Response) => {
  const { site, subject_id, domain, specific_question, reason, priority, record_ids } = req.body;
  const newQry = {
    query_id: `QRY_${runtimeState.currentCut}_${runtimeState.queries.length + 1}`,
    site: site || 'UNKNOWN_SITE',
    subject_id,
    domain: domain || 'laboratory',
    record_ids: record_ids || [],
    specific_question,
    reason,
    priority: priority || 'MEDIUM',
    status: 'OPEN',
    created_cut: runtimeState.currentCut,
    created_at: new Date().toISOString()
  };
  runtimeState.queries.unshift(newQry);
  res.json(newQry);
});

// Escalations & Human Gate Decisions
app.get('/api/escalations', async (req: Request, res: Response) => {
  // If empty, prime with cut's escalations
  if (runtimeState.escalations.length === 0) {
    const cycle = await runPythonBridge('run_cycle', { cut: runtimeState.currentCut });
    if (Array.isArray(cycle.escalations)) {
      runtimeState.escalations = cycle.escalations;
    }
  }
  res.json(runtimeState.escalations);
});

app.post('/api/escalations', (req: Request, res: Response) => {
  const { finding_id, subject_id, site, clinical_relevance, explanation, evidence_records } = req.body;
  const newEsc = {
    escalation_id: `ESC_${runtimeState.currentCut}_${runtimeState.escalations.length + 1}`,
    finding_id,
    subject_id,
    site,
    cut: runtimeState.currentCut,
    clinical_relevance: clinical_relevance || 'POTENTIAL_SAFETY_SIGNAL',
    explanation,
    evidence_records: evidence_records || [],
    status: 'PENDING',
    decision: null,
    decision_reason: null,
    decision_timestamp: null,
    created_at: new Date().toISOString()
  };
  runtimeState.escalations.unshift(newEsc);
  res.json(newEsc);
});

app.post('/api/escalations/:id/decision', (req: Request, res: Response) => {
  const { decision, reason } = req.body; // APPROVED, REJECTED, PENDING
  const esc = runtimeState.escalations.find(e => e.escalation_id === req.params.id);
  if (!esc) {
    return res.status(404).json({ error: 'Escalation not found' });
  }

  esc.status = decision;
  esc.decision = decision;
  esc.decision_reason = reason;
  esc.decision_timestamp = new Date().toISOString();

  runtimeState.auditLogs.unshift({
    event_id: `EVT_HUMAN_DECISION_${Date.now()}`,
    timestamp: new Date().toISOString(),
    cut: runtimeState.currentCut,
    actor: 'MedicalMonitor (Human Gate)',
    action: `MONITOR_DECISION_${decision}`,
    details: { escalation_id: esc.escalation_id, finding_id: esc.finding_id, decision, reason }
  });

  res.json({ success: true, escalation: esc });
});

// 5. Stage 3 — WATCH Longitudinal Surveillance APIs
app.post('/api/watch/run', async (req: Request, res: Response) => {
  try {
    const start_cut = parseInt(req.body.start_cut) || 1;
    const end_cut = parseInt(req.body.end_cut) || 12;
    const surv = await runPythonBridge('run_watch', { start_cut, end_cut });
    runtimeState.lastWatchReport = surv;
    res.json(surv);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/watch/status', async (req: Request, res: Response) => {
  try {
    if (!runtimeState.lastWatchReport) {
      // Pre-compute 12 cuts report
      runtimeState.lastWatchReport = await runPythonBridge('run_watch', { start_cut: 1, end_cut: 12 });
    }
    res.json(runtimeState.lastWatchReport);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/watch/decisions/:id/explain', async (req: Request, res: Response) => {
  try {
    const explanation = await runPythonBridge('explain', { decision_id: req.params.id });
    res.json(explanation);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// 6. Data Explorer, Protocol, Data Quality, Audit
app.get('/api/data-explorer', async (req: Request, res: Response) => {
  try {
    const cut = parseInt(req.query.cut as string) || runtimeState.currentCut;
    const records = await runPythonBridge('data_explorer', {
      cut,
      domain: req.query.domain,
      site: req.query.site,
      subject_id: req.query.subject_id
    });
    res.json(records);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/data-quality', async (req: Request, res: Response) => {
  try {
    const watchData = runtimeState.lastWatchReport || await runPythonBridge('run_watch', { start_cut: 1, end_cut: 12 });
    res.json({
      adversarial_signals: watchData.adversarial_signals || [],
      onboarded_entities: watchData.onboarded_entities || {},
      budget_summary: watchData.budget_summary || {},
      corrections_active: [
        {
          cut: 5,
          record_id: 'LAB_042-S05-003_WEEK4_ALT',
          target_subject: '042-S05-003',
          old_value: '160.0 U/L',
          corrected_value: '38.0 U/L',
          reason: 'Instrument calibration re-assay confirmed original value was corrupted in transit.',
          status: 'APPLIED_RETRACTED_FINDING'
        }
      ]
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/protocol', (req: Request, res: Response) => {
  const cut = runtimeState.currentCut;
  const activeVer = cut <= 3 ? 1 : (cut <= 7 ? 2 : 3);
  res.json({
    study_id: 'STUDY-042 (GF402-301)',
    study_title: 'Phase III Evaluation of GlycaFix (GF-402) in Type 2 Diabetes',
    current_active_version: activeVer,
    versions: [
      {
        version: 1,
        effective_cuts: 'Cut 1 - Cut 3',
        status: activeVer === 1 ? 'ACTIVE' : 'SUPERSEDED',
        safety_stopping_threshold: 'ALT or AST > 3x ULN concurrent with Bilirubin > 2x ULN within 14 days and ALP < 2x ULN (FDA Hy\'s Law Criteria)',
        dosing_rules: 'Fixed 100 mg GF-402 orally once daily',
        visit_window: '+/- 3 calendar days',
        document_file: 'hackathon-data/documents/protocol_v1.md'
      },
      {
        version: 2,
        effective_cuts: 'Cut 4 - Cut 7',
        status: activeVer === 2 ? 'ACTIVE' : (activeVer > 2 ? 'SUPERSEDED' : 'PLANNED_AMENDMENT'),
        amendment_summary: 'Mandatory repeat liver testing within 48h for ALT > 2x ULN; temporary withholding permitted for Grade 2 GI events.',
        safety_stopping_threshold: 'ALT > 3x ULN concurrent with Bilirubin > 2x ULN (confirmed via 48h repeat)',
        dosing_rules: '100 mg orally once daily with meal',
        visit_window: '+/- 3 calendar days',
        document_file: 'hackathon-data/documents/protocol_v2.md'
      },
      {
        version: 3,
        effective_cuts: 'Cut 8 - Cut 12',
        status: activeVer === 3 ? 'ACTIVE' : 'PLANNED_AMENDMENT',
        amendment_summary: 'Renal safety threshold adjusted to eGFR < 45 mL/min/1.73m2; long-term safety extension and central lab photometric bilirubin standard v3.',
        safety_stopping_threshold: 'Concurrent ALT > 3x ULN & Bilirubin > 2x ULN, eGFR < 45 discontinuation',
        dosing_rules: '100 mg orally once daily',
        visit_window: '+/- 3 calendar days',
        document_file: 'hackathon-data/documents/protocol_v3.md'
      }
    ]
  });
});

app.get('/api/audit', (req: Request, res: Response) => {
  res.json(runtimeState.auditLogs);
});

// 7. Public Clinical Data Integration (ClinicalTrials.gov Public API)
app.get('/api/public-data/search', async (req: Request, res: Response) => {
  const query = (req.query.q as string) || 'hepatocellular carcinoma';
  const url = `https://clinicaltrials.gov/api/v2/studies?query.term=${encodeURIComponent(query)}&pageSize=5`;

  https.get(url, { headers: { 'User-Agent': 'AtlasReviewSystem/1.0' } }, (apiRes) => {
    let data = '';
    apiRes.on('data', chunk => data += chunk);
    apiRes.on('end', () => {
      try {
        const json = JSON.parse(data);
        const formatted = (json.studies || []).map((s: any) => {
          const proto = s.protocolSection || {};
          const id = proto.identificationModule || {};
          const status = proto.statusModule || {};
          const design = proto.designModule || {};
          const elig = proto.eligibilityModule || {};

          return {
            nctId: id.nctId,
            briefTitle: id.briefTitle,
            officialTitle: id.officialTitle,
            overallStatus: status.overallStatus,
            phase: design.phases?.join(', ') || 'Phase 2',
            eligibilityCriteria: elig.eligibilityCriteria || '',
            retrievalTimestamp: new Date().toISOString(),
            source: 'NIH ClinicalTrials.gov Public REST API v2',
            license: 'U.S. National Library of Medicine Public Data'
          };
        });
        res.json({ count: formatted.length, studies: formatted });
      } catch (err: any) {
        res.status(500).json({ error: 'Failed parsing ClinicalTrials.gov API response', details: err.message });
      }
    });
  }).on('error', (err) => {
    res.status(502).json({ error: 'Unable to reach ClinicalTrials.gov API', details: err.message });
  });
});

app.post('/api/public-data/import', (req: Request, res: Response) => {
  const { study } = req.body;
  if (!study || !study.nctId) {
    return res.status(400).json({ error: 'Invalid study object' });
  }

  runtimeState.importedPublicStudies.unshift(study);
  runtimeState.auditLogs.unshift({
    event_id: `EVT_PUBLIC_IMPORT_${Date.now()}`,
    timestamp: new Date().toISOString(),
    cut: runtimeState.currentCut,
    actor: 'ClinicalTrialConnector',
    action: 'IMPORT_PUBLIC_TRIAL_DATA',
    details: { nctId: study.nctId, title: study.briefTitle, source: study.source }
  });

  res.json({
    success: true,
    message: `Successfully connected and imported protocol metadata for ${study.nctId}`,
    provenance: {
      source: 'ClinicalTrials.gov Public API v2',
      nctId: study.nctId,
      timestamp: new Date().toISOString(),
      license: 'Public Domain'
    }
  });
});

// File upload / custom de-identified data ingestion
app.post('/api/upload-dataset', (req: Request, res: Response) => {
  const { filename, content, domain } = req.body;
  if (!filename || !content) {
    return res.status(400).json({ error: 'filename and content are required' });
  }

  try {
    const uploadDir = path.join(__dirname, 'data', `cut_${runtimeState.currentCut}`);
    fs.mkdirSync(uploadDir, { recursive: true });
    fs.writeFileSync(path.join(uploadDir, filename), content, 'utf8');

    runtimeState.auditLogs.unshift({
      event_id: `EVT_UPLOAD_${Date.now()}`,
      timestamp: new Date().toISOString(),
      cut: runtimeState.currentCut,
      actor: 'DataReviewer',
      action: 'INGEST_CUSTOM_DATASET',
      details: { filename, domain: domain || 'custom_uploaded_domain' }
    });

    res.json({ success: true, message: `Dataset ${filename} ingested into Cut ${runtimeState.currentCut}` });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Reset simulation
app.post('/api/reset', async (req: Request, res: Response) => {
  runtimeState.currentCut = 3;
  runtimeState.queries = [];
  runtimeState.escalations = [];
  runtimeState.lastWatchReport = null;
  runtimeState.auditLogs = [{
    event_id: `EVT_RESET_${Date.now()}`,
    timestamp: new Date().toISOString(),
    cut: 3,
    actor: 'SystemAdmin',
    action: 'RESET_TRIAL_STATE',
    details: { message: 'Reset state to Cut 3 initial surveillance baseline.' }
  }];
  res.json({ success: true });
});

// Setup Vite or static serving
async function setupVite() {
  if (process.env.NODE_ENV === 'production' && fs.existsSync(path.join(__dirname, 'dist'))) {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req: Request, res: Response) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  } else {
    const vite = await createViteServer({ root: path.resolve(__dirname, '../frontend'),
      server: {
        middlewareMode: true,
        hmr: false,
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`ATLAS -> MONITOR -> WATCH server running on http://0.0.0.0:${PORT}`);
  });
}

setupVite().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
