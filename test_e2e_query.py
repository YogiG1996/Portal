import requests

# Adjust if running on a different port or host
BASE_URL = 'http://127.0.0.1:5000'

# Simulate a POST to /query as the portal would
payload = {
    'application': 'B2C Frontend',
    'jsession_id': '',
    'time_span': '10080',  # Last 7 days
    'limit': '100'
}

response = requests.post(f'{BASE_URL}/query', data=payload)
print('Status code:', response.status_code)
print('Response text:')
print(response.text)
