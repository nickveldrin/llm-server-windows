#!/usr/bin/env python3
"""Validate llm-server-windows AI-tuning on Windows"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

print("=== Windows AI-Tuning Validation ===\n")

# Test 1: Check syntax
print("[1/3] Checking Python syntax...")
try:
    result = subprocess.run([sys.executable, "-m", "py_compile", "llm-server-windows.py"], 
                          capture_output=True, timeout=10)
    if result.returncode == 0:
        print("  [OK] Syntax valid")
    else:
        print(f"  [FAIL] Syntax error\n{result.stderr.decode()}")
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] {e}")
    sys.exit(1)

# Test 2: Check imports
print("\n[2/3] Checking Python imports...")
try:
    result = subprocess.run([
        sys.executable, "-c",
        "import os, sys; import psutil, requests, wmi; from pathlib import Path; import tempfile; print('OK')"
    ], capture_output=True, timeout=10)
    if result.returncode == 0:
        print("  [OK] All imports work")
    else:
        print(f"  [FAIL] Import error\n{result.stderr.decode()}")
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] {e}")
    sys.exit(1)

# Test 3: Check key functions exist
print("\n[3/3] Checking AI-tune functions...")
test_script = '''
import os, sys
sys.path.insert(0, os.getcwd())

# Source the module without shebang
exec(open("llm-server-windows.py").read().replace("#!/usr/bin/env python3", ""))

# Check key functions exist
funcs = ["ai_tune", "build_hw_profile", "build_model_profile", 
         "build_flags", "get_server_help", "run_benchmark", 
         "start_server", "kill_server", "check_server_health"]

missing = [f for f in funcs if f not in dir()]
if missing:
    print(f"  [FAIL] Missing functions: {missing}")
    sys.exit(1)

print(f"  [OK] All {len(funcs)} functions present")

# Test hardware profiling
gpus = [{"index": 0, "name": "RTX 4090", "vram_free": 24576, "vram_total": 24576, "pcie_width": 16, "pcie_gen": 4}]
hw = build_hw_profile(gpus, 65536, 24)
print(f"  [OK] Hardware profile: {len(hw)} bytes")

# Test model profiling
model = build_model_profile("test.gguf", "llama", 32, 1, 5000, False, 0, 24576, 65536)
print(f"  [OK] Model profile: {len(model)} bytes")

# Test flag building
from pathlib import Path
flags = build_flags(Path("test.gguf"), gpus, 24, 65536)
print(f"  [OK] Flag builder: {len(flags)} flags")
'''

result = subprocess.run([sys.executable, "-c", test_script], 
                       capture_output=True, timeout=15)
if result.returncode == 0:
    output = result.stdout.decode().strip()
    for line in output.split('\n'):
        print(f"  {line}")
else:
    print(f"  [FAIL] Function test failed")
    print(result.stderr.decode())
    sys.exit(1)

print("\n=== Validation Complete ===")
print("\nAI-tuning is ready for Windows!")
print("\nTo run actual tuning, you need:")
print("  1. A GGUF model file")
print("  2. llama-server binary (build from llama.cpp or ik_llama.cpp)")
print("  3. GPU with nvidia-smi support")
print("  4. Access to an LLM API for tuning suggestions")
print("\nUsage: llm-server-windows.bat model.gguf --ai-tune")
