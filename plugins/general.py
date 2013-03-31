from socbot.pluginbase import Base, BadParams, StopProcessing
from socbot.plugincore import MultipleTriggers, NoSuchTrigger, NoSuchTracker
from socbot.tools import isChannel

import datetime, fnmatch

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        conf = self.getConfig()
        
        if not 'ignores' in conf['general']:
            conf['general']['ignores'] = []
            conf.write()
            
    @Base.msgprefilter(0)
    def pflt_mignore(self, bot, user, details):
        conf = self.getConfig()
        
        ignores = conf['general']['ignores']
        
        for ignore in ignores:
            if fnmatch.fnmatch(details['fulluser'].lower(), ignore.lower()) and \
                    not user.hasPerm('general.ignore.bypass'):
                raise StopProcessing
            
    @Base.eventprefilter(0)
    def pflt_eignore(self, bot, command, prefix, params):
        conf = self.getConfig()
        
        ignores = conf['general']['ignores']
        user = bot.users.getUser(prefix.split("!")[0])
        
        for ignore in ignores:
            if fnmatch.fnmatch(prefix.lower(), ignore.lower()) and \
                    not user.hasPerm('general.ignore.bypass'):
                raise StopProcessing
            
    @Base.trigger("IGNORE")
    def on_ignore(self, bot, user, details):
        """IGNORE [ADD|REM|LIST] - manipulate the list of ignores"""
        parts = details['splitmsg']
        if not parts:
            raise BadParams
        
        command = parts.pop(0).upper()
        
        if command == "LIST":
            return self.ign_list(bot, parts)
        elif command == "REM":
            user.assertPerm('general.ignore.remove')
            return self.ign_rem(bot, parts)
                
        elif command == "ADD":
            user.assertPerm('general.ignore.add')
            return self.ign_add(bot, parts)
        
        raise BadParams
    
    def ign_add(self, bot, parts):
        if not len(parts):
            raise BadParams
        
        conf = self.getConfig()
            
        for x in parts:
            if not x.lower() in conf['general']['ignores']:
                conf['general']['ignores'].append(x.lower())
        
        conf.write()
        
        return True
    
    def ign_rem(self, bot, parts):
        if not len(parts):
            raise BadParams
        
        conf = self.getConfig()
        
        success = False
        
        for x in parts:
            try:
                conf['general']['ignores'].remove(x.lower())
                success = True
            except ValueError:
                pass
        
        conf.write()
        
        return True if success else "Not found."
    
    def ign_list(self, bot, parts):
        conf = self.getConfig()
        
        if not conf['general']['ignores']:
            return "Noone is ignored!"
        else:
            return ", ".join(conf['general']['ignores'])
        
    @Base.trigger("PING")
    def on_ping(self, bot, user, details):
        """PING - Ask the bot to respond with 'Pong'"""
        return "Pong"
    
    @Base.trigger("NICK")
    def on_nick(self, bot, user, details):
        """NICK <newnick> - Request to change the bot's name"""
        user.assertPerm('general.nick')
        
        if len(details['splitmsg']) != 1:
            raise BadParams
        
        bot.setNick(details['splitmsg'][0])
        
        return True
        
    @Base.trigger("MSG")
    def on_msg(self, bot, user, details):
        """MSG <target> <msg> - Send <msg> to <target>"""
        user.assertPerm('general.msg')
        
        if not len(details['splitmsg']) > 1:
            raise BadParams
        
        target = details['splitmsg'][0]
        msg = " ".join(details['splitmsg'][1:])
        
        bot.msg(target, msg)
        
        if target.lower() != details['channel'].lower():
            return True
    
    @Base.trigger("SAY")
    def on_say(self, bot, user, details):
        """SAY <msg> - Send <msg> to the current channel"""
        user.assertPerm('general.msg')
        
        if not len(details['splitmsg']):
            raise BadParams
        
        target = details['channel']
        msg = " ".join(details['splitmsg'])
        
        bot.msg(target, msg)
    
    @Base.trigger("RESTART")
    def on_restart(self, bot, user, details):
        """RESTART [message] - Ask the bot to restart"""
        user.assertPerm('general.restart')
        
        if details['splitmsg']:
            bot.restart(' '.join(details['splitmsg']))
        else:
            bot.restart()
        
    @Base.trigger("SHUTDOWN")
    def on_shutdown(self, bot, user, details):
        """SHUTDOWN [message] - Ask the bot to shutdown"""
        user.assertPerm('general.shutdown')
        
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
        commands = ", ".join(sorted([x.lower() for x in self.manager.core.getAllTriggers() if x != "TRIG_UNKNOWN"]))
        
        msg = "Commands I am aware of: {0}".format(commands)
        
        bot.msg(user.username(), msg)
        return "Please see the private message I sent you. (this helps keep channel spam down)"
    
    @Base.trigger("HELP")
    def on_help(self, bot, user, details):
        """HELP [trigger] - Show help for a given trigger (See COMMANDS for valid triggers)"""
        
        if not details['splitmsg']:
            raise BadParams
        
        trigger = details['splitmsg'].pop(0)
        
        try:
            tracker, func = self.manager.core.getTrigger(trigger)
        except MultipleTriggers as trigs:
            # Multiple triggers exist, lets list them to the user and die.
            plugs = [
                x[0].getName() for x in trigs.trackers
            ]
            
            s = "The command '%s' is defined in more than one plugin: %s." % (trigger.lower(), ", ".join(plugs))
            return s
        except NoSuchTrigger:
            func = None
            
        if not func:
            # No trigger found, lets see if there's a tracker (plugin) loaded with that name
            try:
                tracker = bot.plugins.getTracker(trigger)
            except NoSuchTracker:
                tracker = None
                
            if tracker:
                # Found a plugin with that name
                
                if details['splitmsg']:
                    # An argument was given, lets use it as a trigger to look for.
                    
                    trigger = details['splitmsg'].pop(0)
                    details['trigger'] = trigger
                    
                    try:
                        func = tracker.getTrigger(trigger)
                    except NoSuchTrigger:
                        s = "The plugin '%s' does not have the command '%s'." % (tracker.getName().capitalize(), trigger)
                        return s
                    
                else:
                    # Lets list the triggers this plugin has exposed publicly.
                    
                    trigs = [x.lower() for x in tracker.getTriggers()]
                    s = "The plugin '%s' has the following commands available: %s" % (tracker.getName(), ", ".join(trigs))
                    return s
                
            else:
                return "No such trigger (%s)" % trigger
        
        if not func.__doc__:
            return "This trigger does not have any help text associated with it."
        
        return func.__doc__ 
        
    @Base.trigger("JOIN")
    def on_join(self, bot, user, details):
        """JOIN <channel> [key] - Join a channel."""
        parts = details["splitmsg"]

        user.assertPerm('general.join')
        
        if parts:
            chan = parts.pop(0).lower()

            if parts:
                pass_ = " ".join(parts)
            else:
                pass_ = None

            bot.join(chan, pass_)
        else:
            raise BadParams

        return True
    
    @Base.trigger("CYCLE")
    def on_cycle(self, bot, user, details):
        """CYCLE [channel] - Leave then rejoin a channel."""
        
        parts = details["splitmsg"]

        user.assertPerm('general.cycle')
        
        if parts:
            channel = parts.pop(0)
        else:
            channel = details['channel']
        
        channel = channel.lower()
        
        bot.leave(channel, "Cycling.")
        
        config = bot.chanConfig(channel)
        
        if 'password' in config and config['password']:
            bot.join(channel, config['password'])
        else:
            bot.join(channel)
        
    @Base.trigger("LEAVE")
    def on_leave(self, bot, user, details):
        """LEAVE <channel> [message] - Leave a channel."""
        parts = details["splitmsg"]

        user.assertPerm('general.part')
        
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
