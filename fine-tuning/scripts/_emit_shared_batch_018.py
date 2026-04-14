"""One-off emitter for shared-base batch-018 — knowledge domain (math/CS-theory/logic/philosophy).

Writes 50 rows with ids shared-00851..00900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_018.tmp.jsonl"
ID_OFFSET = 850

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Cook's theorem establishes that Boolean satisfiability is NP-complete, giving the first complete problem for the class.", "fact", "knowledge", False,
     [("Cook's theorem", "theory"), ("Boolean satisfiability", "concept"), ("NP-complete", "concept")],
     [],
     "which result first identified a complete problem for nondeterministic polynomial time",
     "SAT hardness seminal completeness proof class membership"),
    # --- 2 ---
    ("Rudin's Principles of Mathematical Analysis remains the canonical undergraduate text for rigorous real analysis.", "reference", "knowledge", False,
     [("Rudin", "person"), ("Principles of Mathematical Analysis", "publication"), ("real analysis", "field")],
     [("Principles of Mathematical Analysis", "Rudin", "AUTHORED_BY")],
     "which textbook still anchors undergraduate rigorous calculus teaching",
     "blue book undergraduate metric space epsilon delta standard"),
    # --- 3 ---
    ("Kripke semantics replaces truth-value assignments with possible-worlds models for interpreting modal operators.", "decision", "knowledge", False,
     [("Kripke semantics", "method"), ("truth-value assignments", "method"), ("modal operators", "concept")],
     [("Kripke semantics", "truth-value assignments", "REPLACES")],
     "what interpretation scheme took over for necessity and possibility in logic",
     "possible worlds frame relation accessibility modal foundation"),
    # --- 4 ---
    ("The AKS primality test, published in 2002, was the first deterministic polynomial-time algorithm for primality.", "milestone", "knowledge", False,
     [("AKS primality test", "algorithm"), ("2002", "date")],
     [],
     "when did a deterministic polynomial-time primality checker first appear",
     "Indian trio prime certificate polynomial deterministic year"),
    # --- 5 ---
    ("Grover's algorithm improves on classical unstructured search by giving a quadratic speedup on quantum hardware.", "decision", "knowledge", False,
     [("Grover's algorithm", "algorithm"), ("classical unstructured search", "method")],
     [("Grover's algorithm", "classical unstructured search", "IMPROVES_ON")],
     "which quantum routine beats brute-force lookup by a square-root factor",
     "amplitude amplification quadratic query speedup BQP"),
    # --- 6 ---
    ("Functionalism in philosophy of mind identifies mental states with their causal roles rather than their physical substrate.", "fact", "knowledge", False,
     [("Functionalism", "theory"), ("philosophy of mind", "field")],
     [],
     "which position defines thoughts by their causal-role profile",
     "multiple realisability causal role psychology mind theory"),
    # --- 7 ---
    ("Prefers category theory over set theory as foundational language for modern algebraic geometry work.", "preference", "knowledge", False,
     [("category theory", "field"), ("set theory", "field"), ("algebraic geometry", "field")],
     [("category theory", "set theory", "PREFERS")],
     "which abstract framework anchors current scheme-theoretic work",
     "universal property abstraction foundation pick Grothendieck style"),
    # --- 8 ---
    ("Hartshorne's Algebraic Geometry, published in 1977, became the standard graduate schemes text after Grothendieck's EGA.", "reference", "knowledge", False,
     [("Hartshorne", "person"), ("Algebraic Geometry", "publication"), ("1977", "date"), ("Grothendieck", "person"), ("EGA", "publication")],
     [("Algebraic Geometry", "Hartshorne", "AUTHORED_BY"), ("EGA", "Grothendieck", "AUTHORED_BY")],
     "which graduate text picked up the schemes torch after the French foundations",
     "graduate scheme textbook red book successor canonical"),
    # --- 9 ---
    ("The halting problem is undecidable: no algorithm can determine for every program whether it terminates on a given input.", "fact", "knowledge", False,
     [("halting problem", "concept"), ("algorithm", "concept")],
     [],
     "what classical decision problem has no general computable solution",
     "Turing diagonalisation termination undecidable proof classic"),
    # --- 10. noise ---
    ("Let me pull up the paper to get the exact statement.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("PSPACE contains the polynomial hierarchy, and collapse of PH to any finite level remains open.", "fact", "knowledge", False,
     [("PSPACE", "concept"), ("polynomial hierarchy", "concept"), ("PH", "concept")],
     [],
     "which space class sits above the unbounded alternation tower",
     "space complexity hierarchy containment open collapse question"),
    # --- 12 ---
    ("Wittgenstein's Philosophical Investigations, published posthumously in 1953, dismantled the picture theory of his earlier Tractatus.", "milestone", "knowledge", False,
     [("Wittgenstein", "person"), ("Philosophical Investigations", "publication"), ("1953", "date"), ("Tractatus", "publication")],
     [("Philosophical Investigations", "Wittgenstein", "AUTHORED_BY"), ("Tractatus", "Wittgenstein", "AUTHORED_BY")],
     "when did the later work overturning the picture theory appear",
     "language games later Wittgenstein posthumous reversal year"),
    # --- 13 ---
    ("Dependent type theory extends simply-typed lambda calculus with types that may depend on terms.", "decision", "knowledge", False,
     [("Dependent type theory", "theory"), ("simply-typed lambda calculus", "theory")],
     [("Dependent type theory", "simply-typed lambda calculus", "EXTENDS")],
     "which type system generalises STLC by letting types range over values",
     "Pi types propositions as types term-indexed family generalisation"),
    # --- 14 ---
    ("The simplex method, devised by Dantzig in 1947, solves linear programs by pivoting between basic feasible vertices.", "reference", "knowledge", False,
     [("simplex method", "algorithm"), ("Dantzig", "person"), ("1947", "date"), ("linear programs", "concept")],
     [("simplex method", "Dantzig", "AUTHORED_BY")],
     "which pivoting routine for linear optimisation traces back to the late 1940s",
     "vertex pivot linear program classical algorithm inventor year"),
    # --- 15 ---
    ("Moral realism claims that moral facts exist mind-independently; anti-realism denies that claim.", "fact", "knowledge", False,
     [("Moral realism", "theory"), ("anti-realism", "theory")],
     [("Moral realism", "anti-realism", "CONTRADICTS")],
     "which metaethical stance asserts observer-independent ethical facts",
     "metaethics stance objective moral facts independence thesis"),
    # --- 16 ---
    ("Sipser's Introduction to the Theory of Computation is the usual undergraduate gateway to automata and complexity.", "reference", "knowledge", False,
     [("Sipser", "person"), ("Introduction to the Theory of Computation", "publication"), ("automata", "concept"), ("complexity", "field")],
     [("Introduction to the Theory of Computation", "Sipser", "AUTHORED_BY")],
     "which textbook usually opens the door to automata and complexity theory",
     "undergraduate computation theory standard textbook gateway"),
    # --- 17 ---
    ("Miller-Rabin primality testing trades determinism for speed by accepting a bounded Monte Carlo error.", "decision", "knowledge", False,
     [("Miller-Rabin primality testing", "algorithm"), ("Monte Carlo error", "concept")],
     [],
     "which randomised primality test accepts bounded error for speed",
     "probabilistic prime check witness repeat bounded false"),
    # --- 18 ---
    ("CLRS's Introduction to Algorithms is the default reference for data structures and algorithm design courses.", "reference", "knowledge", False,
     [("CLRS", "publication"), ("Introduction to Algorithms", "publication"), ("data structures", "concept")],
     [],
     "which hefty book anchors most algorithms courses in practice",
     "Cormen Leiserson Rivest Stein algorithm reference default"),
    # --- 19 ---
    ("Parfit's Reasons and Persons argued personal identity is not what matters in survival over time.", "reference", "knowledge", False,
     [("Parfit", "person"), ("Reasons and Persons", "publication"), ("personal identity", "concept")],
     [("Reasons and Persons", "Parfit", "AUTHORED_BY")],
     "which book separated what matters in survival from strict personal identity",
     "reductionist identity survival ethics landmark philosophical work"),
    # --- 20 ---
    ("Public-key cryptography depends on trapdoor functions, one-way maps with an auxiliary secret enabling inversion.", "fact", "knowledge", False,
     [("Public-key cryptography", "field"), ("trapdoor functions", "concept")],
     [("Public-key cryptography", "trapdoor functions", "DEPENDS_ON")],
     "which cryptographic primitive powers asymmetric schemes",
     "asymmetric scheme one-way invert secret primitive basis"),
    # --- 21 ---
    ("Elliptic curve cryptography replaces RSA in constrained environments because keys are far smaller for equivalent security.", "decision", "knowledge", False,
     [("Elliptic curve cryptography", "field"), ("RSA", "algorithm")],
     [("Elliptic curve cryptography", "RSA", "REPLACES")],
     "which key-exchange family took over when bandwidth and compute are tight",
     "smaller key equivalent security constrained device swap"),
    # --- 22 ---
    ("The Curry-Howard correspondence identifies proofs in intuitionistic logic with terms in typed lambda calculus.", "fact", "knowledge", False,
     [("Curry-Howard correspondence", "theory"), ("intuitionistic logic", "field"), ("typed lambda calculus", "theory")],
     [],
     "which bridge links logical proofs to programs in a type system",
     "propositions as types proofs programs isomorphism intuitionistic"),
    # --- 23 ---
    ("Homotopy type theory builds on Martin-Lof type theory by interpreting types as spaces up to homotopy.", "fact", "knowledge", False,
     [("Homotopy type theory", "theory"), ("Martin-Lof type theory", "theory")],
     [("Homotopy type theory", "Martin-Lof type theory", "BUILDS_ON")],
     "which newer foundation reads types as spaces and identities as paths",
     "HoTT univalence path space foundation layered dependent"),
    # --- 24 ---
    ("Fermat's Last Theorem was proven by Andrew Wiles in 1994 using the modularity of elliptic curves.", "milestone", "knowledge", False,
     [("Fermat's Last Theorem", "theory"), ("Andrew Wiles", "person"), ("1994", "date"), ("elliptic curves", "concept")],
     [],
     "when and by whom was the three-century-old number theory conjecture finally resolved",
     "modularity Taniyama Shimura proof completion year"),
    # --- 25 ---
    ("Rawls's A Theory of Justice grounds liberal egalitarian distribution in the original-position thought experiment.", "reference", "knowledge", False,
     [("Rawls", "person"), ("A Theory of Justice", "publication"), ("original-position", "concept")],
     [("A Theory of Justice", "Rawls", "AUTHORED_BY")],
     "which treatise built distributive principles from a hypothetical choice behind a veil",
     "veil of ignorance liberal egalitarian framework political philosophy"),
    # --- 26 ---
    ("Lattice-based cryptography replaces classical number-theoretic schemes in the NIST post-quantum standardisation process as the leading candidate family.", "decision", "knowledge", False,
     [("Lattice-based cryptography", "field"), ("number-theoretic schemes", "method"), ("NIST", "organization")],
     [("Lattice-based cryptography", "number-theoretic schemes", "REPLACES")],
     "which scheme family is favoured by the federal standards body against quantum attackers",
     "post quantum candidate family lattice hardness standardiser swap"),
    # --- 27 ---
    ("The Church-Turing thesis claims every effectively calculable function is computable by a Turing machine.", "fact", "knowledge", False,
     [("Church-Turing thesis", "theory"), ("Turing machine", "concept")],
     [],
     "what informal claim ties effective computability to a single model",
     "effectively calculable thesis model equivalence universal claim"),
    # --- 28 ---
    ("Prefers Coq over Lean for teaching constructive proofs when legacy course material and the stdlib ecosystem matter more than novelty.", "preference", "knowledge", False,
     [("Coq", "tool"), ("Lean", "tool"), ("constructive proofs", "method")],
     [("Coq", "Lean", "PREFERS")],
     "which proof assistant wins when legacy teaching material is the deciding factor",
     "interactive theorem prover teaching material ecosystem legacy pick"),
    # --- 29 ---
    ("Scala's cats library implements recursion schemes over pattern-matching on algebraic data types for typed functional programming.", "architecture", "knowledge", False,
     [("Scala", "language"), ("cats", "library"), ("recursion schemes", "pattern"), ("algebraic data types", "concept")],
     [("cats", "recursion schemes", "IMPLEMENTS")],
     "which typed JVM library packages recursion patterns over inductive data",
     "catamorphism pattern match inductive structure typed FP package"),
    # --- 30 ---
    ("Anscombe's Intention, published in 1957, reframed action theory around the question of why-questions and reasons.", "milestone", "knowledge", False,
     [("Anscombe", "person"), ("Intention", "publication"), ("1957", "date"), ("action theory", "field")],
     [("Intention", "Anscombe", "AUTHORED_BY")],
     "when did the monograph reshaping philosophy of action appear",
     "why question reasons acting agent rationality short book"),
    # --- 31 ---
    ("Byzantine fault tolerance requires more than two-thirds honest participants for safety under arbitrary failures.", "fact", "knowledge", False,
     [("Byzantine fault tolerance", "concept"), ("honest participants", "concept")],
     [],
     "what threshold of honest nodes does arbitrary-fault consensus demand",
     "BFT two thirds threshold arbitrary failure consensus bound"),
    # --- 32 ---
    ("The CAP theorem makes the impossibility claim that a distributed store cannot simultaneously deliver consistency, availability, and partition tolerance.", "fact", "knowledge", False,
     [("CAP theorem", "theory"), ("impossibility claim", "claim"), ("consistency", "concept"), ("availability", "concept"), ("partition tolerance", "concept")],
     [],
     "which impossibility result constrains distributed data store guarantees",
     "Brewer impossibility three-way tradeoff distributed store classic"),
    # --- 33 ---
    ("MacIntyre's After Virtue argued modern moral discourse survives as fragments divorced from the virtue tradition that gave them sense.", "reference", "knowledge", False,
     [("MacIntyre", "person"), ("After Virtue", "publication"), ("virtue tradition", "concept")],
     [("After Virtue", "MacIntyre", "AUTHORED_BY")],
     "which book charged that our moral vocabulary is fragmented leftovers",
     "virtue ethics revival fragments modern discourse diagnosis"),
    # --- 34. noise ---
    ("Hold on, I want to double check that reference before I commit to it.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Quine's Two Dogmas of Empiricism attacked the analytic-synthetic distinction and reductive verification theory in 1951.", "reference", "knowledge", False,
     [("Quine", "person"), ("Two Dogmas of Empiricism", "publication"), ("analytic-synthetic distinction", "concept"), ("1951", "date")],
     [("Two Dogmas of Empiricism", "Quine", "AUTHORED_BY")],
     "which essay rejected the twin empiricist pillars of the mid-century",
     "holism web belief dogma critique analytic synthetic year"),
    # --- 36 ---
    ("Big-O notation characterises asymptotic upper bounds on resource use as input size grows without bound.", "fact", "knowledge", False,
     [("Big-O notation", "concept"), ("asymptotic upper bounds", "concept")],
     [],
     "what notation family captures worst-case growth of resource consumption",
     "asymptotic growth upper bound scaling notation limit"),
    # --- 37 ---
    ("Shor's algorithm improves on classical integer factoring by running in polynomial time on a quantum computer.", "decision", "knowledge", False,
     [("Shor's algorithm", "algorithm"), ("classical integer factoring", "method")],
     [("Shor's algorithm", "classical integer factoring", "IMPROVES_ON")],
     "which quantum routine threatens RSA by factoring in polynomial time",
     "period finding quantum factoring asymptotic exponential speedup"),
    # --- 38 ---
    ("Externalism about mental content holds meaning depends partly on features outside the thinker's head.", "fact", "knowledge", False,
     [("Externalism", "theory"), ("mental content", "concept")],
     [],
     "which view about meaning places part of content outside the individual mind",
     "twin earth wide content meaning outside head thesis"),
    # --- 39 ---
    ("Homomorphic encryption is an emerging technology that supports computation on ciphertexts, producing encrypted results that decrypt to the plaintext answer.", "fact", "knowledge", False,
     [("Homomorphic encryption", "technology"), ("ciphertexts", "concept")],
     [],
     "which cryptographic capability lets a party compute over encrypted data directly",
     "encrypted computation ciphertext operation result decrypt property"),
    # --- 40 ---
    ("Red-black trees replace plain binary search trees when bounded worst-case logarithmic operations matter more than simplicity.", "decision", "knowledge", False,
     [("Red-black trees", "algorithm"), ("binary search trees", "algorithm")],
     [("Red-black trees", "binary search trees", "REPLACES")],
     "which balanced tree takes over when logarithmic worst case is required",
     "balanced search structure logarithmic worst case colour invariant"),
    # --- 41 ---
    ("Martingale convergence theorems underwrite many probabilistic proofs, including laws of large numbers and optional stopping results.", "fact", "knowledge", False,
     [("Martingale convergence theorems", "theory"), ("laws of large numbers", "theory"), ("optional stopping", "concept")],
     [],
     "which probability results quietly power many limit and stopping proofs",
     "martingale limit convergence probability toolkit stopping"),
    # --- 42 ---
    ("Graduate algebra courses commonly follow Dummit and Foote's framework of rings, modules, and Galois theory built on ZFC foundations.", "architecture", "knowledge", False,
     [("Dummit and Foote", "publication"), ("rings", "concept"), ("modules", "concept"), ("Galois theory", "field"), ("ZFC", "framework")],
     [],
     "what course structure often shapes first-year graduate algebra",
     "graduate algebra textbook rings modules Galois sequence"),
    # --- 43 ---
    ("Haskell prefers lazy evaluation over strict evaluation, allowing infinite data structures but complicating space reasoning.", "preference", "knowledge", False,
     [("Haskell", "language"), ("lazy evaluation", "concept"), ("strict evaluation", "concept")],
     [("lazy evaluation", "strict evaluation", "PREFERS")],
     "which evaluation strategy does the canonical pure language pick",
     "non-strict default infinite stream tradeoff language choice"),
    # --- 44 ---
    ("The Riemann Hypothesis conjectures that every non-trivial zero of the zeta function has real part one-half.", "fact", "knowledge", False,
     [("Riemann Hypothesis", "theory"), ("zeta function", "concept")],
     [],
     "what unresolved conjecture pins non-trivial zeta zeros to the critical line",
     "critical line zeta zero conjecture million dollar open problem"),
    # --- 45 ---
    ("Kripke's Princeton lectures of 1970, later collected as Naming and Necessity, introduced rigid designators and causal theories of reference.", "milestone", "knowledge", False,
     [("Kripke", "person"), ("Princeton lectures", "event"), ("1970", "date"), ("Naming and Necessity", "publication"), ("rigid designators", "concept")],
     [("Naming and Necessity", "Kripke", "AUTHORED_BY")],
     "when did the seminar on rigid designation and reference take place",
     "rigid designator causal reference lecture series transformative year"),
    # --- 46 ---
    ("Paxos implements distributed consensus through prepare and accept phases across a majority of replicas.", "architecture", "knowledge", False,
     [("Paxos", "algorithm"), ("distributed consensus", "concept"), ("replicas", "concept")],
     [("Paxos", "distributed consensus", "IMPLEMENTS")],
     "how does the classic consensus protocol structure its agreement rounds",
     "prepare accept majority quorum consensus protocol phases"),
    # --- 47 ---
    ("The Raft protocol improves on Paxos for teachability by separating leader election, log replication, and safety into clean modules.", "decision", "knowledge", False,
     [("Raft", "protocol"), ("Paxos", "algorithm"), ("leader election", "concept"), ("log replication", "concept")],
     [("Raft", "Paxos", "IMPROVES_ON")],
     "which consensus design aimed explicitly at being easier to learn than its predecessor",
     "understandable consensus leader log separation teachability design"),
    # --- 48 ---
    ("Gettier cases show that justified true belief is insufficient for knowledge, a problem still shaping epistemology.", "problem", "knowledge", False,
     [("Gettier cases", "finding"), ("justified true belief", "concept"), ("epistemology", "field")],
     [],
     "which counterexamples undermined the classical definition of knowledge",
     "justified true belief counterexample knowledge analysis problem"),
    # --- 49 ---
    ("Lamport's happens-before relation underpins logical clocks and the definition of concurrency in distributed systems.", "reference", "knowledge", False,
     [("Lamport", "person"), ("happens-before relation", "concept"), ("logical clocks", "concept")],
     [("logical clocks", "Lamport", "AUTHORED_BY")],
     "whose partial order defined distributed concurrency for practical purposes",
     "partial order distributed event clock causality founder"),
    # --- 50 ---
    ("Ramsey theory claims that sufficiently large structures must contain ordered substructures of any fixed size.", "fact", "knowledge", False,
     [("Ramsey theory", "field"), ("ordered substructures", "concept")],
     [],
     "which combinatorial field insists that large enough disorder hides order",
     "combinatorics unavoidable order large structure pigeonhole"),
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
