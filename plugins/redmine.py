from socbot.pluginbase import Base, BadParams, InsuffPerms

import urllib2, json, re
from cookielib import CookieJar

from socbot.config import ConfigObj

def getIssue(baseurl, num, template="[ {project}/{tracker}/{status} ] \"{subject}\" by {author} on {date} ( {url} )"):
    if baseurl.endswith("/"):
        baseurl = baseurl[:-1]

    jar = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    
    opener.addheaders = [
        ('User-agent', 'Mozilla/5.0'),
        ("Cookie", r"_redmine_session=BAh7CDoMdXNlcl9pZGkCJQE6EF9jc3JmX3Rva2VuIjFQRnphL3JjbWlvMVFUL24wbFFSMEwxT3dzK3g0UGIrbGpjcTlqSy9kM3JJPToPc2Vzc2lvbl9pZCIlMzZiOTdmYWE4MWEyNzk3ZTg0YmYzOWYzNjUzMGQ4ZjU%3D--d9c610370deeec86e3ff051b7b2baa616357451c")
    ]
    print '%s/%s.json' % (baseurl, num)
    connection = opener.open('%s/%s.json' % (baseurl, num))

    data = connection.read()
    j = json.loads(data)['issue']
    
    project = j['project']['name']
    author = j['author']['name']
    date = j['start_date']
    tracker = j['tracker']['name']
    status = j['status']['name']
    subject = j['subject']
    url = "%s/%s" % (baseurl, num)
    
    return template.format(
        project=project,
        author=author,
        date=date,
        tracker=tracker,
        status=status,
        subject=subject,
        url=url
    )

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.conf = ConfigObj('conf/redmine.conf')
        
    @Base.trigger("REDURL")
    def on_seturl(self, bot, user, details):
        """REDURL <url> - Set the url to use when looking up issues in redmine"""
        
        if not user.hasPerm('redmine.seturl'):
            raise InsuffPerms
        
        if len(details['splitmsg']) != 1:
            raise BadParams
        
        self.conf.reload()
        
        if not 'general' in self.conf:
            self.conf['general'] = {}
            
        self.conf['general']['redmineurl'] = details['splitmsg'][0]
        
        self.conf.write()
        
        return True
    
    @Base.trigger("SETACTFMT")
    def on_setactfmt(self, bot, user, details):
        """SETACTFMT <string> - Set the template to use when triggering a lookup via the `bug` trigger"""
        
        if not user.hasPerm('redmine.setformat'):
            raise InsuffPerms
        
        if not details['splitmsg']:
            raise BadParams
        
        self.conf.reload()
        
        if not 'general' in self.conf:
            self.conf['general'] = {}
            
        self.conf['general']['activeformat'] = " ".join(details['splitmsg'])
        
        self.conf.write()
        
        return True
    
    @Base.trigger("SETPASSFMT")
    def on_setpassfmt(self, bot, user, details):
        """SETPASSFMT <string> - Set the template to use when triggering a lookup when someone mentions #<id>"""
        
        if not user.hasPerm('redmine.setformat'):
            raise InsuffPerms
        
        if not details['splitmsg']:
            raise BadParams
        
        self.conf.reload()
        
        if not 'general' in self.conf:
            self.conf['general'] = {}
            
        self.conf['general']['passiveformat'] = " ".join(details['splitmsg'])
        
        self.conf.write()
        
        return True
        
    @Base.trigger("BUG", "ISSUE")
    def on_bug(self, bot, user, details):
        """BUG <id> - request link to redmine bug with id <id>"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        try:
            issueid = int(details['splitmsg'][0])
        except Exception:
            raise BadParams
        
        url = self.conf['general']['redmineurl']
        fmt = self.conf['general']['activeformat']
        return getIssue(url, issueid, fmt)
        
    @Base.event("PRIVMSG")
    def on_privmsg(self, bot, command, prefix, params):
        target = params[0]
        if target == bot.nick():
            target = prefix.split("!")[0]
            
        msg = params[1]
        m = re.findall("(#(\d+))+", msg)
        
        url = self.conf['general']['redmineurl']
        fmt = self.conf['general']['passiveformat']
        
        if m:
            issues = [getIssue(url, x[1], fmt) for x in m]
            bot.sendResult(" ".join(issues), target)
                
        