import requests

TOKEN = "YOUR_BOT_TOKEN"
url = f"https://api.telegram.org/bot8458001052:AAGwkvpa15VLfXv69vkAnS3HjcAR-8S8p8U/getUpdates"

resp = requests.get(url)
print(resp.json())
