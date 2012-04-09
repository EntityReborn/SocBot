import urllib2, re
from bs4 import BeautifulSoup

from socbot.pluginbase import Base, BadParams
# Regex found at http://mathiasbynens.be/demo/url-regex (@diegoperini), and modified.
patt = ur"(?P<protocol>(?:https?|ftp)://)?(?:\S+(?::\S*)?@)?(?:(?!10(?:\.\d{1,3}){3})(?!127(?:\.\d{1,3}){3})(?!169\.254(?:\.\d{1,3}){2})(?!192\.168(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?"
urlpattern = re.compile(ur"^%s$"%patt, re.IGNORECASE)
titlepattern = re.compile(ur"(?P<url>%s)\w?"%patt, re.IGNORECASE)

class Plugin(Base):
    def initialize(self):
        self.bots = {} # bot: {channel: url, ...}, ...
        
    @Base.event("PRIVMSG")
    def on_privmsg(self, bot, command, prefix, params):
        if len(params) == 1:
            return
        
        said = params[1]
        channel = params[0]
        
        match = titlepattern.search(said)
        
        if match:
            url = match.group('url')
            pro = match.group('protocol')
            if not pro:
                url = "http://" + url
                
            if not bot in self.bots:
                self.bots[bot] = {}
                
            self.bots[bot][channel] = url
        
    @Base.trigger("TIT", "TITLE")
    def on_title(self, bot, user, details):
        if not len(details['splitmsg']):
            if not bot in self.bots:
                return "No URL has been said recently."
            
            if not details["channel"].lower() in self.bots[bot]:
                return "No URL has been said recently in this channel."
            
            url = self.bots[bot][details['channel']]
        else:
            url = details['splitmsg'][0]
            match = urlpattern.match(url)
            
            if not match:
                return "Oops, try a valid url!"
            
            pro = match.group('protocol')
            if not pro:
                url = "http://" + url

        try:
            page = urllib2.urlopen(url)
            page = page.read()
        except urllib2.HTTPError as e:
            return "Looks like that page has an error on it! (%s: %i)" % (url, e.code)
        except urllib2.URLError, e:
            return "There was an error retrieving the page's data. (%s: %s)" % (url, e)
        
        title = BeautifulSoup(page).title.string
        
        return "%s: %s" % (url, title)
        
    @Base.trigger("UP", "DOWN")
    def on_up(self, bot, user, details):
        if len(details['splitmsg']):
            url = details['splitmsg'][0]
            
            match = urlpattern.match(url)
            
            if not match:
                return "Oops, try a valid url!"
            
            pro = match.group('protocol')
            if not pro:
                url = "http://" + url
            
            try:
                _ = urllib2.urlopen(url, timeout=5)
            except urllib2.HTTPError as e:
                return "She's alive, but thats a %i! (%s)" % (e.code, url)
            except urllib2.URLError, e:
                return "She's dead, Jim! (%s)" % url
            
            return "Looks like she's alive! (%s)" % url
