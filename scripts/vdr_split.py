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
"""Split the monolithic ``vdr.xml`` into per-(CVE, component) files.

Reads ``src/site/static/cyclonedx/vdr.xml`` and writes ``src/vulnerabilities/<CVE-id>/<component>.cdx.xml``.

One output file is produced per affected component.

The special ``log4cxx-conan`` component never gets its own file; its vulnerabilities are always one-to-one with
 ``log4cxx`` and are reflected in the log4cxx file via a ``<components>`` entry plus a ``<dependencies>`` edge.
"""

from __future__ import annotations

import sys

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


def build_bom(
    subject_component: etree._Element,
    vuln_elem: etree._Element,
    timestamp: str,
    serial_number: str,
    version: int,
    extra_components: list[etree._Element] | None = None,
    dependencies: list[tuple[str, list[str]]] | None = None,
) -> etree._Element:
    """Build a CycloneDX 1.7 ``<bom>`` element wrapping a single vulnerability.

    ``subject_component`` becomes ``metadata/component``; ``extra_components``
    and ``dependencies`` (optional) populate the top-level ``<components>`` and
    ``<dependencies>`` sections used by log4cxx files to link log4cxx-conan.
    """
    bom = etree.Element(qn("bom"), nsmap={None: NS, "xsi": NS_XSI})
    bom.set(f"{{{NS_XSI}}}schemaLocation", SCHEMA_LOCATION)
    bom.set("serialNumber", serial_number)
    bom.set("version", str(version))

    metadata = etree.SubElement(bom, qn("metadata"))
    etree.SubElement(metadata, qn("timestamp")).text = timestamp
    metadata.append(clone_into_namespace(subject_component, NS))
    manufacturer = etree.SubElement(metadata, qn("manufacturer"))
    etree.SubElement(manufacturer, qn("name")).text = "Apache Logging Services"
    etree.SubElement(manufacturer, qn("url")).text = "https://logging.apache.org"

    # Log4cxx dependencies get extra components that are dependants of the main log4cxx component.
    # This way we express the fact that:
    #
    # - Our statement is about log4cxx, not log4cxx-conan.
    # - log4cxx-conan is derived from log4cxx and thus shares its vulnerabilities.
    if extra_components:
        components_elem = etree.SubElement(bom, qn("components"))
        for c in extra_components:
            components_elem.append(clone_into_namespace(c, NS))

    if dependencies:
        deps_elem = etree.SubElement(bom, qn("dependencies"))
        for dep_ref, sub_refs in dependencies:
            d = etree.SubElement(deps_elem, qn("dependency"), ref=dep_ref)
            for s in sub_refs:
                etree.SubElement(d, qn("dependency"), ref=s)

    vulns_elem = etree.SubElement(bom, qn("vulnerabilities"))
    vulns_elem.append(clone_into_namespace(vuln_elem, NS))

    return bom


def main() -> int:
    """Parse the source VDR and write one output file per (CVE, component) pair.

    Skips ``log4cxx-conan`` as a standalone subject; instead, when a
    vulnerability affects both ``log4cxx`` and ``log4cxx-conan``, the
    log4cxx output file gains the conan component plus a dependency edge.
    """
    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)
    tree = etree.parse(str(SRC_VDR), parser)
    root = tree.getroot()

    # The source vdr.xml may be at any CycloneDX namespace (1.6 or 1.7); query
    # children using the actual namespace of the root, not the output NS.
    src_ns = etree.QName(root).namespace

    components_root = root.find(qn("components", src_ns))
    components_by_ref = {
        c.get("bom-ref"): c
        for c in components_root.findall(qn("component", src_ns))
    }

    vulns_root = root.find(qn("vulnerabilities", src_ns))
    wrote = 0
    unchanged = 0
    for vuln in vulns_root.findall(qn("vulnerability", src_ns)):
        cve_id = vuln.findtext(qn("id", src_ns))
        target_refs = [
            t.findtext(qn("ref", src_ns))
            for t in vuln.findall(f".//{qn('target', src_ns)}")
        ]
        subject_refs = [r for r in target_refs if r != "log4cxx-conan"]
        if not subject_refs:
            print(f"warning: {cve_id} has no non-conan subject; skipping", file=sys.stderr)
            continue
        updated = vuln.findtext(qn("updated", src_ns))
        for subject in subject_refs:
            extras: list[etree._Element] = []
            deps: list[tuple[str, list[str]]] = []
            # log4cxx-conan is always an extra component of log4cxx, never a standalone subject.
            if subject == "log4cxx" and "log4cxx-conan" in target_refs:
                extras = [components_by_ref["log4cxx-conan"]]
                deps = [("log4cxx-conan", ["log4cxx"])]
            out_path = OUT_DIR / cve_id / f"{subject}.cdx.xml"

            def build_fn(serial: str, version: int) -> etree._Element:
                return build_bom(
                    subject_component=components_by_ref[subject],
                    vuln_elem=vuln,
                    timestamp=updated,
                    serial_number=serial,
                    version=version,
                    extra_components=extras,
                    dependencies=deps,
                )

            did_write, final_version = write_bom_if_changed(out_path, build_fn, serialize)
            rel = out_path.relative_to(ROOT)
            if did_write:
                print(f"wrote {rel} (v{final_version})")
                wrote += 1
            else:
                print(f"unchanged {rel} (v{final_version})")
                unchanged += 1
    print(f"summary: wrote {wrote}, unchanged {unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
