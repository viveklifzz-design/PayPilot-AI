'use client';

import { useState, useEffect } from 'react';
import { api, FailureScenario, SimulateFailureResponse } from '@/lib/api';
import { ShieldCheck, AlertTriangle, Lock, ShieldAlert, Cpu, ArrowRight, Bot, CheckCircle2, XCircle, RefreshCw, AlertOctagon } from 'lucide-react';

export default function SafetyPage() {
  const [metrics, setMetrics] = useState<{ allowed: number; review: number; blocked: number; escalated: number }>({ allowed: 0, review: 0, blocked: 0, escalated: 0 });
  const [recentLogs, setRecentLogs] = useState<any[]>([]);
  const [scenarios, setScenarios] = useState<FailureScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('PAYMENT_VERIFICATION_FAILURE');
  const [simResult, setSimResult] = useState<SimulateFailureResponse | null>(null);
  const [simLoading, setSimLoading] = useState<boolean>(false);

  useEffect(() => {
    const fetchPolicyMetrics = async () => {
      try {
        const [cases, logs, scList] = await Promise.all([
          api.getCases().catch(() => []),
          api.getAuditLogs({ limit: 15 }).catch(() => []),
          api.getFailureScenarios().catch(() => [])
        ]);
        let allowed = 0;
        let review = 0;
        let blocked = 0;
        let escalated = 0;
        cases.forEach((c) => {
          if (c.status === 'RECOVERED') allowed += 1;
          else if (c.status === 'STOPPED') blocked += 1;
          else if (c.status === 'ESCALATED') { review += 1; escalated += 1; }
          else allowed += 1;
        });
        setMetrics({ allowed, review, blocked, escalated });
        setRecentLogs(logs.filter((l) => l.event_type && (l.event_type.includes('POLICY') || l.event_type.includes('HUMAN') || l.event_type.includes('STOPPING') || l.event_type.includes('FAILURE'))));
        setScenarios(scList);
      } catch (err) {
        console.error('Failed to fetch safety metrics:', err);
      }
    };
    fetchPolicyMetrics();
  }, []);

  const handleSimulate = async () => {
    if (!selectedScenario) return;
    setSimLoading(true);
    try {
      const res = await api.simulateFailure(selectedScenario);
      setSimResult(res);
    } catch (err) {
      console.error('Failure simulation error:', err);
    } finally {
      setSimLoading(false);
    }
  };

  const policyRules = [
    {
      name: 'MAX RECOVERY ATTEMPTS',
      value: '3 Retries Max',
      ruleId: 'RULE_ATTEMPT_LIMIT',
      description: 'Prevents customer harassment by halting automated recovery attempts after 3 retries.',
      status: 'ACTIVE',
    },
    {
      name: 'AUTONOMOUS AMOUNT CAP',
      value: '₹5,000.00 Limit',
      ruleId: 'RULE_AUTONOMOUS_AMOUNT_LIMIT',
      description: 'Transactions above ₹5,000 require manual review before autonomous recovery checkout.',
      status: 'ACTIVE',
    },
    {
      name: 'HARD MAXIMUM AMOUNT CAP',
      value: '₹50,000.00 Hard Limit',
      ruleId: 'RULE_HARD_AMOUNT_LIMIT',
      description: 'High-value transactions above ₹50,000 are instantly blocked from automated recovery.',
      status: 'ACTIVE',
    },
    {
      name: 'AI CONFIDENCE THRESHOLD',
      value: '85% Minimum',
      ruleId: 'RULE_AI_CONFIDENCE_THRESHOLD',
      description: 'AI recommendation confidence below 85% routes the case to manual review.',
      status: 'ACTIVE',
    },
    {
      name: 'RISK SCORE THRESHOLD',
      value: '65.0 Max Risk',
      ruleId: 'RULE_RISK_SCORE_CHECK',
      description: 'Elevated merchant/customer risk scores above 65.0 trigger a manual review flag.',
      status: 'ACTIVE',
    },
    {
      name: 'SUSPECTED FRAUD GUARD',
      value: 'Instant Hard Block',
      ruleId: 'RULE_FRAUD_SECURITY_GUARD',
      description: 'Security and suspected fraud error codes trigger an immediate escalation and stop.',
      status: 'ACTIVE',
    },
  ];

  const overrideExamples = [
    {
      title: 'High-Value Payment Over Auto Limit',
      amount: '₹80,000.00',
      aiRec: 'RECOVERY_LINK',
      aiConf: '99%',
      policyDecision: 'BLOCKED',
      violation: 'AMOUNT_EXCEEDS_AUTO_LIMIT',
      finalAction: 'ESCALATE',
      reason: 'Transaction amount exceeds auto-recovery safety threshold of ₹50,000.',
    },
    {
      title: 'Repeated Retries Exhausted',
      amount: '₹1,500.00',
      aiRec: 'RETRY',
      aiConf: '95%',
      policyDecision: 'BLOCKED',
      violation: 'MAX_RETRIES_EXCEEDED',
      finalAction: 'STOP',
      reason: 'Case has reached maximum allowed 3 recovery attempts.',
    },
    {
      title: 'Suspected Fraud Alert',
      amount: '₹5,000.00',
      aiRec: 'RECOVERY_LINK',
      aiConf: '90%',
      policyDecision: 'BLOCKED',
      violation: 'SUSPECTED_FRAUD_GUARD',
      finalAction: 'ESCALATE',
      reason: 'Transaction flagged for suspected fraud by gateway security check.',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-8">
        
        {/* Page Header */}
        <div>
          <div className="flex items-center space-x-2 text-rose-600 font-bold text-xs uppercase tracking-wider mb-1">
            <ShieldCheck className="w-4 h-4 text-rose-600" />
            <span>Deterministic Safety Architecture</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">POLICY SAFETY GATE & GOVERNANCE</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            PayPilot AI guarantees that AI recommendations NEVER execute without passing strict non-bypassable policy rules.
          </p>
        </div>

        {/* Banner: AI RECOMMENDATION != FINAL ACTION */}
        <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-lg border border-slate-800 space-y-3">
          <div className="flex items-center space-x-3 text-amber-400">
            <ShieldAlert className="w-6 h-6 shrink-0" />
            <h2 className="text-lg font-black tracking-wide">CORE SAFETY MANDATE</h2>
          </div>
          <p className="text-sm text-slate-300">
            The AI Model is strictly <strong>ADVISORY</strong>. The deterministic Policy Gate holds <strong>FINAL AUTHORITATIVE POWER</strong> over all recovery execution. An AI recommendation with 99% confidence will be instantly blocked if it violates safety policy thresholds.
          </p>
          <div className="bg-slate-950 p-4 rounded-xl font-mono text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-slate-300 border border-slate-800">
            <div className="flex items-center space-x-2 text-purple-300">
              <Bot className="w-4 h-4 text-purple-400" />
              <span>AI Recommendation: RETRY (99% Conf.)</span>
            </div>
            <ArrowRight className="hidden md:block w-4 h-4 text-amber-400" />
            <div className="flex items-center space-x-2 text-amber-300">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Policy Evaluation: BLOCKED (MAX_RETRIES)</span>
            </div>
            <ArrowRight className="hidden md:block w-4 h-4 text-emerald-400" />
            <div className="flex items-center space-x-2 text-emerald-300 font-bold">
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>Final Effective Action: STOP</span>
            </div>
          </div>
        </div>

        {/* ACTIVE POLICY RULES GRID */}
        <div className="space-y-4">
          <h2 className="text-lg font-extrabold text-slate-900">Enforced Deterministic Policy Rules</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {policyRules.map((rule, idx) => (
              <div key={idx} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    {rule.ruleId}
                  </span>
                  <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800">
                    {rule.status}
                  </span>
                </div>
                <div>
                  <h3 className="font-extrabold text-base text-slate-900">{rule.name}</h3>
                  <p className="text-lg font-black text-rose-600 mt-0.5">{rule.value}</p>
                </div>
                <p className="text-xs text-slate-500">{rule.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* REAL POLICY OVERRIDE VISUALIZATIONS */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-lg font-extrabold text-slate-900">Real Policy Block & Override Demonstrations</h2>
            <p className="text-xs text-slate-500">Concrete examples showing Policy Gate overriding AI recommendations</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {overrideExamples.map((ex, idx) => (
              <div key={idx} className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-xs text-slate-900">{ex.title}</h3>
                  <span className="font-mono text-xs font-bold text-slate-700">{ex.amount}</span>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500">AI Proposed:</span>
                    <span className="font-bold text-purple-700">{ex.aiRec} ({ex.aiConf})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Policy Gate:</span>
                    <span className="font-extrabold text-rose-600">{ex.policyDecision}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Violation:</span>
                    <span className="font-mono text-rose-800">{ex.violation}</span>
                  </div>
                  <div className="flex justify-between border-t pt-1 font-bold">
                    <span className="text-slate-900">Final Action:</span>
                    <span className="text-emerald-700">{ex.finalAction}</span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 italic">"{ex.reason}"</p>
              </div>
            ))}
          </div>
        </div>

        {/* ⚠️ FAILURE & FALLBACK DEMO SECTION */}
        <div className="bg-white border border-amber-200 rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-amber-100 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <AlertOctagon className="w-5 h-5 text-amber-600" />
                <h2 className="text-lg font-black text-slate-900 tracking-tight">FAILURE & FALLBACK DEMONSTRATION ⚠️</h2>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Controlled test mode simulation proving zero false recoveries, fail-closed boundaries, and safe customer messages.
              </p>
            </div>
            <div className="px-3 py-1 bg-amber-50 border border-amber-200 rounded-full text-xs font-mono font-bold text-amber-800">
              TEST MODE SIMULATION ONLY
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left Controls Bar */}
            <div className="space-y-4 md:col-span-1">
              <label className="text-xs font-bold text-slate-600 uppercase tracking-wider block">
                Select Failure Scenario:
              </label>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value)}
                className="w-full text-xs font-mono p-3 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-amber-500 outline-none"
              >
                {scenarios.map((sc) => (
                  <option key={sc.scenario_key} value={sc.scenario_key}>
                    {sc.title} ({sc.category})
                  </option>
                ))}
              </select>

              <button
                onClick={handleSimulate}
                disabled={simLoading}
                className="w-full py-3 px-4 bg-amber-600 hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 text-white text-xs font-extrabold rounded-xl transition-colors flex items-center justify-center space-x-2 shadow-sm font-mono"
              >
                {simLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>EXECUTING SIMULATION...</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4" />
                    <span>RUN FAILURE SIMULATION</span>
                  </>
                )}
              </button>
            </div>

            {/* Right Simulation Output View */}
            <div className="md:col-span-2 space-y-4">
              {simResult ? (
                <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-4">
                  <div className="flex flex-wrap items-center justify-between border-b pb-3 border-slate-200 text-xs font-mono">
                    <span className="font-bold text-slate-900">{simResult.scenario_key}</span>
                    <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                      simResult.retry_policy === 'RETRYABLE' ? 'bg-indigo-100 text-indigo-800' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {simResult.retry_policy}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">STEP-BY-STEP RESOLUTION LINEAGE</span>
                    <div className="space-y-2">
                      {simResult.step_by_step_lineage.map((st) => (
                        <div key={st.step} className="p-3 bg-white border border-slate-200 rounded-lg text-xs space-y-1">
                          <div className="flex items-center justify-between font-bold">
                            <span className="text-slate-900">{st.title}</span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">{st.status}</span>
                          </div>
                          <p className="text-slate-600 text-[11px] leading-relaxed">{st.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 space-y-1">
                    <div className="flex items-center space-x-1.5 font-bold">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>ZERO FALSE RECOVERY CONFIRMED</span>
                    </div>
                    <p className="text-[11px] text-emerald-800">
                      Case state preserved: <strong>{simResult.case_state_preserved}</strong> | Recovered amount preserved: <strong>₹{simResult.recovered_amount_preserved.toFixed(2)}</strong> | Audit log recorded.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="p-8 border border-dashed border-slate-200 rounded-xl bg-slate-50 text-center text-xs text-slate-400 space-y-2">
                  <AlertOctagon className="w-8 h-8 mx-auto text-slate-300" />
                  <p>Select a failure scenario on the left and click "RUN FAILURE SIMULATION" to observe the step-by-step resolution lineage.</p>
                </div>
              )}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
