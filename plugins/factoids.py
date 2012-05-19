from socbot.pluginbase import Base, BadParams, InsuffPerms # Required
from infobase import FactoidManager, NoSuchFactoid, FactoidAlreadyExists

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.factmanagers = {}
        
    def factManager(self, bot):
        if not bot.name().lower() in self.factmanagers:
            self.factmanagers[bot.name().lower()] = FactoidManager("conf/%s-factoids.db" % bot.name().lower())
        
        return self.factmanagers[bot.name().lower()]
    
    @Base.event("TRIG_UNKNOWN")
    def on_unknown(self, bot, user, details):
        try:
            response = self.factManager(bot).getFact(details['trigger'])
            bot.msg(details['channel'], response)
        except NoSuchFactoid, e:
            pass
    
    @Base.trigger("?")
    def on_whatis(self, bot, user, details):
        """? <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        try:
            response = self.factManager(bot).getFact(details['splitmsg'][0])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return str(response)
    
    @Base.trigger("?>", "TELLFACT")
    def on_tell(self, bot, user, details):
        """?> <nick> <id> - tell a user about a factoid"""
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        try:
            response = self.factManager(bot).getFact(details['splitmsg'][1])
        except NoSuchFactoid, e:
            response = "No such factoid!"
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("ADDFACT", "?+")
    def on_define(self, bot, user, details):
        """ADDFACT <id> <message> - define a factoid"""
        
        if not user.hasPerm('factoids.define'):
            raise InsuffPerms, "factoids.define"
        
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        self.factManager(bot).addFact(details['splitmsg'][0], ' '.join(details['splitmsg'][1::]), True)
            
        return "Factoid set."

    @Base.trigger("REMFACT", "?-")
    def on_remove(self, bot, user, details):
        """REMFACT <id> - remove a factoid"""
        
        if not user.hasPerm('factoids.remove'):
            raise InsuffPerms, "factoids.remove"
        
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        self.factManager(bot).remFact(details['splitmsg'][0])
            
        return "Factoid removed."