"""One-off emitter for shared-base batch-215 — personal domain (photography: digital bodies, lenses, film stocks, formats, developing, darkroom, editing, composition, photographers).

Writes 50 rows to data/v2/shared/batch_215.tmp.jsonl with ids shared-10701..10750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_215.tmp.jsonl"
ID_OFFSET = 10700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
# Mix: decision 12, architecture 9, milestone 7, fact 7, reference 6, preference 4, problem 3, noise 2
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Retired the Canon R5 as the primary body and moved to the Sony A7R V for landscape work; the pixel-shift multi-shot mode finally solved the foliage moire that plagued the R5 files on spruce ridges.", "decision", "personal", False,
     [("Canon R5", "tool"), ("Sony A7R V", "tool")],
     [("Sony A7R V", "Canon R5", "REPLACES")],
     "which mirrorless body took over the landscape role and what sensor mode pushed the decision",
     "sony a7r v canon r5 landscape pixel shift moire replace body"),
    # --- 2. architecture ---
    ("The home darkroom pipeline runs three wet trays under the 50H dichroic enlarger: Dektol for paper development, a stop bath of dilute acetic acid, and Kodak Rapid Fixer, with a print washer at the sink.", "architecture", "personal", False,
     [("50H dichroic enlarger", "tool"), ("Dektol", "tool"), ("Kodak Rapid Fixer", "tool"), ("print washer", "tool")],
     [("50H dichroic enlarger", "Dektol", "HAS_PART"), ("50H dichroic enlarger", "Kodak Rapid Fixer", "HAS_PART")],
     "how is the wet-print darkroom laid out under the dichroic head and which chemistry sits in each tray",
     "darkroom enlarger dektol stop fixer print washer tray wet"),
    # --- 3. decision ---
    ("Chose Kodak Portra 400 over Portra 800 as the daily 35mm stock for street work; the finer grain at box speed matters more to me than the extra stop once I carry a Leica Q3 for low light.", "decision", "personal", False,
     [("Kodak Portra 400", "tool"), ("Portra 800", "tool"), ("Leica Q3", "tool")],
     [("Kodak Portra 400", "Portra 800", "PREFERS")],
     "which 35mm colour stock became the daily street emulsion and what digital body covers the low-light gap",
     "portra 400 800 street 35mm leica q3 stock daily low light"),
    # --- 4. reference ---
    ("Saul Leiter's Early Color is the reference I return to when grading winter street frames; the muted palette and through-the-window framing keep telling me to stop cranking clarity in Lightroom Classic.", "reference", "personal", False,
     [("Saul Leiter", "person"), ("Early Color", "publication"), ("Lightroom Classic", "tool")],
     [("Early Color", "Saul Leiter", "AUTHORED_BY")],
     "which photographer and book anchor my winter street grading and what editor restraint does it impose",
     "saul leiter early color winter street grade lightroom classic"),
    # --- 5. milestone ---
    ("Finally nailed a split-grade darkroom print of the Glen Coe negative: a grade 0 base exposure for the sky then a grade 5 burn on the foreground rocks, one of the best fiber prints I have made.", "milestone", "personal", False,
     [("split-grade", "method"), ("Glen Coe", "place"), ("fiber", "tool")],
     [],
     "what darkroom technique finally produced the keeper print from the Scottish highland negative",
     "split grade darkroom print glen coe fiber negative sky burn"),
    # --- 6. fact ---
    ("Developed the latest roll of Tri-X 400 in HC-110 dilution B for five minutes at 20 degrees; the rebate numbers came through cleanly so the tank agitation pattern is working.", "fact", "personal", False,
     [("Tri-X 400", "tool"), ("HC-110", "tool")],
     [("Tri-X 400", "HC-110", "USES")],
     "which developer and dilution did this roll of Tri-X go through and what did the rebate check confirm",
     "tri x 400 hc 110 dilution b five minute 20 develop rebate"),
    # --- 7. architecture ---
    ("My editing stack is Capture One for tethered Phase One captures, Lightroom Classic for the Sony library, and DxO PhotoLab only when DeepPRIME is needed to rescue high-ISO Fujifilm X-T5 frames.", "architecture", "personal", False,
     [("Capture One", "tool"), ("Phase One", "tool"), ("Lightroom Classic", "tool"), ("DxO PhotoLab", "tool"), ("Fujifilm X-T5", "tool")],
     [("Capture One", "Phase One", "APPLIES_TO"), ("DxO PhotoLab", "Fujifilm X-T5", "APPLIES_TO")],
     "how is the raw editor workflow split across three applications and which body owns each lane",
     "capture one phase lightroom dxo photolab x-t5 tether raw stack"),
    # --- 8. preference ---
    ("Prefer Voigtländer Nokton 40mm f/1.2 over the Sony GM 35mm for late-night walks; the rendering is dreamier and the barrel focus ring feels right in gloves at below freezing.", "preference", "personal", False,
     [("Voigtländer Nokton 40mm f/1.2", "tool"), ("Sony GM 35mm", "tool")],
     [("Voigtländer Nokton 40mm f/1.2", "Sony GM 35mm", "PREFERS")],
     "which fast prime wins the cold night-walk slot and why does it beat the Sony equivalent",
     "voigtlander nokton 40 1.2 sony gm 35 night walk manual glove"),
    # --- 9. decision ---
    ("Moved the wildlife kit from the Nikon Z9 to the Canon R5 after a two-week side-by-side on red deer; the R5 animal-eye AF locked faster on antler clutter and the files grade cleaner for my palette.", "decision", "personal", False,
     [("Nikon Z9", "tool"), ("Canon R5", "tool"), ("red deer", "activity")],
     [("Canon R5", "Nikon Z9", "REPLACES")],
     "which flagship replaced the Nikon for wildlife and which AF behaviour tipped the call",
     "nikon z9 canon r5 wildlife red deer animal eye af antler"),
    # --- 10. noise ---
    ("The cat knocked over the film-drying line again and a Portra strip now bears three perfect paw prints down the middle.", "fact", "noise", True, [], [], None, None),
    # --- 11. architecture ---
    ("The 4x5 field kit is built around a Chamonix 45F-2, a 150mm Fujinon W, a 90mm Nikkor SW, and ten holders of FP4 and HP5; everything rides in one modified hiking pack with a dark cloth sleeve.", "architecture", "personal", False,
     [("Chamonix 45F-2", "tool"), ("150mm Fujinon W", "tool"), ("90mm Nikkor SW", "tool"), ("FP4", "tool"), ("HP5", "tool")],
     [("Chamonix 45F-2", "150mm Fujinon W", "HAS_PART"), ("Chamonix 45F-2", "90mm Nikkor SW", "HAS_PART")],
     "what goes in the large-format field pack and which two focal lengths cover the body",
     "4x5 chamonix 45f fujinon 150 nikkor 90 sw fp4 hp5 field pack"),
    # --- 12. problem ---
    ("Ran into light piping on the first roll of Cinestill 800T shot through the Leica SL3; the remjet-free base leaks red into the sprocket area on bright frames and I have to clone it out in post.", "problem", "personal", False,
     [("Cinestill 800T", "tool"), ("Leica SL3", "tool")],
     [],
     "which film and body combination produced the red sprocket leak and what does the fix require",
     "cinestill 800t leica sl3 light pipe remjet sprocket red leak"),
    # --- 13. fact ---
    ("Pro 400H is formally discontinued; Fujifilm confirmed the end-of-production notice and the last fresh bricks I found in Tokyo went for roughly twice the old price on Nakano camera-street shelves.", "fact", "personal", False,
     [("Pro 400H", "tool"), ("Fujifilm", "organization"), ("Tokyo", "place"), ("Nakano", "place")],
     [("Pro 400H", "Fujifilm", "PRODUCES"), ("Nakano", "Tokyo", "LOCATED_IN")],
     "what happened to the Fuji portrait colour stock and where did the last fresh stock show up",
     "pro 400h fuji discontinued tokyo nakano camera street price"),
    # --- 14. decision ---
    ("Picked the Hasselblad X2D over the Leica SL3 for the studio portrait upgrade; 100 megapixel medium-format files give me crop room for magazine layouts that the 60 megapixel 35mm simply cannot.", "decision", "personal", False,
     [("Hasselblad X2D", "tool"), ("Leica SL3", "tool")],
     [("Hasselblad X2D", "Leica SL3", "PREFERS")],
     "which body took the studio portrait slot over the Leica and what workflow need drove the choice",
     "hasselblad x2d leica sl3 studio portrait 100 megapixel crop magazine"),
    # --- 15. reference ---
    ("Re-read Ansel Adams The Negative this week for the zone system refresher; the contraction and expansion development tables still map cleanly onto what I do with HC-110 and T-Max 400.", "reference", "personal", False,
     [("Ansel Adams", "person"), ("The Negative", "publication"), ("HC-110", "tool"), ("T-Max 400", "tool")],
     [("The Negative", "Ansel Adams", "AUTHORED_BY")],
     "which zone-system text drives my development planning and which developer and film pair do I map it to",
     "ansel adams negative zone system contract expand hc 110 tmax"),
    # --- 16. decision ---
    ("Replaced the Sigma 35mm Art on the A7R V with a Zeiss Otus 55mm for product work; the Otus corner-to-corner sharpness at f/4 simply has no peer and the manual-focus workflow fits tethered shooting.", "decision", "personal", False,
     [("Sigma 35mm Art", "tool"), ("Zeiss Otus 55mm", "tool"), ("A7R V", "tool")],
     [("Zeiss Otus 55mm", "Sigma 35mm Art", "REPLACES")],
     "which manual-focus optic took the product-shoot slot on the Sony body and why",
     "zeiss otus 55 sigma 35 art a7r product tether manual corner"),
    # --- 17. milestone ---
    ("Processed my first roll of C-41 at home in a Cinestill Cs41 kit; three rolls of Portra 400 came out dead-on the reference strip, a year of putting off the chemistry was not worth it.", "milestone", "personal", False,
     [("C-41", "method"), ("Cinestill Cs41", "tool"), ("Portra 400", "tool")],
     [("Cinestill Cs41", "C-41", "IMPLEMENTS")],
     "which home colour process did I finally run and which film calibrated against the reference strip",
     "c-41 cinestill cs41 home colour portra 400 first roll reference"),
    # --- 18. preference ---
    ("Prefer fiber-based paper over RC for portfolio prints; the deeper Dmax and the physical weight of a fiber print in the hand is not a thing I can explain to clients but they feel it immediately.", "preference", "personal", False,
     [("fiber-based paper", "tool"), ("RC", "tool")],
     [("fiber-based paper", "RC", "PREFERS")],
     "which darkroom paper stock wins for portfolio work and what tactile quality separates it from resin coated",
     "fiber based rc paper portfolio dmax print weight darkroom"),
    # --- 19. architecture ---
    ("The Leica M6 travel kit is three lenses: a 35mm Summicron for wide street, a 50mm Summilux for indoors and low light, and a 90mm Elmarit for the occasional tight portrait across a cafe table.", "architecture", "personal", False,
     [("Leica M6", "tool"), ("35mm Summicron", "tool"), ("50mm Summilux", "tool"), ("90mm Elmarit", "tool")],
     [("Leica M6", "35mm Summicron", "HAS_PART"), ("Leica M6", "50mm Summilux", "HAS_PART"), ("Leica M6", "90mm Elmarit", "HAS_PART")],
     "how is the rangefinder travel kit partitioned across three focal lengths",
     "leica m6 summicron 35 summilux 50 elmarit 90 travel kit"),
    # --- 20. decision ---
    ("Switched the black-and-white developer from D-76 to Rodinal for Tri-X street work; the grain is sharper and the highlights hold better, even if shadow detail pays a small tax.", "decision", "personal", False,
     [("D-76", "tool"), ("Rodinal", "tool"), ("Tri-X", "tool")],
     [("Rodinal", "D-76", "REPLACES")],
     "which black-and-white developer replaced D-76 for Tri-X street work and what did it cost in shadows",
     "rodinal d 76 tri x black white street developer grain shadow"),
    # --- 21. fact ---
    ("The Pentax K-3 III Monochrome is the only current dedicated B&W digital body outside of the Leica M Monochrom line; I rented one for a week and the base-ISO files have a real silver feel.", "fact", "personal", False,
     [("Pentax K-3 III", "tool"), ("Leica M Monochrom", "tool")],
     [],
     "which two camera lines currently sell dedicated monochrome digital bodies",
     "pentax k3 iii monochrome leica m monochrom b&w silver rental"),
    # --- 22. reference ---
    ("Sebastião Salgado Genesis is the coffee-table book that keeps nudging me to push wildlife compositions toward wider environmental frames instead of tight telephoto portraits of the subject.", "reference", "personal", False,
     [("Sebastião Salgado", "person"), ("Genesis", "publication")],
     [("Genesis", "Sebastião Salgado", "AUTHORED_BY")],
     "which photographer and book keeps pushing my wildlife framing toward wider environmental compositions",
     "salgado genesis wildlife environmental wide frame coffee table"),
    # --- 23. architecture ---
    ("The Fujifilm X-T5 street kit pairs the body with the XF 23mm f/1.4 R LM WR and the XF 56mm f/1.2 R WR; the APS-C crop gives me roughly 35mm and 85mm equivalents without carrying a full-frame rig.", "architecture", "personal", False,
     [("Fujifilm X-T5", "tool"), ("XF 23mm f/1.4 R LM WR", "tool"), ("XF 56mm f/1.2 R WR", "tool")],
     [("Fujifilm X-T5", "XF 23mm f/1.4 R LM WR", "HAS_PART"), ("Fujifilm X-T5", "XF 56mm f/1.2 R WR", "HAS_PART")],
     "how is the APS-C street kit paired with two primes and what equivalents does the crop deliver",
     "fuji x-t5 xf 23 1.4 56 1.2 street aps-c 35 85 equivalent"),
    # --- 24. milestone ---
    ("First 8x10 contact print on Ilford Multigrade Warmtone fiber came out of the tray yesterday; the tonal transitions on a backlit oak leaf are nothing like any scan I have ever printed.", "milestone", "personal", False,
     [("8x10", "method"), ("Ilford Multigrade Warmtone", "tool")],
     [],
     "which large-format contact print finally came out of the tray and on what paper",
     "8x10 contact print ilford multigrade warmtone fiber oak leaf"),
    # --- 25. decision ---
    ("Going to shoot this Iceland trip on 120 format instead of 35mm; a Pentax 67 with two backs of Ektar 100 and one back of Portra 800 gives me the detail I want in the basalt columns.", "decision", "personal", False,
     [("Iceland", "place"), ("Pentax 67", "tool"), ("Ektar 100", "tool"), ("Portra 800", "tool")],
     [("Pentax 67", "Ektar 100", "USES"), ("Pentax 67", "Portra 800", "USES")],
     "which film format and camera pairing did I pick for the Iceland trip and which stocks go in the holders",
     "iceland pentax 67 120 format ektar 100 portra 800 basalt"),
    # --- 26. problem ---
    ("The Nikon Z9 lost focus tracking on backlit gannets over Bass Rock; the 3D tracking kept locking onto wave crests once the sun hit the sensor directly, a single stop of exposure comp cured it.", "problem", "personal", False,
     [("Nikon Z9", "tool"), ("Bass Rock", "place")],
     [],
     "which backlit-subject failure did the Z9 autofocus show and what exposure tweak cured it",
     "nikon z9 bass rock gannet backlit 3d tracking wave exposure"),
    # --- 27. reference ---
    ("Daido Moriyama Provoke era contact sheets are the antidote I keep going back to when my frames get too clean; the are-bure-boke look reminds me that composition sometimes means abandoning rule of thirds.", "reference", "personal", False,
     [("Daido Moriyama", "person"), ("Provoke", "publication"), ("rule of thirds", "concept")],
     [],
     "which Japanese photographer and era do I go back to for messy composition reset",
     "moriyama provoke are bure boke composition rule thirds contact"),
    # --- 28. architecture ---
    ("The scan-and-archive chain for medium-format negs is a Plustek OpticFilm 120 on Silverfast, DNG conversion through Negative Lab Pro in Lightroom Classic, and parity backup to two Synology drives.", "architecture", "personal", False,
     [("Plustek OpticFilm 120", "tool"), ("Silverfast", "tool"), ("Negative Lab Pro", "tool"), ("Lightroom Classic", "tool"), ("Synology", "tool")],
     [("Plustek OpticFilm 120", "Silverfast", "USES"), ("Negative Lab Pro", "Lightroom Classic", "DEPENDS_ON")],
     "how does a 120-format negative travel from scanner to backed-up catalog and which three tools move it",
     "plustek opticfilm 120 silverfast negative lab pro lightroom synology"),
    # --- 29. decision ---
    ("Switched my Leica Q3 JPEG profile to the Monochrom HC preset for street shooting; the preview actually matches the final print look now so I stop second-guessing frames in the field.", "decision", "personal", False,
     [("Leica Q3", "tool"), ("Monochrom HC", "config")],
     [("Leica Q3", "Monochrom HC", "CONFIGURES")],
     "which in-camera profile did I move the Q3 to for street and what field benefit fell out",
     "leica q3 monochrom hc preset street jpeg preview print"),
    # --- 30. milestone ---
    ("Sold a Vivian Maier-style square street print at the local gallery opening; the Rolleiflex 3.5F file came off an HP5 neg I developed last winter in Caffenol, first time a home-stand chemistry print cleared.", "milestone", "personal", False,
     [("Vivian Maier", "person"), ("Rolleiflex 3.5F", "tool"), ("HP5", "tool"), ("Caffenol", "tool")],
     [("HP5", "Caffenol", "USES")],
     "which square-format print sold at the gallery and which home chemistry produced the negative",
     "vivian maier rolleiflex 3.5f hp5 caffenol square street gallery"),
    # --- 31. preference ---
    ("Prefer Darktable to RawTherapee for occasional Linux-laptop edits on trips; the lighttable workflow feels closer to Lightroom muscle memory and the tone equalizer module actually produces results I keep.", "preference", "personal", False,
     [("Darktable", "tool"), ("RawTherapee", "tool"), ("Lightroom", "tool")],
     [("Darktable", "RawTherapee", "PREFERS")],
     "which open-source raw editor wins my Linux laptop slot and what makes the switch worth it",
     "darktable rawtherapee linux laptop trip tone equalizer lightroom"),
    # --- 32. fact ---
    ("Composition checklist for landscape frames is four items on a sticky on the lens cap: leading lines first, then foreground interest, then the rule of thirds grid, then a final sweep for empty corners.", "fact", "personal", False,
     [("leading lines", "concept"), ("foreground interest", "concept"), ("rule of thirds", "concept")],
     [],
     "which four-step composition checklist sits on my lens cap for landscape frames",
     "composition leading lines foreground interest rule thirds corner checklist"),
    # --- 33. decision ---
    ("Committed to the Nikon S-line 24-70mm f/2.8 S for the Z9 over the f/4 variant; the extra stop buys me more than the half-kilo of weight costs me, especially for indoor event work under mixed lighting.", "decision", "personal", False,
     [("Nikon S-line", "tool"), ("24-70mm f/2.8 S", "tool"), ("Z9", "tool")],
     [("24-70mm f/2.8 S", "Z9", "APPLIES_TO")],
     "which Nikon zoom did I choose for the Z9 mid-range slot and what use case drove the aperture call",
     "nikon s line 24 70 2.8 z9 zoom event indoor stop weight"),
    # --- 34. fact ---
    ("T-Max 400 reciprocity kicks in noticeably past one second; Kodak's datasheet says add one stop at 10 seconds and two stops at a minute, which lines up with what my meter is telling me at dusk.", "fact", "personal", False,
     [("T-Max 400", "tool"), ("Kodak", "organization")],
     [("T-Max 400", "Kodak", "PRODUCES")],
     "where does reciprocity failure kick in on T-Max 400 and what does the manufacturer datasheet suggest",
     "tmax 400 reciprocity failure one second ten minute kodak datasheet"),
    # --- 35. preference ---
    ("Prefer Cinestill 50D over Ektar 100 for sunlit travel; the skin tones under harsh Mediterranean light are softer on the Cinestill and the grain structure feels more like motion-picture stock in the scan.", "preference", "personal", False,
     [("Cinestill 50D", "tool"), ("Ektar 100", "tool")],
     [("Cinestill 50D", "Ektar 100", "PREFERS")],
     "which daylight colour stock wins sunlit travel and what tonal quality separates it from the Kodak alternative",
     "cinestill 50d ektar 100 sunlit travel skin tone grain mediterranean"),
    # --- 36. architecture ---
    ("The Canon RF studio zoom set is three lenses: the RF 15-35mm f/2.8L for environmental, the RF 24-70mm f/2.8L for general, and the RF 70-200mm f/2.8L for tight portraits at a distance that keeps the sitter relaxed.", "architecture", "personal", False,
     [("Canon RF", "tool"), ("RF 15-35mm f/2.8L", "tool"), ("RF 24-70mm f/2.8L", "tool"), ("RF 70-200mm f/2.8L", "tool")],
     [("Canon RF", "RF 15-35mm f/2.8L", "HAS_PART"), ("Canon RF", "RF 24-70mm f/2.8L", "HAS_PART"), ("Canon RF", "RF 70-200mm f/2.8L", "HAS_PART")],
     "how does my Canon RF studio set cover environmental through tight portrait ranges",
     "canon rf 15-35 24-70 70-200 2.8 studio zoom environmental portrait"),
    # --- 37. decision ---
    ("Stopped bulk-loading HP5 and now buy pre-rolled 35mm canisters; the saved minutes per roll compound on a shoot week and a single dusty loader scratch ruined one keeper frame last October.", "decision", "personal", False,
     [("HP5", "tool")],
     [],
     "why did I stop bulk-loading HP5 into 35mm canisters and what specific failure pushed the call",
     "hp5 bulk load 35mm canister pre roll dust scratch keeper"),
    # --- 38. milestone ---
    ("Hit 100 developed rolls for the year last night; counting the box of negs on the shelf against the logbook there are 42 Tri-X, 28 HP5, 20 Portra 400, 6 Ektar, and 4 oddball Delta 3200 rolls.", "milestone", "personal", False,
     [("Tri-X", "tool"), ("HP5", "tool"), ("Portra 400", "tool"), ("Ektar", "tool"), ("Delta 3200", "tool")],
     [],
     "how did the year's 100 developed rolls break down by film stock on the logbook",
     "100 roll year tri x hp5 portra 400 ektar delta 3200 logbook"),
    # --- 39. reference ---
    ("Keep a worn copy of Ansel Adams The Print on the darkroom shelf; the chapters on local-area dodging and edge burning are the ones I still re-read before every major fiber session.", "reference", "personal", False,
     [("Ansel Adams", "person"), ("The Print", "publication")],
     [("The Print", "Ansel Adams", "AUTHORED_BY")],
     "which darkroom manual do I still re-read before big fiber sessions and which chapters matter most",
     "ansel adams print dodge burn local fiber darkroom reference"),
    # --- 40. architecture ---
    ("The Leica SL3 multi-format kit pairs the body with an SL 35mm Summicron, an M-to-L adapter for the Summilux 50mm, and a TL 60mm macro that lets me cover environmental, portrait, and detail on one camera.", "architecture", "personal", False,
     [("Leica SL3", "tool"), ("SL 35mm Summicron", "tool"), ("M-to-L adapter", "tool"), ("Summilux 50mm", "tool"), ("TL 60mm macro", "tool")],
     [("Leica SL3", "SL 35mm Summicron", "HAS_PART"), ("Leica SL3", "TL 60mm macro", "HAS_PART"), ("M-to-L adapter", "Summilux 50mm", "APPLIES_TO")],
     "how does the Leica SL3 kit cover environmental, portrait, and detail work across three mounts",
     "leica sl3 summicron summilux macro m-to-l adapter multi format"),
    # --- 41. decision ---
    ("Going to shoot 6x6 square instead of 6x7 for the family project; the square frame forces a different kind of portrait composition and the Rolleiflex is quieter than the Pentax 67 around young kids.", "decision", "personal", False,
     [("6x6", "method"), ("6x7", "method"), ("Rolleiflex", "tool"), ("Pentax 67", "method")],
     [("6x6", "6x7", "PREFERS")],
     "which medium-format aspect did I pick for the family project and which body made the call easier",
     "6x6 6x7 square family rolleiflex pentax 67 quiet portrait kid"),
    # --- 42. fact ---
    ("Caffenol-C recipe on the darkroom wall is 60g washing soda, 16g vitamin C, 40g instant coffee in one litre of water; stand-develop HP5 at box speed for an hour with an agitation at 30 minutes.", "fact", "personal", False,
     [("Caffenol-C", "method"), ("HP5", "tool")],
     [("Caffenol-C", "HP5", "APPLIES_TO")],
     "what is my wall-sticker Caffenol-C recipe and how do I stand-develop HP5 with it",
     "caffenol c washing soda vitamin coffee hp5 stand develop hour"),
    # --- 43. noise ---
    ("A squirrel has decided the tripod stored by the shed door is the correct angle for burying acorns and I have given up relocating the finds.", "fact", "noise", True, [], [], None, None),
    # --- 44. problem ---
    ("The Hasselblad X2D file viewer on Phocus is crashing on files above 90 frames; rebuilding the catalog fixed it once but it came back after the next import, Capture One handles the same files cleanly.", "problem", "personal", False,
     [("Hasselblad X2D", "tool"), ("Phocus", "tool"), ("Capture One", "tool")],
     [],
     "which Hasselblad software keeps crashing on big X2D catalogs and which tool handles the same files without issues",
     "hasselblad x2d phocus crash catalog rebuild capture one import"),
    # --- 45. architecture ---
    ("Print finishing station has three stages in order: a dry-mount press for heat bonding, a 4-ply archival mat board bevelled on a Logan 750, and a signed edition label glued behind the mat window.", "architecture", "personal", False,
     [("dry-mount press", "tool"), ("Logan 750", "tool"), ("archival mat board", "tool")],
     [("archival mat board", "Logan 750", "USES")],
     "how does a finished print move through the three-stage finishing station from bond through signed label",
     "dry mount press logan 750 bevel archival mat signed edition"),
    # --- 46. decision ---
    ("Committed to shooting Iceland entirely manual-focus on the Leica Q3 and a Hasselblad 501CM instead of hauling the autofocus Z9; manual work forces deliberate framing and I am stronger for it on landscape trips.", "decision", "personal", False,
     [("Iceland", "place"), ("Leica Q3", "tool"), ("Hasselblad 501CM", "tool"), ("Z9", "tool")],
     [("Hasselblad 501CM", "Z9", "PREFERS")],
     "why did I leave the autofocus Z9 at home for Iceland and which two manual bodies replaced it",
     "iceland leica q3 hasselblad 501cm manual focus z9 landscape"),
    # --- 47. reference ---
    ("Went back to Vivian Maier Street Photographer for portrait-of-strangers courage; the subway frames in particular taught me to stop hiding the camera and just hold the Rolleiflex at waist level openly.", "reference", "personal", False,
     [("Vivian Maier", "person"), ("Street Photographer", "publication"), ("Rolleiflex", "tool")],
     [("Street Photographer", "Vivian Maier", "AUTHORED_BY")],
     "which street-photography book pushes my courage with strangers and which body benefits from the lesson",
     "vivian maier street photographer rolleiflex waist level subway"),
    # --- 48. milestone ---
    ("Finished the first full slide film portfolio shot entirely on handheld incident readings off the Sekonic L-858D; the in-camera matrix mode did not touch a single frame and the transparencies all landed on the light table evenly exposed.", "milestone", "personal", False,
     [("Sekonic L-858D", "tool"), ("matrix mode", "method"), ("slide film", "tool")],
     [("Sekonic L-858D", "matrix mode", "REPLACES")],
     "which handheld meter drove the first all-incident slide portfolio and what in-camera mode did it retire",
     "sekonic l 858d incident meter slide film matrix transparency portfolio"),
    # --- 49. fact ---
    ("Phase One IQ4 150MP back files come off the card at roughly 200 megabytes each in IIQ Large format; a day of studio work easily fills 256 GB and the SSD tower is what keeps this sustainable.", "fact", "personal", False,
     [("Phase One IQ4", "tool"), ("IIQ Large", "config"), ("SSD tower", "tool")],
     [("Phase One IQ4", "IIQ Large", "PRODUCES")],
     "how big are the Phase One IQ4 raw files in practice and what storage tier keeps a studio day sustainable",
     "phase one iq4 150mp iiq large 200 megabyte ssd tower studio"),
    # --- 50. milestone ---
    ("Hung the first solo show at the neighbourhood library last Friday: twelve 16x20 fiber prints pulled from HP5 and FP4 negatives, all printed split-grade on my 50H enlarger, the opening night had a proper turnout.", "milestone", "personal", False,
     [("16x20", "method"), ("HP5", "tool"), ("FP4", "tool"), ("split-grade", "method"), ("50H enlarger", "tool")],
     [("split-grade", "50H enlarger", "USES")],
     "what did the first solo show consist of and which printing technique carried the fiber prints",
     "solo show library 16x20 fiber hp5 fp4 split grade 50h enlarger"),
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
