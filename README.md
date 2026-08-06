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

## sakkyokuka との境界

ISCO-08 2652 は Musicians, Singers **and Composers** を1職業として束ねている
ので、この職能には **-ka（商売層）が2つ**ぶら下がる。職能は分けない —
`isco-2651`（painters / sculptors / cartoonists）に対して `mangaka` だけが
立っているのと同じ形（ADR-2608081000）。

**分かれ目は音源の出所ではなく商売の単位。** 上の path B が示すとおり
ongakuka も音を作る —— 違うのは、作った音を**自分のカタログに積む**のか、
**依頼主に権利ごと渡す**のか。

| | **ongakuka**（この repo） | [`sakkyokuka`](https://github.com/cloud-itonami/sakkyokuka) |
|---|---|---|
| 単位 | カタログの1曲を選んで使わせる | 依頼1件を受けて作り、権利を定めて渡す |
| 音源 | 既製の調達（path A）+ 自前生成（path B） | 受注ごとに作る |
| 権利 | 資産ごとに違う（調達物は使用許諾のみ、自前生成は原盤を保有） | 作品ごとの保有権利を台帳に持ち、譲渡を検査する |
| 収益 | 使用許諾 / render 同梱 | 受注 + 二次利用 |
| 台帳 | `resources/catalog.edn` | `resources/works.edn` |
| craft | `ongaku.compose` / `.policy` / `.coscientist`（**使い方**を下流で gate） | `ongaku.rights` / `.work` / `.commission`（**渡し方**を上流で gate） |

**path A のカタログ資産について studio が持つのは使用許諾だけで、原盤権では
ない。** だから、その音源を素材にした作品で `:master` を独占譲渡しようと
すると `ongaku.rights` が `:not-held` で拒否し、isco-2652 の governor は
それを（承認待ちではなく）hold に倒す —— 持っていない権利は人間が署名しても
自分のものにならないため。path B で自前生成した音源なら原盤を保有するので
同じ譲渡が通る。**保有権利は repo 単位ではなく資産・作品単位の事実**なので、
台帳がそれを持つ。

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
