from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy import Text, Column, Integer, String
from sqlalchemy import DateTime, PickleType, create_engine
from sqlalchemy.orm import sessionmaker

import hashlib, collections, datetime
import json, re

prefixes = "~&@%+"

Base = declarative_base()

class UserNotLoggedIn(Exception): pass
class UserAlreadyExists(Exception): pass
class NoSuchUser(Exception): pass
class BadPass(Exception): pass
class BadEmail(Exception): pass
class UnknownHostmask(Exception): pass

class TextPickleType(PickleType):
    impl = Text

class MutableList(Mutable, list):
    def __getstate__(self):
        return list(self)

    def __setstate__(self, state):
        self[:] = state
        self.changed()
        
    def append(self, object):
        list.append(self, object)
        self.changed()
        
    def remove(self, object):
        list.remove(self, object)
        self.changed()
    
    def pop(self, *args):
        list.pop(self, *args)
        self.changed()
        
    def extend(self, *args):
        list.extend(self, *args)
        self.changed()

class UnregisteredUser(object):
    def __init__(self, *args, **kwargs):
        self.username = "Unregistered"
        self.hostmasks = []
        self.perms = []
        self.passhash = ""
        self.regdate = datetime.datetime.now()
    
    def addPerm(self, node):
        raise UserNotLoggedIn
            
    def remPerm(self, node):
        raise UserNotLoggedIn
            
    def hasPerm(self, node, default=False):
        return default
    
    def addHostmask(self, hostmask):
        raise UserNotLoggedIn
            
    def remHostmask(self, hostmask):
        raise UserNotLoggedIn
    
    def hasHostmask(self, hostmask):
        raise False

class RegisteredUser(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    passhash = Column(String)
    regdate = Column(DateTime)
    hostmasks = Column(TextPickleType(mutable=True, pickler=json))
    perms = Column(TextPickleType(mutable=True, pickler=json))
    email = Column(String)
    
    def __init__(self, username, passhash, email, regdate=datetime.datetime.now(),
                 perms=None, hostmasks=None):
        if perms == None:
            perms = MutableList()
            
        if hostmasks == None:
            hostmasks = MutableList()
            
        self.username = username.lower()
        self.passhash = passhash
        self.regdate = regdate
        self.email = email
        self.hostmasks = hostmasks
        self.perms = perms

    def __repr__(self):
        return "<RegisteredUser('%s', '%s', '%s', '%s', '%s', '%s')>" % \
            (self.username, self.passhash, self.email, self.regdate,
             self.perms, self.hostmasks)
            
    def addPerm(self, node):
        if not node.lower() in self.perms:
            self.perms.append(node.lower())
            return True
    
        return False
            
    def remPerm(self, node):
        if node.lower() in self.perms:
            self.perms.remove(node.lower())
            return True
        
        return False
            
    def hasPerm(self, node, default=False):
        path = node.lower().split(".")
        curpath = path.pop(0)

        if "*" in self.perms:
            return True
        if "-*" in self.perms:
            return False

        for perm in path:
            if "{0}.*".format(curpath) in self.perms:
                return True
            elif "-{0}.*".format(curpath) in self.perms:
                return False
            elif "{0}.{1}".format(curpath, perm) in self.perms:
                return True
            elif "-{0}.{1}".format(curpath, perm) in self.perms:
                return False

            curpath = "{0}.{1}".format(curpath, perm)

        return default # Undefined
    
    def addHostmask(self, hostmask):
        if not hostmask.lower() in self.hostmasks:
            self.hostmasks.append(hostmask.lower())
            return True
        
        return False
            
    def remHostmask(self, hostmask):
        if hostmask.lower() in self.hostmasks:
            self.hostmasks.remove(hostmask.lower())
            return True
        
        return False
    
    def hasHostmask(self, hostmask):
        return hostmask.lower() in self.hostmasks.lower()
    
emailpat = re.compile(r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", re.IGNORECASE)

class UserChannel(object):
    def __init__(self):
        self.name = ""
        self.modes = ""
        self.joined = datetime.datetime.now()
        self.parted = None

class User(object):
    def __init__(self, db, nick):
        self.db = db
        self.nick = nick
        self.hostmask = None
        self.channels = collections.defaultdict(UserChannel)
        self.registration = UnregisteredUser()
        
    def isLoggedIn(self):
        return isinstance(self.registration, RegisteredUser)
        
    def register(self, username, password, email):
        if not emailpat.match(email):
            raise BadEmail, email
        
        username = username.lower()
        exists = self.db.session.query(RegisteredUser).filter_by(username=username)

        if exists.count():
            raise UserAlreadyExists, username
        else:
            user = RegisteredUser(username, hashlib.sha1(password).hexdigest(), email.lower())
            self.db.session.add(user)

        self.db.saveSession()
        
        return user
    
    def loginPassword(self, username, password):
        user = self.db.getRegistration(username)
            
        if hashlib.sha1(password).hexdigest() == user.passhash:
            self.registration = user
            return True
        
        raise BadPass, username
        
    def loginHostmask(self, hostmask):
        user = self.db.getRegistration(self.nick)

        if hostmask.lower() in user.hostmasks:
            self.registration = user
            return True
        
        raise UnknownHostmask, hostmask
    
    def logout(self):
        self.db.saveSession()
        
        if not self.isLoggedIn():
            raise UserNotLoggedIn, self.nick
        
        self.registration = UnregisteredUser()
    
    def joined(self, bot, channel):
        channel = channel.lower()
        self.channels[channel].name = channel
        
    def parted(self, bot, channel):
        chan = channel.lower()
        
        if chan in self.channels:
            del self.channels[chan]
        
    def quit(self, bot):
        self.db.quit(bot, self.nick)
        
    def addPerm(self, node):
        retn = self.registration.addPerm(node)
        self.db.saveSession()
        return retn
            
    def remPerm(self, node):
        retn = self.registration.remPerm(node)
        self.db.saveSession()
        return retn
            
    def hasPerm(self, node, default=False):
        return self.registration.hasPerm(node, default)
    
    def username(self):
        if self.isLoggedIn():
            username = self.registration.username
        else:
            username = self.nick
            
        return username.lower()
        
    def addHostmask(self, hostmask):
        retn = self.registration.addHostmask(hostmask)
        self.db.saveSession()
        return retn
            
    def remHostmask(self, hostmask):
        retn = self.registration.remHostmask(hostmask)
        self.db.saveSession()
        return retn
    
    def hasHostmask(self, hostmask):
        return self.registration.hasHostmask(hostmask)
    
    def nickChanged(self, bot, tonick):
        self.db.nickChanged(bot, self.nick, tonick)
            
    def changePassword(self, oldpass, newpass):
        if not self.isLoggedIn():
            raise UserNotLoggedIn, self.nick
        
        if hashlib.sha1(oldpass).hexdigest() == self.registration.passhash:
            self.registration.passhash = hashlib.sha1(newpass).hexdigest()
            self.db.saveSession()
            
            return True
        else:
            raise BadPass
        
class UserDB(object):
    def __init__(self, db=None):
        if not db:
            db = ":memory:"
        
        self.db = db   
        self.engine = create_engine('sqlite:///%s' % db)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.users = {}
        
    def rehash(self):
        self.engine = create_engine('sqlite:///%s' % self.db)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        for user in self.users:
            if isinstance(user.registration, RegisteredUser):
                try:
                    username = user.registration.username
                    user.registration = user.getRegistration(username)
                except NoSuchUser:
                    # User was deleted.
                    user.registration = UnregisteredUser()
        
    def saveSession(self):
        self.session.commit()
        
    def allRegistrations(self):
        return self.session.query(RegisteredUser)
        
    def getRegistration(self, username):
        username = username.lower()
            
        exists = self.session.query(RegisteredUser).filter_by(username=username)

        if exists.count():
            reg = exists.first()
            return reg
        
        raise NoSuchUser, username
    
    def getUserInfo(self, username):
        username = username.lower()
        
        usr = User(self, username)
        usr.registration = self.getRegistration(username)
        
        return usr
        
    def hasUser(self, nick):
        nick = nick.lower()
        
        return nick in self.users
    
    def getUser(self, nick):
        nick = nick.lower()
        
        if not nick in self.users:
            self.users[nick] = User(self, nick)
            
        return self.users[nick]
    
    def quit(self, bot, nick):
        nick = nick.lower()
        
        if nick in self.users:
            del self.users[nick.lower()]
        
    def joined(self, bot, nick, channel):
        user = self.getUser(nick)
        user.joined(bot, channel)
        
    def parted(self, bot, nick, channel):
        user = self.getUser(nick)
        user.parted(bot, channel)
        
    def nickChanged(self, bot, fromnick, tonick):
        tonick = tonick.lower()
        fromnick = fromnick.lower()
        
        user = self.getUser(fromnick)
        self.users[tonick] = user
        user.nick = tonick
        
        del self.users[fromnick]
        
    def modeChanged(self, bot, nick, channel, modes, args):
        user = self.getUser(nick)
        user.modeChanged(bot, channel, modes, args)
        
if __name__ == "__main__":
    db = UserDB()
    db.joined(None, 'tester', '#testing')
    tester = db.getUser('tester')
    tester.register('tester', 'testpassword', 'e@n.t')
    tester.loginPassword('tester', 'testpassword')
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
    