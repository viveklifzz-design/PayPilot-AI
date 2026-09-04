import argparse
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import *  # Load all SQLAlchemy models into registry
from app.db.session import AsyncSessionLocal
from app.services.evaluation.evaluator import evaluation_engine

async def main():
    parser = argparse.ArgumentParser(description="PayPilot AI Evaluation Engine CLI Runner")
    parser.add_argument("--size", type=int, default=1000, help="Dataset size (e.g. 100, 500, 1000, 2000)")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for 100% reproducibility")
    parser.add_argument("--mode", type=str, default="deterministic", help="Evaluation mode ('deterministic' or 'live_ai')")
    args = parser.parse_args()

    print("\n=======================================================")
    print("        PAYPILOT AI -- SYNTHETIC EVALUATION BENCHMARK  ")
    print("=======================================================")
    print(f"Mode         : {args.mode}")
    print(f"Dataset Size : {args.size} cases")
    print(f"Random Seed  : {args.seed}")
    print("Executing evaluation pipeline...")

    async with AsyncSessionLocal() as db:
        res = await evaluation_engine.run_evaluation(
            db=db,
            dataset_size=args.size,
            seed=args.seed,
            mode=args.mode
        )

    m = res.metrics
    print("\n-------------------------------------------------------")
    print(f"  Revenue at Risk       : INR {m.total_revenue_at_risk:,.2f}")
    print(f"  Recoverable Revenue   : INR {m.recoverable_revenue:,.2f}")
    print(f"  Revenue Recovered     : INR {m.revenue_recovered:,.2f}")
    print("-------------------------------------------------------")
    print(f"  Precision             : {m.precision}%")
    print(f"  Recall                : {m.recall}%")
    print(f"  Recovery Rate         : {m.recovery_rate}%")
    print(f"  Intervention Rate     : {m.intervention_rate}%")
    print(f"  Safe Stop Rate        : {m.safe_stop_rate}%")
    print(f"  Escalation Rate       : {m.escalation_rate}%")
    print(f"  Unsafe Actions        : {m.unsafe_action_count}")
    print("-------------------------------------------------------")
    print("Synthetic Evaluation -- No Real Money")
    print("Evaluation completed successfully.\n")

if __name__ == "__main__":
    asyncio.run(main())
