from collections import defaultdict, Counter

from app.repositories.relational import PostgresMemoryRepository


# ── Internal helpers ──────────────────────────────────────────────────────

async def _load_room_data(repo: PostgresMemoryRepository) -> dict[str, dict]:
    rows = await repo.get_palace_room_data()

    room_data: dict[str, dict] = defaultdict(
        lambda: {"wings": set(), "halls": set(), "count": 0, "dates": set()}
    )
    for r in rows:
        room = r["room"]
        room_data[room]["wings"].add(r["wing"])
        if r["hall"]:
            room_data[room]["halls"].add(r["hall"])
        if r["date"]:
            room_data[room]["dates"].add(str(r["date"]))
        room_data[room]["count"] += 1

    return room_data


def _build_edges(room_data: dict[str, dict]) -> list[dict]:
    edges: list[dict] = []
    for room, data in room_data.items():
        wings = sorted(data["wings"])
        if len(wings) < 2:
            continue
        for i, wing_a in enumerate(wings):
            for wing_b in wings[i + 1:]:
                halls = data["halls"] or {""}
                for hall in halls:
                    edges.append({
                        "room": room,
                        "wing_a": wing_a,
                        "wing_b": wing_b,
                        "hall": hall,
                        "count": data["count"],
                    })
    return edges


def _serialize_room_data(room_data: dict[str, dict]) -> dict[str, dict]:
    return {
        room: {
            "wings": sorted(data["wings"]),
            "halls": sorted(data["halls"]),
            "count": data["count"],
            "dates": sorted(data["dates"])[-5:] if data["dates"] else [],
        }
        for room, data in room_data.items()
    }


# ── Public API ────────────────────────────────────────────────────────────

async def build_graph(repo: PostgresMemoryRepository) -> dict:
    room_data = await _load_room_data(repo)
    return {
        "nodes": _serialize_room_data(room_data),
        "edges": _build_edges(room_data),
    }


async def traverse(
    repo: PostgresMemoryRepository,
    start_room: str,
    max_hops: int = 3,
) -> list[dict]:
    room_data = await _load_room_data(repo)
    nodes = _serialize_room_data(room_data)

    if start_room not in nodes:
        candidates = _fuzzy_match(start_room, nodes)
        return [{"error": f"Room '{start_room}' not found", "suggestions": candidates}]

    visited: set[str] = {start_room}
    results: list[dict] = [{
        "room": start_room,
        "wings": nodes[start_room]["wings"],
        "halls": nodes[start_room]["halls"],
        "count": nodes[start_room]["count"],
        "hop": 0,
    }]

    frontier: list[tuple[str, int]] = [(start_room, 0)]
    while frontier:
        current_room, depth = frontier.pop(0)
        if depth >= max_hops:
            continue

        current_wings = set(nodes.get(current_room, {}).get("wings", []))

        for room, data in nodes.items():
            if room in visited:
                continue
            shared = current_wings & set(data["wings"])
            if not shared:
                continue
            visited.add(room)
            results.append({
                "room": room,
                "wings": data["wings"],
                "halls": data["halls"],
                "count": data["count"],
                "hop": depth + 1,
                "connected_via": sorted(shared),
            })
            if depth + 1 < max_hops:
                frontier.append((room, depth + 1))

    results.sort(key=lambda x: (x["hop"], -x["count"]))
    return results[:50]


async def find_tunnels(
    repo: PostgresMemoryRepository,
    wing_a: str | None = None,
    wing_b: str | None = None,
) -> list[dict]:
    room_data = await _load_room_data(repo)
    nodes = _serialize_room_data(room_data)

    tunnels: list[dict] = []
    for room, data in nodes.items():
        wings = data["wings"]
        if len(wings) < 2:
            continue
        if wing_a and wing_a not in wings:
            continue
        if wing_b and wing_b not in wings:
            continue
        tunnels.append({
            "room": room,
            "wings": wings,
            "halls": data["halls"],
            "count": data["count"],
            "recent": data["dates"][-1] if data["dates"] else "",
        })

    tunnels.sort(key=lambda x: -x["count"])
    return tunnels[:50]


async def graph_stats(repo: PostgresMemoryRepository) -> dict:
    room_data = await _load_room_data(repo)
    nodes = _serialize_room_data(room_data)
    edges = _build_edges(room_data)

    tunnel_count = sum(1 for d in nodes.values() if len(d["wings"]) >= 2)
    wing_counts: Counter = Counter()
    for data in nodes.values():
        for wing in data["wings"]:
            wing_counts[wing] += 1

    top_tunnels = [
        {"room": room, "wings": data["wings"], "count": data["count"]}
        for room, data in sorted(nodes.items(), key=lambda x: -len(x[1]["wings"]))[:10]
        if len(data["wings"]) >= 2
    ]

    return {
        "total_rooms": len(nodes),
        "tunnel_rooms": tunnel_count,
        "total_edges": len(edges),
        "wing_count": len(wing_counts),
        "rooms_per_wing": dict(wing_counts.most_common()),
        "top_tunnels": top_tunnels,
    }


# ── Fuzzy match helper ────────────────────────────────────────────────────

def _fuzzy_match(query: str, nodes: dict, n: int = 5) -> list[str]:
    query_lower = query.lower()
    scored: list[tuple[str, float]] = []
    for room in nodes:
        if query_lower in room:
            scored.append((room, 1.0))
        elif any(word in room for word in query_lower.split("-")):
            scored.append((room, 0.5))
    scored.sort(key=lambda x: -x[1])
    return [r for r, _ in scored[:n]]
