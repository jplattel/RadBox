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
import os
import urllib 
import re
import time
from time import mktime
from datetime import datetime
from datetime import date
from xml.dom import minidom
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db

class Video(db.Model):
    title = db.StringProperty()
    pubdate = db.StringProperty()
    url = db.StringProperty()
    url_radbox = db.StringProperty()
    date_added = db.DateTimeProperty()
    watched = db.BooleanProperty()
    
        
def RadBoxId(url):
    regex = re.compile("[0-9].*")
    r = regex.search(url)
    id = regex.findall(url)
    return id    
    
class MainHandler(webapp.RequestHandler):
    def get(self):
        content = []
        
        request_url = 'http://radbox.me/feed/video/home/c2d91689d2ebd9bf0d973a890d536e6f' #add apikey after the last slash
        
        result = urlfetch.fetch(request_url)
        if result.status_code == 200:
            result = result.content.replace('&laquo;', '')
            result = result.replace('&raquo;', '')
            
            last_id = datetime(2010, 12, 5)
            videos = db.GqlQuery("SELECT * FROM Video ORDER BY date_added DESC LIMIT 1")
            for video in videos:
                last_id = video.date_added
                
            dom = minidom.parseString(result)
            
            for node in dom.getElementsByTagName('item'):
                
                item_id = node.getElementsByTagName('pubDate')[0].firstChild.data
                item_id = item_id.replace(' EST', '')
                item_id = item_id.replace('Mon, ', '')
                item_id = item_id.replace('Tue, ', '')
                item_id = item_id.replace('Wed, ', '')
                item_id = item_id.replace('Thu, ', '')
                item_id = item_id.replace('Fri, ', '')
                item_id = item_id.replace('Sat, ', '')
                item_id = item_id.replace('Sun, ', '')

                item_id = time.strptime(item_id, "%d %b %Y %H:%M:%S")
                item_id = datetime.fromtimestamp(mktime(item_id))
                
                if item_id > last_id:
                    try: #try if the media:content is available to save
                        v = Video()
                        v.title = node.getElementsByTagName('title')[0].firstChild.data
                        v.pubdate = node.getElementsByTagName('pubDate')[0].firstChild.data
                        v.url = node.getElementsByTagName('media:content')[0].getAttribute('url')
                        v.url_radbox = node.getElementsByTagName('link')[0].firstChild.data
                        v.date_added = item_id
                        v.watched = False
                        v.put()
                    except: #if not available the save the url as empty and use and iframe for display
                        v = Video()
                        v.title = node.getElementsByTagName('title')[0].firstChild.data
                        v.pubdate = node.getElementsByTagName('pubDate')[0].firstChild.data
                        v.url = ''
                        v.date_added = item_id
                        v.url_radbox = node.getElementsByTagName('link')[0].firstChild.data
                        v.watched = False
                        v.put()
                else:
                    break
                    

        
        self.redirect('/')
   
   
class VideoList(webapp.RequestHandler):
    def get(self, offset):    
        offset = int(offset)
        
        #build the urls for next/previous pages
        next = offset + 1
        next = '/video/' + str(next) + '/'
        
        previous = offset - 1
        if previous < 0:
            previous = '#'
        else:
            previous = '/video/' + str(previous) + '/'
        
        content = []
        titles = []
        videos = db.GqlQuery("SELECT * FROM Video WHERE watched = False ORDER BY pubdate DESC LIMIT 100")
        for video in videos:
            if video.url == '':
                url = video.url_radbox
                html = '<iframe class="frame" src="' + url + '" width="1024" height="728"><p>Your browser does not support iframes.</p></iframe>'
                content.append(html)
                video.title = '<a class="remove" href="/mark-as-watched/' + RadBoxId(video.url_radbox)[0] + '">&#215;</a> ' + video.title
                titles.append(video.title)
            else:                 
                url = video.url
                html = '<object width="1024" height="728"><param name="movie" value="' + url + '"></param><param name="allowFullScreen" value="true"></param><param name="allowscriptaccess" value="always"></param><embed src="' + url + '" type="application/x-shockwave-flash" allowscriptaccess="always" allowfullscreen="true" width="1024" height="728"></embed></object>'
                content.append(html)   
                video.title = '<a class="remove" href="/mark-as-watched/' + RadBoxId(video.url_radbox)[0] + '">&#215;</a> ' + video.title
                titles.append(video.title)
        try:
            content = content.pop(offset)
        except:
            content = '<div class="end">You\'ve seen all footage!</div>'
           
        try:
            title = titles.pop(offset)
        except:
            title = 'The end!'
            
        template_values = {
            'content': content,
            'previous': previous,
            'next': next,
            'offset': offset,
            'title': title,
            }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

        
         
class MarkAsWatched(webapp.RequestHandler):
    def get(self ,url_radbox): 
        
        url_radbox = 'http://radbox.me/watch/video/' + str(url_radbox)
        videos = db.GqlQuery("SELECT * FROM Video WHERE url_radbox =:1 ORDER BY pubdate DESC LIMIT 2", url_radbox)
        for video in videos:
            video.watched = True
            title = video.title
            video.put()
            
        
        self.redirect('/')
        
        
class VideoRedirect(webapp.RequestHandler):
    def get(self): 
        self.redirect('/video/0/')
        
class Archives(webapp.RequestHandler):
    def get(self): 
        
        video_id = 0
        videolist = []
        videos = db.GqlQuery("SELECT * FROM Video WHERE watched = False ORDER BY pubdate DESC LIMIT 100")
        for video in videos:
            item = []
            item.append(video.title)
            item.append(video_id)
            item.append(video.url_radbox)
            if video.watched == False:
                link = '<a class="remove" href="/mark-as-watched/' + RadBoxId(video.url_radbox)[0] + '">&#215;</a>&nbsp; '
                item.append(link)
            videolist.append(item)
            video_id = video_id + 1
            
        videolist.sort()    
        videolist.reverse() 
        
        template_values = {
            'videolist': videolist,
            }

        path = os.path.join(os.path.dirname(__file__), 'archives.html')
        self.response.out.write(template.render(path, template_values))
        
        
        
def main():
    application = webapp.WSGIApplication([('/radbox/fetch/', MainHandler),
                                          ('/video/(.*)/', VideoList),
                                          ('/video/', VideoRedirect),
                                          ('/mark-as-watched/(.*)', MarkAsWatched),
                                          ('/', Archives),
    
                                            ],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
