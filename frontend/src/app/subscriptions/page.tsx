'use client';

import { useEffect, useState } from 'react';
import { api, formatIST } from '@/lib/api';
import { RefreshCw, Repeat, ShieldCheck } from 'lucide-react';

export default function SubscriptionsPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getCases();
      const subCases = (data || []).filter((c: any) => c.case_type === 'SUBSCRIPTION_FAILURE');
      setCases(subCases);
    } catch (e) {
      console.error('Failed to load subscription cases:', e);
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
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">FAILED SUBSCRIPTION RECOVERY</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                LOCAL TEST SIMULATION
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Recurring auto-debit attempt failures, churn risk assessment, and subscription recovery links.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Subscriptions</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Case ID</th>
                  <th className="py-3 px-4">Subscription Plan</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">AI Recommended Action</th>
                  <th className="py-3 px-4">Policy Gate</th>
                  <th className="py-3 px-4 text-right">Created At (IST)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {loading && cases.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">Loading subscription cases...</td></tr>
                ) : cases.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No failed subscription recovery cases found.</td></tr>
                ) : (
                  cases.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">#{c.id.substring(0, 8)}</td>
                      <td className="py-3.5 px-4 font-bold text-slate-800">Growth SaaS Monthly</td>
                      <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(c.amount)}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full font-extrabold uppercase text-[11px] bg-sky-100 text-sky-800">
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] font-bold text-slate-800">{c.ai_recommended_action || 'N/A'}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded font-bold uppercase text-[10px] bg-emerald-100 text-emerald-800">
                          Passed ({c.policy_passed ? 'True' : 'False'})
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono text-slate-500 whitespace-nowrap">{formatIST(c.created_at)}</td>
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
