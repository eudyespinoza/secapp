
def inspect_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if "Categor" in line:
            print(f"Line {i+1}: {line.strip()}")
            # Print repr to see exact chars
            print(f"Repr: {repr(line.strip())}")

print("--- ES ---")
inspect_file(r"d:\OtherProyects\SecApp\secureapprove_django\locale\es\LC_MESSAGES\django.po")
print("\n--- PT_BR ---")
inspect_file(r"d:\OtherProyects\SecApp\secureapprove_django\locale\pt_BR\LC_MESSAGES\django.po")
