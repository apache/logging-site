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
  - Apache
  - Commmons Logging
  - Open Source
type: post
---

# Apache Commons Logging

[Apache Commons Logging](https://commons.apache.org/proper/commons-logging/) (JCL) is one of the oldest Java logging API
available.
Released for the first time in 2002, it immediately saw a widespread adoption in the Java community.

While newer APIs, like SLF4J and our own Log4j API, appeared over time, even in 2023 it is hard to find an application stack
that does not depend on JCL.
According to Sonatype, Apache Commons Logging is used in [over 1 million artifacts](https://central.sonatype.com/artifact/commons-logging/commons-logging),
while the second place is taken by SLF4J with [almost 40 thousand artifacts](https://central.sonatype.com/artifact/org.slf4j/slf4j-api).

## Version 1.3.0

After more than 9 years since its previous release (version 1.2 released in July 2014), Apache Commons Logging released
a new 1.3.0 version today (cf. [announcement](https://lists.apache.org/thread/wx6v7wwhbnk64nx708hszctzv8fdsvdl)).
Among the most prominent changes, the new version:

 * forwards logging to the Log4j API out-of-the-box (if present),
 * also supports forwarding to SLF4J,
 * adds support for the Java Platform Module System (JPMS) with the module name `org.apache.commons.logging`.

## Upgrade instructions (Log4j Core/Logback)

The upgrade path for users of the Log4j Core and Logback logging backends is easy.
The first step is upgrading `commons-logging`.
In Maven this can be done using dependency management.

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

The second step consists in removing obsolete dependencies.
Since version 1.2 only supported old generation logging backends out-of-the-box ([Log4j 1.x](https//logging.apache.org/log4j/1.2/),
[Avalon](https//avalon.apache.org) and [Lumberjack](https://javalogging.sourceforge.net)), the Java community developed
many `LogFactory` implementations and complete Apache Commons Logging replacements:

 * [`org.slf4j:jcl-over-slf4j`](https://mvnrepository.com/artifact/org.slf4j/jcl-over-slf4j) (replacement),
 * [`org.springframework:spring-jcl`](https://mvnrepository.com/artifact/org.springframework/spring-jcl) (replacement),
 * our own [`org.apache.logging.log4j:log4j-jcl`](https://mvnrepository.com/artifact/org.apache.logging.log4j/log4j-jcl)
   (`LogFactory` implementation).

These artifacts can be **safely** removed from your dependency stack.
For JPMS users this operation is even **required**.

To do so Maven users can use exclusions:

```xml
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-jcl</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework</groupId>
            <artifactId>spring-jcl</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

and to prevent regressions, add those dependencies to a [`bannedDependencies` Maven Enforcer rule](https://maven.apache.org/enforcer/enforcer-rules/bannedDependencies.html).

## Upgrade instructions (Log4j 1.x/Reload4j users)

For users that use Log4j 1.x or Reload4j as logging backend the upgrade is more complicated: version 1.3.0 disabled the Log4j 1.x backend by default.

Log4j 1.x/Reload4j users are:

 * encouraged to migrate to Log4j 2.x Core (cf. [migration guide](https://logging.apache.org/log4j/2.x/manual/migration.html)) or Logback,
 * if that is not possible (or if a transitional period is required) they need to add a `commons-logging.properties` file to their applications containing:

```
org.apache.commons.logging.Log = org.apache.commons.logging.impl.Log4JLogger
```

## JPMS users

The `org.apache.commons.logging` JPMS module has an **optional** dependency on the Log4j API.
In order for the JVM to automatically add the `org.apache.logging.log4j` module to your application's runtime, you need to add:

```
requires org.apache.logging.log4j;
```

to your application's module descriptor.

