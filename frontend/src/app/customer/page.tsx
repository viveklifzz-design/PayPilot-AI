'use client';

import { useState } from 'react';
import { api, CustomerTransactionDetail } from '@/lib/api';
import { CreditCard, Search, ShieldCheck, ShieldAlert, ArrowLeft, ExternalLink, Clock } from 'lucide-react';

export default function CustomerPortalPage() {
  const [email, setEmail] = useState('');
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState<string>('');
  
  const [transactionId, setTransactionId] = useState('');
  const [transactionDetail, setTransactionDetail] = useState<CustomerTransactionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [myTransactions, setMyTransactions] = useState<CustomerTransactionDetail[]>([]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.customerLogin({ email });
      setAuthToken(res.auth_token);
      setCustomerId(res.customer_id);
      setCustomerName(res.name);
      
      const txns = await api.listCustomerTransactions(res.customer_id).catch(() => []);
      setMyTransactions(txns);
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transactionId || !customerId) return;
    setLoading(true);
    setErrorMsg(null);
    setTransactionDetail(null);
    try {
      const detail = await api.getCustomerTransaction(transactionId, customerId);
      setTransactionDetail(detail);
    } catch (err: any) {
      setErrorMsg(err.message || 'Transaction lookup failed or access denied.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex-1 w-full space-y-8">
        
        {/* Portal Header */}
        <div className="bg-slate-900 text-white p-8 rounded-3xl shadow-xl space-y-2">
          <div className="flex items-center space-x-3">
            <CreditCard className="w-8 h-8 text-sky-400" />
            <h1 className="text-2xl font-black tracking-tight">PAYPILOT — CUSTOMER RECOVERY PORTAL</h1>
          </div>
          <p className="text-sm text-slate-300">
            Securely check payment status, view official failure reasons, and complete payment recoveries.
          </p>
        </div>

        {/* 1. LOGIN STEP */}
        {!authToken ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-bold text-slate-900">Customer Authentication</h2>
            <p className="text-xs text-slate-500">Enter your email address to access your merchant transactions.</p>
            
            <form onSubmit={handleLogin} className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="customer@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-sky-600 text-white font-bold text-sm rounded-xl hover:bg-sky-700 transition-colors shadow-sm"
              >
                {loading ? 'Logging in...' : 'Sign In to Portal'}
              </button>
            </form>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-medium">
                {errorMsg}
              </div>
            )}
          </div>
        ) : (
          /* 2. TRANSACTION LOOKUP & DETAIL */
          <div className="space-y-6">
            
            {/* User Session Bar */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center justify-between shadow-sm">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase">Authenticated Customer</span>
                <p className="font-bold text-sm text-slate-900">{customerName} ({email})</p>
              </div>
              <button
                onClick={() => { setAuthToken(null); setCustomerId(null); setTransactionDetail(null); }}
                className="text-xs text-slate-500 hover:text-slate-900 font-semibold underline"
              >
                Sign Out
              </button>
            </div>

            {/* Lookup Form */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h2 className="text-base font-bold text-slate-900">Transaction Status Lookup</h2>
              <form onSubmit={handleLookup} className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  placeholder="Enter Transaction ID (e.g. 821dd426-... or pay_...)"
                  value={transactionId}
                  onChange={(e) => setTransactionId(e.target.value)}
                  required
                  className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center justify-center space-x-2 px-6 py-2.5 bg-slate-900 text-white font-bold text-sm rounded-xl hover:bg-slate-800 transition-colors shadow-sm"
                >
                  <Search className="w-4 h-4" />
                  <span>Lookup</span>
                </button>
              </form>

              {errorMsg && (
                <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl font-medium flex items-center space-x-2">
                  <ShieldAlert className="w-5 h-5 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}
            </div>

            {/* Transaction Result View */}
            {transactionDetail && (
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-md space-y-6">
                
                <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-4 gap-2">
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase">Transaction ID</span>
                    <p className="text-lg font-mono font-black text-slate-900">{transactionDetail.transaction_id}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full font-black uppercase text-xs self-start ${
                    transactionDetail.status === 'failed' ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    Payment {transactionDetail.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                    <span className="text-xs font-bold text-slate-500 uppercase">Amount</span>
                    <p className="text-2xl font-black text-slate-900 mt-1">{formatCurrency(transactionDetail.amount)}</p>
                  </div>

                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                    <span className="text-xs font-bold text-slate-500 uppercase">Recovery Status</span>
                    <p className="text-lg font-black text-slate-900 mt-1">
                      {transactionDetail.recovery_status || 'None'}
                    </p>
                  </div>
                </div>

                {/* Explanation Banner */}
                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl space-y-1 text-xs">
                  <span className="font-bold text-amber-900 uppercase tracking-wider block">Official Failure Details</span>
                  <p className="text-amber-950 font-medium">{transactionDetail.error_explanation}</p>
                </div>

                {/* Recovery Action Link Button */}
                {transactionDetail.recovery_link_url && (
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-emerald-900 text-sm">Secure Payment Recovery Ready</h4>
                      <p className="text-xs text-emerald-700">Official Razorpay Test Mode Payment Link</p>
                    </div>
                    <a
                      href={transactionDetail.recovery_link_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 px-5 py-2.5 bg-emerald-600 text-white font-bold text-xs rounded-xl hover:bg-emerald-700 transition-colors shadow"
                    >
                      <span>Complete Payment</span>
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                )}

              </div>
            )}

          </div>
        )}

      </main>
    </div>
  );
}
