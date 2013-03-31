from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from  sqlalchemy.exc import InvalidRequestError

import datetime

Base = declarative_base()

class Tell(Base):
    __tablename__ = 'tells'

    id = Column(Integer, primary_key=True)
    target = Column(String)
    sender = Column(String)
    channel = Column(String)
    time = Column(DateTime)
    text = Column(String)

    def __init__(self, target, sender, channel, time, text):
        self.target = target
        self.sender = sender
        self.channel = channel
        self.time = time
        self.text = text

    def __repr__(self):
        return "<Tell('%s', '%s', '%s', '%s', '%s')>" % \
            (self.target, self.sender, self.channel, self.time, self.text)
            
class Seen(Base):
    __tablename__ = 'seen'

    id = Column(Integer, primary_key=True)
    target = Column(String)
    channel = Column(String)
    time = Column(DateTime)
    type = Column(String)
    data = Column(String)

    def __init__(self, target, channel, time, type, data):
        self.target = target
        self.channel = channel
        self.time = time
        self.type = type
        self.data = data

    def __repr__(self):
        return "<Tell('%s', '%s', '%s', '%s', '%s')>" % \
            (self.target, self.channel, self.time, self.type, self.data)

class SeenManager(object):
    def __init__(self, db=None):
        if not db:
            db = ":memory:"
            
        self.engine = create_engine('sqlite:///%s' % db)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def addSeen(self, target, channel, type, data):
        target = target.lower()
        channel = channel.lower()
        type = type.upper()
        
        seen = Seen(target, channel, datetime.datetime.now(), type, data)
        self.session.add(seen)
        
        try:
            self.session.commit()
        except InvalidRequestError, e:
            self.session.rollback()
            
        return seen
    
    def getLastSeen(self, target, channel):
        target = target.lower()
        channel = channel.lower()
        
        exists = self.session.query(Seen).filter_by(target=target).\
            filter_by(channel=channel).order_by(Seen.time.desc())
        
        if not exists.count():
            return None
        
        return exists.first()
    
    def getRangedSeen(self, target, channel, count):
        target = target.lower()
        channel = channel.lower()
        
        exists = self.session.query(Seen).filter_by(target=target).\
            filter_by(channel=channel).order_by(Seen.time.desc())
        
        if not exists.count():
            return []
        
        return exists[0:count]

    def addTell(self, target, sender, channel, text):
        target = target.lower()
        channel = channel.lower()
        sender = sender.lower()

        tell = Tell(target, sender, channel, datetime.datetime.now(), text)
        self.session.add(tell)

        try:
            self.session.commit()
        except InvalidRequestError, e:
            self.session.rollback()
            
        return tell
    
    def getTells(self, target):
        target = target.lower()
        exists = self.session.query(Tell).filter_by(target=target).order_by(Tell.time)

        if not exists.count():
            return []
        
        response = exists.all()
        
        return response

    def clearTells(self, target):
        target = target.lower()
        exists = self.session.query(Tell).filter_by(target=target)

        for item in exists.all():
            self.session.delete(item)
            
        try:
            self.session.commit()
        except InvalidRequestError, e:
            self.session.rollback()