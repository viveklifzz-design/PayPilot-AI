# PayPilot AI — Product Elevator Pitch (10s / 30s / 60s)

## 1. 10-Second Pitch (Headline)
> "PayPilot AI is an autonomous revenue recovery agent that diagnoses failed payments, applies a policy safety gate, and executes recovery via Razorpay."

---

## 2. 30-Second Pitch (Standard Executive Summary)
> "PayPilot AI is an autonomous revenue recovery agent that detects failed payments, diagnoses why they failed using Gemini AI, recommends a recovery action, passes it through a deterministic safety gate, executes bounded recovery through Razorpay Test Mode, verifies the result via signed webhooks, and records an auditable decision trail."

---

## 3. 60-Second Pitch (Detailed Technical Pitch)
> "Online merchants lose up to 30% of revenue to payment failures, but naive automated retries annoy customers and violate retry boundaries.
> 
> PayPilot AI solves this by operating an autonomous 7-stage recovery loop. When Razorpay ingests a failed payment, our AI engine diagnoses the root cause and proposes an intervention.
> 
> Crucially, AI recommends, but our Policy Safety Gate controls. Every recommendation must pass 5 strict safety rules — enforcing confidence thresholds ($\ge 0.70$), retry caps ($\le 3$), cooldown windows ($\ge 1\text{h}$), and amount limits ($\le \text{₹50k}$) — guaranteeing zero unsafe actions. Approved actions are executed via Razorpay Payment Links, verified via HMAC-signed webhooks, and logged in an immutable audit timeline."
