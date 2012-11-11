from socbot.pluginbase import Base, BadParams# Required
import factoidbase

class CyclicalFactoid(factoidbase.FactoidException): 
    def __init__(self, lst):
        self.lst = lst
        
class OrphanedFactoid(factoidbase.FactoidException): pass

class FactType():
    def __init__(self, p):
        self.parts = p
    
    def isGlobal(self):
        val = len(self.parts) > 0 and self.parts[0].lower() == "-g"
        return val
    
    def isNetwork(self):
        val = len(self.parts) > 0 and self.parts[0].lower() == "-n"
        return val
    
    def isChannel(self):
        val = not self.isGlobal() and not self.isNetwork()
        return val
    
    def isValid(self):
        return self.isGlobal() or self.isNetwork() or self.isChannel()
    
    def getParts(self):
        if self.isGlobal() or self.isNetwork():
            return self.parts[1:]
        
        return self.parts

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        self.factmanagers = {}
        
        confdir = self.getDataDir()
        self.globalmanager = factoidbase.FactoidManager("%s/%s" % (confdir, "global.db"))
        
    def preReload(self, *args, **kwargs):
        del self.factmanagers
        del self.globalmanager
        reload(factoidbase)
        
    def factManager(self, bot, channel=None):
        if not channel:
            f = "%s-factoids.db" % (bot.name().lower())
        else:
            f = "%s-%s-factoids.db" % (bot.name().lower(), channel.lower())

        if not f in self.factmanagers:
            confdir = self.getDataDir()  
                      
            self.manager.log.info("loading factoids from %s" % f)
            self.factmanagers[f] = factoidbase.FactoidManager("%s/%s" % (confdir, f))

        return self.factmanagers[f]
    
    def getType(self, parts):
        return FactType(parts)
    
    def getFact(self, bot, details, key, reflist=None):
        key = key.encode('UTF-8').lower()
        
        if reflist == None:
            reflist = []
        
        if "@"+key in reflist:
            raise CyclicalFactoid, key
        
        if reflist == None:
            reflist = ["@"+key,]
        
        try:
            fact = self.factManager(bot, details['channel']).getFact(key)
        except factoidbase.NoSuchFactoid, e:
            try:
                fact = self.factManager(bot).getFact(key)
            except factoidbase.NoSuchFactoid, e:
                fact = self.globalmanager.getFact(key)
                
        response = fact.getResponse()
        
        alias = False
        if response.startswith('@'):
            alias = response.split()[0][1::]
            
            try:
                response = self.getFact(bot, details, alias, reflist)
            except factoidbase.NoSuchFactoid, e:
                raise OrphanedFactoid, e
            
            reflist.append("@"+alias)
                
        return response
    
    @Base.event("TRIG_UNKNOWN")
    def on_unknown(self, bot, user, details):
        try:
            response = self.getFact(bot, details, details['trigger'])
            
            bot.msg(details['channel'], response)
        except OrphanedFactoid, e:
            bot.msg(details['channel'], "Orphaned factoid alias. (This factoid eventually looks for `%s`, which is unknown.)" % e)
        except factoidbase.FactoidException, e:
            pass
    
    @Base.trigger("WHATIS")
    def on_whatis(self, bot, user, details):
        """WHATIS <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        key = details['splitmsg'][0]
        
        try:
            response = self.getFact(bot, details, key)    
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
        except CyclicalFactoid as e:
            return "Cyclical factoid: %s" % " -> ".join(e.lst)
            
        return str(response)
    
    @Base.trigger("LIST")
    def on_list(self, bot, user, details):
        """LIST [-g|-n|<channel>] - list available factoids. Use -g to list global factoids, and -n to list network factoids."""
        
        facttype = self.getType(details['splitmsg'])
        parts = facttype.getParts()
        
        if facttype.isGlobal():
            facts = self.globalmanager.allFacts()
        elif facttype.isNetwork():   
            facts = self.factManager(bot).allFacts()
        elif facttype.isChannel():
            if len(parts):
                channel = parts[0].lower()
            else:
                channel = details['channel']
                
            facts = self.factManager(bot, channel).allFacts()
        
        if facts.count():
            if facttype.isChannel():
                prefix = "Channel factoids for %s: " % details['channel']
            elif facttype.isNetwork():
                prefix = "Network factoids for %s: " % bot.name()
            elif facttype.isGlobal():
                prefix = "Global factoids: "
                
            bot.msg(user.username(), prefix + ", ".join(sorted([f.keyword.lower() for f in facts])))
            
            return "Please see the private message I sent you. (this helps keep channel spam down)"
        else:
            return "No factoids to be shown."

    @Base.trigger("TELL")
    def on_tell(self, bot, user, details):
        """TELL <nick> <id> - tell a user about a factoid"""
        
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        key = details['splitmsg'][1]
        
        try:
            response = self.getFact(bot, details, key) 
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
        except CyclicalFactoid as e:
            return "Cyclical factoid: %s" % " -> ".join(e.lst)
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("ADD")
    def on_add(self, bot, user, details):
        """ADD [-g|-n] <id> <message> - define a factoid. Use -g to define a global factoid, and -n to define a network factoid"""

        facttype = self.getType(details['splitmsg'])
        
        if not facttype.isValid():
            raise BadParams
        
        parts = facttype.getParts()
        
        if facttype.isGlobal():
            user.assertPerm('factoids.global.add')
            manager = self.globalmanager
        elif facttype.isNetwork():
            user.assertPerm('factoids.network.add')
            manager = self.factManager(bot)
        else:
            user.assertPerm('factoids.add')
            manager = self.factManager(bot, details['channel'])
        
        trigger = parts[0]
        data = ' '.join(parts[1::])
           
        try:
            oldfact = manager.getFact(trigger)
        except factoidbase.NoSuchFactoid:
            oldfact = None
        
        ismyfact = not oldfact or (oldfact and oldfact.createdby.lower() == user.username().lower())
        
        overrideslock = (facttype.isGlobal() and user.hasPerm("factoids.global.lock.override")) or \
            (facttype.isNetwork() and user.hasPerm("factoids.network.lock.override")) or \
            (facttype.isChannel() and user.hasPerm("factoids.lock.override"))

        if not oldfact or (oldfact and not oldfact.locked) or \
        ismyfact or overrideslock:
            if oldfact and not ismyfact:
                user.assertPerm("factoids.update")
                
            fact = manager.addFact(trigger, data, True)
        else:
            return "That factoid is locked! (by %s)" % oldfact.lockedby

        if not oldfact:
            fact.createdby = user.username().lower()
        else:
            fact.alteredby = user.username().lower()
        
        manager.save()
          
        return "Factoid set."
    
    @Base.trigger("LOCK")
    def on_lock(self, bot, user, details):
        """LOCK [-g|-n] <id> - lock a factoid. Use -g to lock a global factoid, and -n to lock a network factoid"""
        
        facttype = self.getType(details['splitmsg'])
        
        if not facttype.isValid():
            raise BadParams
        
        parts = facttype.getParts()
        
        if facttype.isGlobal():
            user.assertPerm('factoids.global.lock')
            manager = self.globalmanager
        elif facttype.isNetwork():
            user.assertPerm('factoids.network.lock')
            manager = self.factManager(bot)
        else:
            user.assertPerm('factoids.lock')
            manager = self.factManager(bot, details['channel'])
        
        oldfact = None
        try:
            oldfact = manager.getFactObj(parts[0])
        except factoidbase.NoSuchFactoid, e:
            return "No such factoid. (%s)" % e
        
        if oldfact.locked:
            return "That factoid is already locked. (by %s)" % oldfact.lockedby

        oldfact.locked = True
        oldfact.lockedby = user.username()

        manager.save()
          
        return "Factoid locked."
    
    @Base.trigger("UNLOCK")
    def on_unlock(self, bot, user, details):
        """UNLOCK [-g|-n] <id> - lock a factoid. Use -g to unlock a global factoid, and -n to unlock a network factoid"""
        
        facttype = self.getType(details['splitmsg'])
        
        if not facttype.isValid():
            raise BadParams
        
        parts = facttype.getParts()
        
        if facttype.isGlobal():
            user.assertPerm('factoids.global.lock')
            manager = self.globalmanager
        elif facttype.isNetwork():
            user.assertPerm('factoids.network.lock')
            manager = self.factManager(bot)
        else:
            user.assertPerm('factoids.lock')
            manager = self.factManager(bot, details['channel'])
            
        trigger = parts[0]
            
        oldfact = None
        try:
            oldfact = manager.getFactObj(trigger)
        except factoidbase.NoSuchFactoid, e:
            return "No such factoid. (%s)" % e
        
        if not oldfact.locked:
            return "That factoid is not locked."

        oldfact.locked = False
        oldfact.lockedby = None

        manager.save()
          
        return "Factoid unlocked."

    @Base.trigger("REM")
    def on_remove(self, bot, user, details):
        """REM [-g|-n] <id> - remove a factoid. Use -g to remove a global factoid, and -n for a network factoid"""
        
        facttype = self.getType(details['splitmsg'])
        
        if not facttype.isValid():
            raise BadParams
        
        parts = facttype.getParts()
        
        trigger = parts[0]
        
        try:
            if facttype.isGlobal():
                user.assertPerm('factoids.global.remove')
                self.globalmanager.remFact(trigger)
            elif facttype.isNetwork():
                user.assertPerm('factoids.network.remove')
                self.factManager(bot).remFact(trigger)
            else:
                user.assertPerm('factoids.remove')
                self.factManager(bot, details['channel']).remFact(trigger)
                
        except factoidbase.NoSuchFactoid, e:
            return "Unknown factoid, '%s'" % e
        
        return "Factoid removed."