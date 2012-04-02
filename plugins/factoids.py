from socbot.pluginbase import Base, BadParams # Required
from infobase import FactoidManager, NoSuchFactoid, FactoidAlreadyExists

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.manager = FactoidManager('factoids.sqlite')
        
    @Base.trigger("WHATIS", "?")
    def on_whatis(self, bot, user, details):
        """WHATIS <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            return BadParams
        
        try:
            response = self.manager.getFact(details['splitmsg'][0])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return str(response)
    
    @Base.trigger("TELL", "?>")
    def on_tell(self, bot, user, details):
        """TELL <nick> <id> - tell a user about a factoid"""
        if len(details['splitmsg']) < 2:
            return BadParams
        
        try:
            response = self.manager.getFact(details['splitmsg'][1])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("DEFFACT", "+F")
    def on_define(self, bot, user, details):
        """DEFFACT <id> <message> - define a factoid"""
        
        if not self.userHasPerm(user, 'factoids.define'):
            raise InsuffPerms, "factoids.define"
        
        if len(details['splitmsg']) < 2:
            return BadParams
        
        self.manager.addFact(details['splitmsg'][0], ' '.join(details['splitmsg'][1::]), True)
            
        return "Factoid set."

    @Base.trigger("REMFACT", "-F")
    def on_remove(self, bot, user, details):
        """REMFACT <id> - remove a factoid"""
        
        if not self.userHasPerm(user, 'factoids.remove'):
            raise InsuffPerms, "factoids.remove"
        
        if len(details['splitmsg']) < 1:
            return BadParams
        
        self.manager.remFact(details['splitmsg'][0])
            
        return "Factoid removed."