from socbot.pluginbase import Base, InsuffPerms, BadParams
from socbot.pluginmanager import NoSuchPlugin, PluginAlreadyEnabled, PluginAlreadyDisabled

class Plugin(Base):
    @Base.trigger("RELOAD")
    def on_reload(self, bot, user, details):
        """RELOAD [name] - Reload plugins. If name is not specified, all plugins are reloaded"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not user.hasPerm("plugins.reload"):
            raise InsuffPerms, "plugins.reload"

        if not parts:
            self.manager.reloadPlugins()
        elif len(parts) == 1:
            plugname = parts.pop(0)

            try:
                self.manager.reloadPlugin(plugname)
            except NoSuchPlugin:
                return "No such plugin: {0}".format(plugname)
        else:
            raise BadParams

        return True

    @Base.trigger("ENABLE", "DISABLE")
    def on_enabledisable(self, bot, user, details):
        """{DISABLE, ENABLE} <pluginname> - Enable or disable a plugin by name. The plugin is completely unloaded when disabled."""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not user.hasPerm('plugins.'+command):
            raise InsuffPerms, "plugins."+command

        if not parts:
            raise BadParams

        plugname = parts.pop(0).lower()

        if command == "enable":
            try:
                self.manager.enablePlug(plugname)
            except NoSuchPlugin:
                return "No such plugin, '{0}'.".format(plugname)
            except PluginAlreadyEnabled:
                return "'{0}' already enabled.".format(plugname)
        elif command == "disable":
            try:
                self.manager.disablePlug(plugname)
            except NoSuchPlugin:
                return "No such plugin, '{0}'.".format(plugname)
            except PluginAlreadyDisabled:
                return "'{0}' already disabled.".format(plugname)

        return True
