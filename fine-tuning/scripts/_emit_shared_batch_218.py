"""One-off emitter for shared-base batch-218 — personal domain (woodworking joinery and finishing: hand tools, chisels, sharpening, joints, glue-up, finishes, Japanese joinery).

Writes 50 rows to data/v2/shared/batch_218.tmp.jsonl with ids shared-10851..10900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_218.tmp.jsonl"
ID_OFFSET = 10850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Retired the Stanley #4 as the daily smoother and made the Lie-Nielsen No. 4 the go-to; the thicker iron chatters less across cherry end grain and holds an edge longer between touch-ups.", "milestone", "personal", False,
     [("Stanley #4", "tool"), ("Lie-Nielsen", "organization"), ("cherry", "concept")],
     [("Lie-Nielsen", "Stanley #4", "REPLACES")],
     "which smoothing plane took over as my daily driver and what edge behaviour drove the swap",
     "lie nielsen stanley smoother cherry end grain iron chatter"),
    # --- 2 ---
    ("Ordered the Veritas bevel-up jointer to sit alongside the #7 for shooting board duty; the adjustable mouth and low angle handle end grain on white oak without tearing the fibres.", "milestone", "personal", False,
     [("Veritas", "organization"), ("#7", "tool"), ("shooting board", "concept"), ("white oak", "concept")],
     [("Veritas", "#7", "APPLIES_TO")],
     "which jointer plane joined the bench to cover shooting-board work on difficult end grain",
     "veritas bevel up jointer shooting board white oak end grain"),
    # --- 3 ---
    ("Reground the Stanley #5 into a dedicated scrub with an 8 inch camber; rough-flattening live-edge slabs is now a job for that plane instead of wearing down the smoother's iron.", "architecture", "personal", False,
     [("Stanley #5", "tool"), ("scrub", "concept"), ("live-edge", "concept")],
     [("Stanley #5", "scrub", "APPLIES_TO")],
     "how did the jack plane get repurposed so live-edge flattening stopped eating the smoother iron",
     "stanley jack scrub camber live edge slab flatten repurpose"),
    # --- 4 ---
    ("Paul Sellers' poor-man's sharpening routine with three diamond plates replaced the elaborate waterstone flattening ritual; same polish on the bevel in a quarter of the setup time.", "decision", "personal", False,
     [("Paul Sellers", "person"), ("diamond plates", "tool"), ("waterstone", "tool"), ("bevel", "concept")],
     [("diamond plates", "waterstone", "REPLACES")],
     "which sharpening routine replaced the waterstone ritual and how much setup time did it save",
     "paul sellers diamond plate waterstone bevel flatten sharpen setup"),
    # --- 5 ---
    ("Added Rob Cosman's three-minute dovetail method to the evening practice drill; the bench hook jig and the 1:7 ratio guide shrank my layout time on the pine test boards by half.", "milestone", "personal", False,
     [("Rob Cosman", "person"), ("dovetail", "concept"), ("bench hook", "tool"), ("pine", "concept")],
     [("Rob Cosman", "dovetail", "APPLIES_TO")],
     "which dovetailing method joined the evening practice drills and what layout win did it deliver",
     "rob cosman dovetail bench hook ratio layout pine practice"),
    # --- 6 ---
    ("Swapped the western backsaw for a Gyokucho ryoba on the cross-cut station; the push-stroke fatigue that nagged my wrist on long tenon shoulders disappears with the pull cut.", "decision", "personal", False,
     [("Gyokucho", "organization"), ("ryoba", "tool"), ("backsaw", "tool"), ("tenon", "concept")],
     [("ryoba", "backsaw", "REPLACES")],
     "which Japanese saw replaced the western backsaw for cross-cut work and which ergonomic issue drove the swap",
     "gyokucho ryoba backsaw pull stroke cross cut tenon wrist"),
    # --- 7 ---
    ("The Shinkiwari dozuki became my default for dovetail cheeks after the first pass on walnut; the kerf is thinner than any western dovetail saw I own and the line stays dead-straight.", "preference", "personal", False,
     [("Shinkiwari", "organization"), ("dozuki", "tool"), ("walnut", "concept"), ("dovetail", "concept")],
     [("dozuki", "dovetail", "APPLIES_TO")],
     "which Japanese saw became my preferred tool for cutting dovetail cheeks in hardwood",
     "shinkiwari dozuki dovetail cheek walnut kerf straight"),
    # --- 8 ---
    ("Narex mortise chisels replaced the cheap hardware-store set in the bench rack; side-lands are ground true enough that the walls of a 10 mm mortise come out parallel without fettling.", "decision", "personal", False,
     [("Narex", "organization"), ("mortise chisel", "tool"), ("hardware-store set", "tool")],
     [("Narex", "hardware-store set", "REPLACES")],
     "which mortise chisel brand replaced the hardware-store set and what tolerance advantage did it bring",
     "narex mortise chisel hardware store side land parallel ten mm"),
    # --- 9 ---
    ("The Kiyohisa bench chisel I picked up at the Tokyo Hamono show is reserved for paring dovetail baselines; the laminated blue-paper steel takes a mirror edge that pine and walnut both feel cleanly.", "fact", "personal", False,
     [("Kiyohisa", "organization"), ("bench chisel", "tool"), ("Tokyo Hamono", "event"), ("paring", "concept")],
     [("Kiyohisa", "paring", "APPLIES_TO")],
     "which Japanese chisel from the Tokyo show is reserved for paring dovetail baselines",
     "kiyohisa bench chisel tokyo hamono paring dovetail baseline"),
    # --- 10. noise ---
    ("The neighbour's cat wandered into the shop again and left a dusty trail of paw prints across the assembly table's freshly waxed surface.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Shapton Glass 1000 and 6000 stones are now the primary sharpening progression; the Naniwa Chosera 800 still lives in the drawer for when the edge has nicks and a coarser cut is warranted.", "architecture", "personal", False,
     [("Shapton Glass", "organization"), ("Naniwa Chosera", "organization"), ("1000", "config"), ("6000", "config")],
     [("Shapton Glass", "Naniwa Chosera", "PREFERS")],
     "which waterstone progression handles routine sharpening and which stone covers the nicked-edge case",
     "shapton glass naniwa chosera 1000 6000 800 progression nick"),
    # --- 12 ---
    ("The King 1000/6000 combination stone that sat on the bench for a decade got demoted to the apprentice's kit; wear rates were too fast to keep up with a plane iron that sees daily use.", "decision", "personal", False,
     [("King", "organization"), ("1000/6000", "config"), ("combination stone", "tool"), ("plane iron", "tool")],
     [("King", "combination stone", "APPLIES_TO")],
     "which combination waterstone got demoted after wear rates could not keep up with daily plane-iron use",
     "king combination stone 1000 6000 wear plane iron demote"),
    # --- 13 ---
    ("Scary-sharp with 3M microfinishing film on a granite reference plate is the travel sharpening setup; it fits in a folder and takes an edge to a level where hair peels off the thumb.", "architecture", "personal", False,
     [("Scary-sharp", "pattern"), ("3M", "organization"), ("granite reference plate", "tool"), ("microfinishing film", "tool")],
     [("Scary-sharp", "microfinishing film", "USES")],
     "which portable sharpening setup rides in the travel kit and how is the reference flat achieved",
     "scary sharp 3m microfinishing film granite reference plate travel"),
    # --- 14 ---
    ("Glued a leather strop charged with 0.5 micron green compound onto a scrap of oak for the final polish step; chisels leave the bench with an edge that pushes through end grain without crushing fibres.", "fact", "personal", False,
     [("leather strop", "tool"), ("green compound", "tool"), ("oak", "concept"), ("chisel", "tool")],
     [("leather strop", "chisel", "APPLIES_TO")],
     "which final-polish step do chisels get so end-grain paring leaves no crushed fibres",
     "leather strop green compound oak chisel polish paring edge"),
    # --- 15 ---
    ("The sharpening station lives on its own cart so water never touches the main bench; the old habit of sharpening-in-place left a rust ring on the leg vise screw that took two hours to de-pit.", "problem", "personal", False,
     [("sharpening station", "tool"), ("leg vise", "tool"), ("rust ring", "concept")],
     [("sharpening station", "rust ring", "FIXES")],
     "which shop layout change fixed the rust ring that showed up on the leg vise screw",
     "sharpening station cart water leg vise rust ring pit"),
    # --- 16 ---
    ("Standardised on 1:6 dovetail ratio for softwoods and 1:8 for hardwoods; the mixed-ratio test boxes from last winter showed clear splitting patterns at 1:5 on poplar and stronger joints at 1:8 on maple.", "architecture", "personal", False,
     [("dovetail", "concept"), ("poplar", "concept"), ("maple", "concept"), ("1:6", "config"), ("1:8", "config")],
     [("dovetail", "maple", "APPLIES_TO")],
     "which dovetail ratios did I standardise on for softwood versus hardwood and what test drove the call",
     "dovetail ratio one six eight softwood hardwood poplar maple split"),
    # --- 17 ---
    ("Half-blind dovetails are now the default for drawer fronts on the cabinet builds; the sliding dovetail I tried for the top-front joint telegraphed seasonal movement through the veneer face.", "decision", "personal", False,
     [("Half-blind dovetails", "concept"), ("sliding dovetail", "concept"), ("drawer fronts", "concept"), ("veneer", "concept")],
     [("Half-blind dovetails", "sliding dovetail", "REPLACES")],
     "which drawer-front joint replaced the sliding dovetail and what telegraphing problem drove the change",
     "half blind dovetail sliding drawer front veneer seasonal telegraph"),
    # --- 18 ---
    ("Mortise and tenon remains the primary frame joint on chairs; the draw-bore pin pulls the shoulder tight before the hide glue even starts gelling, so clamp pressure is more about alignment than compression.", "architecture", "personal", False,
     [("Mortise and tenon", "concept"), ("draw-bore pin", "tool"), ("hide glue", "technology"), ("chairs", "concept")],
     [("draw-bore pin", "Mortise and tenon", "APPLIES_TO")],
     "how does the draw-bore pin change the role of clamp pressure in a mortise-and-tenon chair frame glue-up",
     "mortise tenon draw bore pin hide glue chair shoulder clamp"),
    # --- 19 ---
    ("Finger joints went out of the small-box rotation after the jig slipped once on the router table and ruined a walnut blank; the Festool Domino DF500 does the same structural job without the chipout risk.", "decision", "personal", False,
     [("Finger joints", "concept"), ("Festool Domino DF500", "tool"), ("router table", "tool"), ("walnut", "concept")],
     [("Festool Domino DF500", "Finger joints", "REPLACES")],
     "which Festool tool replaced finger joints in the small-box rotation after the router-table mishap",
     "finger joint festool domino df500 router table walnut chipout"),
    # --- 20 ---
    ("Box joints are still the default for the utility shop drawers; a Kreg pocket hole fills the back joinery where strength matters less than how fast the cabinet goes together.", "fact", "personal", False,
     [("Box joints", "concept"), ("Kreg", "organization"), ("pocket hole", "concept"), ("utility shop drawers", "concept")],
     [("Kreg", "pocket hole", "USES")],
     "which joints handle the utility shop drawers and where does a Kreg pocket hole fit into the structure",
     "box joint kreg pocket hole utility shop drawer fast"),
    # --- 21 ---
    ("Bridle joints took over from through-mortises on the garden-bench stretchers; the glue surface doubles in the same footprint and the look suits exterior furniture better than a wedged mortise ever did.", "decision", "personal", False,
     [("Bridle joints", "concept"), ("through-mortises", "concept"), ("garden-bench", "concept"), ("wedged mortise", "concept")],
     [("Bridle joints", "through-mortises", "REPLACES")],
     "which joint replaced the through-mortise on garden-bench stretchers and what glue-surface gain did it deliver",
     "bridle joint through mortise garden bench stretcher glue surface"),
    # --- 22 ---
    ("Half-lap joints are the frame-and-panel drawer bottoms for the workshop cabinets; panel expansion is handled by a floating tongue and groove, not a dado screwed into place.", "reference", "personal", False,
     [("Half-lap joints", "concept"), ("tongue and groove", "concept"), ("dado", "concept"), ("frame-and-panel", "concept")],
     [("tongue and groove", "dado", "REPLACES")],
     "which joint system handles drawer-bottom expansion without being screwed into place",
     "half lap tongue groove dado frame panel expansion drawer"),
    # --- 23 ---
    ("Biscuit joinery survived only for the painted mitre returns on the baseboard project; every structural case I tried it on had the biscuit wallowing out after one humidity cycle.", "reference", "personal", False,
     [("Biscuit joinery", "concept"), ("mitre returns", "concept"), ("baseboard", "concept"), ("humidity", "concept")],
     [],
     "which joinery method got restricted to painted mitre returns after humidity cycles wallowed out structural uses",
     "biscuit joint mitre return baseboard humidity wallow structural"),
    # --- 24 ---
    ("The kumiko panel for the shoji screen is lined up with a kawai tsugi splice in the vertical jigumi; the junction disappears once the asa-no-ha pattern is seated into the surrounding lattice.", "architecture", "personal", False,
     [("kumiko", "concept"), ("kawai tsugi", "concept"), ("jigumi", "concept"), ("shoji", "concept")],
     [("kawai tsugi", "jigumi", "APPLIES_TO")],
     "which Japanese splice hides the vertical jigumi junction on the kumiko shoji panel",
     "kumiko kawai tsugi jigumi shoji vertical splice asa hanoha"),
    # --- 25 ---
    ("Built the first koshikake ari-tsugi for the tea-house bench rail; the half-lap with dovetail key takes hammer tapping to seat and doesn't budge once the wedge is home, even with no glue at all.", "milestone", "personal", False,
     [("koshikake", "concept"), ("ari", "concept"), ("half-lap", "concept"), ("tea-house", "concept")],
     [("koshikake", "ari", "USES")],
     "which Japanese joint did the tea-house bench rail introduce and how does it stay seated without glue",
     "koshikake ari tsugi half lap dovetail key wedge tea house"),
    # --- 26 ---
    ("Titebond III replaced Titebond Original on any exterior or water-exposed glue-up; the open time is longer as well, which matters when a chair frame needs five mortises closed before the glue skins.", "decision", "personal", False,
     [("Titebond III", "technology"), ("Titebond Original", "technology"), ("chair frame", "concept"), ("exterior", "concept")],
     [("Titebond III", "Titebond Original", "REPLACES")],
     "which PVA glue replaced Titebond Original for exterior work and what open-time benefit came along",
     "titebond three original exterior open time chair mortise skin"),
    # --- 27 ---
    ("Titebond Dark is the go-to for walnut assemblies; squeeze-out dries closer to the wood colour so the clean-up pass on show faces doesn't leave pale glue lines haunting the final finish.", "preference", "personal", False,
     [("Titebond Dark", "technology"), ("walnut", "concept"), ("glue line", "concept"), ("squeeze-out", "concept")],
     [("Titebond Dark", "walnut", "APPLIES_TO")],
     "which PVA variant handles walnut assemblies so squeeze-out does not leave pale glue lines",
     "titebond dark walnut glue line squeeze out show face"),
    # --- 28 ---
    ("Hide glue is still the default for any piece that may need future repair; reversibility with warm water and a palette knife has already bailed out one chipped corner on the writing desk without damaging the finish.", "architecture", "personal", False,
     [("Hide glue", "technology"), ("writing desk", "concept"), ("reversibility", "concept")],
     [("Hide glue", "reversibility", "USES")],
     "which glue remains the default for pieces that may need future repair and which property justifies it",
     "hide glue reversibility warm water palette knife writing desk"),
    # --- 29 ---
    ("Fish glue covers the jobs where hide glue's short open time would bite; cabinet carcases with six dovetail corners in sequence need the fifteen-minute window that fish glue gives at 18 C shop temperature.", "decision", "personal", False,
     [("fish glue", "technology"), ("hide glue", "technology"), ("dovetail", "concept"), ("cabinet carcase", "concept")],
     [("fish glue", "hide glue", "REPLACES")],
     "which protein glue covers cabinet carcases when hide glue's open time would run out partway through the glue-up",
     "fish glue hide glue cabinet carcase dovetail open time fifteen"),
    # --- 30 ---
    ("Dewaxed shellac is the universal sealer coat now; barrier properties let a wipe-on poly sit cleanly over an oiled surface without fisheye, and the sealer coat dries fast enough to scuff-sand in an hour.", "architecture", "personal", False,
     [("shellac", "technology"), ("wipe-on poly", "technology"), ("fisheye", "error"), ("sealer", "concept")],
     [("shellac", "fisheye", "FIXES")],
     "which sealer coat became universal and what compatibility problem does it solve for oiled-then-poly surfaces",
     "shellac sealer wipe on poly fisheye oil barrier scuff sand"),
    # --- 31 ---
    ("BLO on bare walnut, then a week to cure, then dewaxed shellac over the top is now the hand-rubbed finish schedule for small boxes; the oil builds chatoyance and the shellac keeps the surface usable.", "architecture", "personal", False,
     [("BLO", "technology"), ("walnut", "concept"), ("shellac", "technology"), ("chatoyance", "concept")],
     [("BLO", "chatoyance", "APPLIES_TO")],
     "which three-step hand-rubbed schedule does walnut get and which step is responsible for chatoyance",
     "blo walnut shellac chatoyance hand rub finish schedule box"),
    # --- 32 ---
    ("Tung oil replaced BLO on the maple cutting board series; the BLO yellowed the light figure within six months, whereas tung oil stays closer to raw after full cure and food contact is straightforward.", "decision", "personal", False,
     [("tung oil", "technology"), ("BLO", "technology"), ("maple cutting board", "concept")],
     [("tung oil", "BLO", "REPLACES")],
     "which drying oil replaced BLO on the maple cutting board series and why did the swap happen",
     "tung oil blo maple cutting board yellow figure food contact"),
    # --- 33 ---
    ("Rubio Monocoat Pure is the one-coat finish for oak floors in the client work; a single pass with the buffer on a three-hundred-square-foot run is done-and-dusted in an afternoon.", "fact", "personal", False,
     [("Rubio Monocoat", "technology"), ("oak", "concept"), ("buffer", "tool"), ("floor", "concept")],
     [("Rubio Monocoat", "oak", "APPLIES_TO")],
     "which one-coat finish handles oak floor jobs on client work and how is it applied",
     "rubio monocoat pure oak floor buffer one coat afternoon"),
    # --- 34 ---
    ("Osmo Polyx-Oil sits on the workshop-built dining table and takes the abuse of nightly meals; the repair story is the reason, since a localised scuff takes one rag and five minutes to blend invisibly.", "decision", "personal", False,
     [("Osmo Polyx", "technology"), ("dining table", "concept"), ("rag", "tool")],
     [("Osmo Polyx", "dining table", "APPLIES_TO")],
     "which hardwax oil handles the dining table and what repair property justifies the choice",
     "osmo polyx oil dining table scuff repair rag blend invisible"),
    # --- 35 ---
    ("Wipe-on poly is the catalogue-grade finish on the client bookcases; three thinned coats with a sanded intercoat land on a surface that looks closer to rubbed effect than to a fresh brush-mark gloss.", "preference", "personal", False,
     [("Wipe-on poly", "technology"), ("bookcases", "concept"), ("intercoat", "concept")],
     [("Wipe-on poly", "bookcases", "APPLIES_TO")],
     "which finish lands the client bookcases and what application method gives the rubbed-effect appearance",
     "wipe on poly bookcase intercoat three coat thin rubbed"),
    # --- 36 ---
    ("Water-based lacquer covers the painted-piece finish schedule; no amber shift over white primer, faster recoat windows than oil-based, and the shop smells like almost nothing through the whole build.", "fact", "personal", False,
     [("Water-based lacquer", "technology"), ("white primer", "technology"), ("painted-piece", "concept")],
     [("Water-based lacquer", "painted-piece", "APPLIES_TO")],
     "which clear coat handles painted pieces without shifting the white and what other workshop benefit comes with it",
     "water based lacquer white primer painted amber shift recoat"),
    # --- 37 ---
    ("The urushi sample panel from the kyoto class sat curing under a damp box for four weeks; the final polish with tonoko and an oil paper brought the depth that no synthetic lacquer I've tried can match.", "milestone", "personal", False,
     [("urushi", "technology"), ("tonoko", "technology"), ("kyoto class", "event"), ("oil paper", "tool")],
     [("urushi", "tonoko", "USES")],
     "which Japanese lacquer sample from the kyoto class reached final polish and how was the depth achieved",
     "urushi tonoko kyoto class oil paper polish four week damp"),
    # --- 38 ---
    ("Dust collection on the finishing side is a downdraft table under the HEPA filter on a timer; pollen season plus an open window used to leave specks in the final shellac coat until that rig went in.", "problem", "personal", False,
     [("downdraft table", "tool"), ("HEPA filter", "tool"), ("shellac", "technology"), ("pollen", "concept")],
     [("HEPA filter", "pollen", "FIXES")],
     "which dust-collection rig fixed the pollen specks landing in the final shellac coat",
     "downdraft table hepa filter timer shellac pollen speck final"),
    # --- 39 ---
    ("The Matsumura chisels need a flatter back than the Narex to cut cleanly; first lapping session on the Shapton 1000 took forty minutes per chisel and the remaining set is on the schedule for this quarter.", "reference", "personal", False,
     [("Matsumura", "organization"), ("Narex", "organization"), ("chisel", "tool"), ("Shapton", "organization")],
     [("Matsumura", "Narex", "IMPROVES_ON")],
     "which chisel brand needs more back-lapping than the Narex and how long did the first one take",
     "matsumura narex chisel shapton 1000 back lap forty minutes"),
    # --- 40 ---
    ("Reference edges on the shooting board are kept straight by running a Veritas low-angle block over them every few sessions; the square reads dead-on after a quick pass even after heavy shooting of oak end grain.", "fact", "personal", False,
     [("Veritas", "organization"), ("low-angle block", "tool"), ("shooting board", "concept"), ("oak", "concept")],
     [("Veritas", "shooting board", "APPLIES_TO")],
     "how do the shooting-board reference edges stay square after heavy oak end-grain work",
     "veritas low angle block shooting board reference edge square oak"),
    # --- 41 ---
    ("Marking gauge work moved from a wheel gauge to a Japanese kebiki on the dovetail layout; the shallow scored line reads clearly in low light and the gauge body hooks cleanly over the board edge.", "preference", "personal", False,
     [("wheel gauge", "tool"), ("kebiki", "tool"), ("dovetail", "concept"), ("Marking gauge", "tool")],
     [("kebiki", "wheel gauge", "REPLACES")],
     "which Japanese marking gauge replaced the wheel gauge for dovetail layout and which property sold the swap",
     "kebiki wheel gauge dovetail marking shallow score low light"),
    # --- 42 ---
    ("Rip-cut duty inside the shop shifted to the ryoba's rip teeth from the western panel saw; long cuts down a board edge come out straighter with less correction and the muscle memory carried across quickly.", "milestone", "personal", False,
     [("ryoba", "tool"), ("panel saw", "tool"), ("rip teeth", "concept")],
     [("ryoba", "panel saw", "REPLACES")],
     "which side of the ryoba took over from the panel saw for in-shop rip cuts",
     "ryoba rip tooth panel saw rip cut board edge muscle memory"),
    # --- 43. noise ---
    ("Found an old jar of hand-mixed wood stain in the back of the paint cupboard and spent an hour cataloguing colours that no one remembered mixing.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Clamp inventory audit: eight Bessey K-Body parallels handle the carcase work, six Jorgensen hand-screws cover awkward angles, and a rack of F-clamps fills gaps when the parallels run out.", "reference", "personal", False,
     [("Bessey", "organization"), ("K-Body", "tool"), ("Jorgensen", "organization"), ("F-clamp", "tool")],
     [("Bessey", "Jorgensen", "APPLIES_TO")],
     "which clamps make up the shop inventory and how are they split across carcase and awkward-angle work",
     "bessey k body jorgensen hand screw f clamp inventory parallel"),
    # --- 45 ---
    ("Workbench face vise is a Benchcrafted Glide; installed after the screw on the original leg vise stripped under a hardwood plane-stop test and a modern acme thread just handles the load better.", "decision", "personal", False,
     [("Benchcrafted", "organization"), ("Glide", "tool"), ("leg vise", "tool"), ("acme thread", "concept")],
     [("Benchcrafted", "leg vise", "REPLACES")],
     "which face vise replaced the original leg vise and what failure mode on the previous one triggered the swap",
     "benchcrafted glide leg vise acme thread strip workbench face"),
    # --- 46 ---
    ("Wax versus oil on the bench top: pure beeswax-paste coat reapplied monthly keeps glue from bonding to the top while an oil-only top grabbed too hard and cost me a freshly-cut tenon last spring.", "problem", "personal", False,
     [("beeswax", "technology"), ("bench top", "concept"), ("tenon", "concept")],
     [("beeswax", "bench top", "APPLIES_TO")],
     "which bench-top treatment keeps glue from bonding and what incident drove the call away from oil-only",
     "beeswax bench top wax oil glue tenon bond monthly"),
    # --- 47 ---
    ("Humidity logbook keeps the shop at 42 percent plus-or-minus 5 percent year round; furniture that came out of a 60 percent glue-up in summer cracked a panel in January before I invested in the humidifier rig.", "reference", "personal", False,
     [("Humidity logbook", "concept"), ("humidifier", "tool"), ("cracked a panel", "error")],
     [("humidifier", "cracked a panel", "FIXES")],
     "which humidity range does the shop log hold and what failure drove the investment in the humidifier",
     "humidity logbook 42 percent humidifier panel crack January"),
    # --- 48 ---
    ("The Festool Domino DF500 loose tenons hit 8 mm, 10 mm, and 14 mm stock for most case work; the 6 mm tenons only come out for small box corners where a mortise chisel is overkill.", "reference", "personal", False,
     [("Festool Domino DF500", "tool"), ("loose tenon", "concept"), ("8 mm", "config"), ("14 mm", "config")],
     [("Festool Domino DF500", "loose tenon", "USES")],
     "which Domino tenon sizes cover case work and where does the 6 mm size get used instead",
     "festool domino df500 loose tenon 8 10 14 mm 6 mm case"),
    # --- 49 ---
    ("The Lie-Nielsen chisel-plane came in for the final flushing pass on plugged pocket holes; a regular block plane left halo marks and the chisel-plane gets the plug dead-level with the face veneer.", "fact", "personal", False,
     [("Lie-Nielsen", "organization"), ("chisel-plane", "tool"), ("pocket hole", "concept"), ("block plane", "tool")],
     [("chisel-plane", "block plane", "REPLACES")],
     "which specialised plane handles the final flushing pass on plugged pocket holes and which tool did it replace",
     "lie nielsen chisel plane block plane pocket hole plug flush"),
    # --- 50 ---
    ("Shop-safety audit from the spring workshop visit: dust mask upgrade to an elastomeric half-mask with P100 cartridges, and the shellac rag disposal now goes straight into a water-filled metal can.", "milestone", "personal", False,
     [("elastomeric half-mask", "tool"), ("P100", "config"), ("shellac rag", "technology"), ("metal can", "tool")],
     [("elastomeric half-mask", "P100", "USES")],
     "which safety upgrades came out of the spring shop audit for dust protection and finish-rag disposal",
     "elastomeric half mask p100 shellac rag metal can water spring"),
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
