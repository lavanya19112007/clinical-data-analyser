import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  Clock,
  Layers,
  ArrowRight,
  X,
  Minimize2,
  Maximize2,
  Shield,
  Brain,
  Sliders,
  FileText
} from 'lucide-react';

interface JudgeWalkthroughProps {
  currentCut: number;
  onSetCut: (cut: number) => void;
  onSwitchTab: (tab: any) => void;
  onTriggerBenchmark?: () => void;
  onOpenSafetyReport?: () => void;
  onCloseWalkthrough: () => void;
}

export const JudgeWalkthroughDeck: React.FC<JudgeWalkthroughProps> = ({
  currentCut,
  onSetCut,
  onSwitchTab,
  onTriggerBenchmark,
  onOpenSafetyReport,
  onCloseWalkthrough
}) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [timerSeconds, setTimerSeconds] = useState<number>(180); // 3 minutes = 180s
  const [timerRunning, setTimerRunning] = useState<boolean>(false);
  const [isMinimized, setIsMinimized] = useState<boolean>(false);

  // Timer countdown
  useEffect(() => {
    let interval: any = null;
    if (timerRunning && timerSeconds > 0) {
      interval = setInterval(() => {
        setTimerSeconds((prev) => prev - 1);
      }, 1000);
    } else if (timerSeconds === 0) {
      setTimerRunning(false);
    }
    return () => clearInterval(interval);
  }, [timerRunning, timerSeconds]);

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const steps = [
    {
      step: 1,
      title: 'Canonical Ingestion & Cut-Aware Graph',
      subtitle: 'STUDY-042 Phase III Dataset: 241 Subjects, 12 Sites, 27,125 Records',
      talkingPoints: [
        'TrialCore Intelligence has fully ingested the official STUDY-042 canonical hackathon dataset (241 subjects, 12 sites, 27,125 records).',
        'Data cuts (Cut 1 to Cut 12) strictly prevent future data leakage. Notice how Cut 3 only exposes records available up to Cut 3.',
        'Units, SDTM domains (DM, LB, AE, EX, CM, VS, DS, MH, EG), and protocol amendments (v1, v2, v3) are preserved deterministically.'
      ],
      actionLabel: 'Switch to Cut 3 & Open Overview',
      executeAction: () => {
        onSetCut(3);
        onSwitchTab('overview');
      }
    },
    {
      step: 2,
      title: '1-Click Regulatory Benchmark Suite',
      subtitle: 'Deterministic COUNT, LOOKUP, FINDING & TRAP Verification',
      talkingPoints: [
        'Clinical AI must not hallucinate. Watch our 1-Click Regulatory Benchmark Runner test all 4 core clinical query archetypes in real-time.',
        'COUNT proves exactly 2 subjects at Site S07 discontinued due to adverse events.',
        'TRAP proves zero-hallucination: when querying Site S01 wrong doses, the engine returns 0 fabricated subjects, achieving 100% compliance!'
      ],
      actionLabel: 'Open ATLAS & Run Benchmark Suite',
      executeAction: () => {
        onSetCut(3);
        onSwitchTab('atlas');
        if (onTriggerBenchmark) {
          setTimeout(onTriggerBenchmark, 300);
        }
      }
    },
    {
      step: 3,
      title: 'Interactive Knowledge Graph & Hy\'s Law Causal Chain',
      subtitle: 'Connected Multi-Domain Graph: Subject 042-S05-003',
      talkingPoints: [
        'TrialCore is not a flat SQL wrapper; it is a connected clinical knowledge graph.',
        'Notice Subject 042-S05-003 at Visit WEEK4: ALT is 160 U/L (4x ULN) and Bilirubin is 2.8 mg/dL (2.3x ULN).',
        'The engine constructs the causal chain: Patient → Visit → Labs → FDA 2009 Hy\'s Law Rule → Safety Escalation Alert!'
      ],
      actionLabel: 'Open Patient 360 Knowledge Graph',
      executeAction: () => {
        onSetCut(3);
        onSwitchTab('patient360');
      }
    },
    {
      step: 4,
      title: 'Clinical Safety Report & Human-in-the-Loop Governance',
      subtitle: '21 CFR Part 11 Audit-Ready Regulatory Report with SHA-256 Checksum',
      talkingPoints: [
        'With one click, reviewers generate an audit-ready Clinical Safety Report (CSR-042) complete with cryptographic SHA-256 hash.',
        'Stage 2 MONITOR enforces a 6-node reviewer pipeline with mandatory human medical monitor sign-off.',
        'Stage 3 WATCH performs longitudinal 12-cut surveillance, catching adversarial unit corruption and site anomalies.'
      ],
      actionLabel: 'Generate Audit Safety Report',
      executeAction: () => {
        if (onOpenSafetyReport) {
          onOpenSafetyReport();
        }
      }
    }
  ];

  const currentStepData = steps[currentStep - 1];

  const handleNext = () => {
    if (currentStep < 4) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      steps[nextStep - 1].executeAction();
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      steps[prevStep - 1].executeAction();
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-40 max-w-lg w-full px-2 sm:px-0 transition-all duration-300">
      <div className="bg-slate-900/95 text-white border border-emerald-500/80 rounded-2xl shadow-2xl backdrop-blur-md overflow-hidden">
        {/* Header Bar */}
        <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 font-mono">
              Judge Presentation Mode
            </span>
            <span className="text-[11px] text-slate-400 font-mono">
              Step {currentStep} of 4
            </span>
          </div>

          {/* 3-Minute Presentation Timer */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-amber-300">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>{formatTimer(timerSeconds)}</span>
              <button
                onClick={() => setTimerRunning(!timerRunning)}
                className="hover:text-white p-0.5 ml-1 cursor-pointer"
                title={timerRunning ? 'Pause' : 'Start'}
              >
                {timerRunning ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 fill-current" />}
              </button>
              <button
                onClick={() => {
                  setTimerRunning(false);
                  setTimerSeconds(180);
                }}
                className="hover:text-white p-0.5 cursor-pointer"
                title="Reset"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>

            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 rounded text-slate-400 hover:text-white cursor-pointer"
              title={isMinimized ? 'Expand' : 'Minimize'}
            >
              {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
            </button>

            <button
              onClick={onCloseWalkthrough}
              className="p-1 rounded text-slate-400 hover:text-white cursor-pointer"
              title="Exit Walkthrough"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Minimized compact bar */}
        {isMinimized ? (
          <div className="p-3 flex items-center justify-between text-xs">
            <div className="font-semibold text-emerald-300 truncate max-w-[280px]">
              {currentStep}. {currentStepData.title}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={currentStepData.executeAction}
                className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 rounded text-white font-medium"
              >
                Action
              </button>
              <button
                onClick={handleNext}
                disabled={currentStep === 4}
                className="p-1 bg-slate-800 hover:bg-slate-700 rounded text-white disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          /* Expanded Walkthrough Body */
          <div className="p-4 space-y-3.5">
            {/* Progress indicator */}
            <div className="flex gap-1.5">
              {[1, 2, 3, 4].map((s) => (
                <div
                  key={s}
                  onClick={() => {
                    setCurrentStep(s);
                    steps[s - 1].executeAction();
                  }}
                  className={`h-1.5 rounded-full flex-1 cursor-pointer transition-all ${
                    s === currentStep
                      ? 'bg-emerald-400'
                      : s < currentStep
                      ? 'bg-emerald-700'
                      : 'bg-slate-800'
                  }`}
                />
              ))}
            </div>

            {/* Step Header */}
            <div>
              <div className="text-[11px] font-mono font-bold text-emerald-400 uppercase">
                {currentStepData.subtitle}
              </div>
              <h3 className="text-sm font-bold text-white mt-0.5">
                {currentStepData.title}
              </h3>
            </div>

            {/* Script / Talking Points */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 space-y-1.5 text-xs text-slate-300">
              <div className="text-[10px] uppercase font-bold text-slate-500 font-mono flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-400" /> Presenter Talking Points (45s cue):
              </div>
              {currentStepData.talkingPoints.map((pt, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px] leading-relaxed">
                  <span className="text-emerald-400 font-bold shrink-0">•</span>
                  <span>{pt}</span>
                </div>
              ))}
            </div>

            {/* Action & Navigation Controls */}
            <div className="flex items-center justify-between pt-1">
              <button
                onClick={handlePrev}
                disabled={currentStep === 1}
                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 disabled:opacity-40 flex items-center gap-1 transition cursor-pointer"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Previous
              </button>

              <button
                onClick={currentStepData.executeAction}
                className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-emerald-950 bg-emerald-400 hover:bg-emerald-300 active:scale-98 transition shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Auto-Run Step Action</span>
              </button>

              <button
                onClick={handleNext}
                disabled={currentStep === 4}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 flex items-center gap-1 transition cursor-pointer"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
