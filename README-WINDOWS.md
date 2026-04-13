# llm-server Windows Native Port

This is a Windows-native port of `llm-server` that runs without WSL2.

## Status

**Windows Native Port - Complete! ✅**

All AI-tuning features have been ported from the Linux bash version. This is a fully functional Windows-native implementation.

## What Works

- ✅ GPU detection (NVIDIA via WMI/nvidia-smi)
- ✅ CPU core detection
- ✅ Memory detection
- ✅ Server binary auto-detection (including pre-built binaries)
- ✅ Full flag building with VRAM optimization
- ✅ Model info parsing (GGUF metadata)
- ✅ Memory budget checking
- ✅ Server start/stop with process management
- ✅ VRAM pre-flight checks with user confirmation (for AI-tuning)
- ✅ Full AI-tune implementation (iterative LLM-driven optimization)
- ✅ Benchmark mode with tok/s measurement
- ✅ Auto-update checking
- ✅ Crash recovery in AI-tuning
- ✅ Windows-specific process management (taskkill)
- ✅ Logging to temp file
- ✅ Vision/MMproj support for multimodal models

## Still To Do

- ⏳ Auto-download from HuggingFace
- ⏳ Vision/mmproj support
- ⏳ GUI launcher
- ⏳ OpenCode integration

**Note:** Multi-GPU tensor split, MoE expert placement, and crash recovery are fully implemented.

## Requirements

- Windows 10 or 11
- Python 3.8 or later
- NVIDIA GPU (for GPU acceleration)
- `nvidia-smi` in PATH (usually comes with NVIDIA drivers)
- Either `ik_llama.cpp` or `llama.cpp` built with Windows support

## Installation

1. Install Python 3.8+ (if not already installed):
   - Download from https://www.python.org/
   - Make sure to check "Add Python to PATH" during installation

2. Install required packages:
```bash
pip install psutil requests wmi
```

3. Get the Windows port:
    - Download `llm-server-windows.py` from the repository
    - Or clone: `git clone https://github.com/nickveldrin/llm-server-windows.git`

4. Install `ik_llama.cpp` or `llama.cpp` with Windows support:
   - Follow Windows build instructions at:
     - https://github.com/ikawrakow/ik_llama.cpp
     - https://github.com/ggml-org/llama.cpp

## Usage

```bash
# Basic usage
llm-server-windows.bat model.gguf

# With VRAM check and AI-tuning
llm-server-windows.bat model.gguf --ai-tune --verbose

# Use pre-built binary (no build needed)
llm-server-windows.bat model.gguf --server-bin D:\ai\loaders\llamacpp\llama-server.exe

# Benchmark mode
llm-server-windows.bat model.gguf --benchmark

# Use specific GPUs
llm-server-windows.bat model.gguf --gpus 0,1 --ram-budget 32G
```

## Differences from Linux Version

### File Paths
- Linux: `/tmp/`, `/proc/`, `/home/`
- Windows: `C:\Users\%USER%\AppData\Local\Temp\`, Windows Registry

### Library Detection
- Linux: `.so` files with versioned symlinks
- Windows: `.dll` files with different versioning

### Process Management
- Linux: `/proc/$pid/oom_score_adj`, `kill -9`
- Windows: `taskkill /F /PID`, no OOM score adjustment

### GPU Detection
- Linux: `nvidia-smi`, `lscpu`, `/proc/meminfo`
- Windows: WMI (`Win32_VideoController`), `nvidia-smi`, `psutil`

### Temp Files
- Linux: `/tmp/llm-lib-hub.XXXXXX`
- Windows: `%TEMP%\llm-lib-hub-xxxxxx`

## Supported Backends

### ik_llama.cpp
- Recommended for multi-GPU
- Requires CUDA 11.8+ and compatible GPU
- Better performance on most configurations

### llama.cpp (mainline)
- More stable for single GPU
- Better for unsupported architectures

## Troubleshooting

### "nvidia-smi not found"
- Install NVIDIA drivers from https://www.nvidia.com/Download/index.aspx
- Verify: Open Command Prompt, type `nvidia-smi`

### "Python not found"
- Install Python 3.8+ from https://www.python.org/
- Check: `python --version`

### "Model not found"
- Ensure model is in current directory or `~/ai_models/`
- Use full path: `llm-server-windows.bat C:\models\model.gguf`

### "Server exited immediately"
- Check `llm-server.log` in temp directory
- Verify server binary works: `llama-server.exe --help`
- Check GPU drivers are up to date
- Ensure all DLLs are in the same directory as `llama-server.exe` (Windows finds them automatically)

### "Out of VRAM"
- Use smaller quantization (Q4_K_M instead of F16)
- Reduce context size: `--ctx-size 4096`
- Use fewer GPUs: `--gpus 0`
- Reduce RAM budget: `--ram-budget 16G`

## Building from Source

The Windows port is written in Python and uses:
- `psutil` - System information (CPU, RAM, processes)
- `requests` - HTTP requests for server health
- `wmi` - Windows Management Instrumentation (GPU info)

Install dependencies:
```bash
pip install psutil requests wmi
```

Run directly:
```bash
python llm-server-windows.py model.gguf
```

## Contributing

The Windows port is fully functional but contributions welcome! Areas needing work:

1. **Auto-download from HuggingFace**: Automate model downloads
2. **GUI launcher**: Windows GUI for easy model management
3. **Performance profiling**: Windows-specific optimizations
4. **Testing**: More real-world testing on different Windows configurations

## Vision/MMproj Support

The Windows port now supports multimodal (vision) models:

```bash
# Auto-detect and use mmproj file for vision models
llm-server-windows.bat Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf --vision

# Or specify mmproj file directly
llm-server-windows.bat Qwen3.5-35B-A3B-UD-Q4_K_XL.gguf --mmproj mmproj-F16.gguf
```

The tool:
- Auto-detects mmproj files matching your model name (expects naming like `Qwen3.5-35B-UD-mmproj-F16.gguf` for `Qwen3.5-35B-UD-Q4_K_XL.gguf`)
- Validates mmproj matches model architecture by filename matching
- Passes `--mmproj` flag to llama-server

## Roadmap

### Phase 1 (Current) - ✅ COMPLETE
- [x] Basic server launch
- [x] GPU detection
- [x] Complete flag building
- [x] Health checks
- [x] AI-tune implementation
- [x] Multi-GPU optimization
- [x] Benchmark mode
- [x] Vision/mmproj support

### Phase 2
- [ ] Auto-download from HuggingFace
- [ ] GUI launcher
- [ ] OpenCode integration

## License

MIT - same as original llm-server

## Credits

- Original llm-server: https://github.com/raketenkater/llm-server
- Windows port: This implementation
- Backends: ik_llama.cpp, llama.cpp
