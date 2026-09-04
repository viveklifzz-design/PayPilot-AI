import re
import os

pattern = r'rzp_test_[A-Za-z0-9]{14}'
doc_files = [
    r'docs/MASTER_REALITY_AUDIT.md',
    r'docs/point21-final-freeze-report.md',
    r'docs/razorpay-test-mode.md',
    r'docs/RAZORPAY_INTEGRATION.md',
    r'docs/REAL_FAILURE_TO_RECOVERY_PROOF.md'
]

for doc in doc_files:
    if os.path.exists(doc):
        with open(doc, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        sanitized = re.sub(pattern, 'rzp_test_YOUR_KEY_ID', content)
        with open(doc, 'w', encoding='utf-8') as f:
            f.write(sanitized)
        print(f"Sanitized {doc}")
