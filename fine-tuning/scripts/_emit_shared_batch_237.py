"""One-off emitter for shared-base batch-237 — knowledge domain (classical algorithms and data structures: CLRS, sorting, search trees, hashing, sketches, graph algorithms, string matching, numeric transforms, linear programming, complexity theory).

Writes 50 rows to data/v2/shared/batch_237.tmp.jsonl with ids shared-11801..11850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_237.tmp.jsonl"
ID_OFFSET = 11800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Introduction to Algorithms by Cormen, Leiserson, Rivest, and Stein remains the reference textbook for graduate-level algorithm courses; the fourth edition added chapters on matchings and online algorithms.", "reference", "technical", False,
     [("Introduction to Algorithms", "publication"), ("Cormen", "concept"), ("Leiserson", "concept"), ("Rivest", "concept"), ("Stein", "concept")],
     [("Introduction to Algorithms", "Cormen", "AUTHORED_BY")],
     "which textbook by Cormen and collaborators anchors graduate algorithm coursework and what topics did the fourth edition add",
     "clrs introduction algorithms cormen leiserson rivest stein fourth edition"),
    # --- 2 ---
    ("Switched the in-house sort routine from Lomuto partitioning to Hoare partitioning for quicksort; the Hoare scheme does fewer swaps on already-sorted runs and handles the equal-keys case more gracefully.", "decision", "technical", False,
     [("Lomuto", "algorithm"), ("Hoare", "algorithm"), ("quicksort", "algorithm")],
     [("Hoare", "Lomuto", "REPLACES")],
     "which partitioning scheme did the quicksort implementation adopt over Lomuto and what behaviour on equal keys drove the choice",
     "hoare lomuto partition quicksort swap equal key sorted run"),
    # --- 3 ---
    ("Mergesort became the stable-sort default in the library after a customer hit a reordering bug with the previous introsort path; the extra O(n) auxiliary space was deemed acceptable for that stability guarantee.", "decision", "technical", False,
     [("Mergesort", "algorithm"), ("introsort", "algorithm"), ("stable-sort", "concept")],
     [("Mergesort", "introsort", "REPLACES")],
     "which sort algorithm became the library's stable-sort default and what stability bug forced the switch away from introsort",
     "mergesort introsort stable sort auxiliary space reorder bug default"),
    # --- 4 ---
    ("Heapsort is used for the priority-queue drain in the scheduler because its worst case stays O(n log n) without recursion; the binary heap sits in a flat array indexed by 2i+1 and 2i+2.", "architecture", "technical", False,
     [("Heapsort", "algorithm"), ("binary heap", "concept"), ("priority-queue", "concept")],
     [("Heapsort", "binary heap", "USES")],
     "why did the scheduler pick heapsort for its priority queue drain and how is the underlying binary heap laid out",
     "heap sort binary heap priority queue worst case drain scheduler"),
    # --- 5 ---
    ("Radix sort on 32-bit keys beat quicksort in the trace-analysis pipeline by roughly four times on ten-million-key inputs; the eight-bit-per-pass LSD variant fit the cache on our commodity boxes.", "milestone", "technical", False,
     [("Radix sort", "algorithm"), ("quicksort", "algorithm"), ("LSD", "method")],
     [("Radix sort", "quicksort", "IMPROVES_ON")],
     "which sort variant beat quicksort on 32-bit trace keys and what pass width fit the CPU cache",
     "radix sort lsd quicksort 32 bit pass cache commodity trace"),
    # --- 6 ---
    ("Binary search on a sorted array is the canonical O(log n) membership test; the lower_bound variant returns the first element not less than the key and forms the building block for equal_range.", "reference", "technical", False,
     [("Binary search", "algorithm"), ("lower_bound", "method"), ("equal_range", "method")],
     [("equal_range", "lower_bound", "DEPENDS_ON")],
     "which binary-search variant returns the first element not less than the key and what higher-level operation builds on it",
     "binary search lower bound equal range sorted log n member"),
    # --- 7 ---
    ("AVL trees keep every subtree balance within plus-or-minus one; the strict balance invariant gives the tightest search bound but rotations fire more often than in red-black trees under heavy insert churn.", "fact", "technical", False,
     [("AVL trees", "algorithm"), ("red-black trees", "algorithm"), ("rotation", "concept")],
     [("AVL trees", "red-black trees", "RELATED_TO")],
     "what balance invariant do AVL trees enforce and how does rotation frequency compare to red-black trees under insert churn",
     "avl tree balance factor rotation red black insert churn subtree"),
    # --- 8 ---
    ("The ordered-map container sits on a red-black tree; the looser balance than AVL trades tighter query depth for fewer rotations per insert, which mattered for the write-heavy audit log.", "decision", "technical", False,
     [("red-black tree", "algorithm"), ("AVL", "algorithm"), ("ordered-map", "concept"), ("audit log", "concept")],
     [("red-black tree", "AVL", "PREFERS")],
     "why did the ordered-map container pick a red-black tree over AVL for the write-heavy audit log",
     "red black avl ordered map rotation insert audit log write"),
    # --- 9 ---
    ("B-trees underpin the on-disk index format; the branching factor is tuned to fill a 16 KB page so each node visit costs one seek instead of cascading through pointer-chased binary tree nodes.", "architecture", "technical", False,
     [("B-trees", "algorithm"), ("on-disk index", "concept"), ("branching factor", "concept")],
     [("B-trees", "on-disk index", "APPLIES_TO")],
     "how is the B-tree branching factor chosen for the on-disk index and what I/O cost does that buy",
     "btree branching factor 16kb page seek index on disk pointer"),
    # --- 10. noise ---
    ("The departmental coffee machine now requires a six-character access code because someone kept brewing decaf by accident at 4 am.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Splay trees are the access-path cache of choice for the symbol-table lookup; recently accessed keys rotate to the root, which amortises repeated lookups to O(log n) without a separate LRU layer.", "decision", "technical", False,
     [("Splay trees", "algorithm"), ("symbol-table", "concept"), ("LRU", "pattern")],
     [("Splay trees", "LRU", "REPLACES")],
     "which self-adjusting tree replaced the explicit LRU layer for symbol-table lookups and what does access do",
     "splay tree symbol table lru amortised access rotate root lookup"),
    # --- 12 ---
    ("Treaps combine BST key order with heap priority drawn at random; expected depth stays O(log n) without bookkeeping colours or balance factors, which made the code noticeably shorter than the AVL path.", "preference", "technical", False,
     [("Treaps", "algorithm"), ("BST", "concept"), ("AVL", "algorithm"), ("heap priority", "concept")],
     [("Treaps", "AVL", "PREFERS")],
     "what invariant combo do treaps enforce and why was the code shorter than the AVL implementation",
     "treap bst heap priority random expected log avl shorter code"),
    # --- 13 ---
    ("Skip lists from the Pugh paper replaced the balanced-tree index in the lock-free cache; the probabilistic level structure is easier to update concurrently than any rotation-based tree.", "decision", "technical", False,
     [("Skip lists", "algorithm"), ("Pugh", "concept"), ("balanced-tree", "algorithm"), ("lock-free cache", "concept")],
     [("Skip lists", "balanced-tree", "REPLACES")],
     "which probabilistic structure from Pugh replaced balanced trees in the lock-free cache and why",
     "skip list pugh balanced tree lock free concurrent rotation probabilistic"),
    # --- 14 ---
    ("The hash table uses linear probing with Robin Hood displacement; on average the longest probe stays under ten even at 0.9 load factor, which was the cutover point versus quadratic probing in our benchmark.", "architecture", "technical", False,
     [("linear probing", "algorithm"), ("Robin Hood", "algorithm"), ("quadratic probing", "algorithm"), ("load factor", "concept")],
     [("Robin Hood", "quadratic probing", "IMPROVES_ON")],
     "which probing scheme does the hash table use under high load and why did it beat quadratic probing",
     "linear probing robin hood quadratic load factor 0.9 probe bench"),
    # --- 15 ---
    ("Cuckoo hashing powers the packet-classifier table because worst-case lookup stays O(1); two hash functions point to candidate slots and a displacement chain triggers a full rehash only above 0.5 load.", "architecture", "technical", False,
     [("Cuckoo hashing", "algorithm"), ("packet-classifier", "concept"), ("rehash", "concept")],
     [("Cuckoo hashing", "packet-classifier", "APPLIES_TO")],
     "which hashing scheme gives the packet-classifier worst-case O(1) lookup and when does the full rehash fire",
     "cuckoo hashing packet classifier lookup worst case rehash load 0.5"),
    # --- 16 ---
    ("Bloom filters front the on-disk key lookup in the log-structured store; a positive hit still goes to disk but the one-percent false-positive rate skips roughly 99 out of 100 misses.", "architecture", "technical", False,
     [("Bloom filters", "algorithm"), ("log-structured store", "concept"), ("false-positive", "concept")],
     [("Bloom filters", "log-structured store", "APPLIES_TO")],
     "which probabilistic filter fronts the log-structured key lookup and what miss rate does it cut",
     "bloom filter log structured false positive one percent miss skip"),
    # --- 17 ---
    ("HyperLogLog estimates unique-visitor counts in the analytics pipeline with a few kilobytes per stream; the 1.04 over root-m standard error was well within the product's display precision.", "fact", "technical", False,
     [("HyperLogLog", "algorithm"), ("analytics pipeline", "concept")],
     [("HyperLogLog", "analytics pipeline", "APPLIES_TO")],
     "which cardinality sketch powers unique-visitor counts and what standard-error bound does it offer",
     "hyperloglog unique visitor cardinality sketch kilobyte standard error"),
    # --- 18 ---
    ("Count-min sketch tracks heavy hitters in the DDoS filter; overestimates never fire false-positive drops because the decision threshold has a guard band above the worst-case sketch error.", "architecture", "technical", False,
     [("Count-min sketch", "algorithm"), ("DDoS filter", "concept"), ("heavy hitters", "concept")],
     [("Count-min sketch", "DDoS filter", "APPLIES_TO")],
     "which streaming sketch feeds the DDoS filter's heavy-hitter detection without producing false drops",
     "count min sketch ddos heavy hitter guard band overestimate drop"),
    # --- 19 ---
    ("The disjoint-set union structure with Tarjan's path compression and union-by-rank makes Kruskal's MST run in effectively O(E alpha(V)); the inverse-Ackermann factor is a small constant in practice.", "fact", "technical", False,
     [("disjoint-set union", "algorithm"), ("Tarjan", "concept"), ("path compression", "method"), ("union-by-rank", "method"), ("Kruskal", "algorithm")],
     [("Kruskal", "disjoint-set union", "USES")],
     "which DSU optimisations from Tarjan give Kruskal its near-linear runtime and what constant replaces log",
     "disjoint set union tarjan path compression rank kruskal ackermann"),
    # --- 20 ---
    ("Dijkstra's shortest-path routine uses a binary-heap priority queue; the Fibonacci-heap variant was ruled out because the constant factors lose on realistic graphs despite the better asymptotic bound.", "decision", "technical", False,
     [("Dijkstra", "algorithm"), ("binary-heap", "concept"), ("Fibonacci-heap", "algorithm")],
     [("Dijkstra", "Fibonacci-heap", "PREFERS")],
     "which heap variant did Dijkstra stick with and why did Fibonacci heaps lose despite the tighter bound",
     "dijkstra binary heap fibonacci constant factor shortest path graph"),
    # --- 21 ---
    ("Bellman-Ford drives the negative-edge path calculation in the currency-arbitrage detector; three passes over the edge list uncover negative cycles that plain Dijkstra cannot handle.", "fact", "technical", False,
     [("Bellman-Ford", "algorithm"), ("negative cycle", "concept"), ("Dijkstra", "algorithm"), ("currency-arbitrage", "concept")],
     [("Bellman-Ford", "Dijkstra", "IMPROVES_ON")],
     "which shortest-path algorithm catches the negative cycles Dijkstra misses in the currency-arbitrage detector",
     "bellman ford negative cycle dijkstra arbitrage currency edge"),
    # --- 22 ---
    ("Floyd-Warshall computes the all-pairs distance matrix for the transit planner at pre-compute time; the O(V^3) bound is fine because the graph is small and dense and the result is cached overnight.", "architecture", "technical", False,
     [("Floyd-Warshall", "algorithm"), ("transit planner", "concept"), ("distance matrix", "concept")],
     [("Floyd-Warshall", "transit planner", "APPLIES_TO")],
     "which all-pairs algorithm precomputes the transit planner's distance matrix and why is O(V^3) acceptable",
     "floyd warshall all pairs transit planner dense graph overnight"),
    # --- 23 ---
    ("Prim's algorithm builds the spanning tree of the cable-routing graph because edges dominate vertices by a wide margin; a binary heap drives the frontier and the lazy-delete trick keeps memory flat.", "decision", "technical", False,
     [("Prim", "algorithm"), ("spanning tree", "concept"), ("cable-routing", "concept")],
     [("Prim", "cable-routing", "APPLIES_TO")],
     "which MST algorithm did the cable-routing graph pick and what data structure drives the frontier",
     "prim spanning tree binary heap frontier lazy delete cable route"),
    # --- 24 ---
    ("Kruskal's algorithm with a disjoint-set union produced the minimum spanning tree for the sparse road network; sorting the edges once and walking them in order outperformed Prim for that graph shape.", "milestone", "technical", False,
     [("Kruskal", "algorithm"), ("disjoint-set union", "algorithm"), ("Prim", "algorithm"), ("road network", "concept")],
     [("Kruskal", "Prim", "PREFERS")],
     "which MST algorithm handled the sparse road network and what edge-sorting step let it beat Prim",
     "kruskal disjoint set prim sparse road network edge sort mst"),
    # --- 25 ---
    ("A* search replaced uniform-cost search in the game pathfinder; the admissible octile-distance heuristic cuts expanded nodes by roughly an order of magnitude on the benchmark maps.", "decision", "technical", False,
     [("A*", "algorithm"), ("uniform-cost search", "algorithm"), ("octile-distance", "method")],
     [("A*", "uniform-cost search", "REPLACES")],
     "which heuristic search replaced uniform-cost in the pathfinder and which heuristic function did it use",
     "a star uniform cost octile distance heuristic pathfinder expand node"),
    # --- 26 ---
    ("Kosaraju's two-pass SCC algorithm powers the dependency-cycle detector; one forward DFS, a graph transpose, and a second DFS on finish-time order isolate each strongly connected component.", "fact", "technical", False,
     [("Kosaraju", "algorithm"), ("SCC", "concept"), ("dependency-cycle detector", "concept"), ("transpose", "method")],
     [("Kosaraju", "dependency-cycle detector", "APPLIES_TO")],
     "which two-pass SCC algorithm feeds the dependency-cycle detector and which intermediate graph does it build",
     "kosaraju scc two pass transpose dfs finish time dependency cycle"),
    # --- 27 ---
    ("Tarjan's single-pass SCC algorithm superseded Kosaraju in the build-tool dependency analyser; the explicit stack and low-link bookkeeping avoid the graph transpose that Kosaraju needs.", "decision", "technical", False,
     [("Tarjan", "algorithm"), ("Kosaraju", "algorithm"), ("low-link", "method"), ("build-tool", "concept")],
     [("Tarjan", "Kosaraju", "REPLACES")],
     "which single-pass SCC algorithm replaced Kosaraju in the build tool and what bookkeeping field drives it",
     "tarjan scc single pass kosaraju low link build tool transpose"),
    # --- 28 ---
    ("Topological sort via Kahn's algorithm orders the task graph in the CI runner; queue up zero-indegree nodes, remove outgoing edges, and a leftover cycle surfaces as an unprocessed remainder.", "architecture", "technical", False,
     [("Topological sort", "algorithm"), ("Kahn", "concept"), ("CI runner", "concept"), ("indegree", "concept")],
     [("Topological sort", "CI runner", "APPLIES_TO")],
     "which topological-sort procedure orders the CI runner's task graph and how does it report a cycle",
     "topological sort kahn indegree queue ci runner task graph cycle"),
    # --- 29 ---
    ("Knuth-Morris-Pratt powers the substring search in the log-ingest tail; the failure-function preprocessing makes the matcher worst-case O(n + m) no matter how adversarial the pattern.", "fact", "technical", False,
     [("Knuth-Morris-Pratt", "algorithm"), ("failure-function", "method"), ("log-ingest", "concept")],
     [("Knuth-Morris-Pratt", "log-ingest", "APPLIES_TO")],
     "which string-match algorithm runs the log-ingest tail and what preprocessing gives its linear worst case",
     "knuth morris pratt kmp failure function log ingest substring worst"),
    # --- 30 ---
    ("Boyer-Moore with the bad-character and good-suffix rules replaced Knuth-Morris-Pratt for the grep-like CLI; long alphabets skip large chunks per mismatch, so real-world English corpora run sub-linear on average.", "decision", "technical", False,
     [("Boyer-Moore", "algorithm"), ("Knuth-Morris-Pratt", "algorithm"), ("good-suffix", "method"), ("bad-character", "method")],
     [("Boyer-Moore", "Knuth-Morris-Pratt", "REPLACES")],
     "which matcher replaced KMP in the grep-like CLI and which two skip rules make it sub-linear on English",
     "boyer moore bad character good suffix grep sub linear english"),
    # --- 31 ---
    ("Rabin-Karp hashing fuels the plagiarism detector because rolling hashes let each sliding window reuse the previous hash in O(1); collision candidates get an exact string compare as a tie-breaker.", "decision", "technical", False,
     [("Rabin-Karp", "algorithm"), ("rolling hash", "method"), ("plagiarism detector", "concept")],
     [("Rabin-Karp", "plagiarism detector", "APPLIES_TO")],
     "which hashing-based matcher drives the plagiarism detector and how does the sliding window avoid recomputation",
     "rabin karp rolling hash plagiarism collision sliding window compare"),
    # --- 32 ---
    ("Aho-Corasick automaton matches thousands of blocklist patterns against each packet in one pass; the trie with failure links keeps matching linear in the input length regardless of pattern count.", "architecture", "technical", False,
     [("Aho-Corasick", "algorithm"), ("blocklist", "concept"), ("failure links", "method"), ("trie", "concept")],
     [("Aho-Corasick", "blocklist", "APPLIES_TO")],
     "which multi-pattern automaton matches the blocklist in one packet pass and what trie extension makes it linear",
     "aho corasick blocklist failure link trie multi pattern packet linear"),
    # --- 33 ---
    ("Suffix arrays replaced hash-based indexing in the genome search service; the DC3 construction builds the array in linear time and the LCP array answers substring queries in O(m log n).", "milestone", "technical", False,
     [("Suffix arrays", "algorithm"), ("DC3", "method"), ("LCP array", "concept"), ("genome search", "concept")],
     [("Suffix arrays", "genome search", "APPLIES_TO")],
     "which indexing structure replaced hashes in the genome search service and which construction builds it in linear time",
     "suffix array dc3 lcp genome search hash linear time substring"),
    # --- 34 ---
    ("Ukkonen's online suffix-tree construction was retired in favour of suffix arrays; the tree built incrementally but the 20x memory overhead per character burned through cache on every realistic workload.", "problem", "technical", False,
     [("Ukkonen", "algorithm"), ("suffix-tree", "algorithm"), ("suffix arrays", "algorithm")],
     [("suffix arrays", "suffix-tree", "REPLACES")],
     "why was Ukkonen's suffix tree replaced by suffix arrays despite its online construction property",
     "ukkonen suffix tree online suffix array memory overhead cache"),
    # --- 35 ---
    ("Manacher's algorithm finds the longest palindromic substring in linear time; the palette editor's mirror-token check switched from quadratic expand-around-centre after a 200 KB paste froze the UI.", "problem", "technical", False,
     [("Manacher", "algorithm"), ("expand-around-centre", "method"), ("palindromic substring", "concept")],
     [("Manacher", "expand-around-centre", "REPLACES")],
     "which linear-time palindrome algorithm replaced expand-around-centre after a big paste froze the UI",
     "manacher palindrome linear expand around centre paste freeze ui"),
    # --- 36 ---
    ("FFT-based convolution replaced the naive O(n^2) loop in the audio-effects chain; the NTT variant sees action only for the cryptographic signature layer where modular arithmetic matters.", "milestone", "technical", False,
     [("FFT", "algorithm"), ("NTT", "algorithm"), ("convolution", "concept"), ("audio-effects", "concept")],
     [("FFT", "convolution", "APPLIES_TO"), ("NTT", "FFT", "IS_A")],
     "which transform replaced the naive convolution in audio effects and where does the NTT variant show up",
     "fft ntt convolution audio effect modular signature n squared"),
    # --- 37 ---
    ("Simplex drives the production scheduler's linear program because each pivot is cheap and real-world instances rarely hit the exponential worst case; interior-point is the fallback for the degenerate constraint sets.", "decision", "technical", False,
     [("Simplex", "algorithm"), ("interior-point", "algorithm"), ("linear program", "concept"), ("production scheduler", "concept")],
     [("Simplex", "interior-point", "PREFERS")],
     "which LP method drives the production scheduler and when does the interior-point fallback kick in",
     "simplex interior point linear program scheduler pivot degenerate"),
    # --- 38 ---
    ("Interior-point methods were introduced by Karmarkar and beat simplex on pathological instances; the polynomial-time guarantee matters for the regulatory reporting LP where adversarial inputs are possible.", "reference", "technical", False,
     [("Interior-point", "algorithm"), ("Karmarkar", "concept"), ("simplex", "algorithm"), ("regulatory reporting", "concept")],
     [("Interior-point", "simplex", "IMPROVES_ON")],
     "which LP method from Karmarkar beats simplex on pathological inputs and why does the regulatory LP care",
     "interior point karmarkar simplex polynomial worst regulatory lp"),
    # --- 39 ---
    ("Dynamic programming via Bellman's equation underpins the dispatch policy; the optimal-substructure property lets memoisation cache sub-problem values and collapse the recursion to polynomial time.", "fact", "technical", False,
     [("Dynamic programming", "method"), ("Bellman's equation", "theory"), ("memoisation", "method"), ("dispatch policy", "concept")],
     [("Dynamic programming", "Bellman's equation", "BUILDS_ON")],
     "which equation from Bellman underpins dynamic programming and what caching pattern collapses its recursion",
     "dynamic programming bellman equation memoise optimal substructure dispatch"),
    # --- 40 ---
    ("LP duality turned out to be the right framing for the matching problem after the primal simplex stalled on degenerate pivots; the dual formulation exposed a complementary slackness check that cut the runtime by half.", "problem", "technical", False,
     [("LP duality", "theory"), ("primal simplex", "algorithm"), ("complementary slackness", "concept"), ("matching problem", "concept")],
     [("LP duality", "primal simplex", "IMPROVES_ON")],
     "which LP reformulation broke the matching-problem stall on the primal simplex and what slackness check appeared",
     "lp duality primal simplex matching complementary slackness pivot stall"),
    # --- 41 ---
    ("The Cook-Levin theorem established SAT as NP-complete and became the bedrock for every subsequent hardness reduction; the memory-eviction scheduling problem reduces from 3-SAT in a half-page proof.", "reference", "technical", False,
     [("Cook-Levin theorem", "theory"), ("SAT", "concept"), ("NP-complete", "concept"), ("3-SAT", "concept")],
     [("Cook-Levin theorem", "SAT", "APPLIES_TO")],
     "which theorem established SAT as NP-complete and how does the eviction-scheduling reduction use 3-SAT",
     "cook levin theorem sat np complete 3 sat reduction eviction"),
    # --- 42 ---
    ("Karp's 21 NP-complete problems catalogue the canonical reductions from SAT; the vertex-cover entry is the one we lean on when arguing that the feature-selection variant is not tractable in the general case.", "reference", "technical", False,
     [("Karp", "concept"), ("21 NP-complete problems", "publication"), ("vertex-cover", "concept"), ("feature-selection", "concept")],
     [("21 NP-complete problems", "Karp", "AUTHORED_BY")],
     "which 1972 catalogue enumerates canonical NP-complete reductions and which entry does feature-selection borrow",
     "karp 21 np complete vertex cover feature selection sat reduction"),
    # --- 43. noise ---
    ("The rooftop herb garden lost most of the basil to an unexpected May frost and the remaining pots got dragged indoors for the rest of the week.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Prefer the iterative heapify over the recursive sift-down in the in-house priority queue; the recursive form blew the 64 KB thread stack on deeply skewed inputs in the stress test.", "preference", "technical", False,
     [("heapify", "method"), ("sift-down", "method"), ("priority queue", "concept")],
     [("heapify", "sift-down", "PREFERS")],
     "which heap-maintenance form did the priority queue prefer and what stack-overflow bug drove the switch",
     "heapify sift down recursive iterative priority queue stack overflow"),
    # --- 45 ---
    ("CLRS chapter on greedy algorithms formalised the matroid framework that justifies Kruskal's correctness; the exchange-argument template in the book is the one we still crib for interview prep materials.", "reference", "technical", False,
     [("CLRS", "publication"), ("matroid", "theory"), ("Kruskal", "algorithm"), ("exchange-argument", "method")],
     [("matroid", "Kruskal", "APPLIES_TO")],
     "which CLRS framework justifies Kruskal's greedy correctness and which proof template does it furnish",
     "clrs matroid kruskal greedy exchange argument interview prep"),
    # --- 46 ---
    ("The interview-question bank prefers red-black trees over AVL for the balanced-BST exercise; candidates were routinely tripping on the AVL rebalance case analysis and the red-black walkthrough reads cleaner.", "preference", "technical", False,
     [("red-black trees", "algorithm"), ("AVL", "algorithm"), ("interview-question bank", "concept")],
     [("red-black trees", "AVL", "PREFERS")],
     "which balanced-BST variant does the interview question bank prefer and what did candidates keep tripping on",
     "red black avl interview question bank rebalance candidate case"),
    # --- 47 ---
    ("Hash-table collision resolution in the compile-cache moved from separate chaining to open addressing; the cache-line friendliness of linear probing cut the compile-cache lookup time by roughly thirty percent.", "milestone", "technical", False,
     [("separate chaining", "algorithm"), ("open addressing", "algorithm"), ("linear probing", "algorithm"), ("compile-cache", "concept")],
     [("open addressing", "separate chaining", "REPLACES")],
     "which collision-resolution scheme replaced separate chaining in the compile cache and what hardware feature won",
     "separate chaining open addressing linear probe cache line compile"),
    # --- 48 ---
    ("The streaming analytics service pairs HyperLogLog for cardinality with count-min sketch for frequency; together they hold a few megabytes per day where the exact-count path needed tens of gigabytes.", "milestone", "technical", False,
     [("HyperLogLog", "algorithm"), ("count-min sketch", "algorithm"), ("streaming analytics", "concept")],
     [("count-min sketch", "HyperLogLog", "RELATED_TO")],
     "which pair of sketches replaced exact counting in the streaming analytics service and what memory ratio did they achieve",
     "hyperloglog count min sketch streaming analytics megabyte gigabyte"),
    # --- 49 ---
    ("Prefer Tarjan's SCC over Kosaraju's when the graph is stored implicitly; the transpose that Kosaraju needs forces a second full traversal that Tarjan's single pass avoids outright.", "preference", "technical", False,
     [("Tarjan", "algorithm"), ("Kosaraju", "algorithm"), ("SCC", "concept"), ("transpose", "method")],
     [("Tarjan", "Kosaraju", "PREFERS")],
     "which SCC algorithm is preferred on implicit graphs and which intermediate pass does it avoid",
     "tarjan kosaraju scc implicit graph transpose single"),
    # --- 50 ---
    ("Delivered the first pass of the MST service on the clean road-network dataset: Kruskal with DSU, eight million edges processed in under two seconds on a single box, validated against a Prim reference output.", "milestone", "technical", False,
     [("MST service", "project"), ("Kruskal", "algorithm"), ("DSU", "algorithm"), ("Prim", "algorithm")],
     [("MST service", "Kruskal", "USES")],
     "which MST service shipped its first pass and what reference algorithm validated the Kruskal-with-DSU output",
     "mst service kruskal dsu prim reference eight million edge road"),
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
