from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
class Factoid(Base):
    __tablename__ = 'factoids'

    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    response = Column(String)

    def __init__(self, key, response):
        self.keyword = key
        self.response = response

    def __repr__(self):
        return "<Factoid('%s', '%s')>" % (self.keyword, self.response)

class FactoidAlreadyExists(Exception): pass
class NoSuchFactoid(Exception): pass
class OrphanedFactoid(Exception): pass
class CyclicalFactoid(Exception): 
    def __init__(self, lst):
        self.lst = lst

class FactoidManager(object):
    def __init__(self, db=None):
        if not db:
            db = "/:memory:"
            
        self.engine = create_engine('sqlite:///%s' % db)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
    def allFacts(self):
        return self.session.query(Factoid)
    
    def isCyclical(self, key, response):
        refs = ["@"+key,]
        
        while True:
            if not response.startswith("@"):
                return False
            
            split = response.split()
            key = split[0].lower()[1:]
            refs.append("@"+key)
            
            exists = self.session.query(Factoid).filter_by(keyword=key)
            if not exists.count():
                return False
            
            response = str(exists.first().response)
            
            if not response in refs:
                continue
            else:
                refs.append(response)
                return refs
        
    def addFact(self, key, response, replace=False):
        key = key.lower()
        exists = self.session.query(Factoid).filter_by(keyword=key)
        
        if exists:
            if not replace:
                raise FactoidAlreadyExists, key
        
        if exists.count():
            fact = exists.first()
            
            cycs = self.isCyclical(key, response)
            if cycs:
                raise CyclicalFactoid(cycs)
            
            fact.response = response
        else:
            fact = Factoid(key, response)
            
            cycs = self.isCyclical(key, response)
            if cycs:
                raise CyclicalFactoid(cycs)
            
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
        
        response = exists.first().response
        
        alias = False
        if response.startswith('@'):
            alias = response[1::]
            try:
                response = self.getFact(alias)
            except NoSuchFactoid, e:
                raise OrphanedFactoid, e
            
        if alias:
            return response
        
        return response

    def remFact(self, key):
        exists = self.session.query(Factoid).filter_by(keyword=key)

        if not exists.count():
            raise NoSuchFactoid, key

        self.session.delete(exists.first())
        self.session.commit()