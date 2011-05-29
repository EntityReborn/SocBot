from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.tools import isChannel

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.registerTrigger(self.on_ping, "PING")
        self.registerTrigger(self.on_joinpart, "JOIN", "PART")
        self.registerTrigger(self.on_help, "HELP", "COMMANDS")

    def on_ping(self, bot, user, details):
        """PING - Ask the bot to respond with 'Pong'"""
        return "Pong"

    def on_help(self, bot, details):
        """{HELP, COMMANDS} -  Show commands known to the bot"""
        commands = ", ".join([x for x in self.manager.triggers.keys() if x != "TRIG_UNKNOWN"])
        msg = "Commands I am aware of: {0}".format(commands)

        return msg

    def on_joinpart(self, bot, user, details):
        """{JOIN, PART} <channel> [<key or message>] - Join or leave a channel. """
        parts = details["splitmsg"]
        command = parts.pop(0).lower()

        if not self.userHasPerm(user, command):
            raise InsuffPerms, "general."+command

        if command == "join":
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

        elif command == "part":
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
                raise BadParams

            bot.leave(chan, message)
        else:
            raise BadParams

        if details["channel"].lower() == bot.nickname.lower():
            return True
