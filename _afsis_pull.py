"""Temporary: pull the AfSIS Phase I CSV tables this pipeline actually reads.

Downloads over anonymous HTTPS (no boto3, no AWS CLI). Deliberately narrow:
Georeferences + every Wet_Chemistry lab CSV + the 2009-2013 licence/readme.
The SOP PDFs (~18 MB) are skipped - they are method documentation, not data.
"""
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

BASE = "https://afsis.s3.amazonaws.com/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
OUT = Path("afsis")
# Kept regardless of extension, so the run's licence claim can cite the real file.
EXPLICIT = ("2009-2013/LICENSE.txt", "2009-2013/README.md")


def list_prefix(prefix, delimiter=None):
    params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if delimiter:
        params["delimiter"] = delimiter
    keys, token = [], None
    while True:
        if token:
            params["continuation-token"] = token
        r = requests.get(BASE, params=params, timeout=60)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for c in root.findall(f"{NS}Contents"):
            keys.append((c.find(f"{NS}Key").text, int(c.find(f"{NS}Size").text)))
        trunc = root.find(f"{NS}IsTruncated")
        nxt = root.find(f"{NS}NextContinuationToken")
        if trunc is not None and trunc.text == "true" and nxt is not None:
            token = nxt.text
        else:
            break
    return keys


def wanted(key: str) -> bool:
    if key in EXPLICIT:
        return True
    if not key.endswith(".csv"):
        return False
    return key.startswith("2009-2013/Georeferences/") or key.startswith("2009-2013/Wet_Chemistry/")


def fetch(key: str, size: int) -> str:
    dest = OUT / key.replace("2009-2013/", "", 1) if key.startswith("2009-2013/") else OUT / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(BASE + key, stream=True, timeout=120) as r:
        r.raise_for_status()
        h = hashlib.sha256()
        n = 0
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
                h.update(chunk)
                n += len(chunk)
    if n != size:
        print(f"  !! {key}: expected {size} bytes, wrote {n}")
    print(f"  {n/1048576:7.3f} MB  {dest.as_posix()}  sha256:{h.hexdigest()[:12]}")
    return h.hexdigest()


def main():
    keys = list_prefix("2009-2013/")
    picked = [(k, s) for k, s in keys if wanted(k)]
    total = sum(s for _, s in picked)
    print(f"{len(picked)} files, {total/1048576:.2f} MB")
    for k, s in picked:
        fetch(k, s)
    print(f"\nwritten under {(OUT / '').resolve()}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
