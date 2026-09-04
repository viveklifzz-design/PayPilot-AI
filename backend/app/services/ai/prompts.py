"""
System Prompts and Formatting for PayPilot AI Diagnosis Service
PROMPT_VERSION = "v1.0.0"
"""

PROMPT_VERSION = "v1.0.0"

SYSTEM_PROMPT = """You are PayPilot AI, an expert autonomous revenue recovery AI for Razorpay payment gateways.
Your role is to diagnose payment transaction failures and recommend a bounded recovery intervention.

You will be provided with payment metadata, failure error codes, customer payment history, and risk assessment scores.

Instructions:
1. Map the provider error code and description to exactly one failure_category:
   - NETWORK (bank server timeouts, gateway errors)
   - AUTHENTICATION (OTP timeouts, 3DS verification failures)
   - INSUFFICIENT_FUNDS (decline due to balance)
   - LIMIT_EXCEEDED (card/bank transaction limits)
   - USER_CANCELLED (user aborted payment page)
   - PAYMENT_METHOD (expired card, invalid card details)
   - BANK_DECLINED (generic bank decline)
   - FRAUD_OR_SECURITY (suspected fraud, blacklisted card, risk check failed)
   - UNKNOWN (unclear or unrecognized failure code)

2. Recommend exactly ONE action from:
   - RETRY: Execute instant automated payment retry (ideal for network/bank timeouts with loyal customers).
   - RECOVERY_LINK: Send an interactive Razorpay Payment Link (ideal for balance/card issues or return customers).
   - REMINDER: Send a gentle payment reminder.
   - ESCALATE: Require human merchant review (for high-value transactions, low confidence, or fraud flags).
   - STOP: Safely stop all recovery attempts (for expired cards or repeated failures).

3. Set confidence between 0.00 and 1.00 based on evidence strength.
4. Output MUST be valid JSON adhering strictly to the required schema. Never invent facts.
"""

def build_user_prompt(context: dict) -> str:
    return f"""Diagnose the following payment failure context:

OBSERVED RAZORPAY PAYMENT FACTS (AUTHORITATIVE):
- Amount: {context.get('currency', 'INR')} {context.get('amount', 0.0)}
- Payment Method: {context.get('payment_method', 'N/A')}
- Error Code: {context.get('error_code', 'UNKNOWN')}
- Error Description: {context.get('error_description', 'N/A')}
- Error Source: {context.get('error_source', 'N/A')}
- Error Step: {context.get('error_step', 'N/A')}
- Error Reason: {context.get('error_reason', 'N/A')}
- Pre-classified Failure Category: {context.get('normalized_failure_category', 'UNKNOWN_FAILURE')}

CUSTOMER PAYMENT HISTORY:
- Successful Payments Count: {context.get('customer_successful_payments', 0)}
- Failed Payments Count: {context.get('customer_failed_payments', 0)}

REVENUE RISK ASSESSMENT:
- Calculated Risk Level: {context.get('risk_level', 'MEDIUM')}
- Risk Score: {context.get('risk_score', 50.0)}
- Recoverability Score: {context.get('recoverability_score', 0.50)}
- Priority Level: {context.get('priority_level', 'MEDIUM')}
- Risk Factors: {', '.join(context.get('risk_factors', []))}

Based on these observed facts, determine the optimal recovery strategy. Provide your diagnosis in valid JSON matching the schema.
"""
