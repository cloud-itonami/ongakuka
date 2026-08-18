;; Generate `src/ongakuka/embedded.cljc` from
;; `resources/models/cinematic-game-composer.xmile`.
;;
;;   clojure -M tools/gen_embedded.clj           # write
;;   clojure -M tools/gen_embedded.clj --check   # exit 1 if stale, 2 if it cannot tell
;;
;; ## Why embed, and why the PARSED tree rather than the XML text
;;
;; There is no portable `io/resource`, and the obvious `:cljs` substitute —
;; reading `resources/<path>` relative to the process's working directory — is
;; right only while this library is the ROOT project. Measured in this
;; workspace on 2026-08-18: a library converted on exactly that pattern
;; produced 159 errors in a DIFFERENT library's suite, every one of them the
;; data coming back nil because nbb's working directory was the other repo's
;; root.
;;
;; Embedding the XML TEXT would not have been enough either.
;; `xmile.xml/parse-xml-string` has a `:cljs` branch, but that branch calls
;; `js/DOMParser`, which is a BROWSER API and does not exist under nbb or
;; node — measured, `(exists? js/DOMParser)` is false. So under nbb the XML
;; could be carried but never parsed: a reader conditional whose `:cljs`
;; branch nothing in this runtime can evaluate, which is the appearance of
;; portability rather than portability.
;;
;; So the PARSED document tree is embedded. `xmile.execute`, `xmile.validate`,
;; `xmile.expr` and `xmile.model` are all cljs-clean (pure `Math`), so once
;; the parse is gone the whole simulation runs anywhere. The `.xmile` file
;; stays the thing a human edits.
;;
;; ## Why this generator is `.clj` and not nbb
;;
;; Every other generator in this sweep is `nbb tools/gen-embedded.cljs`, per
;; the workspace's script-host rule. This one cannot be: producing the parsed
;; tree requires an XML parser, and the only one available here is the JVM's.
;; Writing it in nbb would mean adding an npm DOM shim to a repo that has no
;; `package.json` in order to generate a file whose whole purpose is to make
;; the runtime not need a parser. The exception is deliberate and confined to
;; build time; nothing at runtime touches it.
(require '[clojure.java.io :as io]
         '[clojure.string :as str]
         '[xmile.xml :as xml])

(def xmile-path "resources/models/cinematic-game-composer.xmile")
(def out-path "src/ongakuka/embedded.cljc")

(defn- render [doc]
  (str ";; GENERATED — do not edit. Source: " xmile-path "\n"
       ";; Regenerate: clojure -M tools/gen_embedded.clj   Check: --check\n"
       ";;\n"
       ";; The PARSED XMILE document, not the XML text: `xmile.xml`'s `:cljs`\n"
       ";; parser needs `js/DOMParser`, which does not exist under nbb. This is\n"
       ";; a projection of the `.xmile` file, not a second source of truth — if\n"
       ";; you edit it by hand `--check` fails, which is the whole point.\n"
       "(ns ongakuka.embedded)\n\n"
       "(def document\n"
       "  " (pr-str doc) ")\n"))

(let [args (vec *command-line-args*)
      check? (some #{"--check"} args)
      f (io/file xmile-path)]
  (if-not (.exists f)
    (do (println "SCANNED\t0")
        (println "Refusing to answer: no" xmile-path "— run this from the repo root")
        (System/exit 2))
    (let [want (render (xml/parse-string (slurp f)))
          have (when (.exists (io/file out-path)) (slurp out-path))]
      (println "SCANNED\t1")
      (cond
        (not check?) (do (io/make-parents out-path)
                         (spit out-path want)
                         (println "wrote" out-path (count want) "bytes"))
        (= want have) (println "OK" out-path "matches" xmile-path)
        :else (do (println "STALE" out-path "does not match" xmile-path
                           "— run: clojure -M tools/gen_embedded.clj")
                  (System/exit 1))))))
