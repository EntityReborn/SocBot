import logging
import re

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from socbot.pluginbase import InsuffPerms, BadParams

from socbot.usermanager import UserManager

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

    def receivedMOTD(self, motd):
        self.log.info("received MOTD")

        if self.factory.config["channels"]:
            for channel, chanconfig in self.factory.config["channels"].iteritems():
                if not chanconfig["autojoin"]:
                    continue

                if chanconfig["password"]:
                    self.join(channel, chanconfig["password"])
                else:
                    self.join(channel)

    def sendLine(self, line):
        self.log.debug("sending line `{0}`".format(line))

        irc.IRCClient.sendLine(self, line)

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

        self.factory.sstate["pluginmanager"].triggerEvent("IRC_%s"%command,
            self, command, prefix, params)

        irc.IRCClient.handleCommand(self, command, prefix, params)

    def privmsg(self, user, channel, msg):
        msg = msg.strip()
        nick, hostmask = user.split("!")
        wasprivate = False

        if not msg:
            return

        match = re.search('^[ ]*{0}[:,][ ]*(.*)$'.format(self.nickname), msg)

        if channel.lower() != self.nickname.lower():
            if match:
                msg = match.group(1)
            elif msg[0] in self.factory.sstate['baseconfig']['general']['commandchars']:
                msg = msg[1:]
        else:
            wasprivate = True
            channel = user.split("!")[0]

        trigger = msg.split()[0].upper()
        usr = self.factory.users[nick]
        pm = self.factory.sstate["pluginmanager"]
        details = {
            "fullmsg": msg,
            "splitmsg": msg.split(),
            "channel": channel,
            "wasprivate": wasprivate
        }

        if trigger in pm.triggers:
            self.log.debug("trigger: {0}".format(trigger))

            func = pm.triggerTrigger(trigger)

            try:
                result = func(self, usr, details)
            except InsuffPerms, perm:
                result = "You don't have the required permission: '{0}'".format(perm)
            except BadParams:
                result = func.__doc__

            if result:
                if result == True:
                    result = "Done."

                self.msg(channel, result)

        else:
            func = pm.triggerTrigger("TRIG_UNKNOWN")

            if func:
                result = func(self, usr, details)

                if result:
                    self.msg(channel, result)

    def msg(self, target, message, length=irc.MAX_COMMAND_LENGTH):
        if not message or not target:
            return

        irc.IRCClient.msg(self, target, message, length)

    def quit(self, message):
        self.shutdown = True

        irc.IRCClient.quit(self, message)
        self.factory.shutdown()

    def join(self, channel, key=None):
        channel = channel.lower()

        if not channel in self.factory.config["channels"]:
            self.factory.config["channels"][channel] = {
                "autojoin": True
            }

            if key:
                self.factory.config["channels"][channel]["password"] = key

            self.factory.config.root().write()

        irc.IRCClient.join(self, channel, key)

    def leave(self, channel, msg):
        channel = channel.lower()

        if channel in self.factory.config["channels"]:
            self.factory.config["channels"][channel] = {
                "autojoin": False
            }

            self.factory.config.root().write()

        irc.IRCClient.leave(self, channel, msg)

    def joined(self, channel):
        if not channel.lower() in self.channels:
            self.channels.append(channel.lower())

    def left(self, channel):
        if channel.lower() in self.channels:
            self.channels.remove(channel.lower())

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
        self.users = UserManager(sstate)

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
