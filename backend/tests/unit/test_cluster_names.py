from app.utils.cluster_names import MAX_NAME_CHARS, name_clusters


class View:
    def __init__(self):
        self.members: dict[int, list[str]] = {}
        self.tags: dict[str, list[str]] = {}
        self.projects: dict[str, str | None] = {}
        self.entity_terms: dict[str, set[str]] = {}
        self._next = 0

    def add(self, cluster, project, tags=(), entities=()):
        mid = f"m{self._next}"
        self._next += 1
        if cluster is not None:
            self.members.setdefault(cluster, []).append(mid)
        self.projects[mid] = project
        self.tags[mid] = list(tags)
        if entities:
            self.entity_terms[mid] = set(entities)
        return mid

    def names(self):
        return name_clusters(self.members, self.tags, self.projects, self.entity_terms)


def test_default_project_reads_its_project_tag():
    v = View()
    for project_tags in (
        ["project/darkfoto"],
        ["project/darkfoto"],
        ["project/darkfoto", "project/other"],
        ["project/other"],
    ):
        v.add(0, "default", [*project_tags, "gpu"])
    for _ in range(3):
        v.add(1, "darkcloud")
    names = v.names()
    assert names["0"] == "darkfoto · gpu"
    assert names["1"] == "darkcloud"


def test_prefix_needs_sixty_percent():
    v = View()
    for project in ("alpha", "alpha", "alpha", "beta", "beta"):
        v.add(0, project, ["t0"])
    for project in ("alpha", "alpha", "beta", "beta"):
        v.add(1, project, ["t1"])
    for _ in range(4):
        v.add(2, "default", ["t2"])
    assert v.names() == {"0": "alpha · t0", "1": "t1", "2": "t2"}


def test_single_project_view_has_no_prefix_and_skips_its_project():
    v = View()
    for _ in range(3):
        v.add(0, "darkmem", ["darkmem", "schema"])
    for _ in range(3):
        v.add(1, "darkmem", ["darkmem", "judge"])
    assert v.names() == {"0": "schema", "1": "judge"}


def test_excluded_terms_never_appear():
    v = View()
    for i in range(5):
        tags = ["decision"]
        if i == 0:
            tags.append("lonely")
        if i < 3:
            tags.append("keep")
        v.add(0, "alpha", tags, entities={"alpha"})
    for _ in range(3):
        v.add(1, "beta")
    assert v.names()["0"] == "alpha · keep"


def test_large_cluster_in_small_view_keeps_its_term():
    v = View()
    for _ in range(4):
        v.add(0, "darkload", ["gdrive"])
    for _ in range(2):
        v.add(None, "darkload")
    assert v.names()["0"] == "gdrive"


def _a9_view(with_nodegraph: bool = True) -> View:
    v = View()
    cluster_tags = [
        ["claude code", "dispose", "nodegraph"],
        ["claude code", "dispose", "nodegraph"],
        ["claude code", "dispose", "disposal", "node-graph"],
        ["claude-code", "disposal", "node-graph"],
    ]
    for project, tags in zip(("alpha", "alpha", "beta", "beta"), cluster_tags):
        if not with_nodegraph:
            tags = [t for t in tags if t not in ("nodegraph", "node-graph")]
        v.add(0, project, tags)
    for _ in range(4):
        v.add(1, "gamma", ["other"])
    return v


def test_spellings_fold_and_near_duplicates_skip():
    assert _a9_view().names()["0"] == "claude code · node-graph · dispose"
    assert _a9_view(with_nodegraph=False).names()["0"] == "claude code · dispose"


def test_long_terms_drop_whole():
    def view(project, term_counts):
        v = View()
        for i in range(5):
            v.add(0, project, [term for term, count in term_counts if i < count])
        for _ in range(3):
            v.add(1, "beta", ["other"])
        return v.names()["0"]

    first = view(
        "darkraise-ai-plugins",
        [("dr-superpowers", 5), ("review-routing", 4), ("planning", 3)],
    )
    assert first == "darkraise-ai-plugins · dr-superpowers"
    assert len(first) == 37

    long_project = "p" * 38
    second = view(long_project, [("ten-chars!", 5)])
    assert second == f"{long_project} · ten-chars!"
    assert len(second) == 51

    third = view(
        "alpha",
        [("dr-superpowers", 5), ("release-orchestrator", 4), ("api", 3)],
    )
    assert third == "alpha · dr-superpowers"


def test_long_terms_are_not_terms():
    v = View()
    for project in ("p1", "p2", "p3"):
        v.add(0, project, ["a" * 31, "b" * 30])
    assert v.names()["0"] == "b" * 30


def test_score_uses_mean_cluster_size():
    v = View()
    for i, project in enumerate(("p1", "p2", "p3", "p4")):
        v.add(0, project, ["widget", "gizmo"] if i < 2 else ["widget"])
    for project in ("p5", "p6"):
        v.add(1, project, ["other"])
    for i in range(20):
        v.add(None, f"q{i}", ["widget"] if i < 4 else [])
    assert v.names()["0"] == "gizmo · widget"


def test_unnamed_cluster_falls_back():
    v = View()
    for project, tag in (("p1", "x"), ("p2", "y"), ("p3", "z")):
        v.add(7, project, [tag])
    names = v.names()
    assert names == {"7": "Cluster 7"}
    assert all(names[str(cluster)] for cluster in v.members)


def test_entity_terms_count_as_terms():
    v = View()
    for project in ("p1", "p2", "p3"):
        v.add(0, project, entities={"darkfoto"})
    assert v.names()["0"] == "darkfoto"


def test_names_are_deterministic():
    v = _a9_view()
    first = v.names()

    def reversed_dict(d):
        return dict(reversed(list(d.items())))

    members = reversed_dict({c: list(reversed(m)) for c, m in v.members.items()})
    second = name_clusters(
        members,
        reversed_dict({k: list(reversed(t)) for k, t in v.tags.items()}),
        reversed_dict(v.projects),
        reversed_dict(v.entity_terms),
    )
    assert second == first


def test_two_clusters_never_share_a_name():
    v = View()
    for cluster in (7, 3):
        for _ in range(3):
            v.add(cluster, "alpha", ["gpu"])
    assert v.names() == {"3": "gpu", "7": "gpu 2"}

    for _ in range(3):
        v.add(9, "alpha", ["gpu"])
    assert v.names() == {"3": "gpu", "7": "gpu 2", "9": "gpu 3"}

    long = View()
    for cluster in (0, 1):
        for _ in range(3):
            long.add(cluster, "longprojectname-abcde", ["abcdefghijklmnop"])
    for _ in range(3):
        long.add(2, "other", ["zzz"])
    names = long.names()
    assert len(names["0"]) == MAX_NAME_CHARS
    assert names["1"] == names["0"] + " 2"


def test_term_inside_the_prefix_is_skipped():
    v = View()
    for _ in range(3):
        v.add(0, "darkraise-ai-plugins", ["plugins", "routing"])
    for _ in range(3):
        v.add(1, "other", ["zzz"])
    assert v.names()["0"] == "darkraise-ai-plugins · routing"
