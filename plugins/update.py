import os
import pastie
from twisted.internet.utils import getProcessOutput

from socbot.pluginbase import InsuffPerms, Base

class Plugin(Base):
    def preReload(self, *args, **kwargs):
        reload(pastie)
    
    @Base.hiddenTrigger("UPDATE")
    def on_update(self, bot, user, details):
        """UPDATE - attempt an update operation (using git pull)."""
        
        if not user.hasPerm("update.execute"):
            raise InsuffPerms, "update.execute"
        
        bot.msg(details['channel'], "Update process may take a while. Starting update...")
        
        HOME = os.path.expanduser("~")
        os.environ["HOME"] = HOME # Windows doesn't expose "HOME", causing git to fail
        
        conf = self.getConfig()
        git = conf['general']['git']
        out = getProcessOutput(git, ["pull",], os.environ)
        
        def doPaste(data):
            bot.msg(details['channel'], "Update success, sending results to pastebin...")
            return pastie.pastie(data, prefix="Update results: ")
        
        out.addCallback(doPaste)
        
        def doError(result):
            bot.msg(details['channel'], "Update error, sending results to pastebin...")
            return pastie.pastie(str(result), prefix="Update error: ")
        
        out.addErrback(doError)
        
        return out