import re

from socbot.userdb import UnknownHostmask, NoSuchUser
from socbot.pluginbase import InsuffPerms, BadParams, StopProcessing
from twisted.internet.defer import maybeDeferred

class API(object):
    sourceURL = "https://github.com/entityreborn/SocBot/"
    
    def __init__(self, connection, users, plugins):
        self.connection = connection
        self.users = users
        self.plugins = plugins
        
    def setNick(self, newnick):
        self.connection.setNick(newnick)
        
    def nick(self):
        return self.connection.nickname
        
    def quit(self, message="Good-bye."):
        self.connection.quit(message)
        
    def restart(self, message="Restarting..."):
        self.connection.restart(message)
        
    def join(self, channel, key=None):
        channel = channel.lower()
        config = self.serverConfig()
        
        if not channel in config["channels"]:
            config["channels"][channel] = {}
        
        if key:
            config["channels"][channel]["password"] = key

        self.saveConfig()

        self.connection.join(channel, key)

    def leave(self, channel, msg="Good-bye."):
        channel = channel.lower()
        config = self.serverConfig()
        
        if channel in config['channels']:
            config['channels'][channel]['autojoin'] = False
            
            self.saveConfig()

        self.connection.leave(channel, msg)

    def sendLine(self, line):
        self.connection.sendLine(line)
    
    def msg(self, target, msg, revd=False):
        # revd is for use when calling from a deferred.
        if not revd:
            self.connection.msg(target, msg)
        else: 
            self.connection.msg(msg, target)
            
    def notice(self, target, msg, revd=False):
        # revd is for use when calling from a deferred.
        if not revd:
            self.connection.notice(target, msg)
        else:
            self.connection.notice(msg, target)
        
    def action(self, target, msg, revd=False):
        # revd is for use when calling from a deferred.
        if not revd:
            self.connection.msg(target, u'\x01ACTION %s\x01'%msg)
        else:
            self.connection.msg(u'\x01ACTION %s\x01'%msg, target)
    
    def onCommand(self, command, prefix, params):
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
                
        trigger = True 
        
        for flt in self.plugins.getEventPrefilters():
            try:
                flt(self, command, prefix, params)
            except StopProcessing:
                trigger = False
            except Exception:
                self.log.exception("General exception")
            
        if trigger:
            self.plugins.triggerEvent(command,
                self, command, prefix, params)
        
        if command == 'QUIT':
            usrname = prefix.split("!")[0].lower()
            usr = self.users.getUser(usrname)
            
            usr.quit(self)

        return True

    def onPrivmsg(self, user, channel, msg):
        msg = msg.strip()
        nick = user.split("!")[0]
        wasprivate = False

        if not msg:
            return

        match = re.search('^[ ]*{0}[:,][ ]*(.*)$'.format(self.connection.nickname.lower()), msg)
        
        if channel.lower() != self.connection.nickname.lower():
            if match and self.generalConfig()['nicktrigger'].lower() == 'true':
                msg = match.group(1)
            elif msg[0] not in self.generalConfig()['commandchars']:
                return
        else:
            wasprivate = True
            channel = user.split("!")[0]
            
        if msg[0] in self.generalConfig()['commandchars']:
            msg = msg[1:]
                
        parts = msg.partition(" ")
        split = parts[2].split()
        trigger = parts[0].upper()
        
        if not trigger:
            return
        
        usr = self.users.getUser(nick.lower())
        
        details = {
            "fullmsg": msg,
            "fulluser": user,
            "splitmsg": split,
            "trigger": trigger.lower(),
            "channel": channel.lower(),
            "wasprivate": wasprivate
        }
        
        prefilters = self.plugins.getMsgPrefilters()
        
        for func in prefilters:
            try:
                retn = func(self, usr, details)
                
                if retn and isinstance(retn, dict):
                    details = retn
                    
            except StopProcessing:
                return
                    
            except Exception:
                self.log.exception("General exception")
                
        func = self.plugins.getTrigger(trigger)
            
        if func:
            self.log.debug("trigger: {0}".format(trigger))
            
            try:
                d = maybeDeferred(func, self, usr, details)
                d.addCallback(self.sendResult, channel)
                d.addErrback(self.sendError, channel, func, nick)
            except Exception:
                self.log.exception("General exception")
        else:
            self.plugins.triggerEvent("TRIG_UNKNOWN", self, usr, details)
            
    def sendError(self, err, target, func, nick):
        err.trap(InsuffPerms, BadParams, Exception)
        if err.type == BadParams:
            self.connection.msg(target, func.__doc__)
        elif err.type == InsuffPerms:
            notificationtype = self.generalConfig()['permerrornotification']
            message = "Insufficient permissions (%s). Did you forget to log in?" % err.value.args[0]
            
            if notificationtype == "NOTICE":
                self.notice(nick, message)
            elif notificationtype == "CHANNEL":
                self.msg(target, message)
            elif notificationtype == "PM":
                self.msg(nick, message)
        else:
            self.log.error(err.getTraceback())
            self.msg(target, "Exception in plugin function {0} ({1}). ".format(func.__name__, err.getErrorMessage()) + \
                    "Please check the logs or notify someone who manages me.")
                
    def sendResult(self, msg, target):
        if msg:
            if msg == True:
                msg = "Done."
            
            self.msg(target, str(msg))
            
    def name(self):
        return self.connection.factory.name
            
    def serverConfig(self):
        return self.baseConfig()['servers'][self.name()]
    
    def generalConfig(self):
        return self.baseConfig()['general']
    
    def baseConfig(self):
        return self.connection.factory.core.config
        
    def saveConfig(self):
        self.connection.factory.core.config.write()
        
    def reloadConfig(self):
        self.connection.factory.core.config.reload()
        self.connection.factory.core.config.isValid()