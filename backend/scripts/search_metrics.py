import os

SEARCH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SEARCH_DIR)

TARGETS = ["83.69", "86.13", "59.27", "77.76", "84.98", "56.5"]

results = []
for root, dirs, files in os.walk(PROJECT_ROOT):
    if "venv" in root or "node_modules" in root or ".git" in root or ".next" in root:
        continue
    for file in files:
        if file.endswith((".md", ".json", ".py", ".ts", ".tsx", ".txt")):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for t in TARGETS:
                        if t in content:
                            rel = os.path.relpath(path, PROJECT_ROOT)
                            results.append(f"{rel}: contains '{t}'")
            except Exception:
                pass

print("=== METRIC CITATION AUDIT RESULTS ===")
for r in sorted(list(set(results))):
    print(" -", r)
