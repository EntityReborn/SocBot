#!/usr/bin/env python
import sys, os
import logging

from twisted.internet import reactor
from twisted.application import internet

from socbot.config import ConfigurationFile

from socbot.core import BotFactory
from socbot.plugincore import PluginCore
from socbot.log import addLogger
from socbot import process

class main(object):
    def __init__(self, sstate):
        self.sstate = sstate

        self.sstate["exitcode"] = 0

        log.info("base directory is {0}".format(self.sstate["basedir"]))
        self.factories = {}

    def load(self):
        if not self.loadConfig(): return False
        
        self.loadPlugs()

        return True

    def loadConfig(self, filename="conf/socbot.conf", spec="conf/config.spec"):
        log.info("loading bot config from {0}".format(filename))

        self.config = ConfigurationFile(filename, configspec=spec, unrepr=True)
        
        errors = self.config.isValid()
        if errors:
            log.error("Error in config:")
            log.error('\n'.join(errors))
            
            return False
        
        self.sstate['config'] = self.config
        
        for d in self.config['directories'].values():
            if not os.path.exists(d):
                os.makedirs(d)

        return self.config

    def loadPlugs(self):
        log.info("starting pluginmanager and loading plugins")

        pm = PluginCore(self.sstate, self.config['directories']['plugins'])
        self.sstate["pluginmanager"] = pm
        
        pm.loadPlugins()
        pm.initPlugins()
        
        return pm

    def run(self):
        if "servers" in self.config:
            for name, config in self.config["servers"].iteritems():
                f = BotFactory(name, config, self.sstate, self)
                self.factories[name.lower()] = f
                
                botService = internet.TCPClient(config["host"], config["port"], f)
                log.info("Connecting to {0} ({1})".format(name, config["host"]))
                botService.startService()

                reactor.addSystemEventTrigger('before', 'shutdown',
                                              botService.stopService)

            reactor.addSystemEventTrigger('before', 'shutdown', self.shutdown)

            reactor.run()
            sys.exit(self.sstate['exitcode'])
        else:
            log.error("Nothing to connect to!\nCheck your socbot.conf file!")
            
    def connectionLost(self, lostconnection):
        for f in self.factories.values():
            if f.connection or not f.shuttingdown:
                return
            
        reactor.stop()

    def shutdown(self, msg="Shutdown requested."):
        for factory in self.factories.values(): # [bot, bot, bot, ...]
            try:
                factory.connection.quit(msg)
            except Exception:
                pass

if __name__ == "__main__":
    import argparse, signal
    
    lvl = logging.DEBUG # Should make this a variable.
    log = logging.getLogger("main")
    
    botlog = addLogger("socbot", lvl)
    pmlog = addLogger("pluginmanager", lvl)
    mlog = addLogger("main", lvl)

    parser = argparse.ArgumentParser(description='Run a socbot.')
    parser.add_argument('--daemon', action='store_true',
                        help='run the bot as a daemon (does nothing on Windows)')
    parser.add_argument('--conf',
                        help='specify the directory for configuration files')
    parser.add_argument('--multi', action='store_true',
                        help='run more than one instance')
    args = parser.parse_args()

    if args.daemon:
        process.daemonize()
        
    path = os.path.abspath(os.path.dirname(__file__))
    os.chdir(path)
    
    if not args.multi:
        alone = process.setupSingleInstance("conf/socbot.pid")

        if not alone:
            log.error("A SocBot is already running! Use --multi to run several instances.")
            sys.exit(-1)

    sstate = {
        "basedir":path
    }

    m = main(sstate)
    
    def handle_signal(signum, stackframe):
        m.shutdown()
        reactor.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    if m.load():
        m.run()
    else:
        log.error("error loading data, please check your configuration")
