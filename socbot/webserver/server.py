import cherrypy, os, glob, sys
from socbot.userdb import UserDB

sys.path.append('plugins')
from factoidbase import FactoidManager

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('socbot/webserver/templates'))

from socbot.webserver.auth import AuthController, require

class Users:
    _cp_config = {
        'tools.sessions.on': True,
        'tools.auth.on': True
    }
    
    @cherrypy.expose
    @require()
    def index(self):
        files = glob.glob(os.path.join('conf', "*-users.db"))
        userdbs = []
        
        for f in files:
            userdbs.append([f, UserDB(f)])
    
        tmpl = env.get_template('users.html')
        
        return tmpl.render(dbs=userdbs)
    
class Root:
    _cp_config = {
        'tools.sessions.on': True,
        'tools.auth.on': True
    }
    
    auth = AuthController()
    
    users = Users()
        
    @cherrypy.expose
    def facts(self):
        files = glob.glob(os.path.join('conf', "*-factoids.db"))
        factdbs = []
        
        for f in files:
            factdbs.append([f, FactoidManager(f)])
            
        tmpl = env.get_template('factoids.html')
        
        return tmpl.render(dbs=factdbs)
        
    @cherrypy.expose
    def index(self):
        tmpl = env.get_template('index.html')
        
        return tmpl.render()

def run():
    cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.quickstart(Root())