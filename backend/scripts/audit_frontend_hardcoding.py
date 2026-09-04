import os

def audit_frontend_hardcoding():
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src")
    targets = [
        "pay_TTXlSqxyg5hAiT",
        "order_TU2xgzptEfg7rP",
        "pay_TU3EQsT63DFVuX",
        "17950799",
        "6811001",
        "3710722",
        "19092323",
        "8567489",
        "5080707"
    ]

    print("=================================================================")
    print("   PAYPILOT AI -- FRONTEND HARDCODING AUDIT                      ")
    print("=================================================================\n")

    found_count = 0
    for root, _, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    for t in targets:
                        if t in content:
                            print(f"[FOUND] Target '{t}' in {os.path.relpath(filepath, frontend_dir)}")
                            found_count += 1

    print("\n=================================================================")
    print(f"   HARDCODING AUDIT COMPLETE -- {found_count} MATCHES FOUND     ")
    print("=================================================================\n")

if __name__ == "__main__":
    audit_frontend_hardcoding()
