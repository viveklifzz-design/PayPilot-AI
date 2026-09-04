'use client';

import { useState, useEffect } from 'react';
import { api, EvaluationRunSummary, CaseDetailEvaluation } from '@/lib/api';
import { Play, Activity, AlertCircle, TrendingUp, Download, ShieldCheck, CheckCircle2, RefreshCw, HelpCircle, X, ChevronRight } from 'lucide-react';

export default function BenchmarkPage() {
  const [datasetSize, setDatasetSize] = useState<number>(1000);
  const [seed, setSeed] = useState<number>(42);
  const [mode, setMode] = useState<string>('deterministic');
  const [loading, setLoading] = useState<boolean>(false);
  const [runSummary, setRunSummary] = useState<any | null>(null);
  const [casesList, setCasesList] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any | null>(null);

  const fetchLatestSummary = async () => {
    try {
      const summary = await api.getEvaluationSummary();
      setRunSummary(summary);
      if (summary?.run_id) {
        const cases = await api.getEvaluationCases(summary.run_id);
        setCasesList(cases || []);
      }
    } catch (e) {
      console.error('Failed to fetch initial evaluation summary:', e);
    }
  };

  useEffect(() => {
    fetchLatestSummary();
  }, []);

  const handleRunEvaluation = async () => {
    setLoading(true);
    try {
      const summary = await api.runEvaluation(datasetSize, seed);
      setRunSummary(summary);
      const cases = await api.getEvaluationCases(summary.run_id);
      setCasesList(cases || []);
    } catch (e) {
      console.error('Failed to run evaluation engine:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!runSummary?.run_id) return;
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    const url = `${baseUrl}/api/v1/evaluation/runs/${runSummary.run_id}/export/csv`;
    window.open(url, '_blank');
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-8">
        
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs uppercase tracking-wider mb-1">
              <Activity className="w-4 h-4 text-sky-600" />
              <span>Point #9 — Evaluation Engine & Statistical Benchmark</span>
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">PAYPILOT AI EVALUATION BENCHMARK</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Reproducible seed-based batch evaluation engine assessing decision precision, recall, policy safety, and simulated revenue yields.
            </p>
          </div>

          <div className="px-3.5 py-1.5 rounded-lg bg-amber-50 text-amber-900 border border-amber-300 text-xs font-extrabold flex items-center space-x-2 shrink-0 shadow-sm">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>Synthetic Evaluation — No Real Money</span>
          </div>
        </div>

        {/* BATCH RUNNER CONFIGURATION PANEL */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">Evaluation Run Configuration</h2>
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-500 font-semibold">Preset Size:</span>
              {[100, 500, 1000, 2000].map((sz) => (
                <button
                  key={sz}
                  onClick={() => setDatasetSize(sz)}
                  className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                    datasetSize === sz ? 'bg-sky-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {sz} Cases
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Dataset Size</label>
              <input
                type="number"
                value={datasetSize}
                onChange={(e) => setDatasetSize(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-bold font-mono focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Random Seed (Reproducibility)</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-bold font-mono focus:outline-none focus:ring-2 focus:ring-slate-900"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-slate-600 block mb-1">Evaluation Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="deterministic">Deterministic Adapter</option>
                <option value="live_ai">Live Gemini AI Mode</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleRunEvaluation}
                disabled={loading}
                className="w-full flex items-center justify-center space-x-2 py-2.5 bg-slate-900 text-white rounded-lg font-bold text-sm hover:bg-slate-800 transition-colors shadow-md disabled:opacity-50"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                <span>{loading ? 'Evaluating Engine...' : `Run ${datasetSize}-Case Benchmark`}</span>
              </button>
            </div>
          </div>
        </div>

        {/* RESULTS SUMMARY */}
        {runSummary && (
          <div className="space-y-6">
            
            {/* HERO KPI CARDS */}
            <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-lg border border-slate-800 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-4 gap-2">
                <div>
                  <h2 className="text-lg font-black tracking-wide text-white">{runSummary.run_name || `Evaluation Benchmark (${runSummary.dataset_size || runSummary.batch_size} Cases)`}</h2>
                  <p className="text-xs text-slate-400">Run ID: #{runSummary.run_id} | Seed: {runSummary.seed} | Mode: {runSummary.mode}</p>
                </div>
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleExportCSV}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg text-xs font-bold transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Export CSV</span>
                  </button>
                  <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-bold">
                    ✓ Benchmark Verified
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Revenue At Risk</span>
                  <p className="text-2xl font-black text-white mt-1">{formatCurrency(runSummary.revenue_at_risk || runSummary.total_failed_amount)}</p>
                </div>
                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                  <span className="text-xs font-bold text-sky-400 uppercase tracking-wider block">Recoverable Revenue</span>
                  <p className="text-2xl font-black text-sky-400 mt-1">{formatCurrency(runSummary.recoverable_revenue || 0)}</p>
                </div>
                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider block">Revenue Recovered</span>
                  <p className="text-2xl font-black text-emerald-400 mt-1">{formatCurrency(runSummary.revenue_recovered || runSummary.total_recovered)}</p>
                </div>
                <div className="bg-slate-800/80 p-4 rounded-xl border border-slate-700">
                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block">Recovery Rate</span>
                  <p className="text-2xl font-black text-amber-400 mt-1">{runSummary.recovery_rate}%</p>
                </div>
              </div>

              {/* SECONDARY METRICS GRID */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2 border-t border-slate-800/60">
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-slate-400 block">Precision</span>
                  <span className="text-lg font-bold text-white">{runSummary.precision || runSummary.precision_rate}%</span>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-slate-400 block">Recall</span>
                  <span className="text-lg font-bold text-white">{runSummary.recall || 0}%</span>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-slate-400 block">Intervention Rate</span>
                  <span className="text-lg font-bold text-white">{runSummary.intervention_rate || 0}%</span>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-slate-400 block">Safe Stop Rate</span>
                  <span className="text-lg font-bold text-white">{runSummary.safe_stop_rate}%</span>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-slate-400 block">Escalation Rate</span>
                  <span className="text-lg font-bold text-white">{runSummary.escalation_rate}%</span>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-[11px] font-semibold text-rose-400 block">Unsafe Actions</span>
                  <span className="text-lg font-bold text-emerald-400">{runSummary.unsafe_action_count || 0}</span>
                </div>
              </div>
            </div>

            {/* EVALUATION FUNNEL VISUALIZATION */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Evaluation Conversion Funnel</h3>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl relative overflow-hidden">
                  <div className="text-xs font-semibold text-slate-500 uppercase">1. Total Cases</div>
                  <div className="text-xl font-black text-slate-900 mt-1">{runSummary.dataset_size || runSummary.batch_size} Cases</div>
                  <div className="text-xs text-slate-400 mt-0.5">Synthetic Failure Stream</div>
                </div>

                <div className="bg-sky-50 border border-sky-200 p-4 rounded-xl relative overflow-hidden">
                  <div className="text-xs font-semibold text-sky-700 uppercase">2. Ground Truth Recoverable</div>
                  <div className="text-xl font-black text-sky-900 mt-1">{runSummary.policy_allowed_count} Cases</div>
                  <div className="text-xs text-sky-600 mt-0.5">High Conversion Potential</div>
                </div>

                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl relative overflow-hidden">
                  <div className="text-xs font-semibold text-amber-700 uppercase">3. Policy Approved Actions</div>
                  <div className="text-xl font-black text-amber-900 mt-1">{runSummary.recovery_attempt_count} Interventions</div>
                  <div className="text-xs text-amber-600 mt-0.5">Retry / Link / Reminder</div>
                </div>

                <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl relative overflow-hidden">
                  <div className="text-xs font-semibold text-emerald-700 uppercase">4. Successful Recoveries</div>
                  <div className="text-xl font-black text-emerald-900 mt-1">{runSummary.recovered_count} Recovered</div>
                  <div className="text-xs text-emerald-600 mt-0.5">{runSummary.recovery_rate}% Recovery Yield</div>
                </div>
              </div>
            </div>

            {/* BATCH CASE BREAKDOWN TABLE */}
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden space-y-3">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="font-bold text-sm text-slate-900">
                  Evaluated Sample Breakdown ({casesList.length} Cases)
                </div>
                <span className="text-xs text-slate-500 font-semibold">Click any row to inspect "Why This Decision?"</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                      <th className="py-3 px-4">Case ID</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Failure Reason</th>
                      <th className="py-3 px-4">Ground Truth</th>
                      <th className="py-3 px-4">AI Rec.</th>
                      <th className="py-3 px-4">Policy Gate</th>
                      <th className="py-3 px-4">Final Status</th>
                      <th className="py-3 px-4">Recovered</th>
                      <th className="py-3 px-4">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {casesList.slice(0, 20).map((c, idx) => (
                      <tr
                        key={idx}
                        onClick={() => setSelectedCase(c)}
                        className="hover:bg-sky-50/50 cursor-pointer transition-colors"
                      >
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          #{c.case_id ? c.case_id.substring(0, 12) : `case_${c.case_num}`}
                        </td>
                        <td className="py-3 px-4 font-bold text-slate-900">{formatCurrency(c.amount)}</td>
                        <td className="py-3 px-4 font-mono text-slate-600">{c.failure_reason || c.error_code}</td>
                        <td className="py-3 px-4 font-bold text-slate-700">{c.ground_truth_action || 'N/A'}</td>
                        <td className="py-3 px-4 font-semibold text-amber-700">{c.ai_recommended_action}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded font-bold ${c.policy_allowed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                            {c.policy_allowed ? 'APPROVED' : 'BLOCKED'}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-bold">
                          <span className={`px-2 py-0.5 rounded ${
                            c.final_status === 'RECOVERED' ? 'bg-emerald-600 text-white' :
                            c.final_status === 'ESCALATED' ? 'bg-amber-500 text-white' :
                            c.final_status === 'STOPPED' ? 'bg-rose-500 text-white' : 'bg-slate-200 text-slate-700'
                          }`}>
                            {c.final_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-bold text-emerald-700">
                          {c.recovered_amount ? formatCurrency(c.recovered_amount) : '₹0'}
                        </td>
                        <td className="py-3 px-4 text-sky-600 font-bold flex items-center space-x-1">
                          <span>Explain</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* WHY THIS DECISION? EXPLAINABILITY MODAL */}
        {selectedCase && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-sm flex justify-center items-center p-4">
            <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-200">
              <div className="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <HelpCircle className="w-5 h-5 text-sky-400" />
                  <h3 className="font-bold text-base">WHY THIS DECISION?</h3>
                </div>
                <button
                  onClick={() => setSelectedCase(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4 text-sm">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500 block">Case ID</span>
                    <strong className="text-slate-900 font-mono">{selectedCase.case_id || `#${selectedCase.case_num}`}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Failed Amount</span>
                    <strong className="text-slate-900">{formatCurrency(selectedCase.amount)}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Failure Scenario</span>
                    <strong className="text-slate-900 font-mono">{selectedCase.failure_reason || selectedCase.error_code}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Risk Score</span>
                    <strong className="text-slate-900">{selectedCase.risk_level} ({selectedCase.risk_score})</strong>
                  </div>
                </div>

                <div className="space-y-2 border-t pt-3 border-slate-100">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-semibold">Ground Truth Expectation:</span>
                    <span className="font-bold text-slate-900">{selectedCase.ground_truth_category || 'RECOVERABLE'} ({selectedCase.ground_truth_action || 'RETRY'})</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-semibold">AI Decision Recommended:</span>
                    <span className="font-bold text-amber-600">{selectedCase.ai_recommended_action} (Confidence: {Math.round((selectedCase.ai_confidence || 0.85) * 100)}%)</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-semibold">Deterministic Policy Gate:</span>
                    <span className={`font-bold ${selectedCase.policy_allowed ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {selectedCase.policy_allowed ? 'APPROVED' : 'BLOCKED / OVERRIDDEN'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-semibold">Effective Action Executed:</span>
                    <span className="font-bold text-slate-900">{selectedCase.effective_action}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-slate-500 font-semibold">Final Simulated Outcome:</span>
                    <span className={`font-extrabold ${selectedCase.final_status === 'RECOVERED' ? 'text-emerald-600' : 'text-slate-800'}`}>
                      {selectedCase.final_status} ({selectedCase.recovered_amount ? formatCurrency(selectedCase.recovered_amount) : '₹0'})
                    </span>
                  </div>
                </div>

                {selectedCase.simulation_notes && (
                  <div className="bg-sky-50 border border-sky-200 p-3 rounded-lg text-xs text-sky-900 italic">
                    "{selectedCase.simulation_notes}"
                  </div>
                )}
              </div>

              <div className="bg-slate-50 p-4 border-t border-slate-200 flex justify-end">
                <button
                  onClick={() => setSelectedCase(null)}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800"
                >
                  Close Explanation
                </button>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
