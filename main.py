#!/usr/bin/env python
import sys, os
from collections import defaultdict
import logging

from twisted.internet import reactor
from twisted.application import internet

from socbot.config import ConfigObj

from socbot.core import BotFactory
from socbot.pluginmanager import PluginManager
from socbot.tools import validateConfig
from socbot.log import addLogger
from socbot import process

class main(object):
    def __init__(self, curdir, sstate=None):
        self.sstate = sstate

        if sstate == None:
            self.sstate = {}

        self.sstate["exitcode"] = 0
        self.sstate["bots"] = defaultdict(list)

        if not os.path.isdir(curdir):
            curdir = os.path.dirname(curdir)

        self.sstate["basedir"] = os.path.abspath(curdir)
        self.sstate["confs"] = self.sstate["basedir"] + "/conf/"

        log.info("base directory is {0}".format(self.sstate["basedir"]))

    def load(self):
        if not self.loadConfig(): return False
        if not self.loadUsers(): return False
        self.loadPlugs()

        return True

    def loadConfig(self):
        log.info("loading bot config from {0}".format(
            self.sstate["confs"]+"socbot.conf"))

        self.config = ConfigObj(self.sstate["confs"]+"socbot.conf",
            configspec=self.sstate["confs"]+"config.spec",
            unrepr=True)

        invalid = validateConfig(self.config)
        if invalid:
            log.error('\n'.join(invalid))
            return False

        self.sstate["baseconfig"] = self.config

        return True

    def loadUsers(self):
        log.info("loading user config from {0}".format(
            self.sstate["confs"]+"users.conf"))

        users = ConfigObj(self.sstate["confs"]+"users.conf",
            configspec=self.sstate["confs"]+"users.spec",
            unrepr=True)

        invalid = validateConfig(users)
        if invalid:
            log.error('\n'.join(invalid))
            return False

        self.sstate["users"] = users

        return True

    def loadPlugs(self):
        log.info("starting pluginmanager and loading plugins")

        pm = PluginManager(self.sstate)
        self.sstate["pluginmanager"] = pm
        pm.loadPlugins()
        pm.initPlugins()

    def run(self):
        if "servers" in self.config:
            for name, config in self.config["servers"].iteritems():
                f = BotFactory(name, config, self.sstate, self)

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

    def shutdown(self, msg="Shutdown requested."):
        for bots in self.sstate["bots"].values(): # [bot, bot, bot, ...]
            for inst in bots:
                inst.quit(msg)

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

    dir = os.path.abspath(os.path.dirname(__file__))
    
    if not args.multi:
        alone = process.setupsingleinstance(dir+"/conf/socbot.pid")

        if not alone:
            log.error("A SocBot is already running! Use --multi to run several instances.")
            sys.exit(-1)

    sstate = {}

    def handle_signal(signum, stackframe):
        if signum == signal.SIGINT:
            for name, bots in sstate["bots"].iteritems():
                for bot in bots:
                    bot.quit("CTRL-C")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    m = main(dir, sstate)

    if m.load():
        m.run()
    else:
        log.error("error loading data, please check your configuration")
