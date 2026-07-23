import os
import re
import sys
from pathlib import Path

def compile_po_to_mo(po_path, mo_path):
    """Manually compile a .po file to .mo format"""
    try:
        import polib
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print(f"Compiled: {po_path} -> {mo_path}")
        return True
    except ImportError:
        print("polib not installed. Installing...")
        os.system(f"{sys.executable} -m pip install polib")
        import polib
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print(f"Compiled: {po_path} -> {mo_path}")
        return True
    except Exception as e:
        print(f"Error compiling {po_path}: {e}")
        return False

def compile_all_translations():
    """Find and compile all .po files in locale directory"""
    locale_dir = Path("locale")
    if not locale_dir.exists():
        print("No locale directory found!")
        return
    
    compiled_count = 0
    for po_file in locale_dir.rglob("*.po"):
        if po_file.name.endswith(".po"):
            mo_file = po_file.with_suffix(".mo")
            if compile_po_to_mo(po_file, mo_file):
                compiled_count += 1
    
    print(f"\n✅ Successfully compiled {compiled_count} translation file(s)")
    if compiled_count == 0:
        print("⚠️  No translations were compiled. Check the locale directory structure.")

if __name__ == "__main__":
    compile_all_translations()