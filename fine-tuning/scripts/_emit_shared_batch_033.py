"""One-off emitter for shared-base batch-033 — knowledge domain (visual arts, music theory, architecture, design, aesthetics).

Writes 50 rows with ids shared-01601..01650.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_033.tmp.jsonl"
ID_OFFSET = 1600

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Bauhaus school, founded by Walter Gropius in 1919, unified fine art and craft under a functional design pedagogy.", "milestone", "knowledge", False,
     [("Bauhaus", "concept"), ("Walter Gropius", "person"), ("1919", "date")],
     [("Bauhaus", "Walter Gropius", "AUTHORED_BY")],
     "when and by whom was the influential German design school established",
     "Weimar Dessau craft unity functional pedagogy founding year"),
    # --- 2 ---
    ("Stravinsky's The Rite of Spring premiered in Paris in 1913 and provoked a notorious audience riot with its irregular rhythms.", "milestone", "knowledge", False,
     [("Stravinsky", "person"), ("The Rite of Spring", "publication"), ("Paris", "place"), ("1913", "date")],
     [("The Rite of Spring", "Stravinsky", "AUTHORED_BY")],
     "which ballet score sparked a legendary theatre disturbance on its debut",
     "primitivist ballet premiere riot rhythm Paris year"),
    # --- 3 ---
    ("Tadao Ando prefers exposed board-formed concrete over ornamental cladding to foreground light, shadow, and tactile surface.", "preference", "knowledge", False,
     [("Tadao Ando", "person"), ("board-formed concrete", "concept"), ("ornamental cladding", "concept")],
     [("board-formed concrete", "ornamental cladding", "PREFERS")],
     "which material does the Japanese architect favour to expose light and texture",
     "exposed concrete formwork light shadow signature material choice"),
    # --- 4 ---
    ("Dieter Rams's ten principles for good design, formulated at Braun, still anchor product design discourse.", "reference", "knowledge", False,
     [("Dieter Rams", "person"), ("ten principles for good design", "framework"), ("Braun", "organization")],
     [("ten principles for good design", "Dieter Rams", "AUTHORED_BY")],
     "which product-design heuristics from a German consumer-electronics firm still guide studios",
     "less but better Braun industrial design principles checklist"),
    # --- 5 ---
    ("The Armory Show of 1913 introduced European modernism to the American public in New York, shocking visitors with Duchamp's Nude Descending a Staircase.", "milestone", "knowledge", False,
     [("Armory Show", "event"), ("1913", "date"), ("New York", "place"), ("Duchamp", "person"), ("Nude Descending a Staircase", "publication")],
     [("Nude Descending a Staircase", "Duchamp", "AUTHORED_BY")],
     "which early-twentieth-century exhibition brought European avant-garde painting to American audiences",
     "International Exhibition of Modern Art New York modernism shock year"),
    # --- 6 ---
    ("Schenkerian analysis reduces tonal works to a fundamental Ursatz structure revealing voice-leading across hierarchical levels.", "fact", "knowledge", False,
     [("Schenkerian analysis", "method"), ("Ursatz", "concept"), ("voice-leading", "concept")],
     [],
     "which analytical method strips tonal music down to a background structural skeleton",
     "reductive analysis tonal hierarchy background middleground foreground"),
    # --- 7 ---
    ("Sol LeWitt's wall drawings are defined by written instructions, which may be executed by any draftsperson following the prescribed rules.", "fact", "knowledge", False,
     [("Sol LeWitt", "person"), ("wall drawings", "publication"), ("written instructions", "method")],
     [("wall drawings", "Sol LeWitt", "AUTHORED_BY")],
     "whose conceptual works consist of written directives rather than a fixed hand-made object",
     "conceptual instruction executor draftsperson rule certificate"),
    # --- 8 ---
    ("Brutalism, named from beton brut, favoured raw concrete and expressive massing in postwar civic architecture.", "fact", "knowledge", False,
     [("Brutalism", "concept"), ("beton brut", "concept"), ("raw concrete", "concept")],
     [],
     "which postwar architectural movement took its name from a French term for rough concrete",
     "beton brut heavy civic monumental raw concrete postwar"),
    # --- 9 ---
    ("Clement Greenberg's formalist criticism championed medium specificity and flatness as the endgame of modernist painting.", "fact", "knowledge", False,
     [("Clement Greenberg", "person"), ("formalist criticism", "theory"), ("medium specificity", "concept")],
     [],
     "whose mid-century criticism argued modern painting should pursue flatness and its own medium",
     "modernist painting flatness purity medium criticism essays"),
    # --- 10. noise ---
    ("Let me double-check the exhibition dates before I commit to them.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Bridget Riley's op-art paintings follow strict geometric rules that generate optical vibration through high-contrast pattern repetition.", "fact", "knowledge", False,
     [("Bridget Riley", "person"), ("op-art", "concept"), ("geometric rules", "method")],
     [],
     "whose rule-based op-art paintings rely on repeating geometric pattern for optical effect",
     "optical art pattern rule vibration high contrast painter"),
    # --- 12 ---
    ("The Memphis Group, formed in Milan in 1981 around Ettore Sottsass, rejected corporate modernism with colourful laminate postmodern objects.", "milestone", "knowledge", False,
     [("Memphis Group", "concept"), ("Milan", "place"), ("1981", "date"), ("Ettore Sottsass", "person")],
     [("Memphis Group", "Ettore Sottsass", "AUTHORED_BY")],
     "when and where did the postmodern Italian furniture collective coalesce",
     "Italian postmodern design laminate colour founding year"),
    # --- 13 ---
    ("Steve Reich's Music for 18 Musicians, completed in 1976, codified phase-pulse minimalism with eleven interlocking chord cycles.", "reference", "knowledge", False,
     [("Steve Reich", "person"), ("Music for 18 Musicians", "publication"), ("1976", "date"), ("phase-pulse minimalism", "method")],
     [("Music for 18 Musicians", "Steve Reich", "AUTHORED_BY")],
     "which landmark minimalist composition organised its hour around cycling chords",
     "minimalism phasing eleven chord cycle pulse ensemble year"),
    # --- 14 ---
    ("Critical regionalism, articulated by Kenneth Frampton, resists placeless modernism by grounding buildings in local climate, material, and topography.", "fact", "knowledge", False,
     [("Critical regionalism", "theory"), ("Kenneth Frampton", "person"), ("placeless modernism", "concept")],
     [("Critical regionalism", "Kenneth Frampton", "AUTHORED_BY")],
     "which architectural theory pushes back against generic modernism by insisting on place",
     "Frampton resistance place climate topography material essay"),
    # --- 15 ---
    ("Mono-ha artists in late-1960s Japan presented raw materials such as stone, steel, and wood in minimal arrangements to foreground material encounter.", "fact", "knowledge", False,
     [("Mono-ha", "concept"), ("Japan", "place"), ("stone", "concept"), ("steel", "concept"), ("wood", "concept")],
     [],
     "which late-1960s Japanese art tendency staged raw materials in spare arrangements",
     "school of things Japanese raw material encounter minimal"),
    # --- 16 ---
    ("Bach's Well-Tempered Clavier, completed across two books in 1722 and 1742, pairs a prelude and fugue in every major and minor key.", "reference", "knowledge", False,
     [("Bach", "person"), ("Well-Tempered Clavier", "publication"), ("1722", "date"), ("1742", "date")],
     [("Well-Tempered Clavier", "Bach", "AUTHORED_BY")],
     "which keyboard cycle walks systematically through every major and minor key",
     "forty-eight preludes fugues all keys temperament collection"),
    # --- 17 ---
    ("Relational aesthetics, proposed by Nicolas Bourriaud in 1998, treats artworks as loci of social encounter rather than autonomous objects.", "milestone", "knowledge", False,
     [("Relational aesthetics", "theory"), ("Nicolas Bourriaud", "person"), ("1998", "date")],
     [("Relational aesthetics", "Nicolas Bourriaud", "AUTHORED_BY")],
     "when did the French theory recasting art as social interchange appear",
     "Esthetique relationnelle social encounter art theory year"),
    # --- 18 ---
    ("Eva Hesse's process-based sculptures used latex, fibreglass, and cheesecloth to foreground material fragility and impermanence.", "fact", "knowledge", False,
     [("Eva Hesse", "person"), ("latex", "concept"), ("fibreglass", "concept"), ("cheesecloth", "concept")],
     [],
     "whose sculptural practice embraced fugitive industrial materials to court decay",
     "post minimalist sculpture latex fibreglass fragility material"),
    # --- 19 ---
    ("Lina Bo Bardi's SESC Pompeia, completed in Sao Paulo in 1986, converted a factory complex into a civic leisure facility with raw concrete towers.", "reference", "knowledge", False,
     [("Lina Bo Bardi", "person"), ("SESC Pompeia", "publication"), ("Sao Paulo", "place"), ("1986", "date")],
     [("SESC Pompeia", "Lina Bo Bardi", "AUTHORED_BY")],
     "which Brazilian civic complex repurposed a factory with board-marked concrete towers",
     "factory conversion civic leisure raw concrete tower year"),
    # --- 20 ---
    ("Schoenberg's twelve-tone technique replaces tonal hierarchy with an ordered row of all twelve pitch classes used as the compositional basis.", "decision", "knowledge", False,
     [("Schoenberg", "person"), ("twelve-tone technique", "method"), ("tonal hierarchy", "concept")],
     [("twelve-tone technique", "tonal hierarchy", "REPLACES")],
     "which serial technique displaced functional tonality in early twentieth-century composition",
     "dodecaphony serial row pitch class order atonal method"),
    # --- 21 ---
    ("Arte Povera, theorised by Germano Celant in 1967, embraced humble materials like earth, burlap, and neon against commodified art.", "milestone", "knowledge", False,
     [("Arte Povera", "concept"), ("Germano Celant", "person"), ("1967", "date")],
     [("Arte Povera", "Germano Celant", "AUTHORED_BY")],
     "when did the Italian poor-materials movement receive its naming manifesto",
     "poor art Italian Celant manifesto humble material year"),
    # --- 22 ---
    ("Kant's Critique of Judgment grounds aesthetic judgement in disinterested pleasure and the free play of the faculties.", "reference", "knowledge", False,
     [("Kant", "person"), ("Critique of Judgment", "publication"), ("disinterested pleasure", "concept")],
     [("Critique of Judgment", "Kant", "AUTHORED_BY")],
     "whose third critique built taste on detached pleasure and cognitive free play",
     "third critique taste disinterest cognitive play treatise"),
    # --- 23 ---
    ("Gyorgy Ligeti's Atmospheres, premiered in 1961, uses micropolyphony to dissolve melody and rhythm into dense static textures.", "reference", "knowledge", False,
     [("Gyorgy Ligeti", "person"), ("Atmospheres", "publication"), ("1961", "date"), ("micropolyphony", "method")],
     [("Atmospheres", "Gyorgy Ligeti", "AUTHORED_BY")],
     "which orchestral work introduced a dense cloud-like polyphonic texture to wide audiences",
     "micropolyphony cluster texture orchestral premiere year"),
    # --- 24 ---
    ("The International Style, codified by the 1932 MoMA exhibition curated by Hitchcock and Johnson, promoted volume, regularity, and the rejection of applied ornament.", "milestone", "knowledge", False,
     [("International Style", "concept"), ("1932", "date"), ("MoMA", "organization"), ("Hitchcock", "person"), ("Johnson", "person")],
     [],
     "which 1932 New York exhibition named and codified a pan-European modern architecture",
     "MoMA International Style curated exhibition ornament volume year"),
    # --- 25 ---
    ("Glenn Murcutt prefers long verandahs and corrugated metal roofs over sealed glass facades to negotiate Australian climate passively.", "preference", "knowledge", False,
     [("Glenn Murcutt", "person"), ("verandahs", "concept"), ("corrugated metal roofs", "concept"), ("glass facades", "concept")],
     [("verandahs", "glass facades", "PREFERS")],
     "which Australian architect favours shaded verandahs over sealed glass envelopes",
     "Australian climate verandah corrugated metal passive preference"),
    # --- 26 ---
    ("The Pictures Generation, active in New York around 1977, appropriated mass-media imagery to critique authorship and representation.", "fact", "knowledge", False,
     [("Pictures Generation", "concept"), ("New York", "place"), ("1977", "date")],
     [],
     "which late-1970s New York cohort appropriated media imagery to probe authorship",
     "appropriation media imagery authorship critique late seventies"),
    # --- 27 ---
    ("Constructivism, led by Rodchenko and Tatlin in post-1917 Russia, fused geometric abstraction with utilitarian production aims.", "fact", "knowledge", False,
     [("Constructivism", "concept"), ("Rodchenko", "person"), ("Tatlin", "person"), ("Russia", "place")],
     [],
     "which Russian avant-garde yoked geometric abstraction to socially useful production",
     "Russian avant garde utilitarian geometry production art"),
    # --- 28 ---
    ("Spectralism, centred on Grisey and Murail in 1970s France, derives harmony from computer analysis of the acoustic spectrum.", "fact", "knowledge", False,
     [("Spectralism", "concept"), ("Grisey", "person"), ("Murail", "person"), ("France", "place")],
     [],
     "which French compositional school built harmony from the analysed sound spectrum",
     "spectral music Grisey Murail IRCAM partials analysis"),
    # --- 29 ---
    ("The Ulm School of Design, active from 1953 to 1968, extended the Bauhaus into systems thinking and scientific design methodology.", "fact", "knowledge", False,
     [("Ulm School of Design", "organization"), ("Bauhaus", "concept"), ("1953", "date"), ("1968", "date")],
     [("Ulm School of Design", "Bauhaus", "BUILDS_ON")],
     "which postwar German school continued Bauhaus ideals within a systems and science framework",
     "HfG Ulm systems design methodology successor postwar"),
    # --- 30 ---
    ("Metabolism, launched by Kurosawa, Kurokawa, and Maki at the 1960 World Design Conference in Tokyo, envisioned cities as biological systems of replaceable parts.", "milestone", "knowledge", False,
     [("Metabolism", "concept"), ("Kurosawa", "person"), ("Kurokawa", "person"), ("Maki", "person"), ("Tokyo", "place"), ("1960", "date")],
     [],
     "when and where did the Japanese architectural movement treating cities as organisms launch",
     "Japanese metabolist manifesto Tokyo world design conference year"),
    # --- 31 ---
    ("Walter Benjamin's Work of Art in the Age of Mechanical Reproduction, published in 1935, argued that reproduction strips the artwork of its aura.", "reference", "knowledge", False,
     [("Walter Benjamin", "person"), ("Work of Art in the Age of Mechanical Reproduction", "publication"), ("1935", "date"), ("aura", "concept")],
     [("Work of Art in the Age of Mechanical Reproduction", "Walter Benjamin", "AUTHORED_BY")],
     "which essay famously linked mechanical reproduction to the loss of artistic aura",
     "aura reproduction technology art essay Benjamin year"),
    # --- 32 ---
    ("Sonata form organises a classical movement into exposition, development, and recapitulation with a tonal return that resolves an earlier departure.", "fact", "knowledge", False,
     [("Sonata form", "method"), ("exposition", "concept"), ("development", "concept"), ("recapitulation", "concept")],
     [],
     "which classical movement plan centres on a tonal departure and resolving return",
     "exposition development recapitulation tonal classical plan"),
    # --- 33 ---
    ("Mies van der Rohe's Barcelona Pavilion, completed in 1929, condensed modernist ideals into free-flowing space, travertine, and onyx planes.", "milestone", "knowledge", False,
     [("Mies van der Rohe", "person"), ("Barcelona Pavilion", "publication"), ("1929", "date"), ("travertine", "concept"), ("onyx", "concept")],
     [("Barcelona Pavilion", "Mies van der Rohe", "AUTHORED_BY")],
     "when did the travertine-and-onyx modernist pavilion in Catalonia open",
     "free plan flowing space travertine onyx pavilion modernist year"),
    # --- 34. noise ---
    ("Hmm, I need to check the catalogue raisonne for the exact attribution.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("This Is Tomorrow at the Whitechapel Gallery in 1956 brought pop art, architecture, and collage together and is often credited as British Pop's debut.", "milestone", "knowledge", False,
     [("This Is Tomorrow", "event"), ("Whitechapel Gallery", "organization"), ("1956", "date")],
     [],
     "which 1956 London exhibition is typically cited as the debut of British Pop art",
     "Whitechapel exhibition British pop independent group year"),
    # --- 36 ---
    ("Species counterpoint, systematised by Fux in Gradus ad Parnassum of 1725, trains composers through five graded rule sets.", "reference", "knowledge", False,
     [("Species counterpoint", "method"), ("Fux", "person"), ("Gradus ad Parnassum", "publication"), ("1725", "date")],
     [("Gradus ad Parnassum", "Fux", "AUTHORED_BY")],
     "which early-eighteenth-century treatise formalised graded counterpoint exercises",
     "five species counterpoint pedagogy treatise year"),
    # --- 37 ---
    ("Ansel Adams's Zone System divides tonal range into eleven zones so photographers can plan exposure and development to hit intended values.", "fact", "knowledge", False,
     [("Ansel Adams", "person"), ("Zone System", "method"), ("tonal range", "concept")],
     [("Zone System", "Ansel Adams", "AUTHORED_BY")],
     "which photographic framework splits tone into numbered zones to plan exposure",
     "zone system tonal exposure development landscape photography"),
    # --- 38 ---
    ("Heinrich Wolfflin's Principles of Art History, published in 1915, proposed five polar pairs such as linear vs painterly to contrast Renaissance and Baroque styles.", "reference", "knowledge", False,
     [("Heinrich Wolfflin", "person"), ("Principles of Art History", "publication"), ("1915", "date"), ("linear", "concept"), ("painterly", "concept")],
     [("Principles of Art History", "Heinrich Wolfflin", "AUTHORED_BY")],
     "which 1915 art-historical book opposed Renaissance and Baroque through paired formal concepts",
     "linear painterly polar pairs style analysis textbook year"),
    # --- 39 ---
    ("The Crystal Palace, erected for the 1851 Great Exhibition in London by Paxton, is an emerging technology showcase of modular cast-iron and plate-glass prefabrication.", "fact", "knowledge", False,
     [("Crystal Palace", "publication"), ("1851", "date"), ("Great Exhibition", "event"), ("London", "place"), ("Paxton", "person"), ("cast-iron", "concept"), ("plate-glass", "concept")],
     [("Crystal Palace", "Paxton", "AUTHORED_BY")],
     "which 1851 London pavilion showcased modular iron-and-glass prefabrication at scale",
     "Paxton great exhibition iron glass prefabrication modular year"),
    # --- 40 ---
    ("Documenta, founded by Arnold Bode in Kassel in 1955, runs every five years and remains the benchmark exhibition for contemporary art.", "reference", "knowledge", False,
     [("Documenta", "event"), ("Arnold Bode", "person"), ("Kassel", "place"), ("1955", "date")],
     [("Documenta", "Arnold Bode", "AUTHORED_BY")],
     "which German five-yearly exhibition anchors the contemporary art calendar",
     "Kassel quinquennial contemporary exhibition founder year"),
    # --- 41 ---
    ("Kahn's Salk Institute, completed in La Jolla in 1965, pairs symmetric laboratory blocks with a central travertine plaza oriented to the Pacific.", "reference", "knowledge", False,
     [("Kahn", "person"), ("Salk Institute", "publication"), ("La Jolla", "place"), ("1965", "date"), ("travertine", "concept")],
     [("Salk Institute", "Kahn", "AUTHORED_BY")],
     "which Californian research complex frames a travertine plaza oriented toward the Pacific",
     "Salk travertine plaza laboratory symmetric axis year"),
    # --- 42 ---
    ("Monteverdi's L'Orfeo, premiered in Mantua in 1607, is often treated as the first fully realised opera in the modern sense.", "milestone", "knowledge", False,
     [("Monteverdi", "person"), ("L'Orfeo", "publication"), ("Mantua", "place"), ("1607", "date")],
     [("L'Orfeo", "Monteverdi", "AUTHORED_BY")],
     "which early-seventeenth-century work is commonly called the first mature opera",
     "early opera Mantua premiere baroque founder year"),
    # --- 43 ---
    ("Postmodern architecture, argued for in Robert Venturi's Complexity and Contradiction of 1966, replaced the austere International Style with historical quotation and ornament.", "decision", "knowledge", False,
     [("Postmodern architecture", "concept"), ("Robert Venturi", "person"), ("Complexity and Contradiction", "publication"), ("1966", "date"), ("International Style", "concept")],
     [("Complexity and Contradiction", "Robert Venturi", "AUTHORED_BY"), ("Postmodern architecture", "International Style", "REPLACES")],
     "which 1966 book helped push architecture past austere modernism into historical quotation",
     "Venturi complexity contradiction postmodern manifesto year"),
    # --- 44 ---
    ("Cindy Sherman's Untitled Film Stills, produced between 1977 and 1980, stage the artist as anonymous female archetypes drawn from cinema.", "reference", "knowledge", False,
     [("Cindy Sherman", "person"), ("Untitled Film Stills", "publication"), ("1977", "date"), ("1980", "date")],
     [("Untitled Film Stills", "Cindy Sherman", "AUTHORED_BY")],
     "which late-1970s photographic series cast its maker as generic cinematic heroines",
     "Sherman film still archetype photography late seventies year"),
    # --- 45 ---
    ("Picturesque theory, articulated by Uvedale Price in 1794, placed roughness and variety between Burke's sublime and beautiful categories.", "milestone", "knowledge", False,
     [("Picturesque theory", "theory"), ("Uvedale Price", "person"), ("1794", "date"), ("Burke", "person")],
     [("Picturesque theory", "Uvedale Price", "AUTHORED_BY")],
     "when did the picturesque emerge as a mediating aesthetic category between sublime and beautiful",
     "picturesque roughness variety Burke aesthetic category year"),
    # --- 46 ---
    ("Le Corbusier's Villa Savoye, completed near Paris in 1931, demonstrates his Five Points with pilotis, free plan, roof garden, free facade, and ribbon windows.", "reference", "knowledge", False,
     [("Le Corbusier", "person"), ("Villa Savoye", "publication"), ("Paris", "place"), ("1931", "date"), ("Five Points", "framework")],
     [("Villa Savoye", "Le Corbusier", "AUTHORED_BY"), ("Villa Savoye", "Five Points", "IMPLEMENTS")],
     "which villa near Paris exemplifies the Swiss architect's five points of modernism",
     "pilotis free plan ribbon window roof garden demonstration year"),
    # --- 47 ---
    ("Zaha Hadid's parametric studio replaces orthogonal modernist geometry with algorithmically generated curvilinear forms.", "decision", "knowledge", False,
     [("Zaha Hadid", "person"), ("parametric", "method"), ("orthogonal modernist geometry", "concept")],
     [("parametric", "orthogonal modernist geometry", "REPLACES")],
     "which architect's office swapped right-angled modernist geometry for algorithmic curves",
     "parametric design curvilinear algorithmic Hadid studio"),
    # --- 48 ---
    ("Formalism in film theory depends on technical features such as framing, editing, and sound rather than narrative content for critical judgement.", "fact", "knowledge", False,
     [("Formalism", "theory"), ("film theory", "field"), ("framing", "concept"), ("editing", "concept")],
     [("Formalism", "framing", "DEPENDS_ON")],
     "which film-theoretic stance weighs framing and editing over narrative content",
     "formalist film theory technique framing editing judgement"),
    # --- 49 ---
    ("Pierre Boulez's Le marteau sans maitre, premiered in 1955, extends total serialism to rhythm, dynamics, and timbre alongside pitch.", "reference", "knowledge", False,
     [("Pierre Boulez", "person"), ("Le marteau sans maitre", "publication"), ("1955", "date"), ("total serialism", "method")],
     [("Le marteau sans maitre", "Pierre Boulez", "AUTHORED_BY")],
     "which 1955 chamber work became the showcase for postwar total serialism",
     "total serialism chamber rhythm dynamics timbre premiere year"),
    # --- 50 ---
    ("Alvar Aalto's Paimio Sanatorium, completed in 1933, integrates furniture, lighting, and building fabric into a single humane therapeutic environment.", "reference", "knowledge", False,
     [("Alvar Aalto", "person"), ("Paimio Sanatorium", "publication"), ("1933", "date")],
     [("Paimio Sanatorium", "Alvar Aalto", "AUTHORED_BY")],
     "which Finnish tuberculosis sanatorium unified furniture and architecture as a healing environment",
     "Finnish modernism sanatorium total design therapeutic year"),
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
