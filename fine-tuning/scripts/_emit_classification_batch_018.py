"""One-off emitter for classification top-up batch-018 — contrastive_reference_fact mode, arts and humanities slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_018.tmp.jsonl with ids class-01701..01800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_018.tmp.jsonl"
ID_OFFSET = 1700
PAIR_OFFSET = 600

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text MUST contain a citable source (named work of arts/humanities criticism, named journal, author + year).
# fact_text MUST NOT contain a citation — it is the same underlying humanities claim without the source.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Greenberg on avant-garde and kitsch (visual art history / aesthetics)
    (
        "Clement Greenberg, 'Avant-Garde and Kitsch', Partisan Review 6 (1939) 34-49, argued that the historical avant-garde arose as a defence of high culture against the industrial production of kitsch.",
        "knowledge",
        "The twentieth-century avant-garde can be read as a response to the rise of industrially produced mass culture, with modernist art attempting to preserve the autonomy of aesthetic experience.",
        "knowledge",
    ),
    # 2. Barthes Mythologies (cultural studies / semiotics)
    (
        "Roland Barthes, Mythologies (Seuil, 1957), analyzed everyday bourgeois culture — wrestling, steak and chips, the new Citroen — as a second-order semiological system that naturalizes ideology.",
        "knowledge",
        "Everyday cultural objects and spectacles can operate as myths in a semiotic sense, encoding ideological meanings that their users experience as natural and self-evident.",
        "knowledge",
    ),
    # 3. Frye Anatomy of Criticism (literary criticism / theory)
    (
        "Northrop Frye, Anatomy of Criticism (Princeton University Press, 1957), proposed a systematic theory of modes, symbols, myths, and genres, arguing that literary criticism could be a coherent conceptual discipline.",
        "knowledge",
        "Works of literature can be classified within a structured system of modes and archetypes, allowing criticism to function as a coherent theoretical discipline rather than a series of isolated judgements.",
        "knowledge",
    ),
    # 4. Rosen The Classical Style (music history / theory)
    (
        "Charles Rosen, The Classical Style: Haydn, Mozart, Beethoven (Norton, 1971), argued that the late eighteenth-century classical style was defined by the dramatic articulation of tonal areas through sonata form.",
        "knowledge",
        "The late eighteenth-century classical style of Haydn, Mozart, and Beethoven is characterized by the dramatic articulation of tonal regions, with sonata form organizing large-scale harmonic tension and resolution.",
        "knowledge",
    ),
    # 5. Bordwell Narration in the Fiction Film (film studies)
    (
        "David Bordwell, Narration in the Fiction Film (University of Wisconsin Press, 1985), developed a constructivist theory of narration, distinguishing classical, art-cinema, historical-materialist, and parametric modes.",
        "knowledge",
        "Narrative cinema can be analyzed as a set of distinct modes of narration — classical Hollywood, European art cinema, Soviet historical-materialist, and parametric — each with its own stylistic norms.",
        "knowledge",
    ),
    # 6. Auerbach Mimesis (comparative literature / philology)
    (
        "Erich Auerbach, Mimesis: The Representation of Reality in Western Literature (Princeton University Press, 1953; German original 1946), traced the changing representation of reality from Homer and the Hebrew Bible to Woolf.",
        "knowledge",
        "The depiction of everyday reality in Western literature undergoes major shifts across history, from the external clarity of Homer to the fragmented interiority of twentieth-century modernist prose.",
        "knowledge",
    ),
    # 7. Krauss in October (visual art / grid)
    (
        "Rosalind Krauss, 'Grids', October 9 (1979) 50-64, argued that the grid functions as both a spatial and a mythic emblem of modernist art's ambition to be simultaneously anti-natural and self-contained.",
        "knowledge",
        "The grid is a recurring formal device in modernist visual art because it enacts the ambition of autonomy from nature while insisting on flatness and self-reference.",
        "knowledge",
    ),
    # 8. Panofsky iconology (art history)
    (
        "Erwin Panofsky, Studies in Iconology (Oxford University Press, 1939), distinguished pre-iconographic description, iconographic analysis, and iconological interpretation as three levels of meaning in visual art.",
        "knowledge",
        "The interpretation of a painting can be organized into three levels: identifying what is depicted, recognizing conventional themes, and uncovering the broader cultural meanings the image expresses.",
        "knowledge",
    ),
    # 9. Berger Ways of Seeing (visual culture / cultural studies)
    (
        "John Berger, Ways of Seeing (BBC / Penguin, 1972), argued that oil painting as a genre is structured to celebrate private property and that the female nude is typically constructed for a male spectator.",
        "knowledge",
        "Traditional European oil painting often frames its subjects in relation to ownership, and the female nude in particular is composed to address an implied male viewer rather than the depicted woman's own experience.",
        "knowledge",
    ),
    # 10. Benjamin mechanical reproduction (aesthetics / media theory)
    (
        "Walter Benjamin, 'The Work of Art in the Age of Mechanical Reproduction' (1935; Zeitschrift fuer Sozialforschung V, 1936), argued that photographic and cinematic reproduction destroys the aura of the original artwork.",
        "knowledge",
        "The reproduction of artworks through photography and film erodes the unique presence, or aura, that a single original object holds within a specific tradition and location.",
        "knowledge",
    ),
    # 11. Said Orientalism (postcolonial studies / comparative literature)
    (
        "Edward Said, Orientalism (Pantheon, 1978), argued that European scholarly and literary representations of the Middle East constituted a discourse that both enabled and legitimated imperial rule.",
        "knowledge",
        "European scholarly, literary, and artistic representations of the Middle East historically formed a coherent discourse that supported and justified colonial domination of those regions.",
        "knowledge",
    ),
    # 12. Spivak subaltern (postcolonial studies)
    (
        "Gayatri Chakravorty Spivak, 'Can the Subaltern Speak?', in Marxism and the Interpretation of Culture, ed. Nelson and Grossberg (University of Illinois Press, 1988), argued that the gendered colonial subaltern cannot be recovered through dominant epistemic frames.",
        "knowledge",
        "Women situated at the intersection of colonial rule and patriarchal structures are often rendered inaudible within the dominant archives and theoretical frameworks that purport to represent them.",
        "knowledge",
    ),
    # 13. Foucault discipline (cultural theory / history of ideas)
    (
        "Michel Foucault, Discipline and Punish (French ed. Gallimard, 1975; English ed. Pantheon, 1977), traced the historical shift from sovereign spectacle of punishment to disciplinary techniques of the modern prison.",
        "knowledge",
        "Modern Western societies shifted from public corporal punishment to disciplinary regimes of surveillance, classification, and timetable that train bodies and minds across schools, factories, and prisons.",
        "knowledge",
    ),
    # 14. Mulvey male gaze (film studies / feminist theory)
    (
        "Laura Mulvey, 'Visual Pleasure and Narrative Cinema', Screen 16 (1975) 6-18, argued that classical Hollywood cinema structures vision through an active male gaze and passive female image.",
        "knowledge",
        "Classical Hollywood cinema has typically organized point of view so that the act of looking is coded as masculine and active while women appear as the passive object of that gaze.",
        "knowledge",
    ),
    # 15. Bazin realism (film studies / aesthetics)
    (
        "Andre Bazin, 'The Ontology of the Photographic Image' (1945), collected in What Is Cinema? vol. 1 (University of California Press, 1967), argued that photography's indexical link to reality underwrites cinema's realist vocation.",
        "knowledge",
        "Because a photographic image is causally imprinted by light from the object photographed, cinema carries a distinctive commitment to reproducing the contingency and depth of the physical world.",
        "knowledge",
    ),
    # 16. Propp fairy tale morphology (folklore / structuralism)
    (
        "Vladimir Propp, Morphology of the Folktale (Russian original 1928; English trans. University of Texas Press, 1968), identified a fixed sequence of thirty-one narrative functions underlying the Russian wondertale.",
        "knowledge",
        "Russian wondertales can be analyzed as variations on a limited, ordered sequence of narrative functions such as departure, testing, and return, performed by a small set of character roles.",
        "knowledge",
    ),
    # 17. Bakhtin dialogism (literary theory)
    (
        "Mikhail Bakhtin, 'Discourse in the Novel', in The Dialogic Imagination, ed. Holquist (University of Texas Press, 1981), argued that the novel is defined by heteroglossia and the dialogic interplay of social voices.",
        "knowledge",
        "The novel as a genre is distinguished by its capacity to stage the interaction of many social voices and styles within a single work, rather than imposing a single authoritative discourse.",
        "knowledge",
    ),
    # 18. Jameson postmodernism (cultural studies)
    (
        "Fredric Jameson, 'Postmodernism, or, The Cultural Logic of Late Capitalism', New Left Review 146 (1984) 53-92, argued that postmodern culture is characterized by pastiche, depthlessness, and a weakening of historicity.",
        "knowledge",
        "Late twentieth-century culture increasingly relies on pastiche and stylistic quotation, often losing the sense of historical depth and critical distance associated with earlier modernism.",
        "knowledge",
    ),
    # 19. Rosenberg action painting (visual art history)
    (
        "Harold Rosenberg, 'The American Action Painters', ARTnews 51, no. 8 (1952) 22-23, 48-50, reframed Abstract Expressionist canvases as arenas in which the artist performs an existential act rather than producing pictures.",
        "knowledge",
        "Abstract Expressionist painters such as Pollock can be understood as treating the canvas less as a surface for pictorial representation and more as a stage for a recorded physical act of painting.",
        "knowledge",
    ),
    # 20. Fried absorption and theatricality (art history / aesthetics)
    (
        "Michael Fried, Absorption and Theatricality: Painting and Beholder in the Age of Diderot (University of California Press, 1980), argued that eighteenth-century French painting sought to deny the beholder's presence in order to re-establish pictorial absorption.",
        "knowledge",
        "Eighteenth-century French painting increasingly pursued the fiction of absorbed figures oblivious to the viewer, treating this denial of the beholder as a condition of serious pictorial art.",
        "knowledge",
    ),
    # 21. Pevsner modern architecture (architecture history)
    (
        "Nikolaus Pevsner, Pioneers of the Modern Movement from William Morris to Walter Gropius (Faber, 1936), narrated a teleological history of modern architecture culminating in the Bauhaus.",
        "knowledge",
        "An influential narrative of modern architecture presents its emergence as a development running from the Arts and Crafts movement through engineering advances to the Bauhaus under Gropius.",
        "knowledge",
    ),
    # 22. Venturi complexity (architecture theory)
    (
        "Robert Venturi, Complexity and Contradiction in Architecture (Museum of Modern Art, 1966), argued against the reductive purity of orthodox modernism in favour of an architecture of 'both-and' rather than 'either-or'.",
        "knowledge",
        "A major strand of late twentieth-century architectural thought rejected the purism of orthodox modernism and advocated buildings that embrace ambiguity, historical reference, and contradiction.",
        "knowledge",
    ),
    # 23. Jacobs urbanism (architecture / urban studies)
    (
        "Jane Jacobs, The Death and Life of Great American Cities (Random House, 1961), argued that vibrant urban life depends on dense, mixed-use neighbourhoods with short blocks, aged buildings, and street-level eyes.",
        "knowledge",
        "Lively and safe urban neighbourhoods tend to feature a mix of uses, short blocks, a range of building ages, and enough density to keep eyes on the street throughout the day.",
        "knowledge",
    ),
    # 24. Loos ornament and crime (design history / architecture)
    (
        "Adolf Loos, 'Ornament und Verbrechen' (lecture 1910; published in Les Cahiers d'aujourd'hui, 1913), argued that the cultural evolution of civilized peoples is marked by the removal of ornament from everyday objects.",
        "knowledge",
        "A central early-modernist argument held that the progress of design in industrial societies would be reflected in the elimination of unnecessary decoration from everyday objects and buildings.",
        "knowledge",
    ),
    # 25. Tosches / Gunther Schuller early jazz (music history)
    (
        "Gunther Schuller, Early Jazz: Its Roots and Musical Development (Oxford University Press, 1968), analyzed the musical innovations of Louis Armstrong and his contemporaries through detailed transcription and formal analysis.",
        "knowledge",
        "Louis Armstrong's recordings of the late 1920s introduced rhythmic and melodic innovations that transformed jazz from a collective ensemble style into a soloist-led art form.",
        "knowledge",
    ),
    # 26. McClary feminine endings (musicology / gender studies)
    (
        "Susan McClary, Feminine Endings: Music, Gender, and Sexuality (University of Minnesota Press, 1991), argued that Western tonal music encodes gendered narratives through cadential structures and thematic oppositions.",
        "knowledge",
        "Western tonal music since the seventeenth century often codes its thematic and cadential structures along gendered lines, associating stability with masculine and disruptive otherness with feminine themes.",
        "knowledge",
    ),
    # 27. Taruskin Stravinsky (musicology)
    (
        "Richard Taruskin, Stravinsky and the Russian Traditions (University of California Press, 1996), situated Stravinsky's neoprimitivist works in The Rite of Spring within Russian folk and liturgical sources.",
        "knowledge",
        "Stravinsky's early ballets, including The Rite of Spring, draw extensively on Russian folk melodies and ritual traditions, rather than being a break with tradition in favour of pure modernism.",
        "knowledge",
    ),
    # 28. Meyer emotion and meaning in music (music theory / aesthetics)
    (
        "Leonard B. Meyer, Emotion and Meaning in Music (University of Chicago Press, 1956), argued that musical affect arises from the confirmation and violation of learned stylistic expectations.",
        "knowledge",
        "Listeners experience musical emotion largely through the way a piece plays with their learned expectations, fulfilling or frustrating implications built up by stylistic conventions.",
        "knowledge",
    ),
    # 29. Lerdahl and Jackendoff generative theory (music theory)
    (
        "Fred Lerdahl and Ray Jackendoff, A Generative Theory of Tonal Music (MIT Press, 1983), proposed a formal grammar of grouping, metre, time-span reduction, and prolongational reduction for tonal music.",
        "knowledge",
        "The hierarchical structure of Western tonal music can be modelled by rule systems that segment pieces into groups, impose metrical structure, and derive tree-shaped reductions of pitch content.",
        "knowledge",
    ),
    # 30. Schenker tonal music (music theory)
    (
        "Heinrich Schenker, Der freie Satz (Universal Edition, 1935), presented the Ursatz and concept of structural levels as the foundation of his theory of tonal music.",
        "knowledge",
        "Tonal compositions of the common-practice era can be heard as elaborations of a small number of underlying voice-leading structures that prolong tonic-dominant-tonic motion across an entire work.",
        "knowledge",
    ),
    # 31. Eisenstein montage (film theory)
    (
        "Sergei Eisenstein, 'A Dialectic Approach to Film Form' (1929), collected in Film Form, trans. Leyda (Harcourt, 1949), theorized montage as the collision of conflicting shots to generate new meaning dialectically.",
        "knowledge",
        "A classical Soviet theory of montage treats film editing as the dialectical collision of shots, whose juxtaposition generates meanings not present in either shot alone.",
        "knowledge",
    ),
    # 32. Deleuze cinema (film philosophy)
    (
        "Gilles Deleuze, Cinema 2: The Time-Image (French ed. Minuit, 1985; English trans. University of Minnesota Press, 1989), argued that postwar European cinema produces direct presentations of time rather than sensorimotor action.",
        "knowledge",
        "Postwar European art cinema developed forms in which time is presented directly through duration and memory, rather than indirectly through goal-oriented action.",
        "knowledge",
    ),
    # 33. Casanova world republic of letters (comparative literature)
    (
        "Pascale Casanova, The World Republic of Letters (French ed. Seuil, 1999; English trans. Harvard University Press, 2004), described a stratified international literary space with dominant and peripheral centres of consecration.",
        "knowledge",
        "The global circulation of literature operates through a hierarchical system in which a few metropolitan cities act as dominant centres of consecration, while most national literatures occupy peripheral positions.",
        "knowledge",
    ),
    # 34. Moretti distant reading (literary studies / digital humanities)
    (
        "Franco Moretti, 'Conjectures on World Literature', New Left Review 1 (2000) 54-68, proposed 'distant reading' as a mode of literary analysis that treats systems rather than individual texts as primary objects.",
        "knowledge",
        "One response to the sheer scale of world literature is to replace close reading of individual canonical works with comparative study of large-scale patterns across genres, languages, and markets.",
        "knowledge",
    ),
    # 35. Venuti translator's invisibility (translation studies)
    (
        "Lawrence Venuti, The Translator's Invisibility: A History of Translation (Routledge, 1995), criticized Anglo-American norms of fluent, domesticating translation for rendering the translator invisible.",
        "knowledge",
        "The dominant English-language tradition of fluent, idiomatic translation tends to efface the translator's role and to assimilate foreign texts to target-language stylistic norms.",
        "knowledge",
    ),
    # 36. Toury descriptive translation studies (translation studies)
    (
        "Gideon Toury, Descriptive Translation Studies and Beyond (John Benjamins, 1995), argued that translations should be studied as facts of their target culture, governed by translational norms.",
        "knowledge",
        "Translations can be analyzed empirically as products shaped by the literary and social norms of the culture that receives them, rather than evaluated only against the source text.",
        "knowledge",
    ),
    # 37. Hall encoding decoding (cultural studies)
    (
        "Stuart Hall, 'Encoding/Decoding' (1973; published in Culture, Media, Language, Hutchinson, 1980), argued that audiences may adopt dominant, negotiated, or oppositional readings of a televisual message.",
        "knowledge",
        "A single televisual message does not uniquely determine its reception; audiences can accept its preferred meaning, modify it, or read it against the grain depending on their social position.",
        "knowledge",
    ),
    # 38. Williams structures of feeling (cultural studies)
    (
        "Raymond Williams, Marxism and Literature (Oxford University Press, 1977), developed the concept of 'structures of feeling' to capture emergent experiences not yet codified in dominant ideology.",
        "knowledge",
        "Cultures at any given moment contain emergent patterns of shared experience that have not yet hardened into explicit ideology, and literature often registers these structures of feeling first.",
        "knowledge",
    ),
    # 39. Adorno culture industry (aesthetics / critical theory)
    (
        "Theodor W. Adorno and Max Horkheimer, 'The Culture Industry: Enlightenment as Mass Deception', in Dialectic of Enlightenment (Querido, 1947), argued that industrially produced culture standardizes taste and blocks critical reflection.",
        "knowledge",
        "Industrially produced mass entertainment tends to standardize cultural products and the responses they elicit, working against the autonomous, critical reception associated with older notions of art.",
        "knowledge",
    ),
    # 40. Dewey art as experience (aesthetics)
    (
        "John Dewey, Art as Experience (Minton, Balch & Co., 1934), argued that aesthetic experience is continuous with ordinary experience intensified and unified, not a separate metaphysical realm.",
        "knowledge",
        "Aesthetic experience is not sealed off from the rest of life but arises when ordinary perceptual and practical activity is intensified, unified, and felt as a coherent whole.",
        "knowledge",
    ),
    # 41. Danto end of art (aesthetics / philosophy of art)
    (
        "Arthur C. Danto, 'The Artworld', Journal of Philosophy 61 (1964) 571-584, argued that something becomes an artwork only against a theoretical atmosphere and history of art — the artworld.",
        "knowledge",
        "Whether a given object counts as a work of art depends not on its perceptible properties alone but on its position within a historically situated network of theories, institutions, and practices.",
        "knowledge",
    ),
    # 42. Kuhn history of science (history / humanities crossover — place in architecture history context via Pevsner? use Wölfflin)
    (
        "Heinrich Woelfflin, Principles of Art History (German ed. 1915; English trans. Dover, 1932), proposed five polar pairs — linear vs painterly, plane vs recession, closed vs open form, multiplicity vs unity, absolute vs relative clarity — to characterize the shift from Renaissance to Baroque.",
        "knowledge",
        "The stylistic shift from Renaissance to Baroque visual art can be described through a series of formal polarities contrasting linear clarity and stable composition with painterly fluidity and dynamic recession.",
        "knowledge",
    ),
    # 43. PMLA canonical essay — Sedgwick (literary criticism / queer theory)
    (
        "Eve Kosofsky Sedgwick, Epistemology of the Closet (University of California Press, 1990), argued that much of modern Western thought is structured by a crisis of homo/heterosexual definition since the late nineteenth century.",
        "knowledge",
        "A wide range of modern Western categories — including those in literature, law, and psychology — have been shaped by the unstable opposition between homosexual and heterosexual definitions that crystallized in the late nineteenth century.",
        "knowledge",
    ),
    # 44. Critical Inquiry — Mitchell pictorial turn (visual culture)
    (
        "W. J. T. Mitchell, 'The Pictorial Turn', Picture Theory (University of Chicago Press, 1994), argued that late twentieth-century thought had undergone a shift from the linguistic turn to a renewed interest in images and visuality.",
        "knowledge",
        "Late twentieth-century humanistic inquiry increasingly turned from language-centred models of meaning toward the study of images, visuality, and their role in structuring knowledge and power.",
        "knowledge",
    ),
    # 45. The Musical Quarterly — Kerman (musicology)
    (
        "Joseph Kerman, 'How We Got into Analysis, and How to Get Out', Critical Inquiry 7 (1980) 311-331, argued that Anglo-American musicology had over-invested in positivist analysis at the expense of critical and hermeneutic engagement.",
        "knowledge",
        "Late twentieth-century musicology was criticized for focusing too narrowly on formal and analytic description of scores at the expense of interpretive, historical, and critical engagement with music.",
        "knowledge",
    ),
    # 46. Design history Papanek (design history / ethics)
    (
        "Victor Papanek, Design for the Real World: Human Ecology and Social Change (Pantheon, 1971), argued that industrial design had become complicit in producing wasteful, socially harmful products and should be reoriented toward real human and ecological needs.",
        "knowledge",
        "A long-running strand of design thought holds that industrial design has often served consumer markets in wasteful and ecologically damaging ways and should be refocused on genuine human and environmental needs.",
        "knowledge",
    ),
    # 47. Forty Words and Buildings (architecture history / theory)
    (
        "Adrian Forty, Words and Buildings: A Vocabulary of Modern Architecture (Thames & Hudson, 2000), traced the historical transformation of key terms such as 'space', 'form', 'function', 'design', and 'structure' within modern architectural discourse.",
        "knowledge",
        "Core vocabulary of modern architecture such as 'space', 'form', and 'function' carries a layered history in which each term's meaning has shifted substantially since the nineteenth century.",
        "knowledge",
    ),
    # 48. Gombrich Art and Illusion (art history / perception)
    (
        "E. H. Gombrich, Art and Illusion (Bollingen / Princeton University Press, 1960), argued that pictorial representation develops through schemata and correction, with artists always mediating perception through inherited conventions.",
        "knowledge",
        "Pictorial representation is never a direct copy of nature but always proceeds through inherited schemata that artists modify, so every era's 'realism' is conditioned by conventions of depiction.",
        "knowledge",
    ),
    # 49. Steiner After Babel (translation studies / comparative literature)
    (
        "George Steiner, After Babel: Aspects of Language and Translation (Oxford University Press, 1975), argued that understanding even within a single language is a form of translation, and that translation is a fourfold hermeneutic movement.",
        "knowledge",
        "Understanding any utterance involves an act of translation, and translation between languages can be analyzed as a hermeneutic process of trust, aggression, incorporation, and restitution.",
        "knowledge",
    ),
    # 50. Wimsatt and Beardsley intentional fallacy (literary criticism / aesthetics)
    (
        "W. K. Wimsatt and Monroe Beardsley, 'The Intentional Fallacy', Sewanee Review 54 (1946) 468-488, argued that the author's intention is neither available nor desirable as a standard for judging the success of a literary work.",
        "knowledge",
        "One influential position in twentieth-century literary criticism holds that the meaning and value of a literary work should be assessed from the text itself rather than from claims about the author's private intentions.",
        "knowledge",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, ref_domain, fact_text, fact_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            fact_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({
                "id": ref_id,
                "domain": ref_domain,
                "text": ref_text,
                "memory_type": "reference",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "id": fact_id,
                "domain": fact_domain,
                "text": fact_text,
                "memory_type": "fact",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
