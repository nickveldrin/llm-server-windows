#!/usr/bin/env python3
"""Quick syntax validation check"""

import py_compile
import sys

try:
    py_compile.compile("llm-server-windows.py", doraise=True)
    print("Syntax OK - llm-server-windows.py compiles successfully")
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)
