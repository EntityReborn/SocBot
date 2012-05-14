from socbot.userdb import UserDB, NoSuchUser

def getInput(prefix):
    retn = ""
    
    while not retn:
        retn = raw_input(prefix+": ")
        
    return retn

def getBool(prefix):
    retn = ""
    
    while not retn.lower() in ["y","n"]:
        retn = getInput(prefix+ " [y/n]")
        
    if retn == "y":
        return True
    
    return False

network = getInput("User's network")
username = getInput("User's login name").lower()

db = UserDB('conf/%s-users.db' % network.lower())

try:
    user = db.getRegistration(username)
except NoSuchUser:
    user = None
    
if user:
    print "This user already exists. Continuing with existing user."
else:
    # Get password
    while True:
        password = getInput("User's password")
        passconf = getInput("User's password (confirm)")
        
        if password == passconf:
            break
    
        print "Unmatched passwords, try again."
    
    # Get email
    email = getInput("User's email")

    # Create user
    user = db.getUser(username)
    user = user.register(username, password, email)

# Check if should get * perm
superuser = getBool("Make user a superuser")

if superuser:
    if not user.hasPerm("*"):
        user.addPerm("*")
        db.saveSession()
        
print "Done."

