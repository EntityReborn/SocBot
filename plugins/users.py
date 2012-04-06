from socbot.pluginbase import Base, BadParams
from socbot.userdb import prefixes, BadEmail, NoSuchUser
from socbot.userdb import UserAlreadyExists, UserNotLoggedIn

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
                        user = bot.users.getUser(nick)

                        if not mode in user.channels[channel].modes:
                            user.channels[channel].modes += mode
                    except KeyError:
                        pass

        if removed:
            for mode, nick in removed:
                if nick:
                    try:
                        user = bot.users.getUser(nick)

                        if mode in user.channels[channel].modes:
                            newmodes = user.channels[channel].modes.replace(mode, "")
                            user.channels[channel].modes = newmodes
                    except KeyError:
                        pass

    @Base.event("RPL_WHOREPLY")
    def on_who(self, bot, command, prefix, params):
        mynick = params[0]
        channel = params[1]
        username = params[2]
        host = params[3]
        server = params[4]
        nick = params[5]
        flags = params[6]

        usr = bot.users.getUser(nick)
        usr.channels[channel].modes = flags

    @Base.event("JOIN")
    def on_join(self, bot, command, prefix, params):
        nick, host = prefix.split('!')
        channel = params[-1]

        if nick == bot.nickname:
            bot.sendLine('WHO %s'%channel)

    def print_user(self, usr):
        string = ""

        if usr.isLoggedIn():
            string += "[ Logged in as: %s ] " % usr.registration.username
            
        string += " [ chans: "

        chans = list()

        for name, chan in usr.channels.iteritems():
            chans.append("%s (%s)" % (name, "".join(chan.modes)))

        string += ", ".join(chans) + " ]"

        return string

    @Base.trigger('ISOP')
    def on_isop(self, bot, user, details):
        """ISOP <user> [channel] - Check if a user is an op for a given channel"""
        if len(details['splitmsg']) > 0:
            user = details['splitmsg'][0]
            
            if len(details['splitmsg']) > 1:
                channel = details['splitmsg'][1]
            else:
                channel = details['channel']
        else:
            return BadParams
        
        userdata = bot.users.getUser(user.lower())
        
        if "@" in userdata.channels[channel].modes:
            return "This user is an op!"
        else:
            return "This user is not an op!"
        
    @Base.trigger("IDENTIFY", "ID")
    def on_identify(self, bot, user, details):
        """IDENTIFY [username] <password> - Identify with the bot"""
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

        usr = user.loginPassword(usrname, pass_)

        if usr:
            return "Authentication successful!"
        else:
            return "Authentication failed. (Usernames aren't case sensitive, passwords are!)"

    @Base.trigger("LOGOUT")
    def on_logout(self, bot, user, details):
        """LOGOUT - Log out from the bot."""
        try:
            user.logout()
        except UserNotLoggedIn:
            return "You are not logged in!"
        
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
            usr = user.register(usrname, pass_, email)
        except BadEmail:
            return "Erroneous email provided: {0}".format(email)
        except UserAlreadyExists:
            return "That user already exists! Please choose a different username."

        return "Welcome to the club!"
    
    @Base.trigger("ADDMASK")
    def in_addmask(self, bot, user, details):
        nick, hostmask = details['fulluser'].split("!")
        
        try:
            user.addHostmask(hostmask)
        except UserNotLoggedIn:
            return "You need to login!"
        
        return "Mask added."
    
    @Base.trigger("REMMASK")
    def in_remmask(self, bot, user, details):
        nick, hostmask = details['fulluser'].split("!")
        
        try:
            user.remHostmask(hostmask)
        except UserNotLoggedIn:
            return "You need to login!"
        
        return "Mask removed."

    @Base.trigger("USERINFO")
    def on_userinfo(self, bot, user, details):
        """USERINFO <nick> - Show info for a given user"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not parts:
            nick = user.nick
        else:
            nick = parts.pop(0).lower()

        if nick:
            usr = bot.users.getUser(nick)

            if usr:
                return self.print_user(usr)
            else:
                return "No user known by that name!"
