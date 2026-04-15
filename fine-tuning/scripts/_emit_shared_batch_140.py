"""One-off emitter for shared-base batch-140 — ai_coding domain (game programming patterns in code: ECS, netcode, determinism, save/load, scripting, state machines).

Writes 50 rows to data/v2/shared/batch_140.tmp.jsonl with ids shared-06951..07000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_140.tmp.jsonl"
ID_OFFSET = 6950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the enemy-actor hierarchy to bevy_ecs archetypes; the old deep inheritance tree that chained Character to Actor to Entity got replaced by plain component bundles.", "architecture", "ai_coding", False,
     [("bevy_ecs", "library"), ("archetypes", "pattern"), ("component bundles", "pattern")],
     [("bevy_ecs", "archetypes", "USES")],
     "which ECS library replaced the deep enemy-actor inheritance tree and what pattern did it adopt",
     "bevy ecs archetype component bundle replace inheritance hierarchy"),
    # --- 2 ---
    ("Switched the simulation from flecs queries to EnTT views in the native client; the hot-path iteration sheds a layer of indirection and profiles clean on PS5 hardware.", "decision", "ai_coding", False,
     [("flecs", "library"), ("EnTT", "library"), ("PS5", "platform")],
     [("EnTT", "flecs", "REPLACES")],
     "which ECS library swap did the native client adopt for hot-path iteration on console",
     "entt flecs view query native client ps5 hot path iteration swap"),
    # --- 3 ---
    ("Unity DOTS Burst jobs now drive the crowd-simulation step; the managed MonoBehaviour path survived only for editor tooling and gets stripped from shipping builds.", "milestone", "ai_coding", False,
     [("Unity DOTS", "library"), ("Burst", "tool"), ("MonoBehaviour", "pattern")],
     [("Unity DOTS", "MonoBehaviour", "REPLACES")],
     "which Unity runtime stack replaced MonoBehaviour for the shipping crowd-simulation step",
     "unity dots burst job crowd simulation monobehaviour strip ship"),
    # --- 4 ---
    ("Component composition replaced the old Humanoid subclass: Health, Inventory, and Movement are separate components added to an entity id instead of baked into a base class.", "architecture", "ai_coding", False,
     [("Humanoid", "pattern"), ("Health", "pattern"), ("Inventory", "pattern"), ("Movement", "pattern")],
     [("Health", "Humanoid", "REPLACES")],
     "how did the entity model move from a Humanoid subclass to plain component composition",
     "composition over inheritance health inventory movement component entity"),
    # --- 5 ---
    ("Fixed the variable-step physics jitter by pinning simulation to a 60 Hz fixed step with an accumulator; rendering interpolates between the last two ticks for visual smoothness.", "problem", "ai_coding", False,
     [("variable-step", "pattern"), ("fixed step", "pattern"), ("accumulator", "pattern"), ("60 Hz", "config")],
     [("fixed step", "variable-step", "IMPROVES_ON")],
     "how did the physics jitter get fixed without dropping visual smoothness in the renderer",
     "fixed step accumulator variable physics interpolation render tick"),
    # --- 6 ---
    ("The fighting-game netcode migrated from lockstep to GGPO-style rollback; one-frame input-delay dropped to zero and long-distance matches are now actually playable.", "decision", "ai_coding", False,
     [("GGPO", "framework"), ("lockstep", "pattern"), ("rollback", "pattern")],
     [("rollback", "lockstep", "REPLACES")],
     "which netcode model replaced lockstep for the fighting game and what latency win did it unlock",
     "ggpo rollback netcode lockstep fighting game input delay frame"),
    # --- 7 ---
    ("Replay determinism broke on Ryzen boxes: an FMA contraction in the trig table produced a one-ulp drift per frame that compounded into desyncs within ninety seconds.", "problem", "ai_coding", False,
     [("FMA", "pattern"), ("Ryzen", "platform"), ("trig table", "pattern")],
     [],
     "which CPU-level numeric feature caused the replay desync on Ryzen builds and how fast did it compound",
     "fma contraction determinism ulp drift ryzen replay desync trig"),
    # --- 8 ---
    ("Save files carry a versioned schema header; a migration chain runs on load so a v3 save can be read into a v7 world without a one-off converter per release.", "architecture", "ai_coding", False,
     [("versioned schema", "pattern"), ("migration chain", "pattern")],
     [],
     "how does the save system handle players loading old files into a newer build without bespoke converters",
     "save schema version migration chain upgrade load backward compat"),
    # --- 9 ---
    ("Serialised game state uses FlatBuffers for the in-memory snapshot and Cap'n Proto for the over-the-wire diff; the save path reverts to Protobuf for the settings blob while JSON survives only in dev-build dumps and the telemetry payload.", "architecture", "ai_coding", False,
     [("FlatBuffers", "library"), ("Cap'n Proto", "library"), ("Protobuf", "library"), ("JSON", "technology"), ("telemetry", "service"), ("settings blob", "pattern")],
     [("FlatBuffers", "JSON", "REPLACES"), ("Cap'n Proto", "telemetry", "APPLIES_TO")],
     "which binary serialisation formats did the game pick for snapshots versus wire diffs",
     "flatbuffers capn proto protobuf serialisation snapshot wire telemetry"),
    # --- 10. noise ---
    ("The studio lobby's fish tank sprang a slow leak and someone drew a chalk outline of the puddle each morning.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Scene management switched from a singleton SceneManager to a stack of scene ids with per-scene ECS worlds; unloading a scene drops its world in one call and leaks nothing.", "architecture", "ai_coding", False,
     [("SceneManager", "pattern"), ("stack of scene ids", "pattern"), ("per-scene ECS", "pattern")],
     [("stack of scene ids", "SceneManager", "REPLACES")],
     "which scene-management pattern replaced the singleton SceneManager and how does unload avoid leaks",
     "scene stack manager ecs world unload leak singleton replace"),
    # --- 12 ---
    ("Update-order bug on the pickup system: Inventory ran before Collision, so players sometimes walked through a coin without grabbing it; a system ordering constraint fixed it.", "problem", "ai_coding", False,
     [("Inventory", "pattern"), ("Collision", "pattern"), ("system ordering", "pattern")],
     [],
     "which update-order bug caused players to miss coin pickups and how was the ordering pinned",
     "update order system inventory collision pickup coin constraint"),
    # --- 13 ---
    ("Embedded sol2 as the Lua binding layer for quest scripts; the earlier raw lua_State binding was too easy to misuse and one typo corrupted the registry index on shipping builds.", "decision", "ai_coding", False,
     [("sol2", "library"), ("Lua", "language"), ("lua_State", "method")],
     [("sol2", "lua_State", "REPLACES")],
     "which Lua binding layer replaced raw lua_State in quest scripting and why",
     "sol2 lua binding quest script lua_state registry typo crash"),
    # --- 14 ---
    ("Mono hosts the C# mod layer; the runtime is pinned to a curated appdomain and mods load into a sandbox that denies System.IO outside the mods/ folder.", "architecture", "ai_coding", False,
     [("Mono", "framework"), ("C#", "language"), ("appdomain", "pattern"), ("System.IO", "api")],
     [],
     "how does the C# mod layer sandbox filesystem access while hosting Mono in-process",
     "mono csharp mod appdomain sandbox system io mods folder deny"),
    # --- 15 ---
    ("Picked Wren over Squirrel for the cutscene DSL; the small VM footprint and fiber-per-cutscene model made pause and resume trivial without a custom coroutine layer.", "decision", "ai_coding", False,
     [("Wren", "language"), ("Squirrel", "language"), ("fiber", "pattern")],
     [("Wren", "Squirrel", "PREFERS")],
     "which scripting language won the cutscene DSL bake-off and which feature sealed the choice",
     "wren squirrel fiber cutscene dsl pause resume small vm scripting"),
    # --- 16 ---
    ("AngelScript drives the boss-fight choreography; hot-reload of script modules in the dev build lets designers iterate without restarting the level or losing boss phase state.", "fact", "ai_coding", False,
     [("AngelScript", "language"), ("hot-reload", "pattern"), ("boss-fight", "pattern")],
     [],
     "which scripting language handles boss-fight choreography and what designer workflow does hot-reload unlock",
     "angelscript hot reload boss fight choreography designer iterate"),
    # --- 17 ---
    ("Asset pipeline has importer hooks per extension: a .fbx hook retopologises into the engine mesh format and writes a sidecar .meta with the source hash for cache invalidation.", "architecture", "ai_coding", False,
     [("importer hook", "pattern"), (".fbx", "file"), (".meta", "file")],
     [],
     "how does the asset pipeline invalidate caches when a source fbx file changes on disk",
     "asset importer hook fbx meta sidecar source hash cache invalidate"),
    # --- 18 ---
    ("Hot-reload of shader assets ships with a registry watch: edit a .hlsl, a file-change event queues a reload on the render thread, and materials rebind automatically on the next frame.", "fact", "ai_coding", False,
     [("Hot-reload", "pattern"), (".hlsl", "file"), ("render thread", "pattern")],
     [],
     "how does shader hot-reload route a file-change event into a material rebind without a full restart",
     "shader hot reload hlsl file watch render thread material rebind"),
    # --- 19 ---
    ("Input mapping sits in a two-layer indirection: raw device events feed into abstract actions, and game systems subscribe to actions rather than hardware keys; remapping touches data only.", "architecture", "ai_coding", False,
     [("Input mapping", "pattern"), ("abstract actions", "pattern")],
     [],
     "which indirection lets the input system remap controls without touching gameplay code paths",
     "input mapping abstract action device event remap indirection data"),
    # --- 20 ---
    ("Localisation went from gettext .po files to ICU MessageFormat strings; plural and gender rules that used to live in engine code now come from the translator bundle directly.", "decision", "ai_coding", False,
     [("gettext", "tool"), ("ICU", "library"), ("MessageFormat", "protocol")],
     [("ICU", "gettext", "REPLACES")],
     "which localisation stack replaced gettext and what plural and gender logic did it pull out of code",
     "icu message format gettext plural gender translator bundle po"),
    # --- 21 ---
    ("Quest-flag state machine uses an HFSM with sub-states under each Act; the old flat flag list had thousands of booleans and we hit cross-cutting ordering bugs every patch.", "problem", "ai_coding", False,
     [("HFSM", "pattern"), ("Quest-flag", "pattern"), ("flat flag list", "pattern")],
     [("HFSM", "flat flag list", "REPLACES")],
     "which state-machine flavour replaced the flat quest-flag list and which class of bug did it retire",
     "hfsm hierarchical state machine quest flag act ordering bug flat"),
    # --- 22 ---
    ("Behaviour trees drive the NPC AI now; the old goto-guard-goto FSM couldn't express interruptible fallbacks, so a simple Selector root cleaned up ninety percent of the edge cases.", "decision", "ai_coding", False,
     [("Behaviour trees", "pattern"), ("FSM", "pattern"), ("Selector", "pattern"), ("NPC AI", "pattern")],
     [("Behaviour trees", "FSM", "REPLACES")],
     "which AI pattern replaced the FSM for NPC control and what feature of it handled interruptible fallbacks",
     "behaviour tree fsm npc selector fallback interrupt edge case"),
    # --- 23 ---
    ("GOAP is layered on top of the behaviour-tree fallback in the stealth game; planner computes a sequence of actions and the BT executes them, so ad-hoc subgoals stop hard-coding paths.", "architecture", "ai_coding", False,
     [("GOAP", "pattern"), ("behaviour-tree", "pattern"), ("planner", "pattern")],
     [],
     "how is GOAP layered with the behaviour tree to plan and execute NPC actions in the stealth game",
     "goap planner behaviour tree stealth subgoal action sequence layer"),
    # --- 24 ---
    ("The utility-AI scorer shipped in the companion system weights threats, ammo, and health into a single float per tick; designers tune the weights in a CSV without recompiling.", "fact", "ai_coding", False,
     [("utility-AI", "pattern"), ("companion system", "project"), ("CSV", "technology")],
     [],
     "which AI scoring pattern lets designers tune companion behaviour without a recompile",
     "utility ai scorer companion weight csv tune no recompile float"),
    # --- 25 ---
    ("Save-corruption triage for the v3.1 patch traced to a mid-write crash when the platform suspended the process; the atomic write pattern now goes to a .tmp and renames on flush.", "problem", "ai_coding", False,
     [("Save-corruption", "pattern"), ("atomic write", "pattern"), ("v3.1", "date")],
     [("atomic write", "Save-corruption", "FIXES")],
     "which write pattern did we adopt after a v3.1 suspend-mid-write bug left player saves corrupted",
     "save corruption atomic write tmp rename suspend mid write v3 1"),
    # --- 26 ---
    ("Replay files store an initial seed, the fixed-step tick rate, and a compressed input stream; the sim replays deterministically as long as game logic avoids wall-clock reads.", "architecture", "ai_coding", False,
     [("replay", "pattern"), ("seed", "pattern"), ("input stream", "pattern")],
     [],
     "which three pieces of data make replays deterministic and which anti-pattern breaks them",
     "replay seed tick rate input stream deterministic wall clock avoid"),
    # --- 27 ---
    ("Deterministic RNG is a xoshiro256** stream seeded per match; std::mt19937 was dropped because stepping state across platforms disagreed on one sub-sequence boundary.", "decision", "ai_coding", False,
     [("xoshiro256**", "algorithm"), ("std::mt19937", "algorithm"), ("RNG", "concept")],
     [("xoshiro256**", "std::mt19937", "REPLACES")],
     "which deterministic RNG replaced std::mt19937 and what platform disagreement forced the change",
     "xoshiro mt19937 rng deterministic seed per match platform drift"),
    # --- 28 ---
    ("Event queue between systems is a lock-free SPSC ring per pair; contention on the old global bus was showing up as cache-line bouncing in the profiler on the 8-core build.", "problem", "ai_coding", False,
     [("SPSC ring", "pattern"), ("Event queue", "pattern"), ("global bus", "pattern")],
     [("SPSC ring", "global bus", "REPLACES")],
     "which inter-system event plumbing replaced the global bus and what profiler signal drove the change",
     "spsc ring event queue lock free global bus cache line bounce"),
    # --- 29 ---
    ("Delta snapshots over the wire use a bitmask per component indicating changed fields; the full-snapshot path survives only as the cold join-in-progress fallback for new peers.", "architecture", "ai_coding", False,
     [("Delta snapshots", "pattern"), ("bitmask", "pattern"), ("join-in-progress", "pattern")],
     [],
     "how does the netcode limit bandwidth with delta snapshots while still supporting cold joiners",
     "delta snapshot bitmask join in progress netcode bandwidth full"),
    # --- 30 ---
    ("The authoritative server reconciles client-predicted positions each tick over UDP; a mispredict rewinds the local player to the server state and replays local input up to the present.", "architecture", "ai_coding", False,
     [("authoritative server", "pattern"), ("client-predicted", "pattern"), ("UDP", "protocol"), ("mispredict", "pattern")],
     [],
     "which client-side prediction pattern does the netcode use and how does it handle a mispredict",
     "authoritative server client prediction reconcile rewind replay mispredict"),
    # --- 31 ---
    ("Anti-cheat for competitive is server-side sim validation; the classic client-trusted kill report got retired after a speed-hack wave that ignored movement extents entirely.", "problem", "ai_coding", False,
     [("Anti-cheat", "pattern"), ("server-side sim", "pattern"), ("client-trusted", "pattern"), ("speed-hack", "pattern")],
     [("server-side sim", "client-trusted", "REPLACES")],
     "which anti-cheat strategy replaced client-trusted kill reports after the speed-hack wave",
     "anti cheat server sim validation client trust kill report speed"),
    # --- 32 ---
    ("Asset bundle manifests are versioned JSON and loaded with a checksum gate; a mismatched checksum quarantines the bundle so the next frame falls back to the previous patch's assets.", "architecture", "ai_coding", False,
     [("Asset bundle", "pattern"), ("manifest", "pattern"), ("checksum", "concept")],
     [],
     "how does the asset bundle loader reject tampered or truncated bundles at runtime",
     "asset bundle manifest checksum gate quarantine fallback patch"),
    # --- 33 ---
    ("The entity id is a 64-bit handle: 32 bits index, 24 bits generation, 8 bits type tag; reusing a slot bumps the generation so a stale handle reads as dead on dereference.", "architecture", "ai_coding", False,
     [("entity id", "concept"), ("generation", "pattern"), ("handle", "pattern")],
     [],
     "which 64-bit handle layout does the ECS use and how does it invalidate stale references",
     "entity id generation index handle stale reuse type tag 64 bit"),
    # --- 34 ---
    ("Animation state machine is layered: a Locomotion layer blends base motion while an Additive layer plays combat reactions; the old single-graph approach stalled jump recoveries.", "decision", "ai_coding", False,
     [("Locomotion", "pattern"), ("Additive", "pattern"), ("Animation state machine", "pattern"), ("single-graph", "pattern")],
     [("Locomotion", "single-graph", "REPLACES")],
     "which layered animation approach replaced the single-graph state machine and which stall did it fix",
     "animation state machine layered locomotion additive jump recovery"),
    # --- 35 ---
    ("Camera shake is driven by a Perlin-noise-over-time generator with amplitude bound to recent damage; hand-keyed curves used to desync under slow-mo and got retired.", "problem", "ai_coding", False,
     [("Perlin-noise", "algorithm"), ("Camera shake", "pattern"), ("hand-keyed curves", "pattern"), ("slow-mo", "pattern")],
     [("Perlin-noise", "hand-keyed curves", "REPLACES")],
     "which camera-shake generator replaced hand-keyed curves and why under slow-mo did the old one fail",
     "camera shake perlin noise hand keyed curve slow mo desync"),
    # --- 36 ---
    ("Audio mixing buses route through a snapshot system: entering a menu pushes a ducked snapshot and popping it restores within the fade window declared in data.", "architecture", "ai_coding", False,
     [("snapshot system", "pattern"), ("Audio mixing buses", "pattern"), ("menu", "concept")],
     [],
     "how does the audio engine duck gameplay mix when entering a menu without hard-coding fades",
     "audio snapshot bus duck menu fade push pop mix declare data"),
    # --- 37 ---
    ("Combat hit-detection moved from raycasts-per-frame to swept capsules against a spatial hash; the old approach missed fast weapons between frames in the PvP clips.", "problem", "ai_coding", False,
     [("raycast", "pattern"), ("swept capsule", "pattern"), ("spatial hash", "pattern"), ("PvP", "pattern")],
     [("swept capsule", "raycast", "IMPROVES_ON")],
     "which hit-detection upgrade closed the between-frame miss bug on fast PvP weapons",
     "swept capsule raycast spatial hash hit detection fast weapon pvp"),
    # --- 38 ---
    ("Procedural level generator uses a graph-grammar rewrite on a room graph; the old tile-random sampler kept producing dead-end dungeons that failed the reachability check.", "architecture", "ai_coding", False,
     [("graph-grammar", "algorithm"), ("room graph", "pattern"), ("tile-random sampler", "pattern"), ("reachability", "pattern")],
     [("graph-grammar", "tile-random sampler", "REPLACES")],
     "which procgen algorithm replaced the tile-random sampler after reachability failures plagued dungeons",
     "graph grammar rewrite room tile random sampler reachability procgen"),
    # --- 39 ---
    ("The navmesh is baked offline with Recast and patched at runtime with temporary obstacles via Detour; dynamic rebuild of the full mesh turned out to be too spiky on mid-range CPUs.", "decision", "ai_coding", False,
     [("Recast", "library"), ("Detour", "library"), ("navmesh", "concept"), ("dynamic rebuild", "pattern")],
     [("Detour", "dynamic rebuild", "REPLACES")],
     "how does the navmesh stay current at runtime without a full rebuild spike on mid-range CPUs",
     "recast detour navmesh bake obstacle patch dynamic rebuild spike"),
    # --- 40 ---
    ("Pathfinding queries are amortised across frames with a time-sliced scheduler; a request that exceeds two ms yields and resumes next frame from its open-set cursor.", "architecture", "ai_coding", False,
     [("Pathfinding", "pattern"), ("time-sliced scheduler", "pattern"), ("open-set", "pattern")],
     [],
     "how does the pathfinder cap its per-frame cost on long queries without cancelling the search",
     "path find time slice amortise frame open set cursor yield resume"),
    # --- 41 ---
    ("Save v7 introduced a blob-per-actor split so the save blob isn't one giant serialised world; per-actor versions migrate independently and corrupted actors are quarantined on load.", "milestone", "ai_coding", False,
     [("Save v7", "pattern"), ("blob-per-actor", "pattern"), ("quarantine", "pattern")],
     [],
     "which save format change decoupled actor versions and what does it do with a corrupted actor blob",
     "save v7 blob per actor split version migrate quarantine load"),
    # --- 42 ---
    ("The tick scheduler is a topological sort over system dependencies declared at registration; cyclic dependencies fail the boot rather than deadlocking mid-match in production.", "architecture", "ai_coding", False,
     [("tick scheduler", "pattern"), ("topological sort", "algorithm"), ("cyclic dependencies", "pattern")],
     [],
     "how does the tick scheduler order systems and what does it do with a cyclic dependency",
     "tick schedule topological sort system dependency cycle boot fail"),
    # --- 43. noise ---
    ("The break-room whiteboard is three iterations deep into a doodle war and the character count has outgrown two side panels.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Damage numbers above enemies render through a pooled particle allocator; the old per-hit GameObject spawn thrashed the garbage collector on Switch builds during boss phases.", "problem", "ai_coding", False,
     [("pooled particle allocator", "pattern"), ("GameObject", "framework"), ("Switch", "platform")],
     [("pooled particle allocator", "GameObject", "REPLACES")],
     "which pooling change fixed the boss-phase GC thrash from damage-number spawns on Switch",
     "pool allocator gameobject damage number switch gc thrash boss"),
    # --- 45 ---
    ("Dialogue system is a small bytecode VM: Yarn scripts compile to opcodes and the runtime steps them per frame, which let us pause, rewind, and debug mid-line without a special mode.", "architecture", "ai_coding", False,
     [("Yarn", "language"), ("bytecode VM", "concept"), ("Dialogue system", "pattern")],
     [],
     "which runtime architecture does the dialogue system use to support pause, rewind, and debug mid-line",
     "yarn bytecode vm dialogue pause rewind debug mid line opcode"),
    # --- 46 ---
    ("Quest prerequisite checks used to live as giant switch blocks per quest; a declarative requirements list checked by a single evaluator cut thousands of lines and eliminated a class of typos.", "decision", "ai_coding", False,
     [("switch block", "pattern"), ("requirements list", "pattern"), ("evaluator", "pattern")],
     [("requirements list", "switch block", "REPLACES")],
     "which declarative pattern replaced per-quest switch blocks for prerequisite checks",
     "quest prerequisite requirement list switch block evaluator declarative"),
    # --- 47 ---
    ("Player loadout is persisted as a structural diff against the class default; only changed slots go in the save blob, which shrank the profile file by about sixty percent.", "fact", "ai_coding", False,
     [("loadout", "pattern"), ("structural diff", "pattern"), ("save blob", "pattern")],
     [],
     "how does the loadout persister keep profile saves small by storing only structural changes",
     "loadout structural diff class default save blob shrink profile"),
    # --- 48 ---
    ("Achievements are tracked by a small event-sourced log per profile stored in SQLite; replay against the current ruleset awards any newly-added achievements when the player next connects.", "architecture", "ai_coding", False,
     [("achievement", "pattern"), ("event-sourced log", "pattern"), ("profile", "concept"), ("SQLite", "database")],
     [],
     "which persistence pattern lets newly-added achievements retroactively unlock for existing players",
     "achievement event source log profile replay ruleset retroactive"),
    # --- 49 ---
    ("The match lobby state uses a CRDT so two late-joining clients reconciling with the host don't race on ready-state flips; flicker in the ready column stopped after the switch.", "problem", "ai_coding", False,
     [("CRDT", "pattern"), ("match lobby", "pattern"), ("ready-state", "pattern")],
     [("CRDT", "ready-state", "APPLIES_TO")],
     "which data structure eliminated the ready-state flicker when two clients joined the lobby at once",
     "crdt match lobby ready state flicker race reconcile host join"),
    # --- 50 ---
    ("Crash triage for save loads classifies exceptions into recoverable migration errors versus corrupt data; recoverable kicks the migration chain, corrupt shows the restore-backup dialog.", "architecture", "ai_coding", False,
     [("Crash triage", "pattern"), ("migration chain", "pattern"), ("restore-backup dialog", "api")],
     [],
     "how does save-load triage split recoverable migration errors from genuine corruption at load time",
     "crash triage save load migration recoverable corrupt restore dialog"),
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
