from configobj import ConfigObj, Section

class PathDoesntExist(Exception): pass

def root(self):
    if self.parent == self:
        return self

    return self.parent.root()

def getByPath(self, path):
    config = self

    if not path:
        return config

    for p in path:
        if not p:
            return config

        try:
            config = config[p]
        except KeyError:
            raise PathDoesntExist, path

    return config

def setByPath(self, path, value, autocreate=False):
    config = self

    for p in path[:-1]:
        try:
            config = config[p]

            if not isinstance(config, dict):
                raise ValueError, "Bad path: "+path

        except KeyError:
            if not autocreate:
                raise PathDoesntExist, path
            else:
                config[p] = {}
                config = config[p]

    config[path[-1:][0]] = value

Section.root = root
Section.getByPath = getByPath
Section.setByPath = setByPath

if __name__ == "__main__":
    b = ConfigObj()
    b["a"] = {
        "b": {
            "c": "bik"
        }
    }

    assert b.getByPath(["a", "b", "c"]) == "bik", b.getByPath(["a", "b", "c"])
    b.setByPath(["a", "l"], "bok", True)
    assert b.getByPath(["a", "l"]) == "bok", b.getByPath(["a", "l"])
    b.setByPath(["a", "b", "c"], "bok")
    assert b.getByPath(["a", "b", "c"]) == "bok", b.getByPath(["a", "b", "c"])
    print b.getByPath(["a", "b"]).root()
