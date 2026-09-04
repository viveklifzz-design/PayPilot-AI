import asyncio
import httpx
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_voice_queries():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch all receivables/invoices
        res = await client.get(f"{base_url}/api/v1/receivables")
        invoices = res.json()
        print(f"Total Invoices Found in Receivables: {len(invoices)}")
        
        test_queries = [
            "payment kab hua tha?",
            "payment status kya hai?",
            "invoice amount kitna hai?",
            "customer ka payment pending hai kya?",
            "show payment history",
            "random unknown query test 12345"
        ]
        
        for idx, inv in enumerate(invoices):
            inv_id = inv["id"]
            inv_num = inv["invoice_number"]
            print(f"\n=======================================================")
            print(f"TESTING INVOICE #{idx+1}: ID={inv_id} (#{inv_num}) Amount=₹{inv['amount']}")
            print(f"=======================================================")
            
            for q in test_queries:
                print(f"\n--- QUERY: '{q}' ---")
                payload = {
                    "invoice_id": inv_id,
                    "customer_speech": q,
                    "session_id": f"test_sess_inv_{idx}"
                }
                resp = await client.post(f"{base_url}/api/v1/voice/simulate-intent", json=payload)
                data = resp.json()
                print(f"Status Code: {resp.status_code}")
                print(f"Detected Intent: {data.get('detected_intent')}")
                print(f"response_text: {data.get('response_text')}")
                
                # Assertions
                assert resp.status_code == 200, f"HTTP Error {resp.status_code}"
                assert data.get('response_text'), "FAILURE: response_text is empty!"
                assert isinstance(data.get('response_text'), str) and len(data.get('response_text').strip()) > 0, "FAILURE: response_text is whitespace!"
                print("PASSED SAFETY ASSERTION: Non-empty response_text guaranteed!")

if __name__ == "__main__":
    asyncio.run(test_voice_queries())
