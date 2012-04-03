#!/usr/bin/env python
import subprocess, os, sys
import signal

if __name__ == "__main__":
    code = 3
    inst = None
    
    def handler():
        inst.terminate()
        
    signal.signal(signal.SIGTERM, handler)
    
    while code == 3:
        if os.name == "nt":
            inst = subprocess.Popen(['python', 'main.py'] + sys.argv[1:])
        else:
            inst = subprocess.Popen(['./main.py',] + sys.argv[1:])
            
        inst.wait()
        code = inst.returncode