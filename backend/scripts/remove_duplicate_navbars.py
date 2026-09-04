import os
import re

def remove_duplicate_navbars():
    app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src", "app")
    
    print("=================================================================")
    print("   REMOVING DUPLICATE NAVBARS FROM CHILD PAGES                   ")
    print("=================================================================\n")

    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith((".tsx", ".jsx")) and not root.endswith("layout.tsx"):
                filepath = os.path.join(root, file)
                if filepath.endswith("layout.tsx"):
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                if "import Navbar from" in content or "<Navbar />" in content or "<Navbar" in content:
                    print(f"Fixing page: {os.path.relpath(filepath, app_dir)}")
                    # Remove import line
                    content = re.sub(r'import\s+Navbar\s+from\s+[\'"]@/components/Navbar[\'"];?\n?', '', content)
                    # Remove self-closing Navbar component call
                    content = re.sub(r'<Navbar\s*/>', '', content)
                    # Save cleaned file
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

    print("\n=================================================================")
    print("   DUPLICATE NAVBAR REMOVAL COMPLETE                            ")
    print("=================================================================\n")

if __name__ == "__main__":
    remove_duplicate_navbars()
