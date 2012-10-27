# Introduction #

SocPuppet is a general purpose IRC bot, written in Python,
with a very plugin-based approach to functionality. Originally
designed to be for the ##socialites community of [Freenode][fnirc].

# Dependancies #

* Core
    * [Python 2.6-2.7][python]
    * [Twisted 11+][twist] - Internet engine behind the bot (will need python-dev if installing from setuptools)
    * [Zope.Interface][zope] - Required for Twisted.
    * [ConfigObj][confobj] (and it's validate.py as well) - Provide an easy API for configs.
    * [PyWin32][pywin] - If running on windows.
    * [Argparse][pyargparse] - Helpful for parsing commandline stuff.
    * [SQLAlchemy][sqla] - Database management.
    
* Website (Optional)
    * [CherryPy][cherry] - Website functionality.

* Plugins
    * [BeautifulSoup4][bs4] - HTML parsing lib

# Credits #

* #python on [Freenode][fnirc] - constant help
* #botters on [Freenode][fnirc] - support
* #twisted on [Freenode][fnirc] - general help
* ##socialites on [Freenode][fnirc] - witty idiosyncrasies

# Licence #

Released under the MIT license.
See LICENSE or [this page][license].

[python]: http://www.python.org "Python"
[twist]: http://www.twistedmatrix.com "Twisted Internet Library for Python"
[zope]: www.zope.org/Products/ZopeInterface "Zope.Interface"
[confobj]: www.voidspace.org.uk/python/configobj.html "ConfigObj"
[license]: http://www.opensource.org/licenses/mit-license.php "MIT License"
[fnirc]: irc://irc.freenode.net "FreeNode.net IRC community"
[pywin]: http://sourceforge.net/projects/pywin32 "PyWin32"
[pyargparse]: http://pypi.python.org/pypi/argparse "ArgParse on pypi"
[bs4]: http://www.crummy.com/software/BeautifulSoup/ "BeautifulSoup 4"
[sqla]: http://sqlalchemy.org "SQLAlchemy"
[cherry]: http://cherrypy.org "CherryPy"
