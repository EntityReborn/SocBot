from socbot.pluginbase import Base
from socbot.tools import isChannel

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.registerTrigger(self.on_joinpart, "JOIN", "PART")
        self.registerTrigger(self.on_help, "HELP", "COMMANDS")

    def on_help(self, bot, user, channel, message, inprivate):
        """{HELP, COMMANDS} -  Show commands known to the bot"""
        commands = ", ".join([x for x in self.manager.triggers.keys() if x != "TRIG_UNKNOWN"])
        msg = "Commands I am aware of: {0}".format(commands)
        return msg

    def on_joinpart(self, bot, user, channel, message, inprivate):
        """{JOIN, PART} <channel> [<key or message>] - Join or leave a channel. """
        parts = message.split()
        command = parts.pop(0).lower()

        if not user.loggedIn():
            return "You need to log in first!"

        if not self.userHasPerm(user, command):
            return "You have insufficient privileges."

        if command == "join":
            if parts:
                chan = parts.pop(0).lower()

                if parts:
                    message = " ".join(parts)
                else:
                    message = None

                bot.join(chan, message)
            else:
                return self.on_joinpart.__doc__

            return "Done."

        elif command == "part":
            if parts:
                if isChannel(parts[0]):
                    chan = parts.pop(0)
                else:
                    chan = channel

                if parts:
                    message = " ".join(parts)
                else:
                    message = None
            else:
                return self.on_joinpart.__doc__

            bot.leave(chan, message)
        else:
            return self.on_joinpart.__doc__

        if channel.lower() == bot.nickname.lower():
            return "Done."
