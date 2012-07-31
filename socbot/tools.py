from configobj import flatten_errors
from validate import Validator

import re, string

class CaselessDict:
    def __init__(self, inDict=None, lowerfunc=None):
        self.dict = {}

        if inDict:
            for key in inDict:
                k = self._lower(key)
                self.dict[k] = (key, inDict[key])

        self.keyList = self.dict.keys()
        self.lowerfunc = lowerfunc

    def _lower(self, key):
        if self.lowerfunc:
            return self.lowerfunc(key)

        if hasattr(key, "lower") and callable(key.lower):
            return key.lower()

        return key

    def __iter__(self):
        self.iterPosition = 0
        return self

    def next(self):
        if self.iterPosition >= len(self.keyList):
            raise StopIteration
        x = self.dict[self.keyList[self.iterPosition]][0]
        self.iterPosition += 1
        return x

    def __getitem__(self, key):
        k = self._lower(key)
        return self.dict[k][1]

    def __delitem__(self, key):
        k = self._lower(key)
        del self.dict[k]

    def __setitem__(self, key, value):
        k = self._lower(key)
        self.dict[k] = (key, value)
        self.keyList = self.dict.keys()

    def has_key(self, key):
        k = self._lower(key)
        return k in self.keyList

    def __len__(self):
        return len(self.dict)

    def keys(self):
        return [v[0] for v in self.dict.values()]

    def values(self):
        return [v[1] for v in self.dict.values()]

    def items(self):
        return self.dict.values()

    def __contains__(self, item):
        return self.dict.has_key(self._lower(item))

    def __repr__(self):
        items = ", ".join([("%r: %r" % (k,v)) for k,v in self.items()])
        return "{%s}" % items

    def __str__(self):
        return repr(self)

_rfc1459trans = string.maketrans(string.ascii_uppercase + r'\[]~',
                                 string.ascii_lowercase + r'|{}^')

def toLower(s, casemapping=None):
    """s => s
    Returns the string s lowered according to IRC case rules."""
    if casemapping is None or casemapping == 'rfc1459':
        return s.translate(_rfc1459trans)
    elif casemapping == 'ascii': # freenode
        return s.lower()
    else:
        raise ValueError, 'Invalid casemapping: %r' % casemapping

def isHostMask(line):
    if "!" in line:
        nick, rest = line.split("!")
        if "@" in rest:
            user, host = rest.split("@")
            if user and host:
                return True

    return False

_nickchars = r'[]\`_^{|}'
nickRe = re.compile(r'^[A-Za-z{0}][-0-9A-Za-z{0}]*$'.format(re.escape(_nickchars)))

def isNick(s, strictRfc=True, nicklen=None):
    if strictRfc:
        ret = bool(nickRe.match(s))
        if ret and nicklen is not None:
            ret = len(s) <= nicklen
        return ret
    else:
        return not isChannel(s) and \
               not isHostMask(s) and \
               not ' ' in s and not '!' in s

def isChannel(s, chantypes='#&+!', channellen=50):
    return s and \
           ',' not in s and \
           '\x07' not in s and \
           s[0] in chantypes and \
           len(s) <= channellen and \
           len(s.split(None, 1)) == 1

def isSameNick(nick1, nick2):
    nick1 = nick1.lower()
    nick2 = nick2.lower()
    return nick1 == nick2

def validateConfig(config):
    validator = Validator()
    results = config.validate(validator, preserve_errors=True)
    errors = list()

    if results != True:
        for (section_list, key, exc) in flatten_errors(config, results):
            if key is not None:
                errors.append('\t"%s" in "%s" failed validation. (%s)' % (key, ', '.join(section_list), exc))
            else:
                errors.append('\tThe following sections were missing:%s ' % ', '.join(section_list))

    return errors