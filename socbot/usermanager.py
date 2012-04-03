import datetime, traceback
from collections import defaultdict
import hashlib

from socbot.tools import CaselessDict, isHostMask, toLower

prefixes = "~&@%+"

class cdict(dict):
    """"""
    def __init__(self, getter):
        dict.__init__(self)
        self.getter = getter

    def __missing__(self, key):
        self[key] = result = self.getter(key)
        return result

class UserExists(Exception): pass
class BadEmail(Exception): pass

class UserManager(object):
    def __init__(self, sharedstate):
        self.sharedstate = sharedstate
        self.users = CaselessDict(lowerfunc=toLower) # All users

    def register(self, nick, username, pass_, email):
        username = username.lower()
        self.sharedstate["users"].reload()

        users = self.sharedstate["users"]["users"]

        if username in users:
            raise UserExists, username

        if "@" in email:
            emailuser, domain = email.split("@")

            if not "." in domain:
                raise BadEmail, email
        else:
            raise BadEmail, email

        passhash = hashlib.sha1(pass_).hexdigest()
        users[username] = {
           "passhash": passhash,
           "permissions": [],
           "email": email,
        }

        user = self.users[nick]
        user.userinfo = (username, users[username])
        self.sharedstate["users"].write()

        return user

    def logIn(self, nick, username, pass_):
        username = username.lower()
        users = self.sharedstate["users"]["users"]

        if username in users:
            config = users[username]
            m = hashlib.sha1(pass_)

            if config["passhash"] == m.hexdigest():
                caller = self.users[nick]
                caller.userinfo = [ username, config ]

                return caller

        return False

    def logOut(self, nick):
        caller = self.users[nick]

        if caller.loggedIn():
            caller.logout()

            return True

        return False

    def add(self, nick, hostmask=""):
        if not nick:
            print traceback.print_exc(10)
            return

        if isHostMask(nick):
            nick, hostmask = nick.split("!")

        if not nick in self.users:
            user = User(nick, hostmask)
            self.users[nick] = user
            
            users = self.sharedstate["users"]["users"]

            if nick.lower() in users:
                config = users[nick.lower()]
                self.users[nick.lower()].userinfo = [ nick, config ]

            return user
        else:
            return self[nick]

    def join(self, nick, channel, hostmask=""):
        if isHostMask(nick):
            nick, hostmask = nick.split("!")

        user = self.add(nick, hostmask) # Returns existing user if one already exists
        user.join(channel)

        return user

    def part(self, nick, channel):
        if isHostMask(nick):
            nick, hostmask = nick.split("!")

        user = self[nick]
        channel = channel

        if user:
            if channel in user.channels:
                user.part(channel)

            if not user.channels:
                self.remove(nick)
                return None

            return user

        return None

    def quit(self, nick):
        # Possibly keep the user? Meh.
        self.remove(nick)

    def remove(self, nick):
        if isHostMask(nick):
            nick, hostmask = nick.split("!")

        if nick in self.users:
            del self.users[nick]
            return True

        return False

    def nick(self, oldnick, newnick):
        user = self[oldnick]

        if user:
            self.users[newnick] = user
            self.remove(oldnick)
            user.nick = newnick

    def __getitem__(self, nick):
        return self.users[nick]

class UserChannel(object):
    def __init__(self, name):
        self.name = name
        self.modes = ""
        self.present = True
        self.joined = datetime.datetime.now()
        self.parted = datetime.datetime.now()

class User(object):
    def __init__(self, nick, hostmask):
        self.nick = nick
        self.hostmask = hostmask
        self.channels = cdict(UserChannel)
        self.lastseen = datetime.datetime.now()
        self.password = ""
        self.userinfo = list()

    def loggedIn(self):
        return self.userinfo != list()

    def logOut(self):
        self.userinfo = list()

    def setPassword(self, raw_password):
        hash = "pass" # randomly generate this
        m = hashlib.sha1(raw_password + hash)
        self.password = "%s$%s" % (m.hexdigest(), hash)

    def checkPassword(self, raw_password):
        if not "$" in self.password:
            return False

        pass_, hash = self.password.split("$")
        m = hashlib.sha1(raw_password + hash)
        return m.hexdigest() == pass_

    def join(self, channel):
        if not channel in self.channels:
            self.channels[channel] = UserChannel(channel)

        self.channels[channel].joined = datetime.datetime.now()
        self.channels[channel].present = True

    def part(self, channel):
        if not channel in self.channels:
            self.setupChannel(channel)

        self.channels[channel].parted = datetime.datetime.now()
        self.channels[channel].present = False

    def hasChanPerm(self, channel, perm):
        if channel in self.channels:
            for p in perm:
                if p in self.channels[channel].modes:
                    return True

        return False

    def hasBotPerm(self, perm):
        return True

    def perms(self, channel):
        return self.channels[channel].modes
