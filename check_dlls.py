#!/usr/bin/env python3
"""What are the DLLs in your llama directory?"""

from pathlib import Path

bin_dir = Path(r"D:\ai\loaders\llamacpp")
dlls = sorted(bin_dir.glob("*.dll"))

print(f"DLLs in {bin_dir}:\n")
for dll in dlls:
    print(f"  {dll.name}")

print(f"\nTotal: {len(dlls)} DLLs")
