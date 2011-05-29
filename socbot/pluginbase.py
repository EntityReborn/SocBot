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

    def registerTrigger(self, func, *trigs):
        """Register a trigger-word based event"""
        self.manager.registerTrigger(self.info["info"]["general"]["name"], func, *trigs)

    def registerEvent(self, func, *events):
        """Register an IRC-based event"""
        self.manager.registerEvent(self.info["info"]["general"]["name"], func, *events)

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
