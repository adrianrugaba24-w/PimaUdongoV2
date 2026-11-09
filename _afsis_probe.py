"""Temporary probe: list the public AfSIS S3 bucket over plain HTTPS.

No boto3 / AWS CLI needed. Prints prefixes and object sizes so a download can be
scoped deliberately rather than pulling the whole archive.
"""
import sys
import xml.etree.ElementTree as ET

import requests

BASE = "https://afsis.s3.amazonaws.com/"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def list_prefix(prefix, delimiter=None):
    params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if delimiter:
        params["delimiter"] = delimiter
    out, token = [], None
    while True:
        if token:
            params["continuation-token"] = token
        r = requests.get(BASE, params=params, timeout=60)
        if r.status_code != 200:
            print(f"HTTP {r.status_code} for prefix={prefix!r}: {r.text[:300]}")
            return out
        root = ET.fromstring(r.content)
        for cp in root.findall(f"{NS}CommonPrefixes/{NS}Prefix"):
            out.append(("PREFIX", cp.text, 0))
        for c in root.findall(f"{NS}Contents"):
            key = c.find(f"{NS}Key").text
            size = int(c.find(f"{NS}Size").text)
            out.append(("KEY", key, size))
        trunc = root.find(f"{NS}IsTruncated")
        nxt = root.find(f"{NS}NextContinuationToken")
        if trunc is not None and trunc.text == "true" and nxt is not None:
            token = nxt.text
        else:
            break
    return out


def main():
    for label, prefix, delim in (
        ("top level", "", "/"),
        ("2009-2013", "2009-2013/", "/"),
        ("Georeferences", "2009-2013/Georeferences/", None),
        ("Wet_Chemistry", "2009-2013/Wet_Chemistry/", None),
    ):
        print(f"\n=== {label} (prefix={prefix!r}) ===")
        rows = list_prefix(prefix, delim)
        if not rows:
            print("  (nothing returned)")
            continue
        total = 0
        for kind, key, size in rows:
            if kind == "PREFIX":
                print(f"  DIR   {key}")
            else:
                total += size
                print(f"  {size/1048576:10.2f} MB  {key}")
        print(f"  --- {label}: {total/1048576:.2f} MB in {len(rows)} entries")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
