import json
import re
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks


with open("sam_events.jsonl", encoding="utf-8") as f:
    events = [json.loads(line) for line in f if line.strip()]

completed = [
    event["response"]
    for event in events
    if event.get("response", {}).get("status") == "completed"
]

if not completed:
    raise RuntimeError("No completed SAM response found")

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

    if obj == 0:
        records.append((frame, (x1 + x2) / 2))

records.sort()

frames = [r[0] for r in records]
positions = [r[1] for r in records]

plt.figure(figsize=(12, 5))
plt.plot(frames, positions)
plt.xlabel("Video frame")
plt.ylabel("Horizontal position (pixels)")
plt.title("Pendulum Motion — SAM 3.1 Tracking")
plt.grid(True)
plt.tight_layout()
plt.savefig("pendulum_motion.png", dpi=150)
plt.show()
fps = 30.0
peaks, _ = find_peaks(
    positions,
    distance=25,
    prominence=100
)

peak_frames = np.array(frames)[peaks]
periods = np.diff(peak_frames) / fps

print("Peak frames:", peak_frames.tolist())
print("Individual periods (seconds):", periods.round(3).tolist())
print("Mean period:", round(float(np.mean(periods)), 3), "seconds")
print("Period standard deviation:", round(float(np.std(periods)), 3), "seconds")