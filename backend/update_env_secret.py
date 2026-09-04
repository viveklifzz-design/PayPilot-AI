import hashlib

with open("new_secret.txt", "r") as f:
    secret = f.read().strip()

with open(".env", "r") as f:
    content = f.read()

lines = content.splitlines()
new_lines = []
updated = False
for line in lines:
    if line.startswith("RAZORPAY_WEBHOOK_SECRET="):
        new_lines.append(f'RAZORPAY_WEBHOOK_SECRET="{secret}"')
        updated = True
    else:
        new_lines.append(line)

if not updated:
    new_lines.append(f'RAZORPAY_WEBHOOK_SECRET="{secret}"')

with open(".env", "w") as f:
    f.write("\n".join(new_lines) + "\n")

fingerprint = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]
print(".env updated successfully!")
print("Secret Length:", len(secret))
print("Secret SHA256 Fingerprint:", fingerprint)
