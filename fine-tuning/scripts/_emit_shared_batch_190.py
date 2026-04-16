"""One-off emitter for shared-base batch-190 — technical domain (physics simulation: rigid body engines, solvers, collision detection, soft bodies, differentiable sim).

Writes 50 rows to data/v2/shared/batch_190.tmp.jsonl with ids shared-09451..09500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_190.tmp.jsonl"
ID_OFFSET = 9450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the vehicle simulator's rigid-body core from Bullet Physics to Jolt Physics; the multicore broadphase and deterministic island solver shaved eight milliseconds off the per-tick cost on the 32-car grid.", "decision", "technical", False,
     [("Bullet Physics", "library"), ("Jolt Physics", "library"), ("broadphase", "concept"), ("island solver", "pattern")],
     [("Jolt Physics", "Bullet Physics", "REPLACES")],
     "which rigid-body engine swap cut per-tick cost on the 32-car grid and what features drove it",
     "jolt bullet physics broadphase island solver vehicle grid tick"),
    # --- 2 ---
    ("NVIDIA PhysX 5 replaced Havok on the console client for cloth and destruction; the GPU rigid-body path is still off by default while we retune stacking stability on PS5.", "decision", "technical", False,
     [("NVIDIA PhysX", "library"), ("Havok", "library"), ("GPU rigid-body", "pattern"), ("PS5", "platform")],
     [("NVIDIA PhysX", "Havok", "REPLACES")],
     "which physics library replaced Havok for cloth and destruction on console and what remains disabled",
     "physx havok cloth destruction gpu rigid body ps5 stacking stability"),
    # --- 3 ---
    ("Box2D still powers the 2D platformer's sidescroller sim; Chipmunk2D was evaluated but the polygon clipping and sensor fixture story in Box2D was closer to what the gameplay code already assumed.", "decision", "technical", False,
     [("Box2D", "library"), ("Chipmunk2D", "library"), ("sensor fixture", "pattern")],
     [("Box2D", "Chipmunk2D", "PREFERS")],
     "which 2D physics engine won the sidescroller bake-off and which feature sealed it",
     "box2d chipmunk2d sensor fixture polygon clipping sidescroller 2d"),
    # --- 4 ---
    ("Continuous collision detection is enabled only for bullets and the player capsule; leaving CCD on for every dynamic body doubled solver cost for zero visual benefit in the combat slice.", "decision", "technical", False,
     [("CCD", "concept"), ("bullets", "pattern"), ("player capsule", "pattern"), ("solver", "concept")],
     [("CCD", "bullets", "APPLIES_TO")],
     "which bodies get continuous collision detection and why is it disabled elsewhere",
     "ccd continuous collision bullet capsule solver cost combat slice"),
    # --- 5 ---
    ("The narrowphase uses GJK for convex-convex distance and falls back to EPA for penetration depth; the old SAT path survived only for OBB-vs-OBB where the axis set is trivial.", "reference", "technical", False,
     [("GJK", "algorithm"), ("EPA", "algorithm"), ("SAT", "algorithm"), ("OBB", "concept")],
     [("GJK", "SAT", "REPLACES")],
     "which convex-convex algorithms handle narrowphase distance versus penetration and where does SAT survive",
     "gjk epa sat narrowphase convex penetration obb axis separation"),
    # --- 6 ---
    ("Signed distance fields bake the static world colliders into a 3D texture sampled by the particle sim; raycasts against analytic triangle meshes couldn't keep up with a hundred thousand particles.", "milestone", "technical", False,
     [("Signed distance fields", "concept"), ("3D texture", "pattern"), ("particle sim", "pattern"), ("raycast", "pattern")],
     [("Signed distance fields", "raycast", "REPLACES")],
     "which static-world representation does the particle sim sample and what did it replace",
     "sdf signed distance field texture particle raycast triangle static"),
    # --- 7 ---
    ("Projected Gauss-Seidel drives the constraint solver; ten velocity iterations and three position iterations converge cleanly for the articulated ragdoll chain at 120 Hz.", "fact", "technical", False,
     [("Projected Gauss-Seidel", "algorithm"), ("constraint solver", "concept"), ("ragdoll", "pattern"), ("120 Hz", "config")],
     [("Projected Gauss-Seidel", "constraint solver", "APPLIES_TO")],
     "which solver and iteration counts keep the ragdoll chain stable at 120 Hz",
     "projected gauss seidel pgs solver iteration ragdoll 120 hz"),
    # --- 8 ---
    ("The position-based dynamics core runs the rope and cloth in the sailing sim; XPBD stretched the solver to include compliance parameters so elastic ropes stopped feeling infinitely stiff.", "architecture", "technical", False,
     [("position-based dynamics", "algorithm"), ("XPBD", "algorithm"), ("rope", "concept"), ("cloth", "concept")],
     [("XPBD", "position-based dynamics", "IMPROVES_ON")],
     "which solver family powers the sailing sim's rope and cloth and what did XPBD add",
     "pbd xpbd position based dynamics rope cloth compliance sailing"),
    # --- 9 ---
    ("Rigid-body sleeping thresholds dropped from 0.1 to 0.02 m/s linear velocity after the stacked-crates demo woke the whole pile every time the player walked past; islands stay asleep now unless genuinely disturbed.", "milestone", "technical", False,
     [("sleeping", "concept"), ("island", "concept"), ("stacked-crates", "pattern")],
     [],
     "which sleeping threshold change stopped crate piles from waking on nearby footsteps",
     "rigid body sleeping threshold island stacked crate wake velocity"),
    # --- 10. noise ---
    ("The studio fridge gained a label printer after the mystery yogurt incident and now every container carries a name and a best-by note.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Broadphase is sweep-and-prune on the x axis for the racing title and a dynamic AABB tree BVH for the open-world build; the single broadphase abstraction hides the pick behind a compile-time flag.", "reference", "technical", False,
     [("sweep-and-prune", "algorithm"), ("AABB tree", "algorithm"), ("broadphase", "concept"), ("BVH", "algorithm")],
     [],
     "which broadphase strategies ship for the two titles and how is the choice encoded",
     "sweep prune aabb tree bvh broadphase racing open world flag"),
    # --- 12 ---
    ("The wheeled-vehicle controller uses Jolt's raycast-vehicle model on arcade titles and a fully constrained hinge-and-wheel rigid-body assembly on the sim racer; tire forces come from a Pacejka magic-formula model in both.", "architecture", "technical", False,
     [("Jolt", "library"), ("raycast-vehicle", "pattern"), ("Pacejka", "algorithm"), ("hinge", "concept")],
     [("raycast-vehicle", "hinge", "PREFERS")],
     "which vehicle model ships for arcade versus sim racer and which tire formula is shared",
     "jolt raycast vehicle hinge wheel pacejka tire arcade sim racer"),
    # --- 13 ---
    ("MuJoCo drives the humanoid manipulation benchmarks in the RL lab; Gymnasium wraps the environments and the policy server consumes the contact forces tensor directly from the MJData struct.", "milestone", "technical", False,
     [("MuJoCo", "library"), ("Gymnasium", "framework"), ("MJData", "api"), ("RL lab", "project")],
     [("Gymnasium", "MuJoCo", "DEPENDS_ON")],
     "which simulator and wrapper power the humanoid manipulation benchmarks in the RL lab",
     "mujoco gymnasium mjdata humanoid manipulation rl lab contact"),
    # --- 14 ---
    ("DART is the go-to simulator on the bipedal-locomotion paper reruns; its Featherstone articulated-body algorithm and analytic derivatives let us finite-diff gradients cheaply for trajectory-opt warm starts.", "decision", "technical", False,
     [("DART", "library"), ("Featherstone", "algorithm"), ("bipedal-locomotion", "project")],
     [("DART", "Featherstone", "USES")],
     "which simulator and articulated-body algorithm back the bipedal locomotion reruns",
     "dart featherstone articulated body bipedal locomotion derivative"),
    # --- 15 ---
    ("ODE still powers the legacy driving school sim; we kept it because the fixed-joint stability on the lift-gate training rig was tuned there and porting risked regressions in customer acceptance tests.", "decision", "technical", False,
     [("ODE", "library"), ("fixed-joint", "concept"), ("driving school sim", "project")],
     [],
     "why did the legacy driving school sim stay on ODE instead of moving to a newer engine",
     "ode open dynamics engine fixed joint lift gate legacy driving"),
    # --- 16 ---
    ("RaiSim benchmarks beat Bullet Physics by roughly 3x on the quadruped rollouts at contact-heavy terrain densities; the per-contact Nonlinear Gauss-Seidel path is the reason.", "fact", "technical", False,
     [("RaiSim", "library"), ("Bullet Physics", "library"), ("Nonlinear Gauss-Seidel", "algorithm"), ("quadruped", "concept")],
     [("RaiSim", "Bullet Physics", "REPLACES")],
     "which simulator beats Bullet Physics on quadruped contact rollouts and by how much",
     "raisim bullet nonlinear gauss seidel quadruped contact rollout"),
    # --- 17 ---
    ("Brax runs the batched rollouts on TPU pods; the JAX-native XLA-compiled pipeline lets us scale 8192 parallel envs per host without leaving the accelerator for contact resolution.", "architecture", "technical", False,
     [("Brax", "library"), ("JAX", "framework"), ("TPU", "platform"), ("XLA", "tool")],
     [("Brax", "JAX", "DEPENDS_ON")],
     "which simulator and backend handle 8192-env batched rollouts on TPU and why no host roundtrip",
     "brax jax tpu xla batched rollout parallel environment accelerator"),
    # --- 18 ---
    ("PyBullet stayed as the teaching-lab default; its Python-first API and URDF loader make it the shortest path from a student's robot model to a rolling physics step with no CMake detour.", "preference", "technical", False,
     [("PyBullet", "library"), ("URDF", "protocol"), ("Python", "language"), ("CMake", "tool")],
     [],
     "why does the teaching lab prefer PyBullet over other simulators for student robot models",
     "pybullet urdf python teaching lab student robot cmake detour"),
    # --- 19 ---
    ("Genesis (simulator) took over the photoreal-synthetic-data generation job from Isaac Gym; unified differentiable rigid, fluid, and deformable solvers in one API removed the three-stack pipeline glue.", "decision", "technical", False,
     [("Genesis", "library"), ("Isaac Gym", "library"), ("differentiable", "concept")],
     [("Genesis", "Isaac Gym", "REPLACES")],
     "which simulator replaced Isaac Gym for photoreal synthetic data and what unification drove it",
     "genesis isaac gym differentiable rigid fluid deformable synthetic"),
    # --- 20 ---
    ("Isaac Gym lived on only for the legacy manipulator policies; NVIDIA's deprecation of the standalone package forced a migration plan toward Isaac Lab for anything not yet in production.", "milestone", "technical", False,
     [("Isaac Gym", "library"), ("Isaac Lab", "library"), ("NVIDIA", "organization")],
     [("Isaac Lab", "Isaac Gym", "REPLACES")],
     "which deprecation forced the migration off Isaac Gym and which successor is the target",
     "isaac gym lab deprecation nvidia manipulator policy migration"),
    # --- 21 ---
    ("NVIDIA FleX handles the particle-based fluid and cloth in the previs tool; the position-based solver produces plausible motion cheaply and we never needed the Navier-Stokes accuracy of a grid solver.", "architecture", "technical", False,
     [("NVIDIA FleX", "library"), ("fluid", "concept"), ("Navier-Stokes", "algorithm"), ("previs tool", "project")],
     [("NVIDIA FleX", "previs tool", "APPLIES_TO")],
     "which fluid and cloth solver backs the previs tool and why not a grid-based Navier-Stokes approach",
     "flex fluid cloth navier stokes position based previs plausible"),
    # --- 22 ---
    ("Material Point Method (MPM) drives the snow and mud deformation in the rally game; a grid-particle hybrid preserves conservation while letting us reseed particles without re-meshing the terrain.", "architecture", "technical", False,
     [("Material Point Method", "algorithm"), ("MPM", "algorithm"), ("rally game", "project")],
     [("Material Point Method", "rally game", "APPLIES_TO")],
     "which hybrid grid-particle algorithm powers snow and mud deformation in the rally game",
     "mpm material point method snow mud rally grid particle deform"),
    # --- 23 ---
    ("Smoothed-Particle Hydrodynamics (SPH) still serves the small-scale splash FX; the neighbourhood search uses a spatial hash with a fixed 1.5x kernel radius and skips pressure iterations past a stability ceiling.", "architecture", "technical", False,
     [("Smoothed-Particle Hydrodynamics", "algorithm"), ("SPH", "algorithm"), ("spatial hash", "pattern")],
     [],
     "which fluid algorithm runs the small-scale splash FX and how is neighbourhood search accelerated",
     "sph smoothed particle hydrodynamics splash fx spatial hash pressure"),
    # --- 24 ---
    ("Collision shapes in the asset pipeline are convex-hull auto-decomposed with V-HACD and hand-corrected for characters; triangle meshes on dynamic bodies are banned by a lint rule in the importer.", "architecture", "technical", False,
     [("V-HACD", "algorithm"), ("convex-hull", "concept"), ("triangle mesh", "concept"), ("importer", "pattern")],
     [("V-HACD", "convex-hull", "USES")],
     "which collision shape workflow does the asset pipeline enforce and which shape is banned on dynamics",
     "vhacd convex decomposition triangle mesh dynamic collision lint"),
    # --- 25 ---
    ("The articulated-body cache warms on level load: all inertia tensors, joint limits, and spatial transforms get precomputed so the first simulation tick doesn't spike past the 4 ms budget.", "milestone", "technical", False,
     [("articulated-body", "concept"), ("inertia tensor", "concept"), ("joint limit", "concept"), ("4 ms", "config")],
     [],
     "which precompute step keeps the first simulation tick inside the 4 ms budget on level load",
     "articulated body cache inertia tensor joint limit precompute tick"),
    # --- 26 ---
    ("Rolled back the GPU rigid-body pipeline for the 2026-02-14 patch after stacking stability regressed on Windows drivers 546 and newer; CPU Jolt carries the release and the GPU path stays behind a flag.", "milestone", "technical", False,
     [("GPU rigid-body", "pattern"), ("Jolt", "library"), ("Windows", "platform"), ("2026-02-14", "date")],
     [],
     "which GPU rigid-body regression forced the 2026-02-14 rollback and what now carries the release",
     "gpu rigid body stacking windows driver rollback jolt patch flag"),
    # --- 27 ---
    ("The soft-body tetrahedral meshes for destructible props come out of the offline cook step; tetgen generates the mesh and a stiffness map is painted per region so the hood crumples while the frame resists.", "architecture", "technical", False,
     [("soft-body", "concept"), ("tetrahedral", "concept"), ("tetgen", "tool"), ("stiffness map", "pattern")],
     [("tetgen", "tetrahedral", "USES")],
     "which offline pipeline produces soft-body tet meshes and how are stiffness regions authored",
     "soft body tetrahedral tetgen stiffness map destructible cook prop"),
    # --- 28 ---
    ("Rope in the grapple-hook gameplay uses a Cosserat rod model rather than a mass-spring chain; bending and twisting modes behave correctly when the hook swings past vertical, which the chain model could not.", "decision", "technical", False,
     [("Cosserat rod", "algorithm"), ("mass-spring", "algorithm"), ("grapple-hook", "pattern")],
     [("Cosserat rod", "mass-spring", "REPLACES")],
     "which rope model replaced mass-spring for the grapple hook and which motion did it finally handle",
     "cosserat rod mass spring grapple hook bending twisting swing"),
    # --- 29 ---
    ("Cloth on the cape of the hero character is Extended Position-Based Dynamics with self-collision capsules; the cape no longer clips through the backpack in the turning animation.", "fact", "technical", False,
     [("Extended Position-Based Dynamics", "algorithm"), ("cape", "concept"), ("self-collision", "pattern"), ("backpack", "concept")],
     [("Extended Position-Based Dynamics", "cape", "APPLIES_TO")],
     "which cloth algorithm and collision primitive stopped the hero cape clipping through the backpack",
     "xpbd cloth cape self collision capsule backpack turn animation"),
    # --- 30 ---
    ("The bounding-volume hierarchy BVH for static-world collision is built bottom-up with surface-area-heuristic sorting; the old top-down median split produced overlapping siblings that doubled raycast counts on city streets.", "fact", "technical", False,
     [("BVH", "algorithm"), ("surface-area-heuristic", "algorithm"), ("top-down median split", "algorithm"), ("city streets", "pattern")],
     [("surface-area-heuristic", "top-down median split", "REPLACES")],
     "which BVH construction strategy replaced median split and which workload exposed the old one",
     "bvh surface area heuristic median split raycast city static"),
    # --- 31 ---
    ("Differentiable physics in the policy-training loop uses Brax for rigid and Warp for MPM; gradients flow back through the contact model via the analytic impulse formulation in both, so REINFORCE isn't the only option.", "architecture", "technical", False,
     [("Brax", "library"), ("Warp", "library"), ("MPM", "algorithm"), ("REINFORCE", "algorithm")],
     [("Brax", "Warp", "DEPENDS_ON")],
     "which two engines back the differentiable physics policy-training loop and which algorithm they avoid being forced into",
     "brax warp mpm reinforce differentiable gradient contact policy"),
    # --- 32 ---
    ("Continuous collision uses conservative advancement for fast-moving bodies and TOI-of-impact ordering for the solver's substep cascade; the old linear-sweep approximation missed tunneling through thin walls in the static set.", "fact", "technical", False,
     [("conservative advancement", "algorithm"), ("TOI-of-impact", "algorithm"), ("linear-sweep", "algorithm"), ("thin walls", "pattern")],
     [("conservative advancement", "linear-sweep", "REPLACES")],
     "which CCD upgrade fixed the thin-wall tunneling and how does the solver order the substeps",
     "conservative advancement toi linear sweep ccd thin wall tunnel"),
    # --- 33 ---
    ("Spatial partitioning for the crowd-collision-avoidance layer uses a dynamic grid with cells sized to 1.5x the agent radius; uniform grid gave cleaner profile numbers than a quadtree at one thousand agents.", "decision", "technical", False,
     [("dynamic grid", "pattern"), ("quadtree", "algorithm"), ("crowd", "pattern")],
     [("dynamic grid", "quadtree", "PREFERS")],
     "which spatial partition won the crowd-avoidance bake-off and what cell sizing did it use",
     "dynamic grid quadtree crowd avoidance agent radius spatial cell"),
    # --- 34 ---
    ("The friction cone shape is pyramidal with four basis directions in the character solver; a smooth isotropic cone was tried but the extra dot products didn't pay for the marginal behaviour improvement.", "decision", "technical", False,
     [("friction cone", "concept"), ("pyramidal", "pattern"), ("isotropic", "pattern"), ("character solver", "project")],
     [("pyramidal", "isotropic", "PREFERS")],
     "which friction cone approximation did the character solver pick and why not the smooth one",
     "friction cone pyramidal isotropic character solver dot product"),
    # --- 35 ---
    ("Contact-manifold generation in the contact manifold clusters up to four contact points per pair with a reduced-point heuristic; anything denser made the solver over-constrain stacks and the tower demo tipped on tick 30.", "decision", "technical", False,
     [("contact manifold", "concept"), ("reduced-point", "algorithm"), ("tower demo", "pattern")],
     [],
     "which contact-manifold reduction kept stacks stable and which demo exposed the over-constrain bug",
     "contact manifold four point cluster reduced solver stack tower"),
    # --- 36 ---
    ("Joint limits use a soft-constraint formulation with configurable restitution; hard limits spiked the residual on the Jacobian row at the limit and the solver refused to converge under heavy impact loads.", "problem", "technical", False,
     [("soft-constraint", "pattern"), ("hard limits", "pattern"), ("Jacobian", "concept"), ("restitution", "concept")],
     [("soft-constraint", "hard limits", "REPLACES")],
     "which joint-limit formulation replaced hard limits and what solver symptom drove the switch",
     "soft constraint hard limit jacobian restitution joint solver"),
    # --- 37 ---
    ("The character controller kinematic sweep uses a capsule-vs-world cast with a small skin width; the skin absorbs floating-point slop on stair edges so the climb doesn't hitch at the 16 cm riser.", "fact", "technical", False,
     [("character controller", "concept"), ("capsule", "concept"), ("skin width", "pattern"), ("16 cm riser", "config")],
     [],
     "which kinematic-sweep pattern and parameter keep the character from hitching on 16 cm stair risers",
     "character controller capsule skin width stair riser sweep slop"),
    # --- 38 ---
    ("The determinism contract for the replay system requires fixed-point accumulation across platforms; the floating-point path diverged by the third second on AMD versus Intel even with identical inputs and seeds.", "problem", "technical", False,
     [("determinism", "concept"), ("fixed-point", "pattern"), ("floating-point", "concept"), ("replay", "pattern")],
     [("fixed-point", "floating-point", "REPLACES")],
     "which numeric representation replaced floating point for replay determinism and on which CPU pair it diverged",
     "determinism fixed point float amd intel replay seed diverge"),
    # --- 39 ---
    ("The collision filter layer uses a pair of 32-bit masks per body; the group-and-subgroup scheme that shipped in the earlier build couldn't express vehicle-vs-debris exclusions without a runtime exception list.", "decision", "technical", False,
     [("collision filter", "concept"), ("32-bit mask", "pattern"), ("group-and-subgroup", "pattern")],
     [("32-bit mask", "group-and-subgroup", "REPLACES")],
     "which collision-filter scheme replaced group-and-subgroup and which exclusion it finally expresses cleanly",
     "collision filter 32 bit mask group subgroup vehicle debris exclude"),
    # --- 40 ---
    ("The contact cache persists across frames keyed by body-pair and feature id; warm-starting the solver with cached impulses cut iterations in half on the stacked-crates stress test.", "fact", "technical", False,
     [("contact cache", "pattern"), ("warm-starting", "algorithm"), ("stacked-crates", "pattern")],
     [],
     "which cache and warm-start trick halved solver iterations on the stacked-crates stress test",
     "contact cache warm start impulse body pair feature iteration"),
    # --- 41 ---
    ("Milestone on the 2026-03-10 build: the 10000-body urban demo ran at 45 Hz with Jolt multicore plus a persistent BVH, up from 12 Hz on the old single-thread Bullet path.", "milestone", "technical", False,
     [("Jolt", "library"), ("Bullet", "library"), ("BVH", "algorithm"), ("2026-03-10", "date")],
     [("Jolt", "Bullet", "REPLACES")],
     "which milestone build hit 45 Hz on the 10000-body urban demo and what drove the speedup",
     "2026 03 10 jolt bullet bvh urban demo 10000 body 45 hz multicore"),
    # --- 42 ---
    ("Reference: ERP and CFM in ODE map to bias and compliance in Projected Gauss-Seidel; the derivation in Catto's GDC slides is the canonical translation and we keep a copy in the physics wiki.", "reference", "technical", False,
     [("ERP", "concept"), ("CFM", "concept"), ("ODE", "library"), ("Projected Gauss-Seidel", "algorithm"), ("Catto", "person"), ("GDC", "organization")],
     [],
     "which reference documents the ERP/CFM to bias/compliance mapping between ODE and PGS",
     "erp cfm ode pgs bias compliance catto gdc slide reference"),
    # --- 43. noise ---
    ("The intern's desk plant is now taller than the monitor and someone has started measuring weekly growth with a sticky note ladder.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Ragdoll activation is gated by a damage threshold and a ground-contact check; flipping to ragdoll mid-air in earlier patches created the infamous T-pose helicopter that clipped through the ceiling.", "problem", "technical", False,
     [("ragdoll", "pattern"), ("ground-contact", "pattern"), ("T-pose", "pattern"), ("damage threshold", "config")],
     [],
     "which two gates guard ragdoll activation and which earlier bug did they retire",
     "ragdoll ground contact damage threshold t pose helicopter mid air"),
    # --- 45 ---
    ("Reference: the position-based dynamics paper by Muller et al. lays out the constraint projection loop; XPBD's compliance extension is the Macklin paper and both PDFs live in the team drive.", "reference", "technical", False,
     [("position-based dynamics", "algorithm"), ("Muller", "person"), ("XPBD", "algorithm"), ("Macklin", "person")],
     [],
     "which two papers ground the position-based dynamics and XPBD implementation",
     "pbd xpbd muller macklin paper constraint projection compliance"),
    # --- 46 ---
    ("Preferred practice for new physics code is to author constraints as a row-block Jacobian and let the solver assemble the system matrix; hand-assembling A and b used to duplicate logic and hide sign bugs.", "preference", "technical", False,
     [("Jacobian", "concept"), ("system matrix", "concept"), ("constraint", "concept")],
     [],
     "which constraint-authoring preference replaced hand-assembling the system matrix and why",
     "jacobian row block system matrix constraint solver sign bug"),
    # --- 47 ---
    ("Preferred debug workflow pipes contact points, impulses, and island ids through the in-engine overlay; tearing down to an isolated repro in a Jolt unit test is reserved for stacking regressions only.", "preference", "technical", False,
     [("contact point", "concept"), ("island", "concept"), ("Jolt", "library"), ("overlay", "pattern")],
     [],
     "which physics debug workflow is the default and when do we drop to a Jolt unit test",
     "contact impulse island overlay jolt unit test stacking debug"),
    # --- 48 ---
    ("Reference: the Erin Catto 'Iterative Dynamics with Temporal Coherence' paper is the solver's theoretical base; the warm-start and split-impulse tricks are both discussed there.", "reference", "technical", False,
     [("Erin Catto", "person"), ("solver", "concept"), ("warm-start", "algorithm"), ("split-impulse", "algorithm")],
     [],
     "which Catto paper is the theoretical base for warm-start and split-impulse solver tricks",
     "erin catto iterative dynamics temporal coherence warm start split"),
    # --- 49 ---
    ("Reference: NVIDIA PhysX 5 SDK documentation covers the GPU rigid-body pipeline requirements; the minimum driver versions and feature-level flags are pinned in our platform matrix.", "reference", "technical", False,
     [("NVIDIA PhysX", "library"), ("GPU rigid-body", "pattern"), ("platform matrix", "pattern")],
     [],
     "which reference pins minimum driver versions for the PhysX 5 GPU rigid-body pipeline",
     "physx sdk gpu rigid body driver platform matrix nvidia doc"),
    # --- 50 ---
    ("Preferred collision-shape authoring rule: primitives first, then convex hulls, then V-HACD decompositions, and only then triangle meshes for static-only bodies; the rule cut asset review cycles in half.", "preference", "technical", False,
     [("primitive", "concept"), ("convex hull", "concept"), ("V-HACD", "algorithm"), ("triangle mesh", "concept")],
     [],
     "which collision-shape authoring preference halved asset review cycles and what ordering does it enforce",
     "primitive convex hull vhacd triangle mesh static author review"),
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
