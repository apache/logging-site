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
title: "Upgrade to Apache Commons Logging 1.3.0"
description: "Instructions to upgrade application to Apache Commons Logging 1.3.0."
tags:
  - Logging Services
  - Apache
  - Community
  - Open Source
type: post
---

# Apache Commons Logging

[Apache Commons Logging](https://commons.apache.org/proper/commons-logging/) (JCL) is one of the oldest Java logging APIs
available.
Released for the first time in 2002, it immediately saw a widespread adoption in the Java community.

While newer APIs, like SLF4J and our Log4j API, appeared over time, even in 2023 it is hard to find an application stack
that does not depend on JCL.
According to Sonatype, Apache Commons Logging is used in [over 1 million artifacts](https://central.sonatype.com/artifact/commons-logging/commons-logging),
while the second place is taken by SLF4J with [almost 40 thousand artifacts](https://central.sonatype.com/artifact/org.slf4j/slf4j-api).

## Version 1.3.0

After more than 9 years since its previous release (version 1.2 released in July 2014), Apache Commons Logging released
a new 1.3.0 version today (cf. [announcement]()).
Among the most prominent changes, the new version:

 * forwards logging to the Log4j API out-of-the-box (if present),
 * also supports forwarding to SLF4J,
 * adds support for the Java Platform Module System (JPMS) with the module name `org.apache.commons.logging`.

## Upgrade instructions

For Maven Apache Commons Logging the upgrade should be as simple as adding the new version to you dependency management:

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>commons-logging</groupId>
            <artifactId>commons-logging</artifactId>
            <version>1.3.0</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

Since version 1.2 only supported old generation logging backends out-of-the-box ([Log4j 1.x](https//logging.apache.org/log4j/1.2/),
[Avalon](https//avalon.apache.org) and [Lumberjack](https://javalogging.sourceforge.net)), the Java community developed
many `LogFactory` implementations and complete Apache Commons Logging replacements:

 * [`org.slf4j:jcl-over-slf4j`](https://mvnrepository.com/artifact/org.slf4j/jcl-over-slf4j) (replacement),
 * [`org.springframework:spring-jcl`](https://mvnrepository.com/artifact/org.springframework/spring-jcl) (replacement),
 * our own [`org.apache.logging.log4j:log4j-jcl`](https://mvnrepository.com/artifact/org.apache.logging.log4j/log4j-jcl)
   (`LogFactory` implementation).

These artifacts can be **safely** removed from your dependency stack.
For JPMS users this operation is **required**.
