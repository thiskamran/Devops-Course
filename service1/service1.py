import flask
from flask import jsonify, make_response
import requests
import socket
import psutil
import shutil
import time
import sys
import os
import signal
import threading
import docker
from werkzeug.serving import is_running_from_reloader
import atexit

app = flask.Flask(__name__)

class ServiceState:
    def __init__(self):
        self.current_state = "INIT"
        self.is_shutting_down = False
        self.active_requests = 0
        self.shutdown_time = None
        self.lock = threading.Lock()
        self.state_file = "/tmp/service_state"  # Shared state file


    def start_request(self):
        with self.lock:
            if not self.is_shutting_down:
                self.active_requests += 1
                return True
            return False

    def end_request(self):
        with self.lock:
            if self.active_requests > 0:
                self.active_requests -= 1

    def start_shutdown(self):
        with self.lock:
            self.is_shutting_down = True
            self.shutdown_time = time.time()

    def get_status(self):
        with self.lock:
            return {
                "is_shutting_down": self.is_shutting_down,
                "active_requests": self.active_requests,
                "shutdown_time": self.shutdown_time,
                "uptime": get_uptime() if not self.shutdown_time else self.shutdown_time - psutil.boot_time()
            }
        
    def change_state(self, new_state):
        """Change the current state"""
        with self.lock:
            print(f"Attempting to change state to: {new_state}")  # Debug
            if new_state in ["INIT", "RUNNING", "PAUSED", "SHUTDOWN"]:
                self.current_state = new_state
                print(f"State changed to: {self.current_state}")  # Debug
                return True
            return False

    def get_current_state(self):
        """Get the current state"""
        with self.lock:
            print(f"Current state is: {self.current_state}")  # Debug
            return self.current_state
    
state = ServiceState()

def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

def get_processes():
    return [p.info['name'] for p in psutil.process_iter(['name'])]

def get_disk_space():
    total, used, free = shutil.disk_usage("/")
    return f"Total: {total // (2**30)}GB, Used: {used // (2**30)}GB, Free: {free // (2**30)}GB"

def get_uptime():
    return time.time() - psutil.boot_time()

def post_request_delay():
    """Function to sleep after request is complete"""
    time.sleep(2)

def shutdown_containers():
    """Shutdown all docker containers"""
    try:
        client = docker.from_env()
        containers = client.containers.list()
        for container in client.containers.list():
            print(f"Stopping container: {container.name}")
            container.stop(timeout=10)  # Give containers 10 seconds to stop gracefully
        return True
    except Exception as e:
        print(f"Error shutting down containers: {e}")
        return False

@app.before_request
def before_request():
    if not state.start_request():
        response = {
            "error": "Service is shutting down",
            "status": state.get_status(),
            "message": "Please try again later or check other available instances"
        }
        return make_response(jsonify(response), 503)

@app.after_request
def after_request(response):
    """Start a new thread to handle the delay after response is sent"""
    state.end_request()
    if not state.is_shutting_down:
        thread = threading.Thread(target=post_request_delay)
        thread.daemon = True  # Mark as daemon so it won't prevent shutdown
        thread.start()
    return response

@app.route('/')
def get_info():
    service1_info = {
        "Service1": {
            "IP": get_ip_address(),
            "Processes": get_processes(),
            "Disk Space": get_disk_space(),
            "Status": state.get_status()
        }
    }

    # Fetch data from Service2
    service2_url = "http://service2:8080"
    try:
        service2_response = requests.get(service2_url, timeout=5)
        service2_info = service2_response.json()
    except requests.exceptions.RequestException as e:
        service2_info = {"Service2": {"Error": str(e)}}

    combined_info = {**service1_info, **service2_info}
    return jsonify(combined_info)

@app.route('/api/', methods=['GET'])
def api_response():
    return jsonify({
        "message": "Response from Service 1",
        "status": state.get_status()
    }), 200

@app.route('/api/status', methods=['GET'])
def status():
    service_status = state.get_status()
    if state.is_shutting_down:
        return jsonify({
            "status": "Shutting down",
            "details": service_status,
            "message": "Service is gracefully shutting down. Please try other available instances."
        }), 503
    return jsonify({
        "status": "Running",
        "details": service_status
    }), 200

@app.route('/stop', methods=['POST'])
def stop_services():
    if state.is_shutting_down:
        return jsonify({
            "message": "Shutdown already in progress",
            "status": state.get_status()
        }), 409

    state.start_shutdown()
    
    def delayed_shutdown():
        # Wait for active requests to complete (max 30 seconds)
        shutdown_wait_start = time.time()
        while state.active_requests > 0 and (time.time() - shutdown_wait_start) < 30:
            time.sleep(1)
        
        # Shutdown containers
        containers_stopped = shutdown_containers()
        
        # If we're not in debug/reloader mode, terminate the process
        if not is_running_from_reloader():
            os.kill(os.getpid(), signal.SIGTERM)

    # Start shutdown process in separate thread
    shutdown_thread = threading.Thread(target=delayed_shutdown)
    shutdown_thread.daemon = True
    shutdown_thread.start()

    return jsonify({
        "message": "Graceful shutdown initiated",
        "status": state.get_status(),
        "details": {
            "active_requests": state.active_requests,
            "shutdown_time": state.shutdown_time,
            "note": "Service will complete active requests before shutting down"
        }
    }), 202

@app.route('/state', methods=['GET'])
def get_state():
    current_state = state.get_current_state()
    return current_state

@app.route('/state', methods=['PUT'])
def update_state():
    new_state = flask.request.get_data().decode('utf-8')
    success = state.change_state(new_state)
    current = state.get_current_state()  # Get current state after change
    if success:
        return jsonify({
            "state": current,
            "message": "State updated"
        }), 200
    return jsonify({"error": "Invalid state"}), 400
# Register cleanup function
@atexit.register
def cleanup():
    print("Performing cleanup before shutdown...")
    # Additional cleanup tasks can be added here

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8199, threaded=True)