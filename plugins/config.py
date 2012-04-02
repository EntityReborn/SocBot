from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.config import PathDoesntExist

class Plugin(Base):
    @Base.trigger("CONFIG")
    def on_config(self, bot, user, details):
        """CONFIG PLUGIN|BASE|RELOAD <...>"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not self.userHasPerm(user, command):
            raise InsuffPerms, "config."+command

        if not parts:
            raise BadParams

        type = parts.pop(0).upper()

        if type == "PLUGIN":
            return self.on_plugconf(bot, user, details)
        if type == "RELOAD":
            bot.factory.sstate["baseconfig"].reload()
            return True
        elif type == "BASE":
            return self.on_baseconf(bot, user, details)
        else:
            raise BadParams

    def on_plugconf(self, bot, user, details):
        parts = details["splitmsg"]
        plugname = parts.pop(0).upper()

        if not plugname in self.manager.moduleinfo:
            return "Unknown plugin, '{0}'".format(plugname)

        plug = self.manager.moduleinfo[plugname.upper()]

    def on_baseconf(self, bot, user, details):
        """CONFIG BASE <some.path> [SET <data>] - Reply with base config data, or set data if SET is used."""
        # CONFIG BASE general.commandchars set ^
        parts = details["splitmsg"]
        
        if not parts:
            return self.on_baseconf.__doc__
        
        path = parts[0].lower()

        section = bot.factory.sstate["baseconfig"]

        try:
            config = section.getByPath(path.split("."))
        except PathDoesntExist:
            return "{0} does not exist in config.".format(path)

        if len(parts) >= 2:
            command = parts.pop(0).upper()

            if command == "SET":
                data = " ".join(parts)
                section.setByPath(path.split("."), data)

                return self._respond(path, section)
            else:
                raise BadParams

        elif len(parts) == 1:
            return self._respond(path, section)
        
        else:
            raise BadParams

    def _respond(self, path, section):
        config = section.getByPath(path.split("."))

        if isinstance(config, (list, tuple)):
            line = ", ".join(config)
        if isinstance(config, dict):
            line = ", ".join([
                "%s: %s" % (key,value if not isinstance(value, (list, dict, tuple)) else "(...)") 
                for key, value in config.iteritems()
            ])
        else:
            line = config

        return "'{0}': {1}".format(path, line)
