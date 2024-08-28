import requests
import time
from requests.auth import HTTPDigestAuth
import json
import os

# Configuration
PRINTER_IP = '192.168.101.146'  # Replace with your printer's IP address
APPLICATION_NAME = 'Suppliflow'
USER_NAME = 'hof-university/sacharya2'
CREDENTIALS_FILE = 'credentials.json'

# Endpoints
AUTH_REQUEST_URL = f'http://{PRINTER_IP}/api/v1/auth/request'
AUTH_CHECK_URL = lambda app_id: f'http://{PRINTER_IP}/api/v1/auth/check/{app_id}'
AUTH_VERIFY_URL = f'http://{PRINTER_IP}/api/v1/auth/verify'
PRINTER_STATUS_URL = f'http://{PRINTER_IP}/api/v1/printer/status'
START_PRINT_JOB_URL = f'http://{PRINTER_IP}/api/v1/print/start'
PRINTER_LED_BLINK = f'http://{PRINTER_IP}/api/v1/printer/led/blink'
PRINTER_START_JOB = f'http://{PRINTER_IP}/api/v1/print_job'
PRINTER_PROGRESS = f'http://{PRINTER_IP}/api/v1/print_job/progress'
PRINTER_REAL_TIME = f'http://{PRINTER_IP}/api/v1/print_job'

# Define the relative path to the file
project_root = os.path.dirname(__file__)  # Gets the directory of the currently running script
sample_files_folder = 'sample_files'
file_name = 'UMS5_SAH.ufp'
# Construct the full path to the file
file_path = os.path.join(project_root, sample_files_folder, file_name)

def authenticate():
    """Authenticate with the Ultimaker S5 and return id and key."""
    response = requests.post(AUTH_REQUEST_URL, data={
        'application': APPLICATION_NAME,
        'user': USER_NAME
    })
    
    if response.status_code == 200:
        auth_data = response.json()
        app_id = auth_data['id']
        app_key = auth_data['key']
        # Store credentials
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump({'id': app_id, 'key': app_key}, f)
        return app_id, app_key
    else:
        raise Exception(f"Failed to authenticate: {response.status_code} {response.text}")
    
def load_credentials():
    """Load stored credentials from a file."""
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
            return credentials.get('id'), credentials.get('key')
    return None, None

def check_authorization(app_id):
    """Check if the application is authorized."""
    while True:
        response = requests.get(AUTH_CHECK_URL(app_id))
        if response.status_code == 200:
            status = response.json().get('message')
            if status == 'authorized':
                print("Application is authorized.")
                return True
            elif status == 'unauthorized':
                print("Application is not authorized.")
                return False
            else:
                print("Waiting for authorization...")
        else:
            print(f"Failed to check authorization status: {response.status_code}")
            print(response.text)
        time.sleep(2)  # Wait before checking again

def verify_authentication(app_id, app_key):
    """Verify authentication with the obtained credentials."""
    response = requests.get(AUTH_VERIFY_URL, auth=HTTPDigestAuth(app_id, app_key))
    if response.status_code == 200:
        print("Authentication verification successful.")
    else:
        print(f"Authentication verification failed: {response.status_code}")
        print(response.text)

def get_printer_progress(app_id, app_key):
    """Retrieve the current status of the printer."""
    response = requests.get(PRINTER_PROGRESS, auth=HTTPDigestAuth(app_id, app_key))
    if response.status_code == 200:
        status = response.json()
        return status
        
    else:
        print(f"Failed to retrieve printer status: {response.status_code}")
        print(response.text)

def get_printer_realTime_data(app_id, app_key):
    """Retrieve the current status of the printer."""
    response = requests.get(PRINTER_REAL_TIME, auth=HTTPDigestAuth(app_id, app_key))
    if response.status_code == 200:
        status = response.json()
        return status
    else:
        print(f"Failed to retrieve printer status: {response.status_code}")
        print(response.text)

def get_printer_status(app_id, app_key):
    """Retrieve the current status of the printer."""
    response = requests.get(PRINTER_STATUS_URL, auth=HTTPDigestAuth(app_id, app_key))
    if response.status_code == 200:
        status = response.json()
        return status
    else:
        print(f"Failed to retrieve printer status: {response.status_code}")
        print(response.text)

def led_blink(frequency, count, app_id, app_key):
    response = requests.post(PRINTER_LED_BLINK, auth=HTTPDigestAuth(app_id, app_key), data={
        'frequency': frequency,
        'count': count
    })
    if response.status_code == 204:
        print("LED is blinking")
    else:
        raise Exception(f"LED not blinking: {response.status_code} {response.text}")
        
def start_print_job(app_id, app_key):
    """Start a print job with the specified file."""
    with open(file_path, 'rb') as file:
        files = {
            'file': (file_path, file, 'application/octet-stream')
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
        if response.status_code == 201:
            print("Print job started successfully.")
        else:
            print(f"Failed to start print job: {response.status_code}")
            print(response.text)

def main():
    try:
        app_id, app_key = load_credentials()
        if not app_id or not app_key:
            print("No valid credentials found. Authenticating...")
            app_id, app_key = authenticate()
        
        # Check authorization
        if check_authorization(app_id):
            # Verify authentication
            verify_authentication(app_id, app_key)
            
            # Retrieve and print printer status
            printer_current_status = get_printer_status(app_id, app_key)
            print("Printer Status:", printer_current_status)

            #printer progress
            progress_in_percent = get_printer_progress(app_id,app_key)
            print("Printer Status:", f'Progress: {progress_in_percent*100} %')

            #Real-Time Data
            real_time_info = get_printer_realTime_data(app_id,app_key)
            # Extract time values
            time_elapsed = real_time_info['time_elapsed']
            time_total = real_time_info['time_total']
            printer_state = real_time_info['state']
            print('The status of the printer is: ', printer_state)
            # Calculate remaining time in seconds
            remaining_time_seconds = time_total - time_elapsed
            # Convert remaining time to minutes
            remaining_time_minutes = remaining_time_seconds / 60
            print(f"Remaining time: {remaining_time_minutes:.2f} minutes")

            #Blink the LED
            #led_blink(2, 10, app_id, app_key)

            #Giving a printing job
            if printer_current_status == 'idle':
                start_print_job(app_id,app_key)
            else:
                print("Printing cannot be started, other operation is in progress")
        else:
            print("Application not authorized. Exiting.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()