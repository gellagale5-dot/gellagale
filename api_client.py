
import requests

url = "https://gale-gella-eoam.onrender.com/course"

response = requests.get(url)

if response.status_code == 200:
    data = response.json()

    print("Course Information")
    print("Course Code:", data["course_code"])
    print("Course Title:", data["course_title"])
    print("Instructor:", data["instructor"])
    print("Semester:", data["semester"])
    print("Academic Year:", data["academic_year"])

else:
    print("Request failed.")
    print("Status Code:", response.status_code)
    print(response.text)