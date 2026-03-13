#!/usr/bin/env python3
"""
Universal GGUF Model Downloader
Download any GGUF model from HuggingFace with flexible options
"""

import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files, HfApi

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def clear_screen():
    """Clear terminal screen"""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Print application header"""
    print("\n" + "=" * 70)
    print(" " * 25 + "🦥 Universal GGUF Downloader")
    print("=" * 70 + "\n")


def get_hf_repo():
    """Get HuggingFace repository from user"""
    print("\n📦 Enter HuggingFace model repository")
    print("   Format: username/model-name")
    print("   Examples:")
    print("     - unsloth/Qwen3.5-35B-A3B-GGUF")
    print("     - bartowski/Llama-3.2-3B-Instruct-GGUF")
    print("     - MaziyarPanahi/Meta-Llama-3.1-8B-Instruct-GGUF")
    print()

    while True:
        repo = input("Repository: ").strip()
        if repo:
            return repo
        print("❌ Repository cannot be empty.\n")


def list_available_quantizations(repo):
    """List available quantizations for a model"""
    try:
        files = list_repo_files(repo)
        gguf_files = [f for f in files if f.endswith(".gguf")]

        if not gguf_files:
            return []

        import re

        quantizations = set()

        # Comprehensive quantization pattern matching all GGUF formats (non-capturing groups)
        quant_pattern = re.compile(
            r"(?:IQ[2-8]_[NLXS]|Q[2-9]_(?:K_?(?:XL|XL_?M|L|S|M)|0|[1-9]_?[KS])|MXFP4|MXP4|BF16|F16|F32|F8|I4)",
            re.IGNORECASE,
        )

        for f in gguf_files:
            matches = quant_pattern.findall(f)
            # findall with non-capturing groups returns strings
            quantizations.update(matches)

        return sorted(quantizations, key=lambda x: x.upper())
    except Exception as e:
        print(f"Warning: Could not list quantizations: {e}")
        return []


def get_model_files(repo, selected_quantization):
    """Get list of files to download based on selection"""
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
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def get_download_directory(default_path=None):
    """Get or create download directory"""
    if default_path:
        default_dir = Path(default_path)
    else:
        default_dir = Path.home() / "ai_models"

    print(f"\n📁 Download directory: {default_dir}")

    if default_path:
        # If passed from llm-server, just use it without asking
        return default_dir

    while True:
        choice = input("Use this directory? (y/n): ").strip().lower()
        if choice in ["y", ""]:
            return default_dir
        elif choice == "n":
            custom_dir = input("Enter custom path: ").strip()
            if custom_dir:
                return Path(custom_dir)
        else:
            print("❌ Invalid choice.\n")


def show_progress(progress_bytes, total_bytes, filename):
    """Display download progress bar"""
    if total_bytes == 0:
        return
    percent = (progress_bytes / total_bytes) * 100
    bar_length = 40
    filled = int(bar_length * progress_bytes / total_bytes)
    bar = "█" * filled + "░" * (bar_length - filled)
    speed_mb = progress_bytes / (1024 * 1024)
    print(f"\r   [{bar}] {percent:5.1f}% | {speed_mb:8.2f} MB", end="", flush=True)


def download_files(repo, files_to_download, output_dir):
    """Download model files with progress tracking"""
    print(f"\n🚀 Downloading from: {repo}")
    print(f"   Files to download: {len(files_to_download)}")
    print(f"   Output: {output_dir}\n")

    try:
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        print("⬇️  Downloading files...")
        downloaded = []
        failed = []

        for filename in files_to_download:
            try:
                print(f"\n   Downloading: {filename}")
                from huggingface_hub import hf_hub_download
                import tqdm

                filepath = hf_hub_download(
                    repo_id=repo,
                    filename=filename,
                    local_dir=output_dir,
                    resume_download=True,
                    local_dir_use_symlinks=False,
                    library_name="gguf-downloader",
                )

                size_gb = Path(filepath).stat().st_size / (1024**3)
                print(f"   ✓ {filename} ({size_gb:.2f} GB)")
                downloaded.append((filename, filepath))
            except Exception as e:
                print(f"\n   ✗ Failed to download {filename}: {e}")
                failed.append(filename)

        print()  # New line after progress bars
        print(f"\n✅ Download complete!")
        print(f"   Successful: {len(downloaded)} file(s)")
        if failed:
            print(f"   Failed: {len(failed)} file(s)")

        return downloaded, failed

    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        return [], []


def list_files_in_directory(directory, extension=".gguf"):
    """List all files with given extension in directory"""
    return sorted(directory.glob(f"*{extension}"))


def print_usage_instructions(repo, output_dir):
    """Print how to use the downloaded model"""
    print("\n" + "=" * 70)
    print("📖 How to use this model:")
    print("=" * 70)

    # Get the model files
    gguf_files = list_files_in_directory(output_dir, ".gguf")

    if not gguf_files:
        print("\n⚠️  No GGUF files found in download directory!")
        return

    print(f"\n📁 Model directory: {output_dir}")
    print("\n📦 Available model files:")
    for f in gguf_files:
        size_gb = f.stat().st_size / (1024**3)
        print(f"   • {f.name} ({size_gb:.2f} GB)")

    # Check for mmproj files
    mmproj_files = [f for f in output_dir.glob("mmproj*")]

    if mmproj_files:
        print("\n📦 Available mmproj (vision) files:")
        for f in mmproj_files:
            size_mb = f.stat().st_size / (1024**2)
            print(f"   • {f.name} ({size_mb:.2f} MB)")

    print("\n" + "-" * 70)
    print("🔧 Using llama.cpp (server mode):")
    print("-" * 70)
    if mmproj_files:
        print("""
    # For vision models:
    ./build/bin/llama-server \\
        --model "/path/to/model.gguf" \\
        --mmproj "/path/to/mmproj.gguf" \\
        --ctx-size 16384 \\
        --port 8001
        """)
    else:
        print("""
    # For text-only models:
    ./build/bin/llama-server \\
        --model "/path/to/model.gguf" \\
        --ctx-size 16384 \\
        --port 8001
        """)

    print("\n" + "-" * 70)
    print("🐍 Using Python (OpenAI compatible):")
    print("-" * 70)
    print("""
    from openai import OpenAI
    
    client = OpenAI(
        base_url="http://127.0.0.1:8001/v1",
        api_key="sk-no-key-required",
    )
    
    response = client.chat.completions.create(
        model="qwen3.5",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    
    print(response.choices[0].message.content)
    """)

    print("\n" + "-" * 70)
    print("📋 Using llama.cpp (CLI):")
    print("-" * 70)
    if mmproj_files:
        print("""
    ./build/bin/llama-cli \\
        --model "/path/to/model.gguf" \\
        --mmproj "/path/to/mmproj.gguf" \\
        --ctx-size 16384 \\
        --temp 1.0 \\
        --top-p 0.95 \\
        --prompt "Your question here" \\
        --n-predict 512
        """)
    else:
        print("""
    ./build/bin/llama-cli \\
        --model "/path/to/model.gguf" \\
        --ctx-size 16384 \\
        --temp 1.0 \\
        --top-p 0.95 \\
        --prompt "Your prompt here" \\
        --n-predict 512
        """)


def print_quick_examples():
    """Print example repositories"""
    print("\n" + "=" * 70)
    print("📚 Example repositories to try:")
    print("=" * 70)

    examples = [
        ("Qwen3.5-35B-A3B", "unsloth/Qwen3.5-35B-A3B-GGUF"),
        ("Qwen3.5-122B-A10B", "unsloth/Qwen3.5-122B-A10B-GGUF"),
        ("Llama 3.3 70B", "bartowski/Llama-3.3-70B-Instruct-GGUF"),
        ("Llama 3.2 3B", "bartowski/Llama-3.2-3B-Instruct-GGUF"),
        ("Mistral 7B", "bartowski/Mistral-7B-Instruct-v0.3-GGUF"),
        ("Phi-4", "bartowski/Phi-4-GGUF"),
        ("Gemma 2.5 9B", "MaziyarPanahi/gemma-2.5-9b-it-GGUF"),
    ]

    for name, repo in examples:
        print(f"  • {name}: {repo}")

    print()


import argparse


def get_args():
    parser = argparse.ArgumentParser(description="Universal GGUF Downloader")
    parser.add_argument("--repo", type=str, help="HuggingFace repository")
    parser.add_argument("--dir", type=str, help="Download directory")
    parser.add_argument("--vram", type=int, default=0, help="Available VRAM in MB")
    parser.add_argument("--ram", type=int, default=0, help="Available RAM in MB")
    return parser.parse_args()


def recommend_quant(repo, vram_mb, ram_mb):
    """Recommend the best quantization based on hardware"""
    total_mb = vram_mb + ram_mb

    # Heuristic for a "typical" 27B-35B model size (most common for power users)
    # We use bits-per-weight (bpw) to estimate
    # Q8_0 (~8.5 bpw), Q4_K_M (~4.8 bpw), IQ3_XXS (~3.1 bpw)

    print(
        f"\n🖥️  Hardware detected: {vram_mb / 1024:.1f}GB VRAM | {ram_mb / 1024:.1f}GB System RAM"
    )
    print(f"   Total Memory: {total_mb / 1024:.1f}GB")

    if vram_mb > 48000:
        return "Q8_0", "High-End: Fits entirely in VRAM with maximum quality."
    elif vram_mb > 24000:
        return "Q6_K", "Performance: Fits in VRAM with near-perfect quality."
    elif total_mb > 64000:
        return "Q4_K_M", "Sweet Spot: Best balance of size/quality for offloading."
    elif total_mb > 32000:
        return "Q3_K_M", "Efficiency: Fits in memory, prioritized for stability."
    else:
        return "IQ2_XXS", "Compatibility: Minimal size to run on this hardware."


def select_quantization(repo, vram_mb=0, ram_mb=0):
    """Let user select quantization"""
    print("\n🔍 Scanning repository for available quantizations...")

    quantizations = list_available_quantizations(repo)

    if not quantizations:
        print("   No GGUF quantizations found, downloading all .gguf files")
        return None

    # Get Recommendation
    rec_q = ""
    if vram_mb > 0:
        rec_q, rec_reason = recommend_quant(repo, vram_mb, ram_mb)
        print(f"\n🌟 RECOMMENDED: {rec_q}")
        print(f"   Reason: {rec_reason}")

    print(f"\nAvailable quantizations:")
    for i, q in enumerate(quantizations, 1):
        star = " ★" if q == rec_q else ""
        print(f"  {i}) {q}{star}")

    print("\nPress Enter to use the ★ recommendation (if available) or download all")
    print()

    while True:
        choice = input("Select number (or Enter for default): ").strip()

        if not choice:
            return rec_q if rec_q else None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(quantizations):
                return quantizations[idx]
        except ValueError:
            pass

        print("❌ Invalid selection. Please try again.\n")


def main():
    args = get_args()
    try:
        clear_screen()
        print_header()

        # Get repository
        repo = args.repo if args.repo else get_hf_repo()

        # Select files to download
        selected_quantization = select_quantization(repo, args.vram, args.ram)
        files_to_download = get_model_files(repo, selected_quantization)

        if not files_to_download:
            print("\n❌ No files found to download!")
            return

        print(f"\n📦 Will download {len(files_to_download)} file(s):")
        for f in files_to_download[:5]:  # Show first 5
            print(f"   • {f}")
        if len(files_to_download) > 5:
            print(f"   • ... and {len(files_to_download) - 5} more")

        # Get download directory
        output_dir = get_download_directory(args.dir)
        # Save directly to output_dir without subfolders

        # Confirm
        print("\n" + "=" * 70)
        print("📋 Summary:")
        print("=" * 70)
        print(f"Repository: {repo}")
        if selected_quantization:
            print(f"Quantization: {selected_quantization}")
        else:
            print("Quantization: All GGUF files")
        print(f"Output directory: {output_dir}")
        print("=" * 70)

        confirm = input("\nStart download? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Download cancelled.")
            return

        # Download
        downloaded, failed = download_files(repo, files_to_download, output_dir)

        if downloaded:
            print_usage_instructions(repo, output_dir)
            print("\n🎉 Download complete!")
        else:
            print("\n⚠️  No files were downloaded successfully.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
