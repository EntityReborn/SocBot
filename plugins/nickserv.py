from socbot.pluginbase import Base, BadParams

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
    
    @Base.trigger("SET")
    def on_nsset(self, bot, user, details):
        """SET <nick> <pass> - Set the password to use for registering with nickserv at login"""
        user.assertPerm('nickserv.set')
        
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
    
    @Base.trigger("IDENTIFY")
    def on_id(self, bot, user, details):
        """IDENTIFY - identify with nickserv manually"""
        user.assertPerm('nickserv.identify')
        
        conf = self.getConfig()
        
        if not 'general' in conf:
            return "This plugin isn't set up to identify with nickserv on this network."
        
        bot.msg('NICKSERV', 'identify %s %s' % (conf['general']['nickservnick'], 
                                                conf['general']['nickservpass']))
        
        return True