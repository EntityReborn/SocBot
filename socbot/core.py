import logging

from twisted.words.protocols import irc
from twisted.internet import protocol, reactor

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
    
    #===== Timeout control =====
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

    def irc_PONG(self, prefix_unused, params):
        if params[-1] == 'idle-socbot' and self._reconnect_deferred:
            self.log.debug("received idle pong")
            
            if self._reconnect_deferred and self._reconnect_deferred.active():
                self._reconnect_deferred.cancel()
            
            self._reconnect_deferred = None
            
            self._ping_deferred = reactor.callLater(
                self.factory.ping_interval, self._idle_ping)

    def connectionMade(self):
        self.log.info("connected to server")

        self.factory.resetDelay()
        self.factory.onConnected(self)

        irc.IRCClient.connectionMade(self)
        self._ping_deferred = reactor.callLater(self.factory.ping_interval, self._idle_ping)

    def connectionLost(self, reason):
        self.log.info("lost connection: {0}".format(reason))
        
        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.cancel()
        if self._reconnect_deferred and self._reconnect_deferred.active():
            self._reconnect_deferred.cancel()
        
        irc.IRCClient.connectionLost(self, reason)
        
    #===== Message Control =====
        
    def dataReceived(self, data):
        irc.IRCClient.dataReceived(self, data)

        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.reset(self.factory.ping_interval)

    def sendLine(self, line):
        self.log.debug("sending line `{0}`".format(line))

        irc.IRCClient.sendLine(self, str(line))

        if self._ping_deferred and self._ping_deferred.active():
            self._ping_deferred.reset(self.factory.ping_interval)
            
    def privmsg(self, user, channel, msg):
        channel = channel.lower()
        
        if self.api.onPrivmsg(user, channel, msg):
            irc.IRCClient.privmsg(self, user, channel, msg)
        
    def handleCommand(self, command, prefix, params):
        if self.api.onCommand(command, prefix, params):
            irc.IRCClient.handleCommand(self, command, prefix, params)
        
    def msg(self, target, message, length=400):
        if not message or not target:
            return
            
        irc.IRCClient.msg(self, target, str(message), length)
            
    def notice(self, target, message, length=400):
        if not message or not target:
            return
        
        irc.IRCClient.notice(self, target, str(message))
        
    #===== Lifetime Control =====
    
    def quit(self, message):
        self.shutdown = True

        irc.IRCClient.quit(self, message)
        self.factory.shutdown()
        
    def restart(self, message="Restarting..."):
        self.factory.sharedstate['exitcode'] = 3
        self.factory.shutdownAll(message)
        
    def _doJoins(self):
        if self.factory.config["channels"]:
            for channel, chanconfig in self.factory.config["channels"].iteritems():
                channel = channel.lower()
                
                if not chanconfig["autojoin"]:
                    continue

                if chanconfig["password"]:
                    self.join(channel, chanconfig["password"])
                else:
                    self.join(channel)

    #===== Incoming Events =====

    def irc_ERR_NOMOTD(self, prefix, params):
        self.log.info("no MOTD")
        self._doJoins()

    def receivedMOTD(self, motd):
        self.log.info("received MOTD")
        self._doJoins()

    def joined(self, channel):
        self.log.info("joined " + channel)
        channel = channel.lower()
        
        if not channel in self.channels:
            self.channels.append(channel)

    def left(self, channel):
        self.log.info("left " + channel)
        channel = channel.lower()
        
        if channel in self.channels:
            self.channels.remove(channel)

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
        self.connection = None
        self.users = UserDB('conf/%s-users.db' % name.lower())

    def clientConnectionLost(self, connector, unused_reason):
        self.log.info("connection lost")
        self.connection = None
        
        if not self.shuttingdown:
            protocol.ReconnectingClientFactory.clientConnectionLost(
                self, connector, unused_reason)

        self.core.connectionLost(self)

    def buildProtocol(self, addr):
        self.log.debug("creating new connection")

        p = protocol.ReconnectingClientFactory.buildProtocol(self, addr)
        p.nickname = self.config['nickname']
        p.log = logging.getLogger("socbot.connection."+self.name)
        p.api = API(p, self.users, self.sharedstate['pluginmanager'])
        p.api.log = logging.getLogger("socbot.connection."+self.name)

        return p

    def onConnected(self, bot):
        if self.connection:
            self.log.warning("a previous connection exists, removing it")
            self.connection.quit()
            self.connection = None
            
        self.connection = bot

    def shutdownAll(self, msg="Shutdown requested."):
        self.core.shutdown(msg)

    def shutdown(self):
        self.shuttingdown = True
