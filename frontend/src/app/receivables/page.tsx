'use client';

import { useEffect, useState } from 'react';
import { api, formatIST } from '@/lib/api';
import { Clock, RefreshCw, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ReceivablesPage() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getReceivables();
      setInvoices(data || []);
    } catch (e) {
      console.error('Failed to load receivables:', e);
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
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">B2B RECEIVABLES CHASER</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                LOCAL TEST SIMULATION
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Overdue invoice tracking, reminder stopping rules (max 3), and Promise-to-Pay escalation.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Receivables</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Invoice Number</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Days Overdue</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Promise Date</th>
                  <th className="py-3 px-4">Reminders Sent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {loading && invoices.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">Loading B2B receivables...</td></tr>
                ) : invoices.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No overdue B2B receivables recorded.</td></tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{inv.invoice_number}</td>
                      <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(inv.amount)}</td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">{formatIST(inv.due_date, true)}</td>
                      <td className="py-3.5 px-4 font-bold text-rose-700">{inv.days_overdue} days</td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full font-extrabold uppercase text-[11px] ${
                          inv.status === 'PROMISE_TO_PAY' ? 'bg-sky-100 text-sky-800' :
                          inv.status === 'ESCALATED' ? 'bg-amber-100 text-amber-900' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-700">{inv.promise_date ? formatIST(inv.promise_date, true) : 'None'}</td>
                      <td className="py-3.5 px-4 font-bold text-slate-900">{inv.reminder_count} / 3 (Max)</td>
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
