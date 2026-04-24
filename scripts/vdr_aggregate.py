#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["lxml>=5"]
# ///
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to you under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Aggregate per-CVE VDR files back into the monolithic ``vdr.xml``.

Reads ``src/vulnerabilities/<CVE-id>/<component>.cdx.xml`` (CycloneDX 1.7)
and writes ``src/site/static/cyclonedx/vdr.xml`` (CycloneDX 1.7), preserving
the existing ``serialNumber`` and incrementing ``version`` by one.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from lxml import etree

from vdr_common import (
    NS,
    NS_XSI,
    OUT_DIR,
    ROOT,
    SCHEMA_LOCATION,
    SRC_VDR,
    clone_into_namespace,
    qn,
    serialize,
    write_bom_if_changed,
)

CVE_RE = re.compile(r"^CVE-(\d{4})-(\d+)$")

DUMMY_COMPONENTS_COMMENT = """We add *dummy* components to refer to in `affects` blocks.
    This is necessary, since not all Log4j components have SBOMs associated with them.
"""

GENERATED_HEADER = """<!-- This file is a Vulnerability Disclosure Report (VDR) covering all Apache Logging Services[1] projects.
     This file adheres to the CycloneDX SBOM specification[2].

     The latest version of this file can be found at https://logging.apache.org/cyclonedx/vdr.xml

     All Apache Logging Services projects (e.g., Log4j) generate SBOMs containing `vulnerability-assertion` entries with links to this file.

     If you need help in addressing these vulnerabilities, suggestions/corrections on the content, and/or reporting new vulnerabilities, please refer to the Log4j support page[3].

     This file is maintained in version control[4].

     GENERATED FILE. Do not edit by hand. To update the VDR, edit the per-CVE
     files under `src/vulnerabilities/` and regenerate this file with:

         uv run scripts/vdr_aggregate.py

     [1] https://logging.apache.org
     [2] https://cyclonedx.org
     [3] https://logging.apache.org/log4j/2.x/support.html
     [4] https://github.com/apache/logging-site/tree/cyclonedx
     -->"""


def parse_cve(cve_id: str) -> tuple[int, int]:
    """Parse ``CVE-YYYY-NNNN`` into ``(year, number)`` for sorting."""
    m = CVE_RE.match(cve_id)
    if not m:
        raise ValueError(f"unrecognized CVE id: {cve_id!r}")
    return int(m.group(1)), int(m.group(2))


def discover_inputs() -> list[tuple[int, int, str, str, Path]]:
    """Return a list of ``(-year, -number, slug, cve_id, path)`` tuples.

    Negated year/number give descending sort order via the default ascending sort.
    """
    inputs: list[tuple[int, int, str, str, Path]] = []
    for path in OUT_DIR.glob("CVE-*/*.cdx.xml"):
        cve_id = path.parent.name
        slug = path.name.removesuffix(".cdx.xml")
        year, number = parse_cve(cve_id)
        inputs.append((-year, -number, slug, cve_id, path))
    inputs.sort()
    return inputs


def collect(inputs: list[tuple[int, int, str, str, Path]]) -> tuple[
    list[etree._Element], list[etree._Element], str
]:
    """Collect deduplicated components and vulnerabilities, plus the max timestamp.

    Components are gathered from both ``metadata/component`` (subject) and any
    top-level ``components/component`` (extras like log4cxx-conan), deduped by
    ``bom-ref`` and sorted alphabetically. Vulnerabilities are deduped by CVE
    id, preserving input sort order. The returned timestamp is the lexicographic
    max of every input's ``metadata/timestamp`` (ISO 8601 UTC strings sort
    correctly as text).
    """
    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)

    components_by_ref: dict[str, etree._Element] = {}
    vulns_by_cve: dict[str, etree._Element] = {}
    max_timestamp = ""

    for _, _, _, cve_id, path in inputs:
        tree = etree.parse(str(path), parser)
        root = tree.getroot()
        # Per-CVE files may be at any CycloneDX namespace; query and migrate
        # using the actual root namespace, then write the aggregate at NS.
        src_ns = etree.QName(root).namespace

        ts = root.findtext(f"{qn('metadata', src_ns)}/{qn('timestamp', src_ns)}") or ""
        if ts > max_timestamp:
            max_timestamp = ts

        subject = root.find(f"{qn('metadata', src_ns)}/{qn('component', src_ns)}")
        if subject is not None and subject.get("bom-ref") not in components_by_ref:
            components_by_ref[subject.get("bom-ref")] = clone_into_namespace(subject, NS)

        extras_root = root.find(qn("components", src_ns))
        if extras_root is not None:
            for c in extras_root.findall(qn("component", src_ns)):
                ref = c.get("bom-ref")
                if ref not in components_by_ref:
                    components_by_ref[ref] = clone_into_namespace(c, NS)

        if cve_id not in vulns_by_cve:
            vuln = root.find(f"{qn('vulnerabilities', src_ns)}/{qn('vulnerability', src_ns)}")
            if vuln is not None:
                vulns_by_cve[cve_id] = clone_into_namespace(vuln, NS)

    components = [components_by_ref[ref] for ref in sorted(components_by_ref)]
    seen: set[str] = set()
    ordered_vulns: list[etree._Element] = []
    for _, _, _, cve, _ in inputs:
        if cve in seen or cve not in vulns_by_cve:
            continue
        seen.add(cve)
        ordered_vulns.append(vulns_by_cve[cve])
    return components, ordered_vulns, max_timestamp


def build_bom(
    serial_number: str,
    version: int,
    timestamp: str,
    components: list[etree._Element],
    vulnerabilities: list[etree._Element],
) -> etree._Element:
    """Build the aggregated CycloneDX 1.7 ``<bom>`` element."""
    bom = etree.Element(qn("bom"), nsmap={None: NS, "xsi": NS_XSI})
    bom.set(f"{{{NS_XSI}}}schemaLocation", SCHEMA_LOCATION)
    bom.set("serialNumber", serial_number)
    bom.set("version", str(version))

    metadata = etree.SubElement(bom, qn("metadata"))
    etree.SubElement(metadata, qn("timestamp")).text = timestamp
    manufacturer = etree.SubElement(metadata, qn("manufacturer"))
    etree.SubElement(manufacturer, qn("name")).text = "Apache Logging Services"
    etree.SubElement(manufacturer, qn("url")).text = "https://logging.apache.org"

    bom.append(etree.Comment(DUMMY_COMPONENTS_COMMENT))
    components_elem = etree.SubElement(bom, qn("components"))
    for c in components:
        components_elem.append(c)

    vulns_elem = etree.SubElement(bom, qn("vulnerabilities"))
    for v in vulnerabilities:
        vulns_elem.append(v)

    return bom


def apply_blank_lines(bom: etree._Element) -> None:
    """Insert blank lines around children of ``<components>``/``<vulnerabilities>``,
    and after their closing tags.

    Mutates ``.text`` of each parent and ``.tail`` of every child (and of the
    parent itself) by prepending a single ``\\n`` to the indentation strings
    that ``etree.indent()`` already set. This produces a blank line wherever
    those whitespace nodes are emitted.
    """
    for parent_tag in ("components", "vulnerabilities"):
        parent = bom.find(qn(parent_tag))
        if parent is None:
            continue
        parent.text = "\n" + (parent.text or "")
        for child in parent:
            child.tail = "\n" + (child.tail or "")
        parent.tail = "\n" + (parent.tail or "")


def main() -> int:
    inputs = discover_inputs()
    if not inputs:
        print(f"no inputs found under {OUT_DIR.relative_to(ROOT)}", file=sys.stderr)
        return 1

    components, vulnerabilities, timestamp = collect(inputs)

    def build_fn(serial: str, version: int) -> etree._Element:
        return build_bom(
            serial_number=serial,
            version=version,
            timestamp=timestamp,
            components=components,
            vulnerabilities=vulnerabilities,
        )

    def serialize_fn(bom: etree._Element) -> bytes:
        return serialize(
            bom,
            extra_header=GENERATED_HEADER.encode("utf-8") + b"\n",
            after_indent=apply_blank_lines,
        )

    did_write, final_version = write_bom_if_changed(SRC_VDR, build_fn, serialize_fn)
    rel = SRC_VDR.relative_to(ROOT)
    verb = "wrote" if did_write else "unchanged"
    print(
        f"{verb} {rel} "
        f"({len(components)} components, {len(vulnerabilities)} vulnerabilities, version {final_version})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
