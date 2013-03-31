import json, urllib

from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, RedirectAgent
from twisted.web.http_headers import Headers
from zope.interface import implements
from twisted.web.iweb import IBodyProducer

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class DeferredPrinter(Protocol):
    def __init__(self, finished, prefix, postfix):
        self.finished = finished
        self.data = ""
        self.prefix = prefix
        self.postfix = postfix

    def dataReceived(self, b):
        self.data += b

    def connectionLost(self, reason):
        if "<title>503 Service Temporarily Unavailable</title>" in self.data:
            self.finished.callback("Looks like the pastebin server is down!")
            return
        
        try:
            j = json.loads(self.data)
        except ValueError, e:
            self.finished.callback("Could not parse data. (%s)" % e)
            return
        
        id_ = j['result']['id']
        hash_ = j['result']['hash']
        
        retn = "http://paste.thezomg.com/%s/%s/" % (id_, hash_)
        
        self.finished.callback(self.prefix + retn + self.postfix)
    
def pastie(data, prefix="", postfix="", user="Anonymous", lang="text", private="true", password=None):
    data = {
        'paste_user': user,
        'paste_data': data,
        'paste_lang': lang,
        'api_submit': 'true',
        'mode': 'json',
        'paste_private': private
    }
    
    if password:
        data['paste_password'] = password
    
    headers = {
        'User-agent': ['Mozilla/5.0',],
        'Content-type': ['application/x-www-form-urlencoded',],
    }
    
    agent = RedirectAgent(Agent(reactor))
    headers = Headers(headers)
    datz = urllib.urlencode(data)
    
    d = agent.request('POST', "http://paste.thezomg.com/", headers=headers, bodyProducer=StringProducer(datz))
    
    def cbRequest(response):
        finished = Deferred()
        response.deliverBody(DeferredPrinter(finished, prefix, postfix))
        return finished
    
    d.addCallback(cbRequest)
    
    return d