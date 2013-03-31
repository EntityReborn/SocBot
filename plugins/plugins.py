from socbot.pluginbase import Base, BadParams
from socbot.plugincore import NoSuchPlugin, PluginNotLoaded, PluginAlreadyLoaded

class Plugin(Base):
    @Base.trigger("LIST")
    def on_list(self, bot, user, details):
        plugs = bot.plugins
        names = []
        for plug in plugs.plugintrackers.values():
            names.append(plug.getName())
            
        return "Loaded plugins: %s." % ", ".join(names)
    
    @Base.trigger("RELOAD")
    def on_reload(self, bot, user, details):
        """RELOAD [name] - Reload plugins. If name is not specified, all plugins are reloaded"""
        parts = details["splitmsg"]
        command = details["trigger"]

        user.assertPerm("plugins.reload")

        if not parts:
            self.manager.core.reloadPlugins()
        elif len(parts) == 1:
            plugname = parts.pop(0)

            try:
                self.manager.core.reloadPlugin(plugname)
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

        user.assertPerm('plugins.'+command)

        if not parts:
            raise BadParams

        plugname = parts.pop(0).lower()

        if command == "enable":
            try:
                self.manager.core.enablePlug(plugname)
            except NoSuchPlugin:
                return "No such plugin, '{0}'.".format(plugname)
            except PluginAlreadyLoaded:
                return "'{0}' already enabled.".format(plugname)
        elif command == "disable":
            try:
                self.manager.core.disablePlug(plugname)
            except NoSuchPlugin:
                return "No such plugin, '{0}'.".format(plugname)
            except PluginNotLoaded:
                return "'{0}' already disabled.".format(plugname)

        return True
