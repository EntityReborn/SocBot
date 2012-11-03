import urllib2, re
from bs4 import BeautifulSoup

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, RedirectAgent

titlepattern = re.compile(r"\b(?P<pro>https?://)(?P<url>.*?\.[-A-Z0-9+&@#/%=~_|$?!:,.]*[A-Z0-9+&@#/%=~_|$])", re.IGNORECASE)

from socbot.pluginbase import Base, BadParams

class DeferredPrinter(Protocol):
    def __init__(self, finished, url):
        self.finished = finished
        self.url = url
        self.data = ""

    def dataReceived(self, b):
        self.data += b

    def connectionLost(self, reason):
        title = BeautifulSoup(self.data).title
        
        if title:
            title = title.string
        else:
            title = "No title provided."
            
        self.finished.callback("%s (%s)" % (title.strip(), self.url))

class Plugin(Base):
    def initialize(self):
        self.bots = {} # bot: {channel: url, ...}, ...
        
    @Base.event("PRIVMSG")
    def on_privmsg(self, bot, command, prefix, params):
        if len(params) == 1:
            return
        
        said = params[1]
        channel = params[0].lower()
        
        match = titlepattern.search(said)
        
        if match:
            url = match.group('url')
            pro = match.group('pro')
            
            if not pro:
                url = "http://" + url
            else:
                url = pro + url
                
            if not bot in self.bots:
                self.bots[bot] = {}
                
            self.bots[bot][channel] = url
        
    @Base.trigger("TITLE")
    def on_title(self, bot, user, details):
        """TITLE [url] - If provided, prints the title of url. If not, prints the title of the last mentioned url."""
        if not len(details['splitmsg']):
            if not bot in self.bots:
                return "No URL has been said recently."
            
            if not details["channel"].lower() in self.bots[bot]:
                return "No URL has been said recently in this channel."
            
            url = self.bots[bot][details['channel'].lower()]
        else:
            url = details['splitmsg'][0]
            
            match = titlepattern.match(url)
            
            if not match:
                url = "http://" + url
                match = titlepattern.match(url)
            
            if not match:
                return "Oops, try a valid url!"

        try:
            agent = RedirectAgent(Agent(reactor))
            d = agent.request('GET', url)
            
            def cbRequest(response):
                finished = Deferred()
                response.deliverBody(DeferredPrinter(finished, url))
                return finished
            
            d.addCallback(cbRequest)
            return d
        
        except urllib2.HTTPError as e:
            return "Looks like that page has an error on it! (%s: %i)" % (url, e.code)
        except urllib2.URLError, e:
            return "There was an error retrieving the page's data. (%s: %s)" % (url, e)
        
    @Base.trigger("ISUP")
    def on_up(self, bot, user, details):
        """ISUP http://<url> - Check to see if the webserver at url is up and kicking."""
        if len(details['splitmsg']):
            url = details['splitmsg'][0]
            
            match = titlepattern.match(url)
            
            if not match:
                url = "http://" + url
                match = titlepattern.match(url)
                
            if not match:
                return "Oops, try a valid url!"
            
            agent = Agent(reactor)
            d = agent.request('GET', url)
            
            d.addCallback(lambda *x: "She's alive! (%s)" % url)
            d.addErrback(lambda *x: "She's dead, Jim. :( (%s)" % url)
            
            return d
        else:
            raise BadParams
