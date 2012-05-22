import logging

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from twisted.internet.error import ReactorNotRunning

from socbot.pluginapi import API
from socbot.userdb import UserDB

# Credits to ibid for some helpful code:
# - Ping ponger

class Connection(irc.IRCClient):
    nickname = "SocBot"

    _ping_deferred = None
    _reconnect_deferred = None

    def __init__(self):
        self.factory = None
        self.log = None
        self.shutdown = False
        self.api = None
        self.channels = []

    def _idle_ping(self):
        self.log.debug("sending idle ping")

        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.cancel()
            
        self._ping_deferred = None
            
        self._reconnect_deferred = reactor.callLater(
            self.factory.pong_timeout, self._timeout_reconnect)

        self.sendLine('PING idle-socbot')

    def _timeout_reconnect(self):
        self.log.info("idle timeout; reconnecting")
        self.transport.loseConnection()

    def dataReceived(self, data):
        irc.IRCClient.dataReceived(self, data)

        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.reset(self.factory.ping_interval)

    def irc_PONG(self, prefix_unused, params):
        if params[-1] == 'idle-socbot' and self._reconnect_deferred:
            self.log.debug("received idle pong")
            
            if self._reconnect_deferred and self._reconnect_deferred.active():
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

        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.reset(self.factory.ping_interval)

    def connectionMade(self):
        self.log.info("connected to server")

        self.factory.resetDelay()
        self.factory.addBot(self)

        irc.IRCClient.connectionMade(self)
        self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)

    def connectionLost(self, reason):
        self.log.info("lost connection: {0}".format(reason))
        
        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.cancel()
        if self._reconnect_deferred and self._reconnect_deferred.active():
            self._reconnect_deferred.cancel()
        
        irc.IRCClient.connectionLost(self, reason)
        
        if self.shutdown:
            self.factory.removeBot(self)
        else:
            self._timeout_reconnect()
    
    def privmsg(self, user, channel, msg):
        channel = channel.lower()
        
        if self.api.onPrivmsg(user, channel, msg):
            irc.IRCClient.privmsg(self, user, channel, message)
        
    def handleCommand(self, command, prefix, params):
        if self.api.onCommand(command, prefix, params):
            irc.IRCClient.handleCommand(self, command, prefix, params)
        
    def msg(self, target, message, length=irc.MAX_COMMAND_LENGTH):
        if not message or not target:
            return

        irc.IRCClient.msg(self, target, message, length)

    def quit(self, message):
        self.shutdown = True

        irc.IRCClient.quit(self, message)
        self.factory.shutdown()
        
    def restart(self, message="Restarting..."):
        self.factory.sharedstate['exitcode'] = 3
        self.factory.shutdownAll(message)

    def joined(self, channel):
        self.log.info("joined " + channel)
        
        if not channel.lower() in self.channels:
            self.channels.append(channel.lower())

    def left(self, channel):
        self.log.info("left " + channel)
        
        if channel.lower() in self.channels:
            self.channels.remove(channel.lower())

class BotFactory(protocol.ReconnectingClientFactory):
    protocol = Connection
    log = logging.getLogger("socbot")
    ping_interval = 60.0
    pong_timeout = 60.0

    def __init__(self, name, config, sharedstate, main):
        self.name = name
        self.sharedstate = sharedstate
        self.core = main
        self.config = config
        self.shuttingdown = False
        self.users = UserDB('conf/%s-users.db' % name.lower())

    def clientConnectionLost(self, connector, unused_reason):
        self.log.info("connection lost")
        
        if not self.shuttingdown:
            protocol.ReconnectingClientFactory.clientConnectionLost(
                self, connector, unused_reason)

        if not self.sharedstate["connections"]:
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass

    def buildProtocol(self, addr):
        self.log.debug("creating new connection")

        p = protocol.ReconnectingClientFactory.buildProtocol(self, addr)
        p.nickname = self.config['nickname']
        p.log = logging.getLogger("socbot.connection."+self.name)
        p.api = API(p, self.users, self.sharedstate['pluginmanager'])
        p.api.log = logging.getLogger("socbot.connection."+self.name)

        return p

    def addBot(self, bot):
        self.sharedstate["connections"][self.name].append(bot)

    def removeBot(self, bot):
        self.sharedstate["connections"][self.name].remove(bot)

        if not self.sharedstate["connections"][self.name]:
            del self.sharedstate["connections"][self.name]
            
        if not self.sharedstate["connections"]:
            try:
                reactor.stop()
            except ReactorNotRunning:
                pass

    def shutdownAll(self, msg="Shutdown requested."):
        self.core.shutdown(msg)

    def shutdown(self):
        self.shuttingdown = True
