from socbot.pluginbase import Base, BadParams

import urllib2, json, re

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, RedirectAgent
from twisted.web.http_headers import Headers

class DeferredPrinter(Protocol):
    def __init__(self, finished, baseurl, num, template):
        self.finished = finished
        self.baseurl = baseurl
        self.num = num
        self.template = template
        self.data = ""

    def dataReceived(self, b):
        self.data += b

    def connectionLost(self, reason):
        if "<title>503 Service Temporarily Unavailable</title>" in self.data:
            self.finished.callback("Looks like the redmine server is down!")
            return
        
        try:
            j = json.loads(self.data)['issue']
        except ValueError, e:
            self.finished.callback("Could not parse data. (%s)" % e)
            return
            
        project = j['project']['name']
        author = j['author']['name']
        date = j['start_date']
        tracker = j['tracker']['name']
        status = j['status']['name']
        subject = j['subject']
        url = "%s/%s" % (self.baseurl, self.num)
        
        retn = self.template.format(
            project=project,
            author=author,
            date=date,
            tracker=tracker,
            status=status,
            subject=subject,
            url=url
        )
        
        self.finished.callback(retn)
        return

def getIssue(baseurl, num, template, conf):
    if baseurl.endswith("/"):
        baseurl = baseurl[:-1]
    
    cookiesession = conf['cookie']
    
    headers = {
        'User-agent': ['Mozilla/5.0',],
        "Cookie": [cookiesession,]
    }
    
    url = "%s/%s.json"%(baseurl, num)
    
    agent = RedirectAgent(Agent(reactor))
    headers = Headers(headers)
    d = agent.request('GET', url, headers=headers)
    
    def cbRequest(response):
        finished = Deferred()
        response.deliverBody(DeferredPrinter(finished, baseurl, num, template))
        
        return finished
    
    d.addCallback(cbRequest)
    return d

class Plugin(Base): # Must subclass Base
    @Base.trigger("REDURL")
    def on_seturl(self, bot, user, details):
        """REDURL <url> - Set the url to use when looking up issues in redmine"""
        user.assertPerm('redmine.seturl')
        
        conf = self.getConfig()
        
        if not details['splitmsg']:
            return conf['general']['redmineurl']
        
        if not 'general' in conf:
            conf['general'] = {}
            
        conf['general']['redmineurl'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
        return True
    
    @Base.trigger("REDPASSREGEX")
    def on_setregex(self, bot, user, details):
        """REDPASSREGEX <string> - Set the regex to use when passively looking up issues in redmine"""
        user.assertPerm('redmine.regex')
        
        conf = self.getConfig()
        
        if not details['splitmsg']:
            return conf['general']['passiveregex']
        
        if not 'general' in conf:
            conf['general'] = {}
            
        conf['general']['passiveregex'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
        return True
    
    @Base.trigger("REDADDTRIG")
    def on_add(self, bot, user, details):
        """REDADDTRIG <nick> - Add the user to be forced active output, even when passively triggering"""
        user.assertPerm('redmine.addtrig')
        
        if len(details['splitmsg']) != 1:
            raise BadParams
        
        conf = self.getConfig()
        
        if not 'activetriggerers' in conf['general']:
            conf['general']['activetriggerers'] = []
        
        if not details['splitmsg'][0] in conf['general']['activetriggerers']:
            conf['general']['activetriggerers'].append(details['splitmsg'][0])
            conf.write()
        
        return True
    
    @Base.trigger("REDREMTRIG")
    def on_del(self, bot, user, details):
        """REDREMTRIG <nick> - Remove the user to be forced active output, even when passively triggering"""
        user.assertPerm('redmine.remtrig')
        
        if len(details['splitmsg']) != 1:
            raise BadParams
        
        conf = self.getConfig()
        
        if not 'activetriggerers' in conf['general']:
            conf['general']['activetriggerers'] = []
        
        if details['splitmsg'][0] in conf['general']['activetriggerers']:
            conf['general']['activetriggerers'].remove(details['splitmsg'][0])
            conf.write()
        
        return True
    
    @Base.trigger("SETACTFMT")
    def on_setactfmt(self, bot, user, details):
        """SETACTFMT <string> - Set the template to use when triggering a lookup via the `bug` trigger"""
        user.assertPerm('redmine.setformat')
        
        if not details['splitmsg']:
            raise BadParams
        
        conf = self.getConfig()
            
        conf['general']['activeformat'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
        return True
    
    @Base.trigger("SETPASSFMT")
    def on_setpassfmt(self, bot, user, details):
        """SETPASSFMT <string> - Set the template to use when triggering a lookup when someone mentions #<id>"""
        user.assertPerm('redmine.setformat')
        
        if not details['splitmsg']:
            raise BadParams
        
        conf = self.getConfig()
            
        conf['general']['passiveformat'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
        return True
        
    @Base.trigger("ISSUE")
    def on_bug(self, bot, user, details):
        """ISSUE <id> - request link to redmine bug with id <id>"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        try:
            issueid = int(details['splitmsg'][0])
        except Exception:
            raise BadParams
        
        conf = self.getConfig()['general']
        url = conf['redmineurl']
        fmt = conf['activeformat']
        
        try:
            return getIssue(url, issueid, fmt, conf)
        except urllib2.HTTPError as e:
            if e.getcode() == 404:
                return "That bug/issue number does not exist!"
            else:
                return "Encountered %d error while fetching data." % e.getcode()
        
    @Base.event("PRIVMSG")
    def on_privmsg(self, bot, command, prefix, params):
        target = params[0]
        
        if target == bot.nick():
            target = prefix.split("!")[0]
            
        msg = params[1]
        conf = self.getConfig()['general']
        pat = conf['passiveregex']
        match = re.findall(pat, msg)
        url = conf['redmineurl']
        
        if match:
            if prefix.split("!")[0] in conf['activetriggerers']:
                fmt = conf['activeformat']
            else:
                fmt = conf['passiveformat']
                
            getIssue(url, match[0], fmt, conf).addCallback(bot.msg, target, True)