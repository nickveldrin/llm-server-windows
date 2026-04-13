#!/usr/bin/env python3
"""Test if llama-server can run without DLL copying."""

import subprocess
from pathlib import Path

# Check the current PATH

# Check if D:\ai\loaders\llamacpp is in PATH
llama_dir = Path(r"D:\ai\loaders\llamacpp")

# Try to run the server (without actually starting it, just check if it's findable)
result = subprocess.run(["where", "llama-server.exe"], capture_output=True, text=True)

# Check if Windows can find the DLLs
result = subprocess.run(
    [
        "powershell",
        "-Command",
        "Get-Process -Name llama-server 2>$null; Write-Host 'Process check done'",
    ],
    capture_output=True,
    text=True,
)
