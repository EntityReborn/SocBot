from socbot.pluginbase import Base

class Plugin(Base):
    @Base.trigger("RESPONDSTATIC")
    def on_respondstatic(self, bot, user, details):
        return "Pong!!!"
    
    @Base.trigger("RESPONDINPUT")
    def on_respondinput(self, bot, user, details):
        return details
    
    @Base.trigger("RESPONDDIRECT")
    def on_responddirect(self, bot, user, details):
        bot.msg("user", "direct msg")
        
    @Base.trigger("TRIGDISABLE")
    def on_trigdisable(self, bot, user, details):
        if details == "disable":
            self.manager.removeTrigger(self.on_trigdisable, "TRIGDISABLE")
            return True
            
        return False
    
    @Base.event("EVENTDISABLE")
    def on_eventdisable(self, bot, user, details):
        if details == "disable":
            self.manager.removeEvent(self.on_eventdisable, "EVENTDISABLE")
        
    