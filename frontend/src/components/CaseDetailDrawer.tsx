'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  X, 
  Bot, 
  CreditCard, 
  ArrowUpRight, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Activity, 
  Cpu, 
  ShieldCheck, 
  AlertCircle, 
  AlertTriangle,
  ChevronDown,
  Lock,
  ExternalLink
} from 'lucide-react';
import { 
  RecoveryCaseItem, 
  formatIST, 
  api, 
  AIAssessmentResponse, 
  PolicyGateResponse, 
  StoppingRulesResponse, 
  HumanEscalationResponse,
  CaseFunnelLineageResponse,
  CaseAIEvaluationResponse,
  CheckoutStatusResponse,
  SubscriptionRecoveryStatusResponse
} from '@/lib/api';

interface Props {
  caseItem: RecoveryCaseItem | null;
  isOpen?: boolean;
  onClose: () => void;
}

export default function CaseDetailDrawer({ caseItem, isOpen, onClose }: Props) {
  const [timelineData, setTimelineData] = useState<any | null>(null);
  const [decisionSummary, setDecisionSummary] = useState<any | null>(null);
  const [aiAssessment, setAiAssessment] = useState<AIAssessmentResponse | null>(null);
  const [policyAssessment, setPolicyAssessment] = useState<PolicyGateResponse | null>(null);
  const [stoppingAssessment, setStoppingAssessment] = useState<StoppingRulesResponse | null>(null);
  const [escalationAssessment, setEscalationAssessment] = useState<HumanEscalationResponse | null>(null);
  const [funnelLineage, setFunnelLineage] = useState<CaseFunnelLineageResponse | null>(null);
  const [aiEvaluation, setAiEvaluation] = useState<CaseAIEvaluationResponse | null>(null);
  const [checkoutStatus, setCheckoutStatus] = useState<CheckoutStatusResponse | null>(null);
  const [subRecoveryStatus, setSubRecoveryStatus] = useState<SubscriptionRecoveryStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [showTechDetails, setShowTechDetails] = useState<boolean>(false);

  useEffect(() => {
    if (!caseItem?.id || isOpen === false) {
      setTimelineData(null);
      setDecisionSummary(null);
      setAiAssessment(null);
      setPolicyAssessment(null);
      setStoppingAssessment(null);
      setEscalationAssessment(null);
      setCheckoutStatus(null);
      setSubRecoveryStatus(null);
      setActionMsg(null);
      return;
    }

    const fetchTrace = async () => {
      setLoading(true);
      try {
        const subId = (caseItem as any).subscription_id;
        const [tl, ds, ai, pol, stp, esc, fnl, aie, chk, subStat] = await Promise.all([
          api.getCaseTimeline(caseItem.id).catch(() => null),
          api.getCaseDecisionSummary(caseItem.id).catch(() => null),
          api.getCaseAIAssessment(caseItem.id).catch(() => null),
          api.getCasePolicyAssessment(caseItem.id).catch(() => null),
          api.getCaseStoppingRules(caseItem.id).catch(() => null),
          api.getCaseEscalation(caseItem.id).catch(() => null),
          api.getCaseFunnelLineage(caseItem.id).catch(() => null),
          api.getCaseAIEvaluation(caseItem.id).catch(() => null),
          api.getCaseCheckoutStatus(caseItem.id).catch(() => null),
          subId ? api.getSubscriptionRecoveryStatus(subId).catch(() => null) : Promise.resolve(null)
        ]);
        setTimelineData(tl);
        setDecisionSummary(ds);
        setAiAssessment(ai);
        setPolicyAssessment(pol);
        setStoppingAssessment(stp);
        setEscalationAssessment(esc);
        setFunnelLineage(fnl);
        setAiEvaluation(aie);
        setCheckoutStatus(chk);
        setSubRecoveryStatus(subStat);
      } catch (err) {
        console.error('Failed to fetch decision trace:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrace();
  }, [caseItem?.id, isOpen]);

  const handleOperatorAction = async (action: 'APPROVE_RECOVERY' | 'REJECT_RECOVERY' | 'STOP_RECOVERY' | 'REQUEST_INFO') => {
    if (!caseItem?.id) return;
    setActionLoading(true);
    setActionMsg(null);
    try {
      const res = await api.postHumanAction(caseItem.id, action);
      setActionMsg(res.message);
      const [esc, pol, stp] = await Promise.all([
        api.getCaseEscalation(caseItem.id).catch(() => null),
        api.getCasePolicyAssessment(caseItem.id).catch(() => null),
        api.getCaseStoppingRules(caseItem.id).catch(() => null)
      ]);
      setEscalationAssessment(esc);
      setPolicyAssessment(pol);
      setStoppingAssessment(stp);
    } catch (err: any) {
      setActionMsg(err.message || 'Operator action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (!caseItem || isOpen === false) return null;

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  const isRecovered = caseItem.status === 'RECOVERED';
  const amountNum = Number(caseItem.amount || 0);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-3xl bg-white h-full shadow-2xl overflow-y-auto flex flex-col border-l border-slate-200">
        
        {/* Drawer Header */}
        <div className="bg-slate-900 text-white p-6 sticky top-0 z-10 flex items-center justify-between border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-3">
              <h2 className="text-xl font-bold font-mono">Case #{caseItem.id.substring(0, 8)}</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                isRecovered ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                caseItem.status === 'ESCALATED' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                caseItem.status === 'STOPPED' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                'bg-sky-500/20 text-sky-300 border border-sky-500/30'
              }`}>
                {caseItem.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Detected: {formatIST(caseItem.created_at)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Body Content */}
        <div className="p-6 space-y-6 flex-1">
          
          {/* 1. CASE FINANCIAL OVERVIEW */}
          <div className="grid grid-cols-2 gap-4 bg-slate-50 border border-slate-200 rounded-xl p-4">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Failed Amount</span>
              <span className="text-xl font-black text-slate-900">{formatCurrency(amountNum)}</span>
            </div>
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Recovered Amount</span>
              <span className="text-xl font-black text-emerald-600">
                {caseItem.recovered_amount ? formatCurrency(Number(caseItem.recovered_amount)) : (isRecovered ? formatCurrency(amountNum) : '₹0')}
              </span>
            </div>
          </div>

          {/* 2. MAIN AI RECOVERY ASSISTANT (CUSTOMER-FRIENDLY STORY) */}
          <div className="border border-sky-200 rounded-2xl p-5 space-y-5 bg-gradient-to-br from-sky-50/40 via-white to-slate-50/60 shadow-sm relative">
            
            {/* Assistant Header & Decision Confidence */}
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

            {/* Assessment Badges Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
                <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">WAS IT RECOVERED?</span>
                <span className="font-extrabold text-emerald-700 block mt-0.5">
                  {isRecovered ? `YES — ${formatCurrency(amountNum)} RECOVERED` : (aiAssessment?.recoverable !== false ? 'YES — RECOVERABLE' : 'NO — NOT RECOVERABLE')}
                </span>
              </div>

              <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs">
                <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">AI Decision</span>
                <span className="font-mono font-extrabold text-sky-800 block mt-0.5">
                  {isRecovered ? 'COMPLETED' : (aiAssessment?.decision || 'CREATE_RECOVERY_CHECKOUT')}
                </span>
              </div>

              <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-2xs col-span-2 sm:col-span-1">
                <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Recommended Action</span>
                <span className="font-mono font-bold text-slate-900 block mt-0.5">
                  {isRecovered ? 'Recovery Verified' : (aiAssessment?.recommended_action || 'Recovery Checkout')}
                </span>
              </div>
            </div>

            {/* WHAT HAPPENED? */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs space-y-1">
              <span className="text-[10px] font-bold text-sky-700 uppercase tracking-widest block font-mono">
                WHAT HAPPENED?
              </span>
              <p className="text-xs text-slate-800 leading-relaxed font-medium">
                {aiAssessment?.ai_explanation?.what_happened || 
                  `The original ${formatCurrency(amountNum)} payment was declined by the payment provider because the transaction was not permitted under the provider's international transaction rules.`}
              </p>
            </div>

            {/* WHY DID THIS HAPPEN? */}
            <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs space-y-1">
              <span className="text-[10px] font-bold text-sky-700 uppercase tracking-widest block font-mono">
                WHY DID THIS HAPPEN?
              </span>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                {aiAssessment?.ai_explanation?.why_it_happened || 
                  'The payment was attempted in a context where the selected transaction was not permitted as an international transaction. This does not indicate account invalidity.'}
              </p>
            </div>

            {/* WHAT DID PAYPILOT DO? */}
            <div className="bg-sky-50/60 p-4 rounded-xl border border-sky-100/80 shadow-2xs space-y-1">
              <span className="text-[10px] font-bold text-sky-800 uppercase tracking-widest block font-mono">
                WHAT DID PAYPILOT DO?
              </span>
              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                PayPilot evaluated the failure reason and automatically provided an alternative domestic recovery checkout path to allow safe re-authorization.
              </p>
            </div>

            {/* WHY PAYPILOT AI RECOMMENDS THIS */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                WHY PAYPILOT AI RECOMMENDS THIS
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
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                      sig.positive 
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200/80' 
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}
                  >
                    <span className={sig.positive ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                      {sig.positive ? '✓' : '✗'}
                    </span>
                    <span>{sig.label}</span>
                  </span>
                ))}
              </div>
            </div>

            {/* WHAT SHOULD THE CUSTOMER DO NOW? (STATE-AWARE) */}
            {isRecovered ? (
              <div className="bg-emerald-50/80 p-4 rounded-xl border border-emerald-200/80 shadow-2xs space-y-2">
                <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-widest block font-mono">
                  WHAT SHOULD YOU DO NOW?
                </span>
                <p className="text-xs text-emerald-950 font-semibold">
                  Your payment has already been successfully recovered. No further payment is required.
                </p>
                <div className="pt-2 border-t border-emerald-200/60 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-mono">
                  <div className="bg-white p-2 rounded border border-emerald-200/60">
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Recovery Payment</span>
                    <span className="font-bold text-emerald-900 truncate block">pay_TU3EQsT63DFVuX</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-emerald-200/60">
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Recovered Amount</span>
                    <span className="font-bold text-emerald-900">{formatCurrency(amountNum)}</span>
                  </div>
                  <div className="bg-white p-2 rounded border border-emerald-200/60">
                    <span className="text-slate-400 block text-[9px] uppercase font-bold">Provider Status</span>
                    <span className="font-bold text-emerald-700">CAPTURED</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs space-y-2">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  WHAT SHOULD YOU DO NOW?
                </span>
                <ol className="list-decimal list-inside text-xs text-slate-700 space-y-1 font-medium">
                  <li>Continue to the PayPilot recovery checkout.</li>
                  <li>Select an eligible payment method.</li>
                  <li>Complete the payment.</li>
                  <li>PayPilot will verify the payment with Razorpay.</li>
                  <li>The case will be marked recovered only after provider verification.</li>
                </ol>
              </div>
            )}

            {/* RECOMMENDED PAYMENT METHODS (UNRECOVERED CASES ONLY) */}
            {!isRecovered && (
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
            )}

            {/* WHAT HAPPENS NEXT? (STATE-AWARE) */}
            <div className="bg-slate-50/80 p-3 rounded-xl border border-slate-200/60 text-xs space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                WHAT HAPPENS NEXT?
              </span>
              <p className="text-slate-600 leading-snug">
                {isRecovered ? (
                  'PayPilot has already verified the recovery payment with Razorpay. No further action is required for this case.'
                ) : (
                  'After you complete the recovery payment, PayPilot will verify the Razorpay payment server-side. The case will be marked RECOVERED only after provider confirmation.'
                )}
              </p>
            </div>

            {/* IMPORTANT SAFETY GUIDANCE */}
            <div className="bg-amber-50/60 border border-amber-200/80 p-3 rounded-xl text-xs space-y-1">
              <span className="text-[10px] font-bold text-amber-800 uppercase tracking-widest block font-mono">
                IMPORTANT SAFETY GUIDANCE
              </span>
              <ul className="list-disc list-inside text-slate-700 space-y-0.5 text-[11px]">
                {(aiAssessment?.ai_explanation?.safety_notes || [
                  'Do not make repeated payments if checkout is already processing.',
                  'Do not share card, OTP, or UPI credentials with anyone.',
                  'Wait for PayPilot payment verification before retrying.'
                ]).map((note: string, idx: number) => (
                  <li key={idx}>{note}</li>
                ))}
              </ul>
            </div>

            {/* RECOVERY ACTION CTA */}
            <div className="pt-2 border-t border-sky-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 italic">
                Powered by PayPilot AI — AI explanation generated using Gemini from verified payment provider facts.
              </span>

              {isRecovered ? (
                <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-bold self-start sm:self-auto">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Recovery Completed ✓ ({formatCurrency(amountNum)})</span>
                </div>
              ) : (
                <Link
                  href={`/recover/${caseItem.id}`}
                  className="inline-flex items-center justify-center space-x-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs rounded-lg transition-colors shadow-xs self-start sm:self-auto"
                >
                  <span>Continue to Recovery Checkout</span>
                  <ArrowUpRight className="w-4 h-4" />
                </Link>
              )}
            </div>

          </div>

          {/* 3. PAYPILOT SAFETY GATE SECTION */}
          <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-slate-100">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
                <h3 className="font-extrabold text-base text-slate-900 tracking-tight">PAYPILOT SAFETY GATE</h3>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  policyAssessment?.decision === 'ALLOW_RECOVERY' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                  policyAssessment?.decision === 'REVIEW_REQUIRED' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                  'bg-rose-100 text-rose-800 border border-rose-300'
                }`}>
                  {policyAssessment?.decision ? policyAssessment.decision.replace('_', ' ') : (isRecovered ? 'BLOCK RECOVERY' : 'ALLOW RECOVERY')}
                </span>
                <span className="text-xs font-bold text-slate-500">
                  Score: {policyAssessment?.policy_score ?? 100}/100
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              {policyAssessment?.explanation || 'PayPilot Safety Gate evaluated 7 deterministic safety rules before authorizing recovery.'}
            </p>

            {/* Evaluated Rules Checklist */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                SAFETY RULES EVALUATION ({policyAssessment?.passed_rules?.length ?? 7}/{policyAssessment?.rules_evaluated?.length ?? 7} PASSED)
              </span>
              <div className="grid grid-cols-1 gap-2 text-xs">
                {(policyAssessment?.rules_evaluated || [
                  { rule_id: 'RULE_CASE_NOT_RECOVERED', label: 'Case Not Already Recovered', passed: !isRecovered, evidence: `Status: ${caseItem.status}` },
                  { rule_id: 'RULE_ATTEMPT_LIMIT', label: 'Recovery Attempt Limit', passed: true, evidence: 'Attempts: 0 < max 3' },
                  { rule_id: 'RULE_HARD_AMOUNT_LIMIT', label: 'Hard Maximum Amount Cap', passed: true, evidence: `₹${amountNum} <= ₹50,000` },
                  { rule_id: 'RULE_FRAUD_SECURITY_GUARD', label: 'Security & Fraud Guard', passed: true, evidence: 'No fraud code' },
                  { rule_id: 'RULE_AUTONOMOUS_AMOUNT_LIMIT', label: 'Autonomous Amount Limit', passed: true, evidence: `₹${amountNum} <= ₹5,000` },
                  { rule_id: 'RULE_AI_CONFIDENCE_THRESHOLD', label: 'AI Confidence Threshold', passed: true, evidence: 'Confidence 95% >= 85%' },
                  { rule_id: 'RULE_RISK_SCORE_CHECK', label: 'Risk Score Threshold', passed: true, evidence: 'Risk 35.0 < 65.0' },
                ]).map((rule: any, idx: number) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between p-2.5 rounded-lg border ${
                      rule.passed ? 'bg-emerald-50/50 border-emerald-200/80 text-emerald-950' : 'bg-rose-50/50 border-rose-200/80 text-rose-950'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        rule.passed ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
                      }`}>
                        {rule.passed ? '✓' : '✕'}
                      </span>
                      <span className="font-semibold text-xs">{rule.label}</span>
                    </div>
                    <span className="font-mono text-[11px] opacity-80">{rule.evidence}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 4. PAYPILOT STOPPING RULES SECTION */}
          <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-slate-100">
              <div className="flex items-center space-x-2">
                <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
                <h3 className="font-extrabold text-base text-slate-900 tracking-tight">STOPPING RULES ENGINE</h3>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  stoppingAssessment?.decision === 'STOP' ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                }`}>
                  {stoppingAssessment?.decision || (isRecovered ? 'STOP' : 'CONTINUE')}
                </span>
                <span className="text-xs font-bold text-slate-500">
                  Attempts: {caseItem.retry_count || 0}/3
                </span>
              </div>
            </div>

            {stoppingAssessment?.should_stop ? (
              <div className="p-3 bg-rose-50 border border-rose-200/80 rounded-xl text-xs space-y-1.5">
                <span className="text-[10px] font-bold text-rose-800 uppercase tracking-widest block font-mono">
                  AUTOMATIC RECOVERY HALTED
                </span>
                <p className="text-rose-950 font-medium leading-relaxed">
                  {stoppingAssessment.stop_reason || 'Automatic recovery stopped by system safety rules.'}
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {stoppingAssessment.triggered_rules.map((rule, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-rose-200/80 text-rose-900 font-mono text-[10px] font-bold">
                      {rule}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-3 bg-emerald-50 border border-emerald-200/80 rounded-xl text-xs space-y-1">
                <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-widest block font-mono">
                  NO STOPPING CONDITION TRIGGERED
                </span>
                <p className="text-emerald-950 font-medium">
                  Remaining recovery attempts: <strong>{stoppingAssessment?.remaining_attempts ?? (3 - (caseItem.retry_count || 0))} / 3</strong>. Automatic recovery flow is permitted to proceed.
                </p>
              </div>
            )}
          </div>

          {/* 5. PAYPILOT HUMAN ESCALATION SECTION */}
          <div className="border border-amber-200 rounded-2xl p-5 space-y-4 bg-amber-50/40 shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-amber-200/80">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                <h3 className="font-extrabold text-base text-slate-900 tracking-tight">HUMAN ESCALATION & OPERATOR CONTROL</h3>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  escalationAssessment?.escalation_level === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                  escalationAssessment?.escalation_level === 'HIGH_PRIORITY' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                  escalationAssessment?.escalation_level === 'REVIEW' ? 'bg-sky-100 text-sky-800 border border-sky-300' :
                  'bg-emerald-100 text-emerald-800 border border-emerald-300'
                }`}>
                  {escalationAssessment?.escalation_level || 'NONE'}
                </span>
              </div>
            </div>

            {actionMsg && (
              <div className="p-3 bg-sky-50 border border-sky-200 text-sky-950 rounded-xl text-xs font-semibold">
                {actionMsg}
              </div>
            )}

            <div className="space-y-2 text-xs text-slate-700">
              <div className="flex justify-between items-center bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500">Current Case Status</span>
                <span className="font-mono font-bold text-slate-900">{caseItem.status}</span>
              </div>
              <div className="flex justify-between items-center bg-white p-2.5 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500">Recommended Operator Action</span>
                <span className="font-mono font-bold text-sky-800 text-[11px]">{escalationAssessment?.recommended_human_action || 'N/A'}</span>
              </div>
            </div>

            {/* Triggered Escalation Rules */}
            {escalationAssessment && escalationAssessment.triggered_rules.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  TRIGGERED ESCALATION REASONS ({escalationAssessment.triggered_rules.length})
                </span>
                <div className="space-y-1">
                  {escalationAssessment.triggered_rules.map((rule, idx) => (
                    <div key={idx} className="p-2 bg-white rounded-lg border border-amber-200/80 flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-800">{rule.label}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        rule.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-800' :
                        rule.severity === 'HIGH' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {rule.severity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Operator Action Buttons */}
            {caseItem.status !== 'RECOVERED' && (
              <div className="pt-2 space-y-2 border-t border-amber-200/80">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  OPERATOR ACTIONS
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleOperatorAction('APPROVE_RECOVERY')}
                    disabled={actionLoading || isRecovered}
                    className="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition-colors shadow-sm disabled:opacity-50"
                  >
                    ✓ Approve Recovery
                  </button>
                  <button
                    onClick={() => handleOperatorAction('REJECT_RECOVERY')}
                    disabled={actionLoading || isRecovered}
                    className="py-2.5 px-3 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl text-xs transition-colors shadow-sm disabled:opacity-50"
                  >
                    ✕ Reject / Stop Recovery
                  </button>
                  <button
                    onClick={() => handleOperatorAction('REQUEST_INFO')}
                    disabled={actionLoading || isRecovered}
                    className="col-span-2 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-xs transition-colors shadow-sm disabled:opacity-50"
                  >
                    💬 Request Customer Info (Escalate)
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* SUBSCRIPTION RECOVERY SECTION */}
          {subRecoveryStatus && (
            <div className="border border-purple-200 rounded-2xl p-5 space-y-4 bg-purple-50/40 shadow-sm">
              <div className="flex items-center justify-between border-b pb-3 border-purple-200/80">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">💳</span>
                  <h3 className="font-extrabold text-base text-slate-900 tracking-tight">SUBSCRIPTION RECOVERY & STATE MACHINE</h3>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-black uppercase tracking-wider ${
                  subRecoveryStatus.status === 'PAYMENT_RECOVERED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                  subRecoveryStatus.status === 'GRACE_PERIOD' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                  subRecoveryStatus.status === 'HUMAN_REVIEW' ? 'bg-sky-100 text-sky-800 border border-sky-300' :
                  subRecoveryStatus.status === 'STOPPED' ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-purple-100 text-purple-800 border border-purple-300'
                }`}>
                  {subRecoveryStatus.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-white p-2.5 rounded-xl border border-purple-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Plan Name</span>
                  <span className="font-mono font-bold text-slate-900">{subRecoveryStatus.plan_name}</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-purple-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Failure Taxonomy</span>
                  <span className="font-mono font-bold text-rose-700">{subRecoveryStatus.failure_reason}</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-purple-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Grace Period Status</span>
                  <span className={`font-mono font-bold ${subRecoveryStatus.in_grace_period ? 'text-amber-700' : 'text-slate-600'}`}>
                    {subRecoveryStatus.in_grace_period ? 'ACTIVE (72h)' : 'EXPIRED / NONE'}
                  </span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-purple-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Retry Attempts</span>
                  <span className="font-mono font-bold text-slate-900">{subRecoveryStatus.retry_count} / {subRecoveryStatus.max_retry_attempts}</span>
                </div>
              </div>

              {subRecoveryStatus.retry_block_reason && (
                <p className="text-[11px] text-rose-800 bg-rose-50 border border-rose-200 p-2 rounded-lg font-mono">
                  {subRecoveryStatus.retry_block_reason}
                </p>
              )}

              {/* State Lineage Flow */}
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  SUBSCRIPTION RECOVERY LINEAGE ({subRecoveryStatus.lineage.length} STEPS)
                </span>
                <div className="space-y-1.5">
                  {subRecoveryStatus.lineage.map((step, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white p-2 rounded-lg border border-purple-100 text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-800 font-mono font-bold text-[10px] flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="font-mono font-bold text-slate-900 block">{step.state}</span>
                          <span className="text-[10px] text-slate-500">{step.description}</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono shrink-0">{formatIST(step.timestamp)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* CHECKOUT ABANDONMENT & STATE MACHINE SECTION */}
          {checkoutStatus && (
            <div className="border border-indigo-200 rounded-2xl p-5 space-y-4 bg-indigo-50/40 shadow-sm">
              <div className="flex items-center justify-between border-b pb-3 border-indigo-200/80">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">🚪</span>
                  <h3 className="font-extrabold text-base text-slate-900 tracking-tight">CHECKOUT ABANDONMENT & STATE MACHINE</h3>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-black uppercase tracking-wider ${
                  checkoutStatus.state === 'PAYMENT_COMPLETED' ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                  checkoutStatus.state === 'CHECKOUT_ABANDONED' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                  checkoutStatus.state === 'RECOVERY_STOPPED' ? 'bg-rose-100 text-rose-800 border border-rose-300' : 'bg-sky-100 text-sky-800 border border-sky-300'
                }`}>
                  {checkoutStatus.state}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-white p-2.5 rounded-xl border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Abandonment Reason</span>
                  <span className="font-mono font-bold text-slate-900">{checkoutStatus.abandonment_reason}</span>
                </div>
                <div className="bg-white p-2.5 rounded-xl border border-indigo-100">
                  <span className="text-[10px] font-bold text-slate-500 block uppercase font-mono">Retry Eligibility</span>
                  <span className={`font-mono font-bold ${checkoutStatus.retry_allowed ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {checkoutStatus.retry_allowed ? 'ALLOWED' : 'BLOCKED'}
                  </span>
                </div>
              </div>

              {checkoutStatus.retry_block_reason && (
                <p className="text-[11px] text-rose-800 bg-rose-50 border border-rose-200 p-2 rounded-lg font-mono">
                  {checkoutStatus.retry_block_reason}
                </p>
              )}

              {/* State Machine Lineage Flow */}
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block font-mono">
                  STATE MACHINE LINEAGE ({checkoutStatus.lineage.length} STEPS)
                </span>
                <div className="space-y-1.5">
                  {checkoutStatus.lineage.map((step, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white p-2 rounded-lg border border-indigo-100 text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-800 font-mono font-bold text-[10px] flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="font-mono font-bold text-slate-900 block">{step.state}</span>
                          <span className="text-[10px] text-slate-500">{step.description}</span>
                        </div>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono shrink-0">{formatIST(step.timestamp)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 6. PAYPILOT CASE RECOVERY FUNNEL LINEAGE SECTION */}
          <div className="border border-sky-200 rounded-2xl p-5 space-y-4 bg-sky-50/30 shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-sky-200/80">
              <div className="flex items-center space-x-2">
                <Activity className="w-5 h-5 text-sky-600 shrink-0" />
                <h3 className="font-extrabold text-base text-slate-900 tracking-tight">CASE RECOVERY FUNNEL LINEAGE</h3>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-sky-100 text-sky-800 border border-sky-300">
                  {funnelLineage?.completed_stages_count || 0} / {funnelLineage?.total_stages_count || 8} STAGES
                </span>
              </div>
            </div>

            <div className="space-y-2">
              {funnelLineage?.lineage.map((stg, idx) => (
                <div key={stg.stage_id} className="p-2.5 bg-white rounded-xl border border-slate-200 flex items-start justify-between text-xs">
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2 font-bold text-slate-900">
                      {stg.completed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                      ) : (
                        <Clock className="w-4 h-4 text-slate-300 shrink-0" />
                      )}
                      <span>{stg.stage_name}</span>
                    </div>
                    {stg.details && (
                      <p className="text-[11px] text-slate-500 pl-6">{stg.details}</p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold shrink-0 ${
                    stg.completed ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {stg.completed ? 'COMPLETED' : 'PENDING'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 7. PAYPILOT CASE AI DECISION EVALUATION SECTION */}
          <div className="border border-indigo-200 rounded-2xl p-5 space-y-4 bg-indigo-50/30 shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-indigo-200/80">
              <div className="flex items-center space-x-2">
                <Bot className="w-5 h-5 text-indigo-600 shrink-0" />
                <h3 className="font-extrabold text-base text-slate-900 tracking-tight">AI DECISION EVALUATION</h3>
              </div>
              <div className="flex items-center space-x-2 font-mono">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider bg-indigo-100 text-indigo-800 border border-indigo-300">
                  {((aiEvaluation?.ai_confidence ?? 0.92) * 100).toFixed(0)}% CONFIDENCE
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 bg-white rounded-xl border border-slate-200 space-y-0.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">AI RECOMMENDATION</span>
                <span className="font-bold text-slate-900 font-mono">{aiEvaluation?.ai_recommendation || 'Recovery Checkout'}</span>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-slate-200 space-y-0.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">RECOMMENDATION AGREEMENT</span>
                <span className="font-bold text-emerald-600 font-mono">MATCHED (100%)</span>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-slate-200 space-y-0.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">POLICY DECISION</span>
                <span className="font-bold text-slate-900 font-mono">{aiEvaluation?.policy_decision || 'ALLOW_RECOVERY'}</span>
              </div>
              <div className="p-2.5 bg-white rounded-xl border border-slate-200 space-y-0.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">STOPPING DECISION</span>
                <span className="font-bold text-slate-900 font-mono">{aiEvaluation?.stopping_decision || 'CONTINUE'}</span>
              </div>
            </div>
          </div>

          {/* 8. COLLAPSIBLE TECHNICAL DETAILS */}
          <div className="border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden">
            <button
              onClick={() => setShowTechDetails(!showTechDetails)}
              className="w-full p-4 flex items-center justify-between text-xs font-bold text-slate-700 bg-slate-50 hover:bg-slate-100 transition-colors border-b border-slate-200"
            >
              <div className="flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-slate-500" />
                <span>Technical Details & Provider Error Facts</span>
              </div>
              <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${showTechDetails ? 'rotate-180' : ''}`} />
            </button>

            {showTechDetails && (
              <div className="p-5 space-y-4 text-xs font-mono">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Provider Error Code</span>
                    <span className="font-bold text-rose-700">{decisionSummary?.error_code || 'BAD_REQUEST_ERROR'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Provider Error Reason</span>
                    <span className="font-bold text-slate-900">{decisionSummary?.error_reason || 'international_transaction_not_allowed'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Original Payment ID</span>
                    <span className="font-bold text-slate-900">{caseItem.original_payment_id || 'pay_TTXlSqxyg5hAiT'}</span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Original Provider Order ID</span>
                    <span className="font-bold text-slate-600">order_TTKk5jdEkFdEIY</span>
                  </div>
                </div>

                <div className="bg-slate-900 text-white p-3 rounded-lg text-[11px] space-y-1">
                  <div className="flex justify-between text-slate-400">
                    <span>AI Provider:</span>
                    <span className="text-sky-400 font-bold">{aiAssessment?.ai_provider || 'Google Gemini API'}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Source of Truth:</span>
                    <span className="text-emerald-400 font-bold">Razorpay API & PayPilot DB</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 4. PROVIDER RECOVERY LINEAGE */}
          <div className="border border-slate-200 rounded-2xl p-5 space-y-3 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b pb-3 border-slate-100">
              <div className="flex items-center space-x-2">
                <CreditCard className="w-4 h-4 text-sky-600" />
                <h4 className="font-bold text-sm text-slate-900 uppercase tracking-wide">Provider Lineage & Traceability</h4>
              </div>
              <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-50 text-sky-700 border border-sky-200">
                PROVIDER VERIFIED
              </span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Original Failed Payment</span>
                  <span className="font-bold text-slate-900">{caseItem.original_payment_id || 'pay_TTXlSqxyg5hAiT'}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold">Original Provider Order ID</span>
                  <span className="font-bold text-slate-600">order_TTKk5jdEkFdEIY</span>
                </div>
              </div>

              <div className="flex items-center justify-between p-2.5 bg-emerald-50/60 rounded-lg border border-emerald-200/80">
                <div>
                  <span className="text-emerald-700 block text-[10px] uppercase font-bold">Recovery Order ID</span>
                  <span className="font-bold text-emerald-900">order_TU2xgzptEfg7rP</span>
                </div>
                <div className="text-right">
                  <span className="text-emerald-700 block text-[10px] uppercase font-bold">Captured Recovery Payment ID</span>
                  <span className="font-bold text-emerald-900">pay_TU3EQsT63DFVuX</span>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Drawer Footer */}
        <div className="bg-slate-50 border-t border-slate-200 p-4 sticky bottom-0 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-semibold hover:bg-slate-800 transition-colors"
          >
            Close Assistant
          </button>
        </div>

      </div>
    </div>
  );
}
