import os
import re

def fix_header_elements():
    app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src", "app")
    
    print("=================================================================")
    print("   REPLACING INNER PAGE <header> TAGS WITH <div>                 ")
    print("=================================================================\n")

    for root, _, files in os.walk(app_dir):
        for file in files:
            if file.endswith((".tsx", ".jsx")) and not root.endswith("layout.tsx"):
                filepath = os.path.join(root, file)
                if filepath.endswith("layout.tsx"):
                    continue
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                if "<header" in content:
                    print(f"Fixing page header element: {os.path.relpath(filepath, app_dir)}")
                    # Replace opening <header with <div
                    content = re.sub(r'<header(\s|>|\n)', r'<div\1', content)
                    # Replace closing </header> with </div>
                    content = content.replace("</header>", "</div>")
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

    print("\n=================================================================")
    print("   HEADER ELEMENT FIX COMPLETE                                  ")
    print("=================================================================\n")

if __name__ == "__main__":
    fix_header_elements()
