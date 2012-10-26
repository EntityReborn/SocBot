import logging
import os, sys
from collections import defaultdict

from socbot.config import ConfigurationFile

import pluginbase

log = logging.getLogger('pluginmanager')

class MultipleTriggers(Exception): pass
class NoSuchPlugin(Exception): pass
class PluginAlreadyLoaded(Exception): pass
class PluginNotLoaded(Exception): pass
class UnregisterEvent(Exception): pass
class UnregisterTrigger(Exception): pass
class UnregisterPrefilter(Exception): pass

class PluginTracker(object):
    def __init__(self, core, info, filename):
        self.core = core
        self.msgprefilters = []
        self.eventprefilters = []
        self.events = defaultdict(list)
        self.triggers = {}
        self.info = info
        self.filename = filename
        self._instance = None
        self._env = {}
        self.log = log
    
    def getDataDir(self):
        return self.core.sstate['config']['directories']['plugindata']
        
    def hasTrigger(self, trig):
        return trig.upper() in self.triggers.keys() and self.triggers[trig.upper()]
    
    def hasEvent(self, event):
        return event.upper() in self.events.keys() and self.events[event.upper()]
    
    def getEventPreFilters(self):
        return sorted(self.eventprefilters)
    
    def getMsgPreFilters(self):
        return sorted(self.msgprefilters)
    
    def getTrigger(self, trig):
        trig = trig.upper()
        
        if trig in self.triggers.keys():
            return self.triggers[trig]
        
    def getTriggers(self):
        return [trig.upper() for trig in self.triggers.keys() if not self.triggers[trig.upper()].hidden]
    
    def getEvent(self, event):
        event = event.upper()
        
        if event in self.events.keys():
            return self.events[event]
    
    def fireTrigger(self, trig, *args):
        trig = trig.upper()
        
        if trig in self.triggers.keys():
            func = self.triggers[trig]
            
            try:
                func(*args)
            except UnregisterTrigger:
                self.removeTrigger(func, trig)
            
    def fireEvent(self, event, *args):
        event = event.upper()
        
        if event in self.events.keys():
            funcs = self.events[event]
            
            for func in funcs:
                try:
                    func(*args)
                except UnregisterEvent:
                    self.removeEvent(func, event)
            
    def initialize(self):
        if self.isLoaded():
            self._instance.initialize()
            
    def finalize(self):
        if self.isLoaded():
            self._instance.finalize()
        
    def isLoaded(self):
        try:
            return self._instance != None
        except AttributeError:
            return False
    
    def preReload(self):
        try:
            self._instance.preReload()
        except Exception:
            log.exception("Exception unloading plugin %s" % self.filename)
            
    def postReload(self):
        try:
            self._instance.postReload()
        except Exception:
            log.exception("Exception unloading plugin %s" % self.filename)
        
    def load(self):
        env = {}

        try:
            execfile(self.filename, env, env)
        except Exception:
            log.exception("Exception loading plugin in {0}".format(self.filename))
            return

        if env.has_key("Plugin") and \
        issubclass(env["Plugin"], pluginbase.Base):
            klass = env["Plugin"]

            name = self.info["general"]["name"]

            if self.info["general"]["enabled"]:
                self._instance = klass(self, self.info)
                self._env = env
                self._instance._initTrigs()
            else:
                log.info("Plugin `{0}` is disabled in it's config. Not instantiating it.".format(
                    name))

        else:
            log.warning("Class 'Plugin' doesn't exist in module `{0}`, ".format(self.filename) + \
                "or it doesn't subclass the defined baseclass.")
    
    def unload(self):
        if not self.isLoaded():
            return
        
        try:
            self._instance.finalize()
        except Exception:
            log.exception("Exception unloading plugin `%s`" % self.filename)

        self.triggers = {}
        self.events = defaultdict(list)
        
        del self._env
        del self._instance
        
    def reload(self):
        self.preReload()
        self.unload()
        self.load()
        self.initialize()
        self.postReload()
        
    def registerTrigger(self, pluginname, func, *triggers):
        triggerline = ", ".join(triggers)
        log.debug("registering '{0}' for triggers '{1}'".format(
            func.__name__, triggerline))

        for trig in triggers:
            self.triggers[trig.upper()] = func
            
    def registerMsgPreFilter(self, pluginname, func, priority):
        log.debug("registering '{0}' for msg prefilters with priority {1}".format(
            func.__name__, func.priority))
        
        self.msgprefilters.append([func.priority, func])
        
    def registerEventPreFilter(self, pluginname, func, priority):
        log.debug("registering '{0}' for event prefilters with priority {1}".format(
            func.__name__, func.priority))
        
        self.eventprefilters.append([func.priority, func])
        
    def registerEvent(self, pluginname, func, *events):
        eventline = ", ".join(events)
        log.debug("registering '{0}' for events '{1}'".format(
            func.__name__, eventline))

        for event in events:
            self.events[event.upper()].append(func)

    def removeTrigger(self, func, *triggers):
        triggerline = ", ".join(triggers)
        log.debug("removing '{0}' for triggers '{1}'".format(
            func.__name__, triggerline))

        for trig in triggers:
            if self.triggers[trig.upper()] == func:
                del self.triggers[trig.upper()]

    def removeEvent(self, func, *events):
        eventline = ", ".join(events)
        log.debug("removing '{0}' for events '{1}'".format(
            func.__name__, eventline))

        for event in events:
            if func in self.events[event.upper()]:
                self.events[event.upper()].remove(func)

class PluginCore(object):
    """A class in charge of managing the lifetime of a plugin"""
    def __init__(self, sstate, moduledir="plugins"):
        self.sstate = sstate
        self.log = log
        self.moduledir = os.path.abspath(moduledir)
        self.plugintrackers = {}

        log.debug("PluginManager instantiated with '{0}' for "
            "moduledir.".format(self.moduledir))
        
    def getMsgPrefilters(self):
        flt = list()
        
        for tracker in self.plugintrackers.values():
            flt += tracker.getMsgPreFilters()
            
        return [x[1] for x in sorted(flt)]
    
    def getEventPrefilters(self):
        flt = list()
        
        for tracker in self.plugintrackers.values():
            flt += tracker.getEventPreFilters()
            
        return [x[1] for x in sorted(flt)]
        
    def getAllTriggers(self):
        trigs = list()
        
        for tracker in self.plugintrackers.values():
            trigs += tracker.getTriggers()
            
        return set(trigs)
                
    def getTrigger(self, trigger):
        log.debug("triggering '{0}'".format(trigger))

        trigs = list()
        
        for tracker in self.plugintrackers.values():
            if tracker.hasTrigger(trigger):
                trigs.append(tracker.getTrigger(trigger))

        if len(trigs) > 1:
            raise MultipleTriggers, trigs
        elif not trigs:
            return False

        return trigs[0]

    def triggerEvent(self, event, *args):
        log.debug("triggering '{0}'".format(event))
        self._event_blocked = False
        hadevent = False

        for tracker in self.plugintrackers.values():
            if tracker.hasEvent(event):
                hadevent = True
                
                try:
                    tracker.fireEvent(event, *args)
                except Exception:
                    log.exception("exception firing %s in %s" % (event, tracker.filename))
                
        return hadevent

    def reloadPlugin(self, name):
        name = name.lower()

        if not name in self.plugintrackers.keys():
            raise NoSuchPlugin, name
        
        tracker = self.plugintrackers[name]
        
        try:
            tracker.reload()
        except Exception:
            log.exception("exception reloading plugin %s" % name)

    def reloadPlugins(self):
        log.debug("reloading plugins")

        for name, tracker in self.plugintrackers.iteritems():
            try:
                if tracker.isLoaded():
                    tracker.preReload()
            except Exception:
                log.exception("exception pre-reloading plugin %s" % name)

        self.finalizePlugins()
        self.loadPlugins()
        self.initPlugins()

        for name, tracker in self.plugintrackers.iteritems():
            try:
                if tracker.isLoaded():
                    tracker.postReload()
            except Exception:
                log.exception("exception post-reloading plugin %s" % name)

        return True

    def initPlugins(self):
        log.debug("initializing plugins")

        for name, tracker in self.plugintrackers.iteritems():
            try:
                if tracker.isLoaded():
                    tracker.initialize()
            except Exception:
                log.exception("exception initing plugin %s" % name)

    def finalizePlugins(self):
        log.debug("finalizing plugins")

        for name, tracker in self.plugintrackers.iteritems():
            try:
                if tracker.isLoaded():
                    tracker.finalize()
            except Exception:
                log.exception("exception finalizing plugin in %s" % name)

    def enablePlug(self, name):
        name = name.lower()
        
        log.debug("enabling plugin '{0}'".format(name))

        if not name in self.plugintrackers.keys():
            raise NoSuchPlugin, name

        tracker = self.plugintrackers[name]

        if tracker.isLoaded():
            raise PluginAlreadyLoaded, name
        
        tracker.info.reload()
        tracker.info["general"]["enabled"] = True
        tracker.info.write()

        tracker.load()
        tracker.initialize()

        return True

    def disablePlug(self, name):
        name = name.lower()
        
        log.debug("disabling plugin '{0}'".format(name))

        if not name in self.plugintrackers.keys():
            raise NoSuchPlugin, name

        tracker = self.plugintrackers[name]

        if not tracker.isLoaded():
            raise PluginNotLoaded, name

        tracker.unload()
        
        tracker.info.reload()
        tracker.info["general"]["enabled"] = False
        tracker.info.write()

        return True

    def loadPlugins(self):
        log.debug("loading plugins")

        self.finalizePlugins()

        if not self.moduledir in sys.path:
            sys.path.append(self.moduledir)

        if not self.plugintrackers:
            self.plugintrackers = self.findPlugins()
        
        for name, tracker in self.plugintrackers.iteritems():
            try:
                log.debug("loading plugin module - {0}".format(name))
                tracker.load()
            except Exception:
                log.exception("exception loading plugin %s"%tracker.filename)
                
        for name, tracker in self.plugintrackers.iteritems():
            try:
                tracker.initialize()
            except Exception:
                log.exception("exception loading plugin %s"%tracker.filename)

    def findPlugins(self):
        # Find modules using premade .info descriptor files.
        filelist = os.listdir(self.moduledir)
        plugindata = {}
        
        infos = list(os.path.join(self.moduledir, m) for m in filelist if m.endswith(".info"))
        log.debug("found infos: %s" % ", ".join(infos))
        
        spec = "conf/plugin.spec"

        for infofile in infos:
            info = ConfigurationFile(infofile, configspec=spec)
            errors = info.isValid()

            if errors:
                line = ", ".join(errors)
                log.error(line)
                continue
            
            geninfo = info["general"]
            
            # Get absolute path of module file
            filename = os.path.abspath(
                os.path.join(self.moduledir,
                geninfo["modulefile"]))

            if os.path.exists(filename):
                log.debug("adding %s to queue."%filename)
                plugindata[geninfo['name'].lower()] = PluginTracker(self, info, filename)
            else:
                log.warning("could not find module file: %s"%filename)

        return plugindata