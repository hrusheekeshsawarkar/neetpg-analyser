#!/usr/bin/env python3
"""Download NEET PG memory-based papers from known public sources."""

from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("neet-pg-papers")

# CollegeHai Google Drive (from collegehai/google-drive-links.txt)
GDRIVE = {
    "collegehai/NEETPG-2024-shift1.pdf": "12FmBfxFgnCdl6JYRzOeCS87n18wZ5_cb",
    "collegehai/NEETPG-2024-shift2.pdf": "1e9EZd8EEwB8Sbyb6pi4hR4sJ8AnJ0n8o",
    "collegehai/NEETPG-2023.pdf": "1FmZcfKFGisiad_GW9Ve0EfySnbYSUNnF",
    "collegehai/NEETPG-2020.pdf": "1nwtUqWhFRvz8sMhinYG28FCtMSX5fDJc",
}

# Dr Nishant Bhushan direct CDN links (public on neetpgquestionpapers page)
NISHANT = {
    "nishant-bhushan/NEETPG-2024-shift1-web.pdf": "https://www.nishantbhushan.in/_files/ugd/37999e_8c8e8e8e8e8e.pdf",  # placeholder - use known shift1 if found
}

# Known working Nishant URLs (from prior session)
NISHANT_KNOWN = {
    "nishant-bhushan/NEETPG-2024-shift2-direct.pdf": "https://www.nishantbhushan.in/_files/ugd/37999e_23cddc70e9364bf7baa07fa1886ee309.pdf?index=true",
}


def download_gdrive(file_id: str, dest: Path) -> bool:
    """Download Google Drive file by ID."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 5000:
        print(f"  skip (exists): {dest} ({dest.stat().st_size} bytes)")
        return True

    session_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    req = urllib.request.Request(session_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()

    # Large-file confirm token
    if b"virus scan warning" in data.lower() or b"confirm=" in data:
        m = re.search(rb"confirm=([0-9A-Za-z_-]+)", data)
        if m:
            token = m.group(1).decode()
            url = f"https://drive.google.com/uc?export=download&confirm={token}&id={file_id}"
            req2 = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=180) as resp2:
                data = resp2.read()

    if len(data) < 1000 or not data[:4].startswith(b"%PDF"):
        print(f"  FAIL {dest.name}: not a PDF ({len(data)} bytes)")
        return False

    dest.write_bytes(data)
    print(f"  OK {dest} ({len(data)} bytes)")
    return True


def download_url(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 5000:
        print(f"  skip (exists): {dest}")
        return True
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if len(data) < 500 or not data[:4].startswith(b"%PDF"):
        print(f"  FAIL {dest.name}: {len(data)} bytes")
        return False
    dest.write_bytes(data)
    print(f"  OK {dest} ({len(data)} bytes)")
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok = fail = 0

    print("=== Google Drive (CollegeHai) ===")
    for rel, fid in GDRIVE.items():
        if download_gdrive(fid, OUT / rel):
            ok += 1
        else:
            fail += 1

    print("\n=== Nishant direct ===")
    for rel, url in NISHANT_KNOWN.items():
        if download_url(url, OUT / rel):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} ok, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
