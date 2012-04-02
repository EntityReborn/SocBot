from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.tools import isChannel

class Plugin(Base):
    @Base.trigger("PING")
    def on_ping(self, bot, user, details):
        """PING - Ask the bot to respond with 'Pong'"""
        return "Pong!"

    @Base.trigger("HELP", "COMMANDS")
    def on_help(self, bot, user, details):
        """{HELP, COMMANDS} -  Show commands known to the bot"""
        commands = ", ".join([x for x in self.manager.triggers.keys() if x != "TRIG_UNKNOWN"])
        msg = "Commands I am aware of: {0}".format(commands)

        return msg

    @Base.trigger("JOIN")
    def on_join(self, bot, user, details):
        """JOIN <channel> [key] - Join a channel."""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not self.userHasPerm(user, 'general.join'):
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
        command = details["trigger"]

        if not self.userHasPerm(user, 'general.part'):
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
            message = "Bye!"
        
        if chan.lower() != bot.nickname.lower():
            bot.leave(chan, message)
            return False
        
        return "Can't leave a PM!"