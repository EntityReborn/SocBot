from socbot.pluginbase import Base, BadParams, InsuffPerms # Required
import factoidbase
    
import sys

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.factmanagers = {}
        
        confdir = self.getDataDir()
        self.globalmanager = factoidbase.FactoidManager("%s/%s" % (confdir, "global.db"))
        
    def preReload(self, *args, **kwargs):
        del self.factmanagers
        del self.globalmanager
        reload(factoidbase)
        
    def factManager(self, bot):
        if not bot.name().lower() in self.factmanagers:
            confdir = self.getDataDir()
            file = "%s/%s-factoids.db" % (confdir, bot.name().lower())
            self.manager.log.info("loading factoids from %s" % file)
            self.factmanagers[bot.name().lower()] = factoidbase.FactoidManager(file)
        
        return self.factmanagers[bot.name().lower()]
    
    def getFact(self, bot, fact):
        try:
            response = self.factManager(bot).getFact(fact)
        except factoidbase.NoSuchFactoid, e:
            response = self.globalmanager.getFact(fact)
            
        return response
    
    @Base.event("TRIG_UNKNOWN")
    def on_unknown(self, bot, user, details):
        try:
            response = self.getFact(bot, details['trigger'])
            
            bot.msg(details['channel'], response)
        except factoidbase.NoSuchFactoid, e:
            pass
    
    @Base.trigger("?")
    def on_whatis(self, bot, user, details):
        """? <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        key = details['splitmsg'][0]
        
        try:
            response = self.getFact(bot, key)    
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except factoidbase.OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
            
        return str(response)
    
    @Base.trigger("FACTLIST", "LISTFACTS")
    def on_list(self, bot, user, details):
        """FACTLIST [-g] - list available factoids. Use -g to list global factoids"""
        
        isglobal = len(details['splitmsg']) and details['splitmsg'][0].lower() == "-g"
        
        if not isglobal:
            facts = self.factManager(bot).allFacts()
        else:   
            facts = self.globalmanager.allFacts()
        
        if facts:
            retn = ", ".join([f.keyword for f in facts])
        else:
            retn = "No factoids."
            
        bot.notice(user.username(), retn)
    
    @Base.trigger("?>", "TELLFACT")
    def on_tell(self, bot, user, details):
        """?> <nick> <id> - tell a user about a factoid"""
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        key = details['splitmsg'][1]
        
        try:
            response = self.getFact(bot, key) 
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except factoidbase.OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("ADDFACT", "?+")
    def on_define(self, bot, user, details):
        """ADDFACT [-g] <id> <message> - define a factoid. Use -g to define a global factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if paramcount < 2:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        
        if isglobal and paramcount < 3:
            raise BadParams
        
        if not user.hasPerm('factoids.define') and not isglobal:
            raise InsuffPerms, "factoids.define"
        elif not user.hasPerm('factoids.define.global') and isglobal:
            raise InsuffPerms, "factoids.define.global"
        
        try:
            if not isglobal:
                self.factManager(bot).addFact(details['splitmsg'][0], ' '.join(details['splitmsg'][1::]), True)
            else:
                self.globalmanager.addFact(details['splitmsg'][1], ' '.join(details['splitmsg'][2::]), True)
        except factoidbase.CyclicalFactoid as e:
            return "Recursive factoid! Not saving. (Resulting chain would be `%s`)" % " -> ".join(e.lst)
        except factoidbase.OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
          
        return "Factoid set."

    @Base.trigger("REMFACT", "?-")
    def on_remove(self, bot, user, details):
        """REMFACT [-g] <id> - remove a factoid. Use -g to remove a global factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if paramcount < 1:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        
        if paramcount < 2 and isglobal:
            raise BadParams
        
        if not user.hasPerm('factoids.remove') and not isglobal:
            raise InsuffPerms, "factoids.remove"
        if not user.hasPerm('factoids.remove.global') and isglobal:
            raise InsuffPerms, "factoids.remove.global"
        
        try:
            if not isglobal:
                self.factManager(bot).remFact(details['splitmsg'][0])
            else:
                self.globalmanager.remFact(details['splitmsg'][1])
        except factoidbase.NoSuchFactoid, e:
            return "Unknown factoid, '%s'" % e
        
        return "Factoid removed."