#!/usr/bin/env python3
"""What are the DLLs in your llama directory?"""

from pathlib import Path

bin_dir = Path(r"D:\ai\loaders\llamacpp")
dlls = sorted(bin_dir.glob("*.dll"))

for _dll in dlls:
    pass
