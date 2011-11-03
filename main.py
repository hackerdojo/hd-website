#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

def _request(url, cache_ttl=3600, force=False):
    request_cache_key = 'request:%s' % url
    failure_cache_key = 'failure:%s' % url
    resp = memcache.get(request_cache_key)
    if force or not resp:
        try:
            resp = simplejson.loads(urlfetch.fetch(url).content[11:-3])
            memcache.set(request_cache_key, resp, cache_ttl)
            memcache.set(failure_cache_key, resp, cache_ttl*10)
        except (ValueError, urlfetch.DownloadError), e:
            # Not valid JSON or request timeout
            resp = memcache.get(failure_cache_key)
            if not resp:
                resp = {}
    return resp

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!')

class ContentHandler(webapp.RequestHandler):
    def get(self, page):
        skip_cache = self.request.get('cache') == '0'
        try:
            page = _request('https://shdh.pbworks.com/api_v2/op/GetPage/page/%s' % page, force=skip_cache)
            if page['folder'] != 'Website':
                raise LookupError()
            self.response.out.write(template.render('templates/content.html', locals()))
        except LookupError:
            self.error(404)

def main():
    application = webapp.WSGIApplication([('/', MainHandler), ('/(.+)', ContentHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

