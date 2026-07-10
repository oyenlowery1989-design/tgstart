#!/usr/bin/env python3
"""
Diagnostic Tool for Session Converter
======================================
Run this script to check if your environment is properly configured.
"""

import sys
import os
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def check_python_version():
    """Check Python version."""
    print("\n[Python Version]")
    version = sys.version_info
    print(f"  Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ❌ FAIL: Python 3.8 or higher required")
        return False
    else:
        print("  ✅ PASS: Version is compatible")
        return True

def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name
    
    try:
        module = __import__(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"  ✅ {package_name}: {version}")
        return True
    except ImportError:
        print(f"  ❌ {package_name}: NOT INSTALLED")
        return False

def check_dependencies():
    """Check all required dependencies."""
    print("\n[Required Packages]")
    
    results = {
        'telethon': check_package('telethon'),
        'opentele': check_package('opentele'),
    }
    
    print("\n[Optional Packages]")
    results['tgcrypto'] = check_package('tgcrypto')
    
    print("\n[Alternative Packages]")
    results['tgconvertor'] = check_package('tgconvertor')
    
    return results

def check_session_file():
    """Check for session files in the current directory."""
    print("\n[Session Files]")
    
    session_files = list(Path('.').glob('*.session'))
    
    if not session_files:
        print("  ❌ No .session files found in current directory")
        print(f"  Current directory: {os.getcwd()}")
        return False
    else:
        print(f"  ✅ Found {len(session_files)} session file(s):")
        for f in session_files:
            size = f.stat().st_size
            print(f"     - {f.name} ({size:,} bytes)")
        return True

def check_script_file():
    """Check if the main script exists."""
    print("\n[Script Files]")
    
    if Path('session_to_tdata_converter.py').exists():
        print("  ✅ session_to_tdata_converter.py found")
        return True
    else:
        print("  ❌ session_to_tdata_converter.py NOT FOUND")
        return False

def get_installation_commands(results):
    """Generate installation commands based on missing packages."""
    missing = [pkg for pkg, installed in results.items() 
               if not installed and pkg in ['telethon', 'opentele']]
    
    if not missing and not results.get('tgcrypto', False):
        # Only tgcrypto missing
        return [
            "pip install tgcrypto-pyrofork",
            "# OR if above fails:",
            "# Just continue without it - script will work (slower)"
        ]
    
    if missing:
        return [
            f"pip install {' '.join(missing)} tgcrypto-pyrofork",
            "# OR without tgcrypto:",
            f"pip install {' '.join(missing)}"
        ]
    
    return ["# All required packages are installed!"]

def main():
    """Run all diagnostic checks."""
    print_header("SESSION CONVERTER DIAGNOSTIC TOOL")
    
    print("\nThis tool will check if your environment is ready to run the converter.\n")
    
    # Run all checks
    python_ok = check_python_version()
    deps = check_dependencies()
    session_ok = check_session_file()
    script_ok = check_script_file()
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    
    all_required = deps.get('telethon', False) and deps.get('opentele', False)
    
    print("\n[Status]")
    print(f"  Python Version: {'✅ PASS' if python_ok else '❌ FAIL'}")
    print(f"  Required Packages: {'✅ PASS' if all_required else '❌ FAIL'}")
    print(f"  Session File: {'✅ PASS' if session_ok else '❌ WARN'}")
    print(f"  Script File: {'✅ PASS' if script_ok else '❌ FAIL'}")
    print(f"  TGCrypto (optional): {'✅ PASS' if deps.get('tgcrypto', False) else '⚠️  WARN'}")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    if not all_required:
        print("\n❌ REQUIRED ACTIONS:")
        print("\n   Install missing packages with:\n")
        for cmd in get_installation_commands(deps):
            print(f"   {cmd}")
    
    elif not deps.get('tgcrypto', False):
        print("\n⚠️  OPTIONAL IMPROVEMENT:")
        print("\n   For faster encryption, install tgcrypto:")
        print("   pip install tgcrypto-pyrofork\n")
        print("   The script will work without it, just slower.")
    
    if not session_ok:
        print("\n⚠️  WARNING:")
        print("\n   No .session files found in current directory.")
        print("   Make sure to:")
        print("   1. Place your .session file in the same folder as the script")
        print("   2. Update SESSION_NAME in the script to match your file")
    
    if not script_ok:
        print("\n❌ ERROR:")
        print("\n   Main script not found!")
        print("   Make sure session_to_tdata_converter.py is in this directory.")
    
    # Final verdict
    print_header("FINAL VERDICT")
    
    if python_ok and all_required and script_ok:
        print("\n✅ Your environment is ready!")
        print("\nNext steps:")
        print("  1. Edit session_to_tdata_converter.py")
        print("  2. Set SESSION_NAME, API_ID, and API_HASH")
        print("  3. Run: python session_to_tdata_converter.py")
        if not session_ok:
            print("\n  ⚠️  Don't forget to add your .session file!")
    else:
        print("\n❌ Your environment needs attention")
        print("\nPlease address the issues above before running the converter.")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Diagnostic failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
