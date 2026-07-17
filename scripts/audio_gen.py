#!/usr/bin/env python3
"""audio-gen — murakumo fleet music worker (MusicGen OSS path).

Matches cloud-murakumo.engine :audio argv:
  audio-gen --model <id> --modality music|sfx --prompt "..." --seconds N

Models:
  musicgen-small  (default, facebook/musicgen-small, MIT-friendly small OSS)
  musicgen-medium
  ace-step        (alias → musicgen-small until ACE-Step weights land)
  stable-audio-open (alias → musicgen-small until SAO checkpoint is on fleet)

Writes WAV to CWD (or --out) and prints the path on stdout.
"""
from __future__ import annotations

import argparse
import os
import sys
import time


MODEL_ALIASES = {
    "ace-step": "facebook/musicgen-small",
    "stable-audio-open": "facebook/musicgen-small",
    "musicgen-small": "facebook/musicgen-small",
    "musicgen-medium": "facebook/musicgen-medium",
    "facebook/musicgen-small": "facebook/musicgen-small",
    "facebook/musicgen-medium": "facebook/musicgen-medium",
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="audio-gen")
    p.add_argument("--model", default="musicgen-small")
    p.add_argument("--modality", default="music")
    p.add_argument("--prompt", required=True)
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--negative", default="")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    hf_id = MODEL_ALIASES.get(args.model, args.model)
    seconds = max(1.0, min(float(args.seconds), 30.0))
    out = args.out or f"murakumo-aud-{int(time.time())}.wav"

    # Prefer ROCm/CUDA when available; MusicGen falls back to CPU.
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[audio-gen] model={hf_id} device={device} seconds={seconds}", file=sys.stderr)

    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    import scipy.io.wavfile
    import numpy as np

    processor = AutoProcessor.from_pretrained(hf_id)
    model = MusicgenForConditionalGeneration.from_pretrained(hf_id)
    model = model.to(device)
    model.eval()

    prompt = args.prompt
    if args.negative:
        # Soft negative: append avoidance text (MusicGen has no native CFG-neg).
        prompt = f"{prompt}. Avoid: {args.negative}"

    inputs = processor(text=[prompt], padding=True, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # MusicGen: ~50 tokens ≈ 1s at 32 kHz for small/medium family.
    max_new_tokens = max(64, int(seconds * 50))
    gen_kwargs = {"max_new_tokens": max_new_tokens, "do_sample": True, "guidance_scale": 3.0}
    if args.seed is not None:
        torch.manual_seed(int(args.seed))
        if device == "cuda":
            torch.cuda.manual_seed_all(int(args.seed))

    with torch.no_grad():
        audio_values = model.generate(**inputs, **gen_kwargs)

    sampling_rate = model.config.audio_encoder.sampling_rate
    audio = audio_values[0, 0].cpu().numpy()
    # peak normalize lightly
    peak = float(np.max(np.abs(audio))) or 1.0
    if peak > 1e-6:
        audio = (audio / peak) * 0.9
    audio_i16 = (audio * 32767.0).astype(np.int16)
    scipy.io.wavfile.write(out, rate=sampling_rate, data=audio_i16)

    abs_out = os.path.abspath(out)
    print(abs_out)
    print(
        f"[audio-gen] wrote {abs_out} samples={audio_i16.shape[-1]} sr={sampling_rate}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"[audio-gen] FAILED: {e}", file=sys.stderr)
        raise
