#!/usr/bin/env nbb
;; Print an nbb classpath for `test/run_portable.cljs`.
;;
;;   nbb --classpath "$(nbb tools/portable-classpath.cljs)" test/run_portable.cljs
;;
;; nbb does not resolve `deps.edn` git deps, and this repo's portable half
;; needs three of them on the classpath as SOURCE (`org-oasis-open-xmile`,
;; and `dsl-core` which `xmile.validate` requires). So ask `clojure` for the
;; resolved paths and drop the jars, which nbb cannot read.
;;
;; This is a convenience, not a dependency: the classpath is just directories,
;; and anyone can assemble it by hand. It exists because the first attempt at
;; running the portable suite failed with `Could not find namespace:
;; kotoba.dsl.problem` — a transitive dep two levels down that no amount of
;; reading this repo would have revealed.
(require '["node:child_process" :as cp] '[clojure.string :as str])

(let [paths (-> (.toString (cp/execSync "clojure -Spath"))
                str/trim
                (str/split #":"))
      dirs (remove #(str/ends-with? % ".jar") paths)]
  (when (empty? dirs)
    (println "Refusing to answer: clojure -Spath returned no directories")
    (set! (.-exitCode js/process) 2))
  (println (str/join ":" (cons "test" dirs))))
