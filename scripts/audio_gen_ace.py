#!/usr/bin/env python3
"""audio-gen-ace — ACE-Step full-song worker (structured tags + tunable guidance)."""
from __future__ import annotations

import argparse
import os
import sys
import time


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="audio-gen-ace")
    p.add_argument("--model", default="ace-step")
    p.add_argument("--modality", default="music")
    p.add_argument("--prompt", required=True, help="Style tags / description (comma tags preferred)")
    p.add_argument("--seconds", type=float, default=120.0)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--lyrics", default="",
                   help="Structure lyrics: [intro]/[verse]/... or empty for default instrumental map")
    p.add_argument("--infer-step", type=int, default=50)
    p.add_argument("--guidance-scale", type=float, default=10.0)
    p.add_argument("--min-guidance-scale", type=float, default=3.0)
    p.add_argument("--omega-scale", type=float, default=10.0)
    p.add_argument("--scheduler-type", default="euler", choices=["euler", "heun", "pingpong"])
    p.add_argument("--cfg-type", default="apg")
    p.add_argument(
        "--checkpoint",
        default=os.environ.get("ACE_STEP_CKPT", "/home/gad/.cache/ace-step/checkpoints"),
    )
    p.add_argument("--cpu-offload", action="store_true", default=True)
    p.add_argument("--no-cpu-offload", action="store_true")
    p.add_argument("--bf16", action="store_true", default=True)
    p.add_argument("--no-bf16", action="store_true")
    return p.parse_args(argv)


DEFAULT_INSTRUMENTAL_MAP = """[intro]
[verse]
[verse]
[pre-chorus]
[chorus]
[verse]
[chorus]
[bridge]
[chorus]
[outro]
"""


def main(argv=None) -> int:
    args = parse_args(argv)
    seconds = max(30.0, min(float(args.seconds), 240.0))
    out = os.path.abspath(args.out or f"ace-step-{int(time.time())}.wav")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    cpu_offload = False if args.no_cpu_offload else True
    bf16 = False if args.no_bf16 else True
    seed = args.seed if args.seed is not None else int(time.time()) % 2_000_000_000
    lyrics = (args.lyrics or "").strip()
    if not lyrics or lyrics in ("[Instrumental]", "[inst]"):
        lyrics = DEFAULT_INSTRUMENTAL_MAP

    print(
        f"[audio-gen-ace] model=ACE-Step-v1-3.5B seconds={seconds} "
        f"steps={args.infer_step} guidance={args.guidance_scale} "
        f"scheduler={args.scheduler_type} seed={seed} out={out}",
        file=sys.stderr,
    )
    t0 = time.time()

    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio

    def _save_soundfile(uri, src, sample_rate, channels_first=True, **kwargs):
        audio = src.detach().cpu().float().numpy() if isinstance(src, torch.Tensor) else np.asarray(src)
        if audio.ndim == 2 and channels_first:
            audio = audio.T
        sf.write(uri, audio, int(sample_rate))

    torchaudio.save = _save_soundfile

    from acestep.pipeline_ace_step import ACEStepPipeline

    pipe = ACEStepPipeline(
        checkpoint_dir=args.checkpoint,
        dtype="bfloat16" if bf16 else "float32",
        torch_compile=False,
        cpu_offload=cpu_offload,
        overlapped_decode=True,
    )
    pipe(
        audio_duration=seconds,
        prompt=args.prompt,
        lyrics=lyrics,
        infer_step=int(args.infer_step),
        guidance_scale=float(args.guidance_scale),
        scheduler_type=args.scheduler_type,
        cfg_type=args.cfg_type,
        omega_scale=float(args.omega_scale),
        manual_seeds=str(seed),
        guidance_interval=0.5,
        guidance_interval_decay=0.0,
        min_guidance_scale=float(args.min_guidance_scale),
        use_erg_tag=True,
        use_erg_lyric=True,
        use_erg_diffusion=True,
        oss_steps="",
        guidance_scale_text=0.0,
        guidance_scale_lyric=0.0,
        save_path=out,
    )

    if not os.path.isfile(out):
        d = os.path.dirname(out) or "."
        cands = sorted(
            [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".wav")],
            key=os.path.getmtime,
            reverse=True,
        )
        if cands:
            out = cands[0]

    elapsed = time.time() - t0
    size = os.path.getsize(out) if os.path.isfile(out) else 0
    print(out)
    print(f"[audio-gen-ace] wrote {out} bytes={size} elapsed={elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"[audio-gen-ace] FAILED: {e}", file=sys.stderr)
        raise
