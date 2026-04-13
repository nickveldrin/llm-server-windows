#!/usr/bin/env python3
"""Test if llama-server can run without DLL copying"""

import subprocess
import os
from pathlib import Path

# Check the current PATH
print("Current PATH (first 500 chars):")
print(os.environ.get("PATH", "")[:500])
print()

# Check if D:\ai\loaders\llamacpp is in PATH
llama_dir = Path(r"D:\ai\loaders\llamacpp")
print(f"Is {llama_dir} in PATH? {str(llama_dir) in os.environ.get('PATH', '')}")

# Try to run the server (without actually starting it, just check if it's findable)
result = subprocess.run(["where", "llama-server.exe"], capture_output=True, text=True)
print(f"\nwhere llama-server.exe:")
print(result.stdout if result.stdout else "(not found)")

# Check if Windows can find the DLLs
result = subprocess.run(["powershell", "-Command", "Get-Process -Name llama-server 2>$null; Write-Host 'Process check done'"], capture_output=True, text=True)
