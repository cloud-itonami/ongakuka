#!/usr/bin/env nbb
;; The portable suite on nbb — no build step, no JVM.
;;
;;   nbb --classpath src:test:<xmile>/src test/run_portable.cljs
;;
;; The classpath needs `kotoba-lang/org-oasis-open-xmile`'s `src`, because
;; nbb does not resolve `deps.edn` git deps. `tools/portable-classpath.cljs`
;; prints a working one.
;;
;; ## Why only `ongakuka.world-composer-test`
;;
;; `ongakuka.catalog-test` is ALREADY `.cljc` and still cannot run here, which
;; is the sharpest illustration of why this runner exists: the file extension
;; is not the portability. It calls `ongaku.catalog/load-catalog`, whose
;; `:cljs` branch is `(throw (ex-info "load-catalog needs host-provided EDN on
;; cljs" …))` — a deliberate refusal in `kotoba-lang/ongaku`, not something
;; this repo can fix. Its `:cljs` branch has, as far as this runner can tell,
;; never been evaluated by anything.
;;
;; ## Run it from somewhere that is NOT this repo
;;
;; `ongakuka.world-model` and `ongakuka.actor` touch no file at runtime — the
;; XMILE document is compiled in, already parsed — so neither may care what
;; the process's working directory is. Running only from the repo root proves
;; the case that already worked, which is exactly the case a cwd-relative read
;; also passes.
;;
;; Every `deftest`-bearing portable namespace must be named BOTH in the
;; require and in `run-tests`: requiring registers the vars, only `run-tests`
;; runs them, and a runner naming a subset prints the same `Ran N tests`
;; shape as one naming all of them.
(require '[cljs.test :as t]
         '[ongakuka.world-composer-test])

(defmethod t/report [:cljs.test/default :end-run-tests] [m]
  (when-not (t/successful? m) (set! (.-exitCode js/process) 1)))

(t/run-tests 'ongakuka.world-composer-test)
