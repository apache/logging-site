---
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
layout: post
title: "How I Learned to Stop Worrying and Love the VEX"
description: "A short history of how we learned the importance of VEX-es for vulnerability analysis."
tags:
  - Apache Log4j
  - Open Source
  - Vulnerability Exploitation eXchange
type: post
---
![How I learned to Stop Worrying and Love the VEX](/img/posts/love-the-vex.png)

A **Vulnerability Exploitability eXchange (VEX)** is a machine-readable file used to indicate whether vulnerabilities in an application's third-party dependencies are actually exploitable.

We first encountered the term "VEX" in 2023 when we began publishing SBOMs and Vulnerability Disclosure Reports (VDRs) for Log4j, as part of [a larger STF initiative](https://logging.apache.org/blog/2023/12/14/announcing-support-from-the-stf.html). That work gave us the chance to learn directly from experts like [Steve Springett](https://owasp.org/www-board-candidates/2023/steve_springett) (whom we sincerely thank for his time and patience). One key takeaway from that experience: there are **two ways** in the CycloneDX machine-readable format for conveying vulnerability information in software components:

* A **Vulnerability Disclosure Report (VDR)** lists vulnerabilities **present** in a software component. There’s debate about whether it should also include third-party dependency vulnerabilities, but in the case of Log4j (a Java library that bundles no third-party dependencies), the answer is clear: it does not matter.

* A **Vulnerability Exploitability eXchange (VEX)** goes further, analysing whether the vulnerabilities present are **actually exploitable**.

# Why We Skipped the VEX for Log4j

Maintaining VEX files can be expensive—some companies spend hundreds of thousands, even millions of dollars each year to process and manage them. The cost typically scales with the number of CVEs that need to be evaluated annually.

For commercial entities that keep parts of their SBOM private, the bar is higher: **they must include every CVE in their VEX** to meet regulatory or contractual obligations, since clients are not able to determine whether a dependency is present or not in the product.

Open Source projects, on the other hand, often operate under different constraints. Since we publish a full SBOM that transparently lists all dependencies, we could reasonably limit our scope to just those declared dependencies—about 100 across all Log4j modules.

Still, even 100 dependencies represent a significant burden when all analysis must be done by volunteers in their spare time. Given that reality, we made a pragmatic decision: rather than invest that effort into producing and maintaining a VEX, we chose to only publish a VDR, which only lists the vulnerabilities in our own codebase.

# When the Absence of a VEX Became a Problem

At first, we were comfortable with our decision. But that changed when we helped Kafka migrate from Log4j 1 to Log4j 2\. I suggested using more human-friendly YAML-formatted configuration files, only to be met with [valid concerns](https://lists.apache.org/thread/khm0jn9f0vgp30pfyoy6jc0qy46sbklp):

* Adding `log4j-core` and its optional `jackson-dataformat-yaml` dependency could introduce security risks.

* Parsers are common sources of CVEs.

* While Log4j doesn't bundle dependencies (we only provide metadata and recommendations), Kafka's situation is different—each vulnerability in its transitive dependencies could force a new release.

That experience revealed a key blind spot: even if *we* know certain dependencies aren’t exploitable, our users don’t. They spend unnecessary time analyzing risks that don’t exist. For example, in Log4j Core, the parsing capabilities of Jackson are only used to read **trusted** configuration files—so typical parser vulnerabilities aren’t exploitable. But this nuance wasn’t documented **anywhere** that automated scanners could read.

# VEX *ante litteram*

Log4j Core is a very controlled consumer of `jackson-dataformat-yaml`. But what about other consumers? Would they be vulnerable to transitive dependencies like SnakeYAML? You’d think so—but when I thoroughly analyzed several SnakeYAML CVEs, none turned out to be exploitable through Jackson.

Still, that kind of analysis is extremely time-consuming:

1. Identify the exact method that caused the CVE (rarely detailed in CVE descriptions).

2. Analyze how, if at all, that method can be reached through your dependency tree.

3. Confirm there’s no sanitization or validation on any reachable path.

Surprisingly, some of this work has already been done for years by maintainers\! For example, downstream projects often raise issues like:

"Please upgrade `foo` to version 1.2.3 due to CVE-2025-1234."

What this request actually means is:

* *Please confirm your library is **compatible** with the patched version.*

* *Please tell us whether the vulnerability is **exploitable**.*

These human-readable questions are, in effect, *VEX requests*. Some examples can be found in the [`jackson-dataformats-text` repository](https://github.com/FasterXML/jackson-dataformats-text/issues?q=is%3Aissue%20state%3Aclosed%20snakeyaml%20cve).

These kinds of request leave Open Source maintainers two choices:

* Publish machine-readable VEXes so tools can automatically dismiss non-exploitable issues and many user questions can be avoided.

* Or answer these questions only manually—repeatedly, and often redundantly.

# Toward Faster, Smarter VEXes

The turning point came at FOSDEM 2025, where I met **Munawar Hafiz (OpenRefactory)**. As we discussed the VEX burden, we realized much of the manual analysis could be automated.

In the months that followed, Munawar’s team built a prototype that automates two key parts of VEX creation:

* Identifying the vulnerable method(s) in a dependency.

* Tracing all possible paths from the application to the vulnerability.

This drastically reduces the time needed to analyze each new CVE. The human factor remains essential (at least until tools like CycloneDX Threat Models become fully automated), but the workload is now much more manageable.

# VEXes Come to Open Source

As of **July 2025**, we're excited to share that a new **VEX Initiative** has been launched by the **Alpha-Omega Fund**. It will release OpenRefactory's tooling under the `Apache-2.0` license and integrate it into Apache Solr workflows.

The goal: generate more accurate and timely VEX files. For example, the first CVE addressed—[**CVE-2025-48924**](https://www.cve.org/CVERecord?id=CVE-2025-48924) (an infinite recursion in a Commons Lang method)—was reported just days after the initiative started. The analysis showed Solr was *not* vulnerable, meaning users don’t need to rush to upgrade to the next release.

This is only the beginning. We aim to push this effort up the dependency chain—supporting not just Solr, but also projects like Log4j and Apache Commons. This collaborative model allows us to **distribute the effort**: both the computational workload of automated analysis and the human effort required to review, validate, and interpret the results.

By working together across projects, we can reduce duplication, increase accuracy, and accelerate the delivery of trustworthy VEX files—benefiting the entire open source ecosystem.

# What It Means for You

Under the EU’s **Cyber Resilience Act (CRA)**, commercial vendors must ensure that:

“Products with digital elements shall be made available on the market without known exploitable vulnerabilities.”

Improved VEX tooling and publishing open up two practical paths for meeting the requirements of the CRA:

1. **Patch your Solr installations** to use dependency versions that are free of known CVEs.

2. **Leverage the Apache Solr VEX file** to demonstrate to regulators that known vulnerabilities are *not exploitable* in your context.

If you choose the second approach—and you have internal insights into the exploitability of vulnerabilities in your open source–based products—**don’t keep that knowledge to yourself**. Contributing your findings upstream helps the broader ecosystem. By sharing what you’ve already analyzed, you enable other organizations to invest their resources into analyzing vulnerabilities in other OSS projects—possibly the same ones you rely on.

It's a win-win: stronger shared security, reduced duplication of effort, and a more resilient open source supply chain.

*Written by Piotr P. Karwasz. Edited by Charlie Bedard.*

> **Note**: The image at the top is generated by [Sora](https://openai.com/pl-PL/sora/). We used the following prompt: “Create an image for a blog post with the following title "How I Learned to Stop Worrying and Love the VEX" . Here VEX refers to the Vulnerability Exploitability eXchange document which is used to describe whether a vulnerability affects a downstream dependent application or not. Please use references from the Dr Strangelove movie while preparing the image.”
