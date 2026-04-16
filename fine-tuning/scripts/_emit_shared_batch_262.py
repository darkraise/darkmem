"""One-off emitter for shared-base batch-262 — personal domain (chess: openings, endgames, tactics, engines, platforms, players, ratings, tournaments).

Writes 50 rows to data/v2/shared/batch_262.tmp.jsonl with ids shared-13051..13100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_262.tmp.jsonl"
ID_OFFSET = 13050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched my main opening as White from the Italian Game to the Ruy Lopez; the Italian felt too symmetrical at club level and the Ruy Lopez gave me a richer middlegame to study.", "decision", "personal", False,
     [("Italian Game", "concept"), ("Ruy Lopez", "concept")],
     [("Ruy Lopez", "Italian Game", "REPLACES")],
     "which king-pawn opening did I move to after dropping the symmetrical Italian at club level",
     "ruy lopez italian game white opening swap club middlegame"),
    # --- 2 ---
    ("After a rough month against 1.e4 e5, I decided to answer it with the Petrov instead of the Berlin Defense because the pawn structures suit my calculation style better.", "decision", "personal", False,
     [("Petrov", "concept"), ("Berlin Defense", "concept")],
     [("Petrov", "Berlin Defense", "PREFERS")],
     "which symmetrical king-pawn reply did I pick over the Berlin after struggling with 1 e4 e5",
     "petrov berlin defense black reply e4 e5 structure calculation"),
    # --- 3 ---
    ("My anti-Sicilian repertoire runs the Open Sicilian against the Sicilian Najdorf and the Sicilian Dragon, switches to a Rossolimo against 2.Nc6, and skips the Sicilian Sveshnikov theory maze entirely with 3.Bb5.", "architecture", "personal", False,
     [("Open Sicilian", "concept"), ("Sicilian Najdorf", "concept"), ("Sicilian Dragon", "concept"), ("Sicilian Sveshnikov", "concept"), ("Rossolimo", "concept")],
     [("Rossolimo", "Sicilian Sveshnikov", "REPLACES")],
     "how does my anti-Sicilian scheme split between mainlines and sidelines depending on Black's second move",
     "anti sicilian repertoire najdorf dragon sveshnikov rossolimo bb5"),
    # --- 4 ---
    ("Dropped the King's Gambit from my blitz rotation after a bad run on Lichess; the positions were fun but the engine eval kept punishing the exposed king once opponents booked up.", "decision", "personal", False,
     [("King's Gambit", "concept"), ("Lichess", "organization")],
     [("King's Gambit", "Lichess", "APPLIES_TO")],
     "which romantic gambit did I pull from my blitz rotation after Lichess opponents started booking up on it",
     "kings gambit blitz lichess drop romantic engine eval booked"),
    # --- 5 ---
    ("Against 1.d4, I play the Grünfeld as my main and the King's Indian as a surprise weapon; the Nimzo-Indian sits in the files as a backup if my opponent allows 3.Nc3.", "architecture", "personal", False,
     [("Grünfeld", "concept"), ("King's Indian", "concept"), ("Nimzo-Indian", "concept")],
     [("King's Indian", "Grünfeld", "RELATED_TO"), ("Nimzo-Indian", "Grünfeld", "RELATED_TO")],
     "how does my 1 d4 repertoire layer a main, a surprise weapon, and a backup depending on White's third move",
     "grunfeld kings indian nimzo d4 repertoire main surprise backup"),
    # --- 6 ---
    ("Picked up the Caro-Kann over the French Defense after realising I kept misplaying the locked pawn structures the French drops you into on move five.", "decision", "personal", False,
     [("Caro-Kann", "concept"), ("French Defense", "concept")],
     [("Caro-Kann", "French Defense", "PREFERS")],
     "which solid Black reply to 1 e4 replaced the French in my repertoire and why",
     "caro kann french defense e4 black structure locked pawn move five"),
    # --- 7 ---
    ("Studied the Lucena position until I could reproduce the bridge-building technique from any side of the board; the whole endgame clicked once I internalised the rook-lift.", "milestone", "personal", False,
     [("Lucena position", "concept"), ("bridge-building", "method"), ("rook-lift", "method")],
     [("bridge-building", "Lucena position", "APPLIES_TO"), ("rook-lift", "Lucena position", "APPLIES_TO")],
     "which winning rook-endgame idea did I drill until I could reproduce it from either side of the board",
     "lucena bridge building rook lift endgame drill winning technique"),
    # --- 8 ---
    ("Finally understood the Philidor position defensively; holding a third-rank rook and waiting for the pawn to commit is the difference between a draw and a lost rook endgame.", "milestone", "personal", False,
     [("Philidor position", "concept"), ("rook endgame", "concept")],
     [("Philidor position", "rook endgame", "APPLIES_TO")],
     "which defensive rook-endgame setup did I finally internalise to draw instead of drift into a loss",
     "philidor third rank rook endgame draw defensive wait pawn commit"),
    # --- 9 ---
    ("Added the Vancura defense to my drawing toolkit against rook plus a-pawn versus rook; sidestepping the wrong-side problem with a lateral rook saved me half a point last weekend.", "milestone", "personal", False,
     [("Vancura defense", "concept"), ("rook", "concept"), ("a-pawn", "concept")],
     [("Vancura defense", "a-pawn", "APPLIES_TO")],
     "which lateral-rook drawing idea against a rook-and-a-pawn endgame did I bank half a point with last weekend",
     "vancura defense rook a pawn endgame draw lateral half point"),
    # --- 10. noise ---
    ("The kettle at the club makes a high whistle every third boil and nobody has descaled it since March.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Drilled K+P vs K with both the key-square method and the opposition rule; the rook-pawn exception still trips me up on a 1.e tempo mistake.", "problem", "personal", False,
     [("K+P vs K", "concept"), ("key-square", "method"), ("opposition", "method"), ("rook-pawn", "concept")],
     [("key-square", "K+P vs K", "APPLIES_TO"), ("opposition", "K+P vs K", "APPLIES_TO")],
     "which basic pawn endgame still catches me on tempo despite drilling key squares and opposition",
     "kpk key square opposition rook pawn endgame drill tempo"),
    # --- 12 ---
    ("The Réti endgame study is the position that finally taught me kings travel on diagonals for counting purposes; the double-threat geometry is elegant even on the tenth replay.", "fact", "personal", False,
     [("Réti endgame study", "publication"), ("kings", "concept"), ("diagonal", "concept")],
     [("kings", "diagonal", "RELATED_TO")],
     "which famous study taught me the counting geometry of king moves on diagonals",
     "reti endgame study king diagonal counting geometry double threat"),
    # --- 13 ---
    ("The fork, the pin, and the skewer are drilled nightly on ChessTempo at 5-minute time control; the double attack motif lives in my muscle memory now and I see it on move two in blitz.", "fact", "personal", False,
     [("fork", "concept"), ("pin", "concept"), ("skewer", "concept"), ("ChessTempo", "organization"), ("double attack", "concept")],
     [("ChessTempo", "double attack", "APPLIES_TO")],
     "which tactics platform do I drill the basic motifs on nightly and at what time control",
     "fork pin skewer chesstempo double attack drill nightly 5 minute"),
    # --- 14 ---
    ("I prefer Lichess over Chess.com for analysis because the free engine, free studies, and open source database win every comparison round for me.", "preference", "personal", False,
     [("Lichess", "organization"), ("Chess.com", "organization")],
     [("Lichess", "Chess.com", "PREFERS")],
     "which study platform do I prefer and which three free features drive the choice",
     "lichess chess com prefer analysis engine study open source"),
    # --- 15 ---
    ("Picked Chessable for opening spaced repetition over ChessBase; the MoveTrainer keeps me honest on recall and ChessBase stays as my PGN archive and classical database tool.", "decision", "personal", False,
     [("Chessable", "organization"), ("ChessBase", "organization"), ("MoveTrainer", "tool"), ("PGN", "concept")],
     [("Chessable", "ChessBase", "PREFERS")],
     "which platform handles my opening spaced repetition versus which one stays as a PGN archive",
     "chessable chessbase movetrainer pgn repetition opening archive"),
    # --- 16 ---
    ("Running Stockfish 17 locally for deep analysis; the NNUE weights ship fast enough on my laptop that 30 ply on a quiet middlegame takes under a minute.", "fact", "personal", False,
     [("Stockfish 17", "tool"), ("NNUE", "method"), ("laptop", "platform")],
     [("Stockfish 17", "NNUE", "USES")],
     "which top engine and neural evaluation do I run on my laptop for deep home analysis",
     "stockfish 17 nnue laptop deep analysis ply middlegame minute"),
    # --- 17 ---
    ("For style contrast I keep a Leela Chess Zero net on disk; Leela's positional picks disagree with Stockfish just often enough to catch plans a classical engine would miss.", "reference", "personal", False,
     [("Leela Chess Zero", "tool"), ("Stockfish", "tool")],
     [("Leela Chess Zero", "Stockfish", "CONTRADICTS")],
     "which neural engine do I keep around to second-guess Stockfish's positional reads",
     "leela chess zero stockfish neural positional disagreement plan"),
    # --- 18 ---
    ("AlphaZero's 2017 games are on my study list as the canonical reference for long-term piece activity over material; the sacrificial h-pawn pushes changed how I value prophylaxis.", "reference", "personal", False,
     [("AlphaZero", "tool"), ("prophylaxis", "concept"), ("h-pawn", "concept")],
     [("AlphaZero", "prophylaxis", "APPLIES_TO")],
     "which landmark engine's games reshaped how I weigh long-term activity against material",
     "alphazero 2017 games activity material h pawn prophylaxis study"),
    # --- 19 ---
    ("Noted Komodo Dragon and Berserk as the two engines I still want to test on endgame tablebases; they trade top-five spots with Stockfish depending on the time control.", "reference", "personal", False,
     [("Komodo Dragon", "tool"), ("Berserk", "tool"), ("Stockfish", "tool")],
     [("Komodo Dragon", "Stockfish", "RELATED_TO"), ("Berserk", "Stockfish", "RELATED_TO")],
     "which two challenger engines sit on my to-test list against Stockfish on endgame tablebases",
     "komodo dragon berserk stockfish endgame tablebase test challenger"),
    # --- 20 ---
    ("Keeping the Obsidian engine in a sandbox folder for now; it's the dark-horse that's been climbing TCEC standings and I want a clean comparison against Stockfish 17 before moving it to my main rig.", "reference", "personal", False,
     [("Obsidian", "tool"), ("TCEC", "event"), ("Stockfish 17", "tool")],
     [("Obsidian", "TCEC", "APPLIES_TO"), ("Obsidian", "Stockfish 17", "RELATED_TO")],
     "which rising engine am I sandboxing before it earns a spot against Stockfish 17 on my main rig",
     "obsidian tcec engine sandbox stockfish 17 rig compare climb"),
    # --- 21 ---
    ("Houdini sits in my archive as a retired champion; the 2013-2016 era of Houdini versus Stockfish match analysis still holds up for manual review of endgame conversion technique.", "architecture", "personal", False,
     [("Houdini", "tool"), ("Stockfish", "tool")],
     [("Houdini", "Stockfish", "RELATED_TO")],
     "which retired champion engine do I still mine for manual endgame conversion study",
     "houdini stockfish archive endgame conversion retired champion match"),
    # --- 22 ---
    ("The London System entered my White repertoire as the quiet-week fallback; when I'm tired, 1.d4 Nf6 2.Bf4 lets me play on autopilot and still reach move 20 with a pulse.", "decision", "personal", False,
     [("London System", "concept")],
     [],
     "which solid White system is my low-energy fallback when I need to reach move 20 on autopilot",
     "london system white quiet repertoire fallback low energy move 20"),
    # --- 23 ---
    ("Studying the Catalan seriously this month; the fianchetto plus isolated queen's-pawn middlegames are the positional school I want to grow into beyond tactics-first play.", "decision", "personal", False,
     [("Catalan", "concept"), ("fianchetto", "concept"), ("isolated queen's-pawn", "concept")],
     [("fianchetto", "Catalan", "APPLIES_TO"), ("isolated queen's-pawn", "Catalan", "APPLIES_TO")],
     "which positional opening school am I aiming to internalise beyond my tactics-first habits",
     "catalan fianchetto isolated queens pawn middlegame positional study"),
    # --- 24 ---
    ("The Queen's Gambit Declined is my rock-solid answer when I face a 2000-plus player; the Slav is the backup when I want an earlier piece trade and a cleaner endgame.", "architecture", "personal", False,
     [("Queen's Gambit Declined", "concept"), ("Slav", "concept")],
     [("Slav", "Queen's Gambit Declined", "RELATED_TO")],
     "which two 1 d4 d5 replies split between rock-solid for strong opponents and cleaner endgame",
     "queens gambit declined slav 1 d4 d5 rock solid endgame backup"),
    # --- 25 ---
    ("Adopted the English Opening on the third board at our team match; 1.c4 gave me a flexible transposition tree and dodged the theoretical Sicilian lines I hadn't prepped for.", "milestone", "personal", False,
     [("English Opening", "concept"), ("Sicilian", "concept")],
     [("English Opening", "Sicilian", "REPLACES")],
     "which flank opening did I pick up to dodge prep-heavy Sicilian lines at the team match",
     "english opening c4 flank team match sicilian dodge transposition"),
    # --- 26 ---
    ("The Reti and Bird's Opening are in my surprise-weapon drawer; once a season each, mostly to rattle juniors who only prep against 1.e4 and 1.d4.", "preference", "personal", False,
     [("Reti", "concept"), ("Bird's Opening", "concept")],
     [("Reti", "Bird's Opening", "RELATED_TO")],
     "which two flank surprise weapons do I reserve for juniors who only prep against king and queen pawn",
     "reti birds opening surprise weapon juniors flank once season"),
    # --- 27 ---
    ("Magnus Carlsen's endgame grind against Fabiano Caruana in 2018 is the model I keep replaying; the way Magnus converts a nothing-position into a win is its own short course.", "reference", "personal", False,
     [("Magnus Carlsen", "person"), ("Fabiano Caruana", "person")],
     [("Magnus Carlsen", "Fabiano Caruana", "RELATED_TO")],
     "which 2018 championship grind do I keep on replay as an endgame conversion masterclass",
     "magnus carlsen fabiano caruana 2018 endgame grind nothing conversion"),
    # --- 28 ---
    ("Hikaru Nakamura's speed-chess stream is where I pick up practical blitz ideas; the move-order tricks and the way he handles Zwischenzug attempts are worth the screen time.", "fact", "personal", False,
     [("Hikaru Nakamura", "person"), ("Zwischenzug", "concept")],
     [("Hikaru Nakamura", "Zwischenzug", "APPLIES_TO")],
     "which GM's stream is my practical blitz school and which in-between-move concept do I pick up there",
     "hikaru nakamura speed chess blitz stream zwischenzug move order"),
    # --- 29 ---
    ("Ding Liren's 2023 championship run is the emotional model for me; the way he came back from mid-match collapse against Ian Nepomniachtchi is the kind of tilt-recovery I want to learn.", "milestone", "personal", False,
     [("Ding Liren", "person"), ("Ian Nepomniachtchi", "person")],
     [("Ding Liren", "Ian Nepomniachtchi", "RELATED_TO")],
     "which 2023 championship comeback is my template for tilt-recovery in a long match",
     "ding liren 2023 championship tilt recovery ian nepomniachtchi comeback"),
    # --- 30 ---
    ("Gukesh D winning the Candidates Tournament reset my sense of what a teenager can do at the top; his calm clock management under pressure is what I'm trying to borrow.", "milestone", "personal", False,
     [("Gukesh D", "person"), ("Candidates Tournament", "event")],
     [("Gukesh D", "Candidates Tournament", "RELATED_TO")],
     "which teenage Candidates winner's clock-management habit am I deliberately trying to borrow",
     "gukesh d candidates tournament teenage clock management calm"),
    # --- 31 ---
    ("Bobby Fischer's My 60 Memorable Games is still the single best book I own; the annotations teach calculation discipline better than any modern engine-first collection.", "decision", "personal", False,
     [("Bobby Fischer", "person"), ("My 60 Memorable Games", "publication")],
     [("My 60 Memorable Games", "Bobby Fischer", "AUTHORED_BY")],
     "which classic annotated game collection still outranks engine-first modern books on my shelf",
     "bobby fischer 60 memorable games annotation calculation discipline"),
    # --- 32 ---
    ("Watching Garry Kasparov's attack on Vishy Anand in the 1995 match gave me a feel for initiative that no engine line can replicate; the pawn storm on move 19 still stuns me.", "fact", "personal", False,
     [("Garry Kasparov", "person"), ("Vishy Anand", "person")],
     [("Garry Kasparov", "Vishy Anand", "RELATED_TO")],
     "which 1995 match attack taught me the feel of initiative better than any engine line",
     "garry kasparov vishy anand 1995 match attack initiative pawn storm"),
    # --- 33 ---
    ("Mikhail Tal's sacrificial style is where I go when my play gets too dry; a session of Tal games loosens the calculation and reminds me that engine eval is a guide not a god.", "preference", "personal", False,
     [("Mikhail Tal", "person"), ("sacrificial style", "concept")],
     [("Mikhail Tal", "sacrificial style", "APPLIES_TO")],
     "whose sacrificial style do I revisit when my own play gets too dry",
     "mikhail tal sacrificial style dry calculation engine eval guide"),
    # --- 34 ---
    ("Capablanca's endgame technique is the textbook I study before every long tournament; José Raúl Capablanca makes the simplification look obvious and my move selection benefits the next day.", "reference", "personal", False,
     [("Capablanca", "person"), ("José Raúl Capablanca", "person"), ("simplification", "concept")],
     [("José Raúl Capablanca", "simplification", "APPLIES_TO")],
     "whose endgame technique do I revisit before every long classical tournament",
     "capablanca jose raul endgame technique simplification tournament prep"),
    # --- 35 ---
    ("My FIDE rating crossed 1800 at the regional open last month; the goal now is to push past 1900 before the next Candidates cycle begins in earnest.", "milestone", "personal", False,
     [("FIDE", "organization"), ("regional open", "event")],
     [("regional open", "FIDE", "APPLIES_TO")],
     "which rating milestone did I just cross and what number is next on my list before the Candidates cycle",
     "fide rating 1800 1900 regional open candidates cycle milestone"),
    # --- 36 ---
    ("My Lichess Glicko is a honest 200 points above my FIDE Elo; the platform inflation is real, but the rating is still a useful progress dial on the blitz pool.", "fact", "personal", False,
     [("Lichess", "organization"), ("Glicko", "method"), ("FIDE", "organization"), ("Elo", "method")],
     [("Lichess", "Glicko", "USES"), ("FIDE", "Elo", "USES")],
     "how does my Lichess Glicko compare to my FIDE Elo and what does that gap tell me",
     "lichess glicko fide elo inflation blitz pool progress dial"),
    # --- 37 ---
    ("Analysed my last ten losses with Stockfish 17 and found four were back-rank oversights; added a back-rank puzzle set on Lichess to my daily 15-minute warmup.", "problem", "personal", False,
     [("Stockfish 17", "tool"), ("back-rank", "concept"), ("Lichess", "organization")],
     [("Stockfish 17", "back-rank", "APPLIES_TO")],
     "which tactic class showed up four times in my last ten losses and what drill did I add to counter it",
     "stockfish 17 back rank oversight lichess puzzle 15 minute warmup"),
    # --- 38 ---
    ("Zugzwang still bites me in king-and-pawn endgames; I tagged a ten-puzzle set specifically on zugzwang motifs and assigned it to Tuesday mornings so the pattern lands for real.", "architecture", "personal", False,
     [("Zugzwang", "concept"), ("king-and-pawn", "concept")],
     [("Zugzwang", "king-and-pawn", "APPLIES_TO")],
     "which endgame motif keeps biting me and how did I schedule the fix into my week",
     "zugzwang king pawn endgame tuesday puzzle ten set schedule"),
    # --- 39 ---
    ("Added a tactics filter for the discovered check on ChessTempo; seeing twenty of them in a row reveals the recurring geometry where the uncovering piece is a bishop on the long diagonal.", "fact", "personal", False,
     [("discovered check", "concept"), ("ChessTempo", "organization"), ("bishop", "concept")],
     [],
     "which tactics filter revealed that most discovered-check motifs uncover a bishop on the long diagonal for me",
     "discovered check chesstempo bishop long diagonal filter geometry"),
    # --- 40 ---
    ("Joined our city's weekly rapid over-the-board evening; sitting across a human with a ticking clock is the single best antidote to the online-blitz flag-fest habits I'd picked up.", "decision", "personal", False,
     [("city", "place"), ("rapid", "concept")],
     [],
     "which weekly in-person format did I join to reset the flag-fest habits from online blitz",
     "city rapid over the board weekly blitz flag online antidote"),
    # --- 41 ---
    ("Signed up for the next FIDE-rated weekend swiss in November; the goal is three wins against titled players to chase a Candidate Master norm before the year ends.", "decision", "personal", False,
     [("FIDE", "organization"), ("swiss", "event"), ("Candidate Master", "concept"), ("November", "date")],
     [("swiss", "FIDE", "APPLIES_TO"), ("swiss", "November", "HAPPENED_ON")],
     "which FIDE-rated format am I entering in November and which title norm am I chasing",
     "fide rated swiss november candidate master norm titled player win"),
    # --- 42 ---
    ("Prophylaxis is my study focus for the next quarter; reading Dvoretsky and then replaying Petrosian games feels like the shortest path from tactical to positional maturity at my level.", "decision", "personal", False,
     [("Prophylaxis", "concept"), ("Dvoretsky", "person"), ("Petrosian", "person")],
     [("Dvoretsky", "Prophylaxis", "APPLIES_TO"), ("Petrosian", "Prophylaxis", "APPLIES_TO")],
     "which strategic theme pairs which author study with which player's games on my quarter plan",
     "prophylaxis dvoretsky petrosian study quarter positional maturity plan"),
    # --- 43. noise ---
    ("The baker next to the chess club started a sourdough Friday and three of us now schedule rapid games around the pickup window.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Prefer studying in the morning with a coffee and a physical board over evening screen time; retention on opening lines is measurably better when I walk the pieces manually.", "preference", "personal", False,
     [("morning", "date"), ("coffee", "food"), ("physical board", "concept")],
     [("coffee", "morning", "HAPPENED_ON")],
     "which study habit gives me better opening retention compared to evening screen time",
     "morning coffee physical board study evening screen retention opening"),
    # --- 45 ---
    ("Classified my blunder log in a spreadsheet; skewer misses and pin blindness each account for about fifteen percent, so the weekly pattern drill leans on both for the rest of the quarter.", "architecture", "personal", False,
     [("blunder log", "concept"), ("skewer", "concept"), ("pin", "concept")],
     [("skewer", "blunder log", "APPLIES_TO"), ("pin", "blunder log", "APPLIES_TO")],
     "which two tactical blind spots dominate my spreadsheet blunder log and what drill do I lean on for them",
     "blunder log skewer pin spreadsheet fifteen percent drill quarter"),
    # --- 46 ---
    ("The Lichess Opening Explorer stays pinned as my primary prep view; its win-rate filter by rating band is the one feature that makes the move a real data decision rather than a hunch.", "architecture", "personal", False,
     [("Lichess Opening Explorer", "tool"), ("win-rate filter", "method"), ("rating band", "concept")],
     [],
     "which prep tool and filter turn my opening move choice from a hunch into a data-backed decision",
     "lichess opening explorer win rate rating band prep filter data"),
    # --- 47 ---
    ("Keep a short list of pet ideas per opening: a Najdorf English Attack gambit line, a Grünfeld exchange sideline, and a Caro-Kann Advance piece sacrifice; each one is annotated and ready to deploy once per month.", "architecture", "personal", False,
     [("Najdorf", "concept"), ("English Attack", "concept"), ("Grünfeld", "concept"), ("Caro-Kann", "concept"), ("Advance", "concept")],
     [],
     "how do I organise pet surprise ideas across my three main openings with a deployment cadence",
     "najdorf english attack grunfeld exchange caro kann advance pet list"),
    # --- 48 ---
    ("Built a little engine-assisted review loop: game ends, I annotate first without Stockfish 17, then diff my evaluations against the engine, and log the biggest assessment gap into a notebook.", "architecture", "personal", False,
     [("engine-assisted review", "method"), ("Stockfish 17", "tool"), ("notebook", "concept")],
     [("engine-assisted review", "Stockfish 17", "USES")],
     "which two-step post-game review loop do I run before comparing against Stockfish",
     "engine review stockfish 17 diff notebook annotation assessment gap"),
    # --- 49 ---
    ("Failed to convert a winning position against a 2100 last round because I missed a Zwischenzug defence; the lesson is to always burn thirty seconds before capturing when the board is loud.", "problem", "personal", False,
     [("Zwischenzug", "concept"), ("2100", "concept")],
     [],
     "which in-between-move defence did I miss against a 2100 and what time-use rule did I set afterwards",
     "zwischenzug 2100 winning position capture thirty seconds loud board"),
    # --- 50 ---
    ("Signed up for a Chessable course on the Giuoco Piano as my second White option behind the Ruy Lopez; the Scotch is now the third, to give me variety when opponents have seen my Spanish twice.", "decision", "personal", False,
     [("Chessable", "organization"), ("Giuoco Piano", "concept"), ("Ruy Lopez", "concept"), ("Scotch", "concept")],
     [("Giuoco Piano", "Ruy Lopez", "RELATED_TO")],
     "how does my White king-pawn repertoire layer a primary, secondary, and tertiary opening against 1 e4 e5",
     "chessable giuoco piano ruy lopez scotch white repertoire layer"),
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
