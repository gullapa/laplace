"""
Step 2 test: can SAM 3.1 find individual blocks in tower photos?

Usage (from the evidence-os folder, venv active):
    python test_tower_sam.py                      # all photos in test_photos/, prompt "wooden block"
    python test_tower_sam.py --prompt "block"     # try a different text prompt
    python test_tower_sam.py --only phone_1.jpg   # one photo

For each photo it saves to sam_tests/:
    <name>__<prompt>_overlay.png   photo with numbered boxes drawn on it
    <name>__<prompt>_raw.txt       raw SAM output text
and prints how many blocks were found and how long the call took.
Does not touch your existing pendulum files.
"""
import argparse
import json
import mimetypes
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
API = "https://api.meta.ai/v1"
KEY = os.environ["MODEL_API_KEY"]
HDR = {"Authorization": f"Bearer {KEY}"}
BOX_RE = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")


def upload(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    with path.open("rb") as fh:
        r = requests.post(f"{API}/files", headers=HDR, data={"purpose": "user_data"},
                          files={"file": (path.name, fh, mime)}, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Upload failed {r.status_code}: {r.text[:500]}")
    return r.json()["id"]


def segment(file_id: str, prompt: str) -> str:
    payload = {
        "model": "sam-3.1",
        "input": [{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "file_id": file_id},
        ]}],
        "stream": True,
        "metadata": {"mask_encoding": "lossless"},
    }
    final = None
    with requests.post(f"{API}/responses", json=payload, stream=True, timeout=300,
                       headers={**HDR, "Content-Type": "application/json",
                                "Accept": "text/event-stream"}) as r:
        if not r.ok:
            raise RuntimeError(f"SAM call failed {r.status_code}: {r.text[:800]}")
        for line in r.iter_lines():
            if not line.startswith(b"data: "):
                continue
            data = line[6:].decode("utf-8", errors="replace")
            if data == "[DONE]":
                break
            ev = json.loads(data)
            if ev.get("type") in ("response.completed", "response.failed", "error"):
                final = ev
    if not final or final.get("type") != "response.completed":
        raise RuntimeError(f"SAM did not complete: {json.dumps(final)[:800]}")
    return "\n".join(p.get("text", "") for it in final["response"].get("output", [])
                     for p in it.get("content", []))


def draw(path: Path, boxes, out: Path):
    img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    for i, (x1, y1, x2, y2, w, h) in enumerate(boxes, 1):
        sx, sy = img.width / w, img.height / h  # boxes are in SAM's coordinate size
        b = [x1 * sx, y1 * sy, x2 * sx, y2 * sy]
        d.rectangle(b, outline=(255, 0, 80), width=3)
        d.text((b[0] + 3, b[1] + 1), str(i), fill=(255, 255, 0), font=font)
    img.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="wooden block")
    ap.add_argument("--only")
    a = ap.parse_args()
    out_dir = Path("sam_tests"); out_dir.mkdir(exist_ok=True)
    photos = sorted(p for p in Path("test_photos").iterdir()
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if a.only:
        photos = [p for p in photos if p.name == a.only]
    tag = re.sub(r"\W+", "_", a.prompt)
    for p in photos:
        t0 = time.time()
        try:
            text = segment(upload(p), a.prompt)
        except Exception as e:
            print(f"{p.name:24s} ERROR: {e}")
            continue
        boxes = [tuple(map(int, m)) for m in BOX_RE.findall(text)]
        (out_dir / f"{p.stem}__{tag}_raw.txt").write_text(text, encoding="utf-8")
        draw(p, boxes, out_dir / f"{p.stem}__{tag}_overlay.png")
        print(f"{p.name:24s} blocks found: {len(boxes):3d}   time: {time.time() - t0:5.1f}s")
    print(f"\nOverlays saved in {out_dir.resolve()}")


if __name__ == "__main__":
    main()
