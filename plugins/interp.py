import urllib2, urllib, json

import requests

from socbot.pluginbase import Base

class Plugin(Base):
    @Base.trigger("PY", "PYTHON")
    def on_python(self, bot, user, details):
        """PY <code> - run arbitrary python code (in an offsite sandboxed process)"""
        
        if not details['splitmsg']):
            raise BadParams
        
        code = " ".join(details['splitmsg'])
        
        try:
            result = requests.get("http://eval.appspot.com/eval", params=dict(statement=code, nick=user.nick)).content
        except Exception, e:
            return "Error querying the sandbox: %s" % e
        
        if result.startswith("Traceback (most recent call last):") and \
        len(result.splitlines()) > 1:
            return result.splitlines()[-1]
        
        if result:
            return "%s" % result
        
        return "No output."