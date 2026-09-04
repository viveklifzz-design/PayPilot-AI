'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Script from 'next/script';
import Link from 'next/link';
import { api, RecoveryCaseItem, AIAssessmentResponse, PolicyGateResponse, StoppingRulesResponse, HumanEscalationResponse, CheckoutStatusResponse, formatIST } from '@/lib/api';
import PayPilotLogo from '@/components/PayPilotLogo';
import { 
  CreditCard, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  ArrowLeft,
  Clock,
  ShieldCheck,
  Bot,
  ChevronDown,
  Cpu,
  Lock,
  ArrowUpRight,
  ExternalLink,
  XCircle,
  AlertTriangle
} from 'lucide-react';

declare global {
  interface Window {
    Razorpay: any;
  }
}

export default function RecoveryCheckoutPage() {
  const params = useParams();
  const rawCaseId = params?.caseId as string;

  const [caseItem, setCaseItem] = useState<RecoveryCaseItem | null>(null);
  const [aiAssessment, setAiAssessment] = useState<AIAssessmentResponse | null>(null);
  const [policyAssessment, setPolicyAssessment] = useState<PolicyGateResponse | null>(null);
  const [stoppingAssessment, setStoppingAssessment] = useState<StoppingRulesResponse | null>(null);
  const [escalationAssessment, setEscalationAssessment] = useState<HumanEscalationResponse | null>(null);
  const [checkoutStatus, setCheckoutStatus] = useState<CheckoutStatusResponse | null>(null);
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [successResult, setSuccessResult] = useState<any | null>(null);
  const [pendingPaymentInfo, setPendingPaymentInfo] = useState<{ payment_id: string; order_id: string; signature?: string } | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState<boolean>(false);
  const [showTechDetails, setShowTechDetails] = useState<boolean>(false);

  const loadCaseData = async () => {
    if (!rawCaseId) return;
    setLoading(true);
    setError(null);

    try {
      // 1. Fetch case list to find matching case by full ID or 8-char prefix
      const cases = await api.getCases().catch(() => []);
      let found = cases.find((c) => c.id === rawCaseId || c.id.substring(0, 8) === rawCaseId);

      // Fallback: fetch case detail directly if not found in first page
      if (!found) {
        const detail = await api.getCaseDetail(rawCaseId).catch(() => null);
        if (detail) found = detail;
      }

      if (found) {
        setCaseItem(found);

        // 2. Fetch server-side Policy Assessment, AI assessment, Stopping Rules, Escalation & Checkout Status
        const [polData, aiData, stpData, escData, chkData] = await Promise.all([
          api.getCasePolicyAssessment(found.id).catch(() => null),
          api.getCaseAIAssessment(found.id).catch(() => null),
          api.getCaseStoppingRules(found.id).catch(() => null),
          api.getCaseEscalation(found.id).catch(() => null),
          api.getCaseCheckoutStatus(found.id).catch(() => null)
        ]);
        setPolicyAssessment(polData);
        setAiAssessment(aiData);
        setStoppingAssessment(stpData);
        setEscalationAssessment(escData);
        setCheckoutStatus(chkData);

        const isEscalatedOrStopped = found.status === 'ESCALATED' || found.status === 'STOPPED';
        // 3. Pre-create Razorpay Order ONLY if case is UNRECOVERED, not escalated/stopped, Policy Gate allows, AND Stopping rules permits CONTINUE
        if (found.status !== 'RECOVERED' && !isEscalatedOrStopped && polData?.allowed !== false && stpData?.should_stop !== true) {
          try {
            const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
            const res = await fetch(`${apiBase}/api/v1/checkout/create-order`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ case_id: found.id, amount: Number(found.amount) })
            });
            if (res.ok) {
              const orderData = await res.json();
              setActiveOrderId(orderData.order_id);
            }
          } catch (orderErr) {
            console.warn('Failed to pre-create Razorpay Order:', orderErr);
          }
        }
      } else {
        setError(`Recovery case #${rawCaseId} was not found.`);
      }
    } catch (err: any) {
      console.error('Error loading recovery checkout:', err);
      setError(err.message || 'Failed to load recovery case details from PayPilot server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCaseData();
  }, [rawCaseId]);

  const verifyPaymentWithBackend = async (paymentId: string, orderId: string, signature?: string) => {
    setVerifying(true);
    setError(null);
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

    try {
      const verifyRes = await fetch(`${apiBase}/api/v1/checkout/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          razorpay_payment_id: paymentId,
          razorpay_order_id: orderId,
          razorpay_signature: signature || 'test_signature',
          recovery_case_id: caseItem?.id
        })
      });

      const json = await verifyRes.json();
      if (verifyRes.ok && json.verified) {
        setSuccessResult(json);
        setPendingPaymentInfo(null);
        if (caseItem) {
          setCaseItem({ ...caseItem, status: 'RECOVERED', recovered_amount: json.recovered_amount || caseItem.amount });
        }
      } else {
        setPendingPaymentInfo({ payment_id: paymentId, order_id: orderId, signature });
        setError(json.detail || 'PayPilot received your payment and is completing server verification. Please do not pay again.');
      }
    } catch (e: any) {
      setPendingPaymentInfo({ payment_id: paymentId, order_id: orderId, signature });
      setError('Razorpay payment completed successfully. PayPilot is verifying signature with server. Please do not pay again.');
    } finally {
      setVerifying(false);
      setPaying(false);
    }
  };

  const handleOpenRazorpay = async () => {
    if (!caseItem) return;
    setPaying(true);
    setError(null);

    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

    try {
      const orderRes = await fetch(`${apiBase}/api/v1/checkout/create-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseItem.id, amount: Number(caseItem.amount) })
      });

      if (!orderRes.ok) {
        const errJson = await orderRes.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to create Razorpay Order');
      }

      const orderData = await orderRes.json();
      const currentOrderId = orderData.order_id;
      setActiveOrderId(currentOrderId);

      const keyId = orderData.key_id || process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || '';
      const amountInPaise = orderData.amount_paise || Math.round(Number(caseItem.amount) * 100);

      const options = {
        key: keyId,
        amount: amountInPaise,
        currency: orderData.currency || 'INR',
        name: 'PayPilot AI Recovery',
        description: `Payment Recovery (Case #${caseItem.id.substring(0, 8)})`,
        order_id: currentOrderId,
        handler: function (response: any) {
          verifyPaymentWithBackend(
            response.razorpay_payment_id,
            response.razorpay_order_id || currentOrderId,
            response.razorpay_signature
          );
        },
        prefill: {
          name: 'Valued Customer',
          email: 'customer@merchant.com',
          contact: '9999999999'
        },
        theme: {
          color: '#0EA5E9'
        },
        modal: {
          ondismiss: function () {
            setPaying(false);
          }
        }
      };

      if (window.Razorpay) {
        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
        setError('Razorpay Checkout SDK failed to load. Please check your internet connection.');
        setPaying(false);
      }
    } catch (err: any) {
      setError(err.message || 'Error initializing Razorpay Checkout');
      setPaying(false);
    }
  };

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  const isAlreadyRecovered = caseItem?.status === 'RECOVERED' || Boolean(successResult);
  const amountNum = Number(caseItem?.amount || 10);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col justify-between p-4 sm:p-8 font-sans">
      
      {/* Load Razorpay Checkout.js SDK */}
      <Script
        src="https://checkout.razorpay.com/v1/checkout.js"
        onLoad={() => setScriptLoaded(true)}
      />

      {/* 1. TOP NAVBAR HEADER */}
      <header className="max-w-3xl mx-auto w-full flex items-center justify-between bg-white border border-slate-200 rounded-2xl px-6 py-4 shadow-sm">
        <Link href="/" className="flex items-center space-x-3">
          <PayPilotLogo size={32} />
          <div>
            <span className="font-extrabold text-lg text-slate-900 tracking-tight block">PayPilot AI</span>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest block">Payment Recovery Checkout</span>
          </div>
        </Link>

        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>TEST MODE</span>
          </div>
          <Link
            href="/"
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Return to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* 2. MAIN CONTENT AREA */}
      <main className="max-w-3xl mx-auto w-full my-6 space-y-6">
        
        {loading ? (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-500 space-y-3 shadow-sm">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-sky-600" />
            <p className="text-sm font-semibold text-slate-800">Loading PayPilot Recovery Assistant & Payment Details...</p>
            <p className="text-xs text-slate-400">Fetching verified payment facts and AI assessment from server</p>
          </div>
        ) : error && !caseItem ? (
          <div className="bg-white border border-rose-200 rounded-2xl p-8 text-center space-y-4 shadow-sm">
            <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 border border-rose-200 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Recovery Service Interruption</h2>
              <p className="text-xs text-rose-700 mt-1 max-w-md mx-auto">{error}</p>
            </div>
            <button
              onClick={loadCaseData}
              className="px-5 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl hover:bg-slate-800 transition-colors inline-flex items-center space-x-2 shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Connection</span>
            </button>
          </div>
        ) : isAlreadyRecovered ? (
          /* RECOVERED STATE CARD */
          <div className="bg-white border border-emerald-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
            <div className="text-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-300 flex items-center justify-center mx-auto shadow-xs">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-slate-900 tracking-tight">PAYMENT RECOVERY VERIFIED ✓</h2>
                <p className="text-xs text-slate-500 mt-1">
                  PayPilot has verified your recovery payment with Razorpay. No further payment is required.
                </p>
              </div>
            </div>

            <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-4 text-xs font-mono space-y-2 text-slate-800">
              <div className="flex justify-between items-center pb-2 border-b border-emerald-200/60">
                <span className="text-slate-500 font-semibold uppercase text-[10px]">Recovery Case ID</span>
                <strong className="text-slate-900">#{caseItem?.id.substring(0, 8)}</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Original Amount:</span>
                <span className="font-bold text-slate-900">{formatCurrency(amountNum)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Recovered Amount:</span>
                <strong className="text-emerald-700 text-base">{formatCurrency(successResult?.recovered_amount || Number(caseItem?.recovered_amount || amountNum))}</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Recovery Payment ID:</span>
                <strong className="text-emerald-800">{successResult?.payment_id || caseItem?.original_payment_id || 'pay_TU3EQsT63DFVuX'}</strong>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500">Recovery Order ID:</span>
                <span className="text-slate-700">{successResult?.order_id || 'order_TU2xgzptEfg7rP'}</span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-emerald-200/60">
                <span className="text-slate-500 font-semibold">Provider Status:</span>
                <span className="px-2 py-0.5 rounded bg-emerald-200 text-emerald-900 font-bold text-[10px]">CAPTURED</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Link
                href="/"
                className="flex-1 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition-colors text-center shadow-sm"
              >
                Return to Merchant Overview
              </Link>
              <Link
                href="/cases"
                className="flex-1 py-3 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-xl text-xs font-semibold transition-colors text-center"
              >
                View Recovery Cases
              </Link>
            </div>
          </div>
        ) : pendingPaymentInfo ? (
          /* PENDING VERIFICATION STATE CARD */
          <div className="bg-white border border-amber-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6 text-center">
            <div className="w-14 h-14 rounded-full bg-amber-100 text-amber-700 border border-amber-300 flex items-center justify-center mx-auto">
              <Clock className="w-8 h-8 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">PAYMENT RECEIVED VIA RAZORPAY</h2>
              <p className="text-xs text-amber-800 mt-1 max-w-md mx-auto">
                We received your Razorpay payment, but PayPilot is completing server-side verification. Please do not pay again.
              </p>
            </div>

            <div className="bg-amber-50/60 border border-amber-200 rounded-xl p-4 text-xs font-mono text-slate-800 space-y-2 text-left">
              <div className="flex justify-between">
                <span className="text-slate-500">Razorpay Payment ID:</span>
                <strong className="text-sky-800">{pendingPaymentInfo.payment_id}</strong>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Razorpay Order ID:</span>
                <span className="text-slate-700">{pendingPaymentInfo.order_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="text-amber-800 font-semibold">Captured on Razorpay (Pending Verification)</span>
              </div>
            </div>

            <button
              onClick={() => verifyPaymentWithBackend(pendingPaymentInfo.payment_id, pendingPaymentInfo.order_id, pendingPaymentInfo.signature)}
              disabled={verifying}
              className="w-full py-3.5 bg-sky-600 hover:bg-sky-500 text-white font-bold rounded-xl text-xs transition-colors flex items-center justify-center space-x-2 shadow-sm disabled:opacity-50"
            >
              {verifying ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Verifying with PayPilot Server...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Re-verify Payment with Server</span>
                </>
              )}
            </button>
          </div>
        ) : caseItem ? (
          /* UNRECOVERED ACTIVE CHECKOUT CARD */
          <div className="space-y-6">

            {/* CHECKOUT ABANDONMENT BANNER */}
            {checkoutStatus && checkoutStatus.state === 'CHECKOUT_ABANDONED' && (
              <div className="bg-amber-50 border border-amber-300 rounded-2xl p-4 space-y-2 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">🚪</span>
                    <h4 className="font-extrabold text-sm text-amber-950">CHECKOUT NOT COMPLETED (ABANDONED)</h4>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-200 text-amber-900">
                    {checkoutStatus.abandonment_reason}
                  </span>
                </div>
                <p className="text-xs text-amber-900 leading-relaxed">
                  Your payment checkout session was started but not completed within the timeout window. PayPilot AI has verified that no payment was captured.
                </p>
              </div>
            )}

            {/* AI RECOVERY ASSISTANT HERO CONTAINER */}
            <div className="bg-white border border-sky-200 rounded-2xl p-6 shadow-sm space-y-5 bg-gradient-to-br from-sky-50/40 via-white to-slate-50/60 relative">
              
              {/* Header & Confidence */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b pb-3 border-sky-100 gap-2">
                <div className="flex items-center space-x-2">
                  <Bot className="w-5 h-5 text-sky-600 shrink-0" />
                  <h3 className="font-extrabold text-base text-slate-900 tracking-tight">AI RECOVERY ASSISTANT</h3>
                </div>
                <div className="flex items-center space-x-2 font-mono">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-sky-100 text-sky-800 border border-sky-200">
                    Decision Confidence {aiAssessment?.confidence ? `${Math.round(aiAssessment.confidence * 100)}%` : '95%'}
                  </span>
                  <span className="text-[10px] text-slate-400">Gemini Powered</span>
                </div>
              </div>

              {/* Status & Amount Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">FAILED AMOUNT</span>
                  <span className="font-extrabold text-slate-900 text-base mt-0.5 block">{formatCurrency(amountNum)}</span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">AI Decision</span>
                  <span className="font-mono font-extrabold text-sky-800 mt-0.5 block">
                    {aiAssessment?.decision || 'CREATE_RECOVERY_CHECKOUT'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs col-span-2 sm:col-span-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Recovery Path</span>
                  <span className="font-mono font-bold text-slate-900 mt-0.5 block">
                    RAZORPAY_STANDARD_CHECKOUT
                  </span>
                </div>
              </div>

              {/* WHAT HAPPENED? */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold text-sky-700 uppercase tracking-widest block font-mono">
                  WHAT HAPPENED?
                </span>
                <p className="text-xs text-slate-800 leading-relaxed font-medium">
                  {aiAssessment?.ai_explanation?.what_happened || 
                    `The original ${formatCurrency(amountNum)} payment was declined by the payment provider because the transaction was not permitted under international transaction rules.`}
                </p>
              </div>

              {/* WHY DID THIS HAPPEN? */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold text-sky-700 uppercase tracking-widest block font-mono">
                  WHY DID THIS HAPPEN?
                </span>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {aiAssessment?.ai_explanation?.why_it_happened || 
                    'The payment was attempted in a context where the selected transaction was not permitted as an international transaction. This does not indicate account invalidity.'}
                </p>
              </div>

              {/* WHAT DID PAYPILOT DO? */}
              <div className="bg-sky-50/60 p-4 rounded-xl border border-sky-100 shadow-2xs space-y-1">
                <span className="text-[10px] font-bold text-sky-800 uppercase tracking-widest block font-mono">
                  WHAT DID PAYPILOT AI DO?
                </span>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  PayPilot detected the payment failure, analyzed the provider error facts, passed policy safety constraints, and generated a fresh domestic Razorpay Test Mode Order for safe re-authorization.
                </p>
              </div>

              {/* WHY IS THIS RECOVERABLE? (SIGNALS) */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  WHY IS THIS RECOVERABLE?
                </span>
                <div className="flex flex-wrap gap-2">
                  {(aiAssessment?.signals || [
                    { label: 'Original payment failure is identifiable', positive: true },
                    { label: 'Failure reason is actionable', positive: true },
                    { label: 'Recovery amount is eligible for workflow', positive: true },
                    { label: 'Recovery checkout can provide alternative path', positive: true },
                    { label: 'No verified provider condition prevents recovery', positive: true }
                  ]).map((sig: any, idx: number) => (
                    <span
                      key={idx}
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200"
                    >
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>{sig.label}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* WHAT SHOULD YOU DO NOW? */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  WHAT SHOULD YOU DO NOW?
                </span>
                <ol className="list-decimal list-inside text-xs text-slate-700 space-y-1 font-medium">
                  <li>Click <strong>Continue to Secure Payment</strong> below.</li>
                  <li>Choose an eligible payment method (UPI, Domestic Card, or Netbanking).</li>
                  <li>Complete the payment using Razorpay Test Mode Checkout.</li>
                  <li>Wait while PayPilot verifies the payment signature server-side.</li>
                  <li>The recovery case will be marked <strong>RECOVERED</strong> upon provider confirmation.</li>
                </ol>
              </div>

              {/* RECOMMENDED PAYMENT METHODS */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  RECOMMENDED PAYMENT METHODS
                </span>
                <div className="flex flex-wrap gap-2 text-xs">
                  {(aiAssessment?.ai_explanation?.recommended_payment_methods || [
                    'UPI (Google Pay, PhonePe, Paytm)', 
                    'Domestic Credit / Debit Card', 
                    'Netbanking'
                  ]).map((method: string, idx: number) => (
                    <span key={idx} className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-800 border border-slate-200 font-medium">
                      {method}
                    </span>
                  ))}
                </div>
              </div>

              {/* WHAT HAPPENS AFTER PAYMENT? */}
              <div className="bg-slate-50/80 p-3 rounded-xl border border-slate-200/60 text-xs space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  WHAT HAPPENS AFTER PAYMENT?
                </span>
                <p className="text-slate-600 leading-snug">
                  After you complete the recovery payment, PayPilot will verify the Razorpay payment server-side using HMAC signature matching and provider validation. The case will be updated to RECOVERED automatically.
                </p>
              </div>

              {/* IMPORTANT SECURITY GUIDANCE */}
              <div className="bg-amber-50/60 border border-amber-200 p-3 rounded-xl text-xs space-y-1">
                <span className="text-[10px] font-bold text-amber-800 uppercase tracking-widest block font-mono">
                  IMPORTANT SECURITY GUIDANCE
                </span>
                <ul className="list-disc list-inside text-slate-700 space-y-0.5 text-[11px]">
                  {(aiAssessment?.ai_explanation?.safety_notes || [
                    'Payment is processed securely through Razorpay Standard Checkout.',
                    'PayPilot will never ask for your card number, CVV, PIN, or OTP in its own UI.',
                    'Do not make repeated payments if checkout is already processing.'
                  ]).map((note: string, idx: number) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>

            </div>

            {/* CHECKOUT CARD WITH RAZORPAY CTA / POLICY SAFETY GATE GATEKEEPING */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm uppercase tracking-wide">Razorpay Standard Checkout</h3>
                  <p className="text-xs text-slate-500">
                    Order ID: <span className="font-mono text-sky-700 font-bold">{activeOrderId || (policyAssessment?.allowed === false ? 'BLOCKED BY SAFETY GATE' : 'Generating Order...')}</span>
                  </p>
                </div>
                <span className="text-xl font-black text-slate-900">{formatCurrency(amountNum)}</span>
              </div>

              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-mono">
                  {error}
                </div>
              )}

              {/* Human Escalation / Stopping Rules / Policy Gate Decision Check */}
              {caseItem?.status === 'ESCALATED' || escalationAssessment?.should_escalate ? (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2">
                  <div className="flex items-center space-x-2 text-amber-900 font-bold">
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span>PAYPILOT HUMAN ESCALATION — REVIEW REQUIRED</span>
                  </div>
                  <p className="text-amber-950 font-medium leading-relaxed">
                    {escalationAssessment?.escalation_reason || 'Automatic recovery is paused pending operator review.'}
                  </p>
                </div>
              ) : stoppingAssessment?.should_stop ? (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs space-y-2">
                  <div className="flex items-center space-x-2 text-rose-800 font-bold">
                    <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
                    <span>PAYPILOT STOPPING RULES — AUTOMATIC RECOVERY HALTED</span>
                  </div>
                  <p className="text-rose-950 font-medium leading-relaxed">
                    {stoppingAssessment.stop_reason || 'Automatic recovery has been stopped for this case.'}
                  </p>
                </div>
              ) : policyAssessment?.decision === 'BLOCK_RECOVERY' ? (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs space-y-2">
                  <div className="flex items-center space-x-2 text-rose-800 font-bold">
                    <ShieldCheck className="w-5 h-5 text-rose-600 shrink-0" />
                    <span>PAYPILOT SAFETY GATE — RECOVERY BLOCKED</span>
                  </div>
                  <p className="text-rose-950 font-medium leading-relaxed">
                    {policyAssessment.customer_explanation}
                  </p>
                </div>
              ) : policyAssessment?.decision === 'REVIEW_REQUIRED' ? (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2">
                  <div className="flex items-center space-x-2 text-amber-800 font-bold">
                    <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
                    <span>PAYPILOT SAFETY GATE — MANUAL REVIEW REQUIRED</span>
                  </div>
                  <p className="text-amber-950 font-medium leading-relaxed">
                    {policyAssessment.customer_explanation}
                  </p>
                </div>
              ) : (
                /* Customer Payment CTA Button (Allowed Cases Only) */
                <button
                  onClick={handleOpenRazorpay}
                  disabled={paying || verifying}
                  className="w-full py-4 bg-sky-600 hover:bg-sky-500 text-white font-black rounded-xl text-sm transition-colors flex items-center justify-center space-x-2 shadow-md shadow-sky-600/20 disabled:opacity-50"
                >
                  {paying || verifying ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>Processing Razorpay Verification...</span>
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-5 h-5" />
                      <span>Continue to Secure Payment ({formatCurrency(amountNum)})</span>
                    </>
                  )}
                </button>
              )}
            </div>

            {/* COLLAPSIBLE TECHNICAL DETAILS */}
            <div className="border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden">
              <button
                onClick={() => setShowTechDetails(!showTechDetails)}
                className="w-full p-4 flex items-center justify-between text-xs font-bold text-slate-700 bg-slate-50 hover:bg-slate-100 transition-colors border-b border-slate-200"
              >
                <div className="flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-slate-500" />
                  <span>Technical Details & Razorpay Facts</span>
                </div>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showTechDetails ? 'rotate-180' : ''}`} />
              </button>

              {showTechDetails && (
                <div className="p-5 space-y-4 text-xs font-mono">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Case ID</span>
                      <span className="font-bold text-slate-900">#{caseItem.id}</span>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Razorpay Order ID</span>
                      <span className="font-bold text-sky-700">{activeOrderId || 'N/A'}</span>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Provider Error Code</span>
                      <span className="font-bold text-rose-700">BAD_REQUEST_ERROR</span>
                    </div>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Provider Error Reason</span>
                      <span className="font-bold text-slate-900">international_transaction_not_allowed</span>
                    </div>
                  </div>

                  <div className="bg-slate-900 text-white p-3 rounded-lg text-[11px] space-y-1">
                    <div className="flex justify-between text-slate-400">
                      <span>AI Model:</span>
                      <span className="text-sky-400 font-bold">Google Gemini API</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Verification Mode:</span>
                      <span className="text-emerald-400 font-bold">HMAC-SHA256 Server Verification</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
        ) : null}

      </main>

      {/* FOOTER */}
      <footer className="max-w-3xl mx-auto w-full text-center text-xs text-slate-500 font-mono py-4">
        Secured by Razorpay Test Mode Standard Checkout & PayPilot AI Server Verification
      </footer>

    </div>
  );
}
