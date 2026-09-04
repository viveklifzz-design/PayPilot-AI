import os

def audit_sidebar_renders():
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src")
    
    print("=================================================================")
    print("   PAYPILOT AI -- AUDITING SIDEBAR RENDERING IN FRONTEND         ")
    print("=================================================================\n")

    for root, _, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "<Sidebar" in content or "import Sidebar" in content:
                        print(f"[FOUND] Sidebar in: {os.path.relpath(filepath, frontend_dir)}")

    print("\n=================================================================")
    print("   SIDEBAR AUDIT COMPLETE                                       ")
    print("=================================================================\n")

if __name__ == "__main__":
    audit_sidebar_renders()
