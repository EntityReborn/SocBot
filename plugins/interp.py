import urllib2, urllib, json

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent

from socbot.pluginbase import BadParams, Base

class DeferredPrinter(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        if len(self.data) > 250:
            self.data = self.data[:247] + "..."
            
        if not self.data:
            self.data = "No output."
            
        if self.data.startswith("Traceback (most recent call last):") and \
        len(self.data.splitlines()) > 1:
            self.data = self.data.splitlines()[-1]
            
        self.finished.callback(self.data)

class Plugin(Base):
    @Base.trigger("PYTHON")
    def on_python(self, bot, user, details):
        """PYTHON <code> - run arbitrary python code (in an offsite sandboxed process)"""
        
        if not details['splitmsg']:
            raise BadParams
        
        code = " ".join(details['splitmsg'])
        data = urllib.urlencode({'statement':code})
        
        try:
            agent = Agent(reactor)

            d = agent.request(
                'GET', 
                'http://eval.appspot.com/eval?%s'%data
            )
            
            def cbRequest(response):
                finished = Deferred()
                response.deliverBody(DeferredPrinter(finished))
                return finished
            
            d.addCallback(cbRequest)
            return d
                
        except Exception, e:
            return "Error querying the sandbox: %s" % e