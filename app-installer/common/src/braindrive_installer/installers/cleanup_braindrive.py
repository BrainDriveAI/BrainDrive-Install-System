#!/usr/bin/env python3
"""
Targeted cleanup script to find and terminate actual BrainDrive backend/frontend processes
"""
import psutil
import sys
import time
import socket

def check_port_in_use(port):
    """Check if a port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def find_actual_braindrive_processes():
    """Find actual BrainDrive backend/frontend processes"""
    braindrive_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            cwd = proc.info['cwd'] or ''
            
            # Look for specific BrainDrive patterns (not just any process in BrainDrive directory)
            is_braindrive = False
            
            # Backend patterns
            if any(pattern in cmdline for pattern in [
                'uvicorn main:app',
                'python main.py',
                'fastapi',
                '--port 8005'
            ]):
                is_braindrive = True
                
            # Frontend patterns  
            elif any(pattern in cmdline for pattern in [
                'npm run dev',
                'vite',
                '--port 5173',
                'node_modules/.bin/vite'
            ]) and 'braindrive' in cwd.lower():
                is_braindrive = True
                
            # Python processes in BrainDrive directory
            elif proc.info['name'] == 'python.exe' and 'braindrive' in cwd.lower() and 'backend' in cwd.lower():
                is_braindrive = True
                
            # Node processes in BrainDrive directory
            elif proc.info['name'] == 'node.exe' and 'braindrive' in cwd.lower() and 'frontend' in cwd.lower():
                is_braindrive = True
            
            if is_braindrive:
                braindrive_processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmdline': cmdline,
                    'cwd': cwd
                })
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    return braindrive_processes

def kill_process_tree(pid):
    """Kill a process and all its children"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                print(f"  Killing child process {child.pid} ({child.name()})")
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Kill parent
        try:
            print(f"  Killing parent process {parent.pid} ({parent.name()})")
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Wait for termination
        gone, alive = psutil.wait_procs(children + [parent], timeout=5)
        
        # Force kill if still alive
        for proc in alive:
            try:
                print(f"  Force killing stubborn process {proc.pid}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    except psutil.NoSuchProcess:
        print(f"  Process {pid} already gone")

def main():
    print("🔍 Searching for actual BrainDrive backend/frontend processes...")
    
    # Check ports first
    backend_port_active = check_port_in_use(8005)
    frontend_port_active = check_port_in_use(5173)
    
    print(f"Backend port 8005: {'🔴 IN USE' if backend_port_active else '🟢 FREE'}")
    print(f"Frontend port 5173: {'🔴 IN USE' if frontend_port_active else '🟢 FREE'}")
    
    processes = find_actual_braindrive_processes()
    
    if not processes:
        if backend_port_active or frontend_port_active:
            print("⚠️  Ports are in use but no BrainDrive processes found!")
            print("This might indicate hidden or system processes using these ports.")
        else:
            print("✅ No BrainDrive processes found and ports are free")
        return
    
    print(f"\n🎯 Found {len(processes)} actual BrainDrive processes:")
    for proc in processes:
        print(f"  PID {proc['pid']}: {proc['name']}")
        print(f"    CMD: {proc['cmdline'][:80]}...")
        print(f"    CWD: {proc['cwd']}")
    
    print("\n🛑 Terminating BrainDrive processes...")
    for proc in processes:
        print(f"Terminating PID {proc['pid']} ({proc['name']})")
        kill_process_tree(proc['pid'])
    
    print("\n⏳ Waiting for cleanup...")
    time.sleep(3)
    
    # Check ports again
    backend_port_active = check_port_in_use(8005)
    frontend_port_active = check_port_in_use(5173)
    
    print(f"Backend port 8005: {'🔴 STILL IN USE' if backend_port_active else '🟢 NOW FREE'}")
    print(f"Frontend port 5173: {'🔴 STILL IN USE' if frontend_port_active else '🟢 NOW FREE'}")
    
    # Check if any are still running
    remaining = find_actual_braindrive_processes()
    if remaining:
        print(f"⚠️  {len(remaining)} processes still running:")
        for proc in remaining:
            print(f"  PID {proc['pid']}: {proc['name']}")
    else:
        print("✅ All BrainDrive processes terminated successfully")
        
    if not backend_port_active and not frontend_port_active:
        print("🎉 Directory should now be deletable!")

if __name__ == "__main__":
    main()