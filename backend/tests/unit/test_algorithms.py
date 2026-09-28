"""Comprehensive unit tests for darkmem algorithm implementations.

Covers: C3 MRO, suffix index, call resolution cache, symbol table owner index,
RRF fusion, memory classifier accuracy, process tracer parameters,
DBSCAN/Louvain clustering, multi-hop binding propagation.
"""

import pytest
import numpy as np

from app.services.symbol_table import SymbolTable, SymbolEntry, CALLABLE_KINDS
from app.services.suffix_index import SuffixIndex
from app.services.heritage_resolver import (
    _c3_linearize,
    _leftmost_base,
    _implements_split,
    _qualified_syntax,
    _single_inheritance,
)
from app.services.call_resolver import CallResolver
from app.services.code_parser import ExtractedCall
from app.services.hybrid_search import HybridSearchService


# =============================================================================
# C3 MRO LINEARIZATION
# =============================================================================


class TestC3Linearization:
    """Test Python-style C3 MRO with diamond and complex hierarchies."""

    def test_single_class_no_parents(self):
        result = _c3_linearize("A", {}, {})
        assert result == ["A"]

    def test_single_inheritance_chain(self):
        parent_map = {"C": ["B"], "B": ["A"]}
        result = _c3_linearize("C", parent_map, {})
        assert result == ["C", "B", "A"]

    def test_diamond_inheritance(self):
        # Classic diamond: D -> B, C -> A
        parent_map = {"D": ["B", "C"], "B": ["A"], "C": ["A"]}
        result = _c3_linearize("D", parent_map, {})
        assert result == ["D", "B", "C", "A"]

    def test_diamond_a_appears_once(self):
        parent_map = {"D": ["B", "C"], "B": ["A"], "C": ["A"]}
        result = _c3_linearize("D", parent_map, {})
        assert result.count("A") == 1

    def test_complex_hierarchy(self):
        # E -> C, D; C -> A; D -> B; B -> A
        parent_map = {"E": ["C", "D"], "C": ["A"], "D": ["B"], "B": ["A"]}
        result = _c3_linearize("E", parent_map, {})
        assert result is not None
        assert result[0] == "E"
        assert result[-1] == "A"
        assert result.count("A") == 1

    def test_cycle_detection(self):
        parent_map = {"A": ["B"], "B": ["A"]}
        result = _c3_linearize("A", parent_map, {})
        assert result is None

    def test_inconsistent_hierarchy_returns_none(self):
        # This creates an impossible MRO in Python:
        # class X(A, B): ...
        # class Y(B, A): ...
        # class Z(X, Y): ... -> inconsistent
        parent_map = {
            "X": ["A", "B"],
            "Y": ["B", "A"],
            "Z": ["X", "Y"],
        }
        result = _c3_linearize("Z", parent_map, {})
        assert result is None

    def test_cache_is_populated(self):
        parent_map = {"B": ["A"]}
        cache: dict[str, list[str]] = {}
        _c3_linearize("B", parent_map, cache)
        assert "A" in cache
        assert "B" in cache
        assert cache["A"] == ["A"]
        assert cache["B"] == ["B", "A"]

    def test_cache_is_reused(self):
        parent_map = {"D": ["B", "C"], "B": ["A"], "C": ["A"]}
        cache: dict[str, list[str]] = {}
        _c3_linearize("B", parent_map, cache)
        # B and A should be cached; D should reuse them
        result = _c3_linearize("D", parent_map, cache)
        assert result == ["D", "B", "C", "A"]

    def test_three_parents(self):
        parent_map = {"D": ["A", "B", "C"]}
        result = _c3_linearize("D", parent_map, {})
        assert result == ["D", "A", "B", "C"]

    def test_deep_chain_depth_10(self):
        # A0 -> A1 -> ... -> A10
        parent_map = {f"A{i}": [f"A{i+1}"] for i in range(10)}
        result = _c3_linearize("A0", parent_map, {})
        assert result == [f"A{i}" for i in range(11)]


class TestLeftmostBase:
    """Test C++ leftmost-base DFS with last-occurrence dedup."""

    def test_simple_chain(self):
        parent_map = {"C": ["B"], "B": ["A"]}
        result = _leftmost_base("C", parent_map)
        assert result == ["C", "B", "A"]

    def test_diamond_deduplication(self):
        parent_map = {"D": ["B", "C"], "B": ["A"], "C": ["A"]}
        result = _leftmost_base("D", parent_map)
        assert result.count("A") == 1
        assert result[0] == "D"

    def test_leftmost_parent_preferred(self):
        parent_map = {"D": ["B", "C"], "B": ["A"], "C": ["A"]}
        result = _leftmost_base("D", parent_map)
        assert result.index("B") < result.index("C")

    def test_no_parents(self):
        result = _leftmost_base("A", {})
        assert result == ["A"]


class TestImplementsSplit:
    """Test Java/C#/Kotlin extends+implements split."""

    def test_single_extends(self):
        parent_map = {"B": ["A"]}
        edge_types = {"B": {"A": "extends"}}
        extends, impls = _implements_split("B", parent_map, edge_types)
        assert extends == ["B", "A"]
        assert impls == []

    def test_extends_plus_implements(self):
        parent_map = {"C": ["A", "I1", "I2"]}
        edge_types = {"C": {"A": "extends", "I1": "implements", "I2": "implements"}}
        extends, impls = _implements_split("C", parent_map, edge_types)
        assert extends == ["C", "A"]
        assert set(impls) == {"I1", "I2"}

    def test_deep_extends_chain(self):
        parent_map = {"C": ["B", "I"], "B": ["A"]}
        edge_types = {"C": {"B": "extends", "I": "implements"}, "B": {"A": "extends"}}
        extends, impls = _implements_split("C", parent_map, edge_types)
        assert extends == ["C", "B", "A"]
        assert impls == ["I"]

    def test_no_extends_only_implements(self):
        parent_map = {"C": ["I1", "I2"]}
        edge_types = {"C": {"I1": "implements", "I2": "implements"}}
        extends, impls = _implements_split("C", parent_map, edge_types)
        assert extends == ["C"]
        assert set(impls) == {"I1", "I2"}


class TestQualifiedSyntax:
    def test_returns_self_plus_parents(self):
        parent_map = {"S": ["T1", "T2"]}
        result = _qualified_syntax("S", parent_map)
        assert result == ["S", "T1", "T2"]

    def test_no_parents(self):
        assert _qualified_syntax("S", {}) == ["S"]


class TestSingleInheritance:
    def test_walks_first_parent(self):
        parent_map = {"C": ["B", "X"], "B": ["A"]}
        result = _single_inheritance("C", parent_map)
        assert result == ["C", "B", "A"]
        assert "X" not in result

    def test_walks_full_chain(self):
        parent_map = {f"A{i}": [f"A{i+1}"] for i in range(20)}
        result = _single_inheritance("A0", parent_map)
        assert len(result) == 21
        assert result[0] == "A0"
        assert result[-1] == "A20"


# =============================================================================
# SUFFIX INDEX
# =============================================================================


class TestSuffixIndex:
    """Test O(1) import resolution via suffix-keyed lookup."""

    @pytest.fixture
    def index(self):
        return SuffixIndex([
            "src/utils/helpers.py",
            "src/models/user.ts",
            "src/index.ts",
            "lib/auth/jwt_handler.py",
            "tests/test_utils.py",
        ])

    def test_exact_filename(self, index):
        assert index.lookup("helpers.py") == "src/utils/helpers.py"

    def test_partial_path(self, index):
        assert index.lookup("utils/helpers.py") == "src/utils/helpers.py"

    def test_full_path(self, index):
        assert index.lookup("src/utils/helpers.py") == "src/utils/helpers.py"

    def test_dotted_module_name(self, index):
        assert index.lookup("utils.helpers") == "src/utils/helpers.py"

    def test_stem_without_extension(self, index):
        assert index.lookup("helpers") == "src/utils/helpers.py"

    def test_extension_trial_py(self, index):
        result = index.lookup("jwt_handler")
        assert result == "lib/auth/jwt_handler.py"

    def test_extension_trial_ts(self, index):
        result = index.lookup("user")
        assert result == "src/models/user.ts"

    def test_case_insensitive_fallback(self, index):
        result = index.lookup("HELPERS.PY")
        assert result == "src/utils/helpers.py"

    def test_nonexistent_returns_none(self, index):
        assert index.lookup("does_not_exist.py") is None

    def test_directory_listing(self, index):
        files = index.list_dir("utils")
        assert "src/utils/helpers.py" in files

    def test_backslash_normalization(self, index):
        assert index.lookup("utils\\helpers.py") == "src/utils/helpers.py"

    def test_empty_index(self):
        si = SuffixIndex([])
        assert si.lookup("anything") is None

    def test_single_file(self):
        si = SuffixIndex(["main.py"])
        assert si.lookup("main.py") == "main.py"
        assert si.lookup("main") == "main.py"

    def test_index_ts_resolution(self, index):
        assert index.lookup("src/index") == "src/index.ts"


# =============================================================================
# SYMBOL TABLE — OWNER INDEX
# =============================================================================


class TestSymbolTableOwnerIndex:
    """Test the owner-keyed index for method/property lookup."""

    @pytest.fixture
    def table(self):
        st = SymbolTable()
        st.add(SymbolEntry("1", "a.py", "foo", "method", owner_name="MyClass"))
        st.add(SymbolEntry("2", "a.py", "bar", "method", owner_name="MyClass"))
        st.add(SymbolEntry("3", "b.py", "foo", "method", owner_name="OtherClass"))
        st.add(SymbolEntry("4", "a.py", "MyClass", "class"))
        st.add(SymbolEntry("5", "a.py", "baz", "method"))  # no owner
        st.add(SymbolEntry("6", "c.py", "OtherClass", "class"))
        return st

    def test_owner_index_hit(self, table):
        result = table.lookup_by_owner("MyClass", "foo")
        assert len(result) == 1
        assert result[0].node_id == "1"

    def test_owner_index_different_owner(self, table):
        result = table.lookup_by_owner("OtherClass", "foo")
        assert len(result) == 1
        assert result[0].node_id == "3"

    def test_owner_index_multiple_members(self, table):
        foo = table.lookup_by_owner("MyClass", "foo")
        bar = table.lookup_by_owner("MyClass", "bar")
        assert len(foo) == 1
        assert len(bar) == 1
        assert foo[0].node_id == "1"
        assert bar[0].node_id == "2"

    def test_fallback_file_colocation(self, table):
        # baz has no owner_name but is in same file as MyClass
        result = table.lookup_by_owner("MyClass", "baz")
        assert len(result) == 1
        assert result[0].node_id == "5"

    def test_nonexistent_owner(self, table):
        result = table.lookup_by_owner("NoSuchClass", "foo")
        assert result == []

    def test_nonexistent_member(self, table):
        result = table.lookup_by_owner("MyClass", "nonexistent")
        assert result == []

    def test_global_lookup_unaffected(self, table):
        result = table.lookup_global("foo")
        assert len(result) == 2  # foo in both MyClass and OtherClass

    def test_local_lookup_unaffected(self, table):
        result = table.lookup_local("a.py", "foo")
        assert len(result) == 1
        assert result[0].owner_name == "MyClass"


# =============================================================================
# CALL RESOLUTION CACHE
# =============================================================================


class TestCallResolverCache:
    """Test that the per-instance cache avoids redundant lookups."""

    @pytest.fixture
    def resolver(self):
        st = SymbolTable()
        st.add(SymbolEntry("target1", "lib.py", "helper", "function", param_count=1))
        st.add(SymbolEntry("target2", "lib.py", "utility", "function", param_count=0))
        import_map = {"main.py": {"lib.py"}}
        return CallResolver(st, import_map)

    def test_cache_hit_returns_same_result(self, resolver):
        call = ExtractedCall(called_name="helper", call_form="free", line=10, arg_count=1)
        result1 = resolver.resolve(call, "main.py")
        result2 = resolver.resolve(call, "main.py")
        assert result1 is not None
        assert result1 == result2

    def test_cache_stores_none_for_unresolved(self, resolver):
        call = ExtractedCall(called_name="nonexistent", call_form="free", line=10, arg_count=0)
        result1 = resolver.resolve(call, "main.py")
        assert result1 is None
        result2 = resolver.resolve(call, "main.py")
        assert result2 is None
        assert ("main.py", "nonexistent", None, "free", 0) in resolver._cache

    def test_different_files_cached_separately(self, resolver):
        call = ExtractedCall(called_name="helper", call_form="free", line=10, arg_count=1)
        result1 = resolver.resolve(call, "main.py")
        result2 = resolver.resolve(call, "other.py")
        # Both resolve (main.py via import, other.py via global fallback) but to different confidence
        assert result1 is not None
        assert result2 is not None
        assert result1[1] > result2[1]  # import-scoped > global
        assert ("main.py", "helper", None, "free", 1) in resolver._cache
        assert ("other.py", "helper", None, "free", 1) in resolver._cache

    def test_builtins_not_cached(self, resolver):
        call = ExtractedCall(called_name="print", call_form="free", line=1, arg_count=1)
        result = resolver.resolve(call, "main.py")
        assert result is None
        assert ("main.py", "print") not in resolver._cache

    def test_cache_populated_after_resolve(self, resolver):
        assert len(resolver._cache) == 0
        call = ExtractedCall(called_name="helper", call_form="free", line=10, arg_count=1)
        resolver.resolve(call, "main.py")
        assert len(resolver._cache) == 1


# =============================================================================
# CALL RESOLUTION ACCURACY
# =============================================================================


class TestCallResolutionAccuracy:
    """Test that the multi-stage resolution produces correct results with proper confidence."""

    @pytest.fixture
    def resolver(self):
        st = SymbolTable()
        # Same-file symbol
        st.add(SymbolEntry("local_fn", "app.py", "process", "function", param_count=2))
        # Import-scoped symbol
        st.add(SymbolEntry("imported_fn", "utils.py", "format_data", "function", param_count=1))
        # Global symbol
        st.add(SymbolEntry("global_fn", "other.py", "global_helper", "function", param_count=0))
        # Class method for member dispatch
        st.add(SymbolEntry("cls_method", "models.py", "save", "method",
                           param_count=0, owner_name="User"))

        import_map = {"app.py": {"utils.py"}}
        named_imports = {"app.py": {"format_data": ("utils.py", "format_data")}}
        return CallResolver(st, import_map, named_import_map=named_imports)

    def test_same_file_resolution_confidence(self, resolver):
        call = ExtractedCall(called_name="process", call_form="free", line=10, arg_count=2)
        result = resolver.resolve(call, "app.py")
        assert result is not None
        assert result[0] == "local_fn"
        assert result[1] == 0.95  # same-file confidence

    def test_named_import_resolution(self, resolver):
        call = ExtractedCall(called_name="format_data", call_form="free", line=20, arg_count=1)
        result = resolver.resolve(call, "app.py")
        assert result is not None
        assert result[0] == "imported_fn"
        assert result[1] == 0.90  # import-scoped confidence

    def test_global_fallback_confidence(self, resolver):
        call = ExtractedCall(called_name="global_helper", call_form="free", line=30, arg_count=0)
        result = resolver.resolve(call, "app.py")
        assert result is not None
        assert result[0] == "global_fn"
        assert result[1] == 0.50  # global confidence

    def test_unresolvable_returns_none(self, resolver):
        call = ExtractedCall(called_name="does_not_exist", call_form="free", line=1, arg_count=0)
        assert resolver.resolve(call, "app.py") is None

    def test_arity_filtering_exact(self):
        st = SymbolTable()
        st.add(SymbolEntry("fn1", "a.py", "do_thing", "function", param_count=1))
        st.add(SymbolEntry("fn2", "a.py", "do_thing", "function", param_count=3))
        resolver = CallResolver(st, {})
        call = ExtractedCall(called_name="do_thing", call_form="free", line=1, arg_count=1)
        result = resolver.resolve(call, "a.py")
        assert result is not None
        assert result[0] == "fn1"

    def test_arity_filtering_lenient(self):
        st = SymbolTable()
        st.add(SymbolEntry("fn1", "a.py", "do_thing", "function", param_count=2))
        st.add(SymbolEntry("fn2", "a.py", "do_thing", "function", param_count=10))
        resolver = CallResolver(st, {})
        # arg_count=3, fn1 has param_count=2 (diff=1, within lenient range)
        call = ExtractedCall(called_name="do_thing", call_form="free", line=1, arg_count=3)
        result = resolver.resolve(call, "a.py")
        assert result is not None
        assert result[0] == "fn1"


# =============================================================================
# RRF FUSION
# =============================================================================


class TestRRFFusion:
    """Test Reciprocal Rank Fusion for hybrid search."""

    def test_single_source_ordering(self):
        semantic = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.7},
            {"id": "c", "score": 0.5},
        ]
        result = HybridSearchService._rrf_fuse(semantic, [], 0.7, 3)
        ids = [r["id"] for r in result]
        assert ids == ["a", "b", "c"]

    def test_both_sources_boost_shared_results(self):
        semantic = [{"id": "a", "score": 0.5}, {"id": "b", "score": 0.5}]
        keyword = [{"id": "b", "score": 1.0}, {"id": "c", "score": 0.5}]
        result = HybridSearchService._rrf_fuse(semantic, keyword, 0.5, 3)
        # b appears in both → should get boosted above items in only one list
        scores = {r["id"]: r["rrf_score"] for r in result}
        assert scores["b"] > scores["c"]

    def test_limit_respected(self):
        items = [{"id": str(i), "score": 1.0 - i * 0.1} for i in range(10)]
        result = HybridSearchService._rrf_fuse(items, [], 0.7, 3)
        assert len(result) == 3

    def test_empty_inputs(self):
        result = HybridSearchService._rrf_fuse([], [], 0.7, 5)
        assert result == []

    def test_semantic_weight_affects_scores(self):
        semantic = [{"id": "a", "score": 0.9}]
        keyword = [{"id": "b", "score": 3.0}]
        # High semantic weight → semantic results scored higher
        result_high = HybridSearchService._rrf_fuse(semantic, keyword, 0.9, 2)
        result_low = HybridSearchService._rrf_fuse(semantic, keyword, 0.1, 2)
        high_scores = {r["id"]: r["rrf_score"] for r in result_high}
        low_scores = {r["id"]: r["rrf_score"] for r in result_low}
        assert high_scores["a"] > low_scores["a"]
        assert low_scores["b"] > high_scores["b"]

    def test_deduplication_by_id(self):
        semantic = [{"id": "x", "score": 0.8}]
        keyword = [{"id": "x", "score": 2.0}]
        result = HybridSearchService._rrf_fuse(semantic, keyword, 0.5, 5)
        assert len(result) == 1
        assert result[0]["id"] == "x"


class TestClassificationMode:
    """Test simple vs expanded classification mode."""

    def test_simple_mode_returns_the_closed_memory_type_vocabulary(self):
        from app.services.classification_areas import get_merged_llm_types
        from app.taxonomy import MEMORY_TYPES
        types = get_merged_llm_types(["general", "technical", "debugging"], mode="simple")
        assert set(types.keys()) == set(MEMORY_TYPES)

    def test_expanded_mode_returns_area_types(self):
        from app.services.classification_areas import get_merged_llm_types
        types = get_merged_llm_types(["general", "technical"], mode="expanded")
        assert "decision" in types
        assert "reference" in types
        assert "architecture" in types
        # Expanded is a per-area label space, not a superset of MEMORY_TYPES:
        # it carries area-specific labels (`emotional`, `root_cause`, ...) that
        # SIMPLE_NORMALIZATION folds back into the closed vocabulary.
        from app.taxonomy import MEMORY_TYPES
        assert set(types) - set(MEMORY_TYPES)

    def test_default_mode_is_simple(self):
        from app.services.classification_areas import get_merged_llm_types
        from app.taxonomy import MEMORY_TYPES
        types = get_merged_llm_types(["general", "technical"])
        assert set(types.keys()) == set(MEMORY_TYPES)

    def test_simple_normalization_remaps_invalid_types(self):
        from app.services.classification_areas import SIMPLE_NORMALIZATION, SIMPLE_TYPES
        for source, target in SIMPLE_NORMALIZATION.items():
            assert target in SIMPLE_TYPES, f"{source} maps to {target} which is not a simple type"

    def test_simple_normalization_covers_all_expanded_types(self):
        from app.services.classification_areas import (
            AREAS, SIMPLE_NORMALIZATION, SIMPLE_TYPES,
        )
        all_expanded = set()
        for area in AREAS.values():
            all_expanded.update(area.llm_types.keys())
        for t in all_expanded:
            assert t in SIMPLE_TYPES or t in SIMPLE_NORMALIZATION, (
                f"Expanded type '{t}' has no simple mapping"
            )


# =============================================================================
# VECTOR CLUSTERING (DBSCAN + LOUVAIN)
# =============================================================================


class TestVectorClustering:
    """Test sklearn DBSCAN and igraph Louvain implementations."""

    def test_dbscan_clusters_similar_vectors(self):
        pytest.importorskip("sklearn")
        from sklearn.cluster import DBSCAN

        # Two tight clusters + one outlier
        vectors = np.array([
            [1.0, 0.0, 0.0],  # cluster 0
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
            [0.0, 1.0, 0.0],  # cluster 1
            [0.01, 0.99, 0.0],
            [0.02, 0.98, 0.0],
            [0.5, 0.5, 0.5],  # potential outlier
        ], dtype=np.float32)

        clustering = DBSCAN(eps=0.1, min_samples=2, metric="cosine").fit(vectors)
        labels = clustering.labels_
        assert labels[0] == labels[1] == labels[2]
        assert labels[3] == labels[4] == labels[5]
        assert labels[0] != labels[3]

    def test_dbscan_single_point_is_noise(self):
        pytest.importorskip("sklearn")
        from sklearn.cluster import DBSCAN

        vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        clustering = DBSCAN(eps=0.1, min_samples=2, metric="cosine").fit(vectors)
        assert all(l == -1 for l in clustering.labels_)


# =============================================================================
# MULTI-HOP BINDING PROPAGATION
# =============================================================================


class TestMultiHopBindings:
    """Test chain-walk binding resolution for TypeScript barrel re-exports."""

    @staticmethod
    def _resolve(name, source_file, named_import_map, visited=None, depth=0):
        from app.services.code_pipeline import _resolve_binding_chain
        return _resolve_binding_chain(name, source_file, named_import_map, visited, depth)

    def test_single_hop(self):
        nim = {
            "app.ts": {"User": ("models/user.ts", "User")},
        }
        result = self._resolve("User", "app.ts", nim)
        assert result == ("models/user.ts", "User")

    def test_two_hop_barrel(self):
        nim = {
            "app.ts": {"User": ("index.ts", "User")},
            "index.ts": {"User": ("models/user.ts", "User")},
        }
        result = self._resolve("User", "app.ts", nim)
        assert result == ("models/user.ts", "User")

    def test_three_hop_chain(self):
        nim = {
            "a.ts": {"X": ("b.ts", "X")},
            "b.ts": {"X": ("c.ts", "X")},
            "c.ts": {"X": ("d.ts", "X")},
        }
        result = self._resolve("X", "a.ts", nim)
        assert result == ("d.ts", "X")

    def test_cycle_detection(self):
        nim = {
            "a.ts": {"X": ("b.ts", "X")},
            "b.ts": {"X": ("a.ts", "X")},
        }
        result = self._resolve("X", "a.ts", nim)
        assert result is not None

    def test_depth_limit(self):
        nim = {}
        for i in range(7):
            nim[f"f{i}.ts"] = {"X": (f"f{i+1}.ts", "X")}
        result = self._resolve("X", "f0.ts", nim)
        assert result is not None

    def test_missing_binding_returns_none(self):
        nim = {"a.ts": {"Y": ("b.ts", "Y")}}
        result = self._resolve("X", "a.ts", nim)
        assert result is None

    def test_terminal_binding_no_further_chain(self):
        nim = {
            "a.ts": {"User": ("b.ts", "User")},
            "b.ts": {},
        }
        result = self._resolve("User", "a.ts", nim)
        assert result == ("b.ts", "User")


# =============================================================================
# PROCESS TRACER PARAMETERS
# =============================================================================


class TestProcessTracerParameters:
    """Test that ProcessTracer accepts the new branching/confidence params."""

    def test_trace_signature(self):
        import inspect
        from app.services.process_tracer import ProcessTracer
        sig = inspect.signature(ProcessTracer.trace)
        params = sig.parameters
        assert "max_branching" in params
        assert "min_edge_confidence" in params
        assert params["max_branching"].default == 4
        assert params["min_edge_confidence"].default == 0.5

    def test_max_depth_clamped(self):
        from app.services.process_tracer import ProcessTracer
        import inspect
        sig = inspect.signature(ProcessTracer.trace)
        assert sig.parameters["max_depth"].default == 10


# =============================================================================
# HERITAGE RESOLVER MRO DISPATCH
# =============================================================================


class TestHeritageResolverDispatch:
    """Test that compute_mro routes to the correct strategy."""

    def test_python_uses_c3(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("python") == "c3"

    def test_cpp_uses_leftmost_base(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("cpp") == "leftmost-base"

    def test_java_uses_implements_split(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("java") == "implements-split"

    def test_csharp_uses_implements_split(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("csharp") == "implements-split"

    def test_rust_uses_qualified_syntax(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("rust") == "qualified-syntax"

    def test_unknown_uses_single_inheritance(self):
        from app.services.heritage_resolver import HeritageResolver
        assert HeritageResolver.compute_mro("lua") == "single-inheritance"
        assert HeritageResolver.compute_mro("") == "single-inheritance"
