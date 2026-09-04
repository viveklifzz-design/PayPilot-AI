'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { MessageSquare, PhoneCall, ShieldCheck, Sparkles } from 'lucide-react';

export default function CommunicationsPage() {
  const [customerName, setCustomerName] = useState('Rahul Sharma');
  const [amount, setAmount] = useState('2500');
  const [language, setLanguage] = useState('hinglish');
  const [paymentLink, setPaymentLink] = useState('https://rzp.io/rzp/vsKQMYz');
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.generateCommunication({
        customer_name: customerName,
        amount: parseFloat(amount) || 0,
        language: language,
        payment_link_url: paymentLink,
      });
      setResult(res);
    } catch (err) {
      console.error('Failed to generate communication:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 space-y-6 w-full">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-black text-slate-900 tracking-tight">COMMUNICATION CENTER</h1>
              <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-sky-100 text-sky-800 border border-sky-300">
                LOCAL TEST SIMULATION
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              Localized Hinglish / Hindi / English recovery messaging & voice script assistance generator.
            </p>
          </div>
        </div>

        <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl text-xs font-semibold text-amber-900 flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-amber-700 shrink-0" />
          <span>
            TEST COMMUNICATION — NOT SENT TO REAL CUSTOMER. Communication assistance only. Money movement strictly requires Policy Gate & Razorpay Payment Link.
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Generator Form */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-sky-600" />
              <span>Generate Recovery Communication</span>
            </h2>

            <form onSubmit={handleGenerate} className="space-y-4 text-xs font-medium">
              <div>
                <label className="block text-slate-600 mb-1">Customer Name</label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-900"
                />
              </div>

              <div>
                <label className="block text-slate-600 mb-1">Payment Amount (INR)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-900"
                />
              </div>

              <div>
                <label className="block text-slate-600 mb-1">Target Language</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-bold"
                >
                  <option value="hinglish">Hinglish (Recommended)</option>
                  <option value="hindi">Hindi</option>
                  <option value="english">English</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-600 mb-1">Razorpay Recovery Link URL</label>
                <input
                  type="text"
                  value={paymentLink}
                  onChange={(e) => setPaymentLink(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 font-mono"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-colors shadow-sm"
              >
                {loading ? 'Generating Template...' : 'Generate Messages & Scripts'}
              </button>
            </form>
          </div>

          {/* Generated Result Preview */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <MessageSquare className="w-4 h-4 text-sky-600" />
              <span>Generated Output Preview</span>
            </h2>

            {result ? (
              <div className="space-y-4 text-xs">
                
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-1">
                  <span className="font-bold text-slate-500 uppercase block">SMS / WhatsApp Message Text</span>
                  <p className="text-slate-900 font-semibold">{result.text_message}</p>
                </div>

                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl space-y-1">
                  <div className="flex items-center space-x-2 text-slate-500 font-bold uppercase">
                    <PhoneCall className="w-3.5 h-3.5 text-sky-600" />
                    <span>Voice Call Script Assistance</span>
                  </div>
                  <p className="text-slate-900 font-semibold">{result.voice_script}</p>
                </div>

                <div className="text-[11px] text-slate-400 italic">
                  {result.disclaimer}
                </div>

              </div>
            ) : (
              <div className="py-12 text-center text-slate-400 text-xs">
                Fill form and click generate to preview localized Hinglish recovery messages.
              </div>
            )}
          </div>

        </div>

      </main>
    </div>
  );
}
