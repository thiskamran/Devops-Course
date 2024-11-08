import flask
from flask import jsonify
import requests
import socket
import psutil
import shutil
import time
import sys
import os
import signal
import subprocess
import docker
import time

app = flask.Flask(__name__)

# Global variable to track shutdown status
is_shutting_down = False

def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

def get_processes():
    return [p.info['name'] for p in psutil.process_iter(['name'])]

def get_disk_space():
    total, used, free = shutil.disk_usage("/")
    return f"Total: {total // (2**30)}GB, Used: {used // (2**30)}GB, Free: {free // (2**30)}GB"

def get_uptime():
    return time.time() - psutil.boot_time()

@app.route('/')
def get_info():
    # Gather information from Service1
    service1_info = {
        "Service1": {
            "IP": get_ip_address(),
            "Processes": get_processes(),
            "Disk Space": get_disk_space(),
            "Uptime": get_uptime()
        }
    }

    # Fetch data from Service2
    service2_url = "http://service2:8080"
    try:
        service2_response = requests.get(service2_url)
        service2_info = service2_response.json()
    except Exception as e:
        service2_info = {"Service2": {"Error": str(e)}}

    # Combine both Service1 and Service2 data
    combined_info = {**service1_info, **service2_info}
    return jsonify(combined_info)

@app.route('/api/', methods=['GET'])
def api_response():
    time.sleep(2)  # Sleep for 2 seconds
    return jsonify({"message": "Response from Service 1"}), 200


@app.route('/stop', methods=['POST'])
def stop_services():
    # Log shutdown for confirmation
    print("Shutting down services...")
    sys.stdout.flush()
    
    is_shutting_down = True

    try:
        
        # Create a Docker client
        client = docker.from_env()

        # Stop all running containers
        for container in client.containers.list():
            print(f"Stopping container: {container.name}")
            container.stop()
        print("All services have been stopped.")
    except Exception as e:
        print(f"Error shutting down services: {e}")
        return jsonify({"error": str(e)}), 500
    # subprocess.call(["docker-compose", "down"])
    os.kill(os.getpid(), signal.SIGTERM)
    print("Services have been shut down.")
    return jsonify({"message": "Shutdown in progress"}), 200

@app.route('/api/status', methods=['GET'])
def status():
    if is_shutting_down:
        return jsonify({"status": "Shutting down"}), 503  # 503 Service Unavailable
    return jsonify({"status": "Running"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8199)
