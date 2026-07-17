#!/usr/bin/env python3
"""Fleet-direct ongakuka coscientist runner (MusicGen on gad).

Mirrors ongaku.coscientist control flow without spinning another heavy JVM
on a contended workstation: Generate → materialize(SSH audio-gen) → score → rank.

Usage:
  python3 scripts/run_coscientist_fleet.py --genre freetempo-club --candidates 2 --seconds 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

GENRES = {
    "game-jp": {
        "bpm": 118,
        "extras": [
            "clear motif statement in first 4 bars",
            "hopeful major lift into chorus",
            "soft arpeggiated piano under lead",
        ],
        "template": (
            "Instrumental Japanese video game soundtrack, memorable melodic motif, "
            "playable JRPG field-theme energy, clear loop-friendly structure, "
            "warm strings and piano, light percussion, emotional but not dark, "
            "high production polish, BPM {bpm}. {extra}"
        ),
        "keywords": ["jrpg", "motif", "game", "piano", "strings", "loop"],
    },
    "jpop": {
        "bpm": 128,
        "extras": [
            "big pre-chorus lift",
            "sparkling chorus guitars",
            "tight sidechain-free pop drums",
        ],
        "template": (
            "Modern J-pop instrumental bed, bright catchy hook, polished radio mix, "
            "tight drums and bass, electric guitar sparkle, synth pads, "
            "verse-chorus energy, club-adjacent but melodic, BPM {bpm}. {extra}"
        ),
        "keywords": ["j-pop", "hook", "chorus", "guitar", "synth", "drums"],
    },
    "freetempo-club": {
        "bpm": 118,
        "extras": [
            "Rhodes comping slightly behind the beat",
            "soft filter open over 8 bars",
            "organic room on the kick, not super-club punch",
        ],
        "template": (
            "Warm four-on-the-floor house groove, FreeTEMPO-like nu-jazz club quality, "
            "soft Rhodes electric piano, gentle bossa / AOR influence, organic bass, "
            "brushed hi-hats, polished club mix, instrumental, no vocals, BPM {bpm}. {extra}"
        ),
        "keywords": ["house", "rhodes", "four-on-the-floor", "bossa", "club", "freetempo"],
    },
}

SSH_HOST = os.environ.get("ONGAKUKA_AUDIO_GEN_SSH", "gad")
SSH_CMD = os.environ.get(
    "ONGAKUKA_AUDIO_GEN_CMD",
    "source /home/gad/TRELLIS-AMD/.venv/bin/activate && python3 /home/gad/bin/audio-gen",
)
OUT = Path(
    os.environ.get(
        "ONGAKUKA_OUT",
        str(Path(__file__).resolve().parents[1] / "artifacts" / "coscientist"),
    )
)


def sh(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def score_recipe(prompt: str, keywords: list[str], bpm: int, band=(110, 128)) -> dict:
    low = prompt.lower()
    cover = sum(1 for k in keywords if k.lower() in low) / max(1, len(keywords))
    bpm_ok = 1.0 if band[0] <= bpm <= band[1] else 0.0
    len_ok = 1.0 if len(prompt) >= 80 else 0.5
    raw = 0.45 * cover + 0.25 * bpm_ok + 0.15 * len_ok + 0.15 * 1.0
    return {"score": 100.0 * raw, "axes": {"keyword-coverage": cover, "bpm-in-band": bpm_ok}}


def score_audio(path: Path) -> dict:
    if not path.exists():
        return {"score": 0.0, "bytes": 0}
    b = path.stat().st_size
    # rough: non-empty wav above 10KB counts as success
    size_ok = 1.0 if b > 10000 else 0.0
    return {"score": 100.0 * size_ok, "bytes": b}


def combined(recipe: dict, audio: dict) -> float:
    if audio.get("bytes", 0) > 0:
        return 0.55 * recipe["score"] + 0.45 * audio["score"]
    return recipe["score"]


def generate_candidates(genre: str, n: int, seconds: int, model: str) -> list[dict]:
    g = GENRES[genre]
    out = []
    for i, extra in enumerate(g["extras"][:n]):
        prompt = g["template"].format(bpm=g["bpm"], extra=extra)
        out.append(
            {
                "id": f"{genre}-g0-{i}",
                "genre": genre,
                "bpm": g["bpm"],
                "extra": extra,
                "prompt": prompt,
                "model": model,
                "seconds": seconds,
                "seed": 1000 + i * 17,
                "keywords": g["keywords"],
            }
        )
    return out


def materialize(c: dict) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{c['id']}.wav"
    remote = f"/tmp/ongakuka-{c['id']}.wav"
    # quote prompt for remote shell
    prompt = c["prompt"].replace("'", "'\"'\"'")
    remote_cmd = (
        f"{SSH_CMD} --model {c['model']} --modality music "
        f"--prompt '{prompt}' --seconds {c['seconds']} --seed {c['seed']} --out {remote}"
    )
    print(f"[materialize] {c['id']} via ssh {SSH_HOST}", flush=True)
    r = sh(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", SSH_HOST, remote_cmd], timeout=900)
    print(f"  exit={r.returncode}", flush=True)
    if r.stderr:
        print("  stderr:", r.stderr[-400:], flush=True)
    if r.returncode != 0:
        c["artifact"] = None
        c["audio"] = score_audio(dest)
        c["recipe"] = score_recipe(c["prompt"], c["keywords"], c["bpm"])
        c["fitness"] = combined(c["recipe"], c["audio"])
        return c
    scp = sh(["scp", "-o", "BatchMode=yes", f"{SSH_HOST}:{remote}", str(dest)], timeout=120)
    if scp.returncode != 0:
        print("  scp failed", scp.stderr, flush=True)
        c["artifact"] = None
    else:
        c["artifact"] = str(dest)
        print(f"  wrote {dest} ({dest.stat().st_size} bytes)", flush=True)
    c["audio"] = score_audio(dest)
    c["recipe"] = score_recipe(c["prompt"], c["keywords"], c["bpm"])
    c["fitness"] = combined(c["recipe"], c["audio"])
    return c


def rank(cands: list[dict]) -> list[dict]:
    return sorted(cands, key=lambda c: -c.get("fitness", 0.0))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--genre", default="freetempo-club", choices=list(GENRES))
    ap.add_argument("--candidates", type=int, default=2)
    ap.add_argument("--seconds", type=int, default=5)
    ap.add_argument("--model", default="musicgen-small")
    args = ap.parse_args()

    print(
        f"[ongakuka cosci py] genre={args.genre} cands={args.candidates} "
        f"seconds={args.seconds} ssh={SSH_HOST}",
        flush=True,
    )
    raw = generate_candidates(args.genre, args.candidates, args.seconds, args.model)
    done = [materialize(c) for c in raw]
    ranked = rank(done)
    best = ranked[0]
    summary = {
        "run/at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run/genre": args.genre,
        "run/model": args.model,
        "run/backend": "fleet-direct-musicgen-gad",
        "run/trajectory": [
            {
                "generation": 0,
                "best-id": best["id"],
                "best-score": best["fitness"],
            }
        ],
        "run/ranked": [
            {
                "id": c["id"],
                "fitness": c["fitness"],
                "recipe": c.get("recipe"),
                "audio": c.get("audio"),
                "artifact": c.get("artifact"),
                "prompt": c["prompt"],
            }
            for c in ranked
        ],
        "run/best": {
            "id": best["id"],
            "genre": best["genre"],
            "bpm": best["bpm"],
            "prompt": best["prompt"],
            "fitness": best["fitness"],
            "artifact": best.get("artifact"),
        },
    }
    ledger = OUT / f"iteration-{args.genre}-{int(time.time())}.json"
    ledger.write_text(json.dumps(summary, indent=2))
    print("\n=== RANKED ===", flush=True)
    for c in ranked:
        print(f"  {c['id']}: fitness={c['fitness']:.1f} artifact={c.get('artifact')}", flush=True)
    print(f"\n=== BEST {best['id']} score={best['fitness']:.1f} ===", flush=True)
    print("  prompt:", best["prompt"], flush=True)
    print("  artifact:", best.get("artifact"), flush=True)
    print("  ledger:", ledger, flush=True)
    return 0 if best.get("artifact") else 1


if __name__ == "__main__":
    raise SystemExit(main())
