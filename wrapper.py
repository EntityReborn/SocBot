#!/usr/bin/env python
import subprocess, os, sys
import signal

if __name__ == "__main__":
    code = 3
    inst = None
    
    def handler(signum, stackframe):
        inst.terminate()
        
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    
    while code == 3:
        print "Starting new bot process..."
        
        if os.name == "nt":
            inst = subprocess.Popen(['python', 'main.py'] + sys.argv[1:])
        else:
            inst = subprocess.Popen(['./main.py',] + sys.argv[1:])
            
        inst.wait()
        code = inst.returncode