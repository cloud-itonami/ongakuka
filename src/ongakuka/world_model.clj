(ns ongakuka.world-model
  "Loads and executes the OASIS XMILE model used by the composer actor."
  (:require [clojure.java.io :as io]
            [clojure.set :as set]
            [clojure.string :as str]
            [xmile.execute :as execute]
            [xmile.validate :as validate]
            [xmile.xml :as xml]))

(def default-resource "models/cinematic-game-composer.xmile")

(def required-stocks
  #{"Theme_Coherence" "Orchestral_Narrative" "Melodic_Memorability"
    "Harmonic_Tension" "Loop_Durability"})

(def required-flows
  #{"Theme_Development" "Motif_Fatigue" "Orchestral_Build" "Density_Cost"
    "Melody_Clarification" "Melody_Saturation" "Tension_Build" "Resolution"
    "Loop_Learning" "Loop_Wear"})

(defn- eqn-number [variable]
  (try (Double/parseDouble (:xmile/eqn variable))
       (catch Exception _ nil)))

(defn- by-kind [variables kind]
  (into {} (filter (fn [[_ v]] (= kind (:xmile/kind v)))) variables))

(defn load-model
  ([] (load-model default-resource))
  ([resource-name]
   (let [resource (or (io/resource resource-name)
                      (throw (ex-info "XMILE resource not found"
                                      {:resource resource-name})))
         document (xml/parse-string (slurp resource))
         raw-model (first (:xmile/models document))
         runtime-model (assoc raw-model :xmile/sim-specs (:xmile/sim-specs document))
         variables (:xmile/variables raw-model)
         stocks (by-kind variables :stock)
         flows (by-kind variables :flow)
         auxes (by-kind variables :aux)]
     {:xmile/document document
      :xmile/version "1.0"
      :xmile/name (get-in document [:xmile/header :xmile/name])
      :xmile/model-name (:xmile/name raw-model)
      :xmile/sim {:start (get-in document [:xmile/sim-specs :xmile/start])
                  :stop (get-in document [:xmile/sim-specs :xmile/stop])
                  :dt (get-in document [:xmile/sim-specs :xmile/dt])
                  :method (get-in document [:xmile/sim-specs :xmile/method])}
      :xmile/stocks (into {} (map (fn [[n v]] [n (eqn-number v)]) stocks))
      :xmile/flows (set (keys flows))
      :xmile/parameters (into {} (keep (fn [[n v]]
                                         (when-let [x (eqn-number v)] [n x]))) auxes)
      :xmile/runtime-model runtime-model})))

(defn problems [model]
  (let [stocks (set (keys (:xmile/stocks model)))
        flows (:xmile/flows model)
        standard (validate/validate-doc (:xmile/document model))]
    (cond-> (vec standard)
      (seq (set/difference required-stocks stocks))
      (conj {:problem/type :ongakuka/missing-stocks
             :problem/names (set/difference required-stocks stocks)})
      (seq (set/difference required-flows flows))
      (conj {:problem/type :ongakuka/missing-flows
             :problem/names (set/difference required-flows flows)})
      (not= 1.0 (get-in model [:xmile/parameters "originality_guard"]))
      (conj {:problem/type :ongakuka/originality-guard-disabled}))))

(defn valid? [model] (empty? (problems model)))

(defn- clamp [x] (max 0.0 (min 1.0 x)))

(def signal-keys [:story-pressure :intimacy :wonder :darkness :loop-need])

(defn normalize-signals [brief]
  (into {} (for [k signal-keys] [k (clamp (double (get brief k 0.5)))])))

(defn- signal-variable-name [k] (str/replace (name k) "-" "_"))

(defn- inject-signals [runtime-model signals]
  (reduce-kv (fn [model k value]
               (assoc-in model [:xmile/variables (signal-variable-name k) :xmile/eqn]
                         (str value)))
             runtime-model signals))

(defn simulate
  "Runs the parsed XMILE model through kotoba-lang/org-oasis-open-xmile."
  [model brief]
  (let [issues (problems model)]
    (when (seq issues)
      (throw (ex-info "Invalid composer XMILE model" {:problems issues})))
    (let [signals (normalize-signals brief)
          runtime (inject-signals (:xmile/runtime-model model) signals)
          result (execute/run runtime)
          times (:xmile/times result)
          series (:xmile/series result)]
      (mapv (fn [i time]
              {:time time
               :stocks (into {} (map (fn [stock]
                                       [stock (get-in series [stock i])])
                                     required-stocks))})
            (range (count times)) times))))
