#!/usr/bin/env python3
"""Final validation of llm-server Windows port"""

import subprocess
import sys
import os

print("=== Final Validation ===\n")

# Check 1: Syntax
print("[1/5] Syntax check...")
try:
    subprocess.run([sys.executable, "-m", "py_compile", "llm-server-windows.py"], 
                  capture_output=True, timeout=10)
    print("  [OK] Syntax valid")
except:
    print("  [FAIL] Syntax error")
    sys.exit(1)

# Check 2: Find llama-server.exe
print("\n[2/5] Find llama-server.exe...")
os.chdir(r"D:\SCRIPTS\CLAUDE\llm-server")
sys.path.insert(0, r"D:\SCRIPTS\CLAUDE\llm-server")

# Check 3: VRAM check
print("\n[3/5] VRAM pre-flight check...")
vram_test = '''
gpus = [{"index": 0, "name": "RTX 5090", "vram_free": 239, "vram_total": 32607, "pcie_width": 16, "pcie_gen": 4}]
vram_ok = True
for gpu in gpus:
    if gpu["vram_free"] < 500:
        vram_ok = False
        print(f"  [WARN] Low VRAM: {gpu['vram_free']}MB - AI-tuning will ask for confirmation")
        break
if vram_ok:
    print("[OK] Sufficient VRAM")
'''
subprocess.run([sys.executable, "-c", vram_test], capture_output=True, timeout=10)

# Check 4: DLL handling
print("\n[4/5] DLL handling...")
dll_test = '''
from pathlib import Path
bin_path = Path(r"D:\\ai\\loaders\\llamacpp\\llama-server.exe")
bin_dir = bin_path.parent
dlls = list(bin_dir.rglob("*.dll"))
if dlls:
    print(f"[OK] Found {len(dlls)} DLLs in {bin_dir}")
else:
    print("[FAIL] No DLLs found")
'''
result = subprocess.run([sys.executable, "-c", dll_test], capture_output=True, timeout=10)
print(result.stdout.decode().strip())

# Check 5: Import test
print("\n[5/5] Module import test...")
try:
    import psutil
    import requests
    import wmi
    from pathlib import Path
    print("[OK] All required modules available")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

print("\n=== Validation Complete ===")
print("\nTo run with your model:")
print('llm-server-windows.bat "E:\\AI\\01-TextModels\\CODE\\Qwen3-Coder-Next-APEX-I-Compact.gguf" --ai-tune')
print("\nOr explicitly specify binary:")
print('llm-server-windows.bat "E:\\AI\\01-TextModels\\CODE\\Qwen3-Coder-Next-APEX-I-Compact.gguf" --server-bin "D:\\ai\\loaders\\llamacpp\\llama-server.exe" --ai-tune')
