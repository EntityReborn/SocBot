from socbot.pluginbase import Base
from socbot.pluginmanager import NoSuchPlugin, PluginAlreadyEnabled, PluginAlreadyDisabled

class Plugin(Base):
    def initialize(self, *args, **kwargs):
        self.registerTrigger(self.on_reload, "RELOAD")
        self.registerTrigger(self.on_enabledisable, "DISABLE", "ENABLE")

    def on_reload(self, bot, user, channel, message, inprivate):
        """RELOAD [<pluginname>] - Reload plugins"""

        parts = message.split()
        command = parts.pop(0).lower()

        if not self.userHasPerm(user, command):
            return "You have insufficient privileges."

        if not parts:
            self.manager.reloadPlugins()
        elif len(parts) == 1:
            plugname = parts.pop(0)

            try:
                self.manager.reloadPlugin(plugname)
            except NoSuchPlugin:
                return "No such plugin: {0}".format(plugname)
        else:
            return self.on_reload.__doc__

        return "Done."

    def on_enabledisable(self, bot, user, channel, message, inprivate):
        """{DIS,EN}ABLE <pluginname> - Enable or disable a plugin by name. The plugin is completely unloaded when disabled."""
        parts = message.lower().split()
        command = parts.pop(0)

        if not self.userHasPerm(user, command):
            return "You have insufficient privileges."

        if len(parts):
            plugname = parts.pop(0)

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
                except PluginAlreadyEnabled:
                    return "'{0}' already disabled.".format(plugname)

            return "Done."
        else:
            return self.on_enabledisable.__doc__
