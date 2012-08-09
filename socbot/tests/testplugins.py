import unittest
from socbot.plugincore import PluginCore
from socbot.pluginapi import API
from socbot.userdb import UserDB

class Connection(object):
    nickname = "SocBot"
    sourceURL = "https://github.com/entityreborn/SocBot/"

    def __init__(self):
        self.factory = None
        self.api = None
        self.sentmsgs = []
        self.sentlines = []

    def sendLine(self, line):
        self.sentlines.append(str(line))
        
    def privmsg(self, user, channel, msg):
        channel = channel.lower()
        
        self.api.privmsg(user, channel, msg)
        
    def handleCommand(self, command, prefix, params):
        self.api.handleCommand(command, prefix, params)
        
    def msg(self, target, message):
        if not message or not target:
            return

        self.sentmsgs.append((target, message))

    def quit(self, message):
        self.shutdown = True

class SimpleResponseTestCase(unittest.TestCase):
    def setUp(self):
        self.proto = Connection()
        self.users = UserDB()
        self.sstate = {
            "users":self.users,
            "config": {
                "directories": {
                    "plugindata": "."
                }                      
            }
        }
        self.manager = PluginCore(self.sstate, 'socbot/tests/plugins')
        self.api = API(self.proto, self.users, self.manager)
        
        self.manager.plugintrackers = self.manager.findPlugins()
        
    def addRegUser(self, name, email, perms, hostmask):
        user = self.users.getUser(name)
        user.register(name, 'password', email)
        
    def testStaticResponse(self):
        self.manager.enablePlug('simple')
        
        func = self.manager.getTrigger("respondstatic")
        retn = func(self.api, None, None)
        
        assert retn == "Pong!!!"
        
    def testInputResponse(self):
        self.manager.enablePlug('simple')
        
        func = self.manager.getTrigger("respondinput")
        retn = func(self.api, None, "something")
        
        assert retn == "something"
        
    def testDirectResponse(self):
        self.manager.enablePlug('simple')
        
        func = self.manager.getTrigger("responddirect")
        retn = func(self.api, None, "something")
        
        assert retn == None
        assert ("user", "direct msg") in self.proto.sentmsgs
        
    def testDisableTrigger(self):
        self.manager.enablePlug('simple')
        
        func = self.manager.getTrigger("trigdisable")
        retn = func(self.api, None, "something")
        
        assert retn == False
        
        func = self.manager.getTrigger("trigdisable")
        retn = func(self.api, None, "disable")
        
        assert retn == True
        
        func = self.manager.getTrigger("trigdisable")
        
        assert func == False
        
    def testDisableEvent(self):
        self.manager.enablePlug('simple')
        
        assert self.manager.triggerEvent("eventdisable", self.api, None, "")
        assert self.manager.triggerEvent("eventdisable", self.api, None, "disable")
        assert not self.manager.triggerEvent("eventdisable", self.api, None, "disable")
        
    def testReload(self):
        self.manager.enablePlug('simple')
        
        id1 = id(self.manager.getTrigger("respondstatic"))
        assert id(self.manager.getTrigger("respondstatic")) == id1
        
        self.manager.reloadPlugin('simple')
        
        assert id(self.manager.getTrigger("respondstatic")) != id1
    