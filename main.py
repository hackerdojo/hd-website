#!/usr/bin/env python

from django.utils import simplejson
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template
import logging

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
    def get(self, page):
        skip_cache = self.request.get('cache') == '0'
        try:
            if page:
                page = _request('https://hackerdojo.pbworks.com/api_v2/op/GetPage/page/%s' % page, force=skip_cache)
            self.response.out.write(template.render('templates/content.html', locals()))
        except LookupError:
            self.error(404)

def main():
    application = webapp.WSGIApplication([('/(.*)', MainHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

