"""One-off emitter for shared-base batch-247 — formal verification and proof assistants (Coq/Rocq, Agda, Idris, Lean, Isabelle/HOL, HOL4, Dafny, F*, ACL2, Nuprl, Z3, CVC5, Alt-Ergo, Boolector, TLA+, Alloy, P, SAW, Cryptol, Event-B, B, seL4, CompCert, Frama-C, SPARK, Why3, Viper, Fiat crypto, LiquidHaskell, HoTT, CIC).

Writes 50 rows to data/v2/shared/batch_247.tmp.jsonl with ids shared-12301..12350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_247.tmp.jsonl"
ID_OFFSET = 12300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("The verification team renamed every mention of Coq to Rocq across the CI scripts after the upstream rebrand; the binary is now rocq and the legacy coqc shim survives only on one archived build.", "decision", "technical", False,
     [("Coq", "tool"), ("Rocq", "tool"), ("coqc", "command"), ("rocq", "command")],
     [("Rocq", "Coq", "REPLACES")],
     "which proof-assistant rename forced the CI scripts to drop the legacy coqc shim",
     "coq rocq rename coqc shim rebrand ci binary proof assistant"),
    # --- 2 --- architecture
    ("Lean 4 replaced Lean 3 as the kernel for the mathlib port; the elaborator is now written in Lean itself and the tactic framework compiles down to native code rather than interpreted terms.", "architecture", "technical", False,
     [("Lean 4", "language"), ("Lean 3", "language"), ("mathlib", "library"), ("elaborator", "concept")],
     [("Lean 4", "Lean 3", "REPLACES"), ("mathlib", "Lean 4", "DEPENDS_ON")],
     "which Lean version took over the mathlib port and what shift happened in the elaborator implementation",
     "lean 4 lean 3 mathlib elaborator tactic native compile port"),
    # --- 3 --- reference
    ("The Homotopy Type Theory book, informally called the HoTT book, was produced by the Univalent Foundations program at the Institute for Advanced Study and remains the canonical reference for HoTT.", "reference", "knowledge", False,
     [("Homotopy Type Theory", "theory"), ("HoTT book", "publication"), ("Univalent Foundations", "concept"), ("Institute for Advanced Study", "organization")],
     [("HoTT book", "Univalent Foundations", "AUTHORED_BY")],
     "which canonical reference text for HoTT came out of the Univalent Foundations program at the IAS",
     "hott book univalent foundation ias homotopy type theory reference"),
    # --- 4 --- milestone
    ("Georges Gonthier completed the machine-checked proof of the Four-colour theorem in Coq in 2005; the script closed a decades-long worry over the uninspectable computer-aided argument from 1976.", "milestone", "knowledge", False,
     [("Georges Gonthier", "person"), ("Four-colour theorem", "theory"), ("Coq", "tool"), ("2005", "date")],
     [("Four-colour theorem", "Coq", "IMPLEMENTS"), ("Four-colour theorem", "Georges Gonthier", "AUTHORED_BY")],
     "which mathematician discharged the Four-colour theorem mechanically and in which proof assistant",
     "gonthier four colour theorem coq 2005 machine checked proof"),
    # --- 5 --- milestone
    ("Xavier Leroy and the Gallium team shipped CompCert, the formally verified C compiler, with every optimisation pass proved correct in Coq against a structured operational semantics of CompCert C.", "milestone", "technical", False,
     [("Xavier Leroy", "person"), ("CompCert", "tool"), ("Coq", "tool"), ("CompCert C", "language")],
     [("CompCert", "Coq", "IMPLEMENTS"), ("CompCert", "Xavier Leroy", "AUTHORED_BY")],
     "who led the CompCert effort and which proof assistant mechanised its optimisation correctness arguments",
     "compcert leroy gallium coq verified c compiler optimisation pass"),
    # --- 6 --- milestone
    ("NICTA's seL4 microkernel reached full functional correctness against its abstract specification in Isabelle/HOL in 2009; that verification later extended to binary-level and information-flow proofs.", "milestone", "technical", False,
     [("seL4", "tool"), ("NICTA", "organization"), ("Isabelle/HOL", "tool"), ("2009", "date")],
     [("seL4", "Isabelle/HOL", "IMPLEMENTS")],
     "which microkernel got a full functional-correctness proof in Isabelle/HOL and who led the work",
     "sel4 nicta isabelle hol functional correctness 2009 verify kernel"),
    # --- 7 --- decision
    ("We switched the SMT backend from Z3 to CVC5 for the Dafny proof obligations because the array-theory preprocessor in CVC5 closed three benchmarks that Z3 was timing out on at sixty seconds.", "decision", "technical", False,
     [("Z3", "tool"), ("CVC5", "tool"), ("Dafny", "language"), ("array-theory", "concept")],
     [("CVC5", "Z3", "REPLACES"), ("Dafny", "CVC5", "USES")],
     "which SMT solver took over from Z3 for the Dafny discharges and which theory preprocessor drove the change",
     "cvc5 z3 dafny smt array theory timeout backend preprocessor"),
    # --- 8 --- architecture
    ("The Why3 platform routes verification conditions to a fan-out of backends: Alt-Ergo for linear arithmetic, Z3 for bit vectors, and CVC5 for arrays; a proof session records which solver closed which VC.", "architecture", "technical", False,
     [("Why3", "tool"), ("Alt-Ergo", "tool"), ("Z3", "tool"), ("CVC5", "tool")],
     [("Why3", "Alt-Ergo", "USES"), ("Why3", "Z3", "USES"), ("Why3", "CVC5", "USES")],
     "how does Why3 route verification conditions across multiple solvers and what gets recorded per session",
     "why3 alt ergo z3 cvc5 backend fan out verification condition session"),
    # --- 9 --- reference
    ("The Curry-Howard correspondence identifies propositions with types and proofs with programs; Lean, Coq, and Agda all exploit it so that type-checking a term is the same act as verifying a proof.", "reference", "knowledge", False,
     [("Curry-Howard correspondence", "theory"), ("Lean", "language"), ("Coq", "tool"), ("Agda", "language")],
     [("Lean", "Curry-Howard correspondence", "IMPLEMENTS"), ("Agda", "Curry-Howard correspondence", "IMPLEMENTS")],
     "which foundational correspondence do Lean, Coq and Agda share so that type-checking doubles as proof-checking",
     "curry howard correspondence propositions types proofs programs lean coq agda"),
    # --- 10 --- noise
    ("Somebody left a half-empty jar of marmalade on the reading-room windowsill and the afternoon sun turned it into a small amber lantern.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- decision
    ("We migrated the type theory course notes from Agda to Idris 2 because Idris 2's quantitative type theory makes erasure annotations explicit, which matters for the linearity chapter we wanted to add.", "decision", "knowledge", False,
     [("Agda", "language"), ("Idris 2", "language"), ("quantitative type theory", "theory"), ("erasure", "concept")],
     [("Idris 2", "Agda", "REPLACES"), ("Idris 2", "quantitative type theory", "IMPLEMENTS")],
     "which dependently-typed language took over the course notes from Agda and which feature drove the choice",
     "idris 2 agda quantitative type theory erasure linearity course"),
    # --- 12 --- architecture
    ("Dafny is layered on top of the Boogie intermediate verification language; the Dafny frontend desugars specifications into Boogie, which then generates SMT queries for Z3 to discharge.", "architecture", "technical", False,
     [("Dafny", "language"), ("Boogie", "language"), ("Z3", "tool"), ("SMT", "technology")],
     [("Dafny", "Boogie", "USES"), ("Boogie", "Z3", "USES")],
     "how does Dafny reach an SMT solver and which intermediate verification language sits between them",
     "dafny boogie z3 smt intermediate verification language frontend"),
    # --- 13 --- fact
    ("F* compiles to OCaml for extraction but also targets Low* for verified C code; the HACL* cryptographic library ships as verified C produced by the Low* backend and is used in Mozilla NSS and the Linux kernel.", "fact", "technical", False,
     [("F*", "language"), ("OCaml", "language"), ("Low*", "language"), ("HACL*", "library"), ("Mozilla NSS", "project"), ("Linux kernel", "project")],
     [("HACL*", "F*", "IMPLEMENTS"), ("HACL*", "Mozilla NSS", "DEPLOYED_ON")],
     "which F* subset targets verified C and which downstream projects ship HACL* derived code",
     "fstar low star hacl verified c mozilla nss linux kernel extract"),
    # --- 14 --- preference
    ("Our team prefers Isabelle/HOL over Coq for protocol proofs because Isar structured proofs stay readable across refactors in a way that tactic-script Coq rarely does for our non-expert reviewers.", "preference", "technical", False,
     [("Isabelle/HOL", "tool"), ("Coq", "tool"), ("Isar", "language")],
     [("Isabelle/HOL", "Coq", "PREFERS"), ("Isabelle/HOL", "Isar", "USES")],
     "which proof style do we prefer for protocol work and which assistant gives us that style natively",
     "isabelle hol coq isar structured proof protocol prefer readable"),
    # --- 15 --- architecture
    ("TLA+ specs are model-checked with TLC for small configurations and symbolically verified with Apalache for larger state spaces; the CI runs both backends in parallel against the consensus module.", "architecture", "technical", False,
     [("TLA+", "language"), ("TLC", "tool"), ("Apalache", "tool"), ("consensus module", "project")],
     [("TLA+", "TLC", "USES"), ("TLA+", "Apalache", "USES")],
     "which two TLA+ backends does the CI run in parallel and what role does each play on the consensus spec",
     "tla plus tlc apalache model check symbolic consensus ci parallel"),
    # --- 16 --- reference
    ("Leslie Lamport designed TLA+ as a specification language grounded in temporal logic of actions; his Specifying Systems textbook is the standard on-ramp and the pluscal translator targets the same core semantics.", "reference", "knowledge", False,
     [("Leslie Lamport", "person"), ("TLA+", "language"), ("Specifying Systems", "publication"), ("pluscal", "language")],
     [("TLA+", "Leslie Lamport", "AUTHORED_BY"), ("Specifying Systems", "Leslie Lamport", "AUTHORED_BY")],
     "who designed TLA+ and which textbook of his serves as the canonical introduction",
     "lamport tla plus specifying systems pluscal temporal logic action"),
    # --- 17 --- decision
    ("Alloy 6 replaced Alloy 5 for our storage consistency models because the new first-class temporal operators let us write liveness properties directly instead of the old trace-predicate idiom.", "decision", "technical", False,
     [("Alloy 6", "tool"), ("Alloy 5", "tool"), ("temporal operators", "concept"), ("liveness", "concept")],
     [("Alloy 6", "Alloy 5", "REPLACES")],
     "why did the storage team move from Alloy 5 to Alloy 6 for their consistency models",
     "alloy 6 5 temporal operator liveness consistency storage model"),
    # --- 18 --- fact
    ("Daniel Jackson's group at MIT developed Alloy around the idea that lightweight relational modelling plus a bounded SAT check gets you most of the bugs without the full ceremony of a proof assistant.", "fact", "knowledge", False,
     [("Daniel Jackson", "person"), ("MIT", "organization"), ("Alloy", "tool"), ("SAT", "concept")],
     [("Alloy", "Daniel Jackson", "AUTHORED_BY"), ("Daniel Jackson", "MIT", "WORKS_AT")],
     "who built Alloy and which institution hosted the project",
     "daniel jackson mit alloy relational sat bounded model light"),
    # --- 19 --- architecture
    ("Microsoft's P language compiles state-machine specifications to C for runtime execution and to a model-checker backend for bounded exploration; both backends share the same PSym symbolic engine for conflict tests.", "architecture", "technical", False,
     [("P language", "language"), ("Microsoft", "organization"), ("PSym", "tool"), ("state-machine", "concept")],
     [("P language", "Microsoft", "AUTHORED_BY"), ("P language", "PSym", "USES")],
     "how does Microsoft's P language share a symbolic engine between its runtime and model-checker outputs",
     "p language microsoft psym state machine runtime model check symbolic"),
    # --- 20 --- decision
    ("The crypto group picked Cryptol from Galois for bit-accurate specifications of the block cipher and SAW to discharge equivalence proofs against the C implementation; the pair shipped as the reference harness.", "decision", "technical", False,
     [("Cryptol", "language"), ("SAW", "tool"), ("block cipher", "concept"), ("Galois", "organization")],
     [("Cryptol", "SAW", "RELATED_TO"), ("Cryptol", "Galois", "AUTHORED_BY")],
     "which Galois-built pair of tools did the crypto group pick for bit-accurate spec and equivalence proof",
     "cryptol saw galois block cipher equivalence proof bit accurate harness"),
    # --- 21 --- milestone
    ("The IronFleet paper demonstrated practical verified distributed systems by combining TLA+-style refinement with Dafny proofs; the Paxos and sharded-store artefacts ran at production-ish throughput.", "milestone", "technical", False,
     [("IronFleet", "project"), ("Dafny", "language"), ("TLA+", "language"), ("Paxos", "algorithm")],
     [("IronFleet", "Dafny", "USES"), ("IronFleet", "TLA+", "USES"), ("IronFleet", "Paxos", "IMPLEMENTS")],
     "which paper paired TLA+ refinement with Dafny to verify distributed systems and what artefacts did it ship",
     "iron fleet dafny tla refinement paxos sharded store distributed verify"),
    # --- 22 --- problem
    ("The CertiKOS refinement proof stalled because naïve shared-memory reasoning in Coq blew up context sizes; the fix was a layered deep specification technique that split the kernel into certified sub-abstractions, restoring tractable goals.", "problem", "technical", False,
     [("CertiKOS", "tool"), ("Coq", "tool"), ("deep specification", "concept"), ("shared-memory reasoning", "concept")],
     [("CertiKOS", "Coq", "IMPLEMENTS"), ("deep specification", "CertiKOS", "FIXES")],
     "which technique rescued the CertiKOS proof when naïve shared-memory reasoning blew up Coq contexts",
     "certikos coq deep specification layered shared memory context blow up"),
    # --- 23 --- architecture
    ("Fiat Cryptography generates verified C and assembly for elliptic-curve field arithmetic from a Coq specification; Chrome and Firefox ship the Fiat-produced code for curve25519 field operations.", "architecture", "technical", False,
     [("Fiat Cryptography", "tool"), ("Coq", "tool"), ("Chrome", "project"), ("Firefox", "project"), ("curve25519", "concept")],
     [("Fiat Cryptography", "Coq", "IMPLEMENTS"), ("Fiat Cryptography", "curve25519", "APPLIES_TO")],
     "which Coq-based tool produces the verified curve25519 field arithmetic shipped in Chrome and Firefox",
     "fiat cryptography coq curve25519 chrome firefox elliptic field verified"),
    # --- 24 --- fact
    ("LiquidHaskell bolts refinement types onto Haskell by piggybacking on SMT; a spec such as {v:Int | v >= 0} is checked by Z3 at compile time and the user sees a liquid type error rather than a runtime trap.", "fact", "technical", False,
     [("LiquidHaskell", "tool"), ("Haskell", "language"), ("Z3", "tool"), ("refinement types", "theory")],
     [("LiquidHaskell", "Haskell", "EXTENDS"), ("LiquidHaskell", "Z3", "USES"), ("LiquidHaskell", "refinement types", "IMPLEMENTS")],
     "how does LiquidHaskell add refinement types to Haskell and what solver does it lean on",
     "liquid haskell refinement type smt z3 compile error liquid spec"),
    # --- 25 --- decision
    ("Frama-C with the WP plugin took over from manual Hoare-style review for the airbag controller; the discharge rate on weakest-precondition goals sits near ninety percent once the contracts are tightened.", "decision", "technical", False,
     [("Frama-C", "tool"), ("WP plugin", "tool"), ("Hoare-style review", "method"), ("airbag controller", "project")],
     [("Frama-C", "Hoare-style review", "REPLACES"), ("Frama-C", "WP plugin", "USES")],
     "which Frama-C plugin replaced manual Hoare-style review on the airbag controller and what discharge rate did it reach",
     "frama c wp plugin hoare airbag controller discharge weakest precondition"),
    # --- 26 --- architecture
    ("SPARK Ada restricts full Ada to a verifiable subset and drives GNATprove, which in turn reuses Why3 and a solver fan-out; the toolchain integrates into the same IDE as regular Ada development.", "architecture", "technical", False,
     [("SPARK Ada", "language"), ("Ada", "language"), ("GNATprove", "tool"), ("Why3", "tool")],
     [("SPARK Ada", "Ada", "EXTENDS"), ("GNATprove", "Why3", "USES")],
     "which Ada subset backs GNATprove and how does that prover reach the SMT backends",
     "spark ada gnatprove why3 subset verifiable solver fan out ide"),
    # --- 27 --- reference
    ("Calculus of Inductive Constructions, or CIC, is the core type theory of Coq and by extension Rocq; the foundational text is Coquand and Huet's 1988 Calculus of Constructions paper plus Paulin-Mohring's inductive types extension.", "reference", "knowledge", False,
     [("Calculus of Inductive Constructions", "theory"), ("CIC", "theory"), ("Coq", "tool"), ("Coquand", "person"), ("Huet", "person"), ("Paulin-Mohring", "person")],
     [("Coq", "Calculus of Inductive Constructions", "IMPLEMENTS"), ("Calculus of Inductive Constructions", "Coquand", "AUTHORED_BY")],
     "which core type theory sits under Coq and which original authors introduced its base and inductive extensions",
     "cic calculus inductive construction coq coquand huet paulin mohring"),
    # --- 28 --- preference
    ("For teaching dependent types we prefer Idris 2 over Coq because the interactive hole-filling workflow gives undergraduates a direct feedback loop, while Coq tactics need more upfront investment to feel productive.", "preference", "knowledge", False,
     [("Idris 2", "language"), ("Coq", "tool"), ("dependent types", "theory"), ("hole-filling", "concept")],
     [("Idris 2", "Coq", "PREFERS"), ("Idris 2", "dependent types", "IMPLEMENTS")],
     "which dependently-typed teaching tool do we favour over Coq for undergraduates and why",
     "idris 2 coq dependent type teaching hole filling undergraduate prefer"),
    # --- 29 --- fact
    ("ACL2 is a first-order Lisp-flavoured prover used heavily at AMD and Centaur for microprocessor verification; floating-point divide and FMA units have been discharged against bit-accurate models in ACL2 for decades.", "fact", "technical", False,
     [("ACL2", "tool"), ("Lisp", "language"), ("AMD", "organization"), ("Centaur", "organization"), ("FMA", "concept")],
     [("ACL2", "Lisp", "EXTENDS"), ("AMD", "ACL2", "USES"), ("Centaur", "ACL2", "USES")],
     "which Lisp-flavoured prover do AMD and Centaur use for floating-point unit verification",
     "acl2 lisp amd centaur microprocessor fma divide floating point verify"),
    # --- 30 --- decision
    ("We picked Viper as the intermediate verification language for the concurrent Rust analyser because its permission-based separation logic maps cleanly onto Rust's borrow semantics without a heavyweight encoding.", "decision", "technical", False,
     [("Viper", "language"), ("Rust", "language"), ("separation logic", "theory"), ("borrow semantics", "concept")],
     [("Viper", "separation logic", "IMPLEMENTS"), ("Viper", "Rust", "APPLIES_TO")],
     "which intermediate verification language fits Rust's borrow semantics best and why",
     "viper rust separation logic permission borrow intermediate concurrent"),
    # --- 31 --- architecture
    ("Event-B is the refinement-based successor to Jean-Raymond Abrial's B method; the Rodin toolset drives machines through successive refinement steps and generates proof obligations handed to Atelier B and SMT backends.", "architecture", "technical", False,
     [("Event-B", "language"), ("B method", "method"), ("Jean-Raymond Abrial", "person"), ("Rodin", "tool"), ("Atelier B", "tool")],
     [("Event-B", "B method", "EXTENDS"), ("Rodin", "Event-B", "IMPLEMENTS"), ("B method", "Jean-Raymond Abrial", "AUTHORED_BY")],
     "which toolset drives Event-B refinement and what relationship does Event-B have to Abrial's B method",
     "event b method abrial rodin atelier refinement proof obligation"),
    # --- 32 --- milestone
    ("Paris metro line 14 has run under a controller derived from the B method since 1998; this was one of the first industrial-scale formal-methods deployments in public transport.", "milestone", "technical", False,
     [("Paris metro line 14", "infrastructure"), ("B method", "method"), ("1998", "date")],
     [("Paris metro line 14", "B method", "USES")],
     "which Paris metro line shipped a driverless controller derived from the B method and in what year",
     "paris metro line 14 b method driverless 1998 formal public transport"),
    # --- 33 --- fact
    ("Boolector and its successor Bitwuzla are QF_BV-first SMT solvers; they are the default choice when verification conditions are dominated by bit-vector and array reasoning rather than nonlinear arithmetic.", "fact", "technical", False,
     [("Boolector", "tool"), ("Bitwuzla", "tool"), ("QF_BV", "concept"), ("SMT", "technology")],
     [("Bitwuzla", "Boolector", "REPLACES")],
     "which bit-vector-first SMT solver succeeded Boolector and when is that family the right default",
     "boolector bitwuzla qf bv smt bit vector array nonlinear default"),
    # --- 34 --- preference
    ("For tactic-heavy refactors we prefer Lean 4 over Coq because the macro system and native compilation of tactics keeps edit-compile-check loops under a second even as proof terms grow.", "preference", "technical", False,
     [("Lean 4", "language"), ("Coq", "tool"), ("tactic", "concept"), ("macro system", "concept")],
     [("Lean 4", "Coq", "PREFERS")],
     "why do we prefer Lean 4 to Coq when tactic-heavy refactoring is on the critical path",
     "lean 4 coq tactic macro native compile edit loop refactor"),
    # --- 35 --- decision
    ("The kernel team chose to keep seL4 proofs in Isabelle/HOL rather than port to Lean 4; the existing proof mass was too large and the refinement framework had no proven equivalent in Lean at the time.", "decision", "technical", False,
     [("seL4", "tool"), ("Isabelle/HOL", "tool"), ("Lean 4", "language"), ("refinement framework", "concept")],
     [("seL4", "Isabelle/HOL", "USES")],
     "why did the seL4 team keep their proofs in Isabelle/HOL rather than migrate to Lean 4",
     "sel4 isabelle hol lean 4 refinement port proof mass kernel team"),
    # --- 36 --- problem
    ("Porting a classical analysis script from Nuprl to Coq stumbled because Nuprl's extensional computational type theory admits quotients that Coq's CIC does not; the workaround was to reformulate the quotient statements via setoid equality before the port.", "problem", "knowledge", False,
     [("Nuprl", "tool"), ("computational type theory", "theory"), ("Coq", "tool"), ("CIC", "theory"), ("setoid equality", "concept")],
     [("Nuprl", "computational type theory", "IMPLEMENTS"), ("Coq", "CIC", "IMPLEMENTS"), ("setoid equality", "Nuprl", "FIXES")],
     "which foundational gap tripped up porting a Nuprl analysis script to Coq and what workaround closed it",
     "nuprl coq cic computational type extensional quotient setoid port"),
    # --- 37 --- decision
    ("We dropped HOL4 from the tool evaluation after the shortlist round; the library coverage for our signal-processing domain was thinner than Isabelle/HOL's and the migration effort would not pay back.", "decision", "technical", False,
     [("HOL4", "tool"), ("Isabelle/HOL", "tool"), ("signal-processing", "field")],
     [("Isabelle/HOL", "HOL4", "PREFERS")],
     "why did HOL4 fall out of our shortlist in favour of Isabelle/HOL for signal-processing verification",
     "hol4 isabelle hol shortlist signal processing library coverage drop"),
    # --- 38 --- reference
    ("Pierce's Software Foundations is the standard teaching series for Coq-based certified programming; volumes one through six cover logic, programming languages, and verified functional algorithms in progression.", "reference", "knowledge", False,
     [("Software Foundations", "publication"), ("Pierce", "person"), ("Coq", "tool")],
     [("Software Foundations", "Pierce", "AUTHORED_BY"), ("Software Foundations", "Coq", "USES")],
     "which multi-volume Coq teaching series by Pierce anchors certified-programming courses",
     "pierce software foundations coq certified programming teaching volume"),
    # --- 39 --- milestone
    ("The hs-to-coq project translated a large fraction of the Haskell containers library into Coq and proved structural properties about Data.Map; the pipeline reuses Haskell's deriving machinery to ease the translation.", "milestone", "technical", False,
     [("hs-to-coq", "tool"), ("Haskell", "language"), ("Coq", "tool"), ("Data.Map", "library")],
     [("hs-to-coq", "Haskell", "USES"), ("hs-to-coq", "Coq", "PRODUCES")],
     "which project translates Haskell code into Coq and what library did it prove properties about",
     "hs to coq haskell containers data map deriving translation property"),
    # --- 40 --- fact
    ("Separation logic, introduced by Reynolds and O'Hearn in 2001-2002, is the common semantic substrate for Viper, Iris in Coq, and the concurrent reasoning in VerCors; it replaced flat Hoare logic for heap-manipulating programs.", "fact", "knowledge", False,
     [("Separation logic", "theory"), ("Reynolds", "person"), ("O'Hearn", "person"), ("Iris", "library"), ("VerCors", "tool")],
     [("Separation logic", "Reynolds", "AUTHORED_BY"), ("Separation logic", "O'Hearn", "AUTHORED_BY"), ("Iris", "Separation logic", "IMPLEMENTS")],
     "who introduced separation logic and which modern verification tools built on it for heap reasoning",
     "separation logic reynolds ohearn iris vercors viper heap hoare"),
    # --- 41 --- problem
    ("Our Dafny project suffered flaky proofs whenever Z3 drifted a patch version across developer machines; we fixed it by pinning a solver manifest with Z3 4.12 primary and CVC5 1.0 secondary and failing CI if either falls off the supported list.", "problem", "technical", False,
     [("Dafny", "language"), ("Z3", "tool"), ("CVC5", "tool"), ("solver manifest", "config")],
     [("Dafny", "Z3", "DEPENDS_ON"), ("Dafny", "CVC5", "DEPENDS_ON"), ("solver manifest", "Dafny", "FIXES")],
     "what change stopped Dafny proofs going flaky when Z3 drifted patch versions across developer machines",
     "dafny z3 cvc5 solver manifest pin version drift flaky ci fix"),
    # --- 42 --- decision
    ("We rejected Nuprl for the contract proofs because its extensional type theory, while elegant, lacked the off-the-shelf tactic mass and mathlib-sized library that Lean 4 offered at the time of the bake-off.", "decision", "knowledge", False,
     [("Nuprl", "tool"), ("Lean 4", "language"), ("extensional type theory", "theory"), ("mathlib", "library")],
     [("Lean 4", "Nuprl", "PREFERS"), ("Lean 4", "mathlib", "USES")],
     "why did Lean 4 win the contract-proof bake-off against Nuprl despite Nuprl's theoretical elegance",
     "nuprl lean 4 extensional type theory mathlib bake off tactic reject"),
    # --- 43 --- noise
    ("The common-room espresso machine developed an intermittent hissing noise that the maintenance rota has been arguing about for two weeks.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- preference
    ("For everyday scratch proofs I prefer Lean 4 over Agda because the error messages point at the term hole rather than a whole-file unification failure; Agda's error locality has improved but is still the weaker axis.", "preference", "knowledge", False,
     [("Lean 4", "language"), ("Agda", "language"), ("term hole", "concept")],
     [("Lean 4", "Agda", "PREFERS")],
     "why do scratch proofs feel faster in Lean 4 than Agda on everyday work",
     "lean 4 agda term hole error locality scratch proof everyday prefer"),
    # --- 45 --- architecture
    ("The Iris framework builds a higher-order concurrent separation logic inside Coq; clients instantiate the logic with ghost-state resources and discharge invariants through Iris Proof Mode tactics.", "architecture", "technical", False,
     [("Iris", "library"), ("Coq", "tool"), ("concurrent separation logic", "theory"), ("Iris Proof Mode", "tool")],
     [("Iris", "Coq", "EXTENDS"), ("Iris", "concurrent separation logic", "IMPLEMENTS")],
     "which Coq library hosts a higher-order concurrent separation logic and what tactic layer drives it",
     "iris coq concurrent separation logic ghost state proof mode invariant"),
    # --- 46 --- milestone
    ("Kepler conjecture formalisation, led by Thomas Hales in the Flyspeck project, finished in 2014 using HOL Light and Isabelle/HOL together; it certified a sphere-packing proof first sketched in 1998.", "milestone", "knowledge", False,
     [("Kepler conjecture", "theory"), ("Thomas Hales", "person"), ("Flyspeck", "project"), ("HOL Light", "tool"), ("Isabelle/HOL", "tool"), ("2014", "date")],
     [("Flyspeck", "Thomas Hales", "AUTHORED_BY"), ("Flyspeck", "HOL Light", "USES"), ("Flyspeck", "Isabelle/HOL", "USES")],
     "which sphere-packing proof did Hales finish mechanising in 2014 and which assistants did Flyspeck use",
     "kepler hales flyspeck hol light isabelle 2014 sphere packing proof"),
    # --- 47 --- reference
    ("Benjamin Pierce's Types and Programming Languages, commonly abbreviated TAPL, is the standard textbook on type systems and underpins many of the formalisations in Coq-based courses across universities.", "reference", "knowledge", False,
     [("Types and Programming Languages", "publication"), ("TAPL", "publication"), ("Benjamin Pierce", "person"), ("Coq", "tool")],
     [("Types and Programming Languages", "Benjamin Pierce", "AUTHORED_BY")],
     "which textbook by Benjamin Pierce is the standard reference on type systems in Coq-oriented courses",
     "pierce types programming languages tapl textbook type system coq"),
    # --- 48 --- decision
    ("We picked Alt-Ergo as the default solver in the avionics toolchain because its internal rational arithmetic is deterministic across platforms, which matters more to DO-178C auditors than raw speed.", "decision", "technical", False,
     [("Alt-Ergo", "tool"), ("DO-178C", "concept"), ("rational arithmetic", "concept"), ("avionics", "field")],
     [("Alt-Ergo", "avionics", "APPLIES_TO")],
     "why did the avionics team default to Alt-Ergo despite not being the fastest solver on paper",
     "alt ergo avionics do 178c rational arithmetic deterministic solver"),
    # --- 49 --- fact
    ("The TLC model checker explores TLA+ state spaces by brute enumeration with symmetry reduction; Apalache instead encodes transitions into SMT via Z3 and handles much larger state spaces at the cost of symbolic-only properties.", "fact", "technical", False,
     [("TLC", "tool"), ("TLA+", "language"), ("Apalache", "tool"), ("Z3", "tool"), ("symmetry reduction", "concept")],
     [("TLC", "TLA+", "APPLIES_TO"), ("Apalache", "Z3", "USES")],
     "how do TLC and Apalache differ in how they cover TLA+ state spaces",
     "tlc apalache tla plus z3 smt symmetry enumeration state space"),
    # --- 50 --- decision
    ("We moved the proof CI to cache Coq object files per file hash and invalidate downstream on a transitive import change; rebuilding only the touched subgraph dropped a clean rebuild from forty minutes to under four on the mathlib-sized project.", "decision", "technical", False,
     [("Coq", "tool"), ("proof CI", "pattern"), ("mathlib", "library"), ("transitive import", "concept")],
     [("proof CI", "Coq", "USES")],
     "why did we move the proof CI to a per-file-hash Coq cache and what speedup did the subgraph invalidation unlock",
     "coq ci cache object file transitive import subgraph mathlib rebuild"),
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
