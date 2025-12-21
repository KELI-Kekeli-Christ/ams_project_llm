import requests
import os
#start the record
print("Starting the record...")
response=requests.get("http://localhost:5000/record").json()
file=response.get("file")
print(file)

transcribe=requests.post("http://localhost:5000/transcribe", files={"file": open(file, "rb")}).json()
print(transcribe)
message=transcribe.get("text")
print(message)

chat=requests.post("http://localhost:5000/chat", json={"message": message}).json()
print(chat)
response=chat.get("response")
print(response)