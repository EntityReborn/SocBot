from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
class Factoid(Base):
    __tablename__ = 'factoids'

    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    response = Column(String)
    createdby = Column(String, default="")
    alteredby = Column(String, nullable=True, default="")
    locked = Column(Boolean, nullable=True, default=False)
    lockedby = Column(String, nullable=True, default="")

    def __init__(self, key, response, createdby="", alteredby=None, locked=False, lockedby=None):
        self.keyword = key.encode('UTF-8')
        self.response = response.encode('UTF-8')
        self.createdby = createdby
        self.alteredby = alteredby
        self.locked = locked
        self.lockedby = lockedby
        
    def getResponse(self):
        return self.response.encode('UTF-8')
    
    def getKey(self):
        return self.keyword.encode('UTF-8')

    def __repr__(self):
        return "<Factoid('%s', '%s', '%s', '%s', %s, '%s')>" % \
            (self.getKey(), self.getResponse(), self.createdby, self.alteredby, self.locked, self.lockedby)

class FactoidException(Exception): pass
class FactoidAlreadyExists(FactoidException): pass
class NoSuchFactoid(FactoidException): pass

class FactoidManager(object):
    def __init__(self, db=None):
        if not db:
            db = "/:memory:"
            
        self.engine = create_engine('sqlite:///%s' % db)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def save(self):
        self.session.commit()
        
    def allFacts(self):
        return self.session.query(Factoid)
    
    def addFact(self, key, response, replace=False):
        key = key.lower().decode('UTF-8')
        response = response.decode('UTF-8')
        
        exists = self.session.query(Factoid).filter_by(keyword=key)
        
        if exists:
            if not replace:
                raise FactoidAlreadyExists, key
        
        if exists.count():
            fact = exists.first()
            
            fact.response = response
        else:
            fact = Factoid(key, response)
            
            self.session.add(fact)

        self.session.commit()
        return fact

    def updateFact(self, key, response):
        return self.addFact(key, response, True)
    
    def getFact(self, key):
        key = key.lower()
        exists = self.session.query(Factoid).filter_by(keyword=key)

        if not exists.count():
            raise NoSuchFactoid, key
        
        fact = exists.first()
        return fact

    def remFact(self, key):
        exists = self.session.query(Factoid).filter_by(keyword=key)

        if not exists.count():
            raise NoSuchFactoid, key

        self.session.delete(exists.first())
        self.session.commit()