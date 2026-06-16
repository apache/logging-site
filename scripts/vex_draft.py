#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Generate a draft CycloneDX 1.7 VDR file for a single CVE finding.

Usage (called once per CVE by the workflow):
    python scripts/vex_draft.py \
        --cve-id CVE-2025-12345 \
        --finding '{"cve_id":...,"dep_purl":...,"root_component":{...}}' \
        --vuln-dir src/vulnerabilities
"""

import argparse
import json
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

CDX_NS = "http://cyclonedx.org/schema/bom/1.7"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOC = (
    "http://cyclonedx.org/schema/bom/1.7 "
    "https://cyclonedx.org/schema/bom-1.7.xsd"
)

# CPE pattern per artifact name (sans version wildcard)
_CPE_MAP: dict[str, str] = {
    "log4j-core":                  "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*",
    "log4j-1.2-api":               "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*",
    "log4j-layout-template-json":  "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*",
    "log4net":                     "cpe:2.3:a:apache:log4net:*:*:*:*:*:*:*:*",
    "log4cxx":                     "cpe:2.3:a:apache:log4cxx:*:*:*:*:*:*:*:*",
}

# Ecosystem type → vers prefix
_VERS_PREFIX: dict[str, str] = {
    "maven": "vers:maven",
    "nuget": "vers:nuget",
    "conan": "vers:semver",
}


def _strip_version_from_purl(purl: str) -> str:
    """Remove @version from a purl, keeping qualifiers."""
    return re.sub(r"@[^?#]+", "", purl)


def _bom_ref(root_component: dict) -> str:
    return root_component.get("bom-ref") or root_component.get("name", "unknown")


def _purl_type(purl: str) -> str:
    """Extract type from 'pkg:<type>/...'."""
    m = re.match(r"pkg:([^/]+)/", purl)
    return m.group(1) if m else "maven"


def _vers_range(purl: str) -> str:
    """Return an open-ended vers range appropriate for the purl ecosystem."""
    prefix = _VERS_PREFIX.get(_purl_type(purl), "vers:generic")
    return f"{prefix}/>=0"


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line else "" for line in text.splitlines())


def build_draft_xml(cve_id: str, root_component: dict, dep_purl: str) -> str:
    """
    Produce a draft CycloneDX 1.7 VDR XML matching the template in
    src/vulnerabilities/template.cdx.xml.

    All maintainer-facing fields (description, recommendation, analysis,
    credits, ratings scores) are left as TODO placeholders.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    serial = f"urn:uuid:{uuid.uuid4()}"
    bref = _bom_ref(root_component)

    # Component fields (version-stripped purl)
    comp_purl_raw = root_component.get("purl", "")
    comp_purl_versioned = comp_purl_raw
    comp_purl = _strip_version_from_purl(comp_purl_versioned)
    group = root_component.get("group", "")
    name = root_component.get("name", bref)
    cpe = _CPE_MAP.get(bref, "")

    # Build <group> and <cpe> lines conditionally
    group_line = f"      <group>{group}</group>\n" if group else ""
    cpe_line = f"      <cpe>{cpe}</cpe>\n" if cpe else ""
    purl_line = f"      <purl>{comp_purl}</purl>\n" if comp_purl else ""

    affects_ref = bref
    vers_range = _vers_range(dep_purl)

    xml = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!--
  DRAFT — generated automatically by the VEX monitoring workflow.
  Maintainer checklist:
    [ ] Complete <description> and <recommendation>
    [ ] Add an <analysis> block (state / justification / detail)
    [ ] Set accurate version ranges in <affects>
    [ ] Fill in <ratings> (score / severity / vector) from NVD
    [ ] Add <credits> for the reporter
    [ ] Bump <updated> and <metadata/timestamp> whenever you edit this file
-->
<bom xmlns="{CDX_NS}"
     xmlns:xsi="{XSI_NS}"
     xsi:schemaLocation="{SCHEMA_LOC}"
     serialNumber="{serial}"
     version="1">

  <metadata>
    <timestamp>{now}</timestamp>
    <component type="library" bom-ref="{bref}">
{group_line}\
      <name>{name}</name>
{cpe_line}\
{purl_line}\
    </component>
    <manufacturer>
      <name>Apache Logging Services</name>
      <url>https://logging.apache.org</url>
    </manufacturer>
  </metadata>

  <vulnerabilities>
    <vulnerability>
      <id>{cve_id}</id>
      <source>
        <name>NVD</name>
        <url>https://nvd.nist.gov/vuln/detail/{cve_id}</url>
      </source>
      <ratings>
        <rating>
          <source>
            <name>NVD</name>
            <url>https://nvd.nist.gov/vuln/detail/{cve_id}</url>
          </source>
          <!-- TODO: fill in score, severity, method, vector from NVD -->
          <score>0.0</score>
          <severity>unknown</severity>
          <method>CVSSv3</method>
          <vector>TODO</vector>
        </rating>
      </ratings>
      <description><![CDATA[TODO: add description.]]></description>
      <recommendation><![CDATA[TODO: add recommendation / upgrade path.]]></recommendation>
      <!--
        TODO: add <analysis> block once the team has assessed impact, e.g.:
        <analysis>
          <state>not_affected</state>
          <justification>protected_by_mitigating_control</justification>
          <detail><![CDATA[Explain why.]]></detail>
        </analysis>
      -->
      <created>{now}</created>
      <published>{now}</published>
      <updated>{now}</updated>
      <credits>
        <!-- TODO: add reporter name/org -->
        <individuals>
          <individual>
            <name>TODO</name>
          </individual>
        </individuals>
      </credits>
      <affects>
        <target>
          <ref>{affects_ref}</ref>
          <versions>
            <version>
              <!-- TODO: narrow this range once the fix version is known -->
              <range><![CDATA[{vers_range}]]></range>
            </version>
          </versions>
        </target>
      </affects>
    </vulnerability>
  </vulnerabilities>

</bom>
"""
    return xml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cve-id", required=True)
    parser.add_argument(
        "--finding",
        required=True,
        help="JSON-encoded finding dict (cve_id, dep_purl, root_component)",
    )
    parser.add_argument(
        "--vuln-dir",
        required=True,
        type=Path,
        help="src/vulnerabilities directory",
    )
    args = parser.parse_args()

    finding = json.loads(args.finding)
    cve_id: str = finding["cve_id"]
    dep_purl: str = finding["dep_purl"]
    root_component: dict = finding["root_component"]

    bref = _bom_ref(root_component)
    out_dir = args.vuln_dir / cve_id
    out_file = out_dir / f"{bref}.cdx.xml"

    if out_file.exists():
        print(f"  SKIP: {out_file} already exists.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    xml = build_draft_xml(cve_id, root_component, dep_purl)
    out_file.write_text(xml, encoding="utf-8")
    print(f"  Created: {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
