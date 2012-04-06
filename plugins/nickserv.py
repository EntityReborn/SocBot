from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.config import ConfigObj

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.conf = ConfigObj('conf/nickserv.conf')
        pass
        
    @Base.event("RPL_WELCOME")
    def on_welcome(self, bot, command, prefix, params):
        try:
            bot.msg('NICKSERV', 'identify %s %s' % (bot.nickname, self.conf['general']['nickservpass']))
        except KeyError:
            pass
    
    @Base.trigger("NICKSERVSET")
    def on_nsset(self, bot, user, details):
        """NICKSERVSET <nick> <pass> - Set the password to use for registering with nickserv at login"""
        if not user.hasPerm(user, 'nickserv.set'):
            raise InsuffPerms
        
        if len(details['splitmsg']) != 2:
            raise BadParams
        
        self.conf.reload()
        
        if not 'general' in self.conf:
            self.conf['general'] = {}
            
        self.conf['general']['nickservnick'] = details['splitmsg'][0]
        self.conf['general']['nickservpass'] = details['splitmsg'][1]
        
        self.conf.write()
        
        bot.msg('NICKSERV', 'identify %s %s' % (self.conf['general']['nickservnick'], 
                                                self.conf['general']['nickservpass']))
        
        return True