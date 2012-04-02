import logging
import os, sys
import traceback
from collections import defaultdict

from configobj import ConfigObj

from socbot.tools import validateConfig
import pluginbase

log = logging.getLogger('pluginmanager')

class MultipleTriggers(Exception): pass
class NoSuchPlugin(Exception): pass
class PluginAlreadyEnabled(Exception): pass
class PluginAlreadyDisabled(Exception): pass

class PluginManager(object):
    """A class in charge of managing the lifetime of a plugin"""
    def __init__(self, sstate, moduledir="plugins"):
        self.sstate = sstate
        self.moduledir = os.path.abspath(moduledir)
        self.moduleinfo = {}

        log.debug("PluginManager instantiated with '{0}' for "
            "moduledir.".format(self.moduledir))

        self.triggers = defaultdict(list)
        self.events = defaultdict(list)

    def registerTrigger(self, pluginname, func, *triggers):
        """Register a trigger to be called"""
        triggerline = ", ".join(triggers)
        log.debug("registering '{0}' for triggers '{1}'".format(
            func.__name__, triggerline))

        for trig in triggers:
            self.triggers[trig.upper()].append(func)

            mi = self.moduleinfo[pluginname.upper()]
            funclist = mi["trigfuncs"]
            funclist[trig.upper()] = func

    def registerEvent(self, pluginname, func, *events):
        eventline = ", ".join(events)
        log.debug("registering '{0}' for events '{1}'".format(
            func.__name__, eventline))

        for event in events:
            self.events[event.upper()].append(func)

            mi = self.moduleinfo[pluginname.upper()]
            funclist = mi["eventfuncs"]
            funclist[event.upper()] = func

    def removeTrigger(self, plugname, func, *triggers):
        triggerline = ", ".join(triggers)
        log.debug("removing '{0}' for triggers '{1}'".format(
            func.__name__, triggerline))

        pluginfo = self.moduleinfo[plugname.upper()]

        for trig in triggers:
            for data in self.triggers[trig.upper()]:
                if data == func:
                    self.triggers[trig.upper()].remove(data)

            if trig.upper() in pluginfo["trigfuncs"]:
                del pluginfo["trigfuncs"][trig.upper()]

    def removeEvent(self, plugname, func, *events):
        eventline = ", ".join(events)
        log.debug("removing '{0}' for events '{1}'".format(
            func.__name__, eventline))

        pluginfo = self.moduleinfo[plugname.upper()]

        for event in events:
            if func in self.triggers[event.upper()]:
                self.triggers[event.upper()].remove(func)

            if event.upper() in pluginfo["eventfuncs"]:
                del pluginfo["eventfuncs"].remove[event.upper()]

    def _funcByPath(self, dotpath):
        path = dotpath.split(".")

        if len(path) > 1:
            rootname = path[0].upper()

            if rootname in self.moduleinfo:
                root = self.moduleinfo[rootname]
                funcname = path[1].upper()

                if funcname in root["trigfuncs"]:
                    func = root["trigfuncs"][funcname]

                    return func

        return False

    def triggerByPath(self, dotpath, *args, **kwargs):
        log.debug("triggering by path '{0}'".format(dotpath))

        func = self._funcByPath(dotpath)

        if func:
            func(*args, **kwargs)
            return True
        else:
            log.error("path '{0}' not found".format(dotpath))
            return False


    def getTrigger(self, trigger):
        log.debug("triggering '{0}'".format(trigger))

        trigs = self.triggers[trigger.upper()]

        if len(trigs) > 1:
            raise MultipleTriggers, trigs
        elif not trigs:
            return False

        return trigs[0]


    def triggerEvent(self, event, *args, **kwargs):
        log.debug("triggering '{0}'".format(event))

        for func in self.events[event.upper()]:
            try:
                func(*args, **kwargs)
            except Exception:
                traceback.print_exc(5)

    def reloadPlugin(self, name):
        name = name.upper()

        if not name in self.moduleinfo:
            raise NoSuchPlugin, name

        self.moduleinfo[name]["instance"].beforeReload()
        self.disablePlug(name)
        self.enablePlug(name)
        self.moduleinfo[name]["instance"].afterReload()

    def reloadPlugins(self):
        log.debug("reloading plugins")

        for plug in self.moduleinfo.values():
            try:
                if "instance" in plug and plug["instance"]:
                    plug["instance"].beforeReload()
            except Exception:
                traceback.print_exc(5)

        self.finalizePlugins()
        self.loadPlugins()
        self.initPlugins()

        for plug in self.moduleinfo.values():
            try:
                plug["instance"].afterReload()
            except Exception:
                traceback.print_exc(5)

        return True

    def initPlugins(self):
        log.debug("initializing plugins")

        for plug in self.moduleinfo.values():
            try:
                if "instance" in plug and plug["instance"]:
                    plug["instance"].initialize()
            except Exception:
                traceback.print_exc(5)

    def finalizePlugins(self):
        log.debug("finalizing plugins")

        for plug in self.moduleinfo.values():
            try:
                if "instance" in plug and plug["instance"]:
                    plug["instance"].finalize()
            except Exception:
                traceback.print_exc(5)

        self.cleanup()

    def cleanup(self):
        log.debug("cleaning up plugins")

        self.triggers = defaultdict(list)
        self.events = defaultdict(list)
        self.moduleinfo = {}

    def enablePlug(self, name):
        log.debug("enabling plugin '{0}'".format(name))

        name = name.upper()

        if not name in self.moduleinfo:
            raise NoSuchPlugin, name

        moduleinfo = self.moduleinfo[name]

        if "instance" in moduleinfo and moduleinfo["instance"]:
            raise PluginAlreadyEnabled, name

        moduleinfo["info"]["general"]["enabled"] = True
        moduleinfo["info"].write()

        self._loadplugin(moduleinfo)

        moduleinfo["instance"].initialize()
        moduleinfo["instance"].enabled()

        return True

    def disablePlug(self, name):
        log.debug("disabling plugin '{0}'".format(name))

        name = name.upper()

        if not name in self.moduleinfo:
            raise NoSuchPlugin, name

        moduleinfo = self.moduleinfo[name]

        if not "instance" in moduleinfo or not moduleinfo["instance"]:
            raise PluginAlreadyDisabled, name

        moduleinfo["instance"].disabling()
        self._killplugin(moduleinfo)

        moduleinfo["info"]["general"]["enabled"] = False
        moduleinfo["info"].write()

        return True

    def loadPlugins(self):
        log.debug("loading plugins")

        self.finalizePlugins()

        if not self.moduledir in sys.path:
            sys.path.append(self.moduledir)

        moduleinfo = self._findPlugins() # [(ConfigObjInstance, modulefilename), ... ]

        for info, modulename in moduleinfo:
            try:
                moduleinfo = dict(file=modulename, info=info, trigfuncs=dict(), eventfuncs=dict())

                log.debug("loading plugin module - {0}".format(modulename))

                # Load new version of the module, using above globals
                self._loadplugin(moduleinfo)

            except Exception:
                traceback.print_exc(5)

    def _findPlugins(self):
        # Find modules using premade .info descriptor files.
        dirlist = os.listdir(self.moduledir)
        pairs = list() # ((info, modulefilename), ...)

        # Get all .info files
        infos = list(os.path.join(self.moduledir, m) for m in dirlist if m.endswith(".info"))
        log.debug("found infos: %s" % ", ".join(infos))

        for infofile in infos:
            info = ConfigObj(infofile, configspec=self.moduledir+"/plugin.spec")
            results = validateConfig(info)

            if results:
                line = ", ".join(results)
                log.error(line)

            # 'modulefile' defines the accompanying plugin code's module file
            if "modulefile" in info["general"]:
                # Get absolute path of module file
                filename = os.path.abspath(
                    os.path.join(self.moduledir,
                    info["general"]["modulefile"]))

                if os.path.exists(filename):
                    log.debug("adding %s to queue."%filename)
                    pairs.append((info, filename))
                else:
                    log.warning("could not find module file: %s"%filename)
            else:
                log.warning(
                    "info file '%s' doesn't contain 'modulefile' "
                    "descriptor"%infofile)

        return pairs

    def _getGlobals(self):
        g = {}
        return g

    def _loadplugin(self, moduleinfo):
        # get default globals for plugins
        env = self._getGlobals()

        try:
            execfile(moduleinfo["file"], env, env)
        except Exception, ex:
            log.exception("Exception in {0}".format(moduleinfo["file"]))

        moduleinfo["env"] = env

        if env.has_key("Plugin") and \
              issubclass(env["Plugin"], pluginbase.Base):
            klass = moduleinfo["env"]["Plugin"]

            name = moduleinfo["info"]["general"]["name"]
            self.moduleinfo[name.upper()] = moduleinfo

            if moduleinfo["info"]["general"]["enabled"]:
                instance = moduleinfo["instance"] = klass(self, moduleinfo, self.sstate['users'])
                instance._initTrigs()
            else:
                log.info("plugin {0} is disabled in it's config. Not instantiating it.".format(
                    name))

        else:
            log.warning("Class 'Plugin' doesn't exist in module {0}, "
                "or it doesn't subclass the defined "
                "interface.".format(moduleinfo["file"]))

    def _killplugin(self, moduleinfo):
        moduleinfo["instance"].finalize()

        for key, func in moduleinfo["trigfuncs"].iteritems():
            key = key.upper()

            if key in self.triggers:
                if func in self.triggers[key]:
                    self.triggers[key].remove(func)

        moduleinfo["trigfuncs"] = dict()

        for key, func in moduleinfo["eventfuncs"].iteritems():
            key = key.upper()

            if key in self.events:
                if func in self.events[key]:
                    self.events[key].remove(func)

        moduleinfo["eventfuncs"] = dict()

        del moduleinfo["env"]
        del moduleinfo["instance"]
