#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Scan SBOMs in callgraph-metadata for new CVEs via OSV.dev.

Usage:
    python scripts/osv_scan.py \
        --sbom-dir callgraph-metadata/sboms \
        --vuln-dir src/vulnerabilities \
        --output /tmp/new-cves.json
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_BATCH_LIMIT = 1000  # max queries per request


def load_sboms(sbom_dir: Path) -> list[dict]:
    """
    Walk sbom_dir for *.cdx.json files.

    Returns a list of dicts:
        {
            "root": <metadata.component from SBOM>,
            "dep_purls": [<purl>, ...],
        }
    The root component identifies the monitored Log4j artifact.
    dep_purls are its dependencies — what we query OSV for.
    """
    sboms: list[dict] = []
    for sbom_path in sorted(sbom_dir.rglob("*.json")):
        try:
            with open(sbom_path, encoding="utf-8") as fh:
                sbom = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING: could not parse {sbom_path}: {exc}", file=sys.stderr)
            continue

        root = sbom.get("metadata", {}).get("component")
        if not root:
            print(f"  WARNING: no metadata.component in {sbom_path}", file=sys.stderr)
            continue

        dep_purls = [
            c["purl"]
            for c in sbom.get("components", [])
            if c.get("purl")
        ]
        if not dep_purls:
            continue

        sboms.append({"root": root, "dep_purls": dep_purls})

    return sboms


def _fetch_cve_for_vuln(vuln_id: str) -> str | None:
    """
    Fetch the full OSV record for vuln_id and return the first CVE alias,
    or None if there is no CVE alias.

    The batch API only returns id + modified; aliases require a full fetch.
    """
    url = f"https://api.osv.dev/v1/vulns/{vuln_id}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            record = json.loads(resp.read())
    except urllib.error.URLError as exc:
        print(f"  WARNING: could not fetch {url}: {exc}", file=sys.stderr)
        return None

    for alias in record.get("aliases", []):
        if alias.startswith("CVE-"):
            return alias
    # The primary id itself might be a CVE (less common on OSV)
    if record.get("id", "").startswith("CVE-"):
        return record["id"]
    return None


def query_osv(purls: list[str]) -> dict[str, list[str]]:
    """
    Batch-query OSV.dev for the given purls.

    Returns {purl: [cve_id, ...]} for purls that have CVE hits.
    The batch endpoint only returns GHSA ids + modified; we follow up with
    individual fetches to resolve CVE aliases.
    """
    hits: dict[str, list[str]] = {}
    # Cache GHSA → CVE lookups to avoid redundant fetches
    vuln_id_to_cve: dict[str, str | None] = {}

    for offset in range(0, len(purls), OSV_BATCH_LIMIT):
        chunk = purls[offset : offset + OSV_BATCH_LIMIT]
        payload = json.dumps(
            {"queries": [{"package": {"purl": p}} for p in chunk]}
        ).encode()

        req = urllib.request.Request(
            OSV_BATCH_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read())
        except urllib.error.URLError as exc:
            print(f"OSV.dev request failed: {exc}", file=sys.stderr)
            raise

        for purl, result in zip(chunk, body["results"]):
            cves = []
            for v in result.get("vulns", []):
                vuln_id = v.get("id", "")
                if not vuln_id:
                    continue
                if vuln_id not in vuln_id_to_cve:
                    vuln_id_to_cve[vuln_id] = _fetch_cve_for_vuln(vuln_id)
                cve = vuln_id_to_cve[vuln_id]
                if cve and cve not in cves:
                    cves.append(cve)
            if cves:
                hits[purl] = cves

    return hits


def known_cve_ids(vuln_dir: Path) -> set[str]:
    """Return CVE ids already tracked under src/vulnerabilities/."""
    if not vuln_dir.exists():
        return set()
    return {
        p.name
        for p in vuln_dir.iterdir()
        if p.is_dir() and p.name.startswith("CVE-")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sbom-dir",
        required=True,
        type=Path,
        help="Root of callgraph-metadata/sboms",
    )
    parser.add_argument(
        "--vuln-dir",
        required=True,
        type=Path,
        help="src/vulnerabilities directory in logging-site",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Where to write the JSON findings list",
    )
    args = parser.parse_args()

    # ── 1. Load SBOMs ──────────────────────────────────────────────────────
    print(f"Scanning SBOMs under {args.sbom_dir} …")
    sboms = load_sboms(args.sbom_dir)
    if not sboms:
        print("No SBOMs found; nothing to scan.")
        args.output.write_text("[]")
        return 0
    print(f"  {len(sboms)} SBOM(s) found.")

    # ── 2. Collect unique dep purls, tracking which root(s) each belongs to ─
    purl_to_roots: dict[str, list[dict]] = {}
    for sbom in sboms:
        for purl in sbom["dep_purls"]:
            purl_to_roots.setdefault(purl, []).append(sbom["root"])

    all_purls = list(purl_to_roots)
    print(f"Querying OSV.dev for {len(all_purls)} unique purl(s) …")

    # ── 3. Query OSV.dev ───────────────────────────────────────────────────
    osv_hits = query_osv(all_purls)
    if not osv_hits:
        print("No CVEs found by OSV.dev.")
        args.output.write_text("[]")
        return 0
    print(f"  OSV hit on {len(osv_hits)} purl(s).")

    # ── 4. Filter out already-known CVEs ──────────────────────────────────
    existing = known_cve_ids(args.vuln_dir)
    print(f"  {len(existing)} CVE(s) already tracked in {args.vuln_dir}.")

    # ── 5. Build deduplicated findings list ───────────────────────────────
    seen: set[tuple[str, str]] = set()
    findings: list[dict] = []

    for purl, cves in osv_hits.items():
        for cve in cves:
            if cve in existing:
                continue
            for root in purl_to_roots[purl]:
                bom_ref = root.get("bom-ref") or root.get("name", "unknown")
                key = (cve, bom_ref)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "cve_id": cve,
                        "dep_purl": purl,
                        "root_component": root,
                    }
                )

    print(f"New CVEs to file: {len(findings)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(findings, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())