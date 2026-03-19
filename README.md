# llm-server

Smart launcher for [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) and [llama.cpp](https://github.com/ggml-org/llama.cpp). Auto-detects your hardware, figures out the optimal configuration, and launches the server — no manual flag tuning required.

**Supports Linux (NVIDIA CUDA), macOS (Apple Silicon Metal), and Windows (via WSL2).**

```bash
llm-server unsloth/Qwen3.5-27B-GGUF --download
```

![demo](demo.gif)

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
- **Crash recovery** — auto-restarts with backoff on runtime crashes.
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

# Interactive Download & Recommend — specify any HuggingFace repository
llm-server unsloth/Qwen3.5-27B-GGUF --download

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
