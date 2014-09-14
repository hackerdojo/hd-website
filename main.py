#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import pytz
from datetime import datetime, timedelta
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.api import app_identity
from google.appengine.ext.webapp import util, template
import logging
import pprint
import urllib
import re
import json
import cloudstorage as gcs

PB_WIKI = 'dojowebsite'
PB_API_URL = 'http://%s.pbworks.com/api_v2/op/GetPage/page/%s'
CACHE_ENABLED = True
CDN_ENABLED = False
CDN_HOSTNAME = 'http://cdn.hackerdojo.com'
LOCAL_TZ = 'America/Los_Angeles'

reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|android|ipad|playbook|silk|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

#todo: test with actual cloud storage code
#google cloud storage according to documentation:
doc= "events.json"
FullFileUrl = "http://storage.googleapis.com/%s.appspot.com/%s/%s" \
    % (app_identity.get_application_id(),app_identity.get_default_gcs_bucket_name(),doc)

if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
    CACHE_ENABLED = False
    CDN_ENABLED = False
    #used to get from bucket in sdk:
    FullFileUrl = "http://localhost:10080/_ah/gcs/%s/%s" % (app_identity.get_default_gcs_bucket_name(),doc)

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

def _time(): #returns if hackerdojo is open; moved from IndexHandler
    utc_now = pytz.utc.localize(datetime.utcnow())
    local_now = utc_now.astimezone(pytz.timezone(LOCAL_TZ))
    hour = local_now.hour
    if hour > 8 and hour < 22:
        open = True
    else:
        open = False
    return open

def isMobile(self): #checks if browser is mobile; returns True or False
    #this is taken from http://detectmobilebrowsers.com/; no attribution needed, license is unlicense
    mobileRedirect = False
    user_agent = str(self.request.headers['User-Agent'])
    b = reg_b.search(user_agent)
    v = reg_v.search(user_agent[0:4])
    if b or v:
        mobileRedirect = True
    return mobileRedirect

def EventToList(): #converts json file to python list
    try: #get file from online storage location
        response = urllib.urlopen(FullFileUrl)
        data = json.load(response)
        logging.info("Done from storage")
    except: #gets json data live if corrupted or file does not exist in storage location
        response = urllib.urlopen('http://events.hackerdojo.com/events.json')
        data = json.load(response)
        logging.warning("JSON data not on storage")
    sep = '@' #used for stripping @hackerdojo.com
    num_days = 1 #set the amount of days of events it should get
    num_events = len(data)/4 #calculates 1/4 of the length of all events, so the speed is increased
    c = datetime.now(pytz.timezone(LOCAL_TZ)).date() #local date in LOCAL_TZ
    d = c + timedelta(days=num_days) #calculates todays date + num_days
    events2 = [list([]) for _ in xrange(num_events)] #empty events list to be filled in format [[event1][event2]]
    for i in range(num_events): #runs through the events
        #each event is [member,name of event,id,room,start time,date,status]
        b = datetime.strptime(data[i]['start_time'], '%Y-%m-%dT%H:%M:%S') #converts start_time to datetime format
        if (c <= b.date()) and (b.date() <= d):
            #only shows events on or after todays date and before or on todays date + num_days
            events2[i].append((data[i]['member']).encode('utf-8').split(sep, 1)[0]) #append member without @hackerdojo.com
            events2[i].append((data[i]['name']).encode('utf-8')) #append name of event
            events2[i].append(str(data[i]['id'])) #append id of event, which is for href
            if data[i]['rooms']: #checks if a room is specified, if not just returns empty string
                events2[i].append((data[i]['rooms'][0]).encode('utf-8'))
            else:
                events2[i].append(('').encode('utf-8'))
            events2[i].append((b.strftime("%I:%M%p")).encode('utf-8')) #appends time in 12 hr format
            events2[i].append((b.strftime("%A, %B %d")).encode('utf-8')) #appends day, month and day of the month
            events2[i].append((data[i]['status']).encode('utf-8')) #appends status of event
        elif (b.date() > d): #ends for loop to increase speed
            break
    events = [x for x in events2 if x != []] #cleans out any empty []
    return events

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

class UpdateHandler(webapp.RequestHandler):
    def get(self):
        try:
            _file = urllib.urlopen('http://events.hackerdojo.com/events.json')
            gcs_file_name = '/%s/%s' % (app_identity.get_default_gcs_bucket_name(), "events.json")
            data = json.load(_file)
            with gcs.open(gcs_file_name, 'w') as f:
                json.dump(data,f)
            logging.info("JSON File Updated")
        except:
             logging.warning("Failed to update JSON file")


class IndexHandler(webapp.RequestHandler):
    def get(self):
        #open = _time()
        mobileRedirect = isMobile(self)
        version = os.environ['CURRENT_VERSION_ID']
        if CDN_ENABLED:
            cdn = CDN_HOSTNAME
        if mobileRedirect == True: #checks if browser is mobile; else shows desktop site
            #a little latency from calling EventToList every time
            events = EventToList()
            self.response.out.write(template.render('templates/mobile/main_mobile.html', locals()))
        else:
            events = EventToList()
            self.response.out.write(template.render('templates/main_page.html', locals()))
            #self.response.out.write(template.render('templates/index.html', locals()))

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
        mobileRedirect = isMobile(self)

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
                    open = _time()
                    if mobileRedirect == True: #checks if browser is mobile; else shows desktop site
                        self.response.out.write(template.render('templates/mobile/content_mobile.html', locals()))
                    else:
                        self.response.out.write(template.render('templates/content.html', locals()))
                else:
                  raise LookupError
            except LookupError:
                version = os.environ['CURRENT_VERSION_ID']
                if CDN_ENABLED:
                    cdn = CDN_HOSTNAME
                open = _time()
                if mobileRedirect == True: #checks if browser is mobile; else shows desktop site
                        self.response.out.write(template.render('templates/mobile/404_mobile.html', locals()))
                        self.response.set_status(404)
                else:
                    self.response.out.write(template.render('templates/404.html', locals()))
                    self.response.set_status(404)



app = webapp.WSGIApplication([
    ('/api/pbwebhook', PBWebHookHandler),
    ('/api/event_staff', StaffHandler),
    ('/cron/eventjson', UpdateHandler),
    ('/', IndexHandler),
    ('/(.+)', MainHandler)],
    debug=True)
