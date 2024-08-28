from flask import Flask, jsonify, request, render_template
import requests
from requests.auth import HTTPDigestAuth
import json
import time
import os

app = Flask(__name__)

# Configuration
PRINTER_IP          = '192.168.101.146'  # Replace with your printer's IP address
APPLICATION_NAME    = 'Suppliflow'
USER_NAME           = 'hof-university/sacharya2'
CREDENTIALS_FILE    = 'credentials.json'
verification_status = 0
app_id              = 0
app_key             = 0
uploaded_file       = None

# Endpoints
AUTH_REQUEST_URL    = f'http://{PRINTER_IP}/api/v1/auth/request'
AUTH_CHECK_URL      = lambda app_id: f'http://{PRINTER_IP}/api/v1/auth/check/{app_id}'
AUTH_VERIFY_URL     = f'http://{PRINTER_IP}/api/v1/auth/verify'
PRINTER_STATUS_URL  = f'http://{PRINTER_IP}/api/v1/printer/status'
START_PRINT_JOB_URL = f'http://{PRINTER_IP}/api/v1/print/start'
PRINTER_LED_BLINK   = f'http://{PRINTER_IP}/api/v1/printer/led/blink'
PRINTER_START_JOB   = f'http://{PRINTER_IP}/api/v1/print_job'
PRINTER_PROGRESS    = f'http://{PRINTER_IP}/api/v1/print_job/progress'
PRINTER_REAL_TIME   = f'http://{PRINTER_IP}/api/v1/print_job'

@app.route('/')
def index():
    return render_template('index.html')

def authenticate():
    response = requests.post(AUTH_REQUEST_URL, data={
        'application': APPLICATION_NAME,
        'user': USER_NAME
    })
    
    if response.status_code == 200:
        auth_data = response.json()
        app_id = auth_data['id']
        app_key = auth_data['key']
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump({'id': app_id, 'key': app_key}, f)
        return app_id, app_key
    else:
        raise Exception(f"Failed to authenticate: {response.status_code} {response.text}")

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
            return credentials.get('id'), credentials.get('key')
    return None, None

def check_authorization(app_id):
    while True:
        response = requests.get(AUTH_CHECK_URL(app_id))
        if response.status_code == 200:
            status = response.json().get('message')
            if status == 'authorized':
                return True
            elif status == 'unauthorized':
                return False
            else:
                time.sleep(2)
        else:
            time.sleep(2)

def verify_authentication(app_id, app_key):
    response = requests.get(AUTH_VERIFY_URL, auth=HTTPDigestAuth(app_id, app_key))
    return response.status_code == 200

def get_printer_realTime_data(app_id, app_key):
    response_realTime = requests.get(PRINTER_REAL_TIME, auth=HTTPDigestAuth(app_id, app_key))
    if response_realTime.status_code == 200:
        printer_realTime = response_realTime.json()
        response_progress = requests.get(PRINTER_PROGRESS, auth=HTTPDigestAuth(app_id, app_key))
        if response_progress.status_code == 200:
            printer_progress = (response_progress.json())*100
            return printer_realTime, printer_progress 
    return None, None

def get_printer_status(app_id, app_key):
    response_status = requests.get(PRINTER_STATUS_URL, auth=HTTPDigestAuth(app_id, app_key))
    if response_status.status_code == 200:
        return response_status.json()
    return None

def start_print_job(app_id, app_key, uploaded_file):
    files = {
        'file': (uploaded_file.filename, uploaded_file, 'application/octet-stream')
    }
    data = {
        'jobname': 'Sample'
    }
    response = requests.post(
        PRINTER_START_JOB,
        files=files,
        data=data,
        auth=HTTPDigestAuth(app_id, app_key)
    )
    return response.status_code == 201

@app.route('/confirm_print', methods=['POST'])
def start_print_job_endpoint():
    if verification_status:
        if start_print_job(app_id, app_key, uploaded_file):
            return jsonify({"message": "Print job started successfully."}), 201
        else:
            return jsonify({"message": "Failed to start print job."}), 500
    return jsonify({"message": "Unauthorized."}), 401

@app.route('/start_print_job', methods=['POST'])
def start_print_job_endpoint():
    if verification_status:
        if 'file' not in request.files:
            return False
            #return jsonify({"message": "No file part in the request."}), 400
        else:      
            uploaded_file = request.files['file']
            if uploaded_file.filename == '':
                return False
                #return jsonify({"message": "No selected file."}), 400
            else:
                return True      
    return jsonify({"message": "Unauthorized."}), 401

@app.route('/get_printer_status', methods=['GET'])
def get_printer_status_endpoint():
    global verification_status
    global app_id, app_key
    app_id, app_key = load_credentials()
    if not app_id or not app_key:
        app_id, app_key = authenticate()
    
    if check_authorization(app_id) and verify_authentication(app_id, app_key):
        status = get_printer_status(app_id, app_key)
        if status:
            verification_status = True
            return jsonify(status), 200
        else:
            verification_status = False
            return jsonify({"message": "Failed to retrieve printer status."}), 500
    return jsonify({"message": "Unauthorized."}), 401

@app.route('/get_printer_realTime_data', methods=['GET'])
def get_printer_realTime_data_endpoint():    
    if verification_status:
        realTime_data, progress_data = get_printer_realTime_data(app_id, app_key)
        if realTime_data and progress_data:
            return jsonify({"real_time_data": realTime_data, "progress_data in Percentage": progress_data}), 200
        else:
            return jsonify({"message": "Failed to retrieve real-time data."}), 500
    return jsonify({"message": "Unauthorized."}), 401

if __name__ == '__main__':
    app.run(port=5000)
