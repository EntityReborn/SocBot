import urllib2, urllib, json

from socbot.pluginbase import Base

class Plugin(Base):
    def getOutput(self, code, lang="python"):
        data = urllib.urlencode({
            'code': code,
            'lang': lang
        })
        
        resp = urllib2.urlopen("http://run-this.appspot.com/runthis", data)
        result = resp.read()
        data = json.loads(result)
            
        return data
    
    @Base.trigger("PY", "PYTHON")
    def on_python(self, bot, user, details):
        code = " ".join(details['splitmsg'])
        
        try:
            result = self.getOutput(code, 'python')
        except Exception, e:
            return "Error querying the sandbox: %s" % e
        
        if not "output" in result:
            return "Error: %s (%s)" % (result['stderr'].splitlines()[-1], result['link'])
        
        return "%s (%s)" % (result['output'].splitlines()[0], result['link'])
    
    @Base.trigger("OBJC")
    def on_objc(self, bot, user, details):
        code = " ".join(details['splitmsg'])
        
        try:
            result = self.getOutput(code, 'objc')
        except Exception, e:
            return "Error querying the sandbox: %s" % e
        
        if not "output" in result:
            return "Error: %s (%s)" % (result['stderr'].splitlines()[-1], result['link'])
        
        return "%s (%s)" % (result['output'].splitlines()[0], result['link'])
    

    