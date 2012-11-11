from socbot.pluginbase import Base, BadParams

class Plugin(Base):
    @Base.trigger("ADD")
    def on_add(self, bot, user, details):
        """ADD <trigger> <target> - makes <trigger> an alias for <target>"""
        user.assertPerm("aliases.add")
        
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        conf = self.getConfig()
        
        if not bot.name() in conf['general']:
            conf['general'][bot.name()] = {}
            
        aliases = conf['general'][bot.name()]
        aliases[details['splitmsg'][0].lower()] = " ".join(details['splitmsg'][1:])
        
        conf.write()
        
        return True
    
    @Base.trigger("LIST")
    def on_list(self, bot, user, details):
        """LIST - lists aliases"""
        conf = self.getConfig()
        
        if not bot.name() in conf['general']:
            return "No aliases are defined."
            
        aliases = conf['general'][bot.name()]
        keyvalues = []
        
        for key, value in aliases.iteritems():
            keyvalues.append("%s -> '%s'" % (key, value))
          
        return "Available aliases: %s" % ", ".join(keyvalues) 
    
    @Base.trigger("REM")
    def on_rem(self, bot, user, details):
        """REM <trigger> - removes the alias <trigger>"""
        user.assertPerm("aliases.remove")
        
        if not len(details['splitmsg']):
            raise BadParams
        
        conf = self.getConfig()
        
        if not bot.name() in conf['general']:
            return "No aliases are defined."
            
        aliases = conf['general'][bot.name()]
        trigger = details['splitmsg'][0].lower()
        
        if not trigger in aliases:
            return "That isn't an alias that I am aware of."
        
        del aliases[trigger]
        
        conf.write()
        
        return True
        
    @Base.msgprefilter(0)
    def pflt_alias(self, bot, user, details):
        conf = self.getConfig()
        
        if not bot.name() in conf['general']:
            return
        
        aliases = conf['general'][bot.name()]
        
        #details = {
        #    "fullmsg": msg,
        #    "fulluser": user,
        #    "splitmsg": split,
        #    "trigger": trigger.lower(),
        #    "channel": channel.lower(),
        #    "wasprivate": wasprivate
        #}
        
        if not details['trigger'].startswith("@PLUG") and details['trigger'].lower() in aliases:
            data = aliases[details['trigger'].lower()]
            msg = details['fullmsg']
            parts = msg.partition(" ")
            
            msg = "%s %s" % (data, parts[2])
            
            parts = msg.partition(" ")
            details['splitmsg'] = parts[2].split()
            details['trigger'] = parts[0].lower()
            details['fullmsg'] = msg
            