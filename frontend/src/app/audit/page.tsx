'use client';

import { useEffect, useState } from 'react';
import { api, ActivityItem, formatISTTimeOnly } from '@/lib/api';
import { Activity, RefreshCw } from 'lucide-react';

export default function AuditPage() {
  const [auditLogs, setAuditLogs] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs({ limit: 50 });
      setAuditLogs(data || []);
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-6">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">REAL-TIME AUDIT TRAIL LOGS</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                AUDIT TRAIL
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Immutable audit stream capturing decision factors, Policy Gate outcomes, and provider webhook events.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Audit Logs</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="space-y-3">
            {loading && auditLogs.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">Loading audit log events...</p>
            ) : auditLogs.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No audit log events found.</p>
            ) : (
              auditLogs.map((item) => (
                <div key={item.id} className="flex items-start justify-between bg-slate-50 border border-slate-100 p-4 rounded-xl text-xs">
                  <div className="flex items-start space-x-3">
                    <span className={`px-2.5 py-0.5 rounded font-mono font-bold uppercase shrink-0 mt-0.5 ${
                      item.actor === 'POLICY_ENGINE' ? 'bg-amber-100 text-amber-800' :
                      item.actor === 'AI_AGENT' ? 'bg-purple-100 text-purple-800' :
                      item.actor === 'RAZORPAY_WEBHOOK' ? 'bg-sky-100 text-sky-800' :
                      'bg-slate-200 text-slate-700'
                    }`}>
                      {item.actor}
                    </span>
                    <div>
                      <p className="font-bold text-slate-900">{item.event_type}</p>
                      <p className="text-slate-600 mt-0.5">{item.description}</p>
                    </div>
                  </div>
                  <span className="text-slate-400 font-mono shrink-0 ml-4">
                    {formatISTTimeOnly(item.timestamp)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </main>
    </div>
  );
}
