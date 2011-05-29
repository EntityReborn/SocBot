from socbot.pluginbase import Base # Required

class Plugin(Base): # Must subclass Base
    @Base.trigger("SOURCE")
    def on_source(self, bot, user, details):
        """SOURCE - say the bot's source URL"""
        return bot.sourceURL
