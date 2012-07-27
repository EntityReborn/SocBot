from socbot.config import ConfigObj
from socbot.tools import validateConfig
from socbot.userdb import UserDB

if __name__ == "__main__":

    users = ConfigObj('conf/users.conf', configspec='conf/users.spec', unrepr=True)
    
    invalid = validateConfig(users)
    
    if invalid:
        log.error('\n'.join(invalid))
        exit(1)
    
    db = UserDB('conf/users.db')
    
    for nick, config in users['users'].iteritems():
        print "Found user %s" % nick
        user = db.getUser(nick)
        
        try:
            user.register(nick, config['passhash'], config['email'])
            print "Registered to DB."
        except Exception:
            print "User was already registered!"
        
        reg = user.getRegistration(nick)
        
        for perm in config['permissions']:
            reg.addPerm(perm)
            print "Added %s perm." % perm
            
        for mask in config['hostmasks']:
            reg.addHostmask(mask)
            print "Added %s hostmask." % mask
            
        print "-----"
            
    db.saveSession()
            
    print "New db saved as conf/users.db."