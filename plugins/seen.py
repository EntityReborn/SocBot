from collections import defaultdict
from datetime import datetime

from socbot.pluginbase import Base

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

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.registerTrigger(self.on_seen, "SEEN")
        
        self.registerEvent(self._updateseen, "IRC_NICK", "IRC_PRIVMSG", "IRC_JOIN"
            "IRC_PART", "IRC_QUIT")
        self.registerEvent(self.on_namreply, "IRC_RPL_NAMREPLY")

        self.userinfos = defaultdict(UserInfo)

    def enabled(self, *args, **kwargs):
        self.afterReload(*args, **kwargs)

    def afterReload(self, *args, **kwargs):
        sstate = self.manager.sstate

        for name, botlist in sstate["bots"].iteritems():
            for bot in botlist:
                for chan in bot.channels:
                    bot.sendLine('NAMES %s'%chan)

    def on_namreply(self, bot, command, prefix, params):
        mynick = params[0]
        modechar = params[1]
        channel = params[2]
        rawusers = params[3].lower()
        
        users = [nick.lstrip("~&@%+") for nick in rawusers.split()]

        for nick in users:
            user = self.userinfos[nick]
            user.update(channel.lower(), command.upper(), "Present at my jointime")

    def _updateseen(self, bot, command, prefix, params):
        nick = prefix.split("!")[0].lower()

        if command == "IRC_NICK":
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

    def on_seen(self, bot, user, channel, message, inprivate):
        """SEEN <nick> [<channel>] - report on when <nick> was last seen in <channel>. <channel> defaults to the current channel"""
        parts = message.lower().split()

        if len(parts) >= 2:
            nick = parts[1]
        else:
            bot.msg(channel, self.on_seen.__doc__)
            return

        if len(parts) >= 3:
            chan = parts[2]
        else:
            if inprivate:
                bot.msg(channel, "You need to specify a channel")
                return
            else:
                chan = channel.lower()


        if not chan in bot.channels:
            bot.msg(channel, "I am not in {0}".format(chan))
            return

        if not nick in self.userinfos:
            bot.msg(channel, "I don't know anything about {0}".format(nick))
            return

        usr = self.userinfos[nick]
        data = usr.seen(chan)

        line = "Type: {0}, Data: {1}, Time: {2}".format(data["type"], data["extra"], str(data["timestamp"]))
        bot.msg(channel, line)
