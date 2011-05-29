from collections import defaultdict
from datetime import datetime

from socbot.pluginbase import Base, BadParams

class UserInfo(object):
    def __init__(self):
        self.channels = defaultdict(dict)

    def update(self, channel, type, extra):
        channel = channel.lower()
        self.channels[channel]["type"] = type
        self.channels[channel]["extra"] = extra
        self.channels[channel]["timestamp"] = datetime.now()

    def seen(self, channel):
        return self.channels[channel.lower()]

    def seenLine(self, channel):
        chan = self.channels[channel.lower()]
        type = chan["type"].upper()
        time = chan["timestamp"]
        extra = chan["extra"]

        if type == "NICK":
            return "{0}: User changed nicks to {1}".format(time, extra)
        elif type == "JOIN":
            return "{0}: User joined {1}".format(time, channel)
        elif type == "PRIVMSG":
            return "{0}: User said: '{1}'".format(time, extra)
        elif type == "RPL_NAMREPLY":
            return "User was here when I joined"

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.userinfos = defaultdict(UserInfo)

    def enabled(self, *args, **kwargs):
        self.afterReload(*args, **kwargs)

    def afterReload(self, *args, **kwargs):
        sstate = self.manager.sstate

        for name, botlist in sstate["bots"].iteritems():
            for bot in botlist:
                for chan in bot.channels:
                    bot.sendLine('NAMES %s'%chan)

    @Base.event("RPL_NAMREPLY")
    def on_namreply(self, bot, command, prefix, params):
        mynick = params[0]
        modechar = params[1]
        channel = params[2]
        rawusers = params[3].lower()

        users = [nick.lstrip("~&@%+") for nick in rawusers.split()]

        for nick in users:
            user = self.userinfos[nick]
            user.update(channel.lower(), command.upper(), "Already here when I joined.")

    @Base.event("NICK", "PRIVMSG", "JOIN", "PART", "QUIT")
    def _updateseen(self, bot, command, prefix, params):
        nick = prefix.split("!")[0].lower()

        if command == "NICK":
            newnick = params[0].lower()

            self.userinfos[newnick] = self.userinfos[nick]
            del self.userinfos[nick]

            return

        if len(params) > 1:
            msg = params[1]
        else:
            msg = ""

        user = self.userinfos[nick]
        user.update(params[0], command.upper(), msg)

    @Base.trigger("SEEN")
    def on_seen(self, bot, user, details):
        """SEEN <nick> [<channel>] - report on when <nick> was last seen in <channel>. <channel> defaults to the current channel"""
        parts = details["splitmsg"]
        channel = details["channel"]
        command = details["trigger"]

        if parts:
            nick = parts.pop(0).lower()
        else:
            raise BadParams

        if parts:
            chan = parts.pop(0).lower()
        else:
            if details["wasprivate"]:
                return "You need to specify a channel!"
            else:
                chan = channel.lower()

        if parts:
            raise BadParams

        if not chan in bot.channels:
            return "I am not in {0}".format(chan)

        if not nick in self.userinfos:
            return "I don't know anything about {0}".format(nick)

        usr = self.userinfos[nick]

        return usr.seenLine(chan)
