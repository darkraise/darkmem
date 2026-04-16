"""One-off emitter for shared-base batch-228 — knowledge domain (behavioral economics and decision science: Kahneman and Tversky on Prospect Theory and heuristics, Thaler and Sunstein on Nudge, hyperbolic discounting, loss aversion, endowment effect, sunk-cost fallacy, mental accounting, default effects, choice overload, Gigerenzer, ego depletion, replication crisis, Camerer, Ariely).

Writes 50 rows to data/v2/shared/batch_228.tmp.jsonl with ids shared-11351..11400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_228.tmp.jsonl"
ID_OFFSET = 11350

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Daniel Kahneman and Amos Tversky introduced Prospect Theory in their 1979 Econometrica paper, replacing expected utility theory as the descriptive model of choice under risk for the seminar syllabus.", "milestone", "knowledge", False,
     [("Daniel Kahneman", "person"), ("Amos Tversky", "person"), ("Prospect Theory", "theory"), ("Econometrica", "publication"), ("expected utility theory", "theory")],
     [("Prospect Theory", "Daniel Kahneman", "AUTHORED_BY"), ("Prospect Theory", "Amos Tversky", "AUTHORED_BY"), ("Prospect Theory", "expected utility theory", "REPLACES"), ("Prospect Theory", "Econometrica", "PUBLISHED_IN")],
     "which 1979 paper supplanted expected utility as the descriptive model of risky choice on the reading list",
     "prospect theory kahneman tversky 1979 econometrica expected utility replace"),
    # --- 2 ---
    ("Adopted Daniel Kahneman's Thinking, Fast and Slow as the opening textbook for the undergraduate behavioral economics course; the System 1 and System 2 framing anchors the first four weeks of lectures.", "decision", "knowledge", False,
     [("Daniel Kahneman", "person"), ("Thinking, Fast and Slow", "publication"), ("System 1", "concept"), ("System 2", "concept")],
     [("Thinking, Fast and Slow", "Daniel Kahneman", "AUTHORED_BY")],
     "which popular textbook opens the undergraduate course and which dual-process framing does it lean on",
     "kahneman thinking fast slow system 1 system 2 textbook course"),
    # --- 3 ---
    ("The loss aversion asymmetry is the core of Prospect Theory: losses loom roughly twice as large as equivalent gains, with the coefficient lambda estimated between 2.0 and 2.5 in the classic experiments.", "fact", "knowledge", False,
     [("loss aversion", "concept"), ("Prospect Theory", "theory"), ("lambda", "concept")],
     [("loss aversion", "Prospect Theory", "DEPENDS_ON")],
     "how does Prospect Theory quantify the asymmetry between losses and gains in the classic experiments",
     "loss aversion lambda prospect theory asymmetry gain experiment coefficient"),
    # --- 4 ---
    ("Chose to open the endowment effect lecture with Richard Thaler's Cornell mug experiment rather than the Knetsch pen study, since the roughly two-to-one seller-buyer price gap lands more cleanly with undergraduates.", "decision", "knowledge", False,
     [("endowment effect", "concept"), ("Richard Thaler", "person"), ("Cornell mug experiment", "finding")],
     [("Cornell mug experiment", "Richard Thaler", "AUTHORED_BY"), ("endowment effect", "Cornell mug experiment", "DEPENDS_ON")],
     "which Thaler study won the endowment-effect lecture opening slot over the Knetsch pen variant",
     "endowment effect thaler cornell mug experiment seller buyer lecture"),
    # --- 5 ---
    ("The framing effects literature shows that describing an outcome as ninety percent survival versus ten percent mortality flips choices even when logically equivalent; Amos Tversky and Daniel Kahneman used the Asian Disease study to nail this down.", "fact", "knowledge", False,
     [("framing effects", "concept"), ("Asian Disease study", "finding"), ("Amos Tversky", "person"), ("Daniel Kahneman", "person")],
     [("Asian Disease study", "Amos Tversky", "AUTHORED_BY"), ("Asian Disease study", "Daniel Kahneman", "AUTHORED_BY"), ("framing effects", "Asian Disease study", "DEPENDS_ON")],
     "which disease-framing experiment showed logically equivalent descriptions reversing stated preferences",
     "framing effect asian disease survival mortality equivalent choice tversky"),
    # --- 6 ---
    ("Picked the Amos Tversky and Daniel Kahneman wheel-of-fortune experiment as the anchoring demo for the online homework over the real-estate anchoring study; the randomised-spin setup runs cleanly in a browser without requiring property photos.", "decision", "knowledge", False,
     [("anchoring", "concept"), ("Amos Tversky", "person"), ("Daniel Kahneman", "person"), ("wheel-of-fortune experiment", "finding")],
     [("wheel-of-fortune experiment", "Amos Tversky", "AUTHORED_BY"), ("wheel-of-fortune experiment", "Daniel Kahneman", "AUTHORED_BY"), ("anchoring", "wheel-of-fortune experiment", "DEPENDS_ON")],
     "which anchoring demo won the online homework slot over the real-estate anchoring variant",
     "anchoring tversky wheel fortune online homework real estate pick"),
    # --- 7 ---
    ("Decided to split the availability heuristic from representativeness into separate lectures rather than the bundled treatment in earlier syllabi; the 1973 Amos Tversky and Daniel Kahneman recall-based variant deserves its own session given how often media-vividness examples derail discussion.", "decision", "knowledge", False,
     [("availability heuristic", "concept"), ("Amos Tversky", "person"), ("Daniel Kahneman", "person")],
     [("availability heuristic", "Amos Tversky", "AUTHORED_BY"), ("availability heuristic", "Daniel Kahneman", "AUTHORED_BY")],
     "which heuristic was split out of a bundled lecture to get its own session in the course",
     "availability heuristic tversky kahneman 1973 split lecture media vivid"),
    # --- 8 ---
    ("Prefer the Linda conjunction fallacy from Amos Tversky and Daniel Kahneman over the lawyer-engineer base-rate problem when introducing representativeness; Linda produces cleaner error rates in an intro audience even though both illustrate the same 1972 heuristic.", "preference", "knowledge", False,
     [("representativeness", "concept"), ("Amos Tversky", "person"), ("Daniel Kahneman", "person"), ("Linda conjunction fallacy", "finding")],
     [("representativeness", "Amos Tversky", "AUTHORED_BY"), ("representativeness", "Daniel Kahneman", "AUTHORED_BY"), ("Linda conjunction fallacy", "representativeness", "DEPENDS_ON")],
     "which representativeness illustration beats the lawyer-engineer problem in intro-audience error clarity",
     "representativeness linda conjunction bank teller feminist prefer lawyer"),
    # --- 9 ---
    ("Richard Thaler and Cass Sunstein published Nudge in 2008, formalising libertarian paternalism as a design philosophy in which choice architecture steers decisions without restricting options.", "milestone", "knowledge", False,
     [("Richard Thaler", "person"), ("Cass Sunstein", "person"), ("Nudge", "publication"), ("libertarian paternalism", "theory"), ("choice architecture", "concept")],
     [("Nudge", "Richard Thaler", "AUTHORED_BY"), ("Nudge", "Cass Sunstein", "AUTHORED_BY"), ("Nudge", "libertarian paternalism", "APPLIES_TO")],
     "which 2008 book paired Thaler with Sunstein to formalise libertarian paternalism through choice architecture",
     "nudge thaler sunstein 2008 libertarian paternalism choice architecture"),
    # --- 10. noise ---
    ("The departmental espresso machine ran out of descaler again and a passive-aggressive note appeared on the milk fridge by mid-afternoon.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Save More Tomorrow, designed by Richard Thaler and Shlomo Benartzi, commits employees to raise 401(k) contributions with future pay rises, exploiting default effects and hyperbolic discounting together.", "architecture", "knowledge", False,
     [("Save More Tomorrow", "method"), ("Richard Thaler", "person"), ("Shlomo Benartzi", "person"), ("default effects", "concept"), ("hyperbolic discounting", "concept")],
     [("Save More Tomorrow", "Richard Thaler", "AUTHORED_BY"), ("Save More Tomorrow", "Shlomo Benartzi", "AUTHORED_BY"), ("Save More Tomorrow", "default effects", "USES"), ("Save More Tomorrow", "hyperbolic discounting", "APPLIES_TO")],
     "which retirement plan by Thaler and Benartzi couples future-dated raises with default enrollment to lift savings",
     "save more tomorrow thaler benartzi 401k default hyperbolic discounting"),
    # --- 12 ---
    ("Settled on George Ainslie's 1970s hyperbolic discounting account as the baseline intertemporal model for the course, since its preference reversals predictions match the pigeon and human choice data far better than the textbook exponential.", "decision", "knowledge", False,
     [("hyperbolic discounting", "concept"), ("George Ainslie", "person"), ("preference reversals", "concept")],
     [("hyperbolic discounting", "George Ainslie", "AUTHORED_BY"), ("hyperbolic discounting", "preference reversals", "CAUSES")],
     "which intertemporal-choice baseline did the course settle on in place of textbook exponential discounting",
     "hyperbolic discounting ainslie preference reversal baseline course exponential"),
    # --- 13 ---
    ("David Laibson's beta-delta model formalises quasi-hyperbolic discounting with a present-bias parameter beta alongside an exponential delta, giving a tractable alternative to the full hyperbolic discounting curves from the Ainslie tradition.", "architecture", "knowledge", False,
     [("David Laibson", "person"), ("beta-delta model", "theory"), ("quasi-hyperbolic discounting", "concept"), ("hyperbolic discounting", "concept")],
     [("beta-delta model", "David Laibson", "AUTHORED_BY"), ("beta-delta model", "quasi-hyperbolic discounting", "IMPLEMENTS"), ("beta-delta model", "hyperbolic discounting", "IMPROVES_ON")],
     "which two-parameter discounting model did Laibson propose as a tractable stand-in for pure hyperbolic curves",
     "laibson beta delta quasi hyperbolic discount present bias tractable"),
    # --- 14 ---
    ("Hal Arkes and Catherine Blumer's 1985 Organizational Behavior and Human Decision Processes paper is the standing reference for the sunk-cost fallacy on the course's secondary reading list.", "reference", "knowledge", False,
     [("sunk-cost fallacy", "concept"), ("Hal Arkes", "person"), ("Catherine Blumer", "person")],
     [("sunk-cost fallacy", "Hal Arkes", "AUTHORED_BY"), ("sunk-cost fallacy", "Catherine Blumer", "AUTHORED_BY")],
     "which Arkes and Blumer article from the mid 1980s anchors secondary reading for commitment biases",
     "arkes blumer 1985 organizational behavior human decision process anchor"),
    # --- 15 ---
    ("The mental accounting framework, developed by Richard Thaler, treats money as non-fungible across psychological buckets; the framework predicts why households hold high-interest credit debt while keeping low-yield savings.", "architecture", "knowledge", False,
     [("mental accounting", "theory"), ("Richard Thaler", "person")],
     [("mental accounting", "Richard Thaler", "AUTHORED_BY")],
     "which Thaler framework explains why families hold credit-card balances alongside low-yield savings",
     "mental accounting thaler non fungible bucket credit debt saving"),
    # --- 16 ---
    ("The status quo bias pipeline in the lab wraps William Samuelson and Richard Zeckhauser's 1988 portfolio-allocation paradigm as a reusable module; new experiments inherit the opt-in and opt-out arm through a shared config.", "architecture", "knowledge", False,
     [("status quo bias", "concept"), ("William Samuelson", "person"), ("Richard Zeckhauser", "person")],
     [("status quo bias", "William Samuelson", "AUTHORED_BY"), ("status quo bias", "Richard Zeckhauser", "AUTHORED_BY")],
     "how does the lab standardise status-quo-bias experiments on the 1988 Samuelson and Zeckhauser paradigm",
     "status quo bias samuelson zeckhauser 1988 pipeline opt in module"),
    # --- 17 ---
    ("Prefer Eric Johnson and Daniel Goldstein's 2003 organ-donation study as the canonical default effects illustration over the 401(k) enrollment papers; the cross-country gap between presumed-consent and opt-in countries is harder to attribute to confounds.", "preference", "knowledge", False,
     [("default effects", "concept"), ("Eric Johnson", "person"), ("Daniel Goldstein", "person"), ("organ-donation study", "finding")],
     [("organ-donation study", "Eric Johnson", "AUTHORED_BY"), ("organ-donation study", "Daniel Goldstein", "AUTHORED_BY"), ("default effects", "organ-donation study", "DEPENDS_ON")],
     "which 2003 study does the course prefer for default effects over the 401(k) enrollment literature",
     "default effect johnson goldstein 2003 organ donation prefer 401k"),
    # --- 18 ---
    ("The choice overload effect was documented in Sheena Iyengar and Mark Lepper's 2000 jam study, where a 24-variety display drew more browsers but a 6-variety display produced roughly ten times the purchase rate.", "fact", "knowledge", False,
     [("choice overload", "concept"), ("Sheena Iyengar", "person"), ("Mark Lepper", "person"), ("jam study", "finding")],
     [("jam study", "Sheena Iyengar", "AUTHORED_BY"), ("jam study", "Mark Lepper", "AUTHORED_BY"), ("choice overload", "jam study", "DEPENDS_ON")],
     "which 2000 supermarket jam experiment established choice overload as a testable decision phenomenon",
     "choice overload iyengar lepper 2000 jam study 24 variety purchase"),
    # --- 19 ---
    ("Adopted Sheena Iyengar's The Art of Choosing as the week-six supplementary reading; the chapter on arranged marriages gives students a counterpoint to the culturally narrow Western autonomy framing in earlier lectures.", "reference", "knowledge", False,
     [("Sheena Iyengar", "person"), ("The Art of Choosing", "publication")],
     [("The Art of Choosing", "Sheena Iyengar", "AUTHORED_BY")],
     "which Iyengar book supplements week six and offers a cross-cultural counterpoint to Western autonomy framing",
     "art of choosing iyengar supplementary reading arranged marriage autonomy"),
    # --- 20 ---
    ("The Behavioural Insights Team, known as BIT and nicknamed the Nudge Unit, was founded in 2010 within the UK Cabinet Office with Richard Thaler as academic advisor and later spun out as a social-purpose company.", "milestone", "knowledge", False,
     [("Behavioural Insights Team", "organization"), ("BIT", "organization"), ("UK Cabinet Office", "organization"), ("Richard Thaler", "person")],
     [("Behavioural Insights Team", "UK Cabinet Office", "LOCATED_IN"), ("Behavioural Insights Team", "Richard Thaler", "KNOWS")],
     "which 2010 UK unit operationalised nudge research inside government with Thaler as academic advisor",
     "behavioural insights team bit nudge unit cabinet office thaler 2010"),
    # --- 21 ---
    ("BIT's EAST framework structures policy nudges along four dimensions: easy, attractive, social, timely; the guide is the default playbook across civil-service trials in the UK, Australia, and Singapore.", "architecture", "knowledge", False,
     [("BIT", "organization"), ("EAST framework", "method")],
     [("EAST framework", "BIT", "AUTHORED_BY")],
     "which four-dimension BIT playbook structures civil-service nudge trials across multiple governments",
     "east framework bit easy attractive social timely policy nudge civil"),
    # --- 22 ---
    ("Added Gerd Gigerenzer's fast-and-frugal heuristics track to the curriculum alongside Kahneman, with Simple Heuristics That Make Us Smart as the primary text and Take The Best as the worked running example.", "decision", "knowledge", False,
     [("Gerd Gigerenzer", "person"), ("fast-and-frugal heuristics", "theory"), ("Simple Heuristics That Make Us Smart", "publication"), ("Take The Best", "method")],
     [("Simple Heuristics That Make Us Smart", "Gerd Gigerenzer", "AUTHORED_BY"), ("fast-and-frugal heuristics", "Gerd Gigerenzer", "AUTHORED_BY"), ("Take The Best", "fast-and-frugal heuristics", "IS_A")],
     "which Gigerenzer track was added to the curriculum alongside Kahneman and with which primary text",
     "gigerenzer fast frugal heuristic take the best curriculum add track"),
    # --- 23 ---
    ("A persistent problem for the heuristics-and-biases program is Gerd Gigerenzer's 1996 Psychological Review critique: many framing effects shrink or vanish once single-event probabilities are restated as natural frequencies.", "problem", "knowledge", False,
     [("Gerd Gigerenzer", "person"), ("heuristics-and-biases program", "theory"), ("natural frequencies", "concept"), ("Psychological Review", "publication")],
     [("heuristics-and-biases program", "Gerd Gigerenzer", "CONTRADICTS"), ("natural frequencies", "heuristics-and-biases program", "CONTRADICTS")],
     "which 1996 Gigerenzer critique is the standing problem for the heuristics-and-biases program",
     "gigerenzer heuristics biases natural frequency psychological review 1996"),
    # --- 24 ---
    ("Prefer Gerd Gigerenzer's natural frequencies tree over Bayesian-probability notation for the undergraduate medical-testing worksheet; the tree form raises correct-answer rates from roughly fifteen percent to over seventy.", "preference", "knowledge", False,
     [("Gerd Gigerenzer", "person"), ("natural frequencies", "concept")],
     [("natural frequencies", "Gerd Gigerenzer", "AUTHORED_BY")],
     "which pedagogical representation beats Bayesian notation for the medical-testing worksheet in the course",
     "natural frequency tree gigerenzer medical testing bayesian undergraduate"),
    # --- 25 ---
    ("Roy Baumeister's ego depletion research, published in Journal of Personality and Social Psychology 1998, claimed willpower runs on a finite glucose-linked resource that depletes with successive self-control tasks.", "fact", "knowledge", False,
     [("Roy Baumeister", "person"), ("ego depletion", "theory"), ("Journal of Personality and Social Psychology", "publication")],
     [("ego depletion", "Roy Baumeister", "AUTHORED_BY"), ("ego depletion", "Journal of Personality and Social Psychology", "PUBLISHED_IN")],
     "which 1998 Baumeister paper framed willpower as a finite glucose-linked resource that depletes with use",
     "ego depletion baumeister 1998 willpower glucose self control finite"),
    # --- 26 ---
    ("The ego depletion effect failed a preregistered multi-lab replication coordinated by Martin Hagger in 2016 with over two thousand subjects, and the effect size collapsed to near zero against Roy Baumeister's reported d of 0.6.", "problem", "knowledge", False,
     [("ego depletion", "theory"), ("Martin Hagger", "person"), ("preregistered multi-lab replication", "finding"), ("Roy Baumeister", "person")],
     [("preregistered multi-lab replication", "Martin Hagger", "AUTHORED_BY"), ("preregistered multi-lab replication", "ego depletion", "CONTRADICTS")],
     "which 2016 multi-lab preregistered study failed to replicate ego depletion at Baumeister's reported effect size",
     "ego depletion hagger 2016 preregister replication effect size zero"),
    # --- 27 ---
    ("Adopted the Open Science Collaboration's 2015 Science paper as the reference replication benchmark for course discussions of the replication crisis; any later syllabus claim that cites it must match its 39-of-100 reproduction rate.", "decision", "knowledge", False,
     [("replication crisis", "concept"), ("Open Science Collaboration", "organization"), ("Science", "publication")],
     [("replication crisis", "Open Science Collaboration", "DEPENDS_ON"), ("Open Science Collaboration", "Science", "PUBLISHED_IN")],
     "which 2015 benchmark did the course adopt for classroom discussion of the replication crisis",
     "replication crisis open science collaboration 2015 science benchmark"),
    # --- 28 ---
    ("Brian Nosek founded the Center for Open Science in 2013 to push preregistration, registered reports, and open data as structural fixes for the replication crisis in social and behavioral research.", "milestone", "knowledge", False,
     [("Brian Nosek", "person"), ("Center for Open Science", "organization"), ("replication crisis", "concept"), ("preregistration", "method")],
     [("Center for Open Science", "Brian Nosek", "AUTHORED_BY"), ("Center for Open Science", "replication crisis", "FIXES"), ("Center for Open Science", "preregistration", "USES")],
     "which organisation did Nosek found in 2013 to push preregistration as a structural fix for replication",
     "nosek center open science 2013 preregistration registered report fix"),
    # --- 29 ---
    ("Require preregistration analysis plans for all new lab experiments that will enter the behavioral economics replication crisis follow-up database; the team switched after the 2018 many-labs results showed post-hoc flexibility dominated noise.", "preference", "knowledge", False,
     [("preregistration", "method"), ("many-labs", "finding"), ("replication crisis", "concept")],
     [("preregistration", "replication crisis", "FIXES"), ("many-labs", "preregistration", "SUPPORTS")],
     "which policy did the lab adopt for new experiments after the 2018 many-labs results on post-hoc flexibility",
     "preregistration many labs 2018 analysis plan replication post hoc"),
    # --- 30 ---
    ("Chose Colin Camerer's 2018 Social Sciences Replication Project over the Many Labs series as the example of targeted high-profile replication; covering Nature and Science findings specifically gives a sharper instructional narrative than broad-spectrum replication work at Caltech.", "decision", "knowledge", False,
     [("Colin Camerer", "person"), ("Caltech", "organization"), ("Social Sciences Replication Project", "finding"), ("Nature", "publication"), ("Science", "publication")],
     [("Social Sciences Replication Project", "Colin Camerer", "AUTHORED_BY"), ("Colin Camerer", "Caltech", "WORKS_AT"), ("Social Sciences Replication Project", "Nature", "APPLIES_TO"), ("Social Sciences Replication Project", "Science", "APPLIES_TO")],
     "which 2018 project did the course pick over Many Labs for illustrating targeted high-profile replication",
     "camerer caltech social sciences replication 2018 nature science choice"),
    # --- 31 ---
    ("Colin Camerer's Behavioral Game Theory, published by Princeton in 2003, is the standard graduate reference for experimental work on ultimatum games, coordination, and learning in strategic settings.", "reference", "knowledge", False,
     [("Colin Camerer", "person"), ("Behavioral Game Theory", "publication"), ("ultimatum games", "concept")],
     [("Behavioral Game Theory", "Colin Camerer", "AUTHORED_BY"), ("Behavioral Game Theory", "ultimatum games", "APPLIES_TO")],
     "which 2003 Princeton book serves as the graduate reference for experimental ultimatum and coordination work",
     "camerer behavioral game theory princeton 2003 ultimatum coordination"),
    # --- 32 ---
    ("Dan Ariely's Predictably Irrational, published in 2008, popularised the relative-pricing decoy effect through the Economist subscription experiment where a phantom print-only option shifted demand toward the combined bundle.", "milestone", "knowledge", False,
     [("Dan Ariely", "person"), ("Predictably Irrational", "publication"), ("decoy effect", "concept"), ("Economist subscription experiment", "finding")],
     [("Predictably Irrational", "Dan Ariely", "AUTHORED_BY"), ("Economist subscription experiment", "Dan Ariely", "AUTHORED_BY"), ("decoy effect", "Economist subscription experiment", "DEPENDS_ON")],
     "which 2008 Ariely book popularised the decoy effect through an Economist subscription experiment",
     "ariely predictably irrational 2008 decoy economist subscription phantom"),
    # --- 33 ---
    ("Some Dan Ariely experiments have faced post-publication scrutiny: a 2020 investigation of the 2012 insurance-honesty study with Francesca Gino raised data-fabrication concerns that remain unresolved.", "problem", "knowledge", False,
     [("Dan Ariely", "person"), ("Francesca Gino", "person"), ("insurance-honesty study", "finding")],
     [("insurance-honesty study", "Dan Ariely", "AUTHORED_BY"), ("insurance-honesty study", "Francesca Gino", "AUTHORED_BY")],
     "which 2012 Ariely-Gino study faced data-fabrication scrutiny during the 2020 re-examination",
     "ariely gino insurance honesty 2012 2020 fabrication investigation"),
    # --- 34 ---
    ("Amos Tversky and Daniel Kahneman's 1992 paper on cumulative prospect theory reshapes the probability weighting function with rank-dependent probabilities; this replaces the 1979 Prospect Theory weighting as the internal calculation engine and fixes the stochastic-dominance violation.", "architecture", "knowledge", False,
     [("Amos Tversky", "person"), ("Daniel Kahneman", "person"), ("cumulative prospect theory", "theory"), ("Prospect Theory", "theory"), ("rank-dependent probabilities", "concept")],
     [("cumulative prospect theory", "Amos Tversky", "AUTHORED_BY"), ("cumulative prospect theory", "Daniel Kahneman", "AUTHORED_BY"), ("cumulative prospect theory", "Prospect Theory", "IMPROVES_ON"), ("cumulative prospect theory", "rank-dependent probabilities", "USES")],
     "which 1992 revision fixed a stochastic-dominance violation in the original 1979 Prospect Theory formulation",
     "cumulative prospect theory tversky kahneman 1992 rank dependent dominance"),
    # --- 35 ---
    ("Matthew Rabin's calibration theorem is wired into the course's decision-model comparator as a closed-form check: plug in a small-stakes risk aversion and the 2000 Econometrica result outputs the implied large-stakes absurdity under expected utility theory, which pushes students toward loss aversion.", "architecture", "knowledge", False,
     [("Matthew Rabin", "person"), ("expected utility theory", "theory"), ("loss aversion", "concept"), ("Econometrica", "publication")],
     [("Matthew Rabin", "expected utility theory", "CONTRADICTS"), ("loss aversion", "Matthew Rabin", "SUPPORTS")],
     "how is the 2000 Rabin calibration theorem wired into the course's decision-model comparator",
     "rabin 2000 econometrica calibration theorem small large stake utility"),
    # --- 36 ---
    ("The hot-hand fallacy was famously debunked by Gilovich, Vallone, and Amos Tversky in 1985, though Joshua Miller and Adam Sanjurjo's 2018 reanalysis uncovered a selection-bias correction that partly rehabilitated the effect.", "fact", "knowledge", False,
     [("hot-hand fallacy", "concept"), ("Amos Tversky", "person"), ("Joshua Miller", "person"), ("Adam Sanjurjo", "person")],
     [("hot-hand fallacy", "Amos Tversky", "AUTHORED_BY"), ("hot-hand fallacy", "Joshua Miller", "CONTRADICTS"), ("hot-hand fallacy", "Adam Sanjurjo", "CONTRADICTS")],
     "which 2018 Miller and Sanjurjo reanalysis partly rehabilitated the effect that Tversky had dismissed in 1985",
     "hot hand fallacy gilovich vallone tversky 1985 miller sanjurjo 2018"),
    # --- 37 ---
    ("Ernst Fehr and Simon Gaechter's 2000 American Economic Review paper on altruistic punishment remains the go-to reference for the social-preferences lecture; the public-goods-with-punishment protocol is cited verbatim in the problem-set instructions.", "reference", "knowledge", False,
     [("Ernst Fehr", "person"), ("Simon Gaechter", "person"), ("altruistic punishment", "concept"), ("American Economic Review", "publication")],
     [("altruistic punishment", "Ernst Fehr", "AUTHORED_BY"), ("altruistic punishment", "Simon Gaechter", "AUTHORED_BY"), ("altruistic punishment", "American Economic Review", "PUBLISHED_IN")],
     "which 2000 Fehr and Gaechter paper is the go-to reference for the social-preferences lecture and problem set",
     "fehr gaechter altruistic punishment public goods 2000 reference aer"),
    # --- 38 ---
    ("The planning fallacy, formalised by Daniel Kahneman and Amos Tversky in 1979 and revisited by Roger Buehler in 1994, has people systematically underestimate task duration even when shown their own prior overruns.", "fact", "knowledge", False,
     [("planning fallacy", "concept"), ("Daniel Kahneman", "person"), ("Amos Tversky", "person"), ("Roger Buehler", "person")],
     [("planning fallacy", "Daniel Kahneman", "AUTHORED_BY"), ("planning fallacy", "Amos Tversky", "AUTHORED_BY"), ("planning fallacy", "Roger Buehler", "BUILDS_ON")],
     "which bias did Kahneman and Tversky name in 1979 and Buehler revisit with thesis-completion estimates in 1994",
     "planning fallacy kahneman tversky 1979 buehler 1994 duration estimate"),
    # --- 39 ---
    ("Chose to base the undergraduate reading list on Richard Thaler's Misbehaving rather than Michael Lewis's The Undoing Project; the former gives primary-source depth on decisions from an insider, the latter is secondary biography.", "decision", "knowledge", False,
     [("Richard Thaler", "person"), ("Misbehaving", "publication"), ("Michael Lewis", "person"), ("The Undoing Project", "publication")],
     [("Misbehaving", "Richard Thaler", "AUTHORED_BY"), ("The Undoing Project", "Michael Lewis", "AUTHORED_BY"), ("Misbehaving", "The Undoing Project", "PREFERS")],
     "which Thaler volume won the reading-list slot over Michael Lewis's biography of Kahneman and Tversky",
     "thaler misbehaving lewis undoing project reading list primary source"),
    # --- 40 ---
    ("The course's intellectual-history spine is architected around Herbert Simon's 1957 bounded rationality as the root node, with Daniel Kahneman's program and Gerd Gigerenzer's heuristics branch hanging off it as parallel downstream subtrees rather than alternatives.", "architecture", "knowledge", False,
     [("bounded rationality", "theory"), ("Herbert Simon", "person"), ("Daniel Kahneman", "person"), ("Gerd Gigerenzer", "person")],
     [("bounded rationality", "Herbert Simon", "AUTHORED_BY"), ("Daniel Kahneman", "bounded rationality", "BUILDS_ON"), ("Gerd Gigerenzer", "bounded rationality", "BUILDS_ON")],
     "how does the course structure its intellectual-history spine around Simon and its two downstream branches",
     "bounded rationality simon 1957 spine root kahneman gigerenzer branch"),
    # --- 41 ---
    ("Amos Tversky and Daniel Kahneman's 1981 Science paper on the Asian Disease problem is the canonical demonstration of framing effects and remains the most reprinted item on the behavioral-economics syllabus.", "reference", "knowledge", False,
     [("Amos Tversky", "person"), ("Daniel Kahneman", "person"), ("Asian Disease problem", "finding"), ("Science", "publication")],
     [("Asian Disease problem", "Amos Tversky", "AUTHORED_BY"), ("Asian Disease problem", "Daniel Kahneman", "AUTHORED_BY"), ("Asian Disease problem", "Science", "PUBLISHED_IN")],
     "which 1981 Science paper is the canonical demonstration of framing and the most-reprinted item on the syllabus",
     "asian disease problem tversky kahneman 1981 science framing syllabus"),
    # --- 42 ---
    ("Cass Sunstein's Simpler: The Future of Government, published in 2013, documents the US Office of Information and Regulatory Affairs as the first federal operationalisation of nudge-informed regulatory design.", "reference", "knowledge", False,
     [("Cass Sunstein", "person"), ("Simpler: The Future of Government", "publication"), ("Office of Information and Regulatory Affairs", "organization")],
     [("Simpler: The Future of Government", "Cass Sunstein", "AUTHORED_BY"), ("Simpler: The Future of Government", "Office of Information and Regulatory Affairs", "APPLIES_TO")],
     "which 2013 Sunstein book narrates the first federal agency that operationalised nudge-informed regulation",
     "sunstein simpler future government 2013 oira nudge regulatory design"),
    # --- 43. noise ---
    ("A fox has been visiting the dumpsters behind the psychology wing all week and security finally put up a motion camera to settle the betting pool.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Daniel Kahneman was awarded the 2002 Nobel Memorial Prize in Economic Sciences for integrating psychological insight into economics; Amos Tversky had died in 1996 and the Nobel is not given posthumously.", "milestone", "knowledge", False,
     [("Daniel Kahneman", "person"), ("Nobel Memorial Prize in Economic Sciences", "event"), ("Amos Tversky", "person")],
     [("Daniel Kahneman", "Nobel Memorial Prize in Economic Sciences", "VISITED")],
     "which 2002 prize did Kahneman win alone and why did Tversky not share it despite the joint research",
     "kahneman 2002 nobel memorial economic sciences tversky posthumous"),
    # --- 45 ---
    ("Richard Thaler won the 2017 Nobel Memorial Prize in Economic Sciences for his contributions to behavioral economics, with the citation naming mental accounting, self-control, and fairness as the three pillars.", "milestone", "knowledge", False,
     [("Richard Thaler", "person"), ("Nobel Memorial Prize in Economic Sciences", "event"), ("mental accounting", "theory")],
     [("Richard Thaler", "Nobel Memorial Prize in Economic Sciences", "VISITED"), ("mental accounting", "Richard Thaler", "AUTHORED_BY")],
     "which 2017 Nobel cited Thaler's three pillars of mental accounting, self-control, and fairness",
     "thaler 2017 nobel memorial economic sciences mental accounting fairness"),
    # --- 46 ---
    ("The probability weighting nonlinearity, captured by the inverse-S curve in cumulative prospect theory, overweights tail probabilities and rationalises why people buy both lottery tickets and insurance from the same paycheck.", "fact", "knowledge", False,
     [("probability weighting", "concept"), ("inverse-S curve", "concept"), ("cumulative prospect theory", "theory")],
     [("probability weighting", "cumulative prospect theory", "DEPENDS_ON"), ("inverse-S curve", "probability weighting", "IMPLEMENTS")],
     "which nonlinear curve in cumulative prospect theory explains simultaneous lottery and insurance purchases",
     "probability weighting inverse s curve lottery insurance tail overweight"),
    # --- 47 ---
    ("Adopted the reflection effect from Daniel Kahneman and Amos Tversky as the opening puzzle of lecture three: risk-averse over gains and risk-seeking over losses falls out of Prospect Theory's S-shaped value function.", "decision", "knowledge", False,
     [("reflection effect", "concept"), ("Daniel Kahneman", "person"), ("Amos Tversky", "person"), ("Prospect Theory", "theory"), ("S-shaped value function", "concept")],
     [("reflection effect", "Daniel Kahneman", "AUTHORED_BY"), ("reflection effect", "Amos Tversky", "AUTHORED_BY"), ("reflection effect", "Prospect Theory", "DEPENDS_ON"), ("S-shaped value function", "Prospect Theory", "IMPLEMENTS")],
     "which asymmetry between gains and losses is the opening puzzle of lecture three in the course",
     "reflection effect risk averse seeking s shape value function prospect"),
    # --- 48 ---
    ("Chose George Ainslie's Picoeconomics as the graduate-level primary source on hyperbolic discounting rather than the David Laibson survey; the 1992 monograph develops the bundling and willpower mechanisms in far more depth.", "decision", "knowledge", False,
     [("George Ainslie", "person"), ("Picoeconomics", "publication"), ("hyperbolic discounting", "concept"), ("David Laibson", "person")],
     [("Picoeconomics", "George Ainslie", "AUTHORED_BY"), ("Picoeconomics", "hyperbolic discounting", "APPLIES_TO"), ("Picoeconomics", "David Laibson", "PREFERS")],
     "which 1992 Ainslie monograph won the graduate reading slot over Laibson's survey treatment",
     "ainslie picoeconomics 1992 hyperbolic bundling willpower graduate primary"),
    # --- 49 ---
    ("The ultimatum game data pipeline in the teaching lab implements Werner Guth's 1982 protocol as the canonical bargaining block; responder and proposer screens share one reusable front-end component and a single session table.", "architecture", "knowledge", False,
     [("ultimatum game", "concept"), ("Werner Guth", "person")],
     [("ultimatum game", "Werner Guth", "AUTHORED_BY")],
     "how does the teaching lab implement Guth's 1982 protocol as a reusable bargaining block",
     "ultimatum game guth 1982 pipeline reusable responder proposer session"),
    # --- 50 ---
    ("Standardised on treating behavioral-economics effect sizes with Joseph Simmons's p-curve analysis before admitting findings to the course reading list; the filter retired three once-canonical priming results from the 2012 syllabus.", "decision", "knowledge", False,
     [("Joseph Simmons", "person"), ("p-curve analysis", "method"), ("priming", "concept")],
     [("p-curve analysis", "Joseph Simmons", "AUTHORED_BY"), ("p-curve analysis", "priming", "CONTRADICTS")],
     "which Simmons filter does the course apply before admitting effects to the reading list and what did it cut",
     "p curve simmons priming filter reading list 2012 syllabus retire"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
