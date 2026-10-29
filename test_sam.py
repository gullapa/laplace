import os
from dotenv import load_dotenv
load_dotenv()
import requests
from pathlib import Path
file_path = "videos/swingingpendulum.mp4"
api_key = os.environ["MODEL_API_KEY"]

with open(file_path, "rb") as media_file:
    upload_response = requests.post(
        "https://api.meta.ai/v1/files",
        headers={"Authorization": f"Bearer {api_key}"},
        data={"purpose": "user_data"},
        files={"file": ("upload.mp4", media_file, "video/mp4")},
    )
upload_response.raise_for_status()
upload_data = upload_response.json()
file_id = upload_data.get("id")
if not isinstance(file_id, str) or not file_id:
    raise RuntimeError("File upload completed without a file id.")

payload = {
    "model": "sam-3.1",
    "input": [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "metal ball",
                },
                {
                    "type": "input_video",
                    "file_id": "",
                },
            ],
        },
    ],
    "stream": True,
    "metadata": {
        "mask_encoding": "lossless",
    },
}
payload["input"][0]["content"][1]["file_id"] = file_id

with requests.post(
    "https://api.meta.ai/v1/responses",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    },
    json=payload,
    stream=True,
) as response:
    response.raise_for_status()
    for line in response.iter_lines():
        if not line.startswith(b"data: "):
            continue
        data = line[6:].decode("utf-8", errors="replace")
        if data == "[DONE]":
            break
        with Path("sam_events.jsonl").open("a", encoding="utf-8") as f:
            f.write(data + "\n")