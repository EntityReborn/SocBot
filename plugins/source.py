from socbot.pluginbase import Base # Required

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        # Call `on_source` when a user says "source" to me
        self.registerTrigger(self.on_source, "SOURCE")

    def on_source(self, bot, user, details):
        """SOURCE - say the bot's source URL"""
        return bot.sourceURL
