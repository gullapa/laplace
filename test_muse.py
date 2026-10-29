"""
Step 3 test: can Meta's reasoning model read the tower from a photo, and how fast is it?

Usage (evidence-os folder, venv active):
    python test_muse.py                                   # muse-wonder-1.0 on phone_2.jpg
    python test_muse.py --photo glasses_2_front.png
    python test_muse.py --model muse-spark-1.3            # compare a cheaper/faster model

Saves the full API response to sam_tests/muse_<model>_<photo>.json and prints the answer + timing.
"""
import argparse
import json
import mimetypes
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
API = "https://api.meta.ai/v1"
HDR = {"Authorization": f"Bearer {os.environ['MODEL_API_KEY']}"}

QUESTION = """This photo shows a stacked wooden block tower (3 blocks per level, levels normally
alternate direction). Looking only at what is visible from this camera angle:
1. How many levels does the tower have (count from the bottom = level 1)?
2. For each level, say whether you see the blocks' small END faces or one long SIDE face,
   and for END-face levels say which of the 3 slots (left, middle, right) hold a block.
3. Which slots or levels can you NOT determine from this view, and what view would resolve them?
Reply with JSON only:
{"levels": [{"level": 1, "visible_face": "ends|side", "slots": ["filled|empty|unknown", ...]}],
 "cannot_determine": ["..."], "suggested_view": "..."}"""


def upload(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    with path.open("rb") as fh:
        r = requests.post(f"{API}/files", headers=HDR, data={"purpose": "user_data"},
                          files={"file": (path.name, fh, mime)}, timeout=120)
    if not r.ok:
        raise SystemExit(f"Upload failed {r.status_code}: {r.text[:500]}")
    return r.json()["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="muse-wonder-1.0")
    ap.add_argument("--photo", default="phone_2.jpg")
    a = ap.parse_args()
    photo = Path("test_photos") / a.photo
    fid = upload(photo)
    payload = {
        "model": a.model,
        "input": [{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": QUESTION},
            {"type": "input_image", "file_id": fid},
        ]}],
    }
    t0 = time.time()
    r = requests.post(f"{API}/responses", json=payload, timeout=600,
                      headers={**HDR, "Content-Type": "application/json"})
    dt = time.time() - t0
    if not r.ok:
        raise SystemExit(f"Model call failed {r.status_code}: {r.text[:800]}")
    data = r.json()
    Path("sam_tests").mkdir(exist_ok=True)
    out = Path("sam_tests") / f"muse_{a.model}_{photo.stem}.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    text = "\n".join(p.get("text", "") for it in data.get("output", [])
                     if it.get("type") == "message" for p in it.get("content", []))
    print(text or "(no message text found - see saved JSON)")
    print(f"\nModel: {a.model}   time: {dt:.1f}s   usage: {data.get('usage')}")
    print(f"Saved full response to {out}")


if __name__ == "__main__":
    main()
