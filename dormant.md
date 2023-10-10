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

### Dormant Projects

These are Logging Services Projects that have been deemed inactive since they have seen little recent
development activity or have reached end-of-life. If you wish to use any of these components, you must
build them yourselves. It is best to assume that these components will not be released in the near 
future.

<div class="projects">
    {% for project in site.data.projects %}
      {% if project.status == "dormant" %}
      <div class="project">
        <h2>{{project.name}}</h2>
        <p>{{project.description}}</p>
        <p><a target="_blank" class="btn" href="{{project.url}}">Project site &raquo;</a></p>
      </div>
      {% endif %}
    {% endfor %}      
</div>
