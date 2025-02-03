import flask
from flask import jsonify, make_response, request
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
from datetime import datetime
import logging


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
class ServiceState:
    def __init__(self):
        self.current_state = "INIT"
        logger.info(f"ServiceState initialized with state: {self.current_state}")
        self.lock = threading.Lock()  # Initialize the lock here
        self.is_shutting_down = False
        self.active_requests = 0
        self.shutdown_time = None
        self.state_file = "/tmp/service_state"  # Shared state file
        self.state_transitions = []  # Initialize list
        logger.info(f"ServiceState initialized with state: {self.current_state}")
        self.auth_required = False

        # Add signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        
    def change_state(self, new_state, auth_provided=False):
        with self.lock:
            # Validate state
            if new_state not in ["INIT", "RUNNING", "PAUSED", "SHUTDOWN"]:
                return False, "Invalid state"

            # Check auth requirements
            if self.auth_required and not auth_provided:
                return False, "Authentication required"

            # Skip if no change
            if new_state == self.current_state:
                return True, "State unchanged"

            old_state = self.current_state
            self.current_state = new_state

            # Set auth requirement if transitioning to INIT
            if new_state == "INIT":
                self.auth_required = True
                self.reset_state()
            
            # Initiate shutdown if transitioning to SHUTDOWN
            if new_state == "SHUTDOWN":
                self._initiate_graceful_shutdown()

            self._log_transition(old_state, new_state)
            return True, "State changed"
    
    def get_current_state(self):
        logger.info(f"Getting current state: {self.current_state}")
        return self.current_state
    
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

    def _initiate_graceful_shutdown(self):
        """Handle complete shutdown sequence"""
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        self.shutdown_time = time.time()
        
        def shutdown_sequence():
            try:
                logger.info("Starting shutdown sequence")
                time.sleep(1)
                # Exit with special code 137 which Docker recognizes
                os._exit(137)
            except Exception as e:
                logger.error(f"Shutdown sequence failed: {str(e)}", exc_info=True)
                time.sleep(1)
                os._exit(1)
        
        threading.Thread(target=shutdown_sequence, daemon=True).start()

    def _handle_sigterm(self, signum, frame):
        """Handle termination signals gracefully"""
        logger.info(f"Received signal {signum}")
        self._initiate_graceful_shutdown()

    def get_status(self):
        with self.lock:
            return {
                "is_shutting_down": self.is_shutting_down,
                "active_requests": self.active_requests,
                "shutdown_time": self.shutdown_time,
                "uptime": get_uptime() if not self.shutdown_time else self.shutdown_time - psutil.boot_time()
            }

    def can_process_request(self):
        with self.lock:
            if self.current_state == "PAUSED":
                return False
            return self.current_state == "RUNNING" and not self.is_shutting_down 
    
    def _log_transition(self, old_state, new_state):
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H.%M:%S.%f')[:-3] + 'Z'
        transition = f"{timestamp}: {old_state}->{new_state}"
        self.state_transitions.append(transition)
        logger.info(f"State transition: {transition}")

    def get_run_log(self):
        return "\n".join(self.state_transitions)

    def reset_state(self):
        """Reset everything except logs"""
        self.is_shutting_down = False
        self.active_requests = 0
        self.shutdown_time = None

    def auth_success(self):
        """Call after successful authentication"""
        self.auth_required = False

    def needs_auth(self):
        return self.auth_required
    

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



@app.before_request
def before_request():
    if not state.start_request():
        response = {
            "error": "Service is shutting down",
            "status": state.get_status(),
            "message": "Please try again later or check other available instances"
        }
        return make_response(jsonify(response), 503)
    
@app.before_request
def check_state():
    # Exclude state management endpoints
    if request.path in ['/state', '/run-log', '/stop']:
        return
        
    if not state.can_process_request():
        if state.current_state == "PAUSED":
            return make_response(jsonify({
                "error": "Service is paused",
                "message": "The service is temporarily paused and cannot handle requests."
            }), 503)
        return make_response(jsonify({
            "error": "Service unavailable",
            "message": "The service is unavailable. Please try again later."
        }), 503)
    
@app.after_request
def after_request(response):
    """Start a new thread to handle the delay after response is sent"""
    state.end_request()
    if not state.is_shutting_down:
        thread = threading.Thread(target=post_request_delay)
        thread.daemon = True  # Mark as daemon so it won't prevent shutdown
        thread.start()
    return response

@app.before_request
def log_request_info():
    app.logger.info(f"Request from {request.remote_addr} to {request.path}")
    app.logger.info(f"Handled by {socket.gethostname()}")
    app.logger.info(f"Request headers: {dict(request.headers)}")


# Endpoints for the service
@app.route('/request', methods=['GET'])
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
    return str(combined_info), 200, {'Content-Type': 'text/plain'}

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
        return jsonify({"message": "Shutdown in progress"}), 409

    state.start_shutdown()
    
    def shutdown():
        time.sleep(0.1)
        try:
            # Stop service2 first
            try:
                requests.post('http://service2:8080/stop', timeout=1)
            except:
                pass

            # Stop other service1 instances
            other_services = [
                'exercise1-service1-1:8199',
                'exercise1-service1-2:8199', 
                'exercise1-service1-3:8199'
            ]
            for service in other_services:
                try:
                    requests.post(f'http://{service}/stop', timeout=1)
                except:
                    pass

            time.sleep(0.1)
            os._exit(0)
        except:
            os._exit(1)

    threading.Thread(target=shutdown).start()
    return jsonify({"message": "Shutdown initiated"}), 202


@app.route('/state', methods=['PUT', 'GET'])
def handle_state():
    if request.method == 'GET':
        return state.get_current_state(), 200, {'Content-Type': 'text/plain'}
        
    new_state = request.get_data().decode('utf-8').strip()
    auth = request.authorization
    auth_provided = auth and auth.username == 'user' and auth.password == 'test@123'

    if new_state == "SHUTDOWN":
        stop_services()
        
    success, message = state.change_state(new_state, auth_provided)
    return state.get_current_state(), 200 if success else 400






@app.route('/run-log', methods=['GET'])
def get_run_log():
    logger.info("Handling GET /run-log request")
    return state.get_run_log(), 200, {'Content-Type': 'text/plain'}

# Register cleanup function
@atexit.register
def cleanup():
    print("Performing cleanup before shutdown...")
    # Additional cleanup tasks can be added here

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=8199, threaded=True)