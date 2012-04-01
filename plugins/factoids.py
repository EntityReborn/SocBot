from socbot.pluginbase import Base # Required
from infobase import FactoidManager, NoSuchFactoid, FactoidAlreadyExists

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.manager = FactoidManager('factoids.sqlite')
        
    @Base.trigger("WHATIS")
    def on_whatis(self, bot, user, details):
        """WHATIS <id> - say a factoid"""
        try:
            response = self.manager.getFact(details['splitmsg'][0])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return str(response)
    
    @Base.trigger("DEFINE")
    def on_define(self, bot, user, details):
        """DEFINE <id> <message> - define a factoid"""
        self.manager.addFact(details['splitmsg'][0], ' '.join(details['splitmsg'][1::]), True)
            
        return "Factoid set."
