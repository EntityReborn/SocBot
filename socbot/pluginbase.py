from inspect import getmembers, ismethod
import os

from socbot.config import ConfigurationFile

class InsuffPerms(Exception):
    """The user does not have the required permissions"""

class BadParams(Exception):
    """The supplied parameters are not correct"""
    
class DoesntUseConfig(Exception):
    """This plugin says it doesn't use a config file"""
    
class InvalidConfig(Exception):
    """The config file doesn't match specifications for the values it contains"""

class Base(object):
    def __init__(self, manager, info):
        self.manager = manager
        self.info = info
        
        name = self.info['general']['name'].lower()
            
        maindir = self.manager.getDataDir()
        self._datadir = '%s/%s' % (maindir, name)
        
        if not os.path.exists(self._datadir):
            os.makedirs(self._datadir)
            
    def getDataDir(self):
        return self._datadir
                
    def getConfig(self):
        if self.info['general']['usesconfig']:
            if self.info['general']['usesconfspec']:
                conf = ConfigurationFile('%s/config.conf' % self._datadir, configspec="plugins/%s.spec" % self.info['general']['name'].lower())

                errors = conf.isValid()
                if errors:
                    self.manager.log.error("Error in config for %s:" % self.info['general']['name'])
                    self.manager.log.error('\n'.join(errors))
                    
                    raise InvalidConfig
            else:
                conf = ConfigurationFile('%s/config.conf' % self._datadir)
        else:
            raise DoesntUseConfig
        
        return conf
                
    def initialize(self, *args, **kwargs):
        """Initialize the plugin"""
        pass

    @classmethod
    def trigger(cls, *triggers):
        def call(func):
            func.triggers = triggers
            func.type = "trigger"
            func.hidden = False
            return func
        
        return call
    
    @classmethod
    def hiddenTrigger(cls, *triggers):
        def call(func):
            func.triggers = triggers
            func.type = "trigger"
            func.hidden = True
            return func
        
        return call

    @classmethod
    def event(cls, *triggers):
        def call(func):
            func.triggers = triggers
            func.type = "event"
            
            return func
        
        return call

    def _initTrigs(self):
        name = self.info["general"]["name"]
        members = getmembers(self)

        for funcdata in members:
            func = funcdata[1]
            
            if ismethod(func) and hasattr(func, "triggers"):
                if func.type == "event":
                    self.manager.registerEvent(name, func, *func.triggers)
                else:
                    self.manager.registerTrigger(name, func, *func.triggers)
    
    def blockEvent(self):
        self.manager._event_blocked = True

    def preReload(self, *args, **kwargs):
        pass

    def postReload(self, *args, **kwargs):
        pass

    def enabled(self, *args, **kwargs):
        pass
    
    def disabling(self, *args, **kwargs):
        pass
    
    def finalize(self, *args, **kwargs):
        pass
