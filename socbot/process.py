import os
import sys
import atexit

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    if sys.platform == "win32":
        # TODO: Implement stdio redirects
        return
    
    # Do first fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0)   # Exit first parent.
    except OSError, e: 
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)

    # Decouple from parent environment.
    os.chdir("/") 
    os.umask(0) 
    os.setsid() 

    # Do second fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0)   # Exit second parent.
    except OSError, e: 
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)

    # Now I am a daemon!
    
    si = open(stdin, 'r')
    so = open(stdout, 'a+')
    se = open(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def setupsingleinstance(pidfile):
    def taskexists(pid):
        if sys.platform == "win32":
            import ctypes
            import win32con
            
            h = ctypes.windll.kernel32.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
            
            if h:
                return True
            
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
            
    def alreadyRunning(pidfile):
        if os.path.isfile(pidfile) and os.access(pidfile, os.F_OK):
            with open(pidfile, "r") as f:
                pid = f.read()
                try:
                    pid = int(pid)
                except ValueError:
                    return False
                    
                if taskexists(pid):
                    return True
    
            os.unlink(pidfile)
            return False
        
    if not alreadyRunning(pidfile):
        pid = str(os.getpid())
        
        with open(pidfile, 'w') as f:
            f.write(pid)
        
        atexit.register(_finishsingleinstance, pidfile)
        return True
    else:
        return False
    
def _finishsingleinstance(pidfile):
    os.unlink(pidfile)
