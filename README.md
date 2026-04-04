# llm-server

Smart launcher for [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) and [llama.cpp](https://github.com/ggml-org/llama.cpp). Auto-detects your hardware, figures out the optimal configuration, and launches the server — no manual flag tuning required.

**Supports Linux (NVIDIA CUDA), macOS (Apple Silicon Metal), and Windows (via WSL2).**

```bash
llm-server unsloth/Qwen3.5-27B-GGUF --download
```

![demo](demo.gif)

## Why?

Running llama.cpp on multi-GPU setups means juggling dozens of flags. llm-server figures it all out.

<table>
<tr><th>Without llm-server</th><th>With llm-server</th></tr>
<tr>
<td>

```bash
# Figure out layer count from GGUF metadata
# Calculate VRAM split for 3090Ti + 4070 + 3060
# Pick KV cache quant based on remaining headroom
# Set tensor split ratios by PCIe bandwidth
# Enable graph split mode for ik_llama
# Handle fused tensors, MoE expert placement...

llama-server \
  -m model.gguf \
  -ngl 81 \
  --ctx-size 32768 \
  --tensor-split 24,12,12 \
  --split-mode graph \
  -mg 0 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  -fa on \
  --threads 8 \
  --threads-batch 16 \
  -b 4096 \
  -ub 1024 \
  --jinja \
  --run-time-repack \
  -khad \
  -defrag-thold 0.1 \
  --port 8081
```

</td>
<td>

```bash
llm-server model.gguf
```

</td>
</tr>
</table>

It auto-detects your GPUs, reads the GGUF metadata, calculates optimal memory layout, enables the right backend flags, and handles crash recovery — all from a single command.

### Real-world benchmark

Qwen3.5-27B Q4_K_M on 3090 Ti + 4070 + 3060 (ik_llama.cpp):

| | Manual flags | llm-server | Improvement |
|---|---|---|---|
| **Prompt processing** | 160.9 tok/s | 254.0 tok/s | **+58%** |
| **Token generation** | 26.8 tok/s | 41.5 tok/s | **+55%** |

The "manual flags" run uses `-ngl 999 -fa on` and lets the server split across all 3 GPUs with default settings. llm-server recognized the model fits on the 3090 Ti alone — avoiding multi-GPU overhead — and enabled optimized KV quantization, Hadamard K-transform, run-time repacking, and prompt caching automatically.

## Features

- **Built-in GGUF Downloader** — Use `--download` with any HuggingFace repo. Automatically recommends the best quantization based on your total VRAM and System RAM.
- **Native Fused Support** — Full compatibility with fused `ffn_up_gate` models (e.g., AesSedai) using high-performance `ik_llama.cpp` kernels.
- **Lib Hub** — Automatically symlinks all required `.so` libraries into a temporary directory, solving library path issues.
- **Auto GPU detection** — works with 0 to 8+ GPUs, any mix of NVIDIA cards.
- **GPU selection** — `--gpus 0,1` restricts the instance to specific GPUs, enabling multi-instance usage (e.g. 397B on GPUs 0+1, small model on GPU 2).
- **RAM budget** — `--ram-budget 60G` caps RAM usage so multiple instances can coexist without OOM.
- **Split Mode Graph** — Automatically enables `-sm graph` for both `ik_llama.cpp` and mainline for superior multi-GPU scaling.
- **Heterogeneous GPU support** — different VRAM sizes, different PCIe bandwidths, properly weighted.
- **MoE expert auto-placement** — starts conservative, measures actual VRAM usage, optimizes, caches for instant next startup.
- **Vision support** — `--vision` auto-detects and downloads the correct mmproj from HuggingFace. Also works with `--mmproj auto` or a specific path.
- **Auto-update** — `--update` pulls latest ik_llama.cpp and llama.cpp, rebuilds with CUDA, and automatically rolls back if the new binary breaks.
- **Auto-fallback** — if ik_llama.cpp can't load a model (unsupported architecture), automatically switches to mainline llama.cpp mid-launch.
- **Crash recovery** — auto-restarts with backoff on runtime crashes, detects CUDA errors and image decode loops.
- **Benchmark mode** — `--benchmark` to measure tok/s and auto-exit after completion.

## Install

```bash
git clone https://github.com/raketenkater/llm-server.git
cd llm-server
./install.sh
```

### Requirements

**Linux:**
- [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) (recommended) or [llama.cpp](https://github.com/ggml-org/llama.cpp) built with CUDA
- `nvidia-smi` (for GPU detection)
- `python3`, `huggingface_hub`, `tqdm`, `curl`

**macOS (Apple Silicon):**
- [llama.cpp](https://github.com/ggml-org/llama.cpp) built with Metal (or `brew install llama.cpp`)
- `python3`, `huggingface_hub`, `tqdm`, `curl`

**Windows:**
- Install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) (`wsl --install` in PowerShell)
- Inside WSL2, follow the Linux instructions above
- NVIDIA GPU passthrough works automatically in WSL2 with up-to-date drivers

## Usage

```bash
# Basic — auto-detects everything
llm-server model.gguf

# Vision — auto-downloads the matching mmproj from HuggingFace
llm-server model.gguf --vision

# Interactive Download & Recommend — specify any HuggingFace repository
llm-server unsloth/Qwen3.5-27B-GGUF --download

# Update backends — pulls, rebuilds, rolls back if broken
llm-server --update

# Force a specific backend
llm-server --server-bin /path/to/llama-server model.gguf

# Start and run a quick benchmark (auto-exits)
llm-server --benchmark model.gguf

# Multi-instance: big model on GPUs 0+1, small model on GPU 2
llm-server big-model.gguf --gpus 0,1 --port 8081 --ram-budget 90G
llm-server small-model.gguf --gpus 2 --port 8082 --ram-budget 30G
```

## How It Works

### The Smart Downloader
When you use `--download`, the script calculates your total available memory:
`Total = System VRAM + System RAM`
It then looks at the model repository and recommends the quantization level that will give you the best balance of speed and quality for your specific hardware.

### Vision (multimodal)
Many models support image input via a separate mmproj (multimodal projector) file. With `--vision`, llm-server:
1. Checks for an existing mmproj in the model directory
2. Verifies it matches the loaded model (e.g., won't use a Qwen mmproj for Gemma)
3. If missing or mismatched, downloads the correct `mmproj-F16.gguf` from HuggingFace automatically
4. Infers the correct HuggingFace repo from GGUF metadata (`general.basename` + `general.quantized_by`)

You can also use `--mmproj path/to/mmproj.gguf` to specify a file directly.

### Auto-update
`llm-server --update` updates both ik_llama.cpp and llama.cpp backends safely:
1. Backs up the current working binary
2. `git pull` the latest changes
3. Rebuilds with the existing cmake configuration (preserves your CUDA flags)
4. Smoke-tests the new binary
5. If the build fails or the binary crashes → rolls back to the previous commit and restores the backup

This means you can update fearlessly — a broken upstream commit won't leave you without a working server.

### Auto-fallback
If ik_llama.cpp can't load a model (e.g., unsupported architecture like Gemma 4), llm-server automatically:
1. Detects the load failure from the server log
2. Switches to mainline llama.cpp
3. Strips ik_llama-specific flags (graph split, checkpoints, etc.)
4. Retries the launch — no manual intervention needed

This also works via static detection: known unsupported architectures are caught before launch and routed to mainline directly.

### Native Fused Support
Modern GGUF quants often "fuse" tensors (e.g., `ffn_up_gate`) for 10-20% faster processing. While these previously caused crashes on specialized backends, `llm-server` now detects these models and enables the optimized fused kernels in `ik_llama.cpp` automatically.

## License
MIT

---
<p align="right">
  <a href="https://www.buymeacoffee.com/raketenkater">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 32px !important;width: 116px !important;" >
  </a>
</p>
