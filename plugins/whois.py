import pywhois

from socbot.pluginbase import Base, BadParams

class Plugin(Base): # Must subclass Base
    @Base.trigger("WHOIS")
    def on_whois(self, bot, user, details):
        """WHOIS <domain> - Get info about a domain"""
        parts = details["splitmsg"]
        command = details["trigger"]

        if not parts:
            raise BadParams

        name = parts.pop(0)
        dom = pywhois.whois(name)

        try:
            emails = ", ".join(set([x.strip() for x in dom.emails]))
            ns = ", ".join(set([x.strip() for x in dom.name_servers]))

            reply = "Registrar: {0}, domain(s): {1}, email(s): [ {2} ], nameserver(s): [ {3} ]. ".format(
                dom.registrar[0].strip(), dom.domain_name[0].strip(), emails, ns)
            reply += "More info available at http://who.is/whois/{0}/".format(name)

            return reply
        except IndexError:
            return "The data for this domain is invalid."
