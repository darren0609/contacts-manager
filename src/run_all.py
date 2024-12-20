import subprocess
import sys
from pathlib import Path
import threading
import time
import socket
import psutil

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_process_on_port(port):
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['pid']} using port {port}")
                    proc.kill()
                    time.sleep(1)  # Wait for process to die
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def stream_output(process, prefix):
    """Stream output from a process with a prefix"""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(f"{prefix} | {line.strip()}")
    
    while True:
        line = process.stderr.readline()
        if not line:
            break
        print(f"{prefix} ERROR | {line.strip()}", file=sys.stderr)

def run_all():
    # Check if port is in use
    if is_port_in_use(8000):
        print("Port 8000 is in use. Attempting to kill existing process...")
        if not kill_process_on_port(8000):
            print("Could not free port 8000. Please check what's using it.")
            sys.exit(1)
    
    # Clean up any existing status files
    for file in ["web_app_ready.txt", "duplicate_cache_status.json"]:
        try:
            Path(file).unlink()
        except FileNotFoundError:
            pass
    
    print("Starting web server...")
    web_process = subprocess.Popen(
        [sys.executable, "src/web/run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Wait a moment for web server to start
    time.sleep(2)
    
    if web_process.poll() is not None:
        print("Web server failed to start!")
        return
    
    print("Starting duplicate worker...")
    worker_process = subprocess.Popen(
        [sys.executable, "src/workers/duplicate_worker.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Create threads to stream output
    web_thread = threading.Thread(
        target=stream_output, 
        args=(web_process, "WEB"),
        daemon=True
    )
    worker_thread = threading.Thread(
        target=stream_output, 
        args=(worker_process, "WORKER"),
        daemon=True
    )
    
    # Start output threads
    web_thread.start()
    worker_thread.start()
    
    try:
        while True:
            # Check if either process has terminated
            web_status = web_process.poll()
            worker_status = worker_process.poll()
            
            if web_status is not None:
                print(f"Web process terminated with status {web_status}")
                break
            if worker_status is not None:
                print(f"Worker process terminated with status {worker_status}")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        print("Terminating processes...")
        
        if web_process.poll() is None:
            web_process.terminate()
        if worker_process.poll() is None:
            worker_process.terminate()
        
        print("Waiting for processes to finish...")
        try:
            web_process.wait(timeout=5)
            worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing processes...")
            web_process.kill()
            worker_process.kill()
        
        # Clean up status files
        for file in ["web_app_ready.txt", "duplicate_cache_status.json"]:
            try:
                Path(file).unlink()
            except FileNotFoundError:
                pass
        
        print("All processes terminated")

if __name__ == "__main__":
    print("Starting Contact Manager...")
    run_all() 