"""
Generate laplace/ui/mock/mock_scenario.jsonl - a DEV DATA event stream for
building the UI without the backend (see docs/LAPLACE_UI_SPEC.txt, Sec. 11).

The SAM 3.1 boxes are REAL outputs saved in tests/fixtures/sam/.
Everything else (slot states, timings, outcomes) is scripted DEV DATA.

Run from the repo root:  python scripts/make_mock_scenario.py
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "sam"
OUT = ROOT / "laplace" / "ui" / "mock" / "mock_scenario.jsonl"
BOX_RE = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
LEVELS = 18
ORIENT = ["SIDE" if (lvl % 2 == 1) else "ENDS" for lvl in range(1, LEVELS + 1)]  # L1 = SIDE
RUN_ID = "mock-2026-10-29"


def boxes(name):
    found = [tuple(map(int, m)) for m in BOX_RE.findall((FIX / name).read_text(encoding="utf-8"))]
    return [{"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3]} for b in found], found[0][4], found[0][5]


def map_boxes_to_slots(bxs, view_face):
    """Rough row/column mapping of real boxes to slots, for image_box links only."""
    y0 = min(b["y1"] for b in bxs); y1 = max(b["y2"] for b in bxs)
    x0 = min(b["x1"] for b in bxs); x1 = max(b["x2"] for b in bxs)
    lh = (y1 - y0) / LEVELS; cw = (x1 - x0) / 3
    out = {}
    for b in bxs:
        yc = (b["y1"] + b["y2"]) / 2; xc = (b["x1"] + b["x2"]) / 2
        level = LEVELS - int((yc - y0) // lh)
        level = max(1, min(LEVELS, level))
        o = ORIENT[level - 1]
        # front view: ENDS levels show 3 ends (L/M/R); SIDE levels show the front block (index 0)
        # left/right view: the roles swap
        shows_ends = (o == "ENDS") if view_face == "front" else (o == "SIDE")
        col = max(0, min(2, int((xc - x0) // cw)))
        if not shows_ends:
            idx = 0
        elif view_face == "left":
            idx = 2 - col      # from the left side, the FRONT of the tower is on the image's right
        else:
            idx = col          # front view: L/M/R; right view: F/M/B left-to-right
        out[(level, idx)] = b
    return out


class Stream:
    def __init__(self, start):
        self.t = start; self.seq = 0; self.lines = []

    def emit(self, typ, payload, dt=0.0):
        self.t += timedelta(seconds=dt); self.seq += 1
        self.lines.append({"type": typ, "seq": self.seq,
                           "ts": self.t.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                           "run_id": RUN_ID, "dev_data": True, "payload": payload})


def label(level, idx):
    names = ["FRONT", "MIDDLE", "BACK"] if ORIENT[level - 1] == "SIDE" else ["LEFT", "MIDDLE", "RIGHT"]
    return f"L{level} · {names[idx]}"


def fingerprint(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()


def main():
    fb, fw, fh = boxes("clean_front_sam31_raw.txt")
    sb, sw, sh = boxes("clean_side_sam31_raw.txt")
    front_map = map_boxes_to_slots(fb, "front")
    side_map = map_boxes_to_slots(sb, "left")
    right_map = map_boxes_to_slots(sb, "right")
    s = Stream(datetime(2026, 11, 1, 3, 40, 0, tzinfo=timezone.utc))
    tower = {"levels": LEVELS, "slots_per_level": 3,
             "block_mm": {"length": 75, "width": 25, "height": 15}, "level_orientation": ORIENT}

    # ---------------- TRIAL 07 ----------------
    s.emit("session.start", {"mode": "REPLAY", "structure_id": "STRUCTURE 01", "trial_set": "evaluation",
                             "trial_no": 7, "app_version": "ui-mock-1"})
    s.emit("config.tower", tower, 0.2)
    for svc in ["glasses", "sam", "muse", "voice"]:
        s.emit("status.service", {"service": svc, "state": "ok"}, 0.05)
    s.emit("session.stats", {"trial_set": "evaluation", "predictions": 6, "match": 5, "mismatch": 0,
                             "inconclusive": 1, "unclear": 0}, 0.1)
    s.emit("slot.update", {"scene_version": 1, "changes": [
        {"level": l, "index": i, "state": "UNKNOWN", "source": {"kind": "rule"}}
        for l in range(1, LEVELS + 1) for i in range(3)]}, 0.1)
    s.emit("camera.frame", {"source": "tripod", "face": "front", "url": "/test_photos/clean_front.jpg",
                            "width": fw, "height": fh}, 0.5)
    # scan front
    s.emit("scan.started", {"view_id": "v1", "source": "tripod", "face": "front"}, 1.0)
    s.emit("status.service", {"service": "sam", "state": "busy"}, 0.0)
    s.emit("sam.result", {"view_id": "v1", "face": "front", "model": "sam-3.1", "prompt": "wooden block",
                          "latency_s": 4.1, "image": {"url": "/test_photos/clean_front.jpg", "width": fw,
                                                      "height": fh}, "boxes": fb, "count": len(fb)}, 4.1)
    s.emit("status.service", {"service": "sam", "state": "ok", "latency_s": 4.1}, 0.0)
    s.emit("agent.step", {"kind": "SAW", "text": f"Front view: {len(fb)} blocks detected.",
                          "model": "SAM 3.1", "latency_s": 4.1}, 0.1)
    # front view resolves: ENDS levels all 3 slots; SIDE levels only the FRONT slot (index 0)
    changes = []
    for l in range(1, LEVELS + 1):
        idxs = [0, 1, 2] if ORIENT[l - 1] == "ENDS" else [0]
        for i in idxs:
            c = {"level": l, "index": i, "state": "PRESENT_OBSERVED", "source": {"kind": "view", "view_id": "v1"}}
            if (l, i) in front_map:
                c["image_box"] = front_map[(l, i)]
            changes.append(c)
    s.emit("slot.update", {"scene_version": 2, "changes": changes}, 0.3)
    s.emit("scene.summary", {"scene_version": 2, "slots_total": 54, "observed": len(changes), "confirmed": 0,
                             "inferred": 0, "unknown": 54 - len(changes), "unknown_that_matter": 0,
                             "views": ["v1"]}, 0.1)
    s.emit("agent.step", {"kind": "MODEL", "text": f"Twin updated: {len(changes)} slots resolved from the front "
                          f"view; {54 - len(changes)} hidden behind front blocks stay UNKNOWN."}, 0.2)
    # evidence map (front-only knowledge): side-level front blocks need a view; others assessed
    em = []
    for l in range(1, LEVELS + 1):
        for i in ([0, 1, 2] if ORIENT[l - 1] == "ENDS" else [0]):
            if ORIENT[l - 1] == "SIDE" and l < LEVELS:
                em.append({"level": l, "index": i, "state": "NEEDS_VIEW", "needs_face": "left"})
            elif ORIENT[l - 1] == "ENDS" and i == 1:
                em.append({"level": l, "index": i, "state": "PREDICTS_STAND", "margin_mm": 37.5})
            elif ORIENT[l - 1] == "ENDS":
                em.append({"level": l, "index": i, "state": "PREDICTS_STAND", "margin_mm": 12.5})
            else:
                em.append({"level": l, "index": i, "state": "PREDICTS_STAND", "margin_mm": 12.5})
    s.emit("evidence_map.update", {"scene_version": 2, "blocks": em}, 0.6)
    s.emit("agent.step", {"kind": "MODEL", "text": "Evidence map ready: front blocks of the long-side levels "
                          "need a side view before I can assess them."}, 0.2)

    # question by voice
    q = {"level": 9, "index": 0, "label": label(9, 0)}
    s.emit("voice.heard", {"text": "What happens if I pull this one?", "final": True, "latency_s": 0.6}, 3.0)
    s.emit("agent.step", {"kind": "OPERATOR", "text": "Operator looked at L9 · FRONT and asked what happens "
                          "if it is pulled.", "model": "Muse Voice Transcribe", "latency_s": 0.6}, 0.1)
    s.emit("select.block", {"level": 9, "index": 0, "label": q["label"]}, 0.1)
    s.emit("agent.thinking", {"model": "Muse Spark", "started": True}, 0.1)
    s.emit("agent.thinking", {"model": "Muse Spark", "started": False}, 1.3)
    s.emit("agent.step", {"kind": "UNKNOWN", "text": "L9 · MIDDLE is hidden behind the front block - and it "
                          "decides the outcome. L9 · BACK does not change the answer.",
                          "chips": ["unknown that matter: 1"]}, 0.1)
    fut = {"question": {"level": 9, "index": 0}, "unknown_slot": {"level": 9, "index": 1, "label": label(9, 1)},
           "futures": [{"id": "A", "assume": "PRESENT", "verdict": "PREDICTS_STAND", "margin_mm": 12.5},
                       {"id": "B", "assume": "EMPTY", "verdict": "PREDICTS_FALL", "margin_mm": -12.5,
                        "critical_level": 9, "pivot": "front"}]}
    s.emit("futures.show", fut, 0.2)
    s.emit("agent.step", {"kind": "FUTURE", "text": "Future A - if L9 · MIDDLE is present: predicts stand.",
                          "chips": ["+12.5 mm"]}, 2.6)
    s.emit("agent.step", {"kind": "FUTURE", "text": "Future B - if L9 · MIDDLE is empty: predicts fall; level 10 "
                          "would rest on L9's back block alone.", "chips": ["-12.5 mm"]}, 0.2)
    s.emit("view.request", {"face": "left", "reason": "The left side shows the ends of level 9.",
                            "slots": [{"level": 9, "index": 1}, {"level": 9, "index": 2}]}, 0.3)
    s.emit("agent.step", {"kind": "ASK", "text": "Requesting the LEFT side view to resolve L9 · MIDDLE."}, 0.0)
    say = "I can't see the middle of level nine. Show me the left side."
    s.emit("say.start", {"text": say, "duration_s": 3.2}, 0.1)
    s.emit("agent.step", {"kind": "SAY", "text": say}, 0.0)
    s.emit("say.end", {}, 3.2)
    # operator looks left with glasses
    s.emit("camera.frame", {"source": "glasses", "face": "left", "url": "/test_photos/clean_side.jpg",
                            "width": sw, "height": sh}, 2.5)
    s.emit("view.captured", {"view_id": "v2", "face": "left", "source": "glasses", "width": sw, "height": sh}, 0.4)
    s.emit("scan.started", {"view_id": "v2", "source": "glasses", "face": "left"}, 0.1)
    s.emit("sam.result", {"view_id": "v2", "face": "left", "model": "sam-3.1", "prompt": "wooden block",
                          "latency_s": 4.6, "image": {"url": "/test_photos/clean_side.jpg", "width": sw,
                                                      "height": sh}, "boxes": sb, "count": len(sb)}, 4.6)
    s.emit("agent.step", {"kind": "SAW", "text": f"Left view: {len(sb)} blocks detected.", "model": "SAM 3.1",
                          "latency_s": 4.6}, 0.1)
    changes = []
    for l in range(1, LEVELS + 1):
        if ORIENT[l - 1] == "SIDE":
            for i in (1, 2):
                st = "EMPTY_OBSERVED" if (l, i) == (9, 1) else "PRESENT_OBSERVED"   # scripted DEV DATA
                c = {"level": l, "index": i, "state": st, "source": {"kind": "view", "view_id": "v2"}}
                if st == "PRESENT_OBSERVED" and (l, i) in side_map:
                    c["image_box"] = side_map[(l, i)]
                changes.append(c)
    s.emit("slot.update", {"scene_version": 3, "changes": changes}, 0.3)
    s.emit("scene.summary", {"scene_version": 3, "slots_total": 54, "observed": 54, "confirmed": 0, "inferred": 0,
                             "unknown": 0, "unknown_that_matter": 0, "views": ["v1", "v2"]}, 0.1)
    s.emit("futures.resolve", {"kept": "B", "reason": "Left view shows L9 · MIDDLE is EMPTY."}, 0.4)
    s.emit("agent.step", {"kind": "MODEL", "text": "Left view shows L9 · MIDDLE is EMPTY -> Future B."}, 0.1)
    # all slots now observed: middle blocks +37.5 mm, edge blocks +12.5 mm (aligned-tower model),
    # except level 9 where the middle is already empty: pulling either edge block leaves one edge block
    em2 = []
    for l in range(1, LEVELS + 1):
        for i in range(3):
            if (l, i) == (9, 1):
                continue                                   # empty slot - nothing to assess
            if l == 9:
                em2.append({"level": l, "index": i, "state": "PREDICTS_FALL", "margin_mm": -12.5})
            else:
                em2.append({"level": l, "index": i, "state": "PREDICTS_STAND",
                            "margin_mm": 37.5 if i == 1 else 12.5})
    s.emit("evidence_map.update", {"scene_version": 3, "blocks": em2}, 0.3)
    assess = {"question": q, "verdict": "PREDICTS_FALL", "margin_mm": -12.5,
              "thresholds_mm": {"safe": 4, "fall": 1},
              "reason": "Level 10 and above would rest only on L9's back block.",
              "critical_level": 9, "pivot": "front",
              "basis": {"views": 2, "observed": 54, "confirmed": 0, "unknown_that_matter": 0}}
    s.emit("agent.thinking", {"model": "Muse Spark", "started": True}, 0.2)
    s.emit("agent.text.delta", {"entry_id": "e1", "delta": "Model predicts a fall. "}, 0.6)
    s.emit("agent.text.delta", {"entry_id": "e1", "delta": "With the middle block already gone, "}, 0.3)
    s.emit("agent.text.delta", {"entry_id": "e1", "delta": "level 10 would rest on one edge block."}, 0.3)
    s.emit("agent.text.done", {"entry_id": "e1", "text": "Model predicts a fall. With the middle block already "
                               "gone, level 10 would rest on one edge block.", "model": "Muse Spark",
                               "latency_s": 1.2}, 0.1)
    s.emit("agent.thinking", {"model": "Muse Spark", "started": False}, 0.0)
    s.emit("assessment", assess, 0.1)
    s.emit("agent.step", {"kind": "ASSESS", "text": "PREDICTS FALL - " + assess["reason"],
                          "chips": ["-12.5 mm", "2 views", "0 unknown that matter"]}, 0.0)
    rec = {"scene_version": 3, "question": q, "verdict": "PREDICTS_FALL", "margin_mm": -12.5,
           "locked_at": (s.t + timedelta(seconds=1.5)).isoformat()}
    fp = fingerprint(rec)
    s.emit("lock.created", {"fingerprint_short": fp[:6], "fingerprint_full": fp,
                            "locked_at": (s.t + timedelta(seconds=1.5)).isoformat(timespec="seconds").replace(
                                "+00:00", "Z"), "question": q, "verdict": "PREDICTS_FALL",
                            "margin_mm": -12.5}, 1.5)
    s.emit("agent.step", {"kind": "LOCK", "text": f"Prediction locked before action · #{fp[:6]}"}, 0.0)
    say = "Model predicts a fall. Prediction locked."
    s.emit("say.start", {"text": say, "duration_s": 2.4}, 0.2)
    s.emit("agent.step", {"kind": "SAY", "text": say}, 0.0)
    s.emit("say.end", {}, 2.4)
    s.emit("action.started", {"question": q}, 2.0)
    s.emit("outcome.recorded", {"fingerprint_short": fp[:6], "observed": "OBSERVED_FALL", "source": "OPERATOR",
                                "evidence": {"video": "runs/mock/trial07.mp4"}}, 5.0)
    s.emit("agent.step", {"kind": "OUTCOME", "text": "OBSERVED FALL · operator-confirmed · video retained."}, 0.0)
    s.emit("comparison", {"fingerprint_short": fp[:6], "result": "MATCH"}, 0.8)
    s.emit("agent.step", {"kind": "COMPARE", "text": "MATCH - predicted fall, observed fall."}, 0.0)
    s.emit("session.stats", {"trial_set": "evaluation", "predictions": 7, "match": 6, "mismatch": 0,
                             "inconclusive": 1, "unclear": 0}, 0.2)

    # ---------------- TRIAL 08 ----------------
    s.emit("session.start", {"mode": "REPLAY", "structure_id": "STRUCTURE 01", "trial_set": "evaluation",
                             "trial_no": 8, "app_version": "ui-mock-1"}, 6.0)
    s.emit("slot.update", {"scene_version": 4, "changes": [
        {"level": l, "index": i, "state": "UNKNOWN", "source": {"kind": "rule"}}
        for l in range(1, LEVELS + 1) for i in range(3)]}, 0.2)
    s.emit("agent.step", {"kind": "MODEL", "text": "Tower rebuilt - new scene, previous twin cleared."}, 0.0)
    for vid, face, url, bx, w, h, mp in [("v3", "front", "/test_photos/clean_front.jpg", fb, fw, fh, front_map),
                                         ("v4", "right", "/test_photos/clean_side.jpg", sb, sw, sh, right_map)]:
        s.emit("camera.frame", {"source": "tripod", "face": face, "url": url, "width": w, "height": h}, 0.6)
        s.emit("scan.started", {"view_id": vid, "source": "tripod", "face": face}, 0.4)
        s.emit("sam.result", {"view_id": vid, "face": face, "model": "sam-3.1", "prompt": "wooden block",
                              "latency_s": 4.3, "image": {"url": url, "width": w, "height": h}, "boxes": bx,
                              "count": len(bx)}, 4.3)
        s.emit("agent.step", {"kind": "SAW", "text": f"{face.capitalize()} view: {len(bx)} blocks detected.",
                              "model": "SAM 3.1", "latency_s": 4.3}, 0.1)
        ch = []
        for l in range(1, LEVELS + 1):
            ends = (ORIENT[l - 1] == "ENDS") if face == "front" else (ORIENT[l - 1] == "SIDE")
            idxs = [0, 1, 2] if ends else ([0] if face == "front" else [])
            for i in idxs:
                c = {"level": l, "index": i, "state": "PRESENT_OBSERVED", "source": {"kind": "view", "view_id": vid}}
                if (l, i) in mp:
                    c["image_box"] = mp[(l, i)]
                ch.append(c)
        s.emit("slot.update", {"scene_version": 5 if vid == "v3" else 6, "changes": ch}, 0.3)
    s.emit("scene.summary", {"scene_version": 6, "slots_total": 54, "observed": 54, "confirmed": 0, "inferred": 0,
                             "unknown": 0, "unknown_that_matter": 0, "views": ["v3", "v4"]}, 0.1)
    q2 = {"level": 12, "index": 1, "label": label(12, 1)}
    s.emit("voice.heard", {"text": "And if I pull the middle block on level twelve?", "final": True,
                           "latency_s": 0.7}, 2.5)
    s.emit("select.block", {"level": 12, "index": 1, "label": q2["label"]}, 0.1)
    s.emit("agent.step", {"kind": "OPERATOR", "text": "Operator asked about L12 · MIDDLE.",
                          "model": "Muse Voice Transcribe", "latency_s": 0.7}, 0.0)
    s.emit("agent.step", {"kind": "MODEL", "text": "All slots that matter are observed - no extra view needed."},
           0.4)
    a2 = {"question": q2, "verdict": "PREDICTS_STAND", "margin_mm": 37.5, "thresholds_mm": {"safe": 4, "fall": 1},
          "reason": "The two edge blocks still span the full width under level 13.",
          "critical_level": None, "pivot": None,
          "basis": {"views": 2, "observed": 54, "confirmed": 0, "unknown_that_matter": 0}}
    s.emit("assessment", a2, 1.0)
    s.emit("agent.step", {"kind": "ASSESS", "text": "PREDICTS STAND - " + a2["reason"],
                          "chips": ["+37.5 mm", "2 views"]}, 0.0)
    rec2 = {"scene_version": 6, "question": q2, "verdict": "PREDICTS_STAND", "margin_mm": 37.5}
    fp2 = fingerprint(rec2)
    s.emit("lock.created", {"fingerprint_short": fp2[:6], "fingerprint_full": fp2,
                            "locked_at": (s.t + timedelta(seconds=1.2)).isoformat(timespec="seconds").replace(
                                "+00:00", "Z"), "question": q2, "verdict": "PREDICTS_STAND",
                            "margin_mm": 37.5}, 1.2)
    s.emit("agent.step", {"kind": "LOCK", "text": f"Prediction locked before action · #{fp2[:6]}"}, 0.0)
    say = "Model predicts it stands. Locked."
    s.emit("say.start", {"text": say, "duration_s": 2.0}, 0.2)
    s.emit("say.end", {}, 2.0)
    s.emit("action.started", {"question": q2}, 2.0)
    s.emit("outcome.recorded", {"fingerprint_short": fp2[:6], "observed": "OBSERVED_STAND", "source": "OPERATOR",
                                "evidence": {"video": "runs/mock/trial08.mp4"}}, 6.0)
    s.emit("agent.step", {"kind": "OUTCOME", "text": "OBSERVED STAND · operator-confirmed · video retained."}, 0.0)
    s.emit("comparison", {"fingerprint_short": fp2[:6], "result": "MATCH"}, 0.8)
    s.emit("agent.step", {"kind": "COMPARE", "text": "MATCH - predicted stand, observed stand."}, 0.0)
    s.emit("session.stats", {"trial_set": "evaluation", "predictions": 8, "match": 7, "mismatch": 0,
                             "inconclusive": 1, "unclear": 0}, 0.2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for line in s.lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"Wrote {len(s.lines)} events to {OUT}")


if __name__ == "__main__":
    main()
