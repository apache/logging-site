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

module Jekyll
  class YouTube < Liquid::Tag
    def initialize(tag_name, text, tokens)
      super
      @text = text.strip
    end

    def render(context)
      video_id, image_url = @text.split(' ')
      <<~HTML
        <div class="youtube-placeholder yt-container-#{video_id}" style="cursor: pointer;">
          <img src="#{image_url}" alt="Video thumbnail">
        </div>
        <div class="youtube-placeholder-description">
          Clicking on this image will load the video and send data from and to YouTube/Google.
        </div>
        <style>
          .youtube-placeholder {
            width: 560px; 
            height: auto;
          }
          .youtube-placeholder-description {
            color: gray;
            font-style: italic;
          }
        </style>
        <script>
          document.addEventListener('DOMContentLoaded', function() {
            var container = document.querySelector('.yt-container-#{video_id}');
            function addElement() {
              var iframe = document.createElement('iframe');
              iframe.setAttribute('width', '560');
              iframe.setAttribute('height', '315');
              iframe.setAttribute('src', 'https://www.youtube-nocookie.com/embed/#{video_id}?autoplay=1');
              iframe.setAttribute('title', 'YouTube video player');
              iframe.setAttribute('frameborder', '0');
              iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
              iframe.setAttribute('allowfullscreen', '');
              container.innerHTML = '';
              container.appendChild(iframe);
            }
            container.addEventListener('click', addElement);
          });
        </script>
      HTML
    end
  end
end

Liquid::Template.register_tag('youtube', Jekyll::YouTube)
