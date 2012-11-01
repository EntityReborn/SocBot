from socbot.pluginbase import Base, BadParams# Required
import factoidbase

class CyclicalFactoid(factoidbase.FactoidException): 
    def __init__(self, lst):
        self.lst = lst
        
class OrphanedFactoid(factoidbase.FactoidException): pass

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
        if not bot.name().lower() in self.factmanagers:
            confdir = self.getDataDir()
            
            if not channel:
                f = "%s/%s-factoids.db" % (confdir, bot.name().lower())
            else:
                f = "%s/%s-%s-factoids.db" % (confdir, bot.name().lower(), channel.lower())
                
            self.manager.log.info("loading factoids from %s" % f)
            self.factmanagers[bot.name().lower()] = factoidbase.FactoidManager(f)
        
        return self.factmanagers[bot.name().lower()]
    
    def getFact(self, bot, details, key, reflist=None):
        key = key.lower()
        
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
                
        response = fact.response
        
        alias = False
        if response.startswith('@'):
            alias = response.split()[0][1::]
            
            try:
                response = self.getFact(bot, details, alias, reflist)
            except factoidbase.NoSuchFactoid, e:
                raise OrphanedFactoid, e
            
            reflist.append("@"+alias)
            
        if alias:
            return response
                
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
    
    @Base.trigger("?")
    def on_whatis(self, bot, user, details):
        """? <id> - say a factoid"""
        if len(details['splitmsg']) < 1:
            raise BadParams
        
        key = details['splitmsg'][0]
        
        try:
            response = self.getFact(bot, details, key)    
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
            
        return str(response)
    
    @Base.trigger("?LIST", "FACTLIST", "LISTFACTS")
    def on_list(self, bot, user, details):
        """FACTLIST [-g|-n|<channel>] - list available factoids. Use -g to list global factoids, and -n to list network factoids."""
        
        isglobal = len(details['splitmsg']) and details['splitmsg'][0].lower() == "-g"
        isnetwork = len(details['splitmsg']) and details['splitmsg'][0].lower() == "-n"
        
        if isglobal:
            facts = self.globalmanager.allFacts()
        elif isnetwork:   
            facts = self.factManager(bot).allFacts()
        else:
            if len(details['splitmsg']):
                channel = details['splitmsg'][0].lower()
            else:
                channel = details['channel']
                
            facts = self.factManager(bot, channel).allFacts()
        
        if facts.count():
            bot.msg(user.username(), ", ".join(sorted([f.keyword.lower() for f in facts])))
            return "Please see the private message I sent you. (this helps keep channel spam down)"
        else:
            return "No factoids to be shown."

    @Base.trigger("?>", "TELLFACT")
    def on_tell(self, bot, user, details):
        """TELLFACT <nick> <id> - tell a user about a factoid"""
        if len(details['splitmsg']) < 2:
            raise BadParams
        
        key = details['splitmsg'][1]
        
        try:
            response = self.getFact(bot, details, key) 
        except factoidbase.NoSuchFactoid, e:
            response = "No such factoid! (%s)" % key
        except OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
            
        return '%s: %s' % (details['splitmsg'][0], str(response))
    
    @Base.trigger("ADDFACT", "?+")
    def on_define(self, bot, user, details):
        """ADDFACT [-g|-n] <id> <message> - define a factoid. Use -g to define a global factoid, and -n to define a network factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if paramcount < 2:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        isnetwork = details['splitmsg'][0].lower() == "-n"
        
        if (isglobal or isnetwork) and paramcount < 3:
            raise BadParams
        
        if isglobal:
            user.assertPerm('factoids.global.define')
            manager = self.globalmanager
            trigger = details['splitmsg'][1]
            data = ' '.join(details['splitmsg'][2::])
        elif isnetwork:
            user.assertPerm('factoids.network.define')
            manager = self.factManager(bot)
            trigger = details['splitmsg'][1]
            data = ' '.join(details['splitmsg'][2::])
        else:
            user.assertPerm('factoids.define')
            manager = self.factManager(bot, details['channel'])
            trigger = details['splitmsg'][0]
            data = ' '.join(details['splitmsg'][1::])
            
        oldfact = None
        try:
            oldfact = manager.getFact(trigger)
        except factoidbase.NoSuchFactoid, e:
            pass
        
        try:
            if not oldfact or (oldfact and not oldfact.locked) or \
            (isglobal and user.hasPerm("factoids.global.lock.override")) or \
            (isnetwork and user.hasPerm("factoids.network.lock.override")) or \
            (not isglobal and not isnetwork and user.hasPerm("factoids.lock.override")):
                fact = manager.addFact(trigger, data, True)
            else:
                return "That factoid is locked! (by %s)" % oldfact.lockedby
            
        except CyclicalFactoid as e:
            return "Recursive factoid! Not saving. (Resulting chain would be `%s`)" % " -> ".join(e.lst)
        except OrphanedFactoid, e:
            return "Orphaned factoid alias in chain. Not saving. (Orphaned alias is `%s`)" % e
        
        if not oldfact:
            fact.createdby = user.username()
        else:
            fact.alteredby = user.username()
        
        manager.save()
          
        return "Factoid set."
    
    @Base.trigger("LOCKFACT", "?L", "?LOCK")
    def on_lock(self, bot, user, details):
        """LOCKFACT [-g|-n] <id> - lock a factoid. Use -g to lock a global factoid, and -n to lock a network factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if not paramcount:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        isnetwork = details['splitmsg'][0].lower() == "-n"
        
        if (isglobal or isnetwork) and paramcount < 2:
            raise BadParams
        
        if isglobal:
            user.assertPerm('factoids.global.lock')
            manager = self.globalmanager
            trigger = details['splitmsg'][1]
        elif isnetwork:
            user.assertPerm('factoids.network.lock')
            manager = self.factManager(bot)
            trigger = details['splitmsg'][1]
        else:
            user.assertPerm('factoids.lock')
            manager = self.factManager(bot, details['channel'])
            trigger = details['splitmsg'][0]
        
        oldfact = None
        try:
            oldfact = manager.getFactObj(trigger)
        except factoidbase.NoSuchFactoid, e:
            return "No such factoid. (%s)" % e
        
        if oldfact.locked:
            return "That factoid is already locked. (by %s)" % oldfact.lockedby

        oldfact.locked = True
        oldfact.lockedby = user.username()

        manager.save()
          
        return "Factoid locked."
    
    @Base.trigger("UNLOCKFACT", "?U", "?UNLOCK")
    def on_unlock(self, bot, user, details):
        """UNLOCKFACT [-g|-n] <id> - lock a factoid. Use -g to unlock a global factoid, and -n to unlock a network factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if not paramcount:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        isnetwork = details['splitmsg'][0].lower() == "-n"
        
        if (isglobal or isnetwork) and paramcount < 2:
            raise BadParams
        
        if isglobal:
            user.assertPerm('factoids.global.lock')
            manager = self.globalmanager
            trigger = details['splitmsg'][1]
        elif isnetwork:
            user.assertPerm('factoids.network.lock')
            manager = self.factManager(bot)
            trigger = details['splitmsg'][1]
        else:
            user.assertPerm('factoids.lock')
            manager = self.factManager(bot, details['channel'])
            trigger = details['splitmsg'][0]
            
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

    @Base.trigger("REMFACT", "?-")
    def on_remove(self, bot, user, details):
        """REMFACT [-g|-n] <id> - remove a factoid. Use -g to remove a global factoid, and -n for a network factoid"""
        
        paramcount = len(details['splitmsg'])
        
        if paramcount < 1:
            raise BadParams
        
        isglobal = details['splitmsg'][0].lower() == "-g"
        isnetwork = details['splitmsg'][0].lower() == "-n"
        
        if paramcount < 2 and (isglobal or isnetwork):
            raise BadParams
        
        try:
            if isglobal:
                user.assertPerm('factoids.global.remove')
                self.globalmanager.remFact(details['splitmsg'][1])
            elif isnetwork:
                user.assertPerm('factoids.network.remove')
                self.factManager(bot).remFact(details['splitmsg'][0])
            else:
                user.assertPerm('factoids.remove')
                self.factManager(bot, details['channel']).remFact(details['splitmsg'][0])
        except factoidbase.NoSuchFactoid, e:
            return "Unknown factoid, '%s'" % e
        
        return "Factoid removed."