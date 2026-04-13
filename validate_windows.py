#!/usr/bin/env python3
"""Validate llm-server-windows AI-tuning on Windows."""

import subprocess
import sys

# Test 1: Check syntax
try:
    result = subprocess.run([sys.executable, "-m", "py_compile", "llm-server-windows.py"],
                          capture_output=True, timeout=10)
    if result.returncode == 0:
        pass
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)

# Test 2: Check imports
try:
    result = subprocess.run([
        sys.executable, "-c",
        "import os, sys; import psutil, requests, wmi; from pathlib import Path; import tempfile; print('OK')",
    ], capture_output=True, timeout=10)
    if result.returncode == 0:
        pass
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)

# Test 3: Check key functions exist
test_script = """
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
"""

result = subprocess.run([sys.executable, "-c", test_script],
                       capture_output=True, timeout=15)
if result.returncode == 0:
    output = result.stdout.decode().strip()
    for _line in output.split("\n"):
        pass
else:
    sys.exit(1)

