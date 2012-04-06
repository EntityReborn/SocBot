from collections import defaultdict
import datetime, re

from socbot.pluginbase import Base, BadParams
from socbot.config import ConfigObj

import pastie, seenbase

class UserInfo(object):
    def __init__(self):
        self.channels = defaultdict(dict)
        self.bot = None
        self.nick = ""
        self.tellconfig = {}

    def update(self, channel, type, extra):
        channel = channel.lower()
        self.channels[channel]["type"] = type
        self.channels[channel]["extra"] = extra
        self.channels[channel]["timestamp"] = datetime.datetime.now()
        
        if not type in ["QUIT", "JOIN", "RPL_NAMREPLY"]:
            tosend = list()
                
            for data in self.tellconfig[self.nick]:
                msgdata = eval(data)
                time = datetime.datetime.strftime(msgdata['date'], '%c')
                text = "{0} in {1} asked to tell you the following: {2} ({3})".format(
                    msgdata['from'], msgdata['channel'], msgdata['text'], time)
                tosend.append(text)
            
            if tosend:
                if not len(tosend) > 4:
                    for text in tosend:
                        self.bot.msg(self.nick, text)
                else:
                    tosend = ["Things people wanted you to know:",] + tosend + \
                        ['(It is currently %s)' % datetime.datetime.strftime(datetime.datetime.now(), '%c')]
                    url = pastie.pastie("\n".join(tosend))
                    self.bot.msg(self.nick, "Please check out %s for a list of things people wanted to tell you." % url)
                
                self.tellconfig.reload()
                self.tellconfig[self.nick] = list()
                self.tellconfig.write()

    def seen(self, channel):
        return self.channels[channel.lower()]

    def seenLine(self, channel):
        chan = self.channels[channel.lower()]
        type = chan["type"].upper()
        time = chan["timestamp"]
        extra = chan["extra"]

        time = datetime.datetime.strftime(time, '%c')
        if type == "NICK":
            return "{0}: User changed nicks to {1}".format(time, extra)
        
        elif type == "JOIN":
            return "{0}: User joined {1}".format(time, channel)
        
        elif type == "PRIVMSG":
            if extra.startswith('\x01ACTION'):
                return "{0}: User did an action: '{1}'".format(time, extra[8:-1])
            
            return "{0}: User said: '{1}'".format(time, extra)
        
        elif type == "RPL_NAMREPLY":
            return "User was here when I joined."
        
        elif type == "QUIT":
            return "User quit."
        
        elif type == "PART":
            return "User left the channel."
        
        return "I don't know what this user did last!"

pattern = re.compile(r"^(?P<nick>[^ ]+)(?:\s+(?P<channel>#[^ ]+))?(?:\s+(?P<count>\d+))?$")

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.manager = seenbase.SeenManager("conf/seen.db")

    @Base.event("NICK", "PRIVMSG", "JOIN", "PART", "QUIT")
    def on_updateseen(self, bot, command, prefix, params):
        nick = prefix.split("!")[0].lower()

        if len(params) > 1:
            msg = params[1]
        else:
            msg = ""

        channel = params[0]
        self.manager.addSeen(nick, channel, command, msg)
        
        if command == 'PRIVMSG':
            self.checkTell(bot, nick)
        
    def checkTell(self, bot, nick):
        tells = self.manager.getTells(nick)
        tosend = []
        
        for tell in tells:
            time = datetime.datetime.strftime(tell.time, '%c')
            text = "{0} in {1} asked to tell you the following: {2} ({3})".format(
                tell.sender, tell.channel, tell.text, time)
            tosend.append(text)
        
        if tosend:
            if not len(tosend) > 4:
                for text in tosend:
                    bot.msg(nick, text)
            else:
                tosend = ["Things people wanted you to know:",] + tosend + \
                    ['(It is currently %s)' % datetime.datetime.strftime(datetime.datetime.now(), '%c')]
                url = pastie.pastie("\n".join(tosend))
                bot.msg(nick, "Please check out %s for a list of things people wanted to tell you." % url)
                
            self.manager.clearTells(nick)
                
    def seenLine(self, data):
        if not data:
            return "I have no info on this user."
        
        type = data.type
        extra = data.data
        
        time = datetime.datetime.strftime(data.time, '%c')
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

    @Base.trigger("TELL")
    def on_tell(self, bot, user, details):
        """TELL <nick> <text> - tell a user something when they are next seen"""
        parts = details["splitmsg"]
        channel = details["channel"]
        
        if len(parts) >= 2:
            nick = parts[0].lower()
            
            self.manager.addTell(nick, user.nick, channel, " ".join(parts[1::]))
            
            return "I'll let them know!"
        
        raise BadParams

    @Base.trigger("SEEN")
    def on_seen(self, bot, user, details):
        """SEEN <nick> [channel] [count] - report on when <nick> was last seen in <channel>. <channel> defaults to the current channel"""
        match = pattern.match(" ".join(details['splitmsg']))
        
        if not match:
            raise BadParams
        
        nick = match.group('nick')
        
        channel = match.group('channel')
        if not channel:
            if details["wasprivate"]:
                return "You need to specify a channel!"
            else:
                channel = details["channel"].lower()
        
        if not channel in bot.channels:
            return "I am not in {0}".format(channel)
        
        count = match.group('count')
        if not count:
            data = self.manager.getLastSeen(nick, channel)
            return self.seenLine(data)
        else:
            data = self.manager.getRangedSeen(nick, channel, int(count))
            tosend = []
                
            for item in data:
                tosend.append(self.seenLine(item))
                    
            if len(tosend) > 4:
                url = pastie.pastie("\n".join(tosend))
                return "Please check out %s for the seen listing. (it was greater than 4 lines)" % url
            else:
                for item in tosend:
                    bot.msg(details['channel'], item)
