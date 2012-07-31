from socbot.pluginbase import Base, BadParams, InsuffPerms

import urllib2, json, re
from cookielib import CookieJar

def getIssue(baseurl, num, template, conf):
    if baseurl.endswith("/"):
        baseurl = baseurl[:-1]

    jar = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
    
    cookiesession = conf['cookie']
    
    opener.addheaders = [
        ('User-agent', 'Mozilla/5.0'),
        ("Cookie", cookiesession)
    ]

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
    @Base.trigger("REDURL")
    def on_seturl(self, bot, user, details):
        """REDURL <url> - Set the url to use when looking up issues in redmine"""
        if not user.hasPerm('redmine.seturl'):
            raise InsuffPerms
        
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
        if not user.hasPerm('redmine.regex'):
            raise InsuffPerms
        
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
        if not user.hasPerm('redmine.addtrig'):
            raise InsuffPerms
        
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
        if not user.hasPerm('redmine.remtrig'):
            raise InsuffPerms
        
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
        if not user.hasPerm('redmine.setformat'):
            raise InsuffPerms
        
        if not details['splitmsg']:
            raise BadParams
        
        conf = self.getConfig()
            
        conf['general']['activeformat'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
        return True
    
    @Base.trigger("SETPASSFMT")
    def on_setpassfmt(self, bot, user, details):
        """SETPASSFMT <string> - Set the template to use when triggering a lookup when someone mentions #<id>"""
        if not user.hasPerm('redmine.setformat'):
            raise InsuffPerms
        
        if not details['splitmsg']:
            raise BadParams
        
        conf = self.getConfig()
            
        conf['general']['passiveformat'] = details['fullmsg'].partition(" ")[2]
        
        conf.write()
        
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
                
            for x in match:
                try:
                    bot.sendResult(getIssue(url, x, fmt, conf), target)
                except urllib2.HTTPError as e:
                    pass
                    #if e.code == 404:
                    #    bot.sendResult("The bug/issue number %s does not exist!" % x, target)
                    #else:
                    #    bot.sendResult("Encountered %d error while fetching data." % e.code, target)
                except ValueError as e:
                    bot.sendResult(r"Possible bad regex for passive redmine bug trigger. There should only be one captured group, capturing only digits. An example is (?:bugs?\s*)?#(\d+). The current is %s." % pat, target)
    