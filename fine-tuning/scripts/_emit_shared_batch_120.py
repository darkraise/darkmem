"""One-off emitter for shared-base batch-120 — personal domain (expat life, in-context language learning, cross-cultural experience slice).

Writes 50 rows to data/v2/shared/batch_120.tmp.jsonl with ids shared-05951..06000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_120.tmp.jsonl"
ID_OFFSET = 5950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("The Aufenthaltstitel renewal at Berlin's Ausländerbehörde on 2026-05-14 needs the Meldebescheinigung, the Arbeitsvertrag, and six months of bank statements.", "reference", "personal", False,
     [("Aufenthaltstitel", "concept"), ("Berlin", "place"), ("Ausländerbehörde", "organization"), ("2026-05-14", "date"), ("Meldebescheinigung", "concept"), ("Arbeitsvertrag", "concept")],
     [("Aufenthaltstitel", "Ausländerbehörde", "LOCATED_IN")],
     "what papers do I need for the German residence-permit renewal and when",
     "residence permit renewal Ausländerbehörde document checklist date bank statements"),
    # --- 2 ---
    ("Switched from Duolingo drills to ordering groceries entirely in German at the Rewe on Kastanienallee; the cashier's small talk taught me more in a month than three app streaks.", "decision", "personal", False,
     [("Duolingo", "organization"), ("German", "language"), ("Rewe", "organization"), ("Kastanienallee", "place")],
     [("Rewe", "Duolingo", "REPLACES")],
     "which language-learning approach took over from the app and why",
     "language learning app swap real shop immersion cashier small talk progress"),
    # --- 3 ---
    ("Got the Niederlassungserlaubsnis approved on 2026-03-22 after five years on the Blue Card; no more annual appointments at the Behörde.", "milestone", "personal", False,
     [("Niederlassungserlaubsnis", "concept"), ("2026-03-22", "date"), ("Blue Card", "concept"), ("Behörde", "organization")],
     [("Niederlassungserlaubsnis", "Blue Card", "REPLACES")],
     "when did my permanent residence land and what did it replace",
     "permanent residence approval blue card five year date milestone"),
    # --- 4 ---
    ("The culture-shock spike hit around month four, not week one; Christmas 2024 alone in Lisbon with shuttered shops was the rough patch, not the airport arrival.", "fact", "personal", False,
     [("Christmas 2024", "date"), ("Lisbon", "place"), ("airport", "place")],
     [],
     "when did the culture shock actually peak and what triggered it",
     "culture shock timing month four christmas alone shuttered shops lisbon"),
    # --- 5 ---
    ("Prefers the Stammtisch at Zur Letzten Instanz on Wednesdays over the expat meet-up at Belushi's; locals outnumber newcomers and the German stays slow enough to follow.", "preference", "personal", False,
     [("Stammtisch", "event"), ("Zur Letzten Instanz", "place"), ("Wednesdays", "date"), ("Belushi's", "place"), ("German", "language")],
     [("Stammtisch", "Belushi's", "PREFERS")],
     "which weekly meet-up wins out over the expat bar and why",
     "stammtisch local pub over expat bar language exposure pace reason"),
    # --- 6 ---
    ("The Japanese i-adjective vs na-adjective distinction clicked on 2026-02-03 at Itamae Hiro's counter when he corrected my 'kirei na sushi' to 'oishii sushi' mid-bite.", "milestone", "personal", False,
     [("Japanese", "language"), ("i-adjective", "concept"), ("na-adjective", "concept"), ("2026-02-03", "date"), ("Itamae Hiro", "person")],
     [],
     "when did Japanese adjective classes finally make sense and how",
     "japanese adjective i na breakthrough sushi counter correction date"),
    # --- 7 ---
    ("The Carte de Séjour renewal window opens 2026-06-01 at the Prefecture de Police; arrive before 07:00 or lose the day to the queue.", "reference", "personal", False,
     [("Carte de Séjour", "concept"), ("2026-06-01", "date"), ("Prefecture de Police", "organization")],
     [("Carte de Séjour", "Prefecture de Police", "LOCATED_IN")],
     "when does the French residence-card renewal slot open and what is the queue rule",
     "carte de sejour renewal window prefecture early arrival queue rule date"),
    # --- 8 ---
    ("Going back to Manila for three weeks in 2025-12 reset my Tagalog noticeably; Tita Celia said the Berlin vowels were softening my 'ng' sounds.", "fact", "personal", False,
     [("Manila", "place"), ("2025-12", "date"), ("Tagalog", "language"), ("Tita Celia", "person"), ("Berlin", "place")],
     [],
     "what did the home visit do to my mother tongue and who noticed",
     "home visit tagalog reset accent drift berlin vowel ng sound aunt"),
    # --- 9 ---
    ("The Anmeldung appointment at the Bürgeramt Mitte on 2026-04-03 was booked twelve weeks out; brought passport, Wohnungsgeberbestätigung, and a blue pen because black is rejected.", "reference", "personal", False,
     [("Anmeldung", "concept"), ("Bürgeramt Mitte", "organization"), ("2026-04-03", "date"), ("Wohnungsgeberbestätigung", "concept")],
     [("Anmeldung", "Bürgeramt Mitte", "LOCATED_IN")],
     "how far ahead is the German address registration booked and what must I bring",
     "anmeldung burgeramt booking lead time document pen colour gotcha"),
    # --- 10. noise ---
    ("One second, I'll grab the residence folder from the shelf.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The padaria on Rua do Salitre is where my Portuguese actually lives; Dona Fátima gives me the wrong change on purpose to make me count back in Portuguese.", "fact", "personal", False,
     [("padaria", "place"), ("Rua do Salitre", "place"), ("Portuguese", "language"), ("Dona Fátima", "person")],
     [("padaria", "Rua do Salitre", "LOCATED_IN")],
     "where does the daily Portuguese practice actually happen and what is the trick",
     "bakery portuguese daily practice wrong change count back language drill"),
    # --- 12 ---
    ("Replaced the weekly Zoom call with Mom with a standing Sunday 09:00 Manila time WhatsApp video; the time-zone drift on calendars was killing us.", "decision", "personal", False,
     [("Zoom", "organization"), ("Mom", "person"), ("Sunday", "date"), ("Manila", "place"), ("WhatsApp", "organization")],
     [("WhatsApp", "Zoom", "REPLACES")],
     "which home-call setup took over and why the scheduling change",
     "home call zoom swap whatsapp fixed sunday manila time timezone drift"),
    # --- 13 ---
    ("The TCK identity question hits hardest on forms asking for 'home town'; Manila-born, raised across Dubai and Singapore, twelve years in Berlin — I default to Berlin now.", "fact", "personal", False,
     [("TCK", "concept"), ("Manila", "place"), ("Dubai", "place"), ("Singapore", "place"), ("Berlin", "place")],
     [],
     "how do I answer the home-town question on forms and why",
     "TCK identity hometown form manila dubai singapore berlin default"),
    # --- 14 ---
    ("Chose the Lycée Français over the Berlin International School for Noa starting 2026-09; the trilingual track is closer to how she already codeswitches at home.", "decision", "personal", False,
     [("Lycée Français", "organization"), ("Berlin International School", "organization"), ("Noa", "person"), ("2026-09", "date")],
     [("Lycée Français", "Berlin International School", "PREFERS")],
     "which international school won out for my daughter and why",
     "school choice lycee francais over BIS trilingual codeswitch match"),
    # --- 15 ---
    ("The expat Facebook group 'Lisbon Internationals' is fine for bureaucracy tips but I muted it for social plans; the Discord 'Lisbon Locals' has actual Portuguese speakers.", "preference", "personal", False,
     [("Lisbon Internationals", "organization"), ("Lisbon Locals", "organization"), ("Facebook", "organization"), ("Discord", "organization"), ("Portuguese", "language")],
     [("Lisbon Locals", "Lisbon Internationals", "PREFERS")],
     "which online expat group wins for what use and why",
     "facebook group over discord expat bureaucracy social portuguese speakers"),
    # --- 16 ---
    ("The homesickness pattern I've mapped: worst in late January, a short dip around Noa's birthday in May, fine the rest of the year.", "fact", "personal", False,
     [("homesickness", "emotion"), ("January", "date"), ("Noa", "person"), ("May", "date")],
     [],
     "when does the homesickness cycle hit and when is it quiet",
     "homesickness pattern january dip birthday month calm rest of year"),
    # --- 17 ---
    ("Learned the Berlin S-Bahn ring line by accident on 2024-11-09 after missing the Friedrichstraße change; now I take the ring deliberately when I want to read.", "milestone", "personal", False,
     [("Berlin", "place"), ("S-Bahn", "concept"), ("2024-11-09", "date"), ("Friedrichstraße", "place")],
     [("S-Bahn", "Berlin", "LOCATED_IN")],
     "when did the city ring line click and how do I use it now",
     "sbahn ring berlin accidental discovery miss connection deliberate reading"),
    # --- 18 ---
    ("The Kreuzberg versus Prenzlauer Berg choice settled after six months; Kreuzberg's Turkish bakeries beat Prenzlauer Berg's playgrounds for my daily life, not Noa's.", "decision", "personal", False,
     [("Kreuzberg", "place"), ("Prenzlauer Berg", "place"), ("Turkish", "language"), ("Noa", "person")],
     [("Kreuzberg", "Prenzlauer Berg", "PREFERS")],
     "which Berlin neighbourhood won out for me and what was the tradeoff",
     "kreuzberg over prenzlauer berg turkish bakery playground tradeoff"),
    # --- 19 ---
    ("The Goethe B2 exam on 2026-03-15 at Goethe-Institut Berlin passed with 78 percent; writing was the weakest section at 68, speaking the strongest at 89.", "milestone", "personal", False,
     [("Goethe", "organization"), ("B2", "concept"), ("2026-03-15", "date"), ("Goethe-Institut Berlin", "organization")],
     [],
     "when did the German B2 pass land and what was the score breakdown",
     "goethe B2 pass date percent writing weak speaking strong score"),
    # --- 20 ---
    ("The Hanami picnic at Inokashira Park on 2025-04-05 was the first Tokyo friendship breakthrough; Yuki invited us after three months of nodding in the lift.", "milestone", "personal", False,
     [("Hanami", "event"), ("Inokashira Park", "place"), ("2025-04-05", "date"), ("Tokyo", "place"), ("Yuki", "person")],
     [("Hanami", "Inokashira Park", "LOCATED_IN")],
     "when did making friends in Tokyo finally break open and how",
     "hanami tokyo friendship breakthrough neighbour lift three months invite"),
    # --- 21 ---
    ("Adjusted to Portuguese dinner hours the hard way; eating at 18:30 for the first year meant empty restaurants, 21:00 is the real floor in Lisbon.", "fact", "personal", False,
     [("Portuguese", "language"), ("Lisbon", "place")],
     [],
     "how did I adjust to the Portuguese dinner clock and what is the real floor",
     "dinner hours lisbon adjustment 21:00 floor empty restaurant early"),
    # --- 22 ---
    ("The Finanzamt correspondence about the Steuer-ID on 2026-01-28 panicked me for a week until a colleague explained that Festsetzung just means 'assessment'.", "problem", "personal", False,
     [("Finanzamt", "organization"), ("Steuer-ID", "concept"), ("2026-01-28", "date"), ("Festsetzung", "concept")],
     [],
     "what scared me in the tax-office letter and how was it resolved",
     "finanzamt letter panic steuer id festsetzung assessment translation relief"),
    # --- 23 ---
    ("The 'pão de queijo' I miss from São Paulo does not exist in Lisbon; the Lisbon version uses a different cheese and the texture is all wrong.", "fact", "personal", False,
     [("pão de queijo", "food"), ("São Paulo", "place"), ("Lisbon", "place")],
     [],
     "which Brazilian food does not translate to Portugal and why",
     "pao de queijo sao paulo lisbon cheese texture difference miss"),
    # --- 24 ---
    ("Prefers the slow 'learn by overhearing' method at the Viertel cafe over formal Volkshochschule classes; the grammar surfaces in context and actually sticks.", "preference", "personal", False,
     [("Viertel", "place"), ("Volkshochschule", "organization"), ("grammar", "concept")],
     [("Viertel", "Volkshochschule", "PREFERS")],
     "which German-learning mode wins for me and why it sticks",
     "overhearing cafe over volkshochschule class grammar context retention"),
    # --- 25 ---
    ("The Kita placement for Noa at Kita Regenbogen came through on 2026-02-11 after eighteen months on the waiting list; walking distance, mixed-language group.", "milestone", "personal", False,
     [("Kita", "organization"), ("Noa", "person"), ("Kita Regenbogen", "organization"), ("2026-02-11", "date")],
     [],
     "when did the daycare spot land and how long was the wait",
     "kita placement regenbogen waitlist eighteen months mixed language date"),
    # --- 26 ---
    ("Switched from the English-speaking GP at Praxis Mitte to Dr. Neumann on Chausseestraße; the full-German consultations are slower but I now know my own medical vocabulary.", "decision", "personal", False,
     [("Praxis Mitte", "organization"), ("Dr. Neumann", "person"), ("Chausseestraße", "place"), ("German", "language")],
     [("Dr. Neumann", "Praxis Mitte", "REPLACES")],
     "which doctor took over from the English-speaking one and why",
     "GP swap english german practice chausseestrasse medical vocabulary"),
    # --- 27 ---
    ("The São Jorge district in Lisbon is where I settled after six months of hopping; the tram noise is constant but the padaria, pharmacy and creche are within 200 metres.", "decision", "personal", False,
     [("São Jorge", "place"), ("Lisbon", "place"), ("padaria", "place"), ("pharmacy", "place"), ("creche", "place")],
     [("São Jorge", "Lisbon", "LOCATED_IN")],
     "which Lisbon neighbourhood did I settle on and what made it win",
     "sao jorge lisbon neighbourhood choice walkability tram noise tradeoff"),
    # --- 28 ---
    ("The 'tutoyer' switch with Céline happened 2026-02-19 after the third apéro at her place; I was still reaching for 'vous' out of habit for weeks after.", "milestone", "personal", False,
     [("tutoyer", "concept"), ("Céline", "person"), ("2026-02-19", "date"), ("apéro", "event")],
     [],
     "when did French informal pronouns click with that friend and how",
     "tutoyer switch french informal apero friendship date vous habit"),
    # --- 29 ---
    ("The dual-nationality paperwork for Noa's Portuguese and Philippine passports coordinated on 2026-03-29 through the embassy; three appointments, two notarised translations.", "architecture", "personal", False,
     [("Noa", "person"), ("Portuguese", "language"), ("Philippine", "language"), ("embassy", "organization"), ("2026-03-29", "date")],
     [],
     "how was the dual-passport process set up for my kid",
     "dual nationality child portuguese philippine passport embassy appointments"),
    # --- 30 ---
    ("The Japanese 'uchi-soto' distinction took six months of office mistakes before I stopped addressing my own team with keigo in client meetings.", "fact", "personal", False,
     [("Japanese", "language"), ("uchi-soto", "concept"), ("keigo", "concept")],
     [],
     "how long did the in-group out-group Japanese rule take and where did I trip",
     "uchi soto six months office mistake keigo own team client meeting"),
    # --- 31 ---
    ("Prefers the Berlin Christmas markets at Gendarmenmarkt over the Alexanderplatz one; entry fee, but the Glühwein is actually warm and the crowd can breathe.", "preference", "personal", False,
     [("Berlin", "place"), ("Gendarmenmarkt", "place"), ("Alexanderplatz", "place"), ("Glühwein", "food")],
     [("Gendarmenmarkt", "Alexanderplatz", "PREFERS")],
     "which Berlin Weihnachtsmarkt wins out and what is the tradeoff",
     "christmas market gendarmenmarkt over alex entry fee gluhwein crowd"),
    # --- 32 ---
    ("The Visa Appointment System on 2026-04-01 moved the Behörde from in-person to online booking; the old 06:00 doorstep queue is gone but slots now vanish in 90 seconds.", "decision", "personal", False,
     [("Visa Appointment System", "organization"), ("2026-04-01", "date"), ("Behörde", "organization")],
     [("Visa Appointment System", "Behörde", "REPLACES")],
     "when did the in-person visa queue swap to online and what changed",
     "visa appointment system online replace queue behorde doorstep slot speed"),
    # --- 33 ---
    ("The 'morriña' word from my Galician grandmother covers what 'homesickness' does not; it's the specific ache for the sea smell at A Coruña.", "fact", "personal", False,
     [("morriña", "concept"), ("Galician", "language"), ("homesickness", "emotion"), ("A Coruña", "place")],
     [],
     "which foreign word names a feeling English misses and for where",
     "morrina galician homesickness specific sea smell a coruna grandmother"),
    # --- 34. noise ---
    ("Let me check the Ausweis is in the usual drawer.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Found the Filipino community church at Santo Niño Chapel on Weserstraße through a Facebook post; first Sunday mass in Tagalog fixed the slow homesickness I hadn't named.", "milestone", "personal", False,
     [("Santo Niño Chapel", "organization"), ("Weserstraße", "place"), ("Facebook", "organization"), ("Tagalog", "language"), ("homesickness", "emotion")],
     [("Santo Niño Chapel", "Weserstraße", "LOCATED_IN")],
     "how did I find the Filipino community here and what did it do",
     "filipino church tagalog mass weserstrasse facebook homesickness fix"),
    # --- 36 ---
    ("Prefers eating rice with the Filipino aunties at Kantine Süd on Wednesdays over the German canteen lunch; the food is closer to home and the Tagalog cross-talk rests my head.", "preference", "personal", False,
     [("Kantine Süd", "organization"), ("Wednesdays", "date"), ("German", "language"), ("Tagalog", "language"), ("rice", "food")],
     [("Kantine Süd", "German", "PREFERS")],
     "which weekday lunch wins for my head and why",
     "kantine sud wednesday filipino rice over german canteen tagalog rest"),
    # --- 37 ---
    ("Noa's first full Portuguese sentence at the creche on 2026-01-17 was 'não quero dormir'; the refusal came before the politeness.", "milestone", "personal", False,
     [("Noa", "person"), ("Portuguese", "language"), ("creche", "place"), ("2026-01-17", "date")],
     [("Noa", "creche", "LOCATED_IN")],
     "when did my kid's first full Portuguese sentence happen and what was it",
     "noa first portuguese sentence creche refusal date nao quero dormir"),
    # --- 38 ---
    ("The language cafe at Café Oberkampf on Thursdays is a fixed node in my week; twenty minutes of French with Laurent, twenty of Japanese with Aiko, no homework between.", "architecture", "personal", False,
     [("Café Oberkampf", "place"), ("Thursdays", "date"), ("French", "language"), ("Laurent", "person"), ("Japanese", "language"), ("Aiko", "person")],
     [("Café Oberkampf", "French", "RELATED_TO")],
     "how is the weekly language exchange set up and who anchors it",
     "language cafe oberkampf thursday french japanese laurent aiko format"),
    # --- 39 ---
    ("Replaced the Anki deck with real sticky notes on Berlin apartment objects; two weeks in, kitchen vocabulary stuck in a way eight months of digital SRS never did.", "decision", "personal", False,
     [("Anki", "organization"), ("Berlin", "place"), ("sticky notes", "tool"), ("kitchen", "place"), ("SRS", "concept")],
     [("sticky notes", "Anki", "REPLACES")],
     "which vocabulary method took over and what was the retention difference",
     "sticky notes over anki apartment object kitchen retention SRS failure"),
    # --- 40 ---
    ("The Tokyo 'gaijin card' replacement on 2025-08-11 at Shinjuku-ku Yakusho took 40 minutes total; booking was the hard part, not the counter.", "fact", "personal", False,
     [("Tokyo", "place"), ("gaijin card", "concept"), ("2025-08-11", "date"), ("Shinjuku-ku Yakusho", "organization")],
     [("gaijin card", "Shinjuku-ku Yakusho", "LOCATED_IN")],
     "when did I replace the Japanese resident card and how long did the visit take",
     "gaijin card replace shinjuku ward office booking counter time date"),
    # --- 41 ---
    ("The 'assimilation versus integration' conversation with Papa at Manila dinner 2025-12-23 landed hard; he called the Berlin-German shift 'adoption, not integration'.", "fact", "personal", False,
     [("Papa", "person"), ("Manila", "place"), ("2025-12-23", "date"), ("Berlin", "place"), ("German", "language")],
     [],
     "what did Dad say about my integration in Germany and when",
     "papa manila dinner assimilation integration adoption germany berlin"),
    # --- 42 ---
    ("The Lisbon SEF (now AIMA) transition for the Visto de Residência on 2026-02-08 turned a three-month wait into a six-month wait; the backlog was the real news.", "problem", "personal", False,
     [("Lisbon", "place"), ("SEF", "organization"), ("AIMA", "organization"), ("Visto de Residência", "concept"), ("2026-02-08", "date")],
     [("AIMA", "SEF", "REPLACES")],
     "what agency change hit the Portuguese residence visa and what was the effect",
     "sef aima transition portugal visa backlog wait time change date"),
    # --- 43 ---
    ("The 'going-home-for-Christmas' budget is set at €2,400 for 2026: flights for two, one week of gifts, and the unavoidable Tita Celia envelope for her grandkids.", "reference", "personal", False,
     [("Christmas", "event"), ("2026", "date"), ("Tita Celia", "person")],
     [],
     "how is the annual home-visit budget structured and what are the line items",
     "christmas home visit budget flights gifts envelope aunt yearly"),
    # --- 44 ---
    ("The Philippine dual-citizenship RA 9225 oath at the embassy on 2026-05-20 keeps the passport alive; without it, another five years abroad and it lapses.", "milestone", "personal", False,
     [("Philippine", "language"), ("RA 9225", "concept"), ("embassy", "organization"), ("2026-05-20", "date")],
     [],
     "when is the dual-citizenship oath and why does it matter",
     "RA 9225 philippine dual citizenship oath embassy passport lapse date"),
    # --- 45 ---
    ("The expat Discord 'Berlin Foreigners Helpdesk' broke on 2026-03-20 when a mod deleted the bureaucracy channel; three former members reopened 'Berlin Behörde Survival' the same week.", "problem", "personal", False,
     [("Berlin Foreigners Helpdesk", "organization"), ("Discord", "organization"), ("2026-03-20", "date"), ("Berlin Behörde Survival", "organization")],
     [("Berlin Behörde Survival", "Berlin Foreigners Helpdesk", "REPLACES")],
     "what happened to the expat help server and what came after",
     "discord expat server mod delete bureaucracy channel fork replacement date"),
    # --- 46 ---
    ("Prefers the Filipino sari-sari at Manila Mart on Sonnenallee over the Asian supermarket at Dong Xuan; the bagoong is fresher and the aunties remember which brand I use.", "preference", "personal", False,
     [("Manila Mart", "organization"), ("Sonnenallee", "place"), ("Dong Xuan", "place"), ("bagoong", "food"), ("aunties", "person")],
     [("Manila Mart", "Dong Xuan", "PREFERS")],
     "which Asian grocery wins out and why",
     "manila mart sonnenallee over dong xuan bagoong freshness aunties memory"),
    # --- 47 ---
    ("The 'drei Monate Frist' for the Abmeldung when moving back to Lisbon in 2026-07 means I have to time the deregistration before I leave, not after.", "reference", "personal", False,
     [("drei Monate Frist", "concept"), ("Abmeldung", "concept"), ("Lisbon", "place"), ("2026-07", "date")],
     [],
     "what is the deregistration rule when leaving Germany and what is the timing",
     "abmeldung drei monate frist leaving germany before departure lisbon"),
    # --- 48 ---
    ("Chose the International School of Lisbon over the Deutsche Schule for Noa's 2026-09 start; the IB track survives another move better than the Abitur track would.", "decision", "personal", False,
     [("International School of Lisbon", "organization"), ("Deutsche Schule", "organization"), ("Noa", "person"), ("2026-09", "date"), ("IB", "concept"), ("Abitur", "concept")],
     [("International School of Lisbon", "Deutsche Schule", "PREFERS")],
     "which school track won for my kid and what was the tiebreaker",
     "international school lisbon over deutsche schule IB abitur portability"),
    # --- 49 ---
    ("The A1 Portuguese exam at Instituto Camões on 2026-04-18 passed at 84 percent; the reading comprehension was easier than the listening because I read before I hear daily.", "milestone", "personal", False,
     [("A1", "concept"), ("Portuguese", "language"), ("Instituto Camões", "organization"), ("2026-04-18", "date")],
     [("A1", "Instituto Camões", "LOCATED_IN")],
     "when did the Portuguese A1 pass land and what was easy vs hard",
     "camoes A1 portuguese pass percent reading over listening daily use"),
    # --- 50 ---
    ("The feeling of being 'at home' in Berlin finally clicked on 2026-02-27 at the Turmstraße U-Bahn when I corrected a tourist's platform direction without thinking about it in German first.", "milestone", "personal", False,
     [("Berlin", "place"), ("2026-02-27", "date"), ("Turmstraße", "place"), ("U-Bahn", "concept"), ("German", "language")],
     [("Turmstraße", "Berlin", "LOCATED_IN")],
     "when did Berlin finally feel like home and what was the marker",
     "berlin at home moment turmstrasse u-bahn tourist directions german unthinking"),
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
