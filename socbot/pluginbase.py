from inspect import getmembers, ismethod

class InsuffPerms(Exception):
    """The user does not have the required permissions."""

class BadParams(Exception):
    """The supplied parameters are not correct"""

class Base(object):
    def __init__(self, manager, info, users):
        self.users = users
        self.manager = manager
        self.info = info

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
