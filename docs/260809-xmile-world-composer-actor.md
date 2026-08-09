# XMILE world-composer actor

## Goal

`ongakuka` が映像・ゲーム用のオリジナル cue を作るとき、brief からいきなり
生成モデルの prompt を書かず、作曲上の状態を XMILE stock-flow model で先に
時間発展させる。状態、判断、score event、render request を同じ audit record に
残し、同一 seed から同一 blueprint を再生成できるようにする。

## Influence boundary

ジョン・ウィリアムズと植松伸夫は、人物の再現対象ではなく作曲伝統の provenance
label である。モデル化するのは次の抽象原理だけで、作品の旋律、録音、譜面、
embedding は保持しない。

| 原理群 | model への写像 |
|---|---|
| leitmotif と管弦楽的 narrative | `Theme_Coherence`, `Orchestral_Narrative`, `Harmonic_Tension` |
| 短い旋律 identity と反復耐性 | `Melodic_Memorability`, `Loop_Durability` |

2つの principle weight は合計 1.0。これは人物の「類似度」ではなく、stock の
成長率へ入る説明可能な設計係数である。render prompt は抽象的な音楽要件だけを
含み、人物名や「〜風」を含めない。

## Boundary

```text
brief
  -> XMILE parse + validate
  -> brief signals を aux に注入
  -> OASIS XMILE Euler simulation
  -> deterministic decision (tempo/meter/mode/motif/instruments)
  -> score events + MusicGen render request + audit
```

- XMILE parser / validator / executor:
  `kotoba-lang/org-oasis-open-xmile`
- world model authority:
  `resources/models/cinematic-game-composer.xmile`
- domain adapter:
  `ongakuka.world-model`
- actor:
  `ongakuka.actor`
- audio/network I/O:
  actor の外。既存 fleet runner / MusicGen host が所有する

この actor が生成するのは音声そのものではなく、音声を作れる cue blueprint と
render request である。したがって offline test は作曲判断と event を検証できるが、
聴感品質や fleet 上の WAV 生成成功を主張しない。

## Verification gates

1. 公式 OASIS XMILE 1.0 XSD に通ること。
2. `org-oasis-open-xmile` の parser と structural validator に通ること。
3. 全 stock が simulation 全 step で 0..1 に収まること。
4. brief の story pressure を上げると orchestral narrative が増えること。
5. 同じ brief + seed の結果が等しいこと。
6. event が曲尺を越えず、render prompt に人物名が含まれないこと。
7. source melody と style embedding の audit list が空であること。

## sound request contract 実測（2026-08-09）

内蔵 96 秒 brief を `clojure -M:world-compose` で実行し、host 境界に
`{:model "musicgen-small" :duration_ms 96000 :seed 2652}` が出ることを確認した。
同一入力2回の actor 全出力一致、8 tests / 32 assertions、lint 0 errors / 0
warnings。ここで測ったのは request の決定性と単位であり、host-owned rendererを
呼んでいないため音声生成時間や音質の実測ではない。

## Known limits

- 係数は測定値ではなく明示された作曲 heuristic であり、本人の心理・創作過程を
  推定したものではない。
- 生成された motif に対する外部楽曲 corpus との類似検索はまだ行わない。
- score events は単旋律の MIDI 相当 blueprint。和声 voicing、counterpoint、DAW
  session、実演表現は renderer/arranger の責務である。
- 実音声の品質評価は既存 coscientist の audio materialize + fitness gate が担う。
