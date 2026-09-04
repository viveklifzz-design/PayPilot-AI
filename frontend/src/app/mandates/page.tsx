'use client';

import { useEffect, useState } from 'react';
import { api, formatIST } from '@/lib/api';
import { RefreshCw, Repeat, AlertCircle, Play, ShieldAlert, CheckCircle2, Plus, Info, Clock, X } from 'lucide-react';

export default function MandatesPage() {
  const [mandates, setMandates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedMandateDetail, setSelectedMandateDetail] = useState<any | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // New Mandate Form
  const [newNumber, setNewNumber] = useState(`MND-${Math.floor(1000 + Math.random() * 9000)}`);
  const [newAmount, setNewAmount] = useState('5000');
  const [newInterval, setNewInterval] = useState('monthly');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getMandates();
      setMandates(data || []);
    } catch (e) {
      console.error('Failed to load mandates:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  const handleCreateMandate = async () => {
    if (!newNumber.trim() || !newAmount || parseFloat(newAmount) <= 0) return;
    setActionLoading('create');
    try {
      await api.createMandate({
        mandate_number: newNumber.trim(),
        amount: parseFloat(newAmount),
        billing_interval: newInterval
      });
      setCreateModalOpen(false);
      setNewNumber(`MND-${Math.floor(1000 + Math.random() * 9000)}`);
      await loadData();
    } catch (err) {
      console.error('Create mandate error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerFailure = async (mandateId: string) => {
    setActionLoading(`fail_${mandateId}`);
    try {
      await api.triggerMandateFailure(mandateId, 'Bank auto-debit failed (Insufficient funds)');
      await loadData();
      if (selectedMandateDetail?.id === mandateId) {
        const updated = await api.getMandateDetails(mandateId);
        setSelectedMandateDetail(updated);
      }
    } catch (err) {
      console.error('Trigger failure error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleExecuteRetry = async (mandateId: string) => {
    setActionLoading(`retry_${mandateId}`);
    try {
      await api.executeMandateRetry(mandateId);
      await loadData();
      if (selectedMandateDetail?.id === mandateId) {
        const updated = await api.getMandateDetails(mandateId);
        setSelectedMandateDetail(updated);
      }
    } catch (err) {
      console.error('Execute retry error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEscalate = async (mandateId: string) => {
    setActionLoading(`escalate_${mandateId}`);
    try {
      await api.escalateMandate(mandateId, 'Manual merchant review requested');
      await loadData();
      if (selectedMandateDetail?.id === mandateId) {
        const updated = await api.getMandateDetails(mandateId);
        setSelectedMandateDetail(updated);
      }
    } catch (err) {
      console.error('Escalate error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewDetail = async (mandateId: string) => {
    setActionLoading(`detail_${mandateId}`);
    try {
      const detail = await api.getMandateDetails(mandateId);
      setSelectedMandateDetail(detail);
      setModalOpen(true);
    } catch (err) {
      console.error('Fetch detail error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const activeRetries = mandates.filter(m => m.status === 'RETRYING').length;
  const recoveredCount = mandates.filter(m => m.status === 'RECOVERED').length;
  const escalatedCount = mandates.filter(m => m.status === 'ESCALATED' || m.status === 'CANCELLED').length;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-6">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">MANDATE RETRY SEQUENCER</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300">
                TRACK 03 ACTIVE
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Bounded retry scheduling for recurring mandates ($\le 3$ retries, Policy Gate safety, Razorpay Test Mode execution).
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setCreateModalOpen(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-lg transition-colors shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Mandate</span>
            </button>
            
            <button
              onClick={loadData}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-lg hover:bg-slate-800 transition-colors shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Metrics Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Mandates</p>
              <h3 className="text-2xl font-black text-slate-900 mt-1">{mandates.length}</h3>
            </div>
            <div className="p-3 bg-purple-50 rounded-xl text-purple-600">
              <Repeat className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Active Retries</p>
              <h3 className="text-2xl font-black text-sky-600 mt-1">{activeRetries}</h3>
            </div>
            <div className="p-3 bg-sky-50 rounded-xl text-sky-600">
              <Clock className="w-6 h-6 animate-pulse" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Recovered</p>
              <h3 className="text-2xl font-black text-emerald-600 mt-1">{recoveredCount}</h3>
            </div>
            <div className="p-3 bg-emerald-50 rounded-xl text-emerald-600">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Escalated / Stopped</p>
              <h3 className="text-2xl font-black text-amber-600 mt-1">{escalatedCount}</h3>
            </div>
            <div className="p-3 bg-amber-50 rounded-xl text-amber-600">
              <ShieldAlert className="w-6 h-6" />
            </div>
          </div>
        </div>

        {/* Mandates Table */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-extrabold text-sm text-slate-900 tracking-tight uppercase">Mandate Sequencer Queue</h3>
            <span className="text-xs text-slate-400 font-mono">Showing {mandates.length} recurring mandates</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 text-white font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Mandate Number</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Interval</th>
                  <th className="py-3 px-4">Attempt Progress</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Next Retry Scheduled</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans">
                {loading && mandates.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">Loading mandate retry sequencer...</td></tr>
                ) : mandates.length === 0 ? (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-400">No mandate retries recorded yet. Click "Create Mandate" to start.</td></tr>
                ) : (
                  mandates.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{m.mandate_number}</td>
                      <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(m.amount)}</td>
                      <td className="py-3.5 px-4 font-bold text-slate-700 capitalize">{m.billing_interval}</td>
                      <td className="py-3.5 px-4">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] font-bold text-slate-600">
                            <span>{m.attempt_count} / {m.max_attempts}</span>
                            <span>{Math.round((m.attempt_count / m.max_attempts) * 100)}%</span>
                          </div>
                          <div className="w-28 bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                            <div 
                              className={`h-full transition-all ${
                                m.status === 'RECOVERED' ? 'bg-emerald-500' :
                                m.status === 'ESCALATED' ? 'bg-rose-500' :
                                m.status === 'RETRYING' ? 'bg-sky-500' : 'bg-purple-500'
                              }`}
                              style={{ width: `${Math.min(100, (m.attempt_count / m.max_attempts) * 100)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-0.5 rounded-full font-extrabold uppercase text-[10px] tracking-wide ${
                          m.status === 'RECOVERED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                          m.status === 'ESCALATED' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                          m.status === 'CANCELLED' ? 'bg-amber-100 text-amber-900 border border-amber-300' :
                          m.status === 'RETRYING' ? 'bg-sky-100 text-sky-800 border border-sky-300' :
                          'bg-purple-100 text-purple-800 border border-purple-300'
                        }`}>
                          {m.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        {m.next_retry_date ? formatIST(m.next_retry_date, true) : 'None'}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <div className="flex items-center justify-center space-x-1.5">
                          {/* Trigger Failure */}
                          {m.status !== 'RECOVERED' && m.status !== 'ESCALATED' && m.status !== 'CANCELLED' && (
                            <button
                              onClick={() => handleTriggerFailure(m.id)}
                              disabled={actionLoading === `fail_${m.id}`}
                              className="px-2 py-1 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded text-[10px] transition-colors flex items-center space-x-1"
                              title="Simulate mandate auto-debit failure"
                            >
                              <AlertCircle className="w-3 h-3" />
                              <span>Fail</span>
                            </button>
                          )}

                          {/* Execute Retry */}
                          {m.status !== 'RECOVERED' && m.status !== 'ESCALATED' && m.status !== 'CANCELLED' && (
                            <button
                              onClick={() => handleExecuteRetry(m.id)}
                              disabled={actionLoading === `retry_${m.id}`}
                              className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded text-[10px] transition-colors flex items-center space-x-1"
                              title="Execute Razorpay Test Mode mandate retry"
                            >
                              <Play className="w-3 h-3" />
                              <span>Retry</span>
                            </button>
                          )}

                          {/* Escalate */}
                          {m.status !== 'ESCALATED' && (
                            <button
                              onClick={() => handleEscalate(m.id)}
                              disabled={actionLoading === `escalate_${m.id}`}
                              className="px-2 py-1 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded text-[10px] transition-colors flex items-center space-x-1"
                              title="Escalate mandate to human review"
                            >
                              <ShieldAlert className="w-3 h-3" />
                              <span>Escalate</span>
                            </button>
                          )}

                          {/* View Detail History */}
                          <button
                            onClick={() => handleViewDetail(m.id)}
                            disabled={actionLoading === `detail_${m.id}`}
                            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded text-[10px] transition-colors flex items-center space-x-1"
                            title="View attempt history and audit details"
                          >
                            <Info className="w-3 h-3" />
                            <span>History</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Attempt History Modal */}
      {modalOpen && selectedMandateDetail && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full border border-slate-200 shadow-2xl p-6 space-y-5 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-extrabold text-base text-slate-900">Mandate Attempt History</h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">#{selectedMandateDetail.mandate_number} — {formatCurrency(selectedMandateDetail.amount)}</p>
              </div>
              <button 
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs font-mono">
              <div>
                <span className="text-slate-400 block text-[10px]">Status:</span>
                <strong className="text-slate-900 font-bold uppercase">{selectedMandateDetail.status}</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Attempt Progress:</span>
                <strong className="text-slate-900 font-bold">{selectedMandateDetail.attempt_count} / {selectedMandateDetail.max_attempts}</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Last Failure:</span>
                <strong className="text-amber-600 font-bold truncate block">{selectedMandateDetail.failure_reason || 'None'}</strong>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Next Retry:</span>
                <strong className="text-sky-600 font-bold block">{selectedMandateDetail.next_retry_date ? formatIST(selectedMandateDetail.next_retry_date, true) : 'None'}</strong>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-extrabold text-xs text-slate-900 uppercase tracking-wider">Attempt Audit Trail</h4>
              {selectedMandateDetail.attempts && selectedMandateDetail.attempts.length > 0 ? (
                <div className="space-y-2 font-mono text-xs">
                  {selectedMandateDetail.attempts.map((att: any, idx: number) => (
                    <div key={att.id || idx} className="p-3 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-slate-900">Attempt #{att.attempt_number}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            att.status === 'SUCCEEDED' ? 'bg-emerald-100 text-emerald-800' :
                            att.status === 'BLOCKED' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-800'
                          }`}>
                            {att.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500">Key: <span className="text-slate-700">{att.idempotency_key}</span></p>
                        {att.provider_payment_id && (
                          <p className="text-[11px] text-emerald-600 font-bold">Razorpay ID: {att.provider_payment_id}</p>
                        )}
                        {att.failure_reason && (
                          <p className="text-[11px] text-amber-600">Reason: {att.failure_reason}</p>
                        )}
                      </div>
                      <div className="text-right text-[10px] text-slate-400">
                        <p>{formatIST(att.attempted_at)}</p>
                        {att.policy_decision && <p className="text-purple-600 font-bold">{att.policy_decision}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 py-4 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  No individual attempt records yet. Trigger failure or execute retry to record attempts.
                </p>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl hover:bg-slate-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Mandate Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-extrabold text-sm text-slate-900 uppercase tracking-wider">Create Recurring Mandate</h3>
              <button 
                onClick={() => setCreateModalOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <label className="text-slate-500 font-bold block mb-1">Mandate Number</label>
                <input
                  type="text"
                  value={newNumber}
                  onChange={(e) => setNewNumber(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-slate-900 font-bold focus:outline-none focus:border-purple-600"
                />
              </div>

              <div>
                <label className="text-slate-500 font-bold block mb-1">Amount (INR)</label>
                <input
                  type="number"
                  value={newAmount}
                  onChange={(e) => setNewAmount(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-slate-900 font-bold focus:outline-none focus:border-purple-600"
                />
              </div>

              <div>
                <label className="text-slate-500 font-bold block mb-1">Billing Interval</label>
                <select
                  value={newInterval}
                  onChange={(e) => setNewInterval(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-slate-900 font-bold focus:outline-none focus:border-purple-600"
                >
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
            </div>

            <div className="pt-2 flex justify-end space-x-2">
              <button
                onClick={() => setCreateModalOpen(false)}
                className="px-4 py-2 bg-slate-100 text-slate-600 font-bold text-xs rounded-xl hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMandate}
                disabled={actionLoading === 'create'}
                className="px-4 py-2 bg-purple-600 text-white font-bold text-xs rounded-xl hover:bg-purple-500 transition-colors"
              >
                {actionLoading === 'create' ? 'Creating...' : 'Create Mandate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
