import pywhois

from socbot.pluginbase import Base # Required

class Plugin(Base): # Must subclass Base
    def initialize(self, *args, **kwargs):
        # Call `on_source` when a user says "source" to me
        self.registerTrigger(self.on_whois, "WHOIS")

    def on_whois(self, bot, user, channel, message, inprivate):
        """WHOIS <domain> - Get info about a domain"""
        parts = message.split()
        command = parts.pop(0)

        if parts:
            name = parts.pop(0)
            dom = pywhois.whois(name)
            try:
                emails = ", ".join(set(dom.emails))

                reply = "Registrar: {0}, domain: {1}, emails: [ {2} ], nameservers: [ {3} ]. ".format(
                    dom.registrar[0], dom.domain_name[0], emails, ", ".join(dom.name_servers))
                reply += "More info available at http://who.is/whois/{0}/".format(name)

                return reply
            except IndexError:
                return "The data for this domain is invalid."
        else:
            return self.on_whois.__doc__
