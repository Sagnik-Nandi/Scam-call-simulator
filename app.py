"""Entrypoint for Hugging Face Spaces (Gradio SDK) and local demo.

Why this serves our bespoke mobile web UI instead of stock Gradio widgets:
- Hugging Face's free Gradio SDK simply executes `python app.py` and routes HTTPS traffic to port 7860.
- By serving `backend.app:app` (FastAPI) on port 7860, we get a flagship-grade mobile phone-call UI
  (with Web Audio API auto-play, one-tap MediaRecorder, silence timers, iOS-style OTP push banner,
  and WhatsApp/Instagram-grade glassmorphic call screen) while running 100% natively on a free
  Hugging Face Gradio Space!
"""
import os
import uvicorn
from backend.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("GRADIO_SERVER_PORT", "7860")))
    uvicorn.run(app, host="0.0.0.0", port=port)
