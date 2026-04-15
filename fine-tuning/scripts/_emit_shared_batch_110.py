"""One-off emitter for shared-base batch-110 — cross domain.

Slice: photography meets tech (mirrorless bodies, computational phones, RAW
editors, culling, backup, print/gallery, bags/filters, film-scan pipelines,
Leica M hobby). Writes 50 rows to data/v2/shared/batch_110.tmp.jsonl with ids
shared-05451..05500. The main session aggregates the tmp file into shared.jsonl
after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_110.tmp.jsonl"
ID_OFFSET = 5450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Capture One replaced Lightroom Classic as the primary RAW editor on 2026-02-12 because the Fujifilm X-T5 film simulations rendered faithfully in Capture One while Adobe's profiles kept crushing the Classic Chrome shadows.", "decision", "cross", False,
     [("Capture One", "tool"), ("Lightroom Classic", "tool"), ("2026-02-12", "date"), ("Fujifilm X-T5", "infrastructure"), ("Adobe", "organization"), ("Classic Chrome", "concept")],
     [("Capture One", "Lightroom Classic", "REPLACES")],
     "when did the primary RAW editor switch and what Fuji rendering issue pushed it",
     "raw editor swap fujifilm film simulation profile shadow rendering"),
    # --- 2 ---
    ("Photo Mechanic improves on Lightroom Classic's culling because the preview cache reads the embedded JPEGs off the Sony A7 IV cards at roughly five times the speed Lightroom needs to build 1:1 renders.", "decision", "cross", False,
     [("Photo Mechanic", "tool"), ("Lightroom Classic", "tool"), ("Sony A7 IV", "infrastructure")],
     [("Photo Mechanic", "Lightroom Classic", "IMPROVES_ON")],
     "which culling tool wins for tight wedding turnarounds and why",
     "culling embedded jpeg preview cache card ingest speed wedding"),
    # --- 3 ---
    ("Negative Lab Pro improves on ColorPerfect for the Epson V600 scans because the per-stock Portra 400 profile in NLP handles the orange mask inversion without the manual curve gymnastics ColorPerfect needs.", "decision", "cross", False,
     [("Negative Lab Pro", "tool"), ("ColorPerfect", "tool"), ("Epson V600", "infrastructure"), ("Portra 400", "concept")],
     [("Negative Lab Pro", "ColorPerfect", "IMPROVES_ON")],
     "why did the C-41 scan pipeline move off ColorPerfect",
     "film inversion color negative orange mask stock profile scanner pipeline"),
    # --- 4 ---
    ("The Fujifilm X-T5 replaced the Sony A7 III as the daily-carry body on 2026-01-18 because the in-camera JPEG with Classic Neg ended the Lightroom import step for casual street work.", "milestone", "cross", False,
     [("Fujifilm X-T5", "infrastructure"), ("Sony A7 III", "infrastructure"), ("2026-01-18", "date"), ("Classic Neg", "concept"), ("Lightroom", "tool")],
     [("Fujifilm X-T5", "Sony A7 III", "REPLACES")],
     "when did the daily carry camera change and what workflow benefit pushed it",
     "mirrorless body swap jpeg straight out of camera workflow shortcut"),
    # --- 5 ---
    ("Prefers the Leica M11 over the Q3 for the weekend street hobby because the 60-megapixel optical rangefinder workflow slows the shot down in a way the Q3's autofocus never replicates.", "preference", "cross", False,
     [("Leica M11", "infrastructure"), ("Q3", "infrastructure")],
     [("Leica M11", "Q3", "PREFERS")],
     "which Leica body wins for the deliberate hobby shooting and why",
     "rangefinder versus autofocus deliberate shooting pace hobby street"),
    # --- 6. noise ---
    ("Hold on, I need a moment to line that up.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("DxO PhotoLab 8's DeepPRIME XD noise reduction improves on Lightroom's AI Denoise for the Nikon Z8 ISO 12800 concert files because DxO recovers the cymbal shimmer without smearing the hi-hat stand.", "decision", "cross", False,
     [("DxO PhotoLab 8", "tool"), ("Lightroom", "tool"), ("Nikon Z8", "infrastructure")],
     [("DxO PhotoLab 8", "Lightroom", "IMPROVES_ON")],
     "which denoiser wins for high-ISO concert work on the Nikon and why",
     "deep learning noise reduction high iso concert shimmer detail"),
    # --- 8 ---
    ("The tethered-shooting rig for the 2026-03-07 product set ran Capture One Pro into a 12-inch MacBook Pro over a Tether Tools TetherPro cable because the Sony Imaging Edge link dropped after roughly 80 frames.", "architecture", "cross", False,
     [("2026-03-07", "date"), ("Capture One Pro", "tool"), ("MacBook Pro", "infrastructure"), ("Tether Tools", "organization"), ("Sony Imaging Edge", "tool")],
     [("Capture One Pro", "Sony Imaging Edge", "REPLACES")],
     "how was the March product shoot tethered and what tool got dropped",
     "tethered shooting usb cable session software drop frame reliability"),
    # --- 9 ---
    ("darktable replaced Lightroom CC on the Linux laptop because the Lightroom mobile sync kept silently downgrading the Pixel 9 Pro HDR+ DNGs to 8-bit on the Arch desktop.", "decision", "cross", False,
     [("darktable", "tool"), ("Lightroom CC", "tool"), ("Linux", "platform"), ("Pixel 9 Pro", "infrastructure"), ("Arch", "platform"), ("DNG", "concept")],
     [("darktable", "Lightroom CC", "REPLACES")],
     "why did the Linux editing stack move off Lightroom CC for Pixel DNGs",
     "linux raw editor cloud sync bit depth downgrade computational dng"),
    # --- 10 ---
    ("The 2026-02-28 Backblaze restore of the Iceland catalog took 14 hours because the personal B2 bucket had 640 gigabytes of Leica M11 DNGs and the residential fiber capped the pull at 120 megabits.", "problem", "cross", False,
     [("2026-02-28", "date"), ("Backblaze", "service"), ("Iceland", "place"), ("B2", "service"), ("Leica M11", "infrastructure"), ("DNG", "concept")],
     [("Backblaze", "B2", "IS_A")],
     "how long did the Iceland catalog restore take and what throttled it",
     "cloud backup restore duration raw archive residential bandwidth cap"),
    # --- 11 ---
    ("The primary photo archive lives on a Synology DS923+ running DSM Photos with a nightly Hyper Backup push to Backblaze B2 because losing the 2020 wedding take once was enough.", "architecture", "cross", False,
     [("Synology DS923+", "infrastructure"), ("DSM Photos", "service"), ("Hyper Backup", "tool"), ("Backblaze B2", "service")],
     [("DSM Photos", "Synology DS923+", "DEPLOYED_ON"), ("Hyper Backup", "Backblaze B2", "COMMUNICATES_WITH")],
     "how does the photo library stay safe across the NAS and the cloud",
     "nas library dsm photos nightly offsite backup versioned retention"),
    # --- 12 ---
    ("Pixieset replaced SmugMug for client gallery delivery on 2026-01-29 because the Pixieset proofing PIN workflow and the store-credit handoff both integrated with the Studio Ninja booking records.", "milestone", "cross", False,
     [("Pixieset", "service"), ("SmugMug", "service"), ("2026-01-29", "date"), ("Studio Ninja", "tool")],
     [("Pixieset", "SmugMug", "REPLACES"), ("Pixieset", "Studio Ninja", "COMMUNICATES_WITH")],
     "when did client gallery delivery move off SmugMug and what made Pixieset fit",
     "client gallery proofing store credit booking integration handoff"),
    # --- 13 ---
    ("Nations Photo Lab replaced Printique for the large-format family prints because Nations' Fuji Crystal Archive metallic paper matched the reference print from the 2024 Tokyo test run better than Printique's latest match.", "decision", "cross", False,
     [("Nations Photo Lab", "organization"), ("Printique", "organization"), ("Fuji Crystal Archive", "concept"), ("Tokyo", "place")],
     [("Nations Photo Lab", "Printique", "REPLACES")],
     "which print lab took over for family metallic prints and why",
     "print lab paper metallic match reference print large format swap"),
    # --- 14 ---
    ("Frustration took over on 2026-03-21 when the Peak Design Everyday Backpack V2 stopped fitting the Wandrd Rollo hip pouch because the V2's side access zipper fouled the buckle at the top-handle seam.", "problem", "cross", False,
     [("Frustration", "emotion"), ("2026-03-21", "date"), ("Peak Design", "organization"), ("Wandrd", "organization")],
     [],
     "what went wrong with the new bag and pouch combination",
     "camera bag accessory fit side access zipper hip pouch buckle conflict"),
    # --- 15 ---
    ("Prefers NISI magnetic filters over Moment's drop-in system for the X-T5 because the NISI V7 base ring holds the polarizer and the 6-stop ND without the flare the Moment lens cap keeps introducing.", "preference", "cross", False,
     [("NISI", "organization"), ("Moment", "organization"), ("X-T5", "infrastructure")],
     [("NISI", "Moment", "PREFERS")],
     "which filter system wins for the Fuji landscape rig and why",
     "magnetic filter system polarizer nd stack flare control landscape"),
    # --- 16 ---
    ("The Pakon F135 replaced the Epson V600 for color negative scans on 2026-02-09 because the Pakon's DigitalICE-free workflow handled a roll in under 90 seconds and the V600 took 25 minutes with grain-peaking enabled.", "milestone", "cross", False,
     [("Pakon F135", "infrastructure"), ("Epson V600", "infrastructure"), ("2026-02-09", "date")],
     [("Pakon F135", "Epson V600", "REPLACES")],
     "when did the color negative scan pipeline move to the Pakon",
     "dedicated film scanner roll throughput flatbed comparison workflow"),
    # --- 17 ---
    ("The Fujifilm X-Raw Studio offload runs through the X-T5 as a JPEG engine on a USB-C tether so the existing Classic Neg recipes re-render without burning laptop CPU in Capture One.", "architecture", "cross", False,
     [("Fujifilm X-Raw Studio", "tool"), ("X-T5", "infrastructure"), ("Classic Neg", "concept"), ("Capture One", "tool")],
     [("Fujifilm X-Raw Studio", "X-T5", "USES")],
     "how does the recipe re-render skip the laptop's CPU",
     "in camera jpeg engine raw reprocess recipe tether offload"),
    # --- 18 ---
    ("Relief hit when the 2026-02-04 Sony A7 IV firmware 3.00 fixed the Monitor+Control tethering dropout that plagued the Capture One sessions for four months.", "milestone", "cross", False,
     [("Relief", "emotion"), ("2026-02-04", "date"), ("Sony A7 IV", "infrastructure"), ("Capture One", "tool")],
     [("Sony A7 IV", "Capture One", "COMMUNICATES_WITH")],
     "when did the Sony tethering dropout get a firmware fix",
     "firmware release tether session stability monitor control usb"),
    # --- 19 ---
    ("iPhone 16 Pro ProRAW shots flow into Lightroom CC via iCloud because the Adobe camera profile still beats Apple's default ProRAW rendering for the high-contrast mixed-light shots Mei takes at the noodle shop.", "architecture", "cross", False,
     [("iPhone 16 Pro", "infrastructure"), ("ProRAW", "concept"), ("Lightroom CC", "tool"), ("iCloud", "service"), ("Adobe", "organization"), ("Apple", "organization"), ("Mei", "person")],
     [("Lightroom CC", "iCloud", "USES"), ("Adobe", "Apple", "PREFERS")],
     "how do the iPhone ProRAW files actually reach the editor and why",
     "proraw pipeline cloud sync camera profile mixed lighting phone raw"),
    # --- 20 ---
    ("The Wandrd Prvke 31 replaced the Peak Design Travel Backpack 45 as the carry-on for the 2026-05-17 Tokyo trip because the Prvke's side-zip got the M11 and the 35 Summicron out during the Keisei Skyliner boarding without opening the main panel.", "decision", "cross", False,
     [("Wandrd Prvke 31", "infrastructure"), ("Peak Design Travel Backpack 45", "infrastructure"), ("2026-05-17", "date"), ("Tokyo", "place"), ("M11", "infrastructure"), ("35 Summicron", "infrastructure"), ("Keisei Skyliner", "service")],
     [("Wandrd Prvke 31", "Peak Design Travel Backpack 45", "REPLACES")],
     "which bag took over for the Japan trip and what carry-on pain fixed it",
     "camera travel bag swap side access rangefinder quick draw transit"),
    # --- 21 ---
    ("Printique's Fujiflex print from the 2025 Dolomites panorama finally shipped on 2026-03-15 after a three-week reprint dispute over the magenta cast in the sky gradient.", "milestone", "cross", False,
     [("Printique", "organization"), ("Fujiflex", "concept"), ("Dolomites", "place"), ("2026-03-15", "date")],
     [],
     "when did the Dolomites Fujiflex print finally land",
     "large format print dispute magenta cast gradient reprint delay"),
    # --- 22 ---
    ("The Saal Digital photo book for the 2026-04-08 engagement gift replaced the Artifact Uprising mock because Saal's lay-flat binding and the matte Hahnemühle paper upgrade both landed under the Artifact retail price.", "decision", "cross", False,
     [("Saal Digital", "organization"), ("2026-04-08", "date"), ("Artifact Uprising", "organization"), ("Hahnemühle", "organization")],
     [("Saal Digital", "Artifact Uprising", "REPLACES")],
     "which photo book vendor won the engagement gift and why",
     "photo book lay flat binding paper stock upgrade price comparison"),
    # --- 23 ---
    ("Prefers Photo Mechanic Plus's catalog over Bridge for keywording the Leica archive because Photo Mechanic's IPTC stationery pad tags the year and the roll number in one keystroke across 300 frames.", "preference", "cross", False,
     [("Photo Mechanic Plus", "tool"), ("Bridge", "tool"), ("Leica", "organization"), ("IPTC", "concept")],
     [("Photo Mechanic Plus", "Bridge", "PREFERS")],
     "which tool handles the Leica archive keywording and why",
     "iptc stationery pad batch keyword archive catalog film rolls"),
    # --- 24 ---
    ("The Epson V600 scan workflow flows through VueScan 9.8 into Negative Lab Pro on the Lightroom catalog because the bundled Epson Scan 2 software blew out the highlights on Ektar 100 skies consistently.", "architecture", "cross", False,
     [("Epson V600", "infrastructure"), ("VueScan 9.8", "tool"), ("Negative Lab Pro", "tool"), ("Lightroom", "tool"), ("Epson Scan 2", "tool"), ("Ektar 100", "concept")],
     [("VueScan 9.8", "Epson Scan 2", "REPLACES"), ("VueScan 9.8", "Negative Lab Pro", "COMMUNICATES_WITH")],
     "how does a roll of Ektar actually get from the V600 into the catalog",
     "flatbed scan driver alternative highlight retention color negative"),
    # --- 25 ---
    ("The 2026-03-05 Canon EOS R5 firmware 2.2.0 bricked the Atomos Ninja V recording handshake over HDMI for three hours until the rollback utility restored 2.1.1.", "problem", "cross", False,
     [("2026-03-05", "date"), ("Canon EOS R5", "infrastructure"), ("Atomos Ninja V", "infrastructure"), ("HDMI", "protocol")],
     [("Canon EOS R5", "Atomos Ninja V", "COMMUNICATES_WITH")],
     "what broke the external recorder handshake on the Canon and how was it recovered",
     "mirrorless firmware regression external recorder handshake rollback"),
    # --- 26 ---
    ("Curiosity drove the 2026-02-22 experiment of pairing the Leica M11 with the Voigtländer 35 Nokton II because the 1.2 aperture finally let the rangefinder beat the Q3's native lens in low window-light.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("2026-02-22", "date"), ("Leica M11", "infrastructure"), ("Voigtländer 35 Nokton II", "infrastructure"), ("Q3", "infrastructure")],
     [("Leica M11", "Voigtländer 35 Nokton II", "USES")],
     "what lens pairing let the rangefinder beat the fixed lens body in low light",
     "rangefinder fast prime low light aperture comparison window light"),
    # --- 27 ---
    ("Google Photos replaced iCloud Photos as the phone backup for Julian's casual shots because the unlimited storage trick with the Pixel 9 Pro survived the 2026 policy changes his iCloud tier didn't.", "decision", "cross", False,
     [("Google Photos", "service"), ("iCloud Photos", "service"), ("Julian", "person"), ("Pixel 9 Pro", "infrastructure")],
     [("Google Photos", "iCloud Photos", "REPLACES")],
     "why did Julian's phone backup move off iCloud Photos",
     "phone photo backup storage policy change casual capture swap"),
    # --- 28 ---
    ("Prefers tethering the Sony A7 IV into Capture One via Cascable Studio on the iPad Pro over Imaging Edge on the laptop because the iPad workflow lets the art director approve frames on a calibrated screen at arm's length.", "preference", "cross", False,
     [("Sony A7 IV", "infrastructure"), ("Capture One", "tool"), ("Cascable Studio", "tool"), ("iPad Pro", "infrastructure"), ("Imaging Edge", "tool")],
     [("Cascable Studio", "Imaging Edge", "PREFERS")],
     "which tether target wins for the Sony studio shoots and why",
     "ipad tether workflow art director proof calibrated display studio"),
    # --- 29 ---
    ("Zenfolio replaced SmugMug for the 2026-04-20 portrait mini-session microsite because Zenfolio's built-in session booking page bundled the deposit capture Stripe link cleanly.", "decision", "cross", False,
     [("Zenfolio", "service"), ("SmugMug", "service"), ("2026-04-20", "date"), ("Stripe", "service")],
     [("Zenfolio", "SmugMug", "REPLACES"), ("Zenfolio", "Stripe", "COMMUNICATES_WITH")],
     "which gallery host took over for the April mini-sessions and why",
     "mini session booking microsite deposit capture payment integration"),
    # --- 30 ---
    ("The shared ingest script written in Python 3.12 copies CFexpress cards into the 2026/03 Synology share, runs ExifTool rename, and flags the Leica files with a project tag before Lightroom Classic ever sees the folder.", "architecture", "cross", False,
     [("Python 3.12", "language"), ("CFexpress", "infrastructure"), ("Synology", "infrastructure"), ("ExifTool", "tool"), ("Leica", "organization"), ("Lightroom Classic", "tool")],
     [("ExifTool", "Synology", "DEPLOYED_ON")],
     "how do cards ingest before the editor opens the catalog",
     "ingest script card copy rename exif tag automation pre import"),
    # --- 31 ---
    ("The Moment T-Series 58mm lens on the iPhone 16 Pro replaced the Sony RX100 VII in the everyday pocket rotation because the iPhone's ProRes recording covered the coffee-shop b-roll without a second battery.", "decision", "cross", False,
     [("Moment T-Series", "infrastructure"), ("iPhone 16 Pro", "infrastructure"), ("Sony RX100 VII", "infrastructure"), ("ProRes", "concept")],
     [("iPhone 16 Pro", "Sony RX100 VII", "REPLACES")],
     "what pocket camera dropped out of rotation and what made the phone cover it",
     "phone lens add on compact camera displacement video everyday carry"),
    # --- 32 ---
    ("The Nikon Z8 paired with the Profoto A10 hot-shoe trigger runs the ambient balance for the 2026-06-14 outdoor portrait session because the Air TTL handshake survives the high-speed-sync past 1/8000.", "architecture", "cross", False,
     [("Nikon Z8", "infrastructure"), ("Profoto A10", "infrastructure"), ("2026-06-14", "date"), ("Air TTL", "protocol")],
     [("Profoto A10", "Nikon Z8", "COMMUNICATES_WITH")],
     "how does the June outdoor portrait session handle flash and ambient",
     "hot shoe trigger ttl high speed sync ambient balance outdoor portrait"),
    # --- 33 ---
    ("Prefers the Fujifilm XF 23mm f/1.4 WR over the XF 23mm f/2 WR on the X-T5 because the new linear motor survives the tethered eye-AF handoff Capture One demands during the studio block.", "preference", "cross", False,
     [("Fujifilm XF 23mm f/1.4 WR", "infrastructure"), ("XF 23mm f/2 WR", "infrastructure"), ("X-T5", "infrastructure"), ("Capture One", "tool")],
     [("Fujifilm XF 23mm f/1.4 WR", "XF 23mm f/2 WR", "PREFERS")],
     "which Fuji 23mm wins for the tethered studio block and why",
     "linear motor autofocus tether eye af handoff studio session"),
    # --- 34. noise ---
    ("Hmm, let me think about the light a second.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Nik Collection 7 Silver Efex plugin runs inside Capture One Pro as a smart-object roundtrip because the Fuji Acros 100 recipe still loses the micro-contrast the Silver Efex grain structure adds back.", "architecture", "cross", False,
     [("Nik Collection 7", "tool"), ("Silver Efex", "tool"), ("Capture One Pro", "tool"), ("Acros 100", "concept")],
     [("Silver Efex", "Capture One Pro", "DEPLOYED_ON")],
     "how does the black-and-white workflow regain micro-contrast after Fuji recipes",
     "nik silver efex plugin roundtrip black white film simulation grain"),
    # --- 36 ---
    ("Relief hit when Backblaze Personal finished seeding 2.4 terabytes of the Leica archive on 2026-03-02 because the B1 plan still covered the external LaCie Rugged without charging the inheritance-pricing tier.", "milestone", "cross", False,
     [("Relief", "emotion"), ("Backblaze Personal", "service"), ("Leica", "organization"), ("2026-03-02", "date"), ("LaCie Rugged", "infrastructure")],
     [("Backblaze Personal", "LaCie Rugged", "USES")],
     "when did the Leica archive finish the initial Backblaze seed",
     "cloud backup seed duration external drive coverage plan tier"),
    # --- 37 ---
    ("Prefers the Think Tank Airport Advantage roller over the Peak Design Travel Backpack 45 for the long-haul flight because the overhead-bin compliance for the Nikon D850 and the 70-200 stayed consistent across ANA, KLM, and Delta.", "preference", "cross", False,
     [("Think Tank Airport Advantage", "infrastructure"), ("Peak Design Travel Backpack 45", "infrastructure"), ("Nikon D850", "infrastructure"), ("ANA", "organization"), ("KLM", "organization"), ("Delta", "organization")],
     [("Think Tank Airport Advantage", "Peak Design Travel Backpack 45", "PREFERS")],
     "which bag wins for multi-carrier long-haul camera travel and why",
     "camera roller bag overhead bin carrier compliance long haul swap"),
    # --- 38 ---
    ("The PhotoRec recovery tool pulled 340 Sony A7 IV ARW files from the corrupted CFexpress card on 2026-02-27 after the in-camera format attempt failed mid-write during the Bogotá session.", "fact", "cross", False,
     [("PhotoRec", "tool"), ("Sony A7 IV", "infrastructure"), ("ARW", "concept"), ("CFexpress", "infrastructure"), ("2026-02-27", "date"), ("Bogotá", "place")],
     [("PhotoRec", "CFexpress", "USES")],
     "which tool rescued the corrupted card shoot in Bogota",
     "card corruption recovery raw file rescue format failure field session"),
    # --- 39 ---
    ("The SmallRig cage replaced the Tilta Basic for the Canon EOS R5 video rig because the SmallRig cold-shoe layout puts the Rode Wireless Pro where the Atomos Ninja V HDMI cable doesn't fight the swivel screen.", "decision", "cross", False,
     [("SmallRig", "organization"), ("Tilta", "organization"), ("Canon EOS R5", "infrastructure"), ("Rode Wireless Pro", "infrastructure"), ("Atomos Ninja V", "infrastructure"), ("HDMI", "protocol")],
     [("SmallRig", "Tilta", "REPLACES")],
     "why did the Canon video cage get swapped out",
     "camera cage swap cold shoe layout cable management swivel screen"),
    # --- 40 ---
    ("The DxO PureRAW 4 pre-processing step improves on Topaz Photo AI for the Nikon Z8 astro shots because PureRAW's optical module for the 14-24 S corrects the corner smear Topaz's generic model can't.", "decision", "cross", False,
     [("DxO PureRAW 4", "tool"), ("Topaz Photo AI", "tool"), ("Nikon Z8", "infrastructure")],
     [("DxO PureRAW 4", "Topaz Photo AI", "IMPROVES_ON")],
     "which pre-processor wins for Nikon astro and what optical correction drives it",
     "denoise pre process optical module corner correction astro landscape"),
    # --- 41 ---
    ("The 2026-04-02 backup drill restored 48 hours of Fujifilm X-T5 RAF files from the Synology snapshot within 20 minutes because the Btrfs snapshot schedule was set to hourly on the photo share.", "milestone", "cross", False,
     [("2026-04-02", "date"), ("Fujifilm X-T5", "infrastructure"), ("RAF", "concept"), ("Synology", "infrastructure"), ("Btrfs", "concept")],
     [("Btrfs", "Synology", "DEPLOYED_ON")],
     "how did the April backup drill prove the photo share recovery target",
     "snapshot restore drill hourly schedule raw retention nas recovery"),
    # --- 42 ---
    ("Prefers Lightroom Classic's Enhanced Raw Details over Topaz Gigapixel for the Leica M9 16-megapixel files because the Bayer-aware demosaic keeps the Kodak CCD color that Gigapixel smooths into mud.", "preference", "cross", False,
     [("Lightroom Classic", "tool"), ("Topaz Gigapixel", "tool"), ("Leica M9", "infrastructure"), ("Kodak", "organization")],
     [("Lightroom Classic", "Topaz Gigapixel", "PREFERS")],
     "which upscaler wins for the old M9 CCD files and why",
     "enhanced raw details bayer demosaic ccd color legacy camera upscale"),
    # --- 43 ---
    ("The Plustek OpticFilm 8200i replaced the Epson V600 for the 35mm Kodachrome slide archive because the Plustek's 7200 DPI native scan held the Kodachrome red the flatbed blew through.", "decision", "cross", False,
     [("Plustek OpticFilm 8200i", "infrastructure"), ("Epson V600", "infrastructure"), ("Kodachrome", "concept")],
     [("Plustek OpticFilm 8200i", "Epson V600", "REPLACES")],
     "which scanner took over for the Kodachrome slides and why",
     "dedicated film scanner slide archive color fidelity dpi flatbed swap"),
    # --- 44 ---
    ("Curiosity led to a test run of the Ricoh GR IIIx as the daily-carry replacement for the Leica Q3 on 2026-03-18 because the snap-focus workflow beat the Q3 autofocus for the street-corner candid I kept missing.", "fact", "cross", False,
     [("Curiosity", "emotion"), ("Ricoh GR IIIx", "infrastructure"), ("Leica Q3", "infrastructure"), ("2026-03-18", "date")],
     [("Ricoh GR IIIx", "Leica Q3", "PREFERS")],
     "what compact did I try as a Q3 alternative and why did the test stick",
     "snap focus pocket camera compact street candid test daily carry"),
    # --- 45 ---
    ("The 2026-04-11 Saal Digital calibration target ships with a reference print the Eizo CS2410 accepts, and the DisplayCAL profile finally matches the matte Hahnemühle soft-proof for the Dolomites panorama.", "architecture", "cross", False,
     [("2026-04-11", "date"), ("Saal Digital", "organization"), ("Eizo CS2410", "infrastructure"), ("DisplayCAL", "tool"), ("Hahnemühle", "organization"), ("Dolomites", "place")],
     [("DisplayCAL", "Eizo CS2410", "USES")],
     "how did the monitor profile finally line up with the Saal print proof",
     "monitor calibration soft proof paper profile icc print match"),
    # --- 46 ---
    ("Excitement took over on 2026-03-30 when the Fujifilm GFX 100S replaced the Hasselblad X2D rental slot for the studio still-life week because the GFX's tethered Capture One link survived the 12-hour session without a reconnect.", "milestone", "cross", False,
     [("Excitement", "emotion"), ("2026-03-30", "date"), ("Fujifilm GFX 100S", "infrastructure"), ("Hasselblad X2D", "infrastructure"), ("Capture One", "tool")],
     [("Fujifilm GFX 100S", "Hasselblad X2D", "REPLACES")],
     "which medium format body replaced the Hasselblad rental for the studio week",
     "medium format rental choice long session tether stability studio still life"),
    # --- 47 ---
    ("The Pixel 9 Pro's Magic Eraser improves on Photoshop's Generative Remove for the quick phone-share edit because the on-device model finishes before the iPhone's round-trip to Adobe's cloud even uploads.", "preference", "cross", False,
     [("Pixel 9 Pro", "infrastructure"), ("Magic Eraser", "tool"), ("Photoshop", "tool"), ("iPhone", "infrastructure"), ("Adobe", "organization")],
     [("Magic Eraser", "Photoshop", "IMPROVES_ON")],
     "which quick-edit cleanup wins for phone-share speed and why",
     "on device generative edit cloud round trip latency phone share"),
    # --- 48 ---
    ("The 2026-02-18 Canon EOS R5 Mark II pre-order at B&H replaced the standing Sony A1 II pre-order on Adorama because the Canon's stacked sensor readout beat the Sony's rolling-shutter test for the bird-in-flight hobby shots.", "decision", "cross", False,
     [("2026-02-18", "date"), ("Canon EOS R5 Mark II", "infrastructure"), ("B&H", "organization"), ("Sony A1 II", "infrastructure"), ("Adorama", "organization")],
     [("Canon EOS R5 Mark II", "Sony A1 II", "REPLACES")],
     "why did the flagship pre-order swap between the two retailers",
     "flagship mirrorless preorder sensor readout rolling shutter bird test"),
    # --- 49 ---
    ("The Phoblographer review on 2026-03-24 of the Voigtländer 50 APO-Lanthar confirmed the Leica M11 corner sharpness held at f/2, and the hobby purchase went through on the Popflash listing that week.", "reference", "cross", False,
     [("Phoblographer", "publication"), ("2026-03-24", "date"), ("Voigtländer 50 APO-Lanthar", "infrastructure"), ("Leica M11", "infrastructure"), ("Popflash", "organization")],
     [("Voigtländer 50 APO-Lanthar", "Leica M11", "USES")],
     "which review pushed the APO-Lanthar purchase and where did it come from",
     "lens review corner sharpness rangefinder hobby purchase retailer"),
    # --- 50 ---
    ("Joy surged on 2026-04-05 when the Pixieset gallery for the Santorini elopement crossed 600 favorite taps, and the Printique auto-order pulled the winning shot into a 30-inch Fujiflex print the same night.", "milestone", "cross", False,
     [("Joy", "emotion"), ("2026-04-05", "date"), ("Pixieset", "service"), ("Santorini", "place"), ("Printique", "organization"), ("Fujiflex", "concept")],
     [("Printique", "Pixieset", "COMMUNICATES_WITH")],
     "when did the Santorini elopement gallery favorite count trigger the print order",
     "client gallery favorites threshold print auto order large format"),
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
