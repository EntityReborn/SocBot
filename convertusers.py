from socbot.config import ConfigObj
from socbot.userdb import UserDB

users = ConfigObj('conf/users.conf')
db = UserDB('conf/users.db')

for nick, config in users['users'].iteritems():
    user = db.getUser(nick)
    try:
        user.register(nick, config['passhash'], config['email'])
    except Exception:
        pass
    
    reg = user.getRegistration(nick)
    
    for perm in config['permissions']:
        reg.addPerm(perm)
        
    for mask in config['hostmasks']:
        reg.addHostmask(mask)
        
db.saveSession()
        
print "New db saved as conf/users.db."