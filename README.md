# ai-gftd-ongakuka

gftd の private 音楽家 / 職能 repo（ISCO-08 `2652`）。

## 2 paths

### A. BGM catalog selection（既存）

選定ロジック・ポリシー gate は公開 craft lib
[`kotoba-lang/ongaku`](https://github.com/kotoba-lang/ongaku)
（ADR-2607023000）。この repo が持つのは事業データ:

- `resources/catalog.edn` — DOVA-SYNDROME / Incompetech 台帳
- `docs/` — カタログ運用 + B2 annex runbook

```clojure
(require '[ongaku.compose :as compose])
(compose/compose {:channel-id "cyber" :mood :calm-tech :duration/sec 120})
```

### B. AI generation coscientist（2026-07-17）

日本ゲーム音楽 / J-pop / FreeTEMPO 級 club 向けの
**Generate → Reflect → materialize → Fitness → Elo Rank → Evolve → Meta**
loop。

| 層 | 場所 |
|---|---|
| pure loop / genre / audit / murakumo contract | `kotoba-lang/ongaku` (`ongaku.coscientist` 等) |
| fleet runner (Python) | `scripts/run_coscientist_fleet.py` |
| fleet runner (Clojure) | `scripts/coscientist_murakumo.clj` |
| worker (`audio-gen`) | `scripts/audio_gen.py` → **gad** `/home/gad/bin/audio-gen` |
| murakumo music models | `cloud-murakumo` `:music` default + **quality-authority = `musicgen-small`** |
| ACE-Step | installed on gad (`audio-gen-ace`) but **experimental-non-adopted** (ear quality below MusicGen; ADR-2607171900 addendum 2026-07-18) |

```bash
# Fleet-direct MusicGen on gad (quality-canonical path)
ONGAKUKA_AUDIO_GEN_SSH=gad \
  python3 scripts/run_coscientist_fleet.py \
  --genre freetempo-club --candidates 2 --seconds 24

# genres: freetempo-club | game-jp | jpop
# Do not use ace-step as default for product quality (full-song length only).
```

Public enqueue (queue visibility; workers may not claim yet):

```bash
MURAKUMO_TOKEN_SECRET=$(kagi get MURAKUMO_GENERATION_TOKEN_SECRET) \
  clojure -M:token issue ongakuka-cosci generation 7200   # in cloud-murakumo
# POST https://generation.murakumo.cloud/api/v1/generation
#   {"type":"sound","model":"musicgen-small",...}
```

Artifacts land under `artifacts/coscientist/` (gitignored).

## Test

```bash
# craft lib (includes coscientist offline tests)
cd ../../kotoba-lang/ongaku && clojure -M:test
# catalog repo
clojure -M:dev:test
```

## 由来

superproject 直下 plain tree `orgs/gftdcojp/ongakuka` から child repo 化
（ADR-2607023000）。汎用ロジックは kotoba-lang/ongaku、カタログ + runners はここ。
