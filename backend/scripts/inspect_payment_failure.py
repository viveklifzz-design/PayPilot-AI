import sys
import os
import asyncio

# Add backend dir to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.status == "failed")
            .order_by(Transaction.created_at.desc())
            .limit(5)
        )
        txns = result.scalars().all()

        print("=======================================================")
        print("     PAYPILOT AI -- PAYMENT FAILURE INSPECTOR CLI      ")
        print("=======================================================")
        
        if not txns:
            print("No failed transactions found in database.")
            return

        for idx, txn in enumerate(txns, start=1):
            classified = classify_razorpay_failure(
                error_code=txn.error_code,
                error_source=txn.error_source,
                error_step=txn.error_step,
                error_reason=txn.error_reason,
                error_description=txn.error_description
            )

            print(f"\n--- [Failed Transaction #{idx}] ---")
            print(f"Transaction ID   : {txn.id}")
            print(f"Razorpay Payment : {txn.razorpay_payment_id or 'N/A'}")
            print(f"Amount           : {txn.currency} {float(txn.amount):,.2f}")
            print(f"Payment Method   : {txn.payment_method or 'N/A'}")
            print(f"Error Code       : {txn.error_code or 'N/A'}")
            print(f"Error Description: {txn.error_description or 'N/A'}")
            print(f"Error Source     : {txn.error_source or 'N/A'}")
            print(f"Error Step       : {txn.error_step or 'N/A'}")
            print(f"Error Reason     : {txn.error_reason or 'N/A'}")
            print(f"Classification   : {classified.category} ({classified.reason})")

        print("\nInspection completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
