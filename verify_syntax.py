#!/usr/bin/env python3
"""Quick syntax validation check."""

import py_compile
import sys

try:
    py_compile.compile("llm-server-windows.py", doraise=True)
    sys.exit(0)
except py_compile.PyCompileError:
    sys.exit(1)
