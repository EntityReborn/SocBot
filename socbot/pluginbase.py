from inspect import getmembers, ismethod

class InsuffPerms(Exception):
    """The user does not have the required permissions."""

class BadParams(Exception):
    """The supplied parameters are not correct"""

class Base(object):
    def __init__(self, manager, info):
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
        name = self.info["info"]["general"]["name"]
        members = getmembers(self)

        for funcdata in members:
            func = funcdata[1]
            if ismethod(func) and hasattr(func, "triggers"):
                if func.type == "event":
                    self.manager.registerEvent(name, func, *func.triggers)
                else:
                    self.manager.registerTrigger(name, func, *func.triggers)

    def beforeReload(self, *args, **kwargs):
        pass

    def afterReload(self, *args, **kwargs):
        pass

    def disabling(self, *args, **kwargs):
        pass

    def enabled(self, *args, **kwargs):
        pass

    def finalize(self, *args, **kwargs):
        pass

    def userHasPerm(self, user, permpath):
        path = permpath.lower().split(".")

        if not user.loggedIn():
            return False

        userperms = user.userinfo[1]["permissions"]

        if "*" in userperms:
            return True

        if permpath in self.info["general"]["autoallowperms"]:
            return True

        curpath = self.info["general"]["name"]

        for perm in path:
            if "{0}.*".format(curpath) in userperms:
                return True
            if "{0}.{1}".format(curpath, perm) in userperms:
                return True

            curpath = "{0}.{1}".format(curpath, perm)

        return False
