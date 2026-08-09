(ns ongakuka.world-composer-test
  (:require [clojure.test :refer [deftest is testing]]
            [clojure.string :as str]
            [ongakuka.actor :as actor]
            [ongakuka.world-model :as world]))

(def brief
  {:title "星環の帰路" :duration-sec 96 :seed 2652
   :story-pressure 0.72 :intimacy 0.66 :wonder 0.78 :darkness 0.32
   :loop-need 0.74})

(deftest xmile-model-is-structurally-valid
  (let [model (world/load-model)]
    (is (world/valid? model) (pr-str (world/problems model)))
    (is (= "1.0" (:xmile/version model)))
    (is (= world/required-stocks (set (keys (:xmile/stocks model)))))
    (is (= :euler (get-in model [:xmile/sim :method])))
    (is (= 1.0 (get-in model [:xmile/parameters "originality_guard"])))
    (is (= 1.0 (+ (get-in model [:xmile/parameters "cinematic_principle_weight"])
                  (get-in model [:xmile/parameters "game_melodic_principle_weight"]))))))

(deftest simulation-is-bounded-and-brief-responsive
  (let [model (world/load-model)
        quiet (world/simulate model (assoc brief :story-pressure 0.05))
        urgent (world/simulate model (assoc brief :story-pressure 0.95))
        urgent-final (:stocks (peek urgent))]
    (is (= 25 (count urgent)))
    (is (every? #(<= 0.0 % 1.0) (vals urgent-final)))
    (is (> (get-in (peek urgent) [:stocks "Orchestral_Narrative"])
           (get-in (peek quiet) [:stocks "Orchestral_Narrative"])))))

(deftest actor-produces-deterministic-original-blueprint
  (let [a (actor/compose brief)
        b (actor/compose brief)
        prompt (get-in a [:render/request :prompt])]
    (is (= a b))
    (is (= actor/actor-id (:actor/id a)))
    (is (= {:model "musicgen-small"
            :duration_ms 96000
            :seed 2652}
           (select-keys (:render/request a) [:model :duration_ms :seed])))
    (is (nil? (get-in a [:render/request :duration-sec]))
        "the host contract has one duration unit: integer milliseconds")
    (is (seq (:score/events a)))
    (is (every? #(< (:at-sec %) (:duration-sec brief)) (:score/events a)))
    (is (= 8 (count (get-in a [:composition/decision :motif-intervals]))))
    (is (true? (get-in a [:audit :original?])))
    (is (empty? (get-in a [:audit :source-melodies])))
    (is (not (re-find #"(?i)williams|uematsu|ウィリアムズ|植松" prompt)))
    (is (str/includes? prompt "original cinematic game cue"))))

(deftest invalid-brief-fails-closed
  (testing "short duration"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"Invalid composition brief"
                          (actor/compose (assoc brief :duration-sec 4)))))
  (testing "duration must be numeric"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"Invalid composition brief"
                          (actor/compose (assoc brief :duration-sec "96")))))
  (testing "seed must be reproducible"
    (is (thrown-with-msg? clojure.lang.ExceptionInfo #"Invalid composition brief"
                          (actor/compose (dissoc brief :seed))))))

(deftest fractional-seconds-have-an-exact-millisecond-contract
  (is (= 20500
         (get-in (actor/compose (assoc brief :duration-sec 20.5))
                 [:render/request :duration_ms]))))
