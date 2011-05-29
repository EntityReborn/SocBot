# Hopefully we'll get around to embedding this in the bot code, as opposed to
# it being a plugin. While still in alpha stage, makes more sense as the code
# could still be changed often.

from socbot.pluginbase import Base, BadParams
from socbot.usermanager import prefixes, BadEmail

from twisted.words.protocols.irc import parseModes

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.unknown_nicks = []
        self.looper = None

    def afterReload(self):
        sstate = self.manager.sstate
        for name, botlist in sstate["bots"].iteritems():
            for bot in botlist:
                for chan in bot.channels:
                    bot.sendLine('WHO %s'%chan)

    @Base.event("PRIVMSG")
    def on_msg(self, bot, command, prefix, params):
        nick, hostmask = prefix.split("!")
        user = bot.factory.users[nick]

        if user:
            user.hostmask = hostmask

    @Base.event("MODE")
    def on_mode(self, bot, command, prefix, params):
        channel, modes, args = params[0], params[1], params[2:]

        if modes[0] not in '-+':
            modes = '+' + modes

        if channel == bot.nickname:
            # This is a mode change to our individual user, not a channel mode
            # that involves us.
            paramModes = bot.getUserModeParams()
        else:
            paramModes = bot.getChannelModeParams()

        added, removed = parseModes(modes, args, paramModes)

        if added:
            for mode, nick in added:
                if nick:
                    try:
                        user = bot.factory.users[nick]

                        if not mode in user.channels[channel].modes:
                            user.channels[channel].modes += mode
                    except KeyError:
                        pass

        if removed:
            for mode, nick in removed:
                if nick:
                    try:
                        user = bot.factory.users[nick]

                        if mode in user.channels[channel].modes:
                            newmodes = user.channels[channel].modes.replace(mode, "")
                            user.channels[channel].modes = newmodes
                    except KeyError:
                        pass

    @Base.event("NICK")
    def on_nick(self, bot, command, prefix, params):
        newnick = params[0]
        oldnick = prefix.split("!")[0]
        bot.factory.users.nick(oldnick, newnick)

    @Base.event("RPL_WHOREPLY")
    def on_who(self, bot, command, prefix, params):
        mynick = params[0]
        channel = params[1]
        username = params[2]
        host = params[3]
        server = params[4]
        nick = params[5]
        flags = params[6]

        try:
            usr = bot.factory.users[nick]
        except KeyError:
            usr = bot.factory.users.add(nick)

        usr.hostmask = "%s@%s" % (username, host)
        usr.channels[channel].modes = flags

    @Base.event("JOIN")
    def on_join(self, bot, command, prefix, params):
        nick, host = prefix.split('!')
        channel = params[-1]

        if not nick == bot.nickname:
            if channel[0] in "#":
                user = bot.factory.users.join(nick, channel, host)

                user.hostmask = host
        else:
            bot.sendLine('WHO %s'%channel)

    @Base.event("PART")
    def on_part(self, bot, command, prefix, params):
        parts = prefix.split('!')
        nick, host = parts[0], parts[1]
        channel = params[0]

        if not nick == bot.nickname:
            user = bot.factory.users.part(nick, params[0])

            if user:
                user.hostmask = host

    @Base.event("QUIT")
    def on_quit(self, bot, command, prefix, params):
        nick = prefix.split('!')[0]
        bot.factory.users.quit(nick)

    def print_user(self, usr):
        string = ""

        if usr.loggedIn():
            string += "[ Logged in as: %s ] " % usr.userinfo[0]

        string += "[ mask: %s ]" % usr.hostmask
        string += " [ chans: "

        chans = list()

        for name, chan in usr.channels.iteritems():
            chans.append("%s (%s)" % (chan.name, "".join(chan.modes)))

        string += ", ".join(chans) + " ]"

        return string

    @Base.trigger("IDENTIFY", "ID")
    def on_identify(self, bot, user, details):
        """IDENTIFY (<username>) <password> - Identify with the bot"""
        parts =  details["splitmsg"]
        command = details["trigger"]

        if not details["wasprivate"]:
            return "OOPS! Please privmsg me to identify!"

        if len(parts) == 2:
            usrname, pass_ = parts
        elif len(parts) == 1:
            usrname = user.nick
            pass_ = parts.pop(0)
        else:
            raise BadParams

        usr = bot.factory.users.logIn(user.nick, usrname, pass_)

        if usr:
            return "Authentication successful!"
        else:
            return "Authentication failed. (Usernames aren't case sensitive, passwords are!)"

    @Base.trigger("LOGOUT")
    def on_logout(self, bot, user, details):
        """LOGOUT - Log out from the bot."""
        usr = bot.factory.users[user.nick]
        usr.logOut()

        return "Goodbye!"

    @Base.trigger("REGISTER")
    def on_register(self, bot, user, details):
        """REGISTER <username> <password> <email> - Register to use the bot's functions"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not details["wasprivate"]:
            return "OOPS! Please privmsg me to register!"

        if len(parts) != 3:
            raise BadParams

        usrname = parts.pop(0)
        pass_ = parts.pop(0)
        email = parts.pop(0)

        try:
            usr = bot.factory.users.register(user.nick, usrname, pass_, email)
        except BadEmail:
            return "Erroneous email provided: {0}".format(email)

        return "Welcome to the club!"

    @Base.trigger("USERINFO")
    def on_userinfo(self, bot, user, details):
        """USERINFO <nick> - Show info for a given user"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not parts:
            raise BadParams

        nick = parts.pop(0).lower()

        if nick:
            usr = bot.factory.users[nick]

            if usr:
                return self.print_user(usr)
            else:
                return "No user known by that name!"
