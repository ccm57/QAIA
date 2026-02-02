#!/usr/bin/env python
# -*- coding: utf-8 -*-
# F:\QAIA\
"""Test manuel de transcription avec Wav2VecVoiceAgent."""

# /// script
# dependencies = [
#   "torch>=2.0.0",
#   "transformers>=4.26.0",
#   "numpy>=1.22.0",
#   "scipy>=1.9.0",
#   "sounddevice>=0.4.5",
# ]
# ///

from importlib.machinery import SourceFileLoader
from pathlib import Path

WAV2VEC_AGENT_PATH = Path(__file__).resolve().parents[1] / "agents" / "wav2vec_agent.py"
wav_module = SourceFileLoader("wav2vec_agent", str(WAV2VEC_AGENT_PATH)).load_module()
Wav2VecVoiceAgent = wav_module.Wav2VecVoiceAgent


def main() -> int:
    agent = Wav2VecVoiceAgent(
        debug=True,
        preferred_model="jonatasgrosman/wav2vec2-large-xlsr-53-french",
    )
    print("Device:", agent.device)
    audio_path = "data/audio/test_16000.wav"
    text, conf = agent.transcribe_audio(audio_path)
    print("TRANSCRIPTION:", text)
    print("CONFIDENCE:", conf)
    agent.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


