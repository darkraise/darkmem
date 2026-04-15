"""One-off emitter for shared-base batch-066 — cross domain.

Slice: creative arts meets tech (digital-art tools, music production, film
editing, writing apps, hobby streaming, generative art, 3D printing). Writes
50 rows to data/v2/shared/batch_066.tmp.jsonl with ids shared-03251..03300. The
main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_066.tmp.jsonl"
ID_OFFSET = 3250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Procreate replaced Photoshop on the iPad for the daily sketch habit because the streamlined brush studio and Pencil pressure curve felt less hostile after a long workday.", "decision", "cross", False,
     [("Procreate", "tool"), ("Photoshop", "tool"), ("iPad", "infrastructure"), ("Pencil", "infrastructure")],
     [("Procreate", "Photoshop", "REPLACES")],
     "which iPad app took over for the everyday sketch routine and why",
     "tablet illustration brush studio pressure curve daily sketching habit"),
    # --- 2 ---
    ("Prefers Blender over Cinema 4D for the fan-art renders because the Geometry Nodes scatter system handles the hair-card forest without choking on the 6 GB VRAM budget of the RTX 3060.", "preference", "cross", False,
     [("Blender", "tool"), ("Cinema 4D", "tool"), ("Geometry Nodes", "concept"), ("RTX 3060", "infrastructure")],
     [("Blender", "Cinema 4D", "PREFERS")],
     "which 3D suite wins on the modest GPU and what feature seals it",
     "procedural scatter geometry nodes hair card forest render budget"),
    # --- 3 ---
    ("The 2026-03-22 EP master finally bounced out of Ableton Live with the Pro-Q 4 sidechain dialed in after Logic Pro's stock EQ kept flattening the sub on the kick.", "milestone", "cross", False,
     [("2026-03-22", "date"), ("Ableton Live", "tool"), ("Pro-Q 4", "tool"), ("Logic Pro", "tool")],
     [("Ableton Live", "Logic Pro", "REPLACES")],
     "when did the EP master actually print and what plugin chain made it work",
     "ep master bounce sidechain eq kick sub low end production"),
    # --- 4 ---
    ("DaVinci Resolve replaced Premiere Pro for the family wedding edit because the Fusion title preset survived the Proxmox NAS roundtrip without relinking every clip.", "decision", "cross", False,
     [("DaVinci Resolve", "tool"), ("Premiere Pro", "tool"), ("Fusion", "tool"), ("Proxmox", "infrastructure")],
     [("DaVinci Resolve", "Premiere Pro", "REPLACES")],
     "which NLE took over for the wedding cut and what pushed the swap",
     "nonlinear editor swap title template relink network storage workflow"),
    # --- 5 ---
    ("Scrivener holds the novel draft outline while iA Writer handles the daily morning pages because iA's grayscale focus mode keeps me from fiddling with chapter structure at 6am.", "architecture", "cross", False,
     [("Scrivener", "tool"), ("iA Writer", "tool")],
     [("iA Writer", "Scrivener", "PREFERS")],
     "how is the novel writing actually split between the two writing apps",
     "novel outline morning pages focus mode draft tooling separation"),
    # --- 6. noise ---
    ("Hold on, let me pull up the file.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("OBS Studio's hardware NVENC encoder replaced the software x264 path on the Twitch stream after the 2026-02-09 Subnautica run dropped a quarter of its frames during the leviathan chase.", "decision", "cross", False,
     [("OBS Studio", "tool"), ("NVENC", "technology"), ("x264", "library"), ("Twitch", "platform"), ("2026-02-09", "date"), ("Subnautica", "project")],
     [("NVENC", "x264", "REPLACES")],
     "what fixed the dropped frames on the Twitch stream that February night",
     "stream encoder hardware acceleration dropped frames game capture"),
    # --- 8 ---
    ("Figma replaced Adobe XD for the children's-book illustration storyboards because the auto-layout frames let Maya the editor leave inline comments without breaking the page flow.", "decision", "cross", False,
     [("Figma", "tool"), ("Adobe XD", "tool"), ("Maya", "person")],
     [("Figma", "Adobe XD", "REPLACES")],
     "which design tool runs the picture-book storyboarding now and who pushed for it",
     "storyboard collaboration auto layout inline comments editor review"),
    # --- 9 ---
    ("Reaper improves on Pro Tools for the podcast multitrack because the per-take FX chain costs nothing extra and the SWS extension's region-render macro shaves twenty minutes per episode.", "preference", "cross", False,
     [("Reaper", "tool"), ("Pro Tools", "tool"), ("SWS", "library")],
     [("Reaper", "Pro Tools", "IMPROVES_ON")],
     "which DAW handles the podcast better and what extension closes the gap",
     "podcast multitrack take fx chain region render macro extension"),
    # --- 10 ---
    ("The TouchDesigner generative-art piece for the 2026-04-26 gallery opening at Eastside Projects feeds Kinect skeleton data into a noise displacement on a Geometry SOP exported to Blender.", "architecture", "cross", False,
     [("TouchDesigner", "tool"), ("2026-04-26", "date"), ("Eastside Projects", "place"), ("Kinect", "infrastructure"), ("Blender", "tool")],
     [("TouchDesigner", "Kinect", "USES"), ("TouchDesigner", "Blender", "COMMUNICATES_WITH")],
     "how does the gallery installation pull body data into the rendered geometry",
     "generative art body tracking depth sensor noise displacement gallery"),
    # --- 11 ---
    ("Krita replaced Clip Studio Paint for the long-form comic linework because Krita's pop-up palette and brush stabilization on Wayland actually behaved on the Fedora workstation.", "decision", "cross", False,
     [("Krita", "tool"), ("Clip Studio Paint", "tool"), ("Wayland", "protocol"), ("Fedora", "platform")],
     [("Krita", "Clip Studio Paint", "REPLACES")],
     "which paint app took over for the comic line art on the Linux box",
     "comic linework brush stabilizer pop up palette display server fit"),
    # --- 12 ---
    ("Bambu Studio improves on Cura for the Voron 0.2 because the per-object seam painter drops the Benchy seam onto the back of the hull where the kids never spot it.", "preference", "cross", False,
     [("Bambu Studio", "tool"), ("Cura", "tool"), ("Voron 0.2", "infrastructure"), ("Benchy", "concept")],
     [("Bambu Studio", "Cura", "IMPROVES_ON")],
     "which slicer wins on the small printer and what feature wins it",
     "slicer comparison seam placement painter small printer print quality"),
    # --- 13 ---
    ("Frustration peaked when Lightroom Classic catalog corruption ate the 2026-01-30 Iceland aurora shoot and the Time Machine restore was three days stale.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Lightroom Classic", "tool"), ("2026-01-30", "date"), ("Iceland", "place"), ("Time Machine", "service")],
     [],
     "what wiped out the Iceland aurora photo work that January",
     "catalog corruption raw library backup gap aurora photography loss"),
    # --- 14 ---
    ("The 2026-04-01 launch of the p5.js generative collection on fxhash hit 80 mints in the first hour because the deterministic seed actually matched between the local sketch and the on-chain render.", "milestone", "cross", False,
     [("2026-04-01", "date"), ("p5.js", "library"), ("fxhash", "platform")],
     [("p5.js", "fxhash", "DEPLOYED_ON")],
     "when did the generative art drop sell out and what made the seeds line up",
     "generative collection drop deterministic seed on chain render mint"),
    # --- 15 ---
    ("Prefers PrusaSlicer over OrcaSlicer for the resin masters on the SL1S because the tilt parameters carry over from the SLA profile cleanly while OrcaSlicer keeps resetting the lift speed.", "preference", "cross", False,
     [("PrusaSlicer", "tool"), ("OrcaSlicer", "tool"), ("SL1S", "infrastructure")],
     [("PrusaSlicer", "OrcaSlicer", "PREFERS")],
     "which resin slicer behaves on the SL1S and what setting sticks",
     "resin slicer tilt parameter lift speed sla profile preservation"),
    # --- 16 ---
    ("Joy hit when the Splice subscription finally surfaced an MPC One drum kit on 2026-03-08 that Anya the producer had been hunting for since the EP started.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Splice", "service"), ("MPC One", "infrastructure"), ("2026-03-08", "date"), ("Anya", "person")],
     [("Splice", "MPC One", "USES")],
     "when did the missing drum kit finally show up and who had been searching",
     "sample subscription drum kit hunt producer collaboration discovery"),
    # --- 17 ---
    ("ComfyUI replaced Automatic1111 for the album-cover concepting workflow because the node graph keeps the LoRA stack reproducible across the 2026-03-12 cover and the lyric-video stills.", "decision", "cross", False,
     [("ComfyUI", "tool"), ("Automatic1111", "tool"), ("LoRA", "concept"), ("2026-03-12", "date")],
     [("ComfyUI", "Automatic1111", "REPLACES")],
     "which diffusion UI runs the album visuals now and what made it stick",
     "node graph diffusion workflow lora stack reproducibility cover art"),
    # --- 18 ---
    ("OctoPrint on the Raspberry Pi 4 lets the Bambu X1C and the Voron 2.4 share a single web UI on the workshop tablet even though the upstream Bambu firmware fights the API connection.", "architecture", "cross", False,
     [("OctoPrint", "tool"), ("Raspberry Pi 4", "infrastructure"), ("Bambu X1C", "infrastructure"), ("Voron 2.4", "infrastructure")],
     [("OctoPrint", "Raspberry Pi 4", "DEPLOYED_ON"), ("OctoPrint", "Bambu X1C", "CONFIGURES")],
     "how do both shop printers end up under one tablet UI",
     "print farm web ui shared dashboard firmware api conflict workshop"),
    # --- 19 ---
    ("Affinity Photo 2 replaced Photoshop for the band's tour-poster screen-print prep because the Affinity perpetual license sidesteps Adobe's annual renewal pain on the studio Mac mini.", "decision", "cross", False,
     [("Affinity Photo 2", "tool"), ("Photoshop", "tool"), ("Adobe", "organization"), ("Mac mini", "infrastructure")],
     [("Affinity Photo 2", "Photoshop", "REPLACES")],
     "what handles the screen print prep and why the swap from Adobe",
     "perpetual license screen print color separation studio workflow swap"),
    # --- 20 ---
    ("Curiosity bloomed the first time the Hydra live-coding sketch reacted to the modular synth's CV through an Expert Sleepers ES-9, and the resulting visual jam ran for two unbroken hours.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Hydra", "library"), ("Expert Sleepers ES-9", "infrastructure")],
     [("Hydra", "Expert Sleepers ES-9", "USES")],
     "what made the modular and the live coding finally jam together",
     "live coding visuals control voltage audio interface modular session"),
    # --- 21 ---
    ("The Wacom Cintiq Pro 27 replaced the iPad Pro on the desk for the freelance illustration deliverables because the 4K parallax-free glass actually matches the print proofs out of the studio.", "decision", "cross", False,
     [("Wacom Cintiq Pro 27", "infrastructure"), ("iPad Pro", "infrastructure")],
     [("Wacom Cintiq Pro 27", "iPad Pro", "REPLACES")],
     "which display tablet runs the freelance illustration delivery now",
     "pen display parallax color proof illustration freelance deliverable"),
    # --- 22 ---
    ("The 2026-02-19 short film cut sat in DaVinci Resolve on the Studio dongle license but the offline edit happened on a friend's Premiere Pro rig because Charlie only owns the Adobe suite.", "fact", "cross", False,
     [("2026-02-19", "date"), ("DaVinci Resolve", "tool"), ("Premiere Pro", "tool"), ("Charlie", "person")],
     [("DaVinci Resolve", "Premiere Pro", "COMMUNICATES_WITH")],
     "how did the short film edit shuttle between the two NLEs",
     "offline edit conform xml roundtrip nle handoff collaborator setup"),
    # --- 23 ---
    ("Ardour improves on Reaper for the field-recording ambient album because the JACK routing on the Linux laptop survives the LSP plugin chain when Reaper's bundled bridge crashes on the same chain.", "preference", "cross", False,
     [("Ardour", "tool"), ("Reaper", "tool"), ("JACK", "protocol"), ("LSP", "library")],
     [("Ardour", "Reaper", "IMPROVES_ON")],
     "which DAW survived the heavy plugin chain on the Linux laptop",
     "ambient field recording jack routing plugin bridge stability linux"),
    # --- 24 ---
    ("Notion replaced the messy Apple Notes scratch file for the screenplay character bible after the 2026-03-15 staged reading proved I needed cross-references between scene cards and backstory entries.", "decision", "cross", False,
     [("Notion", "tool"), ("Apple Notes", "tool"), ("2026-03-15", "date")],
     [("Notion", "Apple Notes", "REPLACES")],
     "where does the screenplay character bible live now and what triggered the move",
     "screenplay character bible cross reference scene card backstory move"),
    # --- 25 ---
    ("The Klipper firmware on the Voron 2.4 replaced Marlin once Input Shaper cut the ringing on the 2026-02-22 cosplay helmet print from visible bands to nothing the eye catches.", "milestone", "cross", False,
     [("Klipper", "tool"), ("Voron 2.4", "infrastructure"), ("Marlin", "tool"), ("Input Shaper", "algorithm"), ("2026-02-22", "date")],
     [("Klipper", "Marlin", "REPLACES")],
     "when did the ringing on the cosplay helmet print finally vanish",
     "firmware migration input shaper resonance ringing cosplay print quality"),
    # --- 26 ---
    ("Davinci's Magic Mask object-isolation tool replaced the rotoscoped mask on the 2026-02-28 music video because the AI tracker held the singer's hand silhouette through the whip-pan that the manual roto kept dropping.", "decision", "cross", False,
     [("Davinci", "tool"), ("Magic Mask", "tool"), ("2026-02-28", "date")],
     [("Magic Mask", "Davinci", "IS_A")],
     "what replaced the painful manual roto on that music video shot",
     "music video roto object isolation ai tracker whip pan handheld"),
    # --- 27 ---
    ("Prefers Substance Painter over Quixel Mixer for the prop texturing pipeline because the Substance smart materials carry the wear masks straight into Unreal Engine 5 without baking again.", "preference", "cross", False,
     [("Substance Painter", "tool"), ("Quixel Mixer", "tool"), ("Unreal Engine 5", "framework")],
     [("Substance Painter", "Quixel Mixer", "PREFERS"), ("Substance Painter", "Unreal Engine 5", "COMMUNICATES_WITH")],
     "which texture tool runs the prop pipeline and why",
     "smart material wear mask prop texturing engine handoff bake free"),
    # --- 28 ---
    ("Anxiety set in when the OBS Studio NDI source from the secondary cam dropped on the 2026-03-07 charity stream and the on-screen telemetry reverted to the Counter-Strike spectator default.", "problem", "cross", False,
     [("Anxiety", "emotion"), ("OBS Studio", "tool"), ("NDI", "protocol"), ("2026-03-07", "date"), ("Counter-Strike", "project")],
     [],
     "what went sideways on the charity stream that March evening",
     "ndi source dropout secondary camera charity stream telemetry overlay"),
    # --- 29 ---
    ("Logic Pro's Mastering Assistant replaced the iZotope Ozone 11 chain on the 2026-03-29 single because the Apple model held the loudness target without smashing the transient on the snare.", "decision", "cross", False,
     [("Logic Pro", "tool"), ("Mastering Assistant", "tool"), ("iZotope Ozone 11", "tool"), ("2026-03-29", "date")],
     [("Mastering Assistant", "iZotope Ozone 11", "REPLACES")],
     "which mastering chain handled the late-March single and why",
     "mastering assistant loudness target transient preservation single release"),
    # --- 30 ---
    ("The Glowforge Pro and a Cricut Maker 3 share the makerspace bench but the laser handles the 2026-04-12 birthday-card inserts because the Cricut blade tears the cotton paper at the curves.", "architecture", "cross", False,
     [("Glowforge Pro", "infrastructure"), ("Cricut Maker 3", "infrastructure"), ("2026-04-12", "date")],
     [("Glowforge Pro", "Cricut Maker 3", "REPLACES")],
     "how does the makerspace decide between the laser and the cutter",
     "laser cutter blade plotter cotton paper birthday card insert workflow"),
    # --- 31 ---
    ("Zola the violinist insisted Sibelius stays on the score side because MuseScore 4's playback still mangles the spiccato articulation on the chamber-quartet preview.", "preference", "cross", False,
     [("Zola", "person"), ("Sibelius", "tool"), ("MuseScore 4", "tool")],
     [("Sibelius", "MuseScore 4", "PREFERS")],
     "which scoring program won the chamber piece argument and who pushed",
     "scoring software articulation playback chamber quartet preview choice"),
    # --- 32 ---
    ("Fusion 360 generated the bracket STL for the Bambu X1C 3D-print of the camera rig on 2026-03-31 and the parametric sketch let me dial the GoPro mount to the 1/4-20 thread without redrawing.", "fact", "cross", False,
     [("Fusion 360", "tool"), ("STL", "concept"), ("Bambu X1C", "infrastructure"), ("2026-03-31", "date"), ("GoPro", "infrastructure")],
     [("Fusion 360", "Bambu X1C", "USES")],
     "how did the camera-rig bracket actually come together for the late-March print",
     "parametric cad sketch print export camera mount thread iteration"),
    # --- 33 ---
    ("The Cherry MX Brown keyboard on the writing desk replaced the membrane Magic Keyboard once the Scrivener typing endurance for the 50,000-word draft month started giving the wrist real grief.", "decision", "cross", False,
     [("Cherry MX Brown", "infrastructure"), ("Magic Keyboard", "infrastructure"), ("Scrivener", "tool")],
     [("Cherry MX Brown", "Magic Keyboard", "REPLACES")],
     "what swapped on the writing desk and what triggered it",
     "mechanical keyboard switch swap typing endurance long form drafting wrist"),
    # --- 34. noise ---
    ("Quick reminder, dinner is at seven.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Streamlabs OBS broke its plugin loader on the 2026-02-14 update so the Twitch overlay pipeline reverted to vanilla OBS Studio with the StreamElements browser source instead.", "problem", "cross", False,
     [("Streamlabs OBS", "tool"), ("2026-02-14", "date"), ("Twitch", "platform"), ("OBS Studio", "tool"), ("StreamElements", "service")],
     [("OBS Studio", "Streamlabs OBS", "REPLACES")],
     "what broke on the streaming setup and how did the overlays survive",
     "plugin loader regression streaming overlay browser source fallback"),
    # --- 36 ---
    ("The Apple ProRes 422 master out of DaVinci Resolve filled 380 GB on the 2026-02-19 short film deliverable so the Synology DS923+ now has a dedicated media volume on the four-drive SHR pool.", "architecture", "cross", False,
     [("Apple ProRes 422", "concept"), ("DaVinci Resolve", "tool"), ("2026-02-19", "date"), ("Synology DS923+", "infrastructure"), ("SHR", "concept")],
     [("DaVinci Resolve", "Synology DS923+", "USES")],
     "where does the short film master live and how big did it get",
     "prores master deliverable nas media volume raid pool film storage"),
    # --- 37 ---
    ("Inkscape replaced Adobe Illustrator for the band's merch SVG cuts because the Affinity export to the Cricut workflow kept rasterizing strokes that Inkscape's SVG plain output preserved cleanly.", "decision", "cross", False,
     [("Inkscape", "tool"), ("Adobe Illustrator", "tool"), ("Affinity", "tool"), ("Cricut", "infrastructure")],
     [("Inkscape", "Adobe Illustrator", "REPLACES")],
     "which vector tool runs the merch cut files now and what forced the swap",
     "vector tool merch svg cricut cut stroke preservation export pipeline"),
    # --- 38 ---
    ("The Yamaha THR30II Wireless on the desk replaced the Kemper Profiler for the late-night practice sessions because the THR's Bluetooth backing track piping doesn't wake the kids.", "decision", "cross", False,
     [("Yamaha THR30II Wireless", "infrastructure"), ("Kemper Profiler", "infrastructure"), ("Bluetooth", "protocol")],
     [("Yamaha THR30II Wireless", "Kemper Profiler", "REPLACES")],
     "what runs late-night guitar practice now and why",
     "desktop amp profiler swap silent practice bluetooth backing track"),
    # --- 39 ---
    ("Prefers TouchDesigner over Notch for the projection-mapped stage backdrop because TouchDesigner's free non-commercial license covers the small-venue shows that Notch's runtime billing would punish.", "preference", "cross", False,
     [("TouchDesigner", "tool"), ("Notch", "tool")],
     [("TouchDesigner", "Notch", "PREFERS")],
     "which projection tool wins for the small venue shows and why",
     "projection mapping stage visuals license cost small venue runtime"),
    # --- 40 ---
    ("The 2026-03-25 release of the lo-fi mixtape on Bandcamp sold 47 cassettes in the first week because the National Audio dub run finished on time and the Discogs cross-listing pulled the collectors in.", "milestone", "cross", False,
     [("2026-03-25", "date"), ("Bandcamp", "platform"), ("National Audio", "organization"), ("Discogs", "platform")],
     [("Bandcamp", "Discogs", "COMMUNICATES_WITH")],
     "when did the cassette mixtape drop and what drove the early sales",
     "lofi mixtape cassette release platform listing collector channel"),
    # --- 41 ---
    ("Lightroom mobile presets sync through Adobe Creative Cloud onto the iPhone 15 Pro so the street-photography edits from the 2026-03-08 Tokyo walk match the desktop catalog before the WiFi reaches home.", "architecture", "cross", False,
     [("Lightroom", "tool"), ("Adobe Creative Cloud", "service"), ("iPhone 15 Pro", "infrastructure"), ("2026-03-08", "date"), ("Tokyo", "place")],
     [("Lightroom", "Adobe Creative Cloud", "USES")],
     "how do the on-the-road photo edits stay in sync with the desk",
     "mobile preset sync cloud catalog street photography travel edit"),
    # --- 42 ---
    ("ZBrush 2026 replaced Nomad Sculpt on the iPad for the bust commission because the Dynamesh resolution at 4 million points needed the M2 desktop GPU and the side-view symmetry tools hold up better.", "decision", "cross", False,
     [("ZBrush 2026", "tool"), ("Nomad Sculpt", "tool"), ("iPad", "infrastructure"), ("Dynamesh", "algorithm"), ("M2", "infrastructure")],
     [("ZBrush 2026", "Nomad Sculpt", "REPLACES")],
     "which sculpting tool runs the bust commission and why the move",
     "digital sculpting commission dynamesh resolution symmetry tablet swap"),
    # --- 43 ---
    ("The Voicemeeter Banana virtual mixer on the streaming PC routes the Reaper monitor mix into OBS Studio without doubling the latency that a single ASIO driver would cause on the X32 interface.", "architecture", "cross", False,
     [("Voicemeeter Banana", "tool"), ("Reaper", "tool"), ("OBS Studio", "tool"), ("ASIO", "protocol"), ("X32", "infrastructure")],
     [("Voicemeeter Banana", "Reaper", "USES"), ("Voicemeeter Banana", "OBS Studio", "COMMUNICATES_WITH")],
     "how does the DAW monitor mix make it into the stream cleanly",
     "virtual audio mixer routing daw to streaming pc latency interface"),
    # --- 44 ---
    ("Despair flickered when the Bambu X1C jammed on the 2026-04-02 cosplay pauldron print twelve hours in and the AMS spool sensor missed the runout that should have paused it cleanly.", "problem", "cross", False,
     [("Despair", "emotion"), ("Bambu X1C", "infrastructure"), ("2026-04-02", "date"), ("AMS", "infrastructure")],
     [],
     "what went wrong on the long cosplay print and where did detection fail",
     "filament runout sensor miss long print failure ams cosplay armor"),
    # --- 45 ---
    ("Capture One replaced Lightroom Classic for the studio fashion shoot tethering on 2026-03-01 because Capture One's Sony tether reconnected after the cable bump that froze the Lightroom session mid-set.", "decision", "cross", False,
     [("Capture One", "tool"), ("Lightroom Classic", "tool"), ("2026-03-01", "date"), ("Sony", "organization")],
     [("Capture One", "Lightroom Classic", "REPLACES")],
     "which tethered capture app runs the studio shoots now and why",
     "tethered capture session reconnect cable bump fashion studio swap"),
    # --- 46 ---
    ("Prefers Reason 13's Combinator over Native Instruments Reaktor for sound design sketches because Reason's CV cable view actually shows the routing without the Reaktor patch becoming a wire spaghetti.", "preference", "cross", False,
     [("Reason 13", "tool"), ("Combinator", "tool"), ("Native Instruments Reaktor", "tool")],
     [("Reason 13", "Native Instruments Reaktor", "PREFERS")],
     "which modular sound-design environment wins on readability",
     "modular sound design cv routing patch readability sketch comparison"),
    # --- 47 ---
    ("Pride hit when the 2026-04-05 Indie Game Festival accepted the pixel-art puzzler that I'd been making in Aseprite and exporting tilesets through LDtk into the Godot 4 project.", "milestone", "cross", False,
     [("Pride", "emotion"), ("2026-04-05", "date"), ("Indie Game Festival", "event"), ("Aseprite", "tool"), ("LDtk", "tool"), ("Godot 4", "framework")],
     [("LDtk", "Godot 4", "COMMUNICATES_WITH"), ("Aseprite", "LDtk", "USES")],
     "when did the pixel puzzler get into the festival and what tools shipped it",
     "pixel art puzzle indie game festival tileset pipeline acceptance"),
    # --- 48 ---
    ("The Obsidian vault holds the worldbuilding wiki for the fantasy series while Scrivener still owns the chapter prose because the Obsidian graph view exposes the magic-system contradictions Scrivener hides.", "architecture", "cross", False,
     [("Obsidian", "tool"), ("Scrivener", "tool")],
     [("Obsidian", "Scrivener", "PREFERS")],
     "how is the fantasy worldbuilding split between the two writing tools",
     "worldbuilding wiki graph view contradiction prose chapter split"),
    # --- 49 ---
    ("Catalyst Wedge improves on Plumb in the Houdini-to-Unreal asset pipeline because the Catalyst preset preserves the Vellum cloth attributes through the FBX export that Plumb keeps stripping.", "preference", "cross", False,
     [("Catalyst Wedge", "tool"), ("Plumb", "tool"), ("Houdini", "tool"), ("Unreal", "framework"), ("Vellum", "library"), ("FBX", "concept")],
     [("Catalyst Wedge", "Plumb", "IMPROVES_ON"), ("Houdini", "Unreal", "COMMUNICATES_WITH")],
     "which exporter wins on the Houdini to Unreal cloth pipeline",
     "houdini unreal asset pipeline cloth attribute fbx export comparison"),
    # --- 50 ---
    ("The CDM article on 2026-03-30 about Disting NT firmware tipped me to a granular sampler algorithm that replaced the Clouds clone in the eurorack rig for the ambient set.", "reference", "cross", False,
     [("CDM", "publication"), ("2026-03-30", "date"), ("Disting NT", "infrastructure"), ("Clouds", "infrastructure")],
     [("Disting NT", "Clouds", "REPLACES")],
     "which article surfaced the granular module that took over from the Clouds clone",
     "modular synth firmware granular sampler eurorack ambient set article"),
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
