#!/usr/bin/env python3
"""
Emergency cleanup script to find and terminate BrainDrive processes
"""
import psutil
import sys
import time

def find_braindrive_processes():
    """Find all processes that might be related to BrainDrive"""
    braindrive_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
        try:
            # Check if process is related to BrainDrive
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            cwd = proc.info['cwd'] or ''
            
            # Look for BrainDrive-related patterns
            if any(pattern in cmdline.lower() for pattern in [
                'braindrive', 'uvicorn', 'vite', 'npm run dev'
            ]) or 'braindrive' in cwd.lower():
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
    print("🔍 Searching for BrainDrive processes...")
    processes = find_braindrive_processes()
    
    if not processes:
        print("✅ No BrainDrive processes found")
        return
    
    print(f"🎯 Found {len(processes)} BrainDrive-related processes:")
    for proc in processes:
        print(f"  PID {proc['pid']}: {proc['name']} - {proc['cmdline'][:100]}...")
    
    print("\n🛑 Terminating processes...")
    for proc in processes:
        print(f"Terminating PID {proc['pid']} ({proc['name']})")
        kill_process_tree(proc['pid'])
    
    print("\n⏳ Waiting for cleanup...")
    time.sleep(2)
    
    # Check if any are still running
    remaining = find_braindrive_processes()
    if remaining:
        print(f"⚠️  {len(remaining)} processes still running:")
        for proc in remaining:
            print(f"  PID {proc['pid']}: {proc['name']}")
    else:
        print("✅ All BrainDrive processes terminated successfully")

if __name__ == "__main__":
    main()