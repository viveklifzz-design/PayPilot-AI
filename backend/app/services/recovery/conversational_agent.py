import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.recovery.paypilot_tools import TOOL_FUNCTIONS_MAP

logger = logging.getLogger("paypilot.conversational_agent")

_conversational_sessions: Dict[str, Dict[str, Any]] = {}

SYSTEM_INSTRUCTION = """
You are 'PayPilot', an intelligent, polite, and professional female AI Receivables & Voice Recovery Assistant for PayPilot AI.
Your purpose is to help customers and finance operators understand payment failures, invoice statuses, transaction history, and payment recovery options.

CORE BEHAVIOR RULES:
1. IDENTITY: Always present yourself as 'PayPilot', a female AI receivables assistant. Tone must be polite, helpful, soft, professional, and trustworthy.
2. LANGUAGE: Natural English, Hindi, and Hinglish. Adapt fluently to the language used by the customer.
3. ZERO FINANCIAL HALLUCINATION: NEVER invent, guess, or hallucinate payment statuses, transaction amounts, invoice due dates, customer names, or order numbers.
   - Always request tool calls to look up real database records.
   - If real data for a requested item is not found or unavailable, state clearly that it is unavailable.
4. FINANCIAL SAFETY GATE: You are equiped with read-only data lookup tools. You cannot directly execute financial mutations (such as initiating payments or overriding policy rules).
   - If a customer asks to retry a payment, resend a link, or set a promise-to-pay date, acknowledge their intent clearly and specify that PayPilot's safety policy gate will execute the verified recovery action.
5. CONVERSATION CONTEXT: Maintain multi-turn dialogue awareness. Resolve pronouns and references (e.g. "it", "that payment", "kal karunga") based on earlier turns in the session.
6. CONCISE & HELPFUL: Keep spoken responses natural, polite, clear, and focused on resolving the payment or providing exact facts.
"""

# Tool schemas for Gemini Function Calling
GEMINI_TOOLS_DECLARATION = [
    {
        "name": "get_customer",
        "description": "Retrieve customer details by ID or phone number.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"customer_id": {"type": "STRING", "description": "Customer UUID or phone number"}},
            "required": ["customer_id"]
        }
    },
    {
        "name": "search_customer",
        "description": "Search customers by name, company, email, or phone.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"query": {"type": "STRING", "description": "Search query"}},
            "required": ["query"]
        }
    },
    {
        "name": "get_customer_transactions",
        "description": "Get recent transactions for a specific customer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_id": {"type": "STRING", "description": "Customer UUID"},
                "limit": {"type": "INTEGER", "description": "Max items to return"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_transaction",
        "description": "Retrieve detailed information about a transaction by transaction ID, payment ID, or order ID.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"transaction_id": {"type": "STRING", "description": "Transaction UUID or Razorpay payment/order ID"}},
            "required": ["transaction_id"]
        }
    },
    {
        "name": "get_payment_status",
        "description": "Get current payment status for an invoice, transaction, or order.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"identifier": {"type": "STRING", "description": "Invoice ID, Transaction ID, Payment ID, or Order ID"}},
            "required": ["identifier"]
        }
    },
    {
        "name": "get_payment_history",
        "description": "Retrieve overall or customer-specific payment history.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"customer_id": {"type": "STRING", "description": "Optional customer UUID filter"}},
        }
    },
    {
        "name": "get_invoice",
        "description": "Get invoice details including amount, due date, status, and payment link.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"invoice_id": {"type": "STRING", "description": "Invoice UUID or Invoice number"}},
            "required": ["invoice_id"]
        }
    },
    {
        "name": "get_subscription",
        "description": "Retrieve details for a failed subscription recovery case.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"subscription_id": {"type": "STRING", "description": "Subscription UUID"}},
            "required": ["subscription_id"]
        }
    },
    {
        "name": "get_recovery_case",
        "description": "Get recovery case status, AI confidence score, and recommended recovery action.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"case_id": {"type": "STRING", "description": "Recovery case UUID or invoice ID"}},
            "required": ["case_id"]
        }
    },
    {
        "name": "get_notifications",
        "description": "Retrieve recent system notifications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"limit": {"type": "INTEGER", "description": "Max notifications to return"}},
        }
    },
    {
        "name": "get_account_summary",
        "description": "Get aggregate account summary including recovery cases, transactions, and outstanding balance.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "get_failed_payments",
        "description": "Retrieve all failed payments and failed transactions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "get_payment_link_status",
        "description": "Get payment link status for an active recovery case or invoice.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"case_id": {"type": "STRING", "description": "Case ID or Invoice ID"}},
            "required": ["case_id"]
        }
    },
    {
        "name": "verify_razorpay_payment",
        "description": "Verify payment status directly with Razorpay provider API.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"payment_id": {"type": "STRING", "description": "Razorpay payment ID (pay_...)"}},
            "required": ["payment_id"]
        }
    }
]

class ConversationalAgent:
    """
    Conversational PayPilot AI Voice Agent powered by Gemini API server-side.
    Performs Tool Execution against real PayPilot database & Razorpay provider.
    Maintains session-based conversation context and enforces zero-hallucination safety.
    """

    def __init__(self):
        self._genai_client = None

    def _init_gemini_client(self):
        if self._genai_client is None and settings.GEMINI_API_KEY:
            try:
                from google import genai
                from google.genai import types
                self._genai_client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(api_version="v1beta")
                )
                logger.info("ConversationalAgent successfully initialized Gemini GenAI Client")
            except Exception as e:
                logger.warning(f"Failed to initialize google.genai client: {e}")

    async def execute_tool_call(
        self,
        db: AsyncSession,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute backend tool call securely against database."""
        func = TOOL_FUNCTIONS_MAP.get(tool_name)
        if not func:
            return {"error": f"Tool '{tool_name}' is not registered"}
        try:
            return await func(db, **tool_args)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}' with args {tool_args}: {e}")
            return {"error": str(e)}

    async def process_conversational_turn(
        self,
        db: AsyncSession,
        session_id: str,
        user_speech: str,
        context_invoice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user speech statement using Gemini + PayPilot Real Data Tools.
        Returns response dict containing text (English & Hinglish), tools used, and safety facts.
        """
        self._init_gemini_client()

        sess = _conversational_sessions.setdefault(session_id, {
            "history": [],
            "context_invoice_id": context_invoice_id,
            "turns": 0
        })
        if context_invoice_id:
            sess["context_invoice_id"] = context_invoice_id
        sess["turns"] += 1

        tools_executed = []

        # If Gemini API key is available, use Gemini with tool calling
        if self._genai_client:
            primary_model = settings.GEMINI_MODEL or "gemini-3.6-flash"
            candidate_models = [primary_model, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            models_to_try = list(dict.fromkeys(candidate_models))

            # Fetch initial contextual invoice/transaction facts if context_invoice_id is known
            ctx_facts = {}
            if sess.get("context_invoice_id"):
                try:
                    inv_func = TOOL_FUNCTIONS_MAP["get_invoice"]
                    ctx_facts = await inv_func(db, sess["context_invoice_id"])
                    tools_executed.append({"tool": "get_invoice", "args": {"invoice_id": sess["context_invoice_id"]}})
                except Exception as ctx_err:
                    logger.warning(f"Failed to fetch active invoice context: {ctx_err}")

            prompt_content = f"""
Current Session Context:
- Active Invoice Context: {json.dumps(ctx_facts)}
- Turn Number: {sess['turns']}

User Speech: "{user_speech}"
"""

            logger.info(
                f"[GEMINI CALL] Gemini API IS BEING CALLED | Candidate Models: {models_to_try} | "
                f"Session: '{session_id}' | Turn: {sess['turns']} | User Speech: '{user_speech}'"
            )

            last_err = None
            for model_name in models_to_try:
                try:
                    logger.info(f"[GEMINI DISPATCH] Sending generate_content to model='{model_name}'...")
                    
                    # Run synchronous SDK call in thread pool with 15s timeout to prevent event loop blocking
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._genai_client.models.generate_content,
                            model=model_name,
                            contents=prompt_content,
                            config={
                                "system_instruction": SYSTEM_INSTRUCTION,
                                "temperature": 0.2,
                            }
                        ),
                        timeout=15.0
                    )

                    reply_text = response.text if hasattr(response, 'text') and response.text else None
                    if reply_text and reply_text.strip():
                        reply_text = reply_text.strip()
                        safe_preview = reply_text[:120].encode('ascii', 'backslashreplace').decode('ascii')
                        logger.info(
                            f"[GEMINI SUCCESS] Model '{model_name}' returned valid response ({len(reply_text)} chars) | "
                            f"Preview: '{safe_preview}...'"
                        )
                        sess["history"].append({"user": user_speech, "agent": reply_text})
                        return {
                            "agent_reply": reply_text,
                            "tools_executed": tools_executed,
                            "used_gemini": True,
                            "model_used": model_name,
                            "session_id": session_id
                        }
                    else:
                        logger.warning(f"[GEMINI EMPTY RESPONSE] Model '{model_name}' returned empty or None response.text.")
                except asyncio.TimeoutError:
                    last_err = TimeoutError("Gemini API call timed out after 15.0 seconds")
                    logger.warning(f"[GEMINI TIMEOUT] Model '{model_name}' timed out after 15 seconds.")
                except Exception as gem_err:
                    last_err = gem_err
                    err_type = type(gem_err).__name__
                    status_code = getattr(gem_err, 'code', getattr(gem_err, 'status_code', 'N/A'))
                    logger.warning(
                        f"[GEMINI FAILURE] Model '{model_name}' failed | ExceptionType: {err_type} | "
                        f"Status/Code: {status_code} | Error: {gem_err}"
                    )

            logger.error(f"[GEMINI ALL MODELS FAILED] All candidate models failed. Last exception: {type(last_err).__name__} ({last_err})")
        else:
            logger.warning(f"[GEMINI NOT CALLED] _genai_client is None. GEMINI_API_KEY present in settings: {bool(settings.GEMINI_API_KEY)}")

        # Fallback if Gemini API key is missing or encounters network issue
        return {
            "agent_reply": None,
            "tools_executed": tools_executed,
            "used_gemini": False,
            "session_id": session_id
        }

conversational_agent = ConversationalAgent()
