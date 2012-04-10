import logging
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from socbot.pluginbase import InsuffPerms, BadParams

from socbot.userdb import UserDB, UnknownHostmask, NoSuchUser

# Credits to ibid for some helpful code:
# - Ping ponger

class Bot(irc.IRCClient):
    nickname = "SocBot"
    sourceURL = "http://github.com/entityreborn/SocBot/"

    _ping_deferred = None
    _reconnect_deferred = None

    def __init__(self):
        self.factory = None
        self.log = None
        self.shutdown = False
        self.channels = []

    def _idle_ping(self):
        self.log.debug("sending idle ping")

        self._ping_deferred = None
        self._reconnect_deferred = reactor.callLater(
            self.factory.pong_timeout, self._timeout_reconnect)

        self.sendLine('PING idle-socbot')

    def _timeout_reconnect(self):
        self.log.info("idle timeout; reconnecting")
        self.transport.loseConnection()

    def dataReceived(self, data):
        irc.IRCClient.dataReceived(self, data)

        if self._ping_deferred is not None:
            self._ping_deferred.reset(self.factory.ping_interval)

    def irc_PONG(self, prefix_unused, params):
        if params[-1] == 'idle-socbot' and self._reconnect_deferred:
            self.log.debug("received idle pong")

            self._reconnect_deferred.cancel()

            self._reconnect_deferred = None
            self._ping_deferred = reactor.callLater(
                self.factory.ping_interval, self._idle_ping)

    def doJoins(self):
        if self.factory.config["channels"]:
            for channel, chanconfig in self.factory.config["channels"].iteritems():
                if not chanconfig["autojoin"]:
                    continue

                if chanconfig["password"]:
                    self.join(channel, chanconfig["password"])
                else:
                    self.join(channel)

    def irc_ERR_NOMOTD(self, prefix, params):
        self.log.info("no MOTD")
        self.doJoins()

    def receivedMOTD(self, motd):
        self.log.info("received MOTD")
        self.doJoins()

    def sendLine(self, line):
        self.log.debug("sending line `{0}`".format(line))

        irc.IRCClient.sendLine(self, str(line))

        if self._ping_deferred is not None:
            self._ping_deferred.reset(self.factory.ping_interval)

    def connectionMade(self):
        self.log.info("connected to server")

        self.factory.resetDelay()
        self.factory.addBot(self)

        irc.IRCClient.connectionMade(self)
        self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)

    def connectionLost(self, reason):
        self.log.info("lost connection: {0}".format(reason))

        irc.IRCClient.connectionLost(self, reason)

        if self.shutdown:
            self.factory.removeBot(self)

    def handleCommand(self, command, prefix, params):
        self.log.debug("command `{0}`, from prefix `{1}`".format(
            command, prefix))

        if command == "ERROR":
            self.log.debug("command `{0}`, from prefix `{1}`, with params `{2}`".format(
                command, prefix, params))
            
        if command in ['JOIN', 'PART', 'NICK', 'PRIVMSG', 'NOTICE']:
            if "!" in prefix:
                username, hostmask = prefix.split("!")
                usr = self.users.getUser(username)
                usr.hostmask = hostmask
                
                if not usr.isLoggedIn():
                    try:
                        usr.loginHostmask(hostmask)
                    except UnknownHostmask:
                        pass
                    except NoSuchUser:
                        pass
                        
            if command == 'NICK':
                usr.nickChanged(self, params[0])
            elif command == 'JOIN':
                usr.joined(self, params[-1])
            elif command == 'PART':
                usr.parted(self, params[0])
            
        self.factory.sstate["pluginmanager"].triggerEvent(command,
            self, command, prefix, params)
        
        if command == 'QUIT':
            usrname = prefix.split("!")[0].lower()
            usr = self.users.getUser(usrname)
            
            usr.quit(self)

        irc.IRCClient.handleCommand(self, command, prefix, params)

    def privmsg(self, user, channel, msg):
        msg = msg.strip()
        nick, hostmask = user.split("!")
        wasprivate = False

        if not msg:
            return

        match = re.search('^[ ]*{0}[:,][ ]*(.*)$'.format(self.nickname), msg)

        if channel.lower() != self.nickname.lower():
            if match and self.generalConfig()['nicktrigger'].lower() == 'true':
                msg = match.group(1)
            elif msg[0] in self.generalConfig()['commandchars']:
                msg = msg[1:]
            else:
                return
        else:
            wasprivate = True
            channel = user.split("!")[0]

        trigger = msg.split()[0].upper()
        usr = self.users.getUser(nick.lower())
        pm = self.factory.sstate["pluginmanager"]
        splitmsg = msg.split()
        
        details = {
            "fullmsg": msg,
            "fulluser": user,
            "splitmsg": splitmsg,
            "trigger": splitmsg.pop(0).lower(),
            "channel": channel.lower(),
            "wasprivate": wasprivate
        }
        
        result = None
        
        func = pm.getTrigger(trigger)
            
        if func:
            self.log.debug("trigger: {0}".format(trigger))

            try:
                result = func(self, usr, details)
            except InsuffPerms, perm:
                result = "You don't have the required permission: '{0}'".format(perm)
            except BadParams:
                result = func.__doc__
            except Exception as e:
                self.log.exception(e)
                result = "Exception in plugin function {0} ({1}). ".format(func.__name__, msg) + \
                    "Please check the logs."
        else:
            pm.triggerEvent("TRIG_UNKNOWN", self, usr, details)
                
        if result:
            if result == True:
                result = "Done."
        
            self.msg(channel, str(result))

    def msg(self, target, message, length=irc.MAX_COMMAND_LENGTH):
        if not message or not target:
            return

        irc.IRCClient.msg(self, target, message, length)

    def quit(self, message):
        self.shutdown = True

        irc.IRCClient.quit(self, message)
        self.factory.shutdown()
        
    def restart(self, message="Restarting..."):
        self.factory.sstate['exitcode'] = 3
        self.factory.shutdownAll(message)

    def join(self, channel, key=None):
        channel = channel.lower()
        config = self.serverConfig()
        
        if not channel in config["channels"]:
            config["channels"][channel] = {
                "autojoin": True
            }
        else:
            config["channels"][channel]["autojoin"] = True
        
        if key:
            config["channels"][channel]["password"] = key

        self.saveConfig()

        irc.IRCClient.join(self, channel, key)

    def leave(self, channel, msg):
        channel = channel.lower()
        config = self.serverConfig()

        if channel in config["channels"]:
            config["channels"][channel]['autojoin'] = False

            self.saveConfig()

        irc.IRCClient.leave(self, channel, msg)

    def joined(self, channel):
        self.log.info("joined " + channel)
        
        if not channel.lower() in self.channels:
            self.channels.append(channel.lower())

    def left(self, channel):
        self.log.info("left " + channel)
        
        if channel.lower() in self.channels:
            self.channels.remove(channel.lower())
            
    def serverConfig(self):
        return self.baseConfig()['servers'][self.factory.name]
    
    def generalConfig(self):
        return self.baseConfig()['general']
    
    def baseConfig(self):
        self.factory.core.config.reload()
        return self.factory.core.config
        
    def saveConfig(self):
        self.factory.core.config.write()
        
    def reloadConfig(self):
        self.factory.core.config.reload()

class BotFactory(protocol.ReconnectingClientFactory):
    protocol = Bot
    log = logging.getLogger("socbot")
    ping_interval = 60.0
    pong_timeout = 120.0

    def __init__(self, name, config, sstate, main):
        self.name = name
        self.sstate = sstate
        self.core = main
        self.config = config
        self.shuttingdown = False
        self.users = UserDB('conf/%s-users.db' % name)

    def clientConnectionLost(self, connector, unused_reason):
        self.log.info("connection lost")
        if not self.shuttingdown:
            protocol.ReconnectingClientFactory.clientConnectionLost(
                self, connector, unused_reason)

        if not self.sstate["bots"]:
            reactor.stop()

    def buildProtocol(self, addr):
        self.log.debug("creating new bot")

        p = protocol.ReconnectingClientFactory.buildProtocol(self, addr)
        p.nickname = self.config['nickname']
        p.users = self.users
        p.log = logging.getLogger("socbot."+self.name)

        return p

    def addBot(self, bot):
        self.sstate["bots"][self.name].append(bot)

    def removeBot(self, bot):
        self.sstate["bots"][self.name].remove(bot)

        if not self.sstate["bots"][self.name]:
            del self.sstate["bots"][self.name]

    def shutdownAll(self, msg="Shutdown requested."):
        self.core.shutdown(msg)

    def shutdown(self):
        self.shuttingdown = True
