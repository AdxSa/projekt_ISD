import requests

url = "https://skydiver-filter-chivalry.ngrok-free.dev/receive"

data = {
    "msg": "hej",
    "number": 123
}

r = requests.post(url, json=data)

print(r.json())