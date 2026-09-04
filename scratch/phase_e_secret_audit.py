import os
import re

secret_patterns = [
    (r'AIzaSy[A-Za-z0-9_-]{33}', 'Google Gemini API Key'),
    (r'rzp_(live|test)_[A-Za-z0-9]{14}', 'Razorpay Key ID'),
    (r'EAAG[A-Za-z0-9]{50,}', 'WhatsApp Meta Access Token'),
    (r'sk_live_[A-Za-z0-9]{24}', 'Stripe / General Live Key'),
]

root_dir = '.'
ignore_dirs = {'.git', 'venv', '.venv', 'node_modules', '.next', '__pycache__', 'dist', 'build'}

found_secrets = []

for root, dirs, files in os.walk(root_dir):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for file in files:
        if file.startswith('.env') and not file.endswith('.example'):
            continue # Local env files ignored from audit of tracked source
        file_path = os.path.join(root, file)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for pattern, secret_type in secret_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        found_secrets.append((file_path, secret_type, len(matches)))
        except Exception as e:
            pass

print("=== SECRET AUDIT RESULT ===")
if found_secrets:
    print("[WARNING] Found potential secrets in files:")
    for path, stype, count in found_secrets:
        print(f"  {path} -> {stype} ({count} occurrence(s))")
else:
    print("[OK] ZERO secret key strings found in source/documentation files!")
