#!/usr/bin/env python3
"""
llm-server Auto-Updater for Windows
Checks for updates and downloads the latest version
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
import requests

def get_latest_release():
    """Get the latest release information from GitHub"""
    try:
        result = requests.get(
            "https://api.github.com/repos/raketenkater/llm-server/releases/latest",
            timeout=10
        )
        result.raise_for_status()
        return result.json()
    except Exception as e:
        print(f"Error fetching release info: {e}")
        return None

def check_updates():
    """Check if updates are available"""
    print("Checking for llm-server-windows updates...")
    
    latest = get_latest_release()
    if not latest:
        return False
    
    latest_version = latest.get('tag_name', 'v0.0.0').lstrip('v')
    current_version = "2.0.0"
    
    print(f"Current version: {current_version}")
    print(f"Latest version:  {latest_version}")
    
    if latest_version > current_version:
        print(f"\n✅ Update available!")
        print(f"  Release: {latest.get('name', 'N/A')}")
        print(f"  Published: {latest.get('published_at', 'N/A')}")
        print(f"  Download: {latest.get('html_url', '')}")
        return True
    else:
        print("\n✅ Up to date!")
        return False

def download_update():
    """Download the latest version"""
    print("Downloading update...")
    
    latest = get_latest_release()
    if not latest:
        return False
    
    # Find the Windows asset
    assets = latest.get('assets', [])
    windows_asset = None
    
    for asset in assets:
        name = asset.get('name', '')
        if 'windows' in name.lower() or 'win' in name.lower():
            windows_asset = asset
            break
    
    if not windows_asset:
        print("No Windows asset found in latest release")
        return False
    
    download_url = windows_asset.get('browser_download_url', '')
    if not download_url:
        print("Could not find download URL")
        return False
    
    try:
        # Download to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            tmp_path = tmp.name
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, tmp)
        
        # Extract to current directory
        extract_dir = Path.cwd()
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(extract_dir)
        
        # Clean up
        os.unlink(tmp_path)
        
        print(f"✅ Update installed successfully!")
        return True
    
    except Exception as e:
        print(f"Error downloading update: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd in ['check', '--check']:
            check_updates()
        elif cmd in ['update', '--update', '--upgrade']:
            if check_updates():
                if input("Download and install? [y/N] ").lower() == 'y':
                    download_update()
        else:
            print("Usage: llm-server-update.py [check|update]")
    else:
        # Auto-check for updates
        if check_updates():
            if input("Download and install? [y/N] ").lower() == 'y':
                download_update()
        else:
            print("No updates available.")

if __name__ == "__main__":
    main()
