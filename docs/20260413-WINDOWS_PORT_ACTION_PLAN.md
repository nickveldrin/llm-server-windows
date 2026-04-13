# llm-server Windows Port - Complete Action Plan
**Created:** 2026-04-13  
**Status:** Review Complete - Awaiting Clarification

---

## Executive Summary

The Linux llm-server has sophisticated MoE expert placement, KV quantization, and AI-tuning. The Windows port (`llm-server-windows.py`) already implements much of this, but has critical issues:

1. **VRAM loading issue** - Models load to system RAM instead of GPU VRAM (Issue #7)
2. **Incomplete requirements.txt** - No `.venv` handling
3. **Missing `.gitignore`** - Should exclude `.venv` directories
4. **No GUI launcher** - Windows equivalent of `llm-server-gui`
5. **Limited AI-tune parameter coverage** - Missing KV quantization and other flags
6. **Incomplete MoE handling** - No expert split placement logic

---

## Requirements

### 1. ✅ Proper `requirements.txt` and `.venv` Handling

**Linux/Windows Standard:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

**Current Issues:**
- `requirements-windows.txt` is malformed: `pip install psutil requests wmi` (invalid format)
- No `.venv` detection in startup script
- No `.gitignore` entries for `.venv`

**Required Fixes:**
- [ ] Create proper `requirements.txt` format:
  ```
  psutil>=5.9.0
  requests>=2.31.0
  wmi>=1.5.1
  ```
- [ ] Add `.gitignore` entry: `.venv/`
- [ ] Modify `install-windows.bat` to:
  - Detect existing `.venv`
  - Skip creation if exists
  - Auto-activate `.venv` for subsequent runs
- [ ] Modify `llm-server-windows.bat` to detect and use `.venv`

**Implementation Notes:**
- Check for `.venv` existence at startup
- If `.venv` exists, use it; if not, prompt or create automatically
- Update PATH to use `.venv\Scripts\python.exe`

---

### 2. ✅ `.gitignore` for Virtual Environment Directories

**Add to `.gitignore`:**
```
# Virtual environments
.venv/
venv/
__pycache__/
*.pyc
```

- [ ] Update existing `.gitignore`
- [ ] Ensure all venv-named directories are ignored

---

### 3. ✅ Windows GUI Launcher (Port of `llm-server-gui`)

**Current Linux GUI Features:**
- Interactive model selection from directory
- Option toggles: AI Tune, Benchmark, Vision, OpenCode, Dry Run
- Backend preference (ik_llama vs llama.cpp)
- AI Tune rounds configuration
- Persistent config storage

**Required Windows GUI Implementation:**

**Options A - Python/Tkinter GUI:**
```python
# llm-server-windows-gui.py
- File dialog for model selection
- Checkboxes for options
- Dropdown for backend selection
- Text input for AI Tune rounds
- Save preferences to config.json
```

**Options B - Console-based TUI (simpler):**
- Same structure as `llm-server-gui`
- Use Python's `curses` or simple menu system
- Keyboard shortcuts for toggles

**Required Features:**
- [ ] Model directory scanning and display
- [ ] Option toggles (a=AI Tune, b=Benchmark, v=Vision, o=OpenCode, d=Dry Run)
- [ ] Backend selection (ik_llama/llama.cpp)
- [ ] AI Tune rounds config (1-20, default 8)
- [ ] Persistent config saving
- [ ] GPU-aware model display (show MoE vs dense)

---

### 4. ✅ AI-tune Parameter Completeness

**Linux AI-tune Supports:**
- All llama.cpp/ik_llama.cpp flags via JSON
- KV quantization: `--cache-type-k q8_0/q4_0`, `--cache-type-v`
- Hadamard K-cache: `-khad` (auto-enabled for quantized KV)
- Split modes: `--split-mode graph/row/layer`
- Tensor split: `--tensor-split`
- Batch settings: `-b`, `-ub`
- Context size: `--ctx-size`
- Thread settings: `--threads`, `--threads-batch`

**Windows AI-tune Issues:**
- Current implementation missing KV quantization flags
- Missing split mode configuration
- Missing `-khad` flag automation
- Missing batch size adjustments

**Required Windows Updates:**

**Update `build_flags()` function:**
- [ ] Add KV quantization flags based on VRAM
- [ ] Auto-enable `-khad` for quantized KV
- [ ] Support all llama.cpp flags in JSON overrides
- [ ] Add split mode selection (graph > row > layer priority)

**Update AI-tune system prompt:**
- [ ] Include full flag documentation from `--help`
- [ ] Explain KV quantization options
- [ ] Explain split mode options
- [ ] Explain expert placement flags (for MoE models)

---

### 5. ✅ Smart MoE Expert Placement (Critical - Issue #6)

**Linux Implementation (from `llm-server` bash):**

**Detection:**
```bash
# Parse GGUF metadata for expert count
EXPERT_COUNT=$(grep -o '"general.file_type"[^}]*' model.gguf | grep -o '[0-9]*')
IS_MOE=0
(( EXPERT_COUNT > 1 )) && IS_MOE=1
```

**Per-Layer Expert Size:**
```bash
# Calculate from actual GGUF tensor data
EXPERT_BYTES=$(grep -E 'ffn_(gate_up|up_gate|gate|up|down)_exps' tensors.json | awk '{sum+=$2} END {print sum}')
EXPERT_PER_LAYER_MB=$(( EXPERT_TOTAL_MB / LAYER_COUNT ))
```

**GPU Layer Allocation:**
```bash
# Budget percentages: 70% 55% 50% 45% 40% 35% 30% 25%
# Primary GPU gets extra headroom for embeddings/output
# Cost per layer = Expert + Attention + KV Cache
LAYERS_PER_GPU[0]=$(( (VRAM_FREE[0] - OVERHEAD) * 70% / COST_PER_LAYER ))
LAYERS_PER_GPU[1]=$(( (VRAM_FREE[1]) * 55% / COST_PER_LAYER ))
# etc.
```

**Expert Split String (`-ot` flag):**
```bash
# Example:Experts on GPU 0 (layers 0-2), GPU 1 (layers 3-5), CPU (rest)
-ot "blk.(0-2).ffn_(gate_up|up_gate|gate|up|down)_exps.*=CUDA0,blk.(3-5).ffn_(gate_up|up_gate|gate|up|down)_exps.*=CUDA1,exps=CPU"
```

**Gentle Load Optimization:**
```bash
# Phase 1: Conservative placement
# Phase 2: Measure actual VRAM, add more layers if space available
# Phase 3: Save optimal config to cache
# Phase 4: Restart with optimized placement
```

**Required Windows Implementation:**

**Update `get_model_info()` in Windows Python:**
- [ ] Parse `general.file_type` for expert count
- [ ] Calculate expert bytes from tensor data
- [ ] Return `experts` field with accurate count

**Update `build_flags()` in Windows Python:**
- [ ] Detect MoE models (`experts > 1`)
- [ ] Calculate expert size per layer
- [ ] Calculate GPU layer budgets with decreasing percentages
- [ ] Build `-ot` string for expert placement
- [ ] Handle `-muge` and `-ger` flags (ik_llama.cpp fused experts)

**Update AI-tune for MoE:**
- [ ] Include MoE expert placement in hardware profile
- [ ] Lock expert placement during AI-tune rounds
- [ ] Add `-ot` string to AI-tune flag overrides
- [ ] Cache expert placement configs

**MoE-Only Flags for Windows:**
```python
# For MoE models, add these flags automatically:
if is_moe:
    flags.extend(["-ngl", "999"])  # All non-experts to GPU
    flags.extend(["--no-mmap"])     # Prevent virtual memory blowout
    if use_ik_llama:
        flags.extend(["-muge"])     # Merge up/gate expert tensors
        flags.extend(["-ger"])      # Grouped expert routing
```

---

### 6. ✅ Additional Windows Improvements

#### 6.1 VRAM Loading Issue (Critical - Issue #7)

**Current Problem:**
Windows version loads model into system RAM instead of GPU VRAM immediately. User reports 60 second load time before killing process.

**Root Cause Analysis - CODE REVIEW of `llm-server-windows.py` (lines 1073-1130):**

**Analysis of YOUR Working Qwen3-Coder-Next Command:**
```bash
# Your working command does NOT use -ngl at all:
D:\ai\loaders\llamacpp\llama-server.exe ^
  --model .\Qwen3-Coder-Next-apex-i-compact.gguf ^
  # ... other flags ...
  --no-mmap ^           # ✅ PRESENT
  --n-cpu-moe 16 ^      # ✅ MoE expert split
  --batch-size 4096 ^
  # ... more flags ...
```

**Key Insight from Your Working Command:**
| Flag | Status | Note |
|------|--------|------|
| `--no-mmap` | ✅ REQUIRED | Without this, VRAM loading fails |
| `-ngl` | ❌ NOT USED | Your working command doesn't have it! |
| `--n-cpu-moe <N>` | ✅ MoE models | Specifies CPU expert count |
| `-ot` | ❌ NOT USED | You prefer `--n-cpu-moe` approach |

**Current Windows Code (lines 1073-1130) - PROBLEM:**
```python
# Lines 1109-1111:
flags.extend(["-ngl", "999"])         # ❌ Not needed for dense models
flags.extend(["-mg", str(gpu_list[0]["index"])])
# Missing: Nothing for dense models (loads to VRAM by default)
# Missing: --no-mmap for MoE models (needed for VRAM + CPU expert split)
```

**Your Working Qwen3-Coder-Next (MoE) Command:**
```bash
# --no-mmap IS present, AND --n-cpu-moe 16 for expert split
--no-mmap ^
--n-cpu-moe 16 ^
```

**Your Dense Model (Qwen3.5-27B) - NO --no-mmap:**
```bash
# Dense models load to VRAM by default, NO --no-mmap needed
# Only MoE models need --no-mmap + --n-cpu-moe
```

**Key Insight:**
| Model Type | `--no-mmap` needed? | Expert Split Method |
|------------|---------------------|---------------------|
| Dense | ❌ No (auto VRAM) | N/A |
| MoE | ✅ Yes | `--n-cpu-moe <N>` or `-ot "..."` |

**Required Windows Fixes:**

**Update `build_flags()` function with CORRECT logic:**
```python
def build_flags(model_path, gpu_list, cpu_cores, ram_mb, verbose):
    flags = [
        "-m", str(model_path),
        "--host", HOST,
        "--port", str(PORT),
        "--ctx-size", str(CTX_SIZE),
        "--flash-attn", "on",
        "--jinja",
        "--threads", str(cpu_cores),
        "--threads-batch", str(cpu_cores),
    ]
    
    if gpu_list:
        # Multi-GPU tensor split (only if multiple GPUs)
        if len(gpu_list) > 1:
            splits = ",".join(["1"] * len(gpu_list))
            flags.extend(["--tensor-split", splits])
        
        # MoE expert placement
        layers, experts, metadata = get_model_info(model_path)
        if experts > 1:
            # MoE models: need --no-mmap + --n-cpu-moe <N>
            # Determine --n-cpu-moe via llama-fit-params.exe
            n_cpu_moe = determine_n_cpu_moe(model_path, gpu_list)
            flags.extend(["--no-mmap"])
            flags.extend(["--n-cpu-moe", str(n_cpu_moe)])
            # Also add -cram for CPU RAM budget
            flags.extend(["-cram", str(ram_mb)])
        else:
            # Dense models: let auto VRAM loading work, NO --no-mmap needed
            pass
    else:
        # CPU-only mode
        flags.extend(["-b", "1024", "-ub", "128"])
    
    return flags
```

**Add GPU Memory Verification:**
```python
def verify_vram(model_path, gpu_list):
    """Verify model fits in GPU VRAM before loading"""
    model_mb = get_model_size(model_path)
    total_vram = sum(g["vram_free"] for g in gpu_list)
    vram_needed = int(model_mb * 1.3)  # 30% overhead
    
    if vram_needed > total_vram:
        print(f"⚠ Model needs {vram_needed}MB, but GPU has {total_vram}MB")
        print("  Options:")
        print("  - Use smaller quantization")
        print("  - Reduce context size: --ctx-size 4096")
        response = input("Continue anyway? (y/N): ")
        if response.strip().lower() != 'y':
            return False
    return True
```

**Update `start_server()` function:**
- [ ] Call `verify_vram()` before launch
- [ ] Add `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` for proper Windows process management
- [ ] Add GPU memory check in server startup logs

#### 6.2 Python Import Cleanup

**Issue:** Windows script has duplicate imports (lines 7-35)

**Fix:**
```python
# Remove duplicate imports, keep only once
import os
import sys
import subprocess
import tempfile
import ctypes  # Windows only
import re
import json
import hashlib
import shutil
import time
import threading
import uuid
import struct
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, Callable
import psutil
import requests
import wmi
```

#### 6.3 Better Binary Detection

**Current Issue:** Binary detection only checks user home directories

**Required Improvements:**
- [ ] Check common installation paths (Program Files, AppData)
- [ ] Support environment variable `LLAMA_SERVER_PATH`
- [ ] Provide clear error if binary not found
- [ ] Auto-detect if `ik_llama.cpp` or `llama.cpp` binary

#### 6.4 Proper Benchmarking

**Current Issue:** Benchmark uses `/v1/chat/completions` which requires chat template

**Linux Benchmark:**
```bash
# Uses /slots endpoint directly for tok/s measurement
curl -s http://127.0.0.1:8081/slots | jq '.[0].n_decoded / (.t_token_generation / 1000)'
```

**Windows Fix:**
```python
def run_benchmark(url, port):
    """Run benchmark via /slots endpoint"""
    try:
        # Wait for server to be ready
        time.sleep(2)
        
        # Get benchmark data from /slots
        response = requests.get(f"{url}/slots", timeout=5)
        if response.status_code == 200:
            slots = response.json()
            if slots:
                slot = slots[0]
                n_decoded = slot.get("n_decoded", 0)
                t_gen = slot.get("t_token_generation", 0)
                
                if t_gen > 0:
                    gen_tps = n_decoded / (t_gen / 1000)
                    return gen_tps, 0.0
        
        return 0.0, 0.0
    except:
        return 0.0, 0.0
```

---

## Priority Implementation Order

### Phase 1: Critical (Blockers)
1. ✅ Fix VRAM loading issue (Issue #7) - **HIGHEST PRIORITY**
   - Add `--no-mmap` flag for reliable VRAM loading
   - Add `-ot` string for MoE expert placement
   - Verify VRAM before launch

2. ✅ Create proper `.venv` handling
   - Fix `requirements.txt` format
   - Add `.venv` detection
   - Update batch files to use `.venv`

3. ✅ Add `.venv` to `.gitignore`

4. ✅ **Integrate `llama-fit-params.exe` for MoE models** - **NEW CRITICAL**
   - Detect if `llama-fit-params.exe` available
   - Call it with parameters: `--model`, `--flash-attn on`, `--batch-size 4096`, `--ubatch-size 2048`, `--cache-type-k q8_0`, `--cache-type-v q8_0`
   - Parse output for `--n-cpu-moe` value and `-ot` string
   - Leave 1GB VRAM buffer (1024 MB - default in llama-fit-params)
   - Auto-detect max context size (from `-c` parameter in output)
   - Apply buffer to max context (e.g., reduce from 140032 to 131072 based on user comfort)
   - Fallback to heuristic if `llama-fit-params.exe` not found
   - Cache results per model for reuse

### Phase 2: High Priority
5. ✅ Port Linux GUI to Windows (TUI match)
   - TUI menu for model selection
   - Option toggles
   - Backend preference

6. ✅ Fix AI-tune parameter coverage
   - Add KV quantization flags
   - Add split mode flags
   - Update system prompt

7. ✅ Implement smart MoE expert placement using llama-fit-params
   - Call `llama-fit-params.exe` to get optimal parameters
   - Parse `--n-cpu-moe` value and `-ot` string
   - Cache results for reuse
   - AI-tune optimizes `--n-cpu-moe` value and other flags

### Phase 3: Medium Priority
7. ✅ Improve binary detection
8. ✅ Fix Python import cleanup
9. ✅ Improve benchmarking
10. ✅ Better error messages

### Phase 4: Nice to Have
11. ✅ Auto-update improvements
12. ✅ Download from HuggingFace
13. ✅ OpenCode integration

---

## Questions for Clarification

### MoE Implementation Questions

**Q1: MoE Models You're Using**
✅ **Answer:** Other MoE models (Qwen3-Coder-Next, Qwen3.5-35B-A3B, etc.)

**Q2: Expert Split Strategy**
✅ **Answer:** Use `llama-fit-params.exe` to determine optimal `--n-cpu-moe` value:
- Auto-detect max context size that fits VRAM with 1GB buffer
- Let AI-tune optimize the `--n-cpu-moe` value
- Use llama.cpp backend (not ik_llama.cpp)

**Q3: Backend Preference**
✅ **Answer:** llama.cpp (for MoE models)

**Q4: VRAM Loading Test**
✅ **Answer:** Single GPU (RTX 5090, 32GB VRAM)

**Q5: GUI Type**
✅ **Answer:** Match Linux TUI style (easiest to implement and maintain)

### GUI Questions

**Q5: GUI Type Preference**
Which GUI style do you prefer?
- [ ] Python/Tkinter desktop GUI (like traditional Windows app)
- [ ] Console-based TUI (like Linux `llm-server-gui`)
- [ ] Web-based GUI (browser interface)

**Q6: GUI Features**
Which features are essential?
- [ ] Model selection menu
- [ ] Backend preference selection
- [ ] AI-tune toggles
- [ ] GPU selection
- [ ] Context size configuration
- [ ] All of the above

### Requirements.txt Questions

**Q7: Package Manager Preference**
Do you want to use:
- [ ] `pip` (standard)
- [ ] `uv` (faster, modern)
- [ ] Both (auto-detect `uv`, fallback to `pip`)

**Q8: Virtual Environment Behavior**
Should the script:
- [ ] Auto-create `.venv` if missing
- [ ] Ask user whether to create `.venv`
- [ ] Require user to create `.venv` manually

---

## GitHub Repository Setup (New - 2026-04-13)

### Current State
- Repository: `https://github.com/nickveldrin/llm-server-windows`
- Owner: `nickveldrin`
- Status: **Personal repository** (not a fork)

### Tasks

#### 1. ✅ Clean Up GitHub Workflows
- [ ] Review existing workflows in `.github/workflows/`
- [ ] Remove Linux-specific workflows (shellcheck.yml)
- [ ] Create Windows-specific workflows (if needed):
  - Python linting (pylint/flake8)
  - Windows compatibility tests
  - Binary build verification (Windows)
- [ ] Disable workflows if not needed for Windows-only project

#### 2. ✅ Enable GitHub Actions
- [ ] Verify Actions are enabled on `nickveldrin/llm-server-windows`
- [ ] Test basic workflow (hello-world style)
- [ ] Configure Actions permissions (read/write as needed)

#### 3. ✅ Configure Dependabot
- [ ] Create `.github/dependabot.yml`
- [ ] Enable Python package updates
- [ ] Enable GitHub Actions version updates
- [ ] Set update frequency (weekly recommended)
- [ ] Enable security updates (automatic)
- [ ] Enable version updates (automatic)

**Dependabot Configuration:**
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "python"
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 3
    labels:
      - "dependencies"
      - "github-actions"
```

#### 4. ✅ Enable Branch Protection
- [ ] Require pull requests for `main` branch
- [ ] Require code review approval (1 reviewer minimum)
- [ ] Require status checks to pass before merging
- [ ] Include administrators in restrictions (optional)
- [ ] Enable required linear history (optional)

**Why Branch Protection?**
- Prevents accidental direct commits to `main`
- Ensures code review for all changes
- Maintains clean git history
- Important for shared/maintained projects

---

## Next Steps

1. **Answer the questions above** so I can implement exactly what you need
2. **Provide your GPU specs and model files** so I can test VRAM loading
3. **Review the checklist document** and add any missing items
4. **I'll implement** all critical fixes first (VRAM, `.venv`, MoE)

---

## References

- **Linux `llm-server` source:** `D:\SCRIPTS\CLAUDE\llm-server\llm-server` (3255 lines)
- **Linux GUI source:** `D:\SCRIPTS\CLAUDE\llm-server\llm-server-gui` (350 lines)
- **Current Windows port:** `D:\SCRIPTS\CLAUDE\llm-server\llm-server-windows.py` (1548 lines)
- **Download script:** `D:\SCRIPTS\CLAUDE\llm-server\download_any_gguf.py`

---

**Document Status:** Draft - Awaiting User Clarification

**Next Update:** After user responds to questions
