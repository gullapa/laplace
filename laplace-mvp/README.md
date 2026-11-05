# ForeSight — run the prototype

ForeSight is an experimental copilot that explores what a physical structure might do before a change, asks for missing information, and compares a locked prediction with an operator-reported outcome.

This is a research prototype for a block tower, **not a structural-safety assessment**. SAM detections are candidate boxes; the block arrangement is supplied or confirmed by the user. The 3D visualization is not reconstructed from the camera. Meta glasses and SAM 3D are not integrated. The separate physics replay is experimental, assumes idealized blocks and instant removal, and does not model hand forces. Its results may differ from the static calculation or the physical outcome.

## Requirements

- Python 3.10 or later and Node.js/npm (tested on Windows; recent Node.js recommended).
- A Meta Model API key with access to SAM 3.1, Muse Spark 1.3, and Muse Voice Transcribe 1.0 for those online features. A key is not required for the local static calculation or experimental simulation.
- A current browser. Chrome was used for the demo. A microphone is required only for voice transcription.
- Optional: an Android phone running IP Webcam on the same local network as the computer, or a tower photo for the single-image SAM option.

## Setup on Windows

In PowerShell, from a directory where you want the project:

```powershell
git clone https://github.com/gullapa/laplace.git
cd laplace\laplace-mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm ci
Copy-Item .env.example .env
```

Open `laplace-mvp\.env` in a text editor and replace the placeholder with your own key:

```text
MODEL_API_KEY=your_meta_model_api_key
```

Then start the local server:

```powershell
python server.py
```

Open **http://127.0.0.1:8765/** in the browser on the same computer. Keep the terminal open while using the app. Stop the server with Ctrl+C.

If PowerShell blocks virtual environment activation, you can install and run using the virtual environment's Python directly instead of changing system settings:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

On macOS/Linux, create the virtual environment with `python3 -m venv .venv`, activate with `source .venv/bin/activate`, and use `python -m pip install -r requirements.txt`, `npm ci`, `cp .env.example .env`, then `python server.py` from `laplace-mvp/`.

The key stays in your local `.env`. Never commit it or paste it into an issue. The repository excludes `.env`, run logs, and dependencies through `.gitignore`. SAM image and Muse requests go to the Meta Model API and use your account's access and credits.

## Run the demonstration

1. Build a complete tower and point the camera at it. Enter the `http://` address displayed by IP Webcam and click **CONNECT**. The camera and laptop must be reachable on the same local network. Alternatively, use **UPLOAD PHOTO** for a still image. Guided view collection requires a connected phone stream.
2. Under **GUIDED VIEW COLLECTION**, capture a view. The app sends the still image to SAM 3.1 and displays candidate boxes on that captured image. For additional views, gently turn the tower only if it remains stable; the operator assigns the view labels. **ASK MUSE ABOUT VIEWS** optionally sends box coordinates and counts to Muse, not the images themselves.
3. Confirm the model manually. If every block is present and the tower is aligned, click **CONFIRM ALL PRESENT**. Set **BOTTOM VIEW** to match the starting camera view. To explore uncertainty, select a block and click **MARK UNKNOWN**; the model will not treat that position as verified.
4. Select a present block, click **ASSESS THIS MOVE**, and optionally click **PLAY 3D SIMULATION**. The static assessment and replay are separate models; report any disagreement. Click **LOCK PREDICTION** before performing a physical move.
5. After the move, select **IT STOOD**, **IT FELL**, or **UNCLEAR**. Check **I steadied the tower (assisted)** when applicable. Assisted or unclear outcomes are not scored as a match. Predictions and operator-reported results are stored locally in `runs/events.jsonl`; they do not independently prove when a physical action occurred.
6. To try speech, click **RECORD**, speak, and click **STOP**. Review the transcription, then click **ASK MUSE** for an optional response. Speech is transcribed but does not automatically select or move blocks. The browser supplies the spoken response voice; choose one under **SPOKEN RESPONSE VOICE**.

The demo can use an intentionally withheld block state to demonstrate clarification; disclose that the fact was deliberately withheld. Record the prediction lock and physical action continuously if presenting them as evidence.

## Troubleshooting

- **Page will not open:** confirm `python server.py` is still running and use `http://127.0.0.1:8765/` on the same computer. If the port is occupied, stop only the process you recognize as the earlier ForeSight server.
- **Meta request fails:** confirm `MODEL_API_KEY` is set in `.env`, your account can access the named model, and the computer has network access. Static assessment and the local simulation do not require the API.
- **Phone stream will not connect:** keep IP Webcam's server running, use the HTTP address it displays, and check that both devices can reach each other on the local network. The snapshot endpoint accepts a private IP address. For a still-image SAM test, use **UPLOAD PHOTO**.
- **Microphone or voice playback fails:** permit microphone access for the local page when recording; verify the browser, selected voice, and speaker volume. Voice availability varies by browser and device.
- **3D playback cannot load:** run `npm ci` from `laplace-mvp/`; it installs the `cannon-es` dependency used by the browser module.
- **The page was refreshed:** the on-screen tower and scan cards reset. Previously saved local run events remain in `runs/`.

## Tests

From `laplace-mvp/`:

```text
python -m unittest -v test_engine test_api
node test_physics.mjs
```

The API tests use a temporary local HTTP server and do not call Meta. The physics tests use simplified reference arrangements, not a validated engineering benchmark.

## Evidence and limitations

Two earlier unassisted outcomes were reported by the operator as matching locked static assessments: one stand and one fall. They were not continuously recorded by this prototype. Other tests used hand assistance and were marked not comparable. This small set of trials does not establish predictive accuracy. Longer physics simulations have shown instability, and model signals can disagree. Do not use ForeSight to make real-world safety decisions.
