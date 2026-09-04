'use client';

import { useEffect, useState } from 'react';
import { api, formatIST } from '@/lib/api';
import { ShieldAlert, RefreshCw, IndianRupee, Layers } from 'lucide-react';

export default function RevenueRiskPage() {
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.getUnifiedOpportunities();
      setSummary(res.summary);
      setOpportunities(res.opportunities || []);
    } catch (e) {
      console.error('Failed to load unified revenue risk:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-6">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">UNIFIED REVENUE RISK INTELLIGENCE</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-sky-100 text-sky-800 border border-sky-300">
                CANONICAL RISK ENGINE
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Multi-source opportunity prioritization across Payment Failures, Checkout Drop-offs, Subscriptions, Receivables, and Mandates.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Intelligence</span>
          </button>
        </div>

        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
              <span className="text-xs font-bold text-slate-500 uppercase">Total Revenue at Risk</span>
              <p className="text-2xl font-black text-slate-900 mt-2">{formatCurrency(summary.total_revenue_at_risk)}</p>
              <span className="text-xs text-slate-400 mt-1 block">Active opportunities: {summary.active_opportunities_count}</span>
            </div>

            <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
              <span className="text-xs font-bold text-slate-500 uppercase">Total Recovered Revenue</span>
              <p className="text-2xl font-black text-emerald-600 mt-2">{formatCurrency(summary.total_recovered_revenue)}</p>
              <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded mt-1 inline-block">Recovery Rate: {summary.unified_recovery_rate}%</span>
            </div>

            <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
              <span className="text-xs font-bold text-slate-500 uppercase">High Priority Opportunities</span>
              <p className="text-2xl font-black text-amber-600 mt-2">{summary.high_priority_count}</p>
              <span className="text-xs text-slate-400 mt-1 block">Requires immediate intervention</span>
            </div>
          </div>
        )}

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900">Priority-Sorted Recovery Opportunities</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Case ID</th>
                  <th className="py-3 px-4">Risk Source</th>
                  <th className="py-3 px-4">Amount at Risk</th>
                  <th className="py-3 px-4">Priority Score</th>
                  <th className="py-3 px-4">Failure / Risk Category</th>
                  <th className="py-3 px-4">Unified Status</th>
                  <th className="py-3 px-4 text-right">Created At (IST)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading && opportunities.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">Loading risk opportunities...</td></tr>
                ) : opportunities.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No active revenue risk opportunities.</td></tr>
                ) : (
                  opportunities.map((item) => (
                    <tr key={item.case_id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                        #{item.case_id.substring(0, 8)}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-slate-100 text-slate-800 border border-slate-300">
                          {item.case_type}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-black text-slate-900">
                        {formatCurrency(Number(item.amount))}
                      </td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">
                        <span className={`px-2 py-0.5 rounded font-mono text-[11px] ${
                          item.priority_level === 'CRITICAL' || item.priority_level === 'HIGH' ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {item.priority_score.toFixed(1)} ({item.priority_level})
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-700">
                        {item.failure_category}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full font-extrabold uppercase text-[11px] bg-sky-100 text-sky-800">
                          {item.unified_status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-slate-500 whitespace-nowrap">
                        {formatIST(item.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </main>
    </div>
  );
}
