from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.config import PathDoesntExist

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.registerTrigger(self.on_config, "CONFIG")

    def on_config(self, bot, user, details):
        """CONFIG PLUGIN|BASE <...>"""
        parts = details["splitmsg"]
        command = parts.pop(0).lower()

        if not self.userHasPerm(user, command):
            raise InsuffPerms, "config."+command

        if not parts:
            raise BadParams

        type = parts.pop(0).upper()

        if type == "PLUGIN":
            return self.on_plugconf(bot, user, details)
        elif type == "BASE":
            return self.on_baseconf(bot, user, details)

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
        path = parts.pop(0).lower()

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

        if isinstance(config, (dict, tuple)):
            line = ", ".join(config.keys())
        else:
            line = ", ".join(config)

        return "'{0}': {1}".format(path, line)
