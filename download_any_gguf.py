#!/usr/bin/env python3
"""Universal GGUF Model Downloader
Download any GGUF model from HuggingFace with flexible options.
"""

import operator
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, list_repo_files

# ============================================================================
# IMPORTS (moved to top to comply with PEP 8)
# ============================================================================

import argparse

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def clear_screen() -> None:
    """Clear terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header() -> None:
    """Print application header."""


def get_hf_repo():
    """Get HuggingFace repository from user."""
    while True:
        repo = input("Repository: ").strip()
        if repo:
            return repo


def list_available_quantizations(repo):
    """List available quantizations with total file sizes.
    Returns list of (quant_name, total_size_bytes) tuples sorted by size.
    """
    try:
        api = HfApi()
        info = api.model_info(repo, files_metadata=True)
        gguf_files = [
            (s.rfilename, s.size or 0)
            for s in info.siblings
            if s.rfilename.endswith(".gguf") and "mmproj" not in s.rfilename.lower()
        ]

        if not gguf_files:
            return []

        import re

        # Comprehensive quantization pattern matching all GGUF formats
        quant_pattern = re.compile(
            r"(IQ[2-8]_(?:XXS|XS|NL|S|M|L)|Q[2-9]_(?:K_?(?:XL|XL_?M|L|S|M)|0|[1-9]_?[KS])|MXFP4|MXP4|BF16|F16|F32|F8|I4)",
            re.IGNORECASE,
        )

        # Map each quant to its total size (sum of split files)
        quant_sizes = {}
        for fname, size in gguf_files:
            basename = fname.split("/")[-1]
            matches = quant_pattern.findall(basename)
            for m in matches:
                if m not in quant_sizes:
                    quant_sizes[m] = 0
                quant_sizes[m] += size

        # Sort by size (smallest to largest)
        return sorted(quant_sizes.items(), key=operator.itemgetter(1))
    except Exception:
        return []


def get_model_files(repo, selected_quantization):
    """Get list of files to download based on selection."""
    try:
        import re

        files = list_repo_files(repo)

        if selected_quantization:
            # Normalize quantization name for matching
            # Remove trailing dot and underscore prefix for comparison
            norm_quant = selected_quantization.replace(".", "_").strip("_")

            # Filter by exact quantization name match
            matching = []
            for f in files:
                if not f.endswith(".gguf"):
                    continue
                basename = f.split("/")[-1]
                # Check if filename contains the exact quantization pattern
                if re.search(rf"\b{re.escape(norm_quant)}\b", basename, re.IGNORECASE):
                    matching.append(f)
        else:
            # Get all gguf files
            matching = [f for f in files if f.endswith(".gguf")]

        return matching
    except Exception:
        return []


def get_download_directory(default_path=None):
    """Get or create download directory."""
    default_dir = Path(default_path) if default_path else Path.home() / "ai_models"

    if default_path:
        # If passed from llm-server, just use it without asking
        return default_dir

    while True:
        choice = input("Use this directory? (y/n): ").strip().lower()
        if choice in {"y", ""}:
            return default_dir
        if choice == "n":
            custom_dir = input("Enter custom path: ").strip()
            if custom_dir:
                return Path(custom_dir)


def show_progress(progress_bytes, total_bytes, filename) -> None:
    """Display download progress bar."""
    if total_bytes == 0:
        return
    (progress_bytes / total_bytes) * 100
    bar_length = 40
    filled = int(bar_length * progress_bytes / total_bytes)
    "█" * filled + "░" * (bar_length - filled)
    progress_bytes / (1024 * 1024)


def download_files(repo, files_to_download, output_dir):
    """Download model files with progress tracking."""
    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded = []
        failed = []

        for filename in files_to_download:
            try:
                from huggingface_hub import hf_hub_download

                filepath = hf_hub_download(
                    repo_id=repo,
                    filename=filename,
                    local_dir=output_dir,
                    resume_download=True,
                    local_dir_use_symlinks=False,
                    library_name="gguf-downloader",
                )

                Path(filepath).stat().st_size / (1024**3)
                downloaded.append((filename, filepath))
            except Exception:
                failed.append(filename)

        return downloaded, failed

    except Exception:
        return [], []


def list_files_in_directory(directory, extension=".gguf"):
    """List all files with given extension in directory."""
    return sorted(directory.glob(f"*{extension}"))


def print_usage_instructions(repo, output_dir) -> None:
    """Print how to use the downloaded model."""
    # Get the model files
    gguf_files = list_files_in_directory(output_dir, ".gguf")

    if not gguf_files:
        return

    for f in gguf_files:
        f.stat().st_size / (1024**3)

    # Check for mmproj files
    mmproj_files = list(output_dir.glob("mmproj*"))

    if mmproj_files:
        for f in mmproj_files:
            f.stat().st_size / (1024**2)


def print_quick_examples() -> None:
    """Print example repositories."""
    examples = [
        ("Qwen3.5-35B-A3B", "unsloth/Qwen3.5-35B-A3B-GGUF"),
        ("Qwen3.5-122B-A10B", "unsloth/Qwen3.5-122B-A10B-GGUF"),
        ("Llama 3.3 70B", "bartowski/Llama-3.3-70B-Instruct-GGUF"),
        ("Llama 3.2 3B", "bartowski/Llama-3.2-3B-Instruct-GGUF"),
        ("Mistral 7B", "bartowski/Mistral-7B-Instruct-v0.3-GGUF"),
        ("Phi-4", "bartowski/Phi-4-GGUF"),
        ("Gemma 2.5 9B", "MaziyarPanahi/gemma-2.5-9b-it-GGUF"),
    ]

    for _name, _repo in examples:
        pass


def get_args():
    parser = argparse.ArgumentParser(description="Universal GGUF Downloader")
    parser.add_argument("--repo", type=str, help="HuggingFace repository")
    parser.add_argument("--dir", type=str, help="Download directory")
    parser.add_argument("--vram", type=int, default=0, help="Available VRAM in MB")
    parser.add_argument("--ram", type=int, default=0, help="Available RAM in MB")
    return parser.parse_args()


def recommend_quant(quant_list, vram_mb, ram_mb):
    """Recommend the best quantization based on actual file sizes and hardware.
    quant_list: list of (quant_name, size_bytes) sorted by size ascending.
    Returns (quant_name, reason) or (None, None) if nothing fits.
    """
    total_mb = vram_mb + ram_mb
    # Reserve overhead for KV cache, compute buffers, OS (~30% of model size or 2GB min)
    overhead_mb = 2048

    # Pick the largest quant that fits in total memory (VRAM + RAM)
    # Iterate from largest to smallest to find the best quality that fits
    best = None
    for quant_name, size_bytes in reversed(quant_list):
        size_mb = size_bytes / (1024 * 1024)
        if size_mb + overhead_mb <= total_mb:
            fits_vram = size_mb + overhead_mb <= vram_mb
            if fits_vram:
                reason = f"Fits entirely in VRAM ({size_mb / 1024:.1f}GB model, {vram_mb / 1024:.1f}GB available)"
            else:
                reason = f"Fits in VRAM+RAM ({size_mb / 1024:.1f}GB model, {total_mb / 1024:.1f}GB available)"
            best = (quant_name, reason)
            break

    if not best:
        # Nothing fits — recommend smallest
        quant_name, size_bytes = quant_list[0]
        size_mb = size_bytes / (1024 * 1024)
        best = (
            quant_name,
            f"Smallest available ({size_mb / 1024:.1f}GB) — may not fit, consider a smaller model",
        )

    return best


def select_quantization(repo, vram_mb=0, ram_mb=0):
    """Let user select quantization."""
    try:
        files = list_repo_files(repo)
        has_safetensors = any(f.endswith(".safetensors") for f in files)
        has_ggufs = any(f.endswith(".gguf") for f in files)

        if has_safetensors and not has_ggufs:
            return None
    except Exception:
        pass

    quant_list = list_available_quantizations(repo)

    if not quant_list:
        return None

    # Get Recommendation based on actual file sizes
    rec_q = ""
    if vram_mb > 0:
        rec_q, _rec_reason = recommend_quant(quant_list, vram_mb, ram_mb)

    for _q, size_bytes in quant_list:
        size_bytes / (1024**3)

    while True:
        choice = input("Select number (or Enter for default): ").strip()

        if not choice:
            return rec_q or None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(quant_list):
                return quant_list[idx][0]
        except ValueError:
            pass


def main() -> None:
    args = get_args()
    try:
        clear_screen()
        print_header()

        # Get repository
        repo = args.repo or get_hf_repo()

        # Select files to download
        selected_quantization = select_quantization(repo, args.vram, args.ram)
        files_to_download = get_model_files(repo, selected_quantization)

        if not files_to_download:
            return

        for _f in files_to_download[:5]:  # Show first 5
            pass
        len(files_to_download) > 5

        # Get download directory
        output_dir = get_download_directory(args.dir)
        # Save directly to output_dir without subfolders

        # Confirm

        confirm = input("\nStart download? (y/n): ").strip().lower()
        if confirm != "y":
            return

        # Download
        downloaded, _failed = download_files(repo, files_to_download, output_dir)

        if downloaded:
            print_usage_instructions(repo, output_dir)

    except KeyboardInterrupt:
        sys.exit(1)
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
