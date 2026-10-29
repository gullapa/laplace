import json
import re

with open("sam_events.jsonl", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

completed = [
    event["response"]
    for event in events
    if event.get("response", {}).get("status") == "completed"
]

if not completed:
    raise RuntimeError("No completed response found")

text = "\n".join(
    part.get("text", "")
    for item in completed[-1].get("output", [])
    for part in item.get("content", [])
)

pattern = re.compile(
    r"<(\d+)f>(\d+)<\|box;x1=(\d+);y1=(\d+);"
    r"x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>"
)

records = []

for match in pattern.finditer(text):
    frame, obj, x1, y1, x2, y2, w, h = map(int, match.groups())
    records.append({
        "frame": frame,
        "object": obj,
        "center_x": (x1 + x2) / 2,
        "center_y": (y1 + y2) / 2,
    })

print("Tracking records:", len(records))
print("Unique frames:", len(set(r["frame"] for r in records)))
print("Object IDs:", sorted(set(r["object"] for r in records)))
print("First 10 records:")
for record in records[::100]:
    print(record)