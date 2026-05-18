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
"""Shared constants and helpers for the VDR split/aggregate scripts.

This is a plain importable module (no inline ``# /// script`` block); the
calling script's ``uv run --script`` venv must provide ``lxml``.
"""

from __future__ import annotations

import copy
import re
import uuid
from collections.abc import Callable
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
SRC_VDR = ROOT / "src" / "site" / "static" / "cyclonedx" / "vdr.xml"
OUT_DIR = ROOT / "src" / "vulnerabilities"

NS = "http://cyclonedx.org/schema/bom/1.7"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = f"{NS} https://cyclonedx.org/schema/bom-1.7.xsd"

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


def qn(tag: str, ns: str = NS) -> str:
    """Return the Clark-notation qualified name ``{ns}tag`` for lxml lookups."""
    return f"{{{ns}}}{tag}"


def clone(elem: etree._Element) -> etree._Element:
    """Deep-copy ``elem`` so it can be appended to another tree.

    lxml preserves CDATA across ``deepcopy``; redundant inherited xmlns
    declarations are stripped later by ``cleanup_namespaces`` in ``serialize``.
    """
    return copy.deepcopy(elem)


def clone_into_namespace(elem: etree._Element, dst_ns: str) -> etree._Element:
    """Deep-copy ``elem`` into ``dst_ns``, rewriting the default xmlns.

    Used when migrating elements between CycloneDX schema versions (e.g.
    reading a 1.6 source vdr.xml while writing 1.7 outputs). When the source
    is already in ``dst_ns`` this is a no-op transform. Preserves CDATA via
    the explicit ``strip_cdata=False`` parser.
    """
    src_ns = etree.QName(elem).namespace
    inner = etree.tostring(elem, encoding="unicode")
    if src_ns:
        inner = inner.replace(f' xmlns="{src_ns}"', "")
    wrapped = f'<wrap xmlns="{dst_ns}">{inner}</wrap>'
    parser = etree.XMLParser(strip_cdata=False)
    return etree.fromstring(wrapped.encode("utf-8"), parser)[0]


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


def serialize(
    bom: etree._Element,
    extra_header: bytes = b"",
    after_indent: Callable[[etree._Element], None] | None = None,
) -> bytes:
    """Serialize ``bom`` as a pretty-printed UTF-8 file with the ASF header.

    Drops unused namespace declarations inherited from the source tree,
    applies 2-space indentation, and prepends the XML declaration and
    Apache License comment block. ``extra_header`` (if provided) is inserted
    between the ASF license block and the ``<bom>`` tree. ``after_indent``
    (if provided) runs after ``etree.indent()`` so callers can adjust
    ``.text``/``.tail`` whitespace before serialization.
    """
    etree.cleanup_namespaces(bom, top_nsmap={None: NS})
    etree.indent(bom, space="  ")
    if after_indent is not None:
        after_indent(bom)
    body = fold_bom_attributes(etree.tostring(bom, xml_declaration=False, encoding="UTF-8"))
    decl = b'<?xml version="1.0" encoding="UTF-8"?>\n'
    header = LICENSE_HEADER.encode("utf-8") + b"\n"
    return decl + header + extra_header + body + b"\n"


def _local_attrs(elem: etree._Element) -> dict[str, str]:
    """Attribute dict keyed by local name, dropping namespace prefixes."""
    return {etree.QName(k).localname: v for k, v in elem.attrib.items()}


def equivalent(a: etree._Element, b: etree._Element) -> bool:
    """Recursively compare two elements, ignoring comments, namespaces, and outer whitespace.

    Matches local tag name and attribute dict by local name (so namespace
    differences -- e.g. CycloneDX 1.7 vs 1.8 -- don't trigger inequality on
    structure alone). Compares ``.text`` after ``strip()``; ``.tail``
    (inter-element whitespace) and comment children are ignored. Internal
    whitespace inside text content is significant.
    """
    if etree.QName(a).localname != etree.QName(b).localname:
        return False
    if _local_attrs(a) != _local_attrs(b):
        return False
    if (a.text or "").strip() != (b.text or "").strip():
        return False
    a_kids = [c for c in a if not isinstance(c, etree._Comment)]
    b_kids = [c for c in b if not isinstance(c, etree._Comment)]
    if len(a_kids) != len(b_kids):
        return False
    return all(equivalent(ac, bc) for ac, bc in zip(a_kids, b_kids))


def write_bom_if_changed(
    path: Path,
    build_fn: Callable[[str, int], etree._Element],
    serialize_fn: Callable[[etree._Element], bytes],
) -> tuple[bool, int]:
    """Build a BOM and write it to ``path`` only if it differs from the existing file.

    On a missing file: mints a new ``urn:uuid:`` serial and writes at version 1.
    On an existing file: reuses ``serialNumber``, builds a candidate at the
    existing version, and compares via ``equivalent``. If equivalent, returns
    ``(False, version)`` without touching the file. Otherwise bumps the version
    by one, updates the candidate's ``version`` attribute, writes, and returns
    ``(True, version + 1)``. Parsing errors on an existing file propagate.
    """
    if path.is_file():
        compare_parser = etree.XMLParser(remove_blank_text=True, strip_cdata=False)
        existing_root = etree.parse(str(path), compare_parser).getroot()
        serial = existing_root.get("serialNumber")
        version_str = existing_root.get("version")
        if serial is None or version_str is None:
            raise ValueError(f"{path}: missing serialNumber or version on root element")
        version = int(version_str)
        candidate = build_fn(serial, version)
        if equivalent(candidate, existing_root):
            return False, version
        version += 1
        candidate.set("version", str(version))
    else:
        serial = f"urn:uuid:{uuid.uuid4()}"
        version = 1
        candidate = build_fn(serial, version)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(serialize_fn(candidate))
    return True, version
