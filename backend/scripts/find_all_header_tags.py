import os

def find_all_header_tags():
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "src")
    
    print("=================================================================")
    print("   FINDING ALL <header> TAGS IN FRONTEND                         ")
    print("=================================================================\n")

    for root, _, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for idx, line in enumerate(lines):
                        if "<header" in line:
                            print(f"{os.path.relpath(filepath, frontend_dir)} (line {idx+1}): {line.strip()}")

    print("\n=================================================================")

if __name__ == "__main__":
    find_all_header_tags()
