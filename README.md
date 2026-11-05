# ForeSight

ForeSight is an experimental copilot that predicts what a physical structure will do before you change it, asks for what it cannot see, and lets reality check its answer.

The working hackathon prototype is in [laplace-mvp](laplace-mvp/README.md). It combines a live phone camera, Meta SAM 3.1 visual observations, Meta Muse speech transcription and question answering, an operator-confirmed block model, a simplified static calculation, and an experimental 3D physics replay. Predictions can be locked before a physical trial and compared with user-reported outcomes.

The scan does not automatically reconstruct the tower. The 3D model is user-supplied, glasses are not integrated, and the replay does not model the force of a hand. This is a research prototype, not a structural-safety tool. See the [prototype README](laplace-mvp/README.md) for setup, tests, evidence and limitations.
