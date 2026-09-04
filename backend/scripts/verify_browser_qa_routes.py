import requests
import re

ROUTES = [
    "/",
    "/transactions",
    "/revenue-risk",
    "/cases",
    "/customers",
    "/customer",
    "/audit",
    "/safety",
    "/benchmark",
    "/voice"
]

BASE_URL = "http://localhost:3000"

def verify_routes():
    print("=================================================================")
    print("   PAYPILOT AI -- BROWSER & ROUTE VISUAL QA VERIFICATION        ")
    print("=================================================================\n")

    all_passed = True

    for r in ROUTES:
        url = f"{BASE_URL}{r}"
        try:
            res = requests.get(url, timeout=10)
            status = res.status_code
            html = res.text
            
            # Remove <script> blocks to test actual rendered DOM tags
            body_html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
            
            header_count = body_html.count('<header')
            aside_count = body_html.count('<aside')
            
            print(f"Route: {r:<20} | Status: {status} | Headers: {header_count} | Asides: {aside_count}")
            
            if status != 200:
                print(f"  [FAIL] Route {r} returned status {status}")
                all_passed = False
            if header_count != 1:
                print(f"  [FAIL] Route {r} rendered {header_count} DOM headers instead of 1")
                all_passed = False
            if aside_count > 1:
                print(f"  [FAIL] Route {r} rendered {aside_count} DOM asides instead of <= 1")
                all_passed = False
                
        except Exception as e:
            print(f"Route: {r:<20} | [ERROR] {e}")
            all_passed = False

    print("\n=================================================================")
    if all_passed:
        print(f"   ALL {len(ROUTES)} ROUTES VERIFIED 100% PASS (ZERO ISSUES)               ")
    else:
        print("   ROUTE VERIFICATION FAILED                                    ")
    print("=================================================================\n")

if __name__ == "__main__":
    verify_routes()
