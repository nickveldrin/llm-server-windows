# llm-server

Smart launcher for [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) and [llama.cpp](https://github.com/ggml-org/llama.cpp). Auto-detects your hardware, figures out the optimal configuration, and launches the server — no manual flag tuning required.

```bash
llm-server ~/ai_models/Qwen3.5-397B-A17B-UD-IQ3_XXS.gguf
```

That's it. It handles everything: GPU detection, MoE expert placement, KV cache sizing, context reduction, crash recovery.

## Features

- **Auto GPU detection** — works with 0 to 8+ GPUs, any mix of NVIDIA cards
- **Heterogeneous GPU support** — different VRAM sizes, different PCIe bandwidths, properly weighted
- **MoE expert auto-placement** — starts conservative, measures actual VRAM usage, optimizes, caches for instant next startup
- **Smart KV cache** — picks q8_0 when there's headroom, falls back to q4_0 when tight
- **Dynamic batch sizing** — scales with available VRAM
- **Crash recovery** — auto-restarts with backoff on runtime crashes
- **Config caching** — first run auto-tunes, subsequent runs start instantly
- **SSM/Mamba hybrid support** — detects and disables incompatible features
- **GGUF metadata parsing** — reads layer count, expert count, KV heads directly from model file
- **Benchmark mode** — `--benchmark` to measure tok/s after startup
- **Dry-run mode** — `--dry-run` to print the command without executing

## Install

```bash
curl -sfL https://raw.githubusercontent.com/mik/llm-server/main/install.sh | bash
```

Or manually:

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

# Custom port
llm-server --port 8082 model.gguf

# Custom context size
llm-server --ctx-size 32768 model.gguf

# Force re-tune (ignore cached config)
llm-server --retune model.gguf

# Print the command without running it
llm-server --dry-run model.gguf

# Start and run a quick benchmark
llm-server --benchmark model.gguf

# Model picker TUI
llm-server-gui
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMA_SERVER` | auto-detect | Path to `llama-server` binary |
| `LLM_MODEL_DIR` | `~/ai_models` | Default model directory |
| `LLM_PORT` | `8081` | Server port |
| `LLM_CTX_SIZE` | `65536` | Context size |

## How It Works

### Strategy Selection

The script evaluates your hardware and model, then picks the best strategy:

```
┌─ Model fits on single GPU?
│  └─ Yes → single_gpu (all layers on fastest GPU)
│
├─ Dense model fits across all GPUs?
│  └─ Yes → multi_gpu_dense (row split for parallel matmuls)
│
├─ MoE model?
│  └─ Yes → moe_offload (experts on GPU by bandwidth priority, rest on CPU)
│
├─ Dense model too big for GPU?
│  └─ Yes → dense_cpu_offload (layer split with CPU spill)
│
└─ No GPUs?
   └─ cpu_only
```

### MoE Auto-Tuning

For large MoE models (like Qwen3.5-397B) that don't fit entirely in VRAM:

1. **Conservative start** — places experts on GPUs using safe VRAM budgets
2. **Measure** — checks actual VRAM usage after loading
3. **Optimize** — calculates how many more layers fit, adds them (fastest GPU first)
4. **Fallback** — if optimized config OOMs, backs off by 1 layer and retries
5. **Cache** — saves the working config for instant startup next time

### GPU Priority

GPUs are sorted by `PCIe_width × PCIe_gen` (effective bandwidth). This means:
- A x16 Gen3 GPU handles more layers than a x4 Gen3 GPU
- Tensor splits are weighted by `VRAM × bandwidth` so faster GPUs do more work

### Smart Flag Selection

The script auto-configures based on your hardware:

| Flag | Logic |
|------|-------|
| KV cache type | q8_0 if VRAM/RAM allows, q4_0 otherwise |
| Batch size | 8192 with headroom, 4096 if tight, 2048 for offload |
| Thread count | Physical cores (not hyperthreads) |
| Context shift | Disabled for SSM/Mamba hybrids (crashes) |
| Flash attention | Always on |
| Prompt cache | 10% of free RAM, capped at 16GB |

## Examples

### Single GPU (RTX 3090 24GB)

```
═══ llm-server v1.0.0 ═══
GPUs: 1 detected
  GPU0: NVIDIA GeForce RTX 3090 23456MB free (PCIe x16 gen3)

Model: Qwen3.5-27B-UD-Q4_K_XL.gguf
Size: 17.2GB
Architecture: 36 layers, dense

Strategy: single_gpu
```

### Multi-GPU Heterogeneous (3090 Ti + 4070 + 3060)

```
═══ llm-server v1.0.0 ═══
GPUs: 3 detected
  GPU0: NVIDIA GeForce RTX 3090 Ti 24564MB free (PCIe x16 gen3)
  GPU2: NVIDIA GeForce RTX 4070 12024MB free (PCIe x4 gen3)
  GPU1: NVIDIA GeForce RTX 3060 12036MB free (PCIe x1 gen3)

Model: Qwen3.5-397B-A17B-UD-IQ3_XXS.gguf
Size: 140.2GB
Architecture: 128 layers, 512 experts (MoE)

Strategy: moe_offload
Expert placement (conservative):
  GPU0 (RTX 3090 Ti): 14 layers (blk 0-13)
  GPU2 (RTX 4070):    4 layers (blk 14-17)
  GPU1 (RTX 3060):    7 layers (blk 18-24)
  CPU (RAM): 103 layers (~101970MB)

Optimized placement:
  GPU0 (RTX 3090 Ti): 18 layers (blk 0-17)
  GPU2 (RTX 4070):    5 layers (blk 18-22)
  GPU1 (RTX 3060):    8 layers (blk 23-30)
  CPU (RAM): 97 layers
```

## systemd Service

Run as a system service:

```bash
sudo cp examples/systemd/llm-server.service /etc/systemd/system/llm-server@.service
# Edit ExecStart path and model
sudo systemctl enable --now llm-server@yourusername
```

## Why ik_llama.cpp?

[ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) is a fork of llama.cpp optimized for multi-GPU and MoE inference. Key advantages:

- **Expert CPU offload** (`-ot exps=CPU`) — keeps attention on GPU, offloads expert FFN weights to RAM
- **Merged QKV** (`-mqkv`) — fused attention for faster inference
- **Fused delta-net** — optimized SSM kernels
- **Full graph parallel for Qwen3.5** — better multi-GPU utilization

`llm-server` auto-detects which backend you have and works with either.

## License

MIT
