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

Reads ``src/site/static/cyclonedx/vdr.xml`` (CycloneDX 1.6) and writes
``src/vulnerabilities/<CVE-id>/<component>.cdx.xml`` (CycloneDX 1.7).

One output file is produced per affected component, except that
``log4cxx-conan`` never gets its own file; its vulnerabilities are always
one-to-one with ``log4cxx`` and are reflected in the log4cxx file via a
``<components>`` entry plus a ``<dependencies>`` edge.
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "site" / "static" / "cyclonedx" / "vdr.xml"
OUT_DIR = ROOT / "src" / "vulnerabilities"

NS_OLD = "http://cyclonedx.org/schema/bom/1.6"
NS_NEW = "http://cyclonedx.org/schema/bom/1.7"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = f"{NS_NEW} https://cyclonedx.org/schema/bom-1.7.xsd"

LICENSE_HEADER = """<!--
  ~ Licensed to the Apache Software Foundation (ASF) under one or more
  ~ contributor license agreements.  See the NOTICE file distributed with
  ~ this work for additional information regarding copyright ownership.
  ~ The ASF licenses this file to you under the Apache License, Version 2.0
  ~ (the "License"); you may not use this file except in compliance with
  ~ the License.  You may obtain a copy of the License at
  ~
  ~      http://www.apache.org/licenses/LICENSE-2.0
  ~
  ~ Unless required by applicable law or agreed to in writing, software
  ~ distributed under the License is distributed on an "AS IS" BASIS,
  ~ WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  ~ See the License for the specific language governing permissions and
  ~ limitations under the License.
  -->"""


def qn(tag: str, ns: str = NS_NEW) -> str:
    """Return the Clark-notation qualified name ``{ns}tag`` for lxml lookups."""
    return f"{{{ns}}}{tag}"


def copy_into_new_ns(source_elem: etree._Element) -> etree._Element:
    """Deep-copy ``source_elem`` from NS_OLD into NS_NEW, preserving CDATA.

    Serializes, strips the inherited default xmlns, and re-parses under a
    wrapper declaring NS_NEW as default so the returned element carries no
    redundant xmlns attribute and can be appended cleanly to the new BOM.
    """
    inner = etree.tostring(source_elem, encoding="unicode")
    inner = inner.replace(f' xmlns="{NS_OLD}"', "")
    wrapped = f'<wrap xmlns="{NS_NEW}">{inner}</wrap>'
    parser = etree.XMLParser(strip_cdata=False)
    wrap = etree.fromstring(wrapped.encode("utf-8"), parser)
    return wrap[0]


def read_existing_serial(path: Path) -> str | None:
    """Return the ``serialNumber`` of the BOM at ``path`` if it parses, else None.

    Used to keep ``urn:uuid:`` identifiers stable across re-runs so the script
    is idempotent and re-generation produces no spurious diffs.
    """
    if not path.is_file():
        return None
    try:
        existing = etree.parse(str(path)).getroot()
    except etree.XMLSyntaxError:
        return None
    return existing.get("serialNumber")


def build_bom(
    subject_component: etree._Element,
    vuln_elem: etree._Element,
    timestamp: str,
    serial_number: str,
    extra_components: list[etree._Element] | None = None,
    dependencies: list[tuple[str, list[str]]] | None = None,
) -> etree._Element:
    """Build a CycloneDX 1.7 ``<bom>`` element wrapping a single vulnerability.

    ``subject_component`` becomes ``metadata/component``; ``extra_components``
    and ``dependencies`` (optional) populate the top-level ``<components>`` and
    ``<dependencies>`` sections used by log4cxx files to link log4cxx-conan.
    """
    bom = etree.Element(qn("bom"), nsmap={None: NS_NEW, "xsi": NS_XSI})
    bom.set(f"{{{NS_XSI}}}schemaLocation", SCHEMA_LOCATION)
    bom.set("serialNumber", serial_number)
    bom.set("version", "1")

    metadata = etree.SubElement(bom, qn("metadata"))
    etree.SubElement(metadata, qn("timestamp")).text = timestamp
    metadata.append(copy_into_new_ns(subject_component))
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
            components_elem.append(copy_into_new_ns(c))

    if dependencies:
        deps_elem = etree.SubElement(bom, qn("dependencies"))
        for dep_ref, sub_refs in dependencies:
            d = etree.SubElement(deps_elem, qn("dependency"), ref=dep_ref)
            for s in sub_refs:
                etree.SubElement(d, qn("dependency"), ref=s)

    vulns_elem = etree.SubElement(bom, qn("vulnerabilities"))
    vulns_elem.append(copy_into_new_ns(vuln_elem))

    return bom


def fold_bom_attributes(body: bytes) -> bytes:
    """Hack: fold the ``<bom ...>`` start tag so each attribute past the
    first sits on its own line, indented to align under the first. lxml's
    serializer offers no per-attribute wrap option, so we post-process it.
    """
    match = re.match(rb'<bom ([^>]*?)(/?>)', body)
    if not match:
        return body
    attrs = re.findall(rb'[\w:-]+="[^"]*"', match.group(1))
    if len(attrs) <= 1:
        return body
    indent = b"\n" + b" " * len(b"<bom ")
    return b"<bom " + indent.join(attrs) + match.group(2) + body[match.end():]


def serialize(bom: etree._Element) -> bytes:
    """Serialize ``bom`` as a pretty-printed UTF-8 file with the ASF header.

    Drops unused namespace declarations inherited from the source tree,
    applies 2-space indentation, and prepends the XML declaration and
    Apache License comment block.
    """
    etree.cleanup_namespaces(bom, top_nsmap={None: NS_NEW})
    etree.indent(bom, space="  ")
    body = fold_bom_attributes(etree.tostring(bom, xml_declaration=False, encoding="UTF-8"))
    decl = b'<?xml version="1.0" encoding="UTF-8"?>\n'
    header = LICENSE_HEADER.encode("utf-8") + b"\n"
    return decl + header + body + b"\n"


def main() -> int:
    """Parse the source VDR and write one output file per (CVE, component) pair.

    Skips ``log4cxx-conan`` as a standalone subject; instead, when a
    vulnerability affects both ``log4cxx`` and ``log4cxx-conan``, the
    log4cxx output file gains the conan component plus a dependency edge.
    """
    parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)
    tree = etree.parse(str(SRC), parser)
    root = tree.getroot()

    # Parses the components
    components_root = root.find(qn("components", NS_OLD))
    components_by_ref = {
        c.get("bom-ref"): c
        for c in components_root.findall(qn("component", NS_OLD))
    }

    # Parses the vulnerabilities and write one file per (CVE, component) pair.
    vulns_root = root.find(qn("vulnerabilities", NS_OLD))
    count = 0
    for vuln in vulns_root.findall(qn("vulnerability", NS_OLD)):
        cve_id = vuln.findtext(qn("id", NS_OLD))
        target_refs = [
            t.findtext(qn("ref", NS_OLD))
            for t in vuln.findall(f".//{qn('target', NS_OLD)}")
        ]
        subject_refs = [r for r in target_refs if r != "log4cxx-conan"]
        if not subject_refs:
            print(f"warning: {cve_id} has no non-conan subject; skipping", file=sys.stderr)
            continue
        updated = vuln.findtext(qn("updated", NS_OLD))
        for subject in subject_refs:
            extras: list[etree._Element] = []
            deps: list[tuple[str, list[str]]] = []
            # log4cxx-conan is always an extra component of log4cxx, never a standalone subject.
            if subject == "log4cxx" and "log4cxx-conan" in target_refs:
                extras = [components_by_ref["log4cxx-conan"]]
                deps = [("log4cxx-conan", ["log4cxx"])]
            out_path = OUT_DIR / cve_id / f"{subject}.cdx.xml"
            serial_number = read_existing_serial(out_path) or f"urn:uuid:{uuid.uuid4()}"
            bom = build_bom(
                subject_component=components_by_ref[subject],
                vuln_elem=vuln,
                timestamp=updated,
                serial_number=serial_number,
                extra_components=extras,
                dependencies=deps,
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(serialize(bom))
            print(f"wrote {out_path.relative_to(ROOT)}")
            count += 1
    print(f"generated {count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
