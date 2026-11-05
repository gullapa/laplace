# FORESIGHT — Physical Foresight

FORESIGHT is a copilot that predicts what a physical structure will do before you change it, asks for what it can’t see, and then lets reality check its answer.

This prototype currently uses a phone camera, Meta SAM 3.1 and Muse. **The Meta glasses integration is not implemented here.** The approved submission line, “A working prototype built with Meta glasses, SAM 3.1 and Muse,” should be used only if the glasses integration is completed and verified.

## Current capabilities

The local interface accepts an IP Webcam video feed or uploaded photo and can submit still images to Meta SAM 3.1 for bounding boxes. The user supplies or confirms the block-slot model; SAM detections do not automatically construct it. Meta Muse Spark can ask questions about the scene and summarize SAM box coordinates and counts from the guided scan; the captured images themselves are not sent to Muse. Meta Muse Voice Transcribe can transcribe a recorded microphone question. Computer-generated voice uses the browser's speech synthesis, not Meta TTS.

An idealized static calculation assesses a selected removal and identifies ambiguous cases. Prediction locks and operator-reported outcomes are saved to `runs/events.jsonl`. Assisted trials are marked not comparable. The isometric tower is a visualization of the user-supplied model, not a 360-degree reconstruction. An optional experimental cannon-es playback computes rigid-body motion from an instantly removed block; it does not model the user's hand, and its result is separate from the static prediction.

**Research prototype only.** The model assumes aligned, rigid, equally weighted blocks, uses an aggregate layer-level support check, and does not model individual load paths, friction, forces during removal, or real-world structural safety. Predictions are hypotheses and can be wrong.

## Run

Install Python 3.10 or later and run `pip install -r requirements.txt`. Install Node.js and run `npm install` for the optional 3D physics playback. Copy `.env.example` to `.env`, and set `MODEL_API_KEY` to a Meta Model API key. Run `python server.py` and open `http://127.0.0.1:8765/` in a browser. The application binds to localhost. For Android camera streaming, run IP Webcam on the phone and enter its local HTTP address. For the camera snapshot feature, the address must be a private IPv4 address.

For each test, confirm the scene, select a present block, assess and lock the prediction **before** removing it, then record the outcome. A prediction hash is a record-integrity aid, not independent proof of timing. Retain a continuous recording for demonstration evidence. Do not put `.env`, images containing private data, or generated run logs into a public repository without review.

## Tests

Run `python -m unittest -v test_engine test_api` and `node test_physics.mjs`. The API tests open an ephemeral localhost port and use a temporary event log; they do not call Meta. Meta integration calls are made only when explicitly using the corresponding interface controls.

## Current validation

Unit tests cover basic model cases and uncertainty. Two user-reported, unassisted tests matched their locked static assessments: one tower fall and one tower stand. Assisted removals are recorded as not comparable. The physical trials were not continuously recorded by this prototype. The 3D physics replay is experimental; a short replay and the static assessment have produced different signals, and longer simulations have shown instability. This is a small initial demonstration, not a measured accuracy claim or safety validation.
