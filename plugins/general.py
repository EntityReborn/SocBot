from socbot.pluginbase import Base, InsuffPerms, BadParams, StopProcessing
from socbot.tools import isChannel

import datetime, fnmatch

class Plugin(Base):
    @Base.msgprefilter(0)
    def pflt_mignore(self, bot, user, details):
        conf = self.getConfig()
        
        ignores = conf['general'][bot.name()]['ignores']
        
        for ignore in ignores:
            if fnmatch.fnmatch(details['fulluser'].lower(), ignore.lower()) and \
                    not user.hasPerm('general.ignore.bypass'):
                raise StopProcessing
            
    @Base.eventprefilter(0)
    def pflt_eignore(self, bot, command, prefix, params):
        conf = self.getConfig()
        
        ignores = conf['general'][bot.name()]['ignores']
        user = bot.users.getUser(prefix.split("!")[0])
        
        for ignore in ignores:
            if fnmatch.fnmatch(prefix.lower(), ignore.lower()) and \
                    not user.hasPerm('general.ignore.bypass'):
                raise StopProcessing
            
    @Base.event("JOIN")
    def on_joined(self, bot, command, prefix, params):
        conf = self.getConfig()
        
        if not bot.name() in conf['general']:
            conf['general'][bot.name()] = {"ignores":[]}
            conf.write()
            
    @Base.trigger("IGNORE")
    def on_ignore(self, bot, user, details):
        """IGNORE [ADD|REM|LIST] - manipulate the list of ignores"""
        parts = details['splitmsg']
        if not parts:
            raise BadParams
        
        command = parts.pop(0).upper()
        conf = self.getConfig()
        
        if command == "LIST":
            if not conf['general'][bot.name()]['ignores']:
                return "Noone is ignored!"
            else:
                return ", ".join(conf['general'][bot.name()]['ignores'])
            
        elif command == "REM":
            if not user.hasPerm('general.ignore.remove'):
                raise InsuffPerms, "general.ignore.remove"
            
            if not len(parts):
                raise BadParams
            
            success = False
            
            for x in parts:
                try:
                    conf['general'][bot.name()]['ignores'].remove(x.lower())
                    success = True
                except ValueError:
                    pass
            
            conf.write()
            
            return True if success else "Not found."
                
        elif command == "ADD":
            if not user.hasPerm('general.ignore.add'):
                raise InsuffPerms, "general.ignore.add"
            
            if not len(parts):
                raise BadParams
            
            for x in parts:
                if not x.lower() in conf['general'][bot.name()]['ignores']:
                    conf['general'][bot.name()]['ignores'].append(x.lower())
            
            conf.write()
            
            return True
        
        raise BadParams
        
    @Base.trigger("PING")
    def on_ping(self, bot, user, details):
        """PING - Ask the bot to respond with 'Pong'"""
        return "Pong"
    
    @Base.trigger("NICK")
    def on_nick(self, bot, user, details):
        """NICK <newnick> - Request to change the bot's name"""
        if not user.hasPerm('general.nick'):
            raise InsuffPerms, "general.nick"
        
        if len(details['splitmsg']) != 1:
            raise BadParams
        
        bot.setNick(details['splitmsg'][0])
        
        return True
        
    @Base.trigger("MSG")
    def on_msg(self, bot, user, details):
        """MSG <target> <msg> - Send <msg> to <target>"""
        if not user.hasPerm('general.msg'):
            raise InsuffPerms, "general.msg"
        
        if not len(details['splitmsg']) > 1:
            raise BadParams
        
        target = details['splitmsg'][0]
        msg = " ".join(details['splitmsg'][1:])
        
        bot.msg(target, msg)
        
        return True
    
    @Base.trigger("RESTART")
    def on_restart(self, bot, user, details):
        """RESTART [message] - Ask the bot to restart"""
        
        if not user.hasPerm('general.restart'):
            raise InsuffPerms, "general.restart"
        
        if details['splitmsg']:
            bot.restart(' '.join(details['splitmsg']))
        else:
            bot.restart()
        
    @Base.trigger("SHUTDOWN", "DIAF")
    def on_shutdown(self, bot, user, details):
        """SHUTDOWN [message] - Ask the bot to shutdown"""
        
        if not user.hasPerm('general.shutdown'):
            raise InsuffPerms, "general.shutdown"
        
        if details['splitmsg']:
            bot.quit(' '.join(details['splitmsg']))
        else:
            bot.quit()
    
    @Base.trigger("BOTTIME")
    def on_bottime(self, bot, user, details):
        """BOTTIME - Ask the bot to respond with the time of it's computer"""
        return "The date and time is %s" % datetime.datetime.strftime(datetime.datetime.now(), '%c')

    @Base.trigger("COMMANDS")
    def on_commands(self, bot, user, details):
        """COMMANDS - Show commands known to the bot"""
        commands = ", ".join([x for x in self.manager.core.getAllTriggers() if x != "TRIG_UNKNOWN"])
        msg = "Commands I am aware of: {0}".format(commands)

        return msg
    
    @Base.trigger("HELP")
    def on_help(self, bot, user, details):
        """HELP [trigger] - Show help for a given trigger (See COMMANDS for valid triggers)"""
        if not details['splitmsg']:
            raise BadParams
        
        trigger = details['splitmsg'][0]
        
        func = self.manager.core.getTrigger(trigger)
        
        if not func:
            return "No such trigger (%s)" % trigger
        
        if not func.__doc__:
            return "This trigger does not have a help text associated with it."
        
        return func.__doc__ 
        
    @Base.trigger("JOIN")
    def on_join(self, bot, user, details):
        """JOIN <channel> [key] - Join a channel."""
        parts = details["splitmsg"]

        if not user.hasPerm('general.join'):
            raise InsuffPerms, "general.join"
        
        if parts:
            chan = parts.pop(0).lower()

            if parts:
                message = " ".join(parts)
            else:
                message = None

            bot.join(chan, message)
        else:
            raise BadParams

        return True
    
    @Base.trigger("PART", "LEAVE")
    def on_leave(self, bot, user, details):
        """PART <channel> [message] - Leave a channel."""
        parts = details["splitmsg"]

        if not user.hasPerm('general.part'):
            raise InsuffPerms, "general.part"
        
        if parts:
            if isChannel(parts[0]):
                chan = parts.pop(0)
            else:
                chan = details["channel"]

            if parts:
                message = " ".join(parts)
            else:
                message = None
        else:
            chan = details['channel']
            message = "Good-bye."
        
        if chan.lower() != bot.connection.nickname.lower():
            bot.leave(chan, message)
            return True
        
        return "Can't leave a PM!"
