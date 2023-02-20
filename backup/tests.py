import requests

url = "https://api.github.com/repos/rustic-rs/rustic/releases/latest"  # Replace with your API endpoint URL
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(data['tag_name'])
    # Do something with the data
else:
    print("Request failed with status code:", response.status_code)