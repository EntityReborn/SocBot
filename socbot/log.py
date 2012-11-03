import logging

loggers = {}

hdlr = logging.StreamHandler()
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
hdlr.setFormatter(formatter)

def addLogger(name, level):
    name = name.lower()
    
    log = logging.getLogger(name)
    log.addHandler(hdlr)
    log.setLevel(level)
    loggers[name] = log
    
    return log

def getLogger(name):
    name = name.lower()
    return loggers[name]

def getLoggers():
    return loggers