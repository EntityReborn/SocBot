# -*- encoding: UTF-8 -*-
#
# Form based authentication for CherryPy. Requires the
# Session tool to be loaded.
#

import cherrypy, urllib
from authdb import UserDB, BadPass, NoSuchUser, UserAlreadyExists

SESSION_KEY = '_cp_username'

def checkCredentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    db = UserDB('conf/auth.db')
    
    try:
        u = db.loginPassword(username.lower(), password)
        
        return u
    except BadPass:
        return False
    except NoSuchUser:
        return False

def checkAuth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    conditions = cherrypy.request.config.get('auth.require', None)
    
    get_parmas = urllib.quote(cherrypy.request.request_line.split()[1])
    
    if conditions is not None:
        username = cherrypy.session.get(SESSION_KEY)
        
        if username:
            cherrypy.request.login = username
            
            for condition in conditions:
                # A condition is just a callable that returns true or false
                if not condition():
                    raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_parmas)
        else:
            raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_parmas)
    
cherrypy.tools.auth = cherrypy.Tool('before_handler', checkAuth)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
            
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
            
        f._cp_config['auth.require'].extend(conditions)
        
        return f
    return decorate

# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.

def isAdmin():
    return lambda: UserDB('conf/webauth.db').getUser(cherrypy.request.login.lower()).isAdmin()

# These might be handy

def anyOf(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if callable(c) and c():
                return True
            
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def allOf(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if callable(c) and not c():
                return False
            
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):
    def onLogin(self, username):
        """Called on successful login"""
        
    def onRegister(self, username):
        """Called on successful login"""
        self.onLogin(username)
    
    def onLogout(self, username):
        """Called on logout"""
    
    def getLoginForm(self, username, msg="Enter login information", from_page="/"):
        return """<html><body>
            <form method="post" action="/auth/login">
            <input type="hidden" name="from_page" value="%(from_page)s" />
            %(msg)s<br />
            Username: <input type="text" name="username" value="%(username)s" /><br />
            Password: <input type="password" name="password" /><br />
            <input type="submit" value="Log in" />
        </body></html>""" % locals()
        
    def getRegForm(self, msg="Enter registration information", from_page="/"):
        return """<html><body>
            <form method="post" action="/auth/register">
            <input type="hidden" name="from_page" value="%(from_page)s" />
            %(msg)s<br />
            Username: <input type="text" name="username" /><br />
            Password: <input type="password" name="password" /><br />
            <input type="submit" value="Register" />
        </body></html>""" % locals()
    
    @cherrypy.expose
    def register(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.getRegForm("Enter registration information", from_page=from_page)
        
        try:
            user = UserDB('conf/webauth.db').register(username, password)
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.onRegister(username)
            
            raise cherrypy.HTTPRedirect(from_page or "/")
        except UserAlreadyExists:
            return self.getRegForm("That username already exists", from_page)
        
    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.getLoginForm("", from_page=from_page)
        
        success = checkCredentials(username, password)
        
        if not success:
            return self.getLoginForm(username, "Incorrect username or password", from_page)
        else:
            cherrypy.session.regenerate()
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.onLogin(username)
            
            raise cherrypy.HTTPRedirect(from_page or "/")
    
    @cherrypy.expose
    def logout(self, from_page="/"):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        
        if username:
            cherrypy.lib.sessions.expire()
            cherrypy.request.login = None
            self.onLogout(username)
            
        raise cherrypy.HTTPRedirect(from_page or "/")