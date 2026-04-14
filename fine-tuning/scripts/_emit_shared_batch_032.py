"""One-off emitter for shared-base batch-032 — knowledge domain (linguistics / literature / literary criticism / translation studies).

Writes 50 rows to data/v2/shared/batch_032.tmp.jsonl with ids shared-01551..01600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_032.tmp.jsonl"
ID_OFFSET = 1550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Optimality Theory replaces rule-ordered derivations in phonology with ranked violable constraints evaluated in parallel.", "decision", "knowledge", False,
     [("Optimality Theory", "theory"), ("rule-ordered derivations", "method"), ("phonology", "field")],
     [("Optimality Theory", "rule-ordered derivations", "REPLACES")],
     "which phonological framework swapped serial rewriting for parallel constraint ranking",
     "OT Prince Smolensky constraint ranking parallel evaluation phonology"),
    # --- 2 ---
    ("Construction Grammar builds on Cognitive Linguistics by treating form-meaning pairings rather than atomic lexicon plus syntax as the basic unit.", "fact", "knowledge", False,
     [("Construction Grammar", "theory"), ("Cognitive Linguistics", "field"), ("form-meaning pairings", "concept")],
     [("Construction Grammar", "Cognitive Linguistics", "BUILDS_ON")],
     "which syntactic approach treats pairings of form and meaning as primitives",
     "Goldberg Fillmore construction pairing form meaning primitive"),
    # --- 3 ---
    ("Distributed Morphology, proposed by Halle and Marantz in 1993, splits word formation across syntax, morphology, and late lexical insertion.", "milestone", "knowledge", False,
     [("Distributed Morphology", "theory"), ("Halle", "person"), ("Marantz", "person"), ("1993", "date")],
     [],
     "when did the late-insertion morphology framework first appear",
     "DM late insertion vocabulary item architecture morphology year"),
    # --- 4 ---
    ("Proto-Indo-European is the reconstructed common ancestor of languages spanning from Icelandic to Bengali, inferred through the comparative method.", "fact", "knowledge", False,
     [("Proto-Indo-European", "language"), ("Icelandic", "language"), ("Bengali", "language"), ("comparative method", "method")],
     [],
     "which reconstructed ancestor links languages from the North Atlantic to South Asia",
     "PIE comparative reconstruction ancestor language family range"),
    # --- 5 ---
    ("Austronesian dispersal fanned out from Taiwan across Island Southeast Asia and the Pacific, reaching Madagascar and Rapa Nui by the early second millennium.", "fact", "knowledge", False,
     [("Austronesian dispersal", "event"), ("Taiwan", "place"), ("Madagascar", "place"), ("Rapa Nui", "place")],
     [],
     "which language expansion left relatives from Madagascar to Easter Island",
     "Austronesian Taiwan homeland canoe expansion Pacific Madagascar"),
    # --- 6 ---
    ("Sino-Tibetan groups Chinese with Tibeto-Burman languages, though internal subgrouping past those two branches remains contested.", "fact", "knowledge", False,
     [("Sino-Tibetan", "language"), ("Chinese", "language"), ("Tibeto-Burman", "language")],
     [],
     "which family ties Mandarin to Burmese and Tibetan",
     "Sino-Tibetan family internal subgrouping debate Chinese Tibeto-Burman"),
    # --- 7 ---
    ("Labov's 1962 NYC department-store study used the prestige variable /r/ across Saks, Macy's, and S. Klein to demonstrate class-stratified variation.", "milestone", "knowledge", False,
     [("Labov", "person"), ("1962", "date"), ("Saks", "organization"), ("Macy's", "organization"), ("/r/", "concept"), ("class-stratified variation", "finding")],
     [],
     "which early sociolinguistic survey used three New York stores to index class",
     "Labov department store rhotic New York prestige variable class"),
    # --- 8 ---
    ("Trudgill's Norwich study of 1974 formalised the observation that women lead in adopting prestige variants ahead of men.", "reference", "knowledge", False,
     [("Trudgill", "person"), ("Norwich", "place"), ("1974", "date")],
     [],
     "which British fieldwork documented gendered leading of prestige forms",
     "Trudgill Norwich gender prestige leading women sociolinguistics"),
    # --- 9 ---
    ("Endangered language revitalisation in Hawaiian built on the Punana Leo nest preschools founded in 1984 and later Kaiapuni immersion schools.", "milestone", "knowledge", False,
     [("Hawaiian", "language"), ("Punana Leo", "organization"), ("1984", "date"), ("Kaiapuni", "organization")],
     [],
     "which immersion model anchored the Hawaiian language recovery",
     "Hawaiian revitalisation nest immersion preschool Kaiapuni founding"),
    # --- 10. noise ---
    ("Let me grab the exact publication year from my shelf.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Joyce's Ulysses, published in Paris in 1922 by Shakespeare and Company, remained banned in the United States until the Woolsey decision of 1933.", "milestone", "knowledge", False,
     [("Joyce", "person"), ("Ulysses", "publication"), ("Paris", "place"), ("1922", "date"), ("Shakespeare and Company", "organization"), ("Woolsey decision", "event")],
     [("Ulysses", "Joyce", "AUTHORED_BY")],
     "when was the Irish modernist novel first published and when did the US unban it",
     "Ulysses Paris 1922 Shakespeare Company Woolsey obscenity ruling"),
    # --- 12 ---
    ("Proust's In Search of Lost Time appeared over fourteen years, with Swann's Way in 1913 and the posthumous Time Regained in 1927.", "reference", "knowledge", False,
     [("Proust", "person"), ("In Search of Lost Time", "publication"), ("Swann's Way", "publication"), ("1913", "date"), ("Time Regained", "publication"), ("1927", "date")],
     [("In Search of Lost Time", "Proust", "AUTHORED_BY")],
     "across which years did the French memory cycle reach readers",
     "Proust Recherche Swann Time Regained publication span years"),
    # --- 13 ---
    ("Morrison's Beloved won the Pulitzer Prize for Fiction in 1988 and cemented her place in the African-American literary canon.", "milestone", "knowledge", False,
     [("Morrison", "person"), ("Beloved", "publication"), ("Pulitzer Prize for Fiction", "event"), ("1988", "date")],
     [("Beloved", "Morrison", "AUTHORED_BY")],
     "which year did the novel about Sethe take the American fiction prize",
     "Morrison Beloved Pulitzer 1988 African American canon"),
    # --- 14 ---
    ("Dostoevsky's The Brothers Karamazov, serialised in The Russian Messenger from 1879 to 1880, closes with Alyosha's graveyard speech to the schoolboys.", "reference", "knowledge", False,
     [("Dostoevsky", "person"), ("The Brothers Karamazov", "publication"), ("The Russian Messenger", "publication"), ("1879", "date"), ("1880", "date")],
     [("The Brothers Karamazov", "Dostoevsky", "AUTHORED_BY")],
     "which journal serialised the last Dostoevsky novel and when",
     "Karamazov serialisation Russian Messenger 1879 1880 Dostoevsky"),
    # --- 15 ---
    ("Achebe's Things Fall Apart, published by Heinemann in 1958, opened the African Writers Series and answered European colonial fiction from within.", "milestone", "knowledge", False,
     [("Achebe", "person"), ("Things Fall Apart", "publication"), ("Heinemann", "organization"), ("1958", "date"), ("African Writers Series", "framework")],
     [("Things Fall Apart", "Achebe", "AUTHORED_BY")],
     "which novel launched the African Writers Series at Heinemann",
     "Achebe Things Fall Apart Heinemann 1958 African Writers Series"),
    # --- 16 ---
    ("Modernism in early twentieth-century fiction broke with Victorian realism through fragmentation, stream of consciousness, and mythic method.", "fact", "knowledge", False,
     [("Modernism", "field"), ("Victorian realism", "field"), ("stream of consciousness", "method"), ("mythic method", "method")],
     [("Modernism", "Victorian realism", "REPLACES")],
     "which movement broke with nineteenth-century realism via fragmented time and inner monologue",
     "modernism fragmentation stream consciousness mythic method break"),
    # --- 17 ---
    ("Magical realism as a Latin American literary label crystallised around Garcia Marquez's One Hundred Years of Solitude in 1967.", "milestone", "knowledge", False,
     [("Magical realism", "field"), ("Garcia Marquez", "person"), ("One Hundred Years of Solitude", "publication"), ("1967", "date")],
     [("One Hundred Years of Solitude", "Garcia Marquez", "AUTHORED_BY")],
     "which novel consolidated the magical realism label for Latin American fiction",
     "magical realism Macondo Garcia Marquez 1967 Latin American consolidation"),
    # --- 18 ---
    ("The Lost Generation gathered expatriate American writers in 1920s Paris around Gertrude Stein, Hemingway, and Fitzgerald.", "fact", "knowledge", False,
     [("Lost Generation", "field"), ("1920s", "date"), ("Paris", "place"), ("Gertrude Stein", "person"), ("Hemingway", "person"), ("Fitzgerald", "person")],
     [],
     "which interwar Paris circle grouped expatriate American novelists",
     "Lost Generation Paris expatriate Stein Hemingway Fitzgerald interwar"),
    # --- 19 ---
    ("The Beats emerged from late-1940s New York around Ginsberg, Kerouac, and Burroughs before consolidating in 1955 around the Six Gallery reading.", "milestone", "knowledge", False,
     [("Beats", "field"), ("Ginsberg", "person"), ("Kerouac", "person"), ("Burroughs", "person"), ("Six Gallery", "place"), ("1955", "date")],
     [],
     "which 1955 San Francisco reading crystallised the Beat movement",
     "Beat movement Six Gallery Howl reading 1955 Ginsberg Kerouac"),
    # --- 20 ---
    ("Postcolonial writing grew from anticolonial intellectual work and Said's Orientalism, published in 1978, which recast Western representation of the East.", "fact", "knowledge", False,
     [("Postcolonial writing", "field"), ("Said", "person"), ("Orientalism", "publication"), ("1978", "date")],
     [("Postcolonial writing", "Orientalism", "BUILDS_ON"), ("Orientalism", "Said", "AUTHORED_BY")],
     "which 1978 critical book seeded the postcolonial turn in the humanities",
     "Said Orientalism 1978 postcolonial turn Western representation critique"),
    # --- 21 ---
    ("Venuti's The Translator's Invisibility, published in 1995, made foreignisation a counterweight to Anglo-American domestication in literary translation.", "reference", "knowledge", False,
     [("Venuti", "person"), ("The Translator's Invisibility", "publication"), ("1995", "date"), ("foreignisation", "concept"), ("domestication", "concept")],
     [("The Translator's Invisibility", "Venuti", "AUTHORED_BY")],
     "which book argued translators should resist Anglo smoothing by leaving foreignness visible",
     "Venuti translator invisibility 1995 foreignisation domestication argument"),
    # --- 22 ---
    ("Skopos theory, developed by Vermeer in 1978, grounds translation choices in the target-text purpose rather than source fidelity.", "decision", "knowledge", False,
     [("Skopos theory", "theory"), ("Vermeer", "person"), ("1978", "date")],
     [],
     "which functionalist framework pegs translation choices to the target text's purpose",
     "skopos Vermeer functionalist purpose target text fidelity shift"),
    # --- 23 ---
    ("Pevear and Volokhonsky's Tolstoy translations replace Constance Garnett's smoothed Edwardian English with a closer-to-Russian idiom, sparking decades of reader debate.", "decision", "knowledge", False,
     [("Pevear", "person"), ("Volokhonsky", "person"), ("Tolstoy", "person"), ("Constance Garnett", "person")],
     [("Pevear", "Constance Garnett", "REPLACES")],
     "which translation duo took over from Garnett on the Russian classics",
     "Pevear Volokhonsky Tolstoy Garnett retranslation debate idiom"),
    # --- 24 ---
    ("The International Booker Prize split from the Man Booker in 2016 to award the year's best translated novel, paying the translator equally with the author.", "milestone", "knowledge", False,
     [("International Booker Prize", "event"), ("Man Booker", "event"), ("2016", "date")],
     [],
     "when did the UK prize for translated fiction split off and equalise the translator's share",
     "International Booker split 2016 translator equal share translated fiction"),
    # --- 25 ---
    ("The Goncourt Prize, awarded each November in Paris since 1903, carries outsized sales impact far beyond its symbolic ten-euro cheque.", "fact", "knowledge", False,
     [("Goncourt Prize", "event"), ("Paris", "place"), ("1903", "date"), ("November", "date")],
     [],
     "which November French literary prize moves sales despite a token cash amount",
     "Goncourt Paris November 1903 token prize sales impact French"),
    # --- 26 ---
    ("The Akutagawa Prize, given twice yearly in Japan since 1935, remains the chief gateway award for emerging literary fiction in Japanese.", "fact", "knowledge", False,
     [("Akutagawa Prize", "event"), ("Japan", "place"), ("1935", "date")],
     [],
     "which Japanese prize twice yearly marks the breakthrough of new literary authors",
     "Akutagawa Japan biannual 1935 emerging literary fiction gateway"),
    # --- 27 ---
    ("Prefers Pevear and Volokhonsky over Constance Garnett for teaching Tolstoy when closeness to Russian syntax matters more than Victorian readability.", "preference", "knowledge", False,
     [("Pevear and Volokhonsky", "person"), ("Constance Garnett", "person"), ("Tolstoy", "person")],
     [("Pevear and Volokhonsky", "Constance Garnett", "PREFERS")],
     "which Tolstoy translators win when teachers want Russian syntax preserved",
     "Pevear Volokhonsky preferred Garnett classroom syntax closeness Tolstoy"),
    # --- 28 ---
    ("Prefers foreignisation over domestication when translating poetry in order to keep source-culture markers visible to the target reader.", "preference", "knowledge", False,
     [("foreignisation", "concept"), ("domestication", "concept"), ("poetry", "concept")],
     [("foreignisation", "domestication", "PREFERS")],
     "which translation stance wins for poetry when cultural markers must survive",
     "foreignisation preferred domestication poetry translation markers visible"),
    # --- 29 ---
    ("The 2019 Nobel Prize in Literature controversy centred on Peter Handke's earlier defence of Slobodan Milosevic during the Yugoslav wars.", "problem", "knowledge", False,
     [("2019", "date"), ("Nobel Prize in Literature", "event"), ("Peter Handke", "person"), ("Slobodan Milosevic", "person"), ("Yugoslav wars", "event")],
     [],
     "which Nobel laureate's selection reopened debate over his Milosevic advocacy",
     "Handke Nobel 2019 Milosevic Yugoslav wars controversy literature"),
    # --- 30 ---
    ("Derrida's Of Grammatology, translated by Spivak in 1976, introduced Anglophone humanities readers to deconstruction and the critique of logocentrism.", "milestone", "knowledge", False,
     [("Derrida", "person"), ("Of Grammatology", "publication"), ("Spivak", "person"), ("1976", "date"), ("deconstruction", "method")],
     [("Of Grammatology", "Derrida", "AUTHORED_BY"), ("Of Grammatology", "Spivak", "RELATED_TO")],
     "which 1976 translation brought deconstruction into English-language humanities",
     "Derrida Grammatology Spivak 1976 deconstruction logocentrism English arrival"),
    # --- 31 ---
    ("New Criticism dominated mid-century Anglophone literary study by focusing close reading on the poem as self-contained verbal artifact.", "fact", "knowledge", False,
     [("New Criticism", "field"), ("close reading", "method")],
     [],
     "which Anglophone mid-century school made close reading of the self-contained text central",
     "New Criticism close reading verbal artifact mid-century Anglophone"),
    # --- 32 ---
    ("Structuralist narratology, built on Propp's 1928 morphology of folk tales, culminated in Genette's Narrative Discourse in 1972.", "reference", "knowledge", False,
     [("Structuralist narratology", "field"), ("Propp", "person"), ("1928", "date"), ("Genette", "person"), ("Narrative Discourse", "publication"), ("1972", "date")],
     [("Structuralist narratology", "Propp", "BUILDS_ON"), ("Narrative Discourse", "Genette", "AUTHORED_BY")],
     "which 1972 Genette volume crowned structuralist narrative theory",
     "Genette narrative discourse 1972 Propp morphology structuralist narratology"),
    # --- 33 ---
    ("Bakhtin's Dialogic Imagination, written in the 1930s and translated in 1981, introduced heteroglossia and dialogism into Anglophone literary theory.", "milestone", "knowledge", False,
     [("Bakhtin", "person"), ("Dialogic Imagination", "publication"), ("1930s", "date"), ("1981", "date"), ("heteroglossia", "concept"), ("dialogism", "concept")],
     [("Dialogic Imagination", "Bakhtin", "AUTHORED_BY")],
     "when did heteroglossia and dialogism enter English-language literary theory",
     "Bakhtin Dialogic Imagination 1981 heteroglossia dialogism English translation"),
    # --- 34. noise ---
    ("Hold on, let me check which translation I was actually quoting from.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Showalter's A Literature of Their Own, published in 1977, mapped a distinct tradition of British women novelists from the Brontes to Lessing.", "reference", "knowledge", False,
     [("Showalter", "person"), ("A Literature of Their Own", "publication"), ("1977", "date"), ("Brontes", "person"), ("Lessing", "person")],
     [("A Literature of Their Own", "Showalter", "AUTHORED_BY")],
     "which 1977 survey traced a continuous female British novel tradition",
     "feminist literary history Anglophone female canon survey mapping"),
    # --- 36 ---
    ("The Sapir-Whorf hypothesis claims that grammatical categories shape habitual thought, a strong reading now largely abandoned in linguistics.", "fact", "knowledge", False,
     [("Sapir-Whorf hypothesis", "claim"), ("grammatical categories", "concept"), ("linguistics", "field")],
     [],
     "which linguistic relativity claim held that grammar constrains thought",
     "Sapir Whorf linguistic relativity grammar thought strong abandoned"),
    # --- 37 ---
    ("Grimm's Law describes the systematic consonant shifts that separated Proto-Germanic from its Proto-Indo-European parent.", "fact", "knowledge", False,
     [("Grimm's Law", "theory"), ("Proto-Germanic", "language"), ("Proto-Indo-European", "language")],
     [],
     "which sound-change law defines the Germanic branch's split from PIE",
     "Grimm Law consonant shift Proto-Germanic PIE branch split"),
    # --- 38 ---
    ("Chomsky's Aspects of the Theory of Syntax, published in 1965, introduced the competence-performance distinction and deep structure to generative grammar.", "milestone", "knowledge", False,
     [("Chomsky", "person"), ("Aspects of the Theory of Syntax", "publication"), ("1965", "date"), ("competence-performance distinction", "concept"), ("deep structure", "concept")],
     [("Aspects of the Theory of Syntax", "Chomsky", "AUTHORED_BY")],
     "which 1965 Chomsky book introduced competence, performance, and deep structure",
     "mid sixties generative syntax monograph foundational distinctions"),
    # --- 39 ---
    ("The Minimalist Program replaces Government and Binding in generative syntax by paring the architecture to interface-driven economy conditions.", "decision", "knowledge", False,
     [("Minimalist Program", "theory"), ("Government and Binding", "theory"), ("generative syntax", "field")],
     [("Minimalist Program", "Government and Binding", "REPLACES")],
     "which Chomskyan syntax framework took over from GB in the 1990s",
     "nineties minimalism interface economy pared architecture"),
    # --- 40 ---
    ("Head-Driven Phrase Structure Grammar builds on Generalised Phrase Structure Grammar by enriching feature structures with typed unification.", "architecture", "knowledge", False,
     [("Head-Driven Phrase Structure Grammar", "theory"), ("Generalised Phrase Structure Grammar", "theory"), ("typed unification", "method")],
     [("Head-Driven Phrase Structure Grammar", "Generalised Phrase Structure Grammar", "BUILDS_ON")],
     "which unification-based grammar framework succeeded GPSG",
     "HPSG GPSG typed unification feature structure successor"),
    # --- 41 ---
    ("Gricean maxims underpin much pragmatic analysis of implicature, even when neo-Gricean and relevance-theoretic rivals contest their framing.", "fact", "knowledge", False,
     [("Gricean maxims", "theory"), ("pragmatic analysis", "field"), ("implicature", "concept")],
     [],
     "which conversational principles anchor most analyses of implicature",
     "Grice maxims cooperative principle implicature pragmatics framework"),
    # --- 42 ---
    ("The Hugo Awards controversy of 2015, driven by the Sad Puppies and Rabid Puppies slates, exposed fault lines in science fiction fandom over politics and inclusion.", "problem", "knowledge", False,
     [("Hugo Awards", "event"), ("2015", "date"), ("Sad Puppies", "organization"), ("Rabid Puppies", "organization")],
     [],
     "which 2015 slate-driven controversy split the science fiction Hugo voting community",
     "Hugo Awards 2015 Sad Puppies Rabid Puppies slate controversy fandom"),
    # --- 43 ---
    ("Borges's Ficciones, collected in 1944, anchored Latin American fantastic literature decades before the magical realism boom.", "reference", "knowledge", False,
     [("Borges", "person"), ("Ficciones", "publication"), ("1944", "date")],
     [("Ficciones", "Borges", "AUTHORED_BY")],
     "which 1944 Argentine story collection shaped the fantastic before the boom",
     "Borges Ficciones 1944 Argentine fantastic magical realism precursor"),
    # --- 44 ---
    ("Calvino's Invisible Cities, published in 1972, stages an imagined dialogue between Marco Polo and Kublai Khan across fifty-five prose-poem cities.", "reference", "knowledge", False,
     [("Calvino", "person"), ("Invisible Cities", "publication"), ("1972", "date"), ("Marco Polo", "person"), ("Kublai Khan", "person")],
     [("Invisible Cities", "Calvino", "AUTHORED_BY")],
     "which 1972 Calvino novel frames its cities as a Marco Polo dialogue",
     "Calvino Invisible Cities 1972 Marco Polo Kublai Khan prose poem"),
    # --- 45 ---
    ("Ngugi wa Thiong'o's Decolonising the Mind, published in 1986, argued for abandoning English in African literature in favour of indigenous languages.", "decision", "knowledge", False,
     [("Ngugi wa Thiong'o", "person"), ("Decolonising the Mind", "publication"), ("1986", "date"), ("English", "language")],
     [("Decolonising the Mind", "Ngugi wa Thiong'o", "AUTHORED_BY")],
     "which 1986 essay collection called for African writers to drop English",
     "Ngugi Decolonising Mind 1986 English indigenous African languages argument"),
    # --- 46 ---
    ("Endangered Ainu revitalisation in Hokkaido built on the 1997 Ainu Cultural Promotion Act and the 2019 recognition as an indigenous people of Japan.", "milestone", "knowledge", False,
     [("Ainu", "language"), ("Hokkaido", "place"), ("Ainu Cultural Promotion Act", "publication"), ("1997", "date"), ("2019", "date"), ("Japan", "place")],
     [],
     "which two legislative moments anchored Ainu language revitalisation in Japan",
     "Ainu Hokkaido 1997 Cultural Promotion Act 2019 indigenous recognition Japan"),
    # --- 47 ---
    ("Welsh revitalisation overtook earlier Irish approaches in percentage outcomes by pairing Bangor University research with statutory education since the 1993 Welsh Language Act.", "decision", "knowledge", False,
     [("Welsh", "language"), ("Irish", "language"), ("Bangor University", "organization"), ("Welsh Language Act", "publication"), ("1993", "date")],
     [("Welsh", "Irish", "IMPROVES_ON")],
     "which Celtic revitalisation outpaced its older Irish counterpart in uptake",
     "Welsh Irish revitalisation Bangor Welsh Language Act 1993 comparison"),
    # --- 48 ---
    ("Kafka's posthumous publication by Max Brod against the author's wishes shaped twentieth-century modernism by preserving The Trial, The Castle, and Amerika.", "milestone", "knowledge", False,
     [("Kafka", "person"), ("Max Brod", "person"), ("The Trial", "publication"), ("The Castle", "publication"), ("Amerika", "publication")],
     [("The Trial", "Kafka", "AUTHORED_BY"), ("The Castle", "Kafka", "AUTHORED_BY"), ("Amerika", "Kafka", "AUTHORED_BY")],
     "whose disregard of a dying author's burn instructions gave modernism three canonical novels",
     "Kafka Max Brod posthumous Trial Castle Amerika preservation modernism"),
    # --- 49 ---
    ("Spivak's Can the Subaltern Speak, first published in 1988, became the pivot essay of postcolonial theory after repeated revision through the 1990s.", "reference", "knowledge", False,
     [("Spivak", "person"), ("Can the Subaltern Speak", "publication"), ("1988", "date"), ("postcolonial theory", "field")],
     [("Can the Subaltern Speak", "Spivak", "AUTHORED_BY")],
     "which 1988 essay became the pivot text of postcolonial theory",
     "Spivak Can Subaltern Speak 1988 postcolonial theory pivot essay"),
    # --- 50 ---
    ("Corpus linguistics replaces introspective grammaticality judgements with frequency data drawn from the British National Corpus and comparable archives.", "decision", "knowledge", False,
     [("Corpus linguistics", "field"), ("introspective grammaticality judgements", "method"), ("British National Corpus", "tool")],
     [("Corpus linguistics", "introspective grammaticality judgements", "REPLACES")],
     "which approach swapped armchair judgements for BNC-style frequency evidence",
     "corpus linguistics British National Corpus frequency introspection replacement"),
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
