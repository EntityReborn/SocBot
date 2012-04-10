from socbot.pluginbase import Base, BadParams, InsuffPerms # Required
from infobase import FactoidManager, NoSuchFactoid, FactoidAlreadyExists

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.manager = FactoidManager('factoids.sqlite')
    
    @Base.event("TRIG_UNKNOWN")
    def on_unknown(self, bot, user, details):
        try:
            response = self.manager.getFact(details['trigger'])
            bot.msg(details['channel'], response)
        except NoSuchFactoid, e:
            pass
    
    @Base.trigger("?")
    def on_whatis(self, bot, user, details):
        """? <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        try:
            response = self.manager.getFact(details['splitmsg'][0])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return str(response)
    
    @Base.trigger("?>", "TELLFACT")
    def on_tell(self, bot, user, details):
        """?> <nick> <id> - tell a user about a factoid"""
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        try:
            response = self.manager.getFact(details['splitmsg'][1])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("ADDFACT", "+F")
    def on_define(self, bot, user, details):
        """ADDFACT <id> <message> - define a factoid"""
        
        if not user.hasPerm('factoids.define'):
            raise InsuffPerms, "factoids.define"
        
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        self.manager.addFact(details['splitmsg'][0], ' '.join(details['splitmsg'][1::]), True)
            
        return "Factoid set."

    @Base.trigger("REMFACT", "-F")
    def on_remove(self, bot, user, details):
        """REMFACT <id> - remove a factoid"""
        
        if not user.hasPerm('factoids.remove'):
            raise InsuffPerms, "factoids.remove"
        
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        self.manager.remFact(details['splitmsg'][0])
            
        return "Factoid removed."