from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy import Table, Text, Column, Integer, String, Boolean
from sqlalchemy import PickleType, create_engine
from sqlalchemy.orm import sessionmaker

import hashlib, collections, json

Base = declarative_base()

class UserAlreadyExists(Exception): pass
class NoSuchUser(Exception): pass
class BadPass(Exception): pass
class BadEmail(Exception): pass

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

class RegisteredUser(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    passhash = Column(String)
    perms = Column(TextPickleType(mutable=True, pickler=json))
    isadmin = Column(Boolean)
    
    def __init__(self, username, passhash, perms=None, isadmin=False):
        if perms == None:
            perms = MutableList()
            
        self.username = username.lower()
        self.passhash = passhash
        self.perms = perms
        self.isadmin = isadmin

    def __repr__(self):
        return "<RegisteredUser('%s', '%s', '%s', '%s')>" % \
            (self.username, self.passhash, self.perms, self.isadmin)

class User(object):
    def __init__(self, db, usr):
        self.db = db
        self.usr = usr
        
    def addPerm(self, node):
        if not node.lower() in self.usr.perms:
            self.usr.perms.append(node.lower())
            self.db.session.commit()
            return True
    
        return False
            
    def remPerm(self, node):
        if node.lower() in self.usr.perms:
            self.usr.perms.remove(node.lower())
            self.db.session.commit()
            return True
        
        return False
            
    def hasPerm(self, node, default=False):
        path = node.lower().split(".")
        curpath = path.pop(0)

        if "*" in self.usr.perms:
            return True
        if "-*" in self.usr.perms:
            return False

        for perm in path:
            if "{0}.*".format(curpath) in self.usr.perms:
                return True
            elif "-{0}.*".format(curpath) in self.usr.perms:
                return False
            elif "{0}.{1}".format(curpath, perm) in self.usr.perms:
                return True
            elif "-{0}.{1}".format(curpath, perm) in self.usr.perms:
                return False

            curpath = "{0}.{1}".format(curpath, perm)

        return default # Undefined
        
    def isAdmin(self):
        return self.usr.isadmin
    
    def username(self):
        return self.usr.username.lower()
            
    def changePassword(self, oldpass, newpass):
        if not self.isLoggedIn():
            raise UserNotLoggedIn, self.nick
        
        if hashlib.sha1(oldpass).hexdigest() == self.registration.passhash:
            self.registration.passhash = hashlib.sha1(newpass).hexdigest()
            self.db.session.commit()
            
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
        
    def getUser(self, username):
        username = username.lower()
        exists = self.session.query(RegisteredUser).filter_by(username=username)

        if not exists.count():
            raise NoSuchUser, username
        else:
            return exists.first()
        
    def register(self, username, password):
        username = username.lower()
        
        try:
            user = self.getUser(username)
            raise UserAlreadyExists, username
        except NoSuchUser:
            user = RegisteredUser(username, hashlib.sha1(password).hexdigest())
            self.session.add(user)

        self.session.commit()
        
        return user
    
    def loginPassword(self, username, password):
        user = self.getUser(username)
            
        if hashlib.sha1(password).hexdigest() == user.passhash:
            return user
        
        raise BadPass, username
        