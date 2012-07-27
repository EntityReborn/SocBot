import unittest

from socbot.userdb import UserDB, UserNotLoggedIn, BadEmail, NoSuchUser
from socbot.userdb import UnknownHostmask, BadPass

class UnregisteredTestCase(unittest.TestCase):
    def setUp(self):
        self.db = UserDB()
        self.tester = self.db.getUser('tester')
        
    def testNotRegistered(self):
        assert not self.tester.isLoggedIn()
        
    def testJoinedParted(self):
        self.db.joined(None, 'tester', "#tests")
        assert '#tests' in self.tester.channels
        
        self.db.parted(None, 'tester', "#tests")
        assert not '#tests' in self.tester.channels
        
    def testRegistering(self):
        try:
            doesnotexist = self.db.getRegistration('tester')
            assert False
        except NoSuchUser:
            pass
        
        self.tester.register('tester', 'password', 'tester@gmail.com')
        assert not self.tester.isLoggedIn()
        assert self.db.getRegistration('tester')
        
    def testRegisteringBadEmail(self):
        try:
            self.tester.register('tester', 'password', 'tester')
            assert False
        except BadEmail:
            pass
        
        try:
            self.tester.register('tester', 'password', 'tester@test')
            assert False
        except BadEmail:
            pass
        
        try:
            self.tester.register('tester', 'password', 'tester.test')
            assert False
        except BadEmail:
            pass
        
    def testDefaultPerms(self):
        assert self.tester.hasPerm("default", True)
        
        assert not self.tester.hasPerm("default", False)
        
        assert not self.tester.hasPerm("default")
        
        try:
            self.tester.addPerm("fail")
            assert False
        except UserNotLoggedIn:
            pass
        
        try:
            self.tester.remPerm("fail")
            assert False
        except UserNotLoggedIn:
            pass
        
    def testNickChange(self):
        self.tester.nickChanged(None, 'tester2')
        
        assert self.tester is self.db.getUser('tester2')
        assert not 'tester' in self.db.users
        assert self.tester.nick == 'tester2'
        
        
class RegisteredTestCase(unittest.TestCase):
    def setUp(self):
        self.db = UserDB()
        self.tester = tester = self.db.getUser('tester')
        tester.register('tester', 'password', 'tester@gmail.com')
        tester.loginPassword('tester', 'password')
        
    def testLogout(self):
        assert self.tester.isLoggedIn(), 'expected user to be logged in'
        self.tester.logout()
        assert not self.tester.isLoggedIn(), 'expected user to not be logged in'
        
    def testAddHostmask(self):
        #self.tester.logout()
        self.tester.addHostmask('mask')
        assert self.tester.hasHostmask('mask')
        
    def testRemHostmask(self):
        self.tester.addHostmask('mask')
        assert self.tester.hasHostmask('mask')
        self.tester.remHostmask('mask')
        assert not self.tester.hasHostmask('mask')
    
    def testPasswordLogin(self):
        self.tester.loginPassword('tester', 'password')
        assert self.tester.isLoggedIn()
        
        try:
            self.tester.loginPassword('tester', 'fail')
            assert False
        except BadPass:
            pass
        
    def testHostmaskLogin(self):
        self.tester.addHostmask('mask')
        self.tester.logout()
        
        self.tester.loginHostmask('mask')
        assert self.tester.isLoggedIn()
        
        self.tester.logout()
        try:
            self.tester.loginHostmask('badmask')
            assert False
        except UnknownHostmask:
            pass
        
        
if True == False:
        
    tester.addHostmask('hostmask')
    tester.logout()
    tester.loginHostmask('hostmask')
    tester.changePassword('testpassword', 'testpassword2')
    tester.nickChanged(None, 'tester', 'tester2')
    assert(tester == db.getUser('tester2'))
    
    tester.addPerm('test.dumb.*')
    assert(tester.hasPerm('test.dumb.dang') == True)
    assert(tester.hasPerm('test.dang') == False)
    assert(tester.hasPerm('test.dang', True) == True)
    tester.remPerm('test.dumb.*')
    assert(tester.hasPerm('test.dumb.dang') == False)
    
    tester.remHostmask('hostmask')
    tester.logout()
    assert(tester.isLoggedIn() == False)
    try:
        tester.loginHostmask('hostmask')
        assert(False)
    except NoSuchUser:
        pass
    db.nickChanged(None, 'tester2', 'tester')
    try:
        tester.loginHostmask('hostmask')
        assert(False)
    except UnknownHostmask:
        pass