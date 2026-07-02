# ai-gftd-ongakuka

gftd の private BGM カタログ（音楽家 / 職能 repo）。選定ロジック・ポリシー
gate は公開 craft lib [`kotoba-lang/ongaku`](https://github.com/kotoba-lang/ongaku)
に分離済みで（ADR-2607023000: コードは kotoba-lang、職能は
cloud-itonami-isco、商売は gftdcojp）、この repo が持つのは事業データだけ:

- `resources/catalog.edn` — asset 台帳（DOVA-SYNDROME / Incompetech 由来。
  render-only / no raw public access / no AI-training / no Content-ID の
  ポリシーフラグ付き、チャンネル roster 込み）
- `docs/` — カタログ運用ノートと B2 annex runbook

音源ファイルの実体はこの repo には置かない（`:asset/local-path` は
yukkuri-assets 側の path 参照。大容量実体は B2+DataLad 経路）。

## 使い方

```clojure
(require '[ongaku.compose :as compose])
;; resources/ が classpath にあるので catalog.edn は暗黙に解決される
(compose/compose {:channel-id "cyber" :mood :calm-tech :duration/sec 120})
```

職能: ISCO-08 `2652`
([cloud-itonami-isco-2652](https://github.com/cloud-itonami/cloud-itonami-isco-2652))。

## Test

```bash
clojure -M:test
```

## 由来

superproject 直下の plain tree `orgs/gftdcojp/ongakuka` から child repo 化
（ADR-2607023000 follow-up）。汎用ロジック（compose/policy/catalog reader)は
kotoba-lang/ongaku へ、カタログはここへ。
