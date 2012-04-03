import subprocess

if __name__ == "__main__":
    code = 3
    
    while code == 3:
        p = subprocess.Popen('python main.py')
        p.wait()
        code = p.returncode