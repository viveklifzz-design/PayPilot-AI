'use client';

import { useEffect, useState } from 'react';
import CaseDetailDrawer from '@/components/CaseDetailDrawer';
import { api, RecoveryCaseItem, formatIST } from '@/lib/api';
import { Search, Filter, ShieldCheck, AlertCircle, RefreshCw, ChevronRight, Eye } from 'lucide-react';

export default function CasesPage() {
  const [cases, setCases] = useState<RecoveryCaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<RecoveryCaseItem | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadCases = async (showLoadingState = true) => {
    if (showLoadingState) setLoading(true);
    setFetchError(null);
    try {
      let filterParam: { status?: string; risk_level?: string } = {};
      if (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(activeFilter)) {
        filterParam.risk_level = activeFilter;
      } else if (activeFilter !== 'ALL') {
        filterParam.status = activeFilter;
      }

      const res = await api.getCases(filterParam);
      setCases(res || []);
    } catch (e: any) {
      console.error('Failed to load cases:', e);
      setFetchError(e.message || 'Failed to connect to PayPilot backend API.');
    } finally {
      if (showLoadingState) setLoading(false);
    }
  };

  useEffect(() => {
    loadCases(true);
    const intervalId = setInterval(() => {
      loadCases(false);
    }, 12000);
    return () => clearInterval(intervalId);
  }, [activeFilter]);

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  const filters = [
    { label: 'All Cases', value: 'ALL' },
    { label: 'Critical Risk', value: 'CRITICAL' },
    { label: 'High Risk', value: 'HIGH' },
    { label: 'Medium Risk', value: 'MEDIUM' },
    { label: 'Low Risk', value: 'LOW' },
    { label: 'Recovered', value: 'RECOVERED' },
    { label: 'Escalated', value: 'ESCALATED' },
    { label: 'Stopped', value: 'STOPPED' },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-6">
        
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">RECOVERY CASES EXPLORER</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Detailed Case Registry with Risk Scores, AI Recommendations, & Policy Safety Audit
            </p>
          </div>
          <button
            onClick={() => loadCases(true)}
            disabled={loading}
            className="self-start md:self-auto flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Cases</span>
          </button>
        </div>

        {/* Filter Toolbar */}
        <div className="bg-white border border-slate-200 p-3 rounded-xl shadow-sm flex items-center space-x-2 overflow-x-auto">
          <Filter className="w-4 h-4 text-slate-400 ml-2 shrink-0" />
          <span className="text-xs font-bold text-slate-500 mr-2 shrink-0">Filter:</span>
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setActiveFilter(f.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                activeFilter === f.value
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Cases Table */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900 text-white text-xs font-bold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Case ID</th>
                  <th className="py-3.5 px-4">Type</th>
                  <th className="py-3.5 px-4">Amount</th>
                  <th className="py-3.5 px-4">Risk Level</th>
                  <th className="py-3.5 px-4">AI Rec.</th>
                  <th className="py-3.5 px-4">Confidence</th>
                  <th className="py-3.5 px-4">Policy Check</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400">
                      Loading recovery cases...
                    </td>
                  </tr>
                ) : fetchError ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center">
                      <div className="space-y-2 max-w-md mx-auto">
                        <p className="text-rose-600 font-semibold">{fetchError}</p>
                        <button
                          onClick={() => loadCases(true)}
                          className="px-4 py-1.5 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800"
                        >
                          Retry Connection
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : cases.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-400">
                      No cases found matching the active filter.
                    </td>
                  </tr>
                ) : (
                  cases.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => setSelectedCase(item)}
                      className="hover:bg-slate-50 cursor-pointer transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                        #{item.id.substring(0, 8)}
                      </td>
                      <td className="py-3.5 px-4 font-bold">
                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-extrabold ${
                          item.case_type === 'SUBSCRIPTION_FAILURE'
                            ? 'bg-amber-100 text-amber-900 border border-amber-300'
                            : item.case_type === 'CHECKOUT_DROPOFF'
                            ? 'bg-purple-100 text-purple-800 border border-purple-200'
                            : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}>
                          {item.case_type === 'SUBSCRIPTION_FAILURE' ? 'SUBSCRIPTION' : item.case_type === 'CHECKOUT_DROPOFF' ? 'DROP-OFF' : 'FAILURE'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        {formatCurrency(Number(item.amount))}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded font-bold ${
                          item.risk_level === 'CRITICAL' ? 'bg-rose-100 text-rose-800' :
                          item.risk_level === 'HIGH' ? 'bg-amber-100 text-amber-800' :
                          item.risk_level === 'MEDIUM' ? 'bg-sky-100 text-sky-800' :
                          'bg-emerald-100 text-emerald-800'
                        }`}>
                          {item.risk_level} ({item.risk_score})
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">
                        {item.ai_recommended_action || 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        {item.ai_confidence ? `${Math.round(item.ai_confidence * 100)}%` : 'N/A'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded font-bold ${
                          item.policy_passed ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {item.policy_passed ? 'PASSED' : 'BLOCKED'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full font-extrabold text-xs uppercase ${
                          item.status === 'RECOVERED' ? 'bg-emerald-500 text-white' :
                          item.status === 'ESCALATED' ? 'bg-amber-500 text-white' :
                          item.status === 'STOPPED' ? 'bg-rose-500 text-white' :
                          'bg-sky-600 text-white'
                        }`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCase(item);
                          }}
                          className="inline-flex items-center space-x-1 text-sky-600 font-bold hover:text-sky-800"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </main>

      {/* Case Detail Drawer */}
      <CaseDetailDrawer
        caseItem={selectedCase}
        onClose={() => setSelectedCase(null)}
      />
    </div>
  );
}
