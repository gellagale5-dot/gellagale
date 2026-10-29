
import requests

url = "https://jiza-mae-gubac.onrender.com/student"

try:
    response = requests.get(url, timeout=30)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        data = response.json()
        print("Classmate's API Data:")

        for key, value in data.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
    else:
        print("Request failed.")
        print(response.text)

except requests.exceptions.RequestException as error:
    print("Connection error:", error)