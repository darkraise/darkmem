"""One-off emitter for shared-base batch-267 — knowledge domain (film theory and cinema history: auteurs, directors, movements, theorists).

Writes 50 rows to data/v2/shared/batch_267.tmp.jsonl with ids shared-13301..13350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_267.tmp.jsonl"
ID_OFFSET = 13300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("The film society programmed Jean-Luc Godard's Breathless as the season opener rather than a Truffaut double bill, arguing that jump-cut grammar was the sharper introduction to the French New Wave for first-time viewers.", "decision", "knowledge", False,
     [("Jean-Luc Godard", "person"), ("Breathless", "publication"), ("French New Wave", "concept"), ("jump-cut", "method")],
     [("Breathless", "French New Wave", "APPLIES_TO"), ("Jean-Luc Godard", "Breathless", "AUTHORED_BY")],
     "which Godard film did the programmer pick as season opener over a Truffaut pairing and what technique justified it",
     "godard breathless truffaut french new wave jump cut season opener"),
    # --- 2 --- architecture
    ("André Bazin's long-take realism frames the critical scaffolding at Cahiers du Cinéma: deep focus and mise-en-scène carry ontological weight, while Soviet montage gets read as manipulation of the viewer's perception.", "architecture", "knowledge", False,
     [("André Bazin", "person"), ("Cahiers du Cinéma", "organization"), ("deep focus", "method"), ("mise-en-scène", "concept"), ("Soviet montage", "concept"), ("long-take", "method")],
     [("André Bazin", "Cahiers du Cinéma", "WORKS_AT"), ("long-take", "Soviet montage", "CONTRADICTS")],
     "how does Bazin's critical framework position long takes and deep focus against Soviet montage theory",
     "bazin cahiers long take deep focus mise en scene soviet montage"),
    # --- 3 --- milestone
    ("Citizen Kane's 1941 release reset the grammar of Hollywood narrative: Orson Welles's deep-focus compositions and non-linear flashback scaffolding became the reference point every subsequent film history chapter opens with.", "milestone", "knowledge", False,
     [("Citizen Kane", "publication"), ("1941", "date"), ("Orson Welles", "person"), ("deep-focus", "method"), ("flashback", "method")],
     [("Citizen Kane", "Orson Welles", "AUTHORED_BY"), ("Citizen Kane", "1941", "HAPPENED_ON")],
     "which 1941 Welles film became the textbook reference for deep-focus composition and non-linear flashback structure",
     "citizen kane welles 1941 deep focus flashback hollywood narrative"),
    # --- 4 --- decision
    ("The syllabus dropped the canonical Hitchcock unit in favour of a Chantal Akerman spotlight, arguing that Jeanne Dielman's durational aesthetic was under-taught next to yet another Psycho close-read.", "decision", "knowledge", False,
     [("Hitchcock", "person"), ("Chantal Akerman", "person"), ("Jeanne Dielman", "publication"), ("Psycho", "publication"), ("durational", "concept")],
     [("Chantal Akerman", "Hitchcock", "REPLACES"), ("Jeanne Dielman", "Chantal Akerman", "AUTHORED_BY")],
     "which director unit did the syllabus swap out for an Akerman spotlight and what aesthetic drove the change",
     "akerman jeanne dielman hitchcock psycho durational syllabus swap"),
    # --- 5 --- reference
    ("Laura Mulvey's Visual Pleasure and Narrative Cinema first appeared in Screen in 1975, and the essay's male-gaze argument still anchors most feminist film theory reading lists.", "reference", "knowledge", False,
     [("Laura Mulvey", "person"), ("Visual Pleasure and Narrative Cinema", "publication"), ("Screen", "organization"), ("1975", "date"), ("male-gaze", "theory"), ("feminist film theory", "field")],
     [("Visual Pleasure and Narrative Cinema", "Laura Mulvey", "AUTHORED_BY"), ("Visual Pleasure and Narrative Cinema", "Screen", "PUBLISHED_IN")],
     "where did Mulvey first publish the male-gaze essay and which sub-field still leans on it",
     "mulvey visual pleasure narrative cinema screen 1975 male gaze feminist"),
    # --- 6 --- architecture
    ("Sergei Eisenstein's theory of dialectical montage treats the cut as thesis and antithesis colliding into a synthesis inside the viewer's head, which is why Battleship Potemkin's Odessa Steps is the textbook exhibit.", "architecture", "knowledge", False,
     [("Sergei Eisenstein", "person"), ("dialectical montage", "theory"), ("Battleship Potemkin", "publication"), ("Odessa Steps", "concept")],
     [("dialectical montage", "Sergei Eisenstein", "AUTHORED_BY"), ("Battleship Potemkin", "Sergei Eisenstein", "AUTHORED_BY")],
     "how does Eisenstein frame a film cut theoretically and which sequence serves as the standard classroom exhibit",
     "eisenstein dialectical montage battleship potemkin odessa steps synthesis"),
    # --- 7 --- fact
    ("Yasujirō Ozu held the camera at tatami height across most of his late work, a formal constraint that flattened depth cues and turned the domestic interior into the de facto protagonist of Tokyo Story.", "fact", "knowledge", False,
     [("Yasujirō Ozu", "person"), ("tatami", "concept"), ("Tokyo Story", "publication")],
     [("Tokyo Story", "Yasujirō Ozu", "AUTHORED_BY")],
     "what camera-height constraint shaped Ozu's late style and which film is its most cited example",
     "ozu tatami camera height tokyo story domestic interior formal constraint"),
    # --- 8 --- decision
    ("Dogme 95 committed to hand-held cameras, location sound, and no non-diegetic score; Lars von Trier and the signatories positioned it as a rejection of the effects-heavy Hollywood of the mid-nineties.", "decision", "knowledge", False,
     [("Dogme 95", "concept"), ("hand-held", "method"), ("location sound", "method"), ("non-diegetic score", "concept"), ("Lars von Trier", "person")],
     [("Dogme 95", "Lars von Trier", "AUTHORED_BY"), ("hand-held", "non-diegetic score", "REPLACES")],
     "which manifesto banned non-diegetic score and who spearheaded it as a reaction to mid-nineties Hollywood",
     "dogme 95 lars von trier hand held location sound diegetic hollywood"),
    # --- 9 --- architecture
    ("Christian Metz built his grande syntagmatique as an eight-category typology for narrative film, treating the sequence — not the shot — as the base unit of cinematic meaning.", "architecture", "knowledge", False,
     [("Christian Metz", "person"), ("grande syntagmatique", "theory"), ("sequence", "concept"), ("shot", "concept")],
     [("grande syntagmatique", "Christian Metz", "AUTHORED_BY")],
     "which Metz framework treats the sequence rather than the shot as the basic unit of film signification",
     "metz grande syntagmatique sequence shot typology narrative film"),
    # --- 10. noise ---
    ("The revival cinema's marquee bulb has been flickering since Tuesday and the projectionist is still waiting on the replacement from a supplier two towns over.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- reference
    ("David Bordwell and Kristin Thompson's Film Art textbook is still the standard undergraduate entry point, and its neoformalist bent shows in how the poetics chapters foreground style over ideology.", "reference", "knowledge", False,
     [("David Bordwell", "person"), ("Kristin Thompson", "person"), ("Film Art", "publication"), ("neoformalist", "theory"), ("poetics", "concept")],
     [("Film Art", "David Bordwell", "AUTHORED_BY"), ("Film Art", "Kristin Thompson", "AUTHORED_BY")],
     "which Bordwell and Thompson textbook anchors undergraduate survey courses and what theoretical bent shapes it",
     "bordwell thompson film art neoformalist poetics textbook undergraduate"),
    # --- 12 --- milestone
    ("Bong Joon-ho's Parasite took Best Picture at the 2020 Academy Awards, the first non-English-language film to clear that bar and a structural moment for how Oscar voters treat world cinema.", "milestone", "knowledge", False,
     [("Bong Joon-ho", "person"), ("Parasite", "publication"), ("2020 Academy Awards", "event"), ("world cinema", "field")],
     [("Parasite", "Bong Joon-ho", "AUTHORED_BY"), ("Parasite", "2020 Academy Awards", "HAPPENED_ON")],
     "which South Korean film broke the non-English-language Best Picture barrier and when",
     "bong joon ho parasite best picture oscar 2020 world cinema korean"),
    # --- 13 --- fact
    ("Andrei Tarkovsky's Stalker shot most of its Zone footage at an abandoned hydroelectric plant in Estonia, and the chemical run-off from the location is now widely believed to have contributed to the director's early death.", "fact", "knowledge", False,
     [("Andrei Tarkovsky", "person"), ("Stalker", "publication"), ("Zone", "concept"), ("Estonia", "place")],
     [("Stalker", "Andrei Tarkovsky", "AUTHORED_BY"), ("Stalker", "Estonia", "LOCATED_IN")],
     "where did Tarkovsky shoot Stalker and what production-era health claim is attached to the location",
     "tarkovsky stalker zone estonia hydroelectric chemical runoff location"),
    # --- 14 --- decision
    ("Picked Hou Hsiao-hsien's A City of Sadness over Edward Yang's Yi Yi to anchor the Taiwanese New Wave lecture, because its 1947 February 28 framing gave the class a sharper political entry point.", "decision", "knowledge", False,
     [("Hou Hsiao-hsien", "person"), ("A City of Sadness", "publication"), ("Edward Yang", "person"), ("Yi Yi", "publication"), ("Taiwanese New Wave", "concept")],
     [("A City of Sadness", "Hou Hsiao-hsien", "AUTHORED_BY"), ("A City of Sadness", "Yi Yi", "PREFERS")],
     "which Hou film anchored the Taiwanese New Wave lecture instead of Yang's Yi Yi and why",
     "hou hsiao hsien city of sadness edward yang yi yi taiwanese new wave"),
    # --- 15 --- architecture
    ("Italian Neorealism built its post-war aesthetic on non-professional actors, location shooting, and episodic plots; Rossellini's Rome Open City stands as the founding node and De Sica's Bicycle Thieves as the most-cited follow-up.", "architecture", "knowledge", False,
     [("Italian Neorealism", "concept"), ("Rossellini", "person"), ("Rome Open City", "publication"), ("De Sica", "person"), ("Bicycle Thieves", "publication")],
     [("Rome Open City", "Rossellini", "AUTHORED_BY"), ("Bicycle Thieves", "De Sica", "AUTHORED_BY"), ("Bicycle Thieves", "Italian Neorealism", "APPLIES_TO")],
     "which formal choices define Italian Neorealism and which two films anchor the usual canon pair",
     "italian neorealism rossellini rome open city de sica bicycle thieves"),
    # --- 16 --- reference
    ("Jacques Rivette's 1954 Cahiers essay The Genius of Howard Hawks is routinely cited as an early shot across the bow of politique des auteurs, written while Rivette was still a staff critic covering Hawks on the beat and not yet directing.", "reference", "knowledge", False,
     [("Jacques Rivette", "person"), ("Cahiers", "organization"), ("The Genius of Howard Hawks", "publication"), ("Hawks", "person"), ("politique des auteurs", "theory"), ("1954", "date")],
     [("The Genius of Howard Hawks", "Jacques Rivette", "AUTHORED_BY"), ("The Genius of Howard Hawks", "Cahiers", "PUBLISHED_IN")],
     "which early Rivette Cahiers essay is treated as a foundational text of auteur theory and who was its subject",
     "rivette genius howard hawks cahiers politique auteurs 1954 essay"),
    # --- 17 --- decision
    ("Programming chose Agnès Varda's Cléo from 5 to 7 to open the real-time cinema unit over Hitchcock's Rope, because Cléo's ninety-minute Paris drift read more honestly as real-time than Rope's disguised-cut contrivance.", "decision", "knowledge", False,
     [("Agnès Varda", "person"), ("Cléo from 5 to 7", "publication"), ("Hitchcock", "person"), ("Rope", "publication"), ("real-time", "concept")],
     [("Cléo from 5 to 7", "Agnès Varda", "AUTHORED_BY"), ("Cléo from 5 to 7", "Rope", "PREFERS")],
     "which Varda film opened the real-time cinema unit instead of Hitchcock's Rope and why",
     "varda cleo from 5 to 7 hitchcock rope real time cinema unit"),
    # --- 18 --- fact
    ("Wong Kar-wai and Christopher Doyle worked the blurred step-printing look across Chungking Express and Fallen Angels, pushing the shutter to half-speed so ambient neon smeared into painterly trails on screen.", "fact", "knowledge", False,
     [("Wong Kar-wai", "person"), ("Christopher Doyle", "person"), ("Chungking Express", "publication"), ("Fallen Angels", "publication"), ("step-printing", "method")],
     [("Chungking Express", "Wong Kar-wai", "AUTHORED_BY"), ("Fallen Angels", "Wong Kar-wai", "AUTHORED_BY")],
     "which cinematographer worked with Wong Kar-wai on step-printing and in which two nineties films does the technique headline",
     "wong kar wai christopher doyle step printing chungking express fallen angels"),
    # --- 19 --- decision
    ("Soviet montage schools split into Eisenstein's dialectical cut and Vsevolod Pudovkin's constructive editing; Eisenstein forced conflict between shots while Pudovkin built emotional linkage through association.", "decision", "knowledge", False,
     [("Soviet montage", "concept"), ("Eisenstein", "person"), ("dialectical cut", "method"), ("Vsevolod Pudovkin", "person"), ("constructive editing", "method")],
     [("dialectical cut", "Eisenstein", "AUTHORED_BY"), ("constructive editing", "Vsevolod Pudovkin", "AUTHORED_BY")],
     "how did Soviet montage split between Eisenstein's and Pudovkin's approaches and what does each emphasise",
     "soviet montage eisenstein pudovkin dialectical constructive editing split"),
    # --- 20 --- preference
    ("Among the slow-cinema canon I keep circling back to Béla Tarr's Sátántangó for its seven-and-a-half-hour tracking shots, while Tsai Ming-liang's Goodbye, Dragon Inn is the go-to when the seminar has only two hours to spare.", "preference", "knowledge", False,
     [("Béla Tarr", "person"), ("Sátántangó", "publication"), ("Tsai Ming-liang", "person"), ("Goodbye, Dragon Inn", "publication"), ("slow-cinema", "concept")],
     [("Sátántangó", "Béla Tarr", "AUTHORED_BY"), ("Goodbye, Dragon Inn", "Tsai Ming-liang", "AUTHORED_BY")],
     "which slow-cinema films get picked depending on how much seminar time is available",
     "bela tarr satantango tsai ming liang goodbye dragon inn slow cinema"),
    # --- 21 --- milestone
    ("Akira Kurosawa's Rashomon took the Golden Lion at the 1951 Venice Film Festival and effectively opened the Western festival circuit to Japanese cinema; the multi-perspective structure also gave the language a loanword.", "milestone", "knowledge", False,
     [("Akira Kurosawa", "person"), ("Rashomon", "publication"), ("Golden Lion", "event"), ("1951 Venice Film Festival", "event"), ("Japanese cinema", "field")],
     [("Rashomon", "Akira Kurosawa", "AUTHORED_BY"), ("Rashomon", "1951 Venice Film Festival", "HAPPENED_ON")],
     "which Kurosawa film won the 1951 Venice Golden Lion and what broader festival shift did the win trigger",
     "kurosawa rashomon venice golden lion 1951 japanese cinema loanword"),
    # --- 22 --- architecture
    ("German Expressionism's visual grammar leans on painted chiaroscuro sets, canted angles, and psychologised space; The Cabinet of Dr. Caligari stages every distortion literally in the production design rather than on the lens.", "architecture", "knowledge", False,
     [("German Expressionism", "concept"), ("chiaroscuro", "method"), ("canted angles", "method"), ("The Cabinet of Dr. Caligari", "publication"), ("production design", "field")],
     [("The Cabinet of Dr. Caligari", "German Expressionism", "APPLIES_TO")],
     "which formal devices define German Expressionism and which film pushes them into the built set rather than the lens",
     "german expressionism chiaroscuro canted caligari production design set"),
    # --- 23 --- fact
    ("Kenji Mizoguchi's one-scene-one-shot method in Ugetsu builds meaning from within the frame rather than through the cut, which Bazin cited in the late Cahiers pieces on Japanese realism.", "fact", "knowledge", False,
     [("Kenji Mizoguchi", "person"), ("one-scene-one-shot", "method"), ("Ugetsu", "publication"), ("Bazin", "person"), ("Japanese realism", "field")],
     [("Ugetsu", "Kenji Mizoguchi", "AUTHORED_BY")],
     "which Mizoguchi technique did Bazin cite in his late essays on Japanese realism and in which film does it headline",
     "mizoguchi ugetsu one scene one shot bazin cahiers japanese realism"),
    # --- 24 --- decision
    ("The festival retrospective picked Federico Fellini's 8½ over La Dolce Vita to headline the metacinema sidebar, because 8½'s director-as-protagonist frame reads more cleanly as a film about filmmaking.", "decision", "knowledge", False,
     [("Federico Fellini", "person"), ("8½", "publication"), ("La Dolce Vita", "publication"), ("metacinema", "concept")],
     [("8½", "Federico Fellini", "AUTHORED_BY"), ("La Dolce Vita", "Federico Fellini", "AUTHORED_BY"), ("8½", "La Dolce Vita", "PREFERS")],
     "which Fellini film headlined the metacinema sidebar instead of La Dolce Vita and what justified the pick",
     "fellini 8 half dolce vita metacinema director protagonist retrospective"),
    # --- 25 --- architecture
    ("Michelangelo Antonioni's L'Avventura pivots from disappearance to drift; the missing-character plot opens the first act and then quietly deflates so the film's real subject — L'Eclisse-style alienation — can surface.", "architecture", "knowledge", False,
     [("Michelangelo Antonioni", "person"), ("L'Avventura", "publication"), ("L'Eclisse", "publication"), ("alienation", "concept")],
     [("L'Avventura", "Michelangelo Antonioni", "AUTHORED_BY"), ("L'Eclisse", "Michelangelo Antonioni", "AUTHORED_BY")],
     "how does Antonioni redirect L'Avventura's plot away from its missing-character setup and toward a different thematic register",
     "antonioni avventura eclisse alienation disappearance drift plot pivot"),
    # --- 26 --- reference
    ("Éric Rohmer's Six Moral Tales are the canonical reference when teaching dialogue-driven cinema, with My Night at Maud's usually chosen as the most self-contained entry point to the cycle.", "reference", "knowledge", False,
     [("Éric Rohmer", "person"), ("Six Moral Tales", "publication"), ("My Night at Maud's", "publication"), ("dialogue-driven cinema", "concept")],
     [("Six Moral Tales", "Éric Rohmer", "AUTHORED_BY"), ("My Night at Maud's", "Éric Rohmer", "AUTHORED_BY")],
     "which Rohmer cycle is the standard reference for dialogue-driven cinema and which entry typically serves as the classroom opener",
     "rohmer six moral tales my night maud dialogue driven cinema entry"),
    # --- 27 --- decision
    ("Swapped the Kubrick unit's emphasis from 2001 to Barry Lyndon because candlelit Zeiss-lens photography gave the cinematography week a tighter technical case study than star-gate psychedelia.", "decision", "knowledge", False,
     [("Kubrick", "person"), ("2001", "publication"), ("Barry Lyndon", "publication"), ("Zeiss-lens", "tool"), ("cinematography", "field")],
     [("2001", "Kubrick", "AUTHORED_BY"), ("Barry Lyndon", "Kubrick", "AUTHORED_BY"), ("Barry Lyndon", "2001", "PREFERS")],
     "which Kubrick film replaced 2001 as the cinematography-week case study and what technical detail sold it",
     "kubrick 2001 barry lyndon zeiss lens candlelit cinematography unit"),
    # --- 28 --- milestone
    ("Abbas Kiarostami's Taste of Cherry shared the Palme d'Or at Cannes 1997, which cemented the Iranian New Wave's festival-circuit standing and opened Western distribution for Makhmalbaf and Panahi downstream.", "milestone", "knowledge", False,
     [("Abbas Kiarostami", "person"), ("Taste of Cherry", "publication"), ("Palme d'Or", "event"), ("Cannes 1997", "event"), ("Iranian New Wave", "concept")],
     [("Taste of Cherry", "Abbas Kiarostami", "AUTHORED_BY"), ("Taste of Cherry", "Cannes 1997", "HAPPENED_ON")],
     "which Kiarostami film took the 1997 Palme d'Or and what broader movement did the win elevate",
     "kiarostami taste cherry palme dor cannes 1997 iranian new wave"),
    # --- 29 --- architecture
    ("Stan Brakhage's hand-painted frames in Mothlight bypass the camera entirely; moth wings and plant material are taped directly between strips of 16mm, turning the projector into the primary image-maker.", "architecture", "knowledge", False,
     [("Stan Brakhage", "person"), ("Mothlight", "publication"), ("16mm", "tool"), ("projector", "tool")],
     [("Mothlight", "Stan Brakhage", "AUTHORED_BY")],
     "how does Brakhage's Mothlight make images without the camera and which tool becomes the image-maker instead",
     "brakhage mothlight hand painted 16mm projector cameraless moth wings"),
    # --- 30 --- fact
    ("Maya Deren's Meshes of the Afternoon pioneered the American avant-garde's dream-logic editing; her footage of a repeating stairway and mirrored hooded figure became shorthand for the whole tradition.", "fact", "knowledge", False,
     [("Maya Deren", "person"), ("Meshes of the Afternoon", "publication"), ("American avant-garde", "field"), ("dream-logic", "concept")],
     [("Meshes of the Afternoon", "Maya Deren", "AUTHORED_BY")],
     "which Deren film coded the American avant-garde's dream-logic editing into a recognisable house style",
     "deren meshes afternoon american avant garde dream logic stairway"),
    # --- 31 --- decision
    ("Picked Ingmar Bergman's Persona over The Seventh Seal for the identity-and-performance week, because the face-merge optical and Bibi Andersson's monologues give the identity theme a sharper demonstration than medieval allegory.", "decision", "knowledge", False,
     [("Ingmar Bergman", "person"), ("Persona", "publication"), ("The Seventh Seal", "publication"), ("Bibi Andersson", "person"), ("face-merge", "method")],
     [("Persona", "Ingmar Bergman", "AUTHORED_BY"), ("The Seventh Seal", "Ingmar Bergman", "AUTHORED_BY"), ("Persona", "The Seventh Seal", "PREFERS")],
     "which Bergman film anchored the identity-and-performance week over The Seventh Seal and what sealed the pick",
     "bergman persona seventh seal bibi andersson face merge identity week"),
    # --- 32 --- preference
    ("Of the New German Cinema cohort, Werner Herzog's Aguirre is the lecture-hall default, but Fassbinder's Ali: Fear Eats the Soul sits in the graduate seminar because its melodrama layer rewards a second pass.", "preference", "knowledge", False,
     [("New German Cinema", "concept"), ("Werner Herzog", "person"), ("Aguirre", "publication"), ("Fassbinder", "person"), ("Ali: Fear Eats the Soul", "publication"), ("melodrama", "concept")],
     [("Aguirre", "Werner Herzog", "AUTHORED_BY"), ("Ali: Fear Eats the Soul", "Fassbinder", "AUTHORED_BY")],
     "which New German Cinema films does the syllabus reserve for undergraduate lecture versus graduate seminar",
     "new german cinema herzog aguirre fassbinder ali fear eats soul melodrama"),
    # --- 33 --- architecture
    ("Wim Wenders's road-movie triptych — Alice in the Cities, Wrong Move, Kings of the Road — frames West German post-war identity through repeated border crossings and the Polaroid as diegetic witness.", "architecture", "knowledge", False,
     [("Wim Wenders", "person"), ("Alice in the Cities", "publication"), ("Wrong Move", "publication"), ("Kings of the Road", "publication"), ("Polaroid", "tool")],
     [("Alice in the Cities", "Wim Wenders", "AUTHORED_BY"), ("Wrong Move", "Wim Wenders", "AUTHORED_BY"), ("Kings of the Road", "Wim Wenders", "AUTHORED_BY")],
     "which three Wenders road films form the West German identity triptych and what object recurs as diegetic witness",
     "wenders alice cities wrong move kings road triptych polaroid border"),
    # --- 34 --- milestone
    ("New Hollywood's canonical opening is Bonnie and Clyde in 1967, with Easy Rider in 1969 sealing the generational handover from the studio system to the director-driven decade that followed.", "milestone", "knowledge", False,
     [("New Hollywood", "concept"), ("Bonnie and Clyde", "publication"), ("1967", "date"), ("Easy Rider", "publication"), ("1969", "date"), ("studio system", "concept")],
     [("Bonnie and Clyde", "1967", "HAPPENED_ON"), ("Easy Rider", "1969", "HAPPENED_ON")],
     "which two films bookend New Hollywood's breakthrough window and what older system did they displace",
     "new hollywood bonnie clyde 1967 easy rider 1969 studio system"),
    # --- 35 --- fact
    ("Martin Scorsese edits with Thelma Schoonmaker on every feature since Raging Bull, and the collaboration is the most-cited example in film-school editing classes of a sustained director-editor pairing.", "fact", "knowledge", False,
     [("Martin Scorsese", "person"), ("Thelma Schoonmaker", "person"), ("Raging Bull", "publication"), ("editing", "field")],
     [("Raging Bull", "Martin Scorsese", "AUTHORED_BY")],
     "which editor has worked with Scorsese since Raging Bull and why is the pairing singled out in editing classes",
     "scorsese thelma schoonmaker raging bull editor director editing class"),
    # --- 36 --- decision
    ("The seminar swapped Coppola's The Godfather for Apocalypse Now when the unit refocused on sound design, because Walter Murch's multi-track layering gave a more concrete lab example than a family-saga rewatch.", "decision", "knowledge", False,
     [("Coppola", "person"), ("The Godfather", "publication"), ("Apocalypse Now", "publication"), ("Walter Murch", "person"), ("sound design", "field")],
     [("The Godfather", "Coppola", "AUTHORED_BY"), ("Apocalypse Now", "Coppola", "AUTHORED_BY"), ("Apocalypse Now", "The Godfather", "REPLACES")],
     "which Coppola swap anchored the sound-design unit and which editor made the case",
     "coppola godfather apocalypse now walter murch sound design seminar swap"),
    # --- 37 --- reference
    ("Paul Thomas Anderson's There Will Be Blood is the go-to reference for contemporary American epic framing, and Robert Elswit's widescreen compositions keep showing up in current cinematography breakdowns.", "reference", "knowledge", False,
     [("Paul Thomas Anderson", "person"), ("There Will Be Blood", "publication"), ("Robert Elswit", "person"), ("widescreen", "method"), ("American epic", "concept")],
     [("There Will Be Blood", "Paul Thomas Anderson", "AUTHORED_BY")],
     "which PTA film anchors the contemporary American-epic reference shelf and which cinematographer keeps showing up in breakdowns",
     "paul thomas anderson there will blood elswit widescreen american epic"),
    # --- 38 --- problem
    ("David Fincher's shoot on Zodiac kept burning days because film dailies couldn't keep up with the high take counts; switching to RED One digital capture fixed the turnaround and let the edit bay refine framing in parallel with production.", "problem", "knowledge", False,
     [("David Fincher", "person"), ("Zodiac", "publication"), ("RED One", "tool"), ("edit bay", "field")],
     [("Zodiac", "David Fincher", "AUTHORED_BY")],
     "which production-turnaround problem on Fincher's Zodiac got solved by moving to RED One digital capture",
     "fincher zodiac red one dailies edit bay digital high take turnaround"),
    # --- 39 --- milestone
    ("Denis Villeneuve's Arrival in 2016 reset studio expectations for cerebral science fiction, and its box-office haul was credited with unlocking the Dune adaptation greenlight a year later.", "milestone", "knowledge", False,
     [("Denis Villeneuve", "person"), ("Arrival", "publication"), ("2016", "date"), ("Dune", "publication"), ("cerebral science fiction", "concept")],
     [("Arrival", "Denis Villeneuve", "AUTHORED_BY"), ("Arrival", "2016", "HAPPENED_ON"), ("Dune", "Denis Villeneuve", "AUTHORED_BY")],
     "which 2016 Villeneuve release reset the cerebral science-fiction market and what later adaptation followed from its numbers",
     "villeneuve arrival 2016 dune cerebral science fiction greenlight box"),
    # --- 40 --- architecture
    ("Hayao Miyazaki's Studio Ghibli workflow anchors a hand-drawn pipeline around Miyazaki's own storyboards, and digital compositing only joins in the final pass so the drawn line keeps its weight on the final frame.", "architecture", "knowledge", False,
     [("Hayao Miyazaki", "person"), ("Studio Ghibli", "organization"), ("hand-drawn", "method"), ("digital compositing", "method"), ("storyboards", "tool")],
     [("Studio Ghibli", "Hayao Miyazaki", "WORKS_AT")],
     "how does the Ghibli pipeline order hand-drawn animation against digital compositing and what keeps the line prominent",
     "miyazaki ghibli hand drawn storyboard digital composite pipeline line"),
    # --- 41 --- decision
    ("Park Chan-wook's Decision to Leave got scheduled as the Korean New Wave coda instead of Oldboy, because the colder restraint and procedural frame made a cleaner contrast with Bong Joon-ho's Memories of Murder earlier in the run.", "decision", "knowledge", False,
     [("Park Chan-wook", "person"), ("Decision to Leave", "publication"), ("Oldboy", "publication"), ("Korean New Wave", "concept"), ("Memories of Murder", "publication")],
     [("Decision to Leave", "Park Chan-wook", "AUTHORED_BY"), ("Oldboy", "Park Chan-wook", "AUTHORED_BY"), ("Decision to Leave", "Oldboy", "PREFERS")],
     "which Park Chan-wook film closed out the Korean New Wave slot over Oldboy and what contrast drove it",
     "park chan wook decision to leave oldboy korean new wave memories murder"),
    # --- 42. noise ---
    ("The usual coffee cart in front of the film school moved to the other side of the quad this semester and nobody warned the visiting lecturers.", "fact", "noise", True, [], [], None, None),
    # --- 43 --- fact
    ("Hong Kong New Wave cinematographers standardised on anamorphic prime lenses with heavy bloom in the late eighties, a look that spread into Wong Kar-wai's Days of Being Wild and Johnnie To's early Milkyway features.", "fact", "knowledge", False,
     [("Hong Kong New Wave", "concept"), ("anamorphic", "tool"), ("Wong Kar-wai", "person"), ("Days of Being Wild", "publication"), ("Johnnie To", "person"), ("Milkyway", "organization")],
     [("Days of Being Wild", "Wong Kar-wai", "AUTHORED_BY"), ("Johnnie To", "Milkyway", "WORKS_AT")],
     "which lens standard defined the late-eighties Hong Kong New Wave look and which two directors carried it forward",
     "hong kong new wave anamorphic bloom wong kar wai days being wild johnnie to"),
    # --- 44 --- reference
    ("Theo Angelopoulos's Landscape in the Mist is the standard reference for the long-take tracking shot across Balkan geography, and its one-shot border crossing still gets copied in current festival-circuit work.", "reference", "knowledge", False,
     [("Theo Angelopoulos", "person"), ("Landscape in the Mist", "publication"), ("long-take", "method"), ("Balkan", "place")],
     [("Landscape in the Mist", "Theo Angelopoulos", "AUTHORED_BY"), ("Landscape in the Mist", "Balkan", "LOCATED_IN")],
     "which Angelopoulos film is the canonical reference for long-take tracking across Balkan geography",
     "angelopoulos landscape mist long take tracking balkan border crossing"),
    # --- 45 --- decision
    ("Scheduled Claire Denis's Beau Travail in place of a second Godard screening when the term refocused on the body in cinema; the Melville-derived choreography gave the seminar a tangible object that abstract essayism couldn't match.", "decision", "knowledge", False,
     [("Claire Denis", "person"), ("Beau Travail", "publication"), ("Godard", "person"), ("Melville", "person"), ("body in cinema", "concept")],
     [("Beau Travail", "Claire Denis", "AUTHORED_BY"), ("Beau Travail", "Godard", "REPLACES")],
     "which Claire Denis film replaced the second Godard screening when the seminar pivoted to the body in cinema",
     "claire denis beau travail godard melville body cinema choreography seminar"),
    # --- 46 --- preference
    ("For the melodrama unit I prefer Pedro Almodóvar's Talk to Her over All About My Mother, because the narrative risk of the central ethical question gives seminar discussion more to chew on than the ensemble grief piece.", "preference", "knowledge", False,
     [("Pedro Almodóvar", "person"), ("Talk to Her", "publication"), ("All About My Mother", "publication"), ("melodrama", "concept")],
     [("Talk to Her", "Pedro Almodóvar", "AUTHORED_BY"), ("All About My Mother", "Pedro Almodóvar", "AUTHORED_BY"), ("Talk to Her", "All About My Mother", "PREFERS")],
     "which Almodóvar film headlines the melodrama unit instead of All About My Mother and what justifies the choice",
     "almodovar talk to her all about my mother melodrama seminar discussion"),
    # --- 47 --- problem
    ("The screening of Truffaut's The 400 Blows in the French New Wave unit kept stalling because the print was scratched at the freeze-frame ending; swapped to a restored 4K scan from the Criterion Collection and the classroom discussion finally landed.", "problem", "knowledge", False,
     [("Truffaut", "person"), ("The 400 Blows", "publication"), ("French New Wave", "concept"), ("freeze-frame", "method"), ("Criterion Collection", "organization")],
     [("The 400 Blows", "Truffaut", "AUTHORED_BY"), ("The 400 Blows", "French New Wave", "APPLIES_TO")],
     "what went wrong with The 400 Blows screening and which source fixed the freeze-frame ending playback",
     "truffaut 400 blows french new wave freeze frame scratch criterion"),
    # --- 48 --- problem
    ("The Mumblecore module struggled on first pass: improvised performances in Andrew Bujalski's Funny Ha Ha read as sloppy to the class; reframing the unit around the low-budget DV aesthetic and Joe Swanberg's Hannah Takes the Stairs fixed the engagement gap.", "problem", "knowledge", False,
     [("Mumblecore", "concept"), ("Andrew Bujalski", "person"), ("Funny Ha Ha", "publication"), ("Joe Swanberg", "person"), ("Hannah Takes the Stairs", "publication"), ("DV", "tool")],
     [("Funny Ha Ha", "Andrew Bujalski", "AUTHORED_BY"), ("Hannah Takes the Stairs", "Joe Swanberg", "AUTHORED_BY"), ("Funny Ha Ha", "Mumblecore", "APPLIES_TO")],
     "which reframing rescued the Mumblecore module after Funny Ha Ha read as sloppy on first pass",
     "mumblecore bujalski funny ha ha swanberg hannah stairs dv low budget"),
    # --- 49 --- preference
    ("When assigning a single auteur-theory primer I lean on François Truffaut's A Certain Tendency of French Cinema rather than Andrew Sarris's Notes on the Auteur Theory, because the Truffaut piece shows the polemic register in its original form.", "preference", "knowledge", False,
     [("François Truffaut", "person"), ("A Certain Tendency of French Cinema", "publication"), ("Andrew Sarris", "person"), ("Notes on the Auteur Theory", "publication"), ("auteur-theory", "theory")],
     [("A Certain Tendency of French Cinema", "François Truffaut", "AUTHORED_BY"), ("Notes on the Auteur Theory", "Andrew Sarris", "AUTHORED_BY"), ("A Certain Tendency of French Cinema", "Notes on the Auteur Theory", "PREFERS")],
     "which auteur-theory primer gets assigned first and which competing essay sits in the optional reading",
     "truffaut certain tendency french cinema sarris notes auteur theory primer"),
    # --- 50 --- milestone
    ("Luis Buñuel's Un Chien Andalou in 1929 fused surrealism with cinema in a way the art-world alone couldn't, and the six-minute sliced-eye opening is still the most-cited shock cut in the first lecture of any film-history survey.", "milestone", "knowledge", False,
     [("Luis Buñuel", "person"), ("Un Chien Andalou", "publication"), ("1929", "date"), ("surrealism", "concept"), ("shock cut", "method")],
     [("Un Chien Andalou", "Luis Buñuel", "AUTHORED_BY"), ("Un Chien Andalou", "1929", "HAPPENED_ON"), ("Un Chien Andalou", "surrealism", "APPLIES_TO")],
     "which 1929 Buñuel short fused surrealism with cinema and what opening shot is its most-cited moment",
     "bunuel chien andalou 1929 surrealism shock cut sliced eye film history"),
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
