# llm-server

Smart launcher for [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) and [llama.cpp](https://github.com/ggml-org/llama.cpp). Auto-detects your hardware, figures out the optimal configuration, and launches the server — no manual flag tuning required.

```bash
llm-server ~/ai_models/Qwen3.5-397B-A17B-UD-IQ3_XXS.gguf
```

![demo](demo.gif)

## Features

- **Smart Switcher** — Auto-detects fused `ffn_up_gate` tensors and switches to mainline `llama.cpp` to prevent `ik_llama.cpp` crashes.
- **Lib Hub** — Automatically symlinks all required `.so` libraries into a temporary directory, solving library path issues.
- **Auto GPU detection** — works with 0 to 8+ GPUs, any mix of NVIDIA cards.
- **Split Mode Graph** — Automatically enables `-sm graph` for both `ik_llama.cpp` and mainline for superior multi-GPU scaling.
- **Heterogeneous GPU support** — different VRAM sizes, different PCIe bandwidths, properly weighted.
- **MoE expert auto-placement** — starts conservative, measures actual VRAM usage, optimizes, caches for instant next startup.
- **Smart KV cache** — picks q8_0 when there's headroom, falls back to q4_0 when tight.
- **Crash recovery** — auto-restarts with backoff on runtime crashes.
- **Benchmark mode** — `--benchmark` to measure tok/s and auto-exit after completion.

## Install

```bash
git clone https://github.com/raketenkater/llm-server.git
cp llm-server/llm-server llm-server/llm-server-gui ~/.local/bin/
```

### Requirements

- [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) (recommended) or [llama.cpp](https://github.com/ggml-org/llama.cpp) built with CUDA
- `nvidia-smi` (for GPU detection)
- `python3` (for GGUF metadata parsing)
- `curl` (for health checks and benchmarks)

## Usage

```bash
# Basic — auto-detects everything
llm-server model.gguf

# Force a specific backend
llm-server --server-bin /path/to/llama-server model.gguf

# Start and run a quick benchmark (auto-exits)
llm-server --benchmark model.gguf

# Force CPU-only (ignore GPUs)
llm-server --cpu model.gguf
```

## How It Works

### Strategy Selection
The script evaluates your hardware and model, then picks the best strategy:
- `single_gpu`: Fits entirely in the fastest VRAM.
- `multi_gpu_dense`: Parallelizes across all GPUs using **Split Mode Graph**.
- `moe_offload`: Optimized expert placement for `ik_llama.cpp`.
- `cpu_only`: Fallback for systems without GPUs.

### The Smart Switcher
Newer mainline `llama.cpp` quants often "fuse" tensors (e.g., `ffn_up_gate`). While these provide a 10-20% prefill boost in mainline, they cause a hard crash in `ik_llama.cpp`. `llm-server` peeks at the model's metadata and automatically switches to the correct backend.

## License
MIT
