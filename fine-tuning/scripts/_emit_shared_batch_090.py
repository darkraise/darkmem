"""One-off emitter for shared-base batch-090 — personal domain (spirituality and faith practices slice).

Writes 50 rows to data/v2/shared/batch_090.tmp.jsonl with ids shared-04451..04500.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_090.tmp.jsonl"
ID_OFFSET = 4450

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Attends the 10:30 choral Eucharist at St Alban's Parish every Sunday; the sung liturgy lands better than the said 08:00 service for me.", "preference", "personal", False,
     [("choral Eucharist", "event"), ("St Alban's Parish", "organization"), ("Sunday", "date"), ("sung liturgy", "activity"), ("08:00 service", "event")],
     [("choral Eucharist", "08:00 service", "PREFERS"), ("choral Eucharist", "St Alban's Parish", "LOCATED_IN")],
     "which Sunday service at the parish wins out and why",
     "choral eucharist preference sung over said early service parish"),
    # --- 2 ---
    ("Joined Temple Beth Shalom on 2026-01-18 after three years at Kehillat Or Chadash; the cantor Miriam Rosen was the deciding factor.", "milestone", "personal", False,
     [("Temple Beth Shalom", "organization"), ("2026-01-18", "date"), ("Kehillat Or Chadash", "organization"), ("Miriam Rosen", "person"), ("cantor", "person")],
     [("Temple Beth Shalom", "Kehillat Or Chadash", "REPLACES"), ("Miriam Rosen", "Temple Beth Shalom", "WORKS_AT")],
     "when did I switch synagogues and what tipped the decision",
     "synagogue membership switch congregation cantor deciding factor date"),
    # --- 3 ---
    ("The daf yomi page Berakhot 42a fell on 2026-03-09; working through it with a chavruta partner over Zoom has kept the pace steady for four months.", "fact", "personal", False,
     [("daf yomi", "activity"), ("Berakhot 42a", "publication"), ("2026-03-09", "date"), ("chavruta", "method"), ("Zoom", "platform")],
     [("daf yomi", "chavruta", "USES")],
     "where is the daily Talmud cycle at and how am I keeping up with it",
     "daf yomi page tractate chavruta partner zoom cadence steady"),
    # --- 4 ---
    ("Ramadan 2026 began 2026-02-18; breaking fast at Masjid Al-Noor with the community iftar on Fridays, other nights at home with dates and water first.", "architecture", "personal", False,
     [("Ramadan", "event"), ("2026-02-18", "date"), ("Masjid Al-Noor", "organization"), ("iftar", "event"), ("Fridays", "date"), ("dates", "food")],
     [("iftar", "Masjid Al-Noor", "LOCATED_IN")],
     "how is the fasting month structured between mosque and home this year",
     "ramadan start iftar mosque friday community home dates water rhythm"),
    # --- 5 ---
    ("Switched the morning prayer rhythm from the breviary's Lauds at 07:00 to a shorter lectio divina with the ESV at 06:30; easier to actually hold.", "decision", "personal", False,
     [("breviary", "publication"), ("Lauds", "activity"), ("lectio divina", "activity"), ("ESV", "publication")],
     [("lectio divina", "Lauds", "REPLACES"), ("lectio divina", "ESV", "USES")],
     "which morning prayer practice replaced the liturgy-of-the-hours and why",
     "breviary lauds swap lectio divina shorter sustainable morning rhythm"),
    # --- 6 ---
    ("The confirmation at St Alban's on 2025-05-04 with Bishop Thornton as officiant; sponsor was my godmother Claire, confirmation name chosen was Teresa.", "milestone", "personal", False,
     [("confirmation", "event"), ("St Alban's", "organization"), ("2025-05-04", "date"), ("Bishop Thornton", "person"), ("Claire", "person"), ("Teresa", "person")],
     [("confirmation", "St Alban's", "LOCATED_IN")],
     "when was the confirmation and who officiated and sponsored",
     "confirmation date bishop officiant sponsor godmother saint name choice"),
    # --- 7 ---
    ("Lent 2026 fast this year is alcohol and weekday social media; keeping the Ash Wednesday ashes mark until it rubs off naturally, not washed.", "decision", "personal", False,
     [("Lent", "event"), ("2026", "date"), ("alcohol", "food"), ("social media", "concept"), ("Ash Wednesday", "event"), ("ashes", "concept")],
     [],
     "what am I giving up for the forty-day fast and how am I treating the ash mark",
     "lent fast alcohol social media ash wednesday ashes mark policy"),
    # --- 8 ---
    ("Prefers the 1979 Book of Common Prayer rite over the contemporary Enriching Our Worship liturgy; the cadence of the Rite II Eucharistic Prayer C carries me.", "preference", "personal", False,
     [("1979 Book of Common Prayer", "publication"), ("Enriching Our Worship", "publication"), ("Rite II", "concept"), ("Eucharistic Prayer C", "concept")],
     [("1979 Book of Common Prayer", "Enriching Our Worship", "PREFERS")],
     "which Anglican prayer book edition wins out for my worship",
     "book of common prayer 1979 over enriching worship rite II prayer C"),
    # --- 9 ---
    ("Daily Examen at 21:30 from the Ignatian workbook has replaced the bullet-journal gratitude list; the five movements give the reflection more shape.", "decision", "personal", False,
     [("Daily Examen", "activity"), ("Ignatian workbook", "publication"), ("bullet-journal", "tool"), ("gratitude list", "activity"), ("five movements", "concept")],
     [("Daily Examen", "gratitude list", "REPLACES"), ("Daily Examen", "Ignatian workbook", "USES")],
     "which evening reflection practice replaced the gratitude journal and why",
     "examen ignatian five movements over gratitude journal structure night"),
    # --- 10. noise ---
    ("The kettle just clicked off so give me half a minute.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The pilgrimage to Iona is booked for 2026-07-11 through 2026-07-18; walking week with the Wild Goose community, staying at the abbey.", "milestone", "personal", False,
     [("Iona", "place"), ("2026-07-11", "date"), ("2026-07-18", "date"), ("Wild Goose community", "organization"), ("abbey", "place")],
     [("Wild Goose community", "Iona", "LOCATED_IN")],
     "when is the Iona pilgrimage and with which community am I travelling",
     "iona pilgrimage booking week wild goose community abbey stay dates"),
    # --- 12 ---
    ("Left the Willowbrook Evangelical Fellowship in 2025-09 after eleven years; the six-month silent phase ended with joining a Quaker meeting in Reading.", "milestone", "personal", False,
     [("Willowbrook Evangelical Fellowship", "organization"), ("2025-09", "date"), ("Quaker meeting", "organization"), ("Reading", "place")],
     [("Quaker meeting", "Willowbrook Evangelical Fellowship", "REPLACES"), ("Quaker meeting", "Reading", "LOCATED_IN")],
     "when did I leave the evangelical church and where did I end up worshipping",
     "leaving congregation quaker meeting transition silent phase reading date"),
    # --- 13 ---
    ("The household altar in the south-east alcove holds an icon of Christ Pantocrator, a beeswax candle, and the photo of Grandma Rosa who taught me the Hail Mary.", "reference", "personal", False,
     [("household altar", "infrastructure"), ("alcove", "place"), ("Christ Pantocrator", "concept"), ("beeswax candle", "tool"), ("Grandma Rosa", "person"), ("Hail Mary", "publication")],
     [("household altar", "alcove", "LOCATED_IN")],
     "what sits on the home prayer corner and what is its meaning",
     "home altar icon candle photo grandmother hail mary alcove items"),
    # --- 14 ---
    ("Bar mitzvah at Temple Beth Shalom on 2025-10-25 for my nephew Eli; the aliyah I read was Lech-Lecha, a portion Rabbi Stern gave me as honour father.", "milestone", "personal", False,
     [("Bar mitzvah", "event"), ("Temple Beth Shalom", "organization"), ("2025-10-25", "date"), ("Eli", "person"), ("Lech-Lecha", "publication"), ("Rabbi Stern", "person"), ("aliyah", "activity")],
     [("Bar mitzvah", "Temple Beth Shalom", "LOCATED_IN")],
     "when was Eli's bar mitzvah and what torah portion did I read",
     "bar mitzvah nephew date synagogue parasha lech lecha aliyah rabbi"),
    # --- 15 ---
    ("The Bible-in-a-year plan using the Blue Letter Bible chronological reading hit Leviticus 14 on 2026-04-12; slightly behind, catching up on the commute.", "fact", "personal", False,
     [("Bible-in-a-year", "activity"), ("Blue Letter Bible", "tool"), ("chronological reading", "method"), ("Leviticus 14", "publication"), ("2026-04-12", "date"), ("commute", "activity")],
     [("Bible-in-a-year", "Blue Letter Bible", "USES")],
     "where is my annual scripture plan sitting and how am I catching up",
     "bible in a year chronological leviticus progress commute catch up"),
    # --- 16 ---
    ("Yom Kippur 2025 observed the full 25-hour fast at Kehillat Or Chadash; the Ne'ilah service closing with the shofar blast hit harder than last year.", "fact", "personal", False,
     [("Yom Kippur", "event"), ("2025", "date"), ("Kehillat Or Chadash", "organization"), ("Ne'ilah", "event"), ("shofar", "tool")],
     [("Ne'ilah", "Kehillat Or Chadash", "LOCATED_IN")],
     "how did the day-of-atonement observance go this year",
     "yom kippur full fast twenty five hour neilah shofar closing service"),
    # --- 17 ---
    ("The rosary practice shifted from the full four mysteries daily to one set daily rotating through the week; sustainable is better than heroic.", "decision", "personal", False,
     [("rosary", "activity"), ("four mysteries", "concept"), ("one set daily", "method"), ("week", "date")],
     [("one set daily", "four mysteries", "REPLACES")],
     "which rosary rhythm replaced the heavier daily practice",
     "rosary practice change one set rotation over full daily sustainable"),
    # --- 18 ---
    ("Picked up spiritual direction with Sister Agnes Murphy at the Benedictine priory in Worth; monthly sessions since 2025-11, sliding scale fee.", "milestone", "personal", False,
     [("spiritual direction", "activity"), ("Sister Agnes Murphy", "person"), ("Benedictine priory", "organization"), ("Worth", "place"), ("2025-11", "date")],
     [("Benedictine priory", "Worth", "LOCATED_IN"), ("spiritual direction", "Sister Agnes Murphy", "USES")],
     "when did spiritual direction start and who is directing me",
     "spiritual direction sister benedictine priory worth monthly start date"),
    # --- 19 ---
    ("The Taizé chant evenings at St Alban's run first Fridays at 19:30; the Ubi Caritas setting has stayed in rotation for two years running.", "reference", "personal", False,
     [("Taizé chant", "activity"), ("St Alban's", "organization"), ("Fridays", "date"), ("Ubi Caritas", "publication")],
     [("Taizé chant", "St Alban's", "LOCATED_IN")],
     "when and where do the taize evenings happen at my parish",
     "taize chant first friday evening parish ubi caritas rotation venue"),
    # --- 20 ---
    ("The funeral for Uncle Theodore on 2026-03-22 at Holy Trinity Orthodox Cathedral; Father Demetrios led the Panikhida, I sang the Kontakion for the Departed.", "milestone", "personal", False,
     [("funeral", "event"), ("Uncle Theodore", "person"), ("2026-03-22", "date"), ("Holy Trinity Orthodox Cathedral", "organization"), ("Father Demetrios", "person"), ("Panikhida", "event"), ("Kontakion for the Departed", "publication")],
     [("funeral", "Holy Trinity Orthodox Cathedral", "LOCATED_IN"), ("Father Demetrios", "Holy Trinity Orthodox Cathedral", "WORKS_AT")],
     "when was the uncle's funeral and what was my role at the service",
     "funeral cathedral orthodox priest panikhida kontakion sing role date"),
    # --- 21 ---
    ("Prefers the NRSV study Bible with footnotes over the NIV I grew up on; the historical notes do heavy lifting during the Sunday lectio group.", "preference", "personal", False,
     [("NRSV study Bible", "publication"), ("footnotes", "concept"), ("NIV", "publication"), ("Sunday lectio group", "event")],
     [("NRSV study Bible", "NIV", "PREFERS")],
     "which scripture edition wins out for me now and why",
     "NRSV over NIV study bible footnotes lectio group historical notes"),
    # --- 22 ---
    ("The silent eight-day retreat at St Beuno's Jesuit Centre runs 2026-08-02 to 2026-08-10; full Spiritual Exercises first week, director is Father Brendan Walsh.", "milestone", "personal", False,
     [("silent eight-day retreat", "event"), ("St Beuno's Jesuit Centre", "organization"), ("2026-08-02", "date"), ("2026-08-10", "date"), ("Spiritual Exercises", "publication"), ("Father Brendan Walsh", "person")],
     [("silent eight-day retreat", "St Beuno's Jesuit Centre", "LOCATED_IN")],
     "when is the Ignatian silent retreat and who is directing it",
     "silent retreat ignatian jesuit centre first week director dates"),
    # --- 23 ---
    ("Baptised my daughter Aoife at St Alban's on 2025-06-29 during the Petertide Sunday service; godparents were Priya Shah and my brother Callum.", "milestone", "personal", False,
     [("Baptised", "event"), ("Aoife", "person"), ("St Alban's", "organization"), ("2025-06-29", "date"), ("Petertide", "event"), ("Priya Shah", "person"), ("Callum", "person")],
     [("Baptised", "St Alban's", "LOCATED_IN")],
     "when was Aoife baptised and who stood as godparents",
     "baptism daughter parish petertide sunday date godparents names"),
    # --- 24 ---
    ("The Wednesday Compline service at St Alban's now replaces the Thursday home Evening Prayer I was doing alone; community rhythm beats solitary discipline.", "decision", "personal", False,
     [("Wednesday Compline", "event"), ("St Alban's", "organization"), ("Thursday", "date"), ("Evening Prayer", "activity")],
     [("Wednesday Compline", "Evening Prayer", "REPLACES"), ("Wednesday Compline", "St Alban's", "LOCATED_IN")],
     "which evening office replaced the solo one and what drove the swap",
     "compline parish wednesday over solo evening prayer thursday community"),
    # --- 25 ---
    ("The Advent wreath this year was lit by Aoife on 2025-12-01; purple candle for hope, kept on the dining table with the Jesse tree beside it.", "fact", "personal", False,
     [("Advent wreath", "tool"), ("Aoife", "person"), ("2025-12-01", "date"), ("purple candle", "tool"), ("hope", "concept"), ("dining table", "place"), ("Jesse tree", "tool")],
     [("Advent wreath", "dining table", "LOCATED_IN")],
     "how did this year's advent wreath ritual look in the home",
     "advent wreath daughter lighting first sunday purple hope jesse tree"),
    # --- 26 ---
    ("The chanting practice at Chithurst Buddhist Monastery on 2026-04-05 left me wanting more; might take a lay precept-observance day there in summer.", "fact", "personal", False,
     [("chanting practice", "activity"), ("Chithurst Buddhist Monastery", "organization"), ("2026-04-05", "date"), ("precept-observance day", "event"), ("summer", "date")],
     [("chanting practice", "Chithurst Buddhist Monastery", "LOCATED_IN")],
     "what happened at the monastery visit and what am I considering next",
     "chithurst chanting monastery lay observance day summer plan date"),
    # --- 27 ---
    ("Prefers Fr Emmanuel Abrahamsen's homilies to Fr Liam O'Connor's; Emmanuel builds from one Greek word and Liam from anecdote, Greek lands harder for me.", "preference", "personal", False,
     [("Fr Emmanuel Abrahamsen", "person"), ("Fr Liam O'Connor", "person"), ("homilies", "activity"), ("Greek word", "concept"), ("anecdote", "method")],
     [("Fr Emmanuel Abrahamsen", "Fr Liam O'Connor", "PREFERS")],
     "which priest's preaching lands harder for me and why",
     "homily preference emmanuel over liam greek exegesis over anecdote"),
    # --- 28 ---
    ("The wedding on 2025-08-16 at St Alban's had the Song of Songs 8:6 as the first reading; Vicar Harriet Sinclair preached on 'love as strong as death'.", "milestone", "personal", False,
     [("wedding", "event"), ("2025-08-16", "date"), ("St Alban's", "organization"), ("Song of Songs 8:6", "publication"), ("Vicar Harriet Sinclair", "person")],
     [("wedding", "St Alban's", "LOCATED_IN"), ("Vicar Harriet Sinclair", "St Alban's", "WORKS_AT")],
     "when was the wedding and what was the first reading and preaching",
     "wedding parish first reading song of songs vicar preach date"),
    # --- 29 ---
    ("The Taizé pilgrimage in 2024-07 was the hinge; couldn't go back to the megachurch after a week of silence and candlelit prayer with the brothers.", "fact", "personal", False,
     [("Taizé pilgrimage", "event"), ("2024-07", "date"), ("megachurch", "organization"), ("candlelit prayer", "activity"), ("brothers", "person")],
     [],
     "which trip triggered the break with the previous church style",
     "taize pilgrimage hinge megachurch leaving silence candlelit prayer"),
    # --- 30 ---
    ("The Kaddish for my father Yitzhak Cohen ran eleven months from 2025-04-11; stood daily at Temple Beth Shalom's morning minyan, finished 2026-03-11.", "fact", "personal", False,
     [("Kaddish", "activity"), ("Yitzhak Cohen", "person"), ("2025-04-11", "date"), ("Temple Beth Shalom", "organization"), ("morning minyan", "event"), ("2026-03-11", "date")],
     [("Kaddish", "Temple Beth Shalom", "LOCATED_IN")],
     "when did the mourner's kaddish period run and where did I say it",
     "kaddish father eleven months minyan synagogue start end dates"),
    # --- 31 ---
    ("The Secular Humanist contemplative group at Unity Hall meets second Tuesdays; it replaced the mindfulness app as the landing pad for the non-theist seasons.", "decision", "personal", False,
     [("Secular Humanist contemplative group", "organization"), ("Unity Hall", "place"), ("Tuesdays", "date"), ("mindfulness app", "tool")],
     [("Secular Humanist contemplative group", "mindfulness app", "REPLACES"), ("Secular Humanist contemplative group", "Unity Hall", "LOCATED_IN")],
     "which group replaced the app for the non-theist spiritual seasons",
     "secular humanist contemplative group unity hall over mindfulness app"),
    # --- 32 ---
    ("Prefers the King James Psalms in Coverdale's pointing for chant over the NRSV prose; the parish choir and I both land better on the archaic cadence.", "preference", "personal", False,
     [("King James Psalms", "publication"), ("Coverdale", "person"), ("NRSV", "publication"), ("parish choir", "organization")],
     [("King James Psalms", "NRSV", "PREFERS")],
     "which psalter wins out for the chanted offices and why",
     "king james coverdale psalms over NRSV pointing chant parish choir"),
    # --- 33 ---
    ("The Hajj savings pot stands at £3,420 of the £7,500 target on 2026-04-08; Imam Yusuf said aim for 2028 and the book will find its moment.", "fact", "personal", False,
     [("Hajj", "event"), ("2026-04-08", "date"), ("Imam Yusuf", "person"), ("2028", "date")],
     [("Imam Yusuf", "Hajj", "RELATED_TO")],
     "where is the hajj savings and what is the target year",
     "hajj fund progress target imam advice year savings pilgrimage plan"),
    # --- 34. noise ---
    ("The cat has walked across the keyboard again, one moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Joined the Catechumenate at St Alban's on 2026-02-14; weekly Thursday classes with Deacon Margaret Holbrook until Easter Vigil reception in 2027.", "milestone", "personal", False,
     [("Catechumenate", "event"), ("St Alban's", "organization"), ("2026-02-14", "date"), ("Thursday", "date"), ("Deacon Margaret Holbrook", "person"), ("Easter Vigil", "event"), ("2027", "date")],
     [("Catechumenate", "St Alban's", "LOCATED_IN")],
     "when did the catechumenate start and when does it end",
     "catechumenate start weekly deacon easter vigil reception year dates"),
    # --- 36 ---
    ("The shabbat table rhythm: candles by 18:04 on 2026-04-17, kiddush over the Manischewitz, challah from Goldblatt's Bakery, no phones until havdalah.", "architecture", "personal", False,
     [("shabbat", "event"), ("2026-04-17", "date"), ("kiddush", "activity"), ("Manischewitz", "food"), ("challah", "food"), ("Goldblatt's Bakery", "organization"), ("havdalah", "event")],
     [("challah", "Goldblatt's Bakery", "RELATED_TO")],
     "how is the friday shabbat table structured in our house",
     "shabbat candle time kiddush manischewitz challah bakery phone policy"),
    # --- 37 ---
    ("The Taizé icon corner at home replaced the framed Scripture verses; one candle, the San Damiano cross, a sprig of rosemary from the garden.", "decision", "personal", False,
     [("Taizé icon corner", "infrastructure"), ("Scripture verses", "publication"), ("candle", "tool"), ("San Damiano cross", "tool"), ("rosemary", "food")],
     [("Taizé icon corner", "Scripture verses", "REPLACES")],
     "what replaced the wall verses as the home prayer focal point",
     "taize icon corner over scripture wall verses candle cross rosemary"),
    # --- 38 ---
    ("Prefers Ignatian imaginative-Gospel contemplation over Lectio Divina for the afternoon slot; placing myself in the scene holds my mind better than the text drill.", "preference", "personal", False,
     [("Ignatian imaginative-Gospel contemplation", "activity"), ("Lectio Divina", "activity"), ("afternoon slot", "date")],
     [("Ignatian imaginative-Gospel contemplation", "Lectio Divina", "PREFERS")],
     "which contemplative practice wins the afternoon slot and why",
     "ignatian imaginative contemplation over lectio divina afternoon focus"),
    # --- 39 ---
    ("The Ash Wednesday service on 2026-02-18 at St Alban's was lay-led for the first time in four years; Rev Sinclair was in hospital, warden Joan Patel presided.", "fact", "personal", False,
     [("Ash Wednesday service", "event"), ("2026-02-18", "date"), ("St Alban's", "organization"), ("Rev Sinclair", "person"), ("Joan Patel", "person"), ("warden", "person")],
     [("Ash Wednesday service", "St Alban's", "LOCATED_IN")],
     "how did the ash wednesday service at the parish run this year",
     "ash wednesday lay led service warden presided vicar absent parish"),
    # --- 40 ---
    ("The Book of Common Prayer offices app Daily Prayer replaced the paper breviary on commute days; same 1979 rite, lighter bag, cellular dark-mode at dusk.", "decision", "personal", False,
     [("Book of Common Prayer", "publication"), ("Daily Prayer", "tool"), ("paper breviary", "publication"), ("commute", "activity")],
     [("Daily Prayer", "paper breviary", "REPLACES")],
     "which office aid replaced the paper breviary on the commute and why",
     "daily prayer app over paper breviary commute weight dark mode rite"),
    # --- 41 ---
    ("The Friday Jummah prayer at Masjid Al-Noor runs at 13:15 in winter, 13:45 in summer; Imam Yusuf's khutbah on sabr from 2026-03-20 stays with me.", "fact", "personal", False,
     [("Friday Jummah prayer", "event"), ("Masjid Al-Noor", "organization"), ("winter", "date"), ("summer", "date"), ("Imam Yusuf", "person"), ("khutbah", "activity"), ("sabr", "concept"), ("2026-03-20", "date")],
     [("Friday Jummah prayer", "Masjid Al-Noor", "LOCATED_IN")],
     "when does the friday congregational prayer run and which sermon stayed with me",
     "jummah mosque winter summer time imam khutbah sabr patience date"),
    # --- 42 ---
    ("The grief after Dad's death in 2025-04 cracked the faith open; the honest answer for six months was 'I don't know' and the parish held the space anyway.", "fact", "personal", False,
     [("grief", "emotion"), ("Dad", "person"), ("2025-04", "date"), ("faith", "concept"), ("parish", "organization")],
     [("grief", "faith", "CAUSES")],
     "how did the father's death reshape the faith posture for that stretch",
     "grief father death faith crack honest not knowing parish held space"),
    # --- 43 ---
    ("The Camino de Santiago walk from Sarria to Santiago runs 2026-09-14 to 2026-09-23; carrying the scallop shell from Grandma Rosa's pilgrimage in 1978.", "milestone", "personal", False,
     [("Camino de Santiago", "event"), ("Sarria", "place"), ("Santiago", "place"), ("2026-09-14", "date"), ("2026-09-23", "date"), ("scallop shell", "tool"), ("Grandma Rosa", "person"), ("1978", "date")],
     [("Camino de Santiago", "Santiago", "LOCATED_IN")],
     "when is the camino walk and what heirloom goes with me",
     "camino santiago sarria dates scallop shell grandmother pilgrimage heirloom"),
    # --- 44 ---
    ("The Lord's Prayer I say at night is the ecumenical 1988 ELLC version, not the 1662 one from childhood; 'save us from the time of trial' lands truer than 'lead us not into temptation'.", "preference", "personal", False,
     [("Lord's Prayer", "publication"), ("1988 ELLC version", "publication"), ("1662", "publication"), ("time of trial", "concept"), ("temptation", "concept")],
     [("1988 ELLC version", "1662", "PREFERS")],
     "which version of the Lord's Prayer wins at night for me",
     "lord's prayer ELLC 1988 over 1662 time of trial night version"),
    # --- 45 ---
    ("The scripture-in-a-year plan on Blue Letter Bible stalled in Numbers last year; switching to M'Cheyne four-passages-a-day on 2026-01-01 has held for 14 weeks.", "problem", "personal", False,
     [("scripture-in-a-year", "activity"), ("Blue Letter Bible", "tool"), ("Numbers", "publication"), ("M'Cheyne", "method"), ("2026-01-01", "date")],
     [("M'Cheyne", "scripture-in-a-year", "REPLACES")],
     "which reading plan replaced the stalled one and how is it holding",
     "scripture plan stall numbers mccheyne four passages new year hold"),
    # --- 46 ---
    ("The Orthodox Nativity Fast starting 2025-11-15 was the first full attempt; broke it once at a work dinner on 2025-12-03, Father Demetrios said that's fine, start the next day.", "fact", "personal", False,
     [("Orthodox Nativity Fast", "event"), ("2025-11-15", "date"), ("work dinner", "event"), ("2025-12-03", "date"), ("Father Demetrios", "person")],
     [],
     "how did the forty-day advent fast go in the orthodox tradition this year",
     "nativity fast orthodox start date break work dinner priest counsel"),
    # --- 47 ---
    ("Prefers the sung Divine Liturgy of St John Chrysostom at Holy Trinity Orthodox Cathedral over St Basil on Sundays; Chrysostom's brevity fits the energy I have.", "preference", "personal", False,
     [("Divine Liturgy of St John Chrysostom", "event"), ("Holy Trinity Orthodox Cathedral", "organization"), ("St Basil", "event"), ("Sundays", "date")],
     [("Divine Liturgy of St John Chrysostom", "St Basil", "PREFERS"), ("Divine Liturgy of St John Chrysostom", "Holy Trinity Orthodox Cathedral", "LOCATED_IN")],
     "which divine liturgy wins for me on sundays at the cathedral",
     "chrysostom over basil divine liturgy sunday cathedral orthodox length"),
    # --- 48 ---
    ("The evening examen pairing with my spouse Ben started 2026-03-01; we swap one consolation and one desolation from the day before lights out, no cross-talk.", "architecture", "personal", False,
     [("evening examen pairing", "activity"), ("Ben", "person"), ("2026-03-01", "date"), ("consolation", "concept"), ("desolation", "concept")],
     [],
     "how does the shared nightly examen with my spouse actually run",
     "examen pairing spouse consolation desolation no cross talk rhythm start"),
    # --- 49 ---
    ("The parish small group meets Monday nights at 31 Laurel Close; we're four weeks into N.T. Wright's 'Simply Christian', pairing chapters with Ephesians.", "reference", "personal", False,
     [("parish small group", "organization"), ("Monday nights", "date"), ("31 Laurel Close", "place"), ("N.T. Wright", "person"), ("Simply Christian", "publication"), ("Ephesians", "publication")],
     [("parish small group", "31 Laurel Close", "LOCATED_IN"), ("Simply Christian", "N.T. Wright", "AUTHORED_BY")],
     "when does the home group meet and what are we working through",
     "small group monday house book wright simply christian ephesians pairing"),
    # --- 50. noise ---
    ("My phone just buzzed, I'll silence it and get right back to you.", "fact", "noise", True, [], [], None, None),
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
