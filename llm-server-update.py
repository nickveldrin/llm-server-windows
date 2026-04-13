#!/usr/bin/env python3
"""llm-server Auto-Updater for Windows
Checks for updates and downloads the latest version.
"""

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import requests


def get_latest_release():
    """Get the latest release information from GitHub."""
    try:
        result = requests.get(
            "https://api.github.com/repos/raketenkater/llm-server/releases/latest",
            timeout=10,
        )
        result.raise_for_status()
        return result.json()
    except Exception:
        return None


def check_updates() -> bool:
    """Check if updates are available."""
    latest = get_latest_release()
    if not latest:
        return False

    latest_version = latest.get("tag_name", "v0.0.0").lstrip("v")
    current_version = "2.0.0"

    return latest_version > current_version


def download_update() -> bool | None:
    """Download the latest version."""
    latest = get_latest_release()
    if not latest:
        return False

    # Find the Windows asset
    assets = latest.get("assets", [])
    windows_asset = None

    for asset in assets:
        name = asset.get("name", "")
        if "windows" in name.lower() or "win" in name.lower():
            windows_asset = asset
            break

    if not windows_asset:
        return False

    download_url = windows_asset.get("browser_download_url", "")
    if not download_url:
        return False

    try:
        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = tmp.name
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, tmp)

        # Extract to current directory
        extract_dir = Path.cwd()
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(extract_dir)

        # Clean up
        Path(tmp_path).unlink()

        return True

    except Exception:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()
        return False


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd in {"check", "--check"}:
            check_updates()
        elif cmd in {"update", "--update", "--upgrade"} and check_updates():
            if input("Download and install? [y/N] ").lower() == "y":
                download_update()
    # Auto-check for updates
    elif check_updates():
        if input("Download and install? [y/N] ").lower() == "y":
            download_update()


if __name__ == "__main__":
    main()
