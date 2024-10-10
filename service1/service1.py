import flask
from flask import jsonify
import requests
import socket
import psutil
import shutil
import time

app = flask.Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8199)
