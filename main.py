#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
import urllib
import re
import json

PB_WIKI = 'dojowebsite'
PB_API_URL = 'https://%s.pbworks.com/api_v2/op/GetPage/page/%s'
CACHE_ENABLED = True
CDN_ENABLED = False
CDN_HOSTNAME = 'http://cdn.hackerdojo.com'
LOCAL_TZ = 'America/Los_Angeles'

if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
    CACHE_ENABLED = False
    CDN_ENABLED = False

def _request(url, cache_ttl=3600, force=False):
    request_cache_key = 'request:%s' % url
    failure_cache_key = 'failure:%s' % url
    resp = memcache.get(request_cache_key)
    if force or not resp or not CACHE_ENABLED:
        try:
            data = urlfetch.fetch(url)
            if 'pbworks.com' in url:
                resp = json.loads(data.content[11:-3])
                if "html" in resp:
                    resp["html"] = re.sub("/w/page/\d*", "", resp["html"])
            else:
                resp = json.loads(data.content)
            memcache.set(request_cache_key, resp, cache_ttl)
            memcache.set(failure_cache_key, resp, cache_ttl*10)
        except (ValueError, urlfetch.DownloadError), e:
            resp = memcache.get(failure_cache_key)
            if not resp:
                resp = {}
    return resp

class PBWebHookHandler(webapp.RequestHandler):
    def post(self):
        page = self.request.get('page')
        if page:
            url = PB_API_URL % (PB_WIKI, urllib.pathname2url(page))
            request_cache_key = 'request:%s' % url
            failure_cache_key = 'failure:%s' % url
            memcache.delete(request_cache_key)
            memcache.delete(failure_cache_key)
        self.response.out.write("200 OK")

class IndexHandler(webapp.RequestHandler):
    def get(self):
        version = os.environ['CURRENT_VERSION_ID']
        if CDN_ENABLED:
            cdn = CDN_HOSTNAME
        self.response.out.write(template.render('templates/index.html', locals()))

class StaffHandler(webapp.RequestHandler):
    def get(self):
        staff = _request('http://hackerdojo-signin.appspot.com/staffjson')
        version = os.environ['CURRENT_VERSION_ID']
        if CDN_ENABLED:
            cdn = CDN_HOSTNAME
        self.response.out.write(template.render('templates/event_staff.html', locals()))

class MainHandler(webapp.RequestHandler):
    def get(self, pagename, site = PB_WIKI):
        skip_cache = self.request.get('cache') == '0'
        version = os.environ['CURRENT_VERSION_ID']
        shouldRedirect = False

        redirect_urls = {
          # From: To
          'give': 'Give',
          'auction': 'Auction',
          'Assemble': 'Give',
          'Mobile Device Lab': 'MobileDeviceLab',
          'kickstarter': 'http://www.kickstarter.com/projects/384590180/an-events-space-and-a-design-studio-for-hacker-doj',
          'Kickstarter': 'http://www.kickstarter.com/projects/384590180/an-events-space-and-a-design-studio-for-hacker-doj',
          'KICKSTARTER': 'http://www.kickstarter.com/projects/384590180/an-events-space-and-a-design-studio-for-hacker-doj',
          'key': 'http://signup.hackerdojo.com/key',
        }
        if pagename in redirect_urls:
            url = redirect_urls[pagename]
            self.redirect(url, permanent=True)
        else:
            if CDN_ENABLED:
                cdn = CDN_HOSTNAME
            try:
                pageKey = 'page:%s' % pagename.lower()
                if not(pagename):
                    pagename = 'FrontPage'
                page = _request(PB_API_URL % (site, pagename), cache_ttl=604800, force=skip_cache)
                # fetch a page where a lowercase version may exist
                if not(page and "name" in page):
                  if memcache.get(pageKey):
                    pagename = memcache.get(pageKey)
                    page = _request(PB_API_URL % (site, pagename), cache_ttl=604800, force=skip_cache)
                    shouldRedirect = True
                # Convert quasi-camel-case to spaced words
                title = re.sub('([A-Z])([A-Z][a-z])', r'\1 \2', pagename)
                title = re.sub('([a-z])([A-Z])', r'\1 \2', title)
                if page and "name" in page:
                  fiveDays = 432000
                  memcache.set(pageKey, pagename, fiveDays)
                  if shouldRedirect:
                    self.redirect(pagename, permanent=True)
                  else:
                    version = os.environ['CURRENT_VERSION_ID']
                    if CDN_ENABLED:
                        cdn = CDN_HOSTNAME
                    self.response.out.write(template.render('templates/content.html', locals()))
                else:
                  raise LookupError
            except LookupError:
                version = os.environ['CURRENT_VERSION_ID']
                if CDN_ENABLED:
                    cdn = CDN_HOSTNAME
                self.response.out.write(template.render('templates/404.html', locals()))
                self.response.set_status(404)



app = webapp.WSGIApplication([
    ('/api/pbwebhook', PBWebHookHandler),
    ('/api/event_staff', StaffHandler),
    ('/', IndexHandler),
    ('/(.+)', MainHandler)],
    debug=True)
