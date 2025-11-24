import os

def fix_mojibake(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # The file was likely read as Latin-1/CP1252 and saved as UTF-8, causing double encoding.
        # To fix: encode back to CP1252 (to get the original UTF-8 bytes) and then decode as UTF-8.
        
        try:
            fixed_content = content.encode('latin1').decode('utf-8')
            
            # Check if it actually changed something
            if fixed_content != content:
                print(f"Fixing {file_path}...")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print("Success.")
            else:
                print(f"{file_path} seems fine (no changes after fix attempt).")
                
        except UnicodeEncodeError:
            print(f"Could not encode {file_path} to cp1252. It might contain characters not in cp1252 or is already fixed.")
        except UnicodeDecodeError:
            print(f"Could not decode {file_path} bytes to utf-8.")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

base_dir = r"d:\OtherProyects\SecApp\secureapprove_django\locale"
files = [
    os.path.join(base_dir, "es", "LC_MESSAGES", "django.po"),
    os.path.join(base_dir, "pt_BR", "LC_MESSAGES", "django.po")
]

for f in files:
    if os.path.exists(f):
        fix_mojibake(f)
    else:
        print(f"File not found: {f}")
