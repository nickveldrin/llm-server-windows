#!/usr/bin/env python3
"""llm-server Windows Native Port - Complete Implementation
AI-driven auto-tuning, process management, and performance optimization for Windows.
"""

import os
import subprocess
import sys
import tempfile

if os.name == "nt":
    pass
import contextlib
import hashlib
import json
import re
import shutil
import struct
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import requests
import wmi

# ============================================================================
# CONFIGURATION
# ============================================================================

VERSION = "2.0.0"
PORT = int(os.environ.get("LLM_PORT", "8081"))
HOST = "0.0.0.0"
CTX_SIZE = int(os.environ.get("LLM_CTX_SIZE", "65536"))

# Tuning constants
MAX_RESTARTS = 5
SYSTEM_HEADROOM_MB = 5120
COMPUTE_PER_GPU_MB = 512
MIN_CRAM_MB = 512
VRAM_OVERHEAD_PERCENT = 130
SINGLE_GPU_HEADROOM_MB = 4096
MAX_TUNE_ROUNDS = 8
AI_TUNE_MAX_CRASHES = 4

# Paths
CONFIG_DIR = Path.home() / ".config" / "llm-server"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"

MODEL_DIR = Path(os.environ.get("LLM_MODEL_DIR", Path.home() / "ai_models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = Path.home() / ".cache" / "llm-server"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SERVER_LOG = Path(tempfile.gettempdir()) / "llm-server.log"

# AI Tune cache
TUNE_HISTORY_FILE = CACHE_DIR / "tune_history.jsonl"

# Runtime state
RUNNING_PID = None
LIB_HUB_DIR = None
HEALTH_TIMEOUT = 240

# ============================================================================
# UTILITIES
# ============================================================================


def log(msg: str, level: str = "INFO", verbose: bool = False) -> None:
    """Print message with optional verbosity."""
    if verbose or level != "DEBUG":
        datetime.now().strftime("%H:%M:%S")


def cleanup_lib_hub() -> None:
    """Cleanup - no-op, Windows handles DLL cleanup automatically."""


def setup_lib_hub(bin_path: Path) -> str | None:
    """Add binary directory to PATH for Windows DLLs.

    Windows automatically finds DLLs in the same directory as the executable,
    so we just need to ensure the binary's directory is in PATH.
    """
    global LIB_HUB_DIR

    bin_dir = bin_path.parent

    # Clean up old hub
    if LIB_HUB_DIR and Path(LIB_HUB_DIR).exists():
        with contextlib.suppress(BaseException):
            shutil.rmtree(LIB_HUB_DIR)

    # Add binary directory to PATH (Windows finds DLLs here automatically)
    current_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir!s};{current_path}"

    return str(bin_dir)


# ============================================================================
# HARDWARE DETECTION
# ============================================================================


def get_gpus() -> list[dict[str, Any]]:
    """Detect GPUs on Windows."""
    gpus = []

    # Try WMI first
    try:
        c = wmi.WMI()
        for idx, gpu in enumerate(c.Win32_VideoController()):
            vram_total = gpu.AdapterRAM // (1024 * 1024) if gpu.AdapterRAM else 0

            gpus.append(
                {
                    "index": idx,
                    "name": gpu.Name or "Unknown GPU",
                    "vram_total": vram_total,
                    "vram_free": vram_total,
                    "pcie_width": 16,
                    "pcie_gen": 3,
                    "bandwidth": 16 * 3,
                },
            )
    except Exception as e:
        log(f"WMI detection failed: {e}", level="DEBUG")

    # Try nvidia-smi for more accurate info
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "," in line:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        idx = int(parts[0])
                        for gpu in gpus:
                            if gpu["index"] == idx:
                                gpu["vram_total"] = int(parts[1])
                                if len(parts) > 2:
                                    gpu["vram_free"] = int(parts[2])
                                break
    except Exception:
        pass

    # Filter GPUs with sufficient VRAM
    return [g for g in gpus if g["vram_free"] >= 500]


def get_memory() -> tuple[int, int]:
    """Get RAM info in MB."""
    try:
        mem = psutil.virtual_memory()
        return int(mem.available / (1024 * 1024)), int(mem.total / (1024 * 1024))
    except Exception:
        return 8192, 8192


def get_cpu_cores() -> int:
    """Get physical CPU core count."""
    try:
        return psutil.cpu_count(logical=False) or 4
    except Exception:
        return 4


# ============================================================================
# MODEL HANDLING
# ============================================================================


def get_model_info(model_path: Path) -> tuple[int, int, dict[str, Any]]:
    """Get model info: (layers, experts, metadata)."""
    layers = 0
    experts = 0
    metadata = {"fused": 0, "ssm": 0, "arch": "unknown"}

    try:
        with open(model_path, "rb") as f:
            magic = f.read(4)
            if magic != b"GGUF":
                return 0, 0, metadata

            f.read(4)  # version
            int.from_bytes(f.read(8), "little")
            kv_count = int.from_bytes(f.read(8), "little")

            for _ in range(kv_count):
                kl = int.from_bytes(f.read(8), "little")
                key = f.read(kl).decode("utf-8", errors="replace")
                vt = int.from_bytes(f.read(4), "little")

                if vt == 4:  # U32
                    val = int.from_bytes(f.read(4), "little")
                    if key.endswith(".block_count"):
                        layers = val
                    elif "expert_count" in key and "used" not in key:
                        experts = val
                    elif "ssm.state_size" in key:
                        metadata["ssm"] = 1
                elif vt == 8:  # String
                    sl = int.from_bytes(f.read(8), "little")
                    val = f.read(sl).decode("utf-8", errors="replace")
                    if key.endswith(".architecture"):
                        metadata["arch"] = val

    except Exception as e:
        log(f"Failed to read GGUF: {e}", level="DEBUG")

    if layers == 0:
        layers = 48

    return layers, experts, metadata


def get_model_size(model_path: Path) -> float:
    """Get model size in MB."""
    total_size = 0
    model_name = model_path.name

    split_match = re.search(r"-(\d+)-of-(\d+)\.gguf$", model_name)
    if split_match:
        total_shards = int(split_match.group(2))
        base = str(model_path)[: split_match.start()] + ".gguf"
        for i in range(1, total_shards + 1):
            shard = f"{base[:-5]}-{i:05d}-of-{total_shards:05d}.gguf"
            if os.path.exists(shard):
                total_size += os.path.getsize(shard)
    else:
        total_size = os.path.getsize(model_path)

    return total_size / (1024 * 1024)


def read_mmproj_name(mmproj_path: Path) -> str:
    """Read the 'general.name' field from mmproj GGUF file.

    This function reads the GGUF metadata to extract the architecture name,
    similar to how the Linux bash script does it with the 'name' key.

    Returns empty string if the field is not found or if there's an error.
    """
    try:
        with open(mmproj_path, "rb") as f:
            if f.read(4) != b"GGUF":
                return ""
            f.read(4)  # version
            struct.unpack("<Q", f.read(8))  # tensor count
            kvc = struct.unpack("<Q", f.read(8))[0]  # kv count

            # KV_FIXED: type_code -> fixed_size_in_bytes (for non-string/non-array types)
            KV_FIXED = {
                0: 1,
                1: 1,
                2: 2,
                3: 2,
                4: 4,
                5: 4,
                6: 8,
                7: 1,
                8: 8,
                9: 8,
                10: 8,
                11: 8,
                12: 8,
            }

            for _ in range(kvc):
                kl_data = f.read(8)
                if len(kl_data) < 8:
                    break
                kl = struct.unpack("<Q", kl_data)[0]

                key_data = f.read(kl)
                if len(key_data) < kl:
                    break
                key = key_data.decode("utf-8", "replace")

                vt_data = f.read(4)
                if len(vt_data) < 4:
                    break
                vt = struct.unpack("<I", vt_data)[0]

                if vt == 8:  # STRING
                    sl_data = f.read(8)
                    if len(sl_data) < 8:
                        break
                    sl = struct.unpack("<Q", sl_data)[0]
                    val_data = f.read(sl)
                    if len(val_data) < sl:
                        break
                    val = val_data.decode("utf-8", "replace")
                    if key == "general.name":
                        return val
                elif vt == 9:  # ARRAY
                    at_data = f.read(4)
                    if len(at_data) < 4:
                        break
                    at = struct.unpack("<I", at_data)[0]
                    al_data = f.read(8)
                    if len(al_data) < 8:
                        break
                    al = struct.unpack("<Q", al_data)[0]
                    if at in KV_FIXED:
                        f.read(al * KV_FIXED[at])
                    elif at == 8:
                        for _ in range(al):
                            sl_data = f.read(8)
                            if len(sl_data) < 8:
                                break
                            sl = struct.unpack("<Q", sl_data)[0]
                            f.read(sl)
                    else:
                        break
                elif vt in KV_FIXED:
                    f.read(KV_FIXED[vt])
                else:
                    break
    except Exception:
        pass
    return ""


def find_local_mmproj(model_dir: Path, model_name: str = "") -> Path | None:
    """Find local mmproj file, optionally matching model name."""
    # Pattern-based search
    for pattern in ["mmproj-F16.gguf", "mmproj-BF16.gguf", "mmproj-F32.gguf"]:
        for f in model_dir.glob(pattern):
            if f.exists():
                return f

    # Get list of mmproj files
    mmproj_files = list(model_dir.glob("*mmproj*.gguf"))

    if not mmproj_files:
        return None

    # If model_name provided, try to find exact match first
    if model_name:
        # Try to find mmproj with model name in it
        for f in mmproj_files:
            if model_name.lower().replace(".gguf", "") in f.name.lower():
                return f

    # Fall back to first mmproj found
    return mmproj_files[0] if mmproj_files else None


def validate_mmproj(mmproj_path: Path, model_name: str) -> bool:
    """Validate that mmproj matches model architecture.

    Uses bidirectional loose matching between:
    - The model's base name (extracted from model filename)
    - The mmproj's filename and GGUF metadata name
    """
    if not mmproj_path.exists():
        return False

    # Extract base model name (remove .gguf suffix and quantization suffixes)
    base_model = model_name.lower().replace(".gguf", "")
    for suffix in [
        "-q4_k_m",
        "-q4_k_xl",
        "-q5_k_xl",
        "-q6_k",
        "-q8_0",
        "-f16",
        "-f32",
        "-bf16",
    ]:
        base_model = base_model.replace(suffix, "")

    mmproj_filename = mmproj_path.name.lower()

    # Bidirectional loose matching after removing separators and common suffixes
    base_clean = base_model.replace("-", "").replace("_", "")

    # Try GGUF metadata name first if available
    mmproj_name = read_mmproj_name(mmproj_path)
    if mmproj_name:
        mmproj_name_clean = mmproj_name.replace("-", "").replace("_", "")
        if base_clean in mmproj_name_clean or mmproj_name_clean in base_clean:
            return True

    # Fall back to filename matching
    mmproj_clean = (
        mmproj_filename.replace("-", "")
        .replace("_", "")
        .replace("mmproj", "")
        .replace("f16", "")
        .replace("bf16", "")
        .replace("f32", "")
    )
    return bool(base_clean in mmproj_clean or mmproj_clean in base_clean)


# ============================================================================
# SERVER MANAGEMENT
# ============================================================================


def find_server_binary(backend: str = "") -> Path | None:
    """Find llama-server binary."""
    candidates = []

    if backend == "ik_llama":
        candidates.append(
            Path.home() / "ik_llama.cpp" / "build" / "bin" / "llama-server.exe",
        )
    elif backend == "llama":
        candidates.append(
            Path.home() / "llama.cpp" / "build" / "bin" / "llama-server.exe",
        )
    else:
        candidates.append(
            Path.home() / "ik_llama.cpp" / "build" / "bin" / "llama-server.exe",
        )
        candidates.append(
            Path.home() / "llama.cpp" / "build" / "bin" / "llama-server.exe",
        )

    # Add Windows-style paths (most common locations) - ordered by priority
    win_paths = [
        Path(
            r"C:\Users\%USERNAME%\ik_llama.cpp\build\bin\llama-server.exe"
        ).expandvars(),
        Path(r"C:\Users\%USERNAME%\llama.cpp\build\bin\llama-server.exe").expandvars(),
        Path(r"C:\ai\llama.cpp\build\bin\llama-server.exe"),
        Path(r"C:\ai\ik_llama.cpp\build\bin\llama-server.exe"),
        # User's specific path
        Path(r"D:\ai\loaders\llamacpp\llama-server.exe"),
        Path(r"D:\ai\loaders\llamacpp\build\bin\llama-server.exe"),
    ]
    candidates.extend(win_paths)

    for candidate in candidates:
        if candidate and candidate.exists() and candidate.is_file():
            log(f"Found server binary: {candidate}", level="DEBUG")
            return candidate

    return None


def check_server_health(url: str) -> bool:
    """Check if server is healthy."""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def kill_server(port: int) -> None:
    """Kill any server on the given port."""
    global RUNNING_PID

    if RUNNING_PID:
        try:
            proc = psutil.Process(RUNNING_PID)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                proc.kill()
        except Exception:
            try:
                if RUNNING_PID:
                    subprocess.run(
                        ["taskkill", "/PID", str(RUNNING_PID), "/F"],
                        capture_output=True,
                        timeout=5,
                    )
            except Exception:
                pass

    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().split("\n"):
            if f":{PORT}" in line and "LISTENING" in line:
                parts = [p for p in line.split(" ") if p]
                if len(parts) >= 5:
                    pid = parts[-1].strip()
                    with contextlib.suppress(BaseException):
                        subprocess.run(
                            ["taskkill", "/PID", pid, "/F"],
                            capture_output=True,
                            timeout=5,
                        )
    except Exception:
        pass

    RUNNING_PID = None


def start_server(
    server_bin: Path,
    model_path: Path,
    flags: list[str],
    verbose: bool = False,
) -> tuple[bool, int | None]:
    """Start the server process. Returns (success, pid)."""
    global RUNNING_PID

    cmd = [str(server_bin), *flags]

    log(f"Starting: {' '.join(cmd)}", level="DEBUG", verbose=verbose)

    try:
        # Open log file
        log_file = open(SERVER_LOG, "a")

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                if os.name == "nt"
                else 0
            ),
        )

        RUNNING_PID = process.pid
        log(f"Server started with PID {RUNNING_PID}", level="INFO", verbose=verbose)

        # Wait for health check
        start_time = time.time()
        while time.time() - start_time < HEALTH_TIMEOUT:
            if process.poll() is not None:
                log("Server exited during startup", level="ERROR", verbose=verbose)
                return False, None

            if check_server_health(f"http://127.0.0.1:{PORT}"):
                log("Server is healthy", level="INFO", verbose=verbose)
                return True, process.pid

            time.sleep(1)

        log("Server health check timeout", level="ERROR", verbose=verbose)
        return False, None

    except Exception as e:
        log(f"Failed to start server: {e}", level="ERROR", verbose=verbose)
        if RUNNING_PID:
            kill_server(PORT)
        return False, None


# ============================================================================
# BENCHMARKING
# ============================================================================


def run_benchmark(url: str, port: int) -> tuple[float, float]:
    """Run a quick benchmark and return (gen_tps, pp_tps)."""
    prompt = "Explain the theory of relativity in simple terms. Cover special and general relativity, time dilation, and gravitational effects."

    try:
        response = requests.post(
            f"{url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "test",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=60,
        )

        if response.status_code != 200:
            return 0.0, 0.0

        response.json()

        # Try to get timings from /slots
        try:
            slots_response = requests.get(f"{url}/slots", timeout=5)
            if slots_response.status_code == 200:
                slots_data = slots_response.json()
                if slots_data:
                    slot = slots_data[0] if isinstance(slots_data, list) else slots_data
                    t_pp = slot.get("t_prompt_processing", 0)
                    n_pp = slot.get("n_prompt_tokens_processed", 1)
                    t_gen = slot.get("t_token_generation", 0)
                    n_gen = slot.get("n_decoded", 1)

                    pp_tps = (n_pp / (t_pp / 1000)) if t_pp > 0 else 0
                    gen_tps = (n_gen / (t_gen / 1000)) if t_gen > 0 else 0

                    return gen_tps, pp_tps
        except Exception:
            pass

        return 0.0, 0.0

    except Exception as e:
        log(f"Benchmark failed: {e}", level="DEBUG")
        return 0.0, 0.0


# ============================================================================
# AI TUNE - Core Implementation
# ============================================================================


def build_hw_profile(gpus: list[dict], ram_mb: int, cpu_cores: int) -> str:
    """Build hardware profile JSON."""
    gpu_json = "["
    for i, gpu in enumerate(gpus):
        if i > 0:
            gpu_json += ","
        gpu_json += json.dumps(
            {
                "index": gpu["index"],
                "name": gpu["name"],
                "vram_free_mb": gpu["vram_free"],
                "vram_total_mb": gpu["vram_total"],
                "pcie_width": gpu["pcie_width"],
                "pcie_gen": gpu["pcie_gen"],
            },
        )
    gpu_json += "]"

    return json.dumps(
        {
            "gpu_count": len(gpus),
            "gpus": json.loads(gpu_json),
            "ram_available_mb": ram_mb,
            "physical_cores": cpu_cores,
        },
    )


def build_model_profile(
    model_name: str,
    model_arch: str,
    layers: int,
    experts: int,
    model_size_mb: float,
    is_moe: bool,
    has_fused: bool,
    total_vram_mb: int,
    total_ram_mb: int,
) -> str:
    """Build model profile JSON."""
    return json.dumps(
        {
            "name": model_name,
            "architecture": model_arch,
            "layers": layers,
            "experts": experts,
            "size_mb": model_size_mb,
            "kv_heads": layers,  # Approximation
            "is_moe": is_moe,
            "has_fused": has_fused,
            "total_vram_mb": total_vram_mb,
            "total_ram_mb": total_ram_mb,
            "strategy": "unknown",
        },
    )


def query_llm_chat(url: str, system_prompt: str, messages: list[dict]) -> str:
    """Query the LLM for config suggestions."""
    try:
        response = requests.post(
            f"{url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "messages": [system_prompt, *messages],
                "max_tokens": 16384,
                "temperature": 0.3,
            },
            timeout=600,
        )

        if response.status_code == 200:
            data = response.json()
            return (
                data.get("choices", [{}])[0].get("message", {}).get("content", "ERROR")
            )

        return "ERROR"

    except Exception as e:
        log(f"LLM query failed: {e}", level="DEBUG")
        return "ERROR"


def parse_tune_overrides(response_text: str) -> dict[str, Any]:
    """Parse JSON configuration from LLM response."""
    try:
        # Try to find JSON object in response
        json_match = re.search(
            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",
            response_text,
            re.DOTALL,
        )
        if json_match:
            obj = json.loads(json_match.group())
            if "flags" in obj:
                return obj["flags"]
    except Exception:
        pass

    return {}


def load_tune_history(hw_hash: str) -> str:
    """Load previous tuning history."""
    if not TUNE_HISTORY_FILE.exists():
        return "(No previous tuning data)"

    try:
        history = []
        with open(TUNE_HISTORY_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("hw_hash") == hw_hash:
                        history.append(entry)
                except Exception:
                    continue

        if not history:
            return "(No previous tuning data)"

        # Group by model
        by_model = {}
        for e in history:
            model = e.get("model", "?")
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(e)

        lines = []
        for model, entries in by_model.items():
            ok_entries = [
                e
                for e in entries
                if e.get("status") == "ok" and e.get("gen_tps", 0) > 0
            ]
            if ok_entries:
                best = max(ok_entries, key=lambda e: e.get("gen_tps", 0))
                lines.append(
                    f"  {model}: best={best['gen_tps']} tok/s ({best.get('name', '?')})",
                )

        return "\n".join(lines[:20]) if lines else "(No previous tuning data)"

    except Exception as e:
        log(f"Failed to load tune history: {e}", level="DEBUG")
        return "(No previous tuning data)"


def append_tune_history(
    model_name: str,
    hw_hash: str,
    round_num: int,
    gen_tps: float,
    pp_tps: float,
    status: str,
    flags: dict,
    config_name: str,
) -> None:
    """Append tuning result to history."""
    try:
        TUNE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "model": model_name,
            "hw_hash": hw_hash,
            "round": round_num,
            "name": config_name,
            "gen_tps": gen_tps,
            "pp_tps": pp_tps,
            "status": status,
            "flags": flags,
        }

        with open(TUNE_HISTORY_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception as e:
        log(f"Failed to append tune history: {e}", level="DEBUG")


def ai_tune(
    model_path: Path,
    server_bin: Path,
    gpus: list[dict],
    cpu_cores: int,
    ram_mb: int,
    verbose: bool = False,
) -> dict | None:
    """AI-driven flag optimization
    The model tunes itself by benchmarking different configurations.
    """
    global RUNNING_PID
    log("═══ AI Tune — iterative LLM-driven optimization ═══", verbose=verbose)

    # VRAM pre-flight check for AI-tuning
    vram_ok = True
    for gpu in gpus:
        if gpu["vram_free"] < 1000:
            log(
                f"  VRAM warning: GPU{gpu['index']} only has {gpu['vram_free']}MB free",
                verbose=verbose,
                level="WARNING",
            )
            vram_ok = False

    if not vram_ok:
        log(
            "  WARNING: Low VRAM may cause tuning to fail or be extremely slow",
            verbose=verbose,
            level="WARNING",
        )
        log(
            "  Consider freeing up VRAM or running without --ai-tune",
            verbose=verbose,
            level="WARNING",
        )

    # Get model info
    model_name = model_path.name
    model_mb = get_model_size(model_path)
    layers, experts, metadata = get_model_info(model_path)
    is_moe = experts > 1
    total_vram = sum(g["vram_free"] for g in gpus)

    # Build hardware hash
    hw_hash = hashlib.md5(
        f"{len(gpus)}_{'_'.join(g['name'] for g in gpus)}".encode(),
    ).hexdigest()[:8]

    log(f"Hardware hash: {hw_hash}", verbose=verbose)

    # Load history
    tune_history = load_tune_history(hw_hash)

    # Start server with baseline config
    base_flags = build_flags(model_path, gpus, cpu_cores, ram_mb, verbose)

    success, pid = start_server(server_bin, model_path, base_flags, verbose)
    if not success:
        log("Baseline config failed to start", level="ERROR", verbose=verbose)
        return None

    RUNNING_PID = pid
    url = f"http://127.0.0.1:{PORT}"

    try:
        # Get baseline
        gen_tps, pp_tps = run_benchmark(url, PORT)
        if gen_tps <= 0:
            log("Could not measure baseline", level="ERROR", verbose=verbose)
            return None

        log(
            f"Baseline: gen={gen_tps:.2f} tok/s  pp={pp_tps:.2f} tok/s",
            verbose=verbose,
        )

        # Build system prompt for AI tuning
        help_text = get_server_help(server_bin, verbose)

        system_prompt = {
            "role": "system",
            "content": f"""You are an expert performance tuner for llama.cpp inference servers.

Your goal: maximize GENERATION tok/s while preserving output quality.
Speed is the primary metric.

# Context
- Hardware: {build_hw_profile(gpus, ram_mb, cpu_cores)}
- Model: {build_model_profile(model_name, metadata.get("arch", "unknown"), layers, experts, model_mb, is_moe, metadata.get("fused", 0), total_vram, ram_mb)}
- History: {tune_history}

# How this works
1. I give you the full server --help output and current config
2. You propose ONE config to optimize
3. I benchmark it and report results (or crash)
4. You learn and propose better configs
5. We do {MAX_TUNE_ROUNDS} rounds

# Optimization priority
1. Single GPU > Multi GPU (eliminates inter-GPU transfer overhead)
2. Graph split > Row split > Layer split (when multi-GPU needed)
3. Flash attention: enable it — faster and unlocks KV quantization
4. KV cache quantization: q8_0 (best quality/speed), q4_0 (VRAM-starved)
5. Batch size: 2048-4096 usually optimal
6. Quantized KV (q4_0/q8_0) REQUIRES flash-attn

# Rules
1. Only suggest flags from --help
2. Response must be JSON: {{"name": "short desc", "flags": {{flag: value}}, "reasoning": "why"}}
3. CRITICAL: Don't exceed VRAM/RAM budget

{help_text}""",
        }

        # Start tuning rounds
        best_gen = gen_tps
        best_flags = {}
        best_name = "baseline"

        for round_num in range(1, MAX_TUNE_ROUNDS + 1):
            log(
                f"\nRound {round_num}/{MAX_TUNE_ROUNDS}: Querying model...",
                verbose=verbose,
            )

            # Build context message
            user_message = {
                "role": "user",
                "content": f"""Current config: {" ".join(base_flags)}
Current benchmark: gen={gen_tps:.2f} tok/s, pp={pp_tps:.2f} tok/s

Propose your optimization config.
Respond with JSON only.""",
            }

            # Query LLM
            llm_response = query_llm_chat(url, system_prompt, [user_message])

            if llm_response == "ERROR":
                log("  LLM query failed, skipping round", verbose=verbose)
                continue

            # Parse response
            new_flags = parse_tune_overrides(llm_response)

            if not new_flags:
                log("  Could not parse config, skipping", verbose=verbose)
                continue

            config_name = new_flags.get("name", f"config_{round_num}")
            log(f"  Config: {config_name}", verbose=verbose)

            # Apply flags and benchmark
            test_flags = apply_overrides(base_flags, new_flags)

            kill_server(PORT)
            success, _test_pid = start_server(
                server_bin,
                model_path,
                test_flags,
                verbose,
            )

            if not success:
                log("  CRASHED", verbose=verbose)
                append_tune_history(
                    model_name,
                    hw_hash,
                    round_num,
                    0,
                    0,
                    "crashed",
                    new_flags,
                    config_name,
                )

                # Auto-restart baseline
                success, _ = start_server(server_bin, model_path, base_flags, verbose)
                if not success:
                    log("  Failed to restart baseline", level="ERROR", verbose=verbose)
                    break

                if round_num < MAX_TUNE_ROUNDS:
                    round_num = round_num - 1  # Don't count crashes
                continue

            # Benchmark
            test_gen, test_pp = run_benchmark(url, PORT)
            delta = test_gen - gen_tps
            improvement = (delta / gen_tps * 100) if gen_tps > 0 else 0

            log(
                f"  Result: gen={test_gen:.2f} tok/s ({improvement:+.1f}%)  pp={test_pp:.2f} tok/s",
                verbose=verbose,
            )

            # Update best
            if test_gen > best_gen:
                best_gen = test_gen
                best_flags = new_flags
                best_name = config_name
                log("  ★ NEW BEST!", verbose=verbose)

            # Record and append history
            append_tune_history(
                model_name,
                hw_hash,
                round_num,
                test_gen,
                test_pp,
                "ok",
                new_flags,
                config_name,
            )

            # Kill test config, restart baseline
            kill_server(PORT)
            success, _ = start_server(server_bin, model_path, base_flags, verbose)
            if not success:
                log("  Failed to restart baseline", level="ERROR", verbose=verbose)
                break

        log("\nAI Tune complete!", verbose=verbose)
        log(f"Winner: {best_name} (gen={best_gen:.2f} tok/s)", verbose=verbose)

        return {"name": best_name, "flags": best_flags, "gen_tps": best_gen}

    finally:
        kill_server(PORT)


def get_server_help(server_bin: Path, verbose: bool = False) -> str:
    """Get full --help output."""
    try:
        result = subprocess.run(
            [str(server_bin), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout[:50000]  # Limit size
    except Exception as e:
        log(f"Failed to get help: {e}", level="DEBUG")
        return ""


def apply_overrides(base_flags: list[str], overrides: dict) -> list[str]:
    """Apply flag overrides to base flags."""
    new_flags = base_flags.copy()

    # Remove flags that are being overridden
    to_remove = set()
    for key in overrides:
        if key.startswith("--"):
            try:
                idx = new_flags.index(key)
                to_remove.add(idx)
                to_remove.add(idx + 1)  # Also remove value
            except ValueError:
                pass

    new_flags = [f for i, f in enumerate(new_flags) if i not in to_remove]

    # Add new flags
    for key, value in overrides.items():
        if isinstance(value, bool):
            if value:
                new_flags.append(key)
        else:
            new_flags.append(key)
            new_flags.append(str(value))

    return new_flags


# ============================================================================
# FLAG BUILDING
# ============================================================================


def build_flags(
    model_path: Path,
    gpu_list: list[dict],
    cpu_cores: int,
    ram_mb: int,
    verbose: bool = False,
) -> list[str]:
    """Build server flags based on hardware."""
    flags = [
        "-m",
        str(model_path),
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--ctx-size",
        str(CTX_SIZE),
        "--flash-attn",
        "on",
        "--jinja",
        "--threads",
        str(cpu_cores),
        "--threads-batch",
        str(cpu_cores),
    ]

    model_mb = get_model_size(model_path)
    total_vram = sum(g["vram_free"] for g in gpu_list) if gpu_list else 0

    if gpu_list:
        best_gpu = max(gpu_list, key=lambda g: g["vram_free"])
        if model_mb * 1.1 < best_gpu["vram_free"]:
            flags.extend(["-b", "4096", "-ub", "512"])
        else:
            flags.extend(["-b", "2048", "-ub", "512"])

        flags.extend(["-ngl", "999"])
        flags.extend(["-mg", str(gpu_list[0]["index"])])

        if len(gpu_list) > 1:
            splits = ",".join(["1"] * len(gpu_list))
            flags.extend(["--tensor-split", splits])
    else:
        flags.extend(["-b", "1024", "-ub", "128"])

    # VRAM budget check
    model_overhead = int(model_mb * VRAM_OVERHEAD_PERCENT / 100)
    kv_budget = int(model_mb * 0.5)
    compute_budget = COMPUTE_PER_GPU_MB * max(len(gpu_list), 1)

    if total_vram > 0:
        available = total_vram - model_overhead - kv_budget - compute_budget
        if available > 0:
            cache_mb = min(available // 2, 4096)
            if cache_mb >= 256:
                flags.extend(["-cram", str(cache_mb)])

    return flags


# ============================================================================
# AUTO-UPDATE
# ============================================================================


def check_for_updates() -> bool:
    """Check for llm-server-windows updates."""
    try:
        result = requests.get(
            "https://api.github.com/repos/raketenkater/llm-server/releases/latest",
            timeout=10,
        )
        if result.status_code == 200:
            data = result.json()
            latest_version = data.get("tag_name", "v0.0.0").lstrip("v")
            current_version = VERSION

            if latest_version != current_version:
                log(
                    f"Update available: v{latest_version} (current: v{VERSION})",
                    level="INFO",
                )
                log(f"Download: {data.get('html_url', '')}", level="INFO")
                return True
    except Exception as e:
        log(f"Update check failed: {e}", level="DEBUG")

    return False


# ============================================================================
# INSTALLATION
# ============================================================================


def install_dependencies() -> bool | None:
    """Install required Python packages with uv/pip support."""
    import subprocess
    import sys

    required = ["psutil", "requests", "wmi"]
    missing = []

    # Check for missing packages
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return True

    log(f"Installing missing dependencies: {', '.join(missing)}", level="INFO")

    # Try uv first, then pip
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *missing],
            check=True,
            timeout=120,
            capture_output=True,
            text=True,
        )
        log("Dependencies installed successfully", level="INFO")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Dependency installation failed: {e.stderr}", level="ERROR")
        return False
    except Exception as e:
        log(f"Dependency installation error: {e}", level="ERROR")
        return False


def main() -> int:
    """Main entry point."""
    global RUNNING_PID

    # Check Python version

    # Install dependencies
    if not install_dependencies():
        return 1

    # Parse arguments
    model_arg = None
    backend = ""
    gpu_filter = ""
    ram_budget = 0
    verbose = False
    benchmark = False
    server_bin_path = None
    ai_tune_flag = False
    mmproj_path = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--verbose":
            verbose = True
        elif arg == "--benchmark":
            benchmark = True
        elif arg == "--ai-tune":
            ai_tune_flag = True
        elif arg == "--backend" and i + 1 < len(sys.argv):
            backend = sys.argv[i + 1]
            i += 1
        elif arg == "--server-bin" and i + 1 < len(sys.argv):
            server_bin_path = Path(sys.argv[i + 1])
        elif arg == "--gpus" and i + 1 < len(sys.argv):
            gpu_filter = sys.argv[i + 1]
        elif arg == "--ram-budget" and i + 1 < len(sys.argv):
            ram_str = sys.argv[i + 1]
            if ram_str.endswith("G"):
                ram_budget = int(ram_str[:-1]) * 1024
            elif ram_str.endswith("M"):
                ram_budget = int(ram_str[:-1])
            else:
                ram_budget = int(ram_str)
        elif arg == "--mmproj" and i + 1 < len(sys.argv):
            mmproj_path = sys.argv[i + 1]
            i += 1
        elif arg == "--vision":
            mmproj_path = "auto"
        elif not arg.startswith("-"):
            model_arg = arg
        i += 1

    if not model_arg:
        return 1

    # Find server binary
    if server_bin_path and Path(server_bin_path).exists():
        server_bin = Path(server_bin_path)
    else:
        server_bin = find_server_binary(backend)

    if not server_bin:
        return 1

    # Setup libraries
    setup_lib_hub(server_bin)

    # Cleanup on exit
    import atexit

    atexit.register(cleanup_lib_hub)

    # Check for updates
    check_for_updates()

    # Detect hardware
    cpu_cores = get_cpu_cores()

    ram_avail, _ram_total = get_memory()
    if ram_budget > 0 and ram_budget < ram_avail:
        ram_avail = ram_budget

    # Detect GPUs
    all_gpus = get_gpus()

    # Apply GPU filter
    if gpu_filter:
        allowed = [int(x.strip()) for x in gpu_filter.split(",")]
        all_gpus = [g for g in all_gpus if g["index"] in allowed]

    total_vram = sum(g["vram_free"] for g in all_gpus)

    if all_gpus:
        for gpu in all_gpus:
            pass
    else:
        pass

    # VRAM pre-flight check
    vram_ok = True
    if all_gpus:
        for gpu in all_gpus:
            if gpu["vram_free"] < 500:
                vram_ok = False
            else:
                pass

        if not vram_ok and ai_tune_flag:
            try:
                response = input("Continue with AI-tuning anyway? (yes/NO): ")
                if response.strip().lower() != "yes":
                    return 1
            except EOFError:
                return 1

    # Find model
    model_path = Path(model_arg)
    if not model_path.exists():
        if MODEL_DIR.exists():
            alt_path = MODEL_DIR / model_arg
            if alt_path.exists():
                model_path = alt_path
            else:
                return 1
        else:
            return 1

    # Get model info
    model_name = model_path.name
    model_mb = get_model_size(model_path)
    _layers, experts, metadata = get_model_info(model_path)

    if experts > 1:
        pass

    if metadata["ssm"]:
        pass

    if metadata.get("fused"):
        pass

    # Vision/mmproj handling
    mmproj_model_dir = model_path.parent
    mmproj_path_resolved = None

    if mmproj_path == "auto":
        log("Vision: auto-detecting mmproj...", level="INFO", verbose=verbose)
        local_mmproj = find_local_mmproj(mmproj_model_dir, model_name)
        if local_mmproj:
            if validate_mmproj(local_mmproj, model_name):
                mmproj_path_resolved = local_mmproj
                log(
                    f"Vision: validated local mmproj: {local_mmproj.name}",
                    level="INFO",
                    verbose=verbose,
                )
            else:
                log(
                    "Vision: local mmproj mismatch, skipping",
                    level="DEBUG",
                    verbose=verbose,
                )

    elif mmproj_path:
        mmproj_resolved = Path(mmproj_path)
        if mmproj_resolved.exists():
            mmproj_path_resolved = mmproj_resolved
        else:
            alt_path = mmproj_model_dir / mmproj_path
            if alt_path.exists():
                mmproj_path_resolved = alt_path

    if mmproj_path_resolved:
        mmproj_path_resolved = str(mmproj_path_resolved)

    # Memory check
    model_overhead = int(model_mb * VRAM_OVERHEAD_PERCENT / 100)
    kv_estimate = int(model_mb * 0.5)
    total_needed = (
        model_overhead + kv_estimate + COMPUTE_PER_GPU_MB * max(len(all_gpus), 1)
    )

    if total_needed > total_vram + ram_avail:
        pass

    # AI Tune
    if ai_tune_flag and all_gpus:
        tuned_config = ai_tune(
            model_path,
            server_bin,
            all_gpus,
            cpu_cores,
            ram_avail,
            verbose,
        )
        if tuned_config:
            return 0

    # Build flags

    flags = build_flags(model_path, all_gpus, cpu_cores, ram_avail, verbose)

    if mmproj_path_resolved:
        flags.extend(["--mmproj", mmproj_path_resolved])

    if all_gpus:
        pass

    # Show command

    # Start server

    success, _pid = start_server(server_bin, model_path, flags, verbose)

    if not success:
        return 1

    if benchmark:
        time.sleep(5)
        try:
            result = requests.post(
                f"http://127.0.0.1:{PORT}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "test",
                    "messages": [{"role": "user", "content": "Hello!"}],
                    "max_tokens": 100,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            if result.status_code == 200:
                data = result.json()
                data.get("usage", {}).get("completion_tokens", 0)
        except Exception:
            pass

        kill_server(PORT)
        return 0

    # Keep running

    try:
        while RUNNING_PID:
            try:
                proc = psutil.Process(RUNNING_PID)
                if not proc.is_running():
                    break
            except Exception:
                break
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        kill_server(PORT)

    return 0


if __name__ == "__main__":
    sys.exit(main())
