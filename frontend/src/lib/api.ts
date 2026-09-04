const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

export async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const isClient = typeof window !== 'undefined';
  const url = isClient && endpoint.startsWith('/') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const startTime = Date.now();
  console.log(`[API START] ${options?.method || 'GET'} ${url}`);
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout for AI / Gemini responses

    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        ...options?.headers,
      },
      cache: 'no-store',
    });
    clearTimeout(timeoutId);

    const elapsed = Date.now() - startTime;
    console.log(`[VOICE DEBUG 5] API HTTP status: ${res.status} ${res.statusText} (${elapsed}ms) for ${endpoint}`);

    if (!res.ok) {
      const status = res.status;
      let errorMsg = `HTTP ${status}`;
      try {
        const body = await res.json();
        errorMsg = body?.error?.message || body?.detail || errorMsg;
      } catch {
        errorMsg = res.statusText || errorMsg;
      }
      throw new Error(`API ${status}: ${errorMsg}`);
    }
    const json = await res.json();
    console.log(`[VOICE DEBUG 6] RAW API JSON (${elapsed}ms) for ${endpoint}:`, json);
    return json;
  } catch (error: any) {
    const elapsed = Date.now() - startTime;
    if (error.name === 'AbortError') {
      console.warn(`[VOICE DEBUG 8] Network timeout after ${elapsed}ms calling ${endpoint}`);
      throw new Error('Network timeout: Backend did not respond within 30s');
    }
    console.error(`[VOICE DEBUG 8] Fetch failed after ${elapsed}ms for ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Standardize display timestamps to Asia/Kolkata (IST) timezone.
 * Converts UTC strings to IST format for UI presentation without mutating database values.
 */
export function formatIST(dateInput: string | Date | null | undefined, includeDate = true): string {
  if (!dateInput) return 'N/A';
  let str = typeof dateInput === 'string' ? dateInput : dateInput.toISOString();
  
  if (typeof dateInput === 'string') {
    const timePortion = str.includes('T') ? str.split('T')[1] : str;
    const hasTz = timePortion.endsWith('Z') || timePortion.includes('+') || (timePortion.includes('-') && !timePortion.startsWith('-'));
    if (!hasTz) {
      str += 'Z';
    }
  }

  const date = new Date(str);
  if (isNaN(date.getTime())) return String(dateInput);

  const options: Intl.DateTimeFormatOptions = {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  };
  if (includeDate) {
    options.day = '2-digit';
    options.month = 'short';
    options.year = 'numeric';
  }
  return new Intl.DateTimeFormat('en-IN', options).format(date) + ' IST';
}

export function formatISTTimeOnly(dateInput: string | Date | null | undefined): string {
  return formatIST(dateInput, false);
}

export interface RazorpayHealthStatus {
  configured: boolean;
  test_mode: boolean;
  webhook_configured: boolean;
  status: string;
}

export interface AnalyticsMetrics {
  revenue_at_risk: number;
  payment_failure_risk?: number;
  checkout_dropoff_risk?: number;
  subscription_risk?: number;
  recovered_revenue: number;
  recovery_rate: number;
  failed_payments_count: number;
  checkout_dropoff_cases_count?: number;
  subscription_cases_count?: number;
  recovered_cases_count: number;
  recovery_attempts_count: number;
  policy_allowed_count: number;
  policy_blocked_count: number;
  escalated_count: number;
  remaining_risk: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion: number;
}

export interface ActivityItem {
  id: string;
  case_id: string | null;
  actor: string;
  event_type: string;
  description: string;
  metadata: Record<string, any>;
  timestamp: string;
}

export interface TransactionItem {
  id: string;
  merchant_id: string;
  customer_id: string | null;
  razorpay_payment_id: string | null;
  razorpay_order_id: string | null;
  amount: number;
  currency: string;
  status: string;
  error_code: string | null;
  error_description: string | null;
  error_source?: string | null;
  error_step?: string | null;
  error_reason?: string | null;
  payment_method: string | null;
  created_at: string;
  recovery_case_id?: string | null;
  recovery_status?: string | null;
}

export interface RecoveryCaseItem {
  id: string;
  case_type?: 'PAYMENT_FAILURE' | 'CHECKOUT_DROPOFF' | 'SUBSCRIPTION_FAILURE';
  merchant_id: string;
  transaction_id: string | null;
  original_payment_id?: string | null;
  checkout_session_id?: string | null;
  subscription_id?: string | null;
  customer_id: string | null;
  amount: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  priority_score: number;
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_factors: string[] | null;
  status: 'OPEN' | 'DIAGNOSED' | 'RECOVERY_PENDING' | 'RECOVERING' | 'RECOVERED' | 'FAILED' | 'ESCALATED' | 'STOPPED';
  ai_root_cause: string | null;
  ai_recommended_action: string | null;
  ai_confidence: number | null;
  ai_reasoning: string | null;
  policy_passed: boolean;
  policy_failure_reason: string | null;
  actual_action_taken: string | null;
  retry_count: number;
  recovered_amount: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluationRunSummary {
  run_id: string;
  run_name: string;
  seed: number;
  batch_size: number;
  mode: string;
  total_failed_amount: number;
  total_recovered: number;
  remaining_revenue_at_risk: number;
  diagnosed_count: number;
  policy_allowed_count: number;
  policy_blocked_count: number;
  escalated_count: number;
  recovery_attempt_count: number;
  recovered_count: number;
  failed_recovery_count: number;
  stopped_count: number;
  recovery_rate: number;
  recovery_success_rate: number;
  precision_rate: number;
  false_intervention_rate: number;
  escalation_rate: number;
  safe_stop_rate: number;
  created_at: string;
}

export interface CaseDetailEvaluation {
  case_num: number;
  amount: number;
  error_code: string;
  risk_level: string;
  risk_score: number;
  recoverability_score: number;
  ai_root_cause: string;
  ai_recommended_action: string;
  ai_confidence: number;
  policy_allowed: boolean;
  effective_action: string;
  policy_violations: string[];
  final_status: string;
  recovered_amount: number;
  simulation_notes: string;
}

export interface CustomerLoginResponse {
  customer_id: string;
  name: string;
  email?: string;
  auth_token: string;
}

export interface CustomerTransactionDetail {
  transaction_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_method?: string;
  error_code?: string;
  error_reason?: string;
  error_explanation: string;
  recovery_status?: string;
  recovery_link_url?: string;
  created_at: string;
}

export interface DecisionSignal {
  label: string;
  positive: boolean;
}

export interface ProviderFacts {
  payment_id?: string;
  order_id?: string;
  amount: number;
  currency: string;
  status: string;
  error_code?: string;
  error_reason?: string;
}

export interface AIExplanation {
  what_happened: string;
  why_it_happened: string;
  why_paypilot_recommends: string;
  customer_next_steps: string[];
  recommended_payment_methods: string[];
  what_happens_next: string;
  safety_notes: string[];
}

export interface AIAssessmentResponse {
  case_id: string;
  recoverable: boolean;
  decision: string;
  confidence: number;
  reason_code: string;
  why: string;
  signals: DecisionSignal[];
  recommended_action: string;
  failure_category?: string;
  provider_facts?: ProviderFacts;
  ai_explanation?: AIExplanation;
  ai_provider?: string;
  source_of_truth?: string;
  created_at?: string;
}

export interface PolicyRuleResult {
  rule_id: string;
  label: string;
  description: string;
  passed: boolean;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  evidence: string;
}

export interface PolicyGateResponse {
  case_id: string;
  decision: 'ALLOW_RECOVERY' | 'REVIEW_REQUIRED' | 'BLOCK_RECOVERY';
  allowed: boolean;
  requires_review: boolean;
  blocked: boolean;
  policy_score: number;
  rules_evaluated: PolicyRuleResult[];
  passed_rules: PolicyRuleResult[];
  failed_rules: PolicyRuleResult[];
  explanation: string;
  customer_explanation: string;
  recommended_action: string;
  evaluated_at: string;
}

export interface StoppingRulesResponse {
  case_id: string;
  decision: 'CONTINUE' | 'STOP';
  should_stop: boolean;
  stop_reason?: string;
  triggered_rules: string[];
  remaining_attempts: number;
  evaluated_at: string;
}

export interface EscalationTriggerRule {
  rule_id: string;
  label: string;
  description: string;
  severity: 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL';
}

export interface HumanEscalationResponse {
  case_id: string;
  should_escalate: boolean;
  escalation_level: 'NONE' | 'REVIEW' | 'HIGH_PRIORITY' | 'CRITICAL';
  escalation_reason?: string;
  triggered_rules: EscalationTriggerRule[];
  risk_score: number;
  amount: number;
  policy_decision: string;
  stopping_rule_decision: string;
  ai_confidence?: number;
  recommended_human_action: string;
  evaluated_at: string;
}

export interface HumanActionRequest {
  action: 'APPROVE_RECOVERY' | 'REJECT_RECOVERY' | 'STOP_RECOVERY' | 'REQUEST_INFO';
  reason?: string;
  operator_id?: string;
}

export interface HumanActionResponse {
  case_id: string;
  action_taken: string;
  previous_status: string;
  new_status: string;
  success: boolean;
  message: string;
  audit_id?: string;
}

export interface FunnelStageDetail {
  stage_id: string;
  stage_name: string;
  count: number;
  amount: number;
  conversion_rate: number;
  drop_off_count: number;
  drop_off_rate: number;
}

export interface DropOffReason {
  category: string;
  count: number;
  amount: number;
  reason: string;
}

export interface TimingMetrics {
  avg_failure_to_diagnosis_sec?: number;
  avg_diagnosis_to_policy_sec?: number;
  avg_policy_to_checkout_sec?: number;
  avg_checkout_to_payment_sec?: number;
  avg_total_recovery_sec?: number;
}

export interface FunnelSummary {
  total_failed_cases: number;
  eligible_cases: number;
  recovered_cases: number;
  case_recovery_rate: number;
  total_failed_amount: number;
  eligible_amount: number;
  recovered_amount: number;
  amount_recovery_rate: number;
}

export interface RecoveryFunnelResponse {
  summary: FunnelSummary;
  stages: FunnelStageDetail[];
  drop_off_analysis: DropOffReason[];
  timing_metrics: TimingMetrics;
  evaluated_at: string;
}

export interface CaseFunnelStage {
  stage_id: string;
  stage_name: string;
  completed: boolean;
  completed_at?: string;
  details?: string;
}

export interface CaseFunnelLineageResponse {
  case_id: string;
  current_status: string;
  completed_stages_count: number;
  total_stages_count: number;
  lineage: CaseFunnelStage[];
}

export interface ConfidenceBandDetail {
  band: string;
  label: string;
  case_count: number;
  recovered_count: number;
  recovery_rate: number;
  escalation_count: number;
  policy_block_count: number;
  stopping_count: number;
}

export interface RecommendationOutcome {
  recommendation: string;
  case_count: number;
  recovered_count: number;
  recovery_rate: number;
  recovered_amount: number;
  human_override_count: number;
  policy_block_count: number;
  stopping_count: number;
}

export interface AIMetricsSummary {
  total_evaluated_cases: number;
  ai_diagnosis_coverage: number;
  avg_confidence: number;
  recommendation_agreement_rate: number;
  overall_recovery_rate: number;
  human_intervention_rate: number;
  policy_conflict_count: number;
  stopping_rule_stop_count: number;
  explanation_completeness_rate: number;
}

export interface AIMetricsResponse {
  summary: AIMetricsSummary;
  confidence_analysis: ConfidenceBandDetail[];
  recommendations: RecommendationOutcome[];
  limitations_notice: string;
  evaluated_at: string;
}

export interface CaseAIEvaluationResponse {
  case_id: string;
  ai_recommendation: string;
  ai_confidence: number;
  ai_root_cause: string;
  policy_decision: string;
  stopping_decision: string;
  human_escalation_level: string;
  actual_action_taken: string;
  recovery_outcome: string;
  recommendation_action_agreement: boolean;
  explanation_completeness: boolean;
}

export interface FailureStepLineage {
  step: number;
  title: string;
  description: string;
  status: string;
}

export interface FailureScenario {
  scenario_key: string;
  category: string;
  title: string;
  description: string;
  error_code: string;
  retryable: boolean;
  retry_policy: string;
  detection_mechanism: string;
  fallback_action: string;
  final_case_state: string;
  user_message: string;
}

export interface SimulateFailureResponse {
  scenario_key: string;
  category: string;
  error_code: string;
  message: string;
  user_message: string;
  retryable: boolean;
  retry_policy: string;
  step_by_step_lineage: FailureStepLineage[];
  case_state_preserved: string;
  recovered_amount_preserved: number;
  audit_logged: boolean;
  simulated_at: string;
}

export interface NotificationItem {
  id: string;
  case_id?: string;
  merchant_id: string;
  type: string;
  severity: string;
  title: string;
  message: string;
  is_read: boolean;
  action_url?: string;
  metadata_json?: any;
  created_at: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface CheckoutAbandonmentMetrics {
  total_checkouts: number;
  checkout_started_count: number;
  payment_attempted_count: number;
  payment_completed_count: number;
  payment_failed_count: number;
  abandoned_checkout_count: number;
  abandonment_rate: number;
  completion_rate: number;
  recovery_after_abandonment_rate: number;
  abandoned_amount: number;
  recovered_abandoned_amount: number;
}

export interface StateStepLineage {
  state: string;
  timestamp: string;
  description: string;
}

export interface CheckoutStatusResponse {
  case_id: string;
  checkout_session_id?: string;
  state: string;
  abandonment_reason: string;
  started_at?: string;
  last_activity_at?: string;
  abandoned_at?: string;
  amount: number;
  retry_count: number;
  retry_allowed: boolean;
  retry_block_reason?: string;
  lineage: StateStepLineage[];
}

export interface CheckoutRetryResponse {
  case_id: string;
  status: string;
  message: string;
  razorpay_order_id?: string;
  retry_count: number;
  policy_decision: string;
  stopping_rule_decision: string;
}

export interface SubscriptionItem {
  id: string;
  merchant_id: string;
  customer_id?: string;
  plan_name: string;
  amount: number;
  currency: string;
  billing_interval: string;
  status: string;
  recovery_status: string;
  failure_reason: string;
  retry_count: number;
  max_retry_attempts: number;
  grace_period_until?: string;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionStateLineageItem {
  state: string;
  timestamp: string;
  description: string;
}

export interface SubscriptionRecoveryStatusResponse {
  subscription_id: string;
  merchant_id: string;
  customer_id?: string;
  plan_name: string;
  amount: number;
  currency: string;
  status: string;
  recovery_status: string;
  failure_reason: string;
  retry_count: number;
  max_retry_attempts: number;
  grace_period_until?: string;
  in_grace_period: boolean;
  retry_allowed: boolean;
  retry_block_reason?: string;
  lineage: SubscriptionStateLineageItem[];
}

export interface SubscriptionRetryResponse {
  subscription_id: string;
  status: string;
  message: string;
  razorpay_order_id?: string;
  retry_count: number;
  policy_decision: string;
  stopping_rule_decision: string;
}

export interface SubscriptionAnalytics {
  total_subscriptions: number;
  active_subscriptions_count: number;
  failed_subscriptions_count: number;
  retry_eligible_count: number;
  retry_attempted_count: number;
  retry_successful_count: number;
  grace_period_count: number;
  human_review_count: number;
  stopped_count: number;
  recovered_subscriptions_count: number;
  subscription_risk_amount: number;
  subscription_recovered_amount: number;
  failure_rate: number;
  recovery_rate: number;
}

export interface VoiceSimulateResponse {
  session_id: string;
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  amount: number;
  detected_intent: string;
  intent_description: string;
  response_text?: string;
  response_text_hinglish: string;
  response_text_english: string;
  voice_audio_prompt: string;
  action_taken: string;
  is_payment_link_sent: boolean;
  payment_url?: string;
  is_promise_registered: boolean;
  promise_date?: string;
  policy_decision: string;
  stopping_rule_decision: string;
  escalation_level: string;
  safety_status: string;
}

export interface PromiseToPayResponse {
  promise_id: string;
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  promised_amount: number;
  promise_date: string;
  status: string;
  session_id: string;
}

export interface B2BReceivablesAnalytics {
  total_receivables: number;
  total_outstanding_amount: number;
  total_revenue_at_risk: number;
  overdue_invoices_count: number;
  promises_count: number;
  promises_fulfilled_count: number;
  broken_promises_count: number;
  payment_requests_count: number;
  payments_completed_count: number;
  b2b_recovered_amount: number;
  recovery_rate: number;
  escalated_count: number;
}

export const api = {
  getRazorpayStatus: () => fetchJson<RazorpayHealthStatus>('/api/v1/health/razorpay'),
  getNotifications: (params?: { unread_only?: boolean; severity?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.unread_only) query.append('unread_only', 'true');
    if (params?.severity) query.append('severity', params.severity);
    if (params?.limit) query.append('limit', params.limit.toString());
    return fetchJson<NotificationItem[]>(`/api/v1/notifications?${query.toString()}`);
  },
  getUnreadCount: () => fetchJson<UnreadCountResponse>('/api/v1/notifications/unread-count'),
  markNotificationRead: (id: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/notifications/${id}/read`, { method: 'POST' }).then((r) => r.json() as Promise<NotificationItem>);
  },
  markAllNotificationsRead: () => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/notifications/read-all`, { method: 'POST' }).then((r) => r.json());
  },
  getFailureScenarios: () => fetchJson<FailureScenario[]>('/api/v1/health/failure-scenarios'),
  simulateFailure: (scenario_key: string, target_case_id?: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/health/simulate-failure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_key, target_case_id })
    }).then((res) => {
      if (!res.ok) throw new Error('Failure simulation failed');
      return res.json() as Promise<SimulateFailureResponse>;
    });
  },
  getMetrics: () => fetchJson<AnalyticsMetrics>('/api/v1/analytics/metrics'),
  getFunnel: () => fetchJson<{ funnel: FunnelStage[] }>('/api/v1/analytics/funnel'),
  getRecoveryFunnel: () => fetchJson<RecoveryFunnelResponse>('/api/v1/analytics/recovery-funnel'),
  getAIMetrics: () => fetchJson<AIMetricsResponse>('/api/v1/analytics/ai-metrics'),
  getRecentActivity: () => fetchJson<ActivityItem[]>('/api/v1/analytics/recent-activity'),
  getTransactions: (limit = 20) => fetchJson<TransactionItem[]>(`/api/v1/transactions?limit=${limit}`),
  
  getCases: (params?: { status?: string; risk_level?: string }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.risk_level) query.append('risk_level', params.risk_level);
    return fetchJson<RecoveryCaseItem[]>(`/api/v1/cases?${query.toString()}`);
  },
  
  getEscalatedCases: () => fetchJson<RecoveryCaseItem[]>('/api/v1/cases/escalated'),
  getCaseDetail: (id: string) => fetchJson<RecoveryCaseItem>(`/api/v1/cases/${id}`),
  getCaseTimeline: (caseId: string) => fetchJson<any>(`/api/v1/cases/${caseId}/timeline`),
  getCaseDecisionSummary: (caseId: string) => fetchJson<any>(`/api/v1/cases/${caseId}/decision-summary`),
  getCaseAIAssessment: (caseId: string) => fetchJson<AIAssessmentResponse>(`/api/v1/cases/${caseId}/ai-assessment`),
  getCasePolicyAssessment: (caseId: string) => fetchJson<PolicyGateResponse>(`/api/v1/cases/${caseId}/policy-assessment`),
  getCaseStoppingRules: (caseId: string) => fetchJson<StoppingRulesResponse>(`/api/v1/cases/${caseId}/stopping-rules`),
  getCaseEscalation: (caseId: string) => fetchJson<HumanEscalationResponse>(`/api/v1/cases/${caseId}/escalation`),
  getCaseFunnelLineage: (caseId: string) => fetchJson<CaseFunnelLineageResponse>(`/api/v1/cases/${caseId}/funnel-lineage`),
  getCaseAIEvaluation: (caseId: string) => fetchJson<CaseAIEvaluationResponse>(`/api/v1/cases/${caseId}/ai-evaluation`),
  postHumanAction: (caseId: string, action: HumanActionRequest['action'], reason?: string, operatorId = 'HUMAN_OPERATOR') => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/cases/${caseId}/human-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, reason, operator_id: operatorId })
    }).then((res) => {
      if (!res.ok) throw new Error('Human action request failed');
      return res.json() as Promise<HumanActionResponse>;
    });
  },
  getAuditLogs: (params?: { case_id?: string; event_type?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.case_id) query.append('case_id', params.case_id);
    if (params?.event_type) query.append('event_type', params.event_type);
    if (params?.limit) query.append('limit', String(params.limit));
    return fetchJson<any[]>(`/api/v1/audit?${query.toString()}`);
  },
  
  runEvaluation: (dataset_size = 1000, seed = 42, mode = 'deterministic') =>
    fetchJson<any>('/api/v1/evaluation/run', {
      method: 'POST',
      body: JSON.stringify({ dataset_size, seed, mode }),
    }),

  getEvaluationSummary: () => fetchJson<any>('/api/v1/evaluation/summary'),
  getEvaluationRun: (runId: string) => fetchJson<any>(`/api/v1/evaluation/runs/${runId}`),
  getEvaluationCases: (runId: string) => fetchJson<any[]>(`/api/v1/evaluation/runs/${runId}/cases`),
  getUnifiedSummary: () => fetchJson<any>('/api/v1/revenue-risk/summary'),
  getUnifiedOpportunities: () => fetchJson<any>('/api/v1/revenue-risk/opportunities'),
  executeCaseRecovery: (caseId: string, action?: string) =>
    fetchJson<any>(`/api/v1/cases/${caseId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  customerLogin: (payload: { email?: string; phone?: string; customer_id?: string }) =>
    fetchJson<CustomerLoginResponse>('/api/v1/customer/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listCustomerTransactions: (customerId: string) =>
    fetchJson<CustomerTransactionDetail[]>('/api/v1/customer/transactions', {
      headers: { 'x-customer-id': customerId },
    }),

  getCustomerTransaction: (transactionId: string, customerId: string) =>
    fetchJson<CustomerTransactionDetail>(`/api/v1/customer/transactions/${transactionId}`, {
      headers: { 'x-customer-id': customerId },
    }),

  getReceivables: () => fetchJson<any[]>('/api/v1/receivables'),
  getMandates: () => fetchJson<any[]>('/api/v1/mandates'),
  getMandateDetails: (id: string) => fetchJson<any>(`/api/v1/mandates/${id}`),
  createMandate: (payload: { mandate_number: string; amount: number; billing_interval?: string }) =>
    fetchJson<any>('/api/v1/mandates/create', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  triggerMandateFailure: (mandateId: string, failureReason?: string) =>
    fetchJson<any>('/api/v1/mandates/attempt-failure', {
      method: 'POST',
      body: JSON.stringify({ mandate_id: mandateId, failure_reason: failureReason || 'Bank auto-debit failed' })
    }),
  executeMandateRetry: (mandateId: string, idempotencyKey?: string) =>
    fetchJson<any>(`/api/v1/mandates/${mandateId}/execute-retry`, {
      method: 'POST',
      body: JSON.stringify({ idempotency_key: idempotencyKey, simulate_success: true })
    }),
  escalateMandate: (mandateId: string, reason?: string) =>
    fetchJson<any>(`/api/v1/mandates/${mandateId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || 'Manual merchant escalation requested' })
    }),
  resetMandateEscalation: (mandateId: string) =>
    fetchJson<any>(`/api/v1/mandates/${mandateId}/reset-escalation`, {
      method: 'POST'
    }),
  getCheckoutAbandonmentMetrics: () => fetchJson<CheckoutAbandonmentMetrics>('/api/v1/analytics/checkout-abandonment'),
  getCaseCheckoutStatus: (caseId: string) => fetchJson<CheckoutStatusResponse>(`/api/v1/cases/${caseId}/checkout-status`),
  retryCheckout: (caseId: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/cases/${caseId}/checkout-retry`, { method: 'POST' }).then((r) => r.json() as Promise<CheckoutRetryResponse>);
  },
  getSubscriptions: (status?: string) => {
    const query = new URLSearchParams();
    if (status) query.append('status', status);
    return fetchJson<SubscriptionItem[]>(`/api/v1/subscriptions?${query.toString()}`);
  },
  getSubscriptionDetail: (id: string) => fetchJson<SubscriptionItem>(`/api/v1/subscriptions/${id}`),
  getSubscriptionRecoveryStatus: (id: string) => fetchJson<SubscriptionRecoveryStatusResponse>(`/api/v1/subscriptions/${id}/recovery`),
  getFailedSubscriptionsAnalytics: () => fetchJson<SubscriptionAnalytics>('/api/v1/analytics/failed-subscriptions'),
  retrySubscription: (id: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/subscriptions/${id}/retry`, { method: 'POST' }).then((r) => r.json() as Promise<SubscriptionRetryResponse>);
  },
  stopSubscription: (id: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    return fetch(`${apiBase}/api/v1/subscriptions/${id}/stop`, { method: 'POST' }).then((r) => r.json());
  },
  simulateVoiceIntent: (invoiceId: string, customerSpeech: string, sessionId?: string) =>
    fetchJson<VoiceSimulateResponse>('/api/v1/voice/simulate-intent', {
      method: 'POST',
      body: JSON.stringify({ invoice_id: invoiceId, customer_speech: customerSpeech, session_id: sessionId })
    }),
  registerPromiseToPay: (invoiceId: string, promiseDate: string, sessionId?: string) =>
    fetchJson<PromiseToPayResponse>('/api/v1/voice/promise-to-pay', {
      method: 'POST',
      body: JSON.stringify({ invoice_id: invoiceId, promise_date: promiseDate, session_id: sessionId })
    }),
  getB2BReceivablesAnalytics: () => fetchJson<B2BReceivablesAnalytics>('/api/v1/analytics/b2b-receivables'),
  generateCommunication: (payload: { customer_name: string; amount: number; language: string; payment_link_url?: string }) =>
    fetchJson<any>('/api/v1/communication/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
