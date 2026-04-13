# llm-server Windows - Binary Setup

## Your Setup

You downloaded pre-built binaries, so your structure is:
```
D:\ai\loaders\llamacpp\
├── llama-server.exe          (main executable)
├── cublas64_12.dll          (28 DLLs total)
├── cudart64_12.dll
├── ... (other CUDA DLLs)
└── (no build/ directory needed)
```

## How the Tool Works Now

### 1. Finding llama-server.exe

The tool automatically searches these locations:
- `C:\Users\*\ik_llama.cpp\build\bin\llama-server.exe`
- `C:\Users\*\llama.cpp\build\bin\llama-server.exe`
- `C:\ai\llama.cpp\build\bin\llama-server.exe`
- `C:\ai\ik_llama.cpp\build\bin\llama-server.exe`
- **`D:\ai\loaders\llamacpp\llama-server.exe`** ← Your path!
- `D:\ai\loaders\llamacpp\build\bin\llama-server.exe`

You can also explicitly specify:
```batch
llm-server-windows.bat model.gguf --server-bin "D:\ai\loaders\llamacpp\llama-server.exe"
```

### 2. Finding DLLs

The tool now looks for DLLs **in the same directory as llama-server.exe** (your structure):

```
D:\ai\loaders\llamacpp\
├── llama-server.exe        ← Main binary
└── *.dll                   ← 28 CUDA DLLs copied here
```

If DLLs aren't found there, it also checks the parent directory (for source builds).

### 3. What It Does

1. Copies all `.dll` files from `D:\ai\loaders\llamacpp\` to a temp directory
2. Adds that temp directory to `PATH`
3. Adds `D:\ai\loaders\llamacpp\` to `PATH`
4. Runs `llama-server.exe` with your model

**No build directory needed!** ✅

## Running with Your Binary

```batch
cd D:\SCRIPTS\CLAUDE\llm-server

# Option 1: Let the tool auto-detect (it should find your path)
llm-server-windows.bat "E:\AI\01-TextModels\CODE\Qwen3-Coder-Next-APEX-I-Compact.gguf" --ai-tune

# Option 2: Explicitly specify (if auto-detection fails)
llm-server-windows.bat "E:\AI\01-TextModels\CODE\Qwen3-Coder-Next-APEX-I-Compact.gguf" ^
  --server-bin "D:\ai\loaders\llamacpp\llama-server.exe" --ai-tune
```

## Verification

To verify the tool can find everything:

```batch
python test_find_logic.py
```

Should show:
```
[FOUND] D:\ai\loaders\llamacpp\llama-server.exe
SUCCESS: Your llama-server is in the search path!
```

## Summary

| Component | Location | Auto-found? |
|-----------|----------|-------------|
| `llama-server.exe` | `D:\ai\loaders\llamacpp\` | ✅ Yes |
| DLLs | `D:\ai\loaders\llamacpp\` | ✅ Yes |
| Model | `E:\AI\01-TextModels\CODE\` | ✅ Full path or default |

No manual configuration needed! Just run the command and it will find everything. 🎉
