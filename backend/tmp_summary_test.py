import requests

payload = {
    "session_id": "185",
    "conversation_history": [
        {"role": "assistant", "content": "Hello, how have you been feeling since your last check-in?"},
        {"role": "user", "content": "hand pain"},
        {"role": "assistant", "content": "Could you describe the location and intensity of the hand pain? Also let me know if it started recently or has been ongoing."},
        {"role": "user", "content": "8 constant"},
        {"role": "assistant", "content": "Do you have any weakness, numbness, or difficulty with movement in the hand? Has this affected any daily activities? "},
        {"role": "user", "content": "no hand curls"},
        {"role": "assistant", "content": "Understood. I will summarize the information you provided."},
        {"role": "user", "content": "done"},
        {"role": "assistant", "content": ""}
    ]
}

response = requests.post("http://localhost:8004/ptmantra/summary", json=payload)
print(response.status_code)
print(response.text)
