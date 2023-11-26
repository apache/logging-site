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

layout: default
---

# Project Processes

### Apache Logging Services Project Processes/Checklists 

Here we describe some of the processes we use. 

  * Retire a subproject or component
  * Reactivate a subproject or component

### Retire a subproject or component 

The process starts by a format vote by the PMC on the main development mailing list.
Basically, we have to announce it and make resources read-only. 

  * Version Control
  * Issue Tracker
  * Announcement
  * Build Jobs
  * Landing Page
  * Homepage
  * Releases

#### Retire: Version Control 

Most of our source code is in git, only "site" and "sandbox" use GIT. 
We place a marker RETIRED_PROJECT file on the top level.
Add a note at the top of a README file as well so it is immediately visible 
to people browsing the GitHub mirror. Include a link to this page for a 
possible future reactivation and a link to the vote result.   
Ask infra to make the repository read-only. 

#### Retire: Issue Tracker 

If the subproject/component has its own issue tracker, we have to close that. 
It is enough to make it read-only, so these information are longer available.

#### Retire: Mailing List 

If the subproject/component has its own mailing list, we have to close this. 
We should send a final email. 

#### Retire: Announcement 

We have to announce the retirement of the subproject at dev@, users@
and the Logging blog main page. 

#### Retire: Move section of the landing page 

Move the project from the landing page to the "Dormant projects".

#### Retire: Homepage 

Add the retirement to the archive page. 

#### Retire: Releases 

The last released artifacts, if any, should be removed from the Apache 
distribution server. To do so, remove any artifact related to the retired 
subproject in dist.apache.org (it is managed with subversion). 
Note: as every Apache release, nothing is deleted but everything is archived, 
the artifacts will still be available at archive.apache.org 
(or for Incubator releases). 

### Reactivate a subproject or component 

The process starts by a format vote by the Ant PMC on the main development mailing list. Basically, we have to announce it and make resources read-write again. 

  * Version Control
  * Issue Tracker
  * Mailing List
  * Announcement
  * Build Jobs
  * Landing Page
  * Homepage
  * Releases

#### Reactivate: Version Control 

Delete the marker file "RETIRED_PROJECT".   
Delete the note at the top of a README file as well so it is 
immediately visible to people browsing the GitHub mirror.   
Ask infra to make the repository read-write again. 

#### Reactivate: Issue Tracker 

If the subproject/component has its own issue tracker, we have to reopen that. 

#### Reactivate: Mailing List 

Because reopening implies a smaller community, we should use the
main mailing list dev@. So reactivating a special list is not required 
and could be postponed to a later PMC decision. 

#### Reactivate: Announcement 

Announce the reactivation of the subproject at dev@. 

#### Reactivate: Build Jobs 

Build jobs, as required.

#### Reactivate: Move section of the landing page 

Move the project from the landing page from the "dormant projects" to 
the "active projects."

#### Reactivate: Homepage 

Remove the component from the archive page. 

#### Reactivate: Releases 

No action needed.
