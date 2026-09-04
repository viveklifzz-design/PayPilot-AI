import os

SEARCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SEARCH_DIR)

SECRET_PATTERNS = ["RAZORPAY_KEY_SECRET=", "RAZORPAY_WEBHOOK_SECRET=", "GEMINI_API_KEY="]
LOCALHOST_PATTERNS = ["localhost:8000", "127.0.0.1:8000"]

secret_findings = []
localhost_findings = []

for root, dirs, files in os.walk(PROJECT_ROOT):
    if "venv" in root or "node_modules" in root or ".git" in root or ".next" in root or "brain" in root:
        continue
    for file in files:
        if file.endswith((".py", ".ts", ".tsx", ".env", ".env.local", ".example")):
            path = os.path.join(root, file)
            rel = os.path.relpath(path, PROJECT_ROOT)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, 1):
                        for sp in SECRET_PATTERNS:
                            if sp in line and not line.strip().endswith("=") and "your_" not in line and ".example" not in file:
                                secret_findings.append(f"{rel}:L{line_idx}: Exposed secret pattern '{sp}'")
                        if "frontend" in root:
                            for lp in LOCALHOST_PATTERNS:
                                if lp in line and not line.strip().startswith("//"):
                                    localhost_findings.append(f"{rel}:L{line_idx}: '{lp}' found")
            except Exception:
                pass

print("=== SECRET EXPOSURE AUDIT ===")
if secret_findings:
    for sf in secret_findings:
        print(" [WARNING]", sf)
else:
    print(" [PASS] Zero unredacted secrets found in committed source/env files.")

print("\n=== FRONTEND LOCALHOST AUDIT ===")
if localhost_findings:
    for lf in localhost_findings:
        print(" [INFO]", lf)
else:
    print(" [PASS] Zero hardcoded localhost backend URLs in frontend source.")
