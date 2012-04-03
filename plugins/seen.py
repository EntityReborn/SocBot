from collections import defaultdict
from datetime import datetime

from socbot.pluginbase import Base, BadParams

import pastie

class UserInfo(object):
    def __init__(self):
        self.channels = defaultdict(dict)
        self.bot = None
        self.nick = ""
        self.tellmsgs = list()

    def update(self, channel, type, extra):
        channel = channel.lower()
        self.channels[channel]["type"] = type
        self.channels[channel]["extra"] = extra
        self.channels[channel]["timestamp"] = datetime.now()
        
        if not type in ["QUIT", "JOIN"]:
            tosend = list()
                
            for msgdata in self.tellmsgs:
                time = datetime.strftime(msgdata['date'], '%c')
                text = "{0} in {1} asked to tell you the following: {2} ({3})".format(
                    msgdata['from'].nick, msgdata['channel'], msgdata['text'], time)
                tosend.append(text)
            
            if tosend:
                if not len(tosend) > 4:
                    for text in tosend:
                        self.bot.msg(self.nick, text)
                else:
                    tosend = ["Things people wanted you to know:",] + tosend + \
                        ['(It is currently %s)' % datetime.strftime(datetime.now(), '%c')]
                    url = pastie.pastie("\n".join(tosend))
                    self.bot.msg(self.nick, "Please check out %s for a list of things people wanted to tell you." % url)
                    
                self.tellmsgs = list()

    def seen(self, channel):
        return self.channels[channel.lower()]

    def seenLine(self, channel):
        chan = self.channels[channel.lower()]
        type = chan["type"].upper()
        time = chan["timestamp"]
        extra = chan["extra"]

        time = datetime.strftime(time, '%c')
        if type == "NICK":
            return "{0}: User changed nicks to {1}".format(time, extra)
        elif type == "JOIN":
            return "{0}: User joined {1}".format(time, channel)
        elif type == "PRIVMSG":
            
            if extra.startswith('\x01'):
                return "{0}: User did an action: '{1}'".format(time, extra[8:-1])
            return "{0}: User said: '{1}'".format(time, extra)
        elif type == "RPL_NAMREPLY":
            return "User was here when I joined."
        elif type == "QUIT":
            return "User quit."
        elif type == "PART":
            return "User left the channel."
        
        return "I don't know what this user did last!"

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
            user.bot = bot
            user.nick = nick
            user.update(channel.lower(), command.upper(), "Already here when I joined.")

    @Base.event("NICK", "PRIVMSG", "JOIN", "PART", "QUIT")
    def _updateseen(self, bot, command, prefix, params):
        nick = prefix.split("!")[0].lower()

        if command == "NICK":
            newnick = params[0].lower()

            self.userinfos[newnick] = self.userinfos[nick]
            self.userinfos[newnick].nick = newnick
            del self.userinfos[nick]
            nick = newnick

        if len(params) > 1:
            msg = params[1]
        else:
            msg = ""

        user = self.userinfos[nick]
        user.bot = bot
        user.update(params[0], command.upper(), msg)

    @Base.trigger("TELL")
    def on_tell(self, bot, user, details):
        """TELL <nick> <text> - tell a user something when they are next seen"""
        parts = details["splitmsg"]
        channel = details["channel"]
        
        if len(parts) >= 2:
            data = {
                'channel': details['channel'], 
                'text': " ".join(parts[1::]),
                'from': user,
                'date': datetime.now()
            }
            
            self.userinfos[parts[0].lower()].tellmsgs.append(data)
            
            return "I'll let them know!"
        
        raise BadParams

    @Base.trigger("SEEN")
    def on_seen(self, bot, user, details):
        """SEEN <nick> [channel] - report on when <nick> was last seen in <channel>. <channel> defaults to the current channel"""
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
