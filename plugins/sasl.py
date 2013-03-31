from socbot.pluginbase import Base
import base64

class Plugin(Base):
    @Base.event("IRC_CONNECTED")
    def on_connect(self, bot, command, prefix, params):
        conf = self.getConfig()
        nick = conf['general']['saslnick']
        passwd = conf['general']['saslpass']
        
        if nick and passwd:
            bot.sendLine("CAP LS")
    
    @Base.event("CAP")
    def on_cap(self, bot, command, prefix, params):
        if not len(params) > 2:
            return
        
        if params[1] == "ACK" and "sasl" in params[2]:
            bot.sendLine("AUTHENTICATE PLAIN")
        elif params[1] == "LS":
            if "sasl" in params[2]:
                bot.sendLine("CAP REQ :sasl")
            else:
                bot.sendLine("CAP END")
        elif params[1] == "NAK":
            bot.sendLine("CAP END")
            
    @Base.event("AUTHENTICATE")
    def on_auth(self, bot, command, prefix, params):
        conf = self.getConfig()
        nick = conf['general']['saslnick']
        passwd = conf['general']['saslpass']
        
        tosend = "%s\0%s\0%s" % (nick, nick, passwd)
        
        if params and params[0] == "+":
            bot.sendLine("AUTHENTICATE %s" % 
                 base64.b64encode(tosend))
            
    @Base.event("903")
    def on_903(self, bot, command, prefix, params):
        bot.sendLine("CAP END")