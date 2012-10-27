from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.plugincore import UnregisterEvent

class Plugin(Base):
    @Base.event("RPL_WELCOME")
    def on_notice(self, bot, command, prefix, params):
        try:
            conf = self.getConfig()
            nick = conf['general']['nickservnick']
            pass_ = conf['general']['nickservpass']
            
            if nick:
                bot.msg('NICKSERV', 'identify %s %s' % (nick, pass_))
        except KeyError:
            pass
        
        raise UnregisterEvent
    
    @Base.trigger("NICKSERVSET")
    def on_nsset(self, bot, user, details):
        """NICKSERVSET <nick> <pass> - Set the password to use for registering with nickserv at login"""
        if not user.hasPerm('nickserv.set'):
            raise InsuffPerms
        
        if len(details['splitmsg']) != 2:
            raise BadParams
        
        conf = self.getConfig()
        
        if not 'general' in conf:
            conf['general'] = {}
            
        conf['general']['nickservnick'] = details['splitmsg'][0]
        conf['general']['nickservpass'] = details['splitmsg'][1]
        
        conf.write()
        
        bot.msg('NICKSERV', 'identify %s %s' % (conf['general']['nickservnick'], 
                                                conf['general']['nickservpass']))
        
        return True