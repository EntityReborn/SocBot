import os
import pastie
from twisted.internet.utils import getProcessOutputAndValue

from socbot.pluginbase import Base

class Plugin(Base):
    def preReload(self, *args, **kwargs):
        reload(pastie)
    
    @Base.hiddenTrigger("UPDATE") 
    def on_update(self, bot, user, details):
        """UPDATE - attempt an update operation (using git pull)."""
        user.assertPerm("update.execute")
        
        bot.msg(details['channel'], "Update process may take a while. Starting update...")
        
        HOME = os.path.expanduser("~")
        os.environ["HOME"] = HOME # Windows doesn't expose "HOME", causing git to fail
        
        conf = self.getConfig()
        git = conf['general']['git']
        
        path = bot.connection.factory.sharedstate['basedir']
        
        out = getProcessOutputAndValue(git, ["pull",], os.environ, path=path)
        
        def doPaste(data):
            stdout, stderr, exitcode = data
            
            if exitcode == 0:
                tag = "Success!"
            else:
                tag = "Error!"
                
            bot.msg(details['channel'], tag + " Sending update results to pastebin...")
            dat = """SocBot Update Report (%s)
STDOUT:
%s
STDERR:
%s
Exit code: %d""" % (tag, stdout, stderr, exitcode)
                
            return pastie.pastie(dat, prefix="Update results: ")
        
        out.addCallback(doPaste)
        
        return out