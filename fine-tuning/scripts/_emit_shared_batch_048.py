"""One-off emitter for shared-base batch-048 — knowledge domain (religion, mythology, comparative religious studies).

Writes 50 rows with ids shared-02351..02400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_048.tmp.jsonl"
ID_OFFSET = 2350

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Karl Jaspers's Axial Age framework dates a simultaneous spiritual ferment across Greece, Israel, India, and China between roughly 800 and 200 BCE.", "reference", "knowledge", False,
     [("Karl Jaspers", "person"), ("Axial Age", "theory"), ("Greece", "place"), ("Israel", "place"), ("India", "place"), ("China", "place")],
     [("Axial Age", "Karl Jaspers", "AUTHORED_BY")],
     "which mid-century philosopher proposed a shared first-millennium spiritual watershed across Eurasia",
     "Achsenzeit simultaneous Eurasian awakening philosopher periodisation"),
    # --- 2 ---
    ("The Upanishadic turn moved Vedic religion away from external sacrificial ritual toward inner identification of atman with brahman.", "decision", "knowledge", False,
     [("Upanishadic turn", "concept"), ("Vedic religion", "concept"), ("atman", "concept"), ("brahman", "concept")],
     [("Upanishadic turn", "Vedic religion", "REPLACES")],
     "which transition shifted Indian religion from outer sacrifice toward inner self-brahman identity",
     "shramana internalisation sacrifice ritual atman brahman turn"),
    # --- 3 ---
    ("Mahayana Buddhism emerged in the first centuries CE and foregrounds the bodhisattva ideal against the earlier arhat goal of Nikaya schools.", "fact", "knowledge", False,
     [("Mahayana Buddhism", "concept"), ("bodhisattva", "concept"), ("arhat", "concept"), ("Nikaya schools", "concept")],
     [("Mahayana Buddhism", "Nikaya schools", "BUILDS_ON")],
     "which later Buddhist movement elevated the bodhisattva vow over the arhat goal of earlier schools",
     "bodhisattva ideal great vehicle early Buddhist school successor"),
    # --- 4 ---
    ("Nagarjuna's Mulamadhyamakakarika, composed around the second century CE, grounds Madhyamaka philosophy in the emptiness of inherent existence.", "reference", "knowledge", False,
     [("Nagarjuna", "person"), ("Mulamadhyamakakarika", "publication"), ("Madhyamaka", "theory"), ("emptiness", "concept")],
     [("Mulamadhyamakakarika", "Nagarjuna", "AUTHORED_BY"), ("Madhyamaka", "emptiness", "DEPENDS_ON")],
     "which early Indian treatise anchors the middle-way school in the doctrine of emptiness",
     "middle way sunyata root verses Nagarjuna treatise century"),
    # --- 5 ---
    ("Yogacara philosophy, articulated by Asanga and Vasubandhu in the fourth century CE, reframes experience around the storehouse consciousness known as alayavijnana.", "fact", "knowledge", False,
     [("Yogacara", "theory"), ("Asanga", "person"), ("Vasubandhu", "person"), ("alayavijnana", "concept")],
     [("Yogacara", "Asanga", "AUTHORED_BY")],
     "which mind-only Mahayana school introduced the storehouse consciousness as its central construct",
     "mind only consciousness only alaya store brothers fourth century"),
    # --- 6 ---
    ("Bodhidharma is traditionally said to have brought Chan Buddhism from India to China around 520 CE, where it later transmitted to Japan as Zen.", "milestone", "knowledge", False,
     [("Bodhidharma", "person"), ("Chan Buddhism", "concept"), ("India", "place"), ("China", "place"), ("Japan", "place"), ("520 CE", "date"), ("Zen", "concept")],
     [("Zen", "Chan Buddhism", "BUILDS_ON")],
     "which monk is traditionally credited with carrying Chan from India to China in the sixth century",
     "first patriarch Chan transmission India China year Zen successor"),
    # --- 7 ---
    ("The Council of Nicaea in 325 CE produced the Nicene Creed, settling the Arian controversy in favour of the homoousios formula.", "milestone", "knowledge", False,
     [("Council of Nicaea", "event"), ("325 CE", "date"), ("Nicene Creed", "publication"), ("Arian controversy", "concept"), ("homoousios", "concept")],
     [("Nicene Creed", "Council of Nicaea", "AUTHORED_BY")],
     "which fourth-century council produced the creed that fixed the homoousios formula",
     "Nicaea Arian homoousios ecumenical council creed year"),
    # --- 8 ---
    ("The Masoretic Text of the Tanakh, fixed by Tiberian scribes between the seventh and tenth centuries CE, standardised Hebrew vocalisation and cantillation.", "reference", "knowledge", False,
     [("Masoretic Text", "publication"), ("Tanakh", "publication"), ("Tiberian scribes", "organization")],
     [("Masoretic Text", "Tiberian scribes", "AUTHORED_BY")],
     "which early medieval scribal tradition fixed the pointed Hebrew text of the Jewish scriptures",
     "Masoretes Tiberian vocalisation Hebrew Bible pointing standardisation"),
    # --- 9 ---
    ("Athanasius's Easter Letter of 367 CE is the earliest surviving document listing the twenty-seven New Testament books as canonical.", "reference", "knowledge", False,
     [("Athanasius", "person"), ("Easter Letter", "publication"), ("367 CE", "date"), ("New Testament", "publication")],
     [("Easter Letter", "Athanasius", "AUTHORED_BY")],
     "which fourth-century festal letter first enumerates the standard New Testament canon",
     "thirty ninth festal letter Athanasius canon enumeration year"),
    # --- 10. noise ---
    ("Let me double-check that ordination date against the diocesan archive before I cite it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Abu Hanifa founded the Hanafi school of Sunni jurisprudence in eighth-century Kufa, privileging reasoned analogy alongside the Quran and hadith.", "milestone", "knowledge", False,
     [("Abu Hanifa", "person"), ("Hanafi school", "concept"), ("Kufa", "place"), ("Quran", "publication"), ("hadith", "concept")],
     [("Hanafi school", "Abu Hanifa", "AUTHORED_BY")],
     "which eighth-century Iraqi jurist founded the Sunni school that leans on qiyas",
     "Kufa Iraqi school ray qiyas reasoned analogy founder century"),
    # --- 12 ---
    ("Al-Shafi'i's Risala, written around 820 CE, systematised Islamic legal theory by ranking Quran, sunnah, consensus, and analogy as the four sources.", "reference", "knowledge", False,
     [("Al-Shafi'i", "person"), ("Risala", "publication"), ("820 CE", "date"), ("sunnah", "concept"), ("consensus", "concept")],
     [("Risala", "Al-Shafi'i", "AUTHORED_BY")],
     "which ninth-century treatise first ordered the four roots of Sunni jurisprudence",
     "usul al fiqh four sources ranking treatise ninth century"),
    # --- 13 ---
    ("The Naqshbandi Sufi order, organised around Baha al-Din Naqshband in fourteenth-century Bukhara, prefers silent dhikr over vocal remembrance.", "preference", "knowledge", False,
     [("Naqshbandi", "organization"), ("Baha al-Din Naqshband", "person"), ("Bukhara", "place"), ("silent dhikr", "method"), ("vocal remembrance", "method")],
     [("Naqshbandi", "Baha al-Din Naqshband", "AUTHORED_BY"), ("silent dhikr", "vocal remembrance", "PREFERS")],
     "which central-Asian Sufi order favours silent remembrance over vocal recitation",
     "Bukhara tariqa silent dhikr khafi vocal comparison order"),
    # --- 14 ---
    ("The Chishti order, carried into South Asia by Muin al-Din Chishti in the late twelfth century, became the dominant Sufi brotherhood of the Delhi Sultanate.", "fact", "knowledge", False,
     [("Chishti order", "organization"), ("Muin al-Din Chishti", "person"), ("South Asia", "place"), ("Delhi Sultanate", "organization")],
     [("Chishti order", "Muin al-Din Chishti", "AUTHORED_BY")],
     "which Sufi order shaped medieval north-Indian Islam under the Delhi sultans",
     "Ajmer Khwaja Chishti South Asia brotherhood spread twelfth century"),
    # --- 15 ---
    ("The Reform Judaism movement, formalised at the 1885 Pittsburgh Platform, scaled back binding halakhic observance in favour of ethical monotheism.", "decision", "knowledge", False,
     [("Reform Judaism", "concept"), ("Pittsburgh Platform", "publication"), ("1885", "date"), ("halakhic observance", "concept"), ("ethical monotheism", "concept")],
     [("Pittsburgh Platform", "Reform Judaism", "AUTHORED_BY"), ("ethical monotheism", "halakhic observance", "PREFERS")],
     "which 1885 American platform repositioned Reform Judaism around ethical monotheism",
     "Pittsburgh Platform American Reform classical ethical monotheism year"),
    # --- 16 ---
    ("Conservative Judaism, crystallised around Solomon Schechter and the Jewish Theological Seminary from 1902, positions itself between Reform and Orthodox trajectories.", "fact", "knowledge", False,
     [("Conservative Judaism", "concept"), ("Solomon Schechter", "person"), ("Jewish Theological Seminary", "organization"), ("1902", "date")],
     [("Conservative Judaism", "Solomon Schechter", "AUTHORED_BY")],
     "which early-twentieth-century American movement placed itself between Reform and Orthodox Judaism",
     "JTS Schechter Conservative Judaism founding middle path year"),
    # --- 17 ---
    ("The Second Vatican Council, convened between 1962 and 1965, replaced the Tridentine Latin liturgy with vernacular worship and reframed Catholic engagement with other religions.", "milestone", "knowledge", False,
     [("Second Vatican Council", "event"), ("1962", "date"), ("1965", "date"), ("Tridentine Latin liturgy", "concept"), ("vernacular worship", "concept")],
     [("vernacular worship", "Tridentine Latin liturgy", "REPLACES")],
     "which mid-twentieth-century council swapped Latin liturgy for vernacular Catholic worship",
     "Vatican II aggiornamento vernacular liturgy reform years"),
    # --- 18 ---
    ("Pentecostalism traces its modern origin to the Azusa Street revival of 1906 led by William J. Seymour in Los Angeles.", "milestone", "knowledge", False,
     [("Pentecostalism", "concept"), ("Azusa Street revival", "event"), ("1906", "date"), ("William J. Seymour", "person"), ("Los Angeles", "place")],
     [("Azusa Street revival", "William J. Seymour", "AUTHORED_BY")],
     "which 1906 Los Angeles revival is treated as the founding event of modern Pentecostalism",
     "Azusa Street Seymour revival Los Angeles Spirit year"),
    # --- 19 ---
    ("Gustavo Gutierrez's A Theology of Liberation, published in 1971, argued that Christian theology must begin from the perspective of the oppressed poor.", "reference", "knowledge", False,
     [("Gustavo Gutierrez", "person"), ("A Theology of Liberation", "publication"), ("1971", "date"), ("oppressed poor", "concept")],
     [("A Theology of Liberation", "Gustavo Gutierrez", "AUTHORED_BY")],
     "which 1971 Peruvian book programmed liberation theology as a method from the poor",
     "Peruvian theology praxis preferential option year"),
    # --- 20 ---
    ("Alfred North Whitehead's process theology, sketched in Process and Reality of 1929, conceives God as dipolar and co-evolving with creation.", "architecture", "knowledge", False,
     [("Alfred North Whitehead", "person"), ("process theology", "theory"), ("Process and Reality", "publication"), ("1929", "date")],
     [("Process and Reality", "Alfred North Whitehead", "AUTHORED_BY")],
     "whose 1929 metaphysics seeded twentieth-century process theology",
     "process reality dipolar God metaphysics philosopher year"),
    # --- 21 ---
    ("Joseph Smith dictated the Book of Mormon in 1829 near Palmyra, New York, claiming translation from inscribed gold plates.", "milestone", "knowledge", False,
     [("Joseph Smith", "person"), ("Book of Mormon", "publication"), ("1829", "date"), ("Palmyra", "place"), ("New York", "place")],
     [("Book of Mormon", "Joseph Smith", "AUTHORED_BY")],
     "when and where did Joseph Smith dictate the Book of Mormon",
     "Palmyra gold plates dictation LDS founding text year"),
    # --- 22 ---
    ("The Baha'i Faith originated when Baha'u'llah declared his prophetic mission in the Baghdad Garden of Ridvan in 1863.", "milestone", "knowledge", False,
     [("Baha'i Faith", "concept"), ("Baha'u'llah", "person"), ("Garden of Ridvan", "place"), ("Baghdad", "place"), ("1863", "date")],
     [("Baha'i Faith", "Baha'u'llah", "AUTHORED_BY")],
     "in which year and city did the founder of this new faith proclaim his mission",
     "Baghdad Ridvan declaration Baha prophethood founding year"),
    # --- 23 ---
    ("Guru Gobind Singh founded the Khalsa at Anandpur Sahib in 1699, consolidating Sikh identity around the five Ks.", "milestone", "knowledge", False,
     [("Guru Gobind Singh", "person"), ("Khalsa", "concept"), ("Anandpur Sahib", "place"), ("1699", "date"), ("five Ks", "concept")],
     [("Khalsa", "Guru Gobind Singh", "AUTHORED_BY")],
     "when did the tenth Sikh guru initiate the Khalsa at Anandpur",
     "Khalsa Anandpur five Ks tenth guru founding year"),
    # --- 24 ---
    ("The Jain schism between Digambara and Svetambara traditions, traced to roughly the first century CE, centres on monastic nudity and the accessibility of liberation to women.", "problem", "knowledge", False,
     [("Jain schism", "event"), ("Digambara", "concept"), ("Svetambara", "concept"), ("monastic nudity", "activity")],
     [],
     "which ancient Jain split hinges on monastic nudity and women's liberation",
     "Digambara Svetambara nudity women moksha schism ancient"),
    # --- 25 ---
    ("State Shinto, instituted under the Meiji government in 1868, refashioned shrine Shinto into an imperial civic cult until its 1945 disestablishment.", "fact", "knowledge", False,
     [("State Shinto", "concept"), ("Meiji government", "organization"), ("1868", "date"), ("shrine Shinto", "concept"), ("1945", "date")],
     [("State Shinto", "shrine Shinto", "REPLACES")],
     "which Meiji-era policy restructured shrine Shinto into an imperial civic cult",
     "Kokka Shinto Meiji imperial cult disestablishment years"),
    # --- 26 ---
    ("The Poetic Edda, preserved in the thirteenth-century Codex Regius manuscript, anchors most surviving Norse mythological cycles.", "reference", "knowledge", False,
     [("Poetic Edda", "publication"), ("Codex Regius", "publication"), ("Norse mythological cycles", "concept")],
     [],
     "which medieval Icelandic manuscript preserves the core Norse mythological poems",
     "Codex Regius Elder Edda Icelandic poem collection thirteenth century"),
    # --- 27 ---
    ("Hesiod's Theogony, composed around 700 BCE, narrates the succession of Greek divine generations from Chaos through Zeus.", "reference", "knowledge", False,
     [("Hesiod", "person"), ("Theogony", "publication"), ("700 BCE", "date"), ("Chaos", "concept"), ("Zeus", "concept")],
     [("Theogony", "Hesiod", "AUTHORED_BY")],
     "which archaic Greek poem organises the divine generations from Chaos to Zeus",
     "Hesiod Theogony divine succession Greek cosmogony archaic"),
    # --- 28 ---
    ("The Mahabharata, attributed to Vyasa and compiled between roughly 400 BCE and 400 CE, frames its ethical discourse around the Kurukshetra war.", "reference", "knowledge", False,
     [("Mahabharata", "publication"), ("Vyasa", "person"), ("Kurukshetra war", "event")],
     [("Mahabharata", "Vyasa", "AUTHORED_BY")],
     "which long Sanskrit epic stages its ethical teaching around the Kurukshetra war",
     "Vyasa Sanskrit epic Kurukshetra dharma war narrative compilation"),
    # --- 29 ---
    ("The Popol Vuh, preserved in an early-eighteenth-century Quiche Maya manuscript, records the Hero Twins narrative of Mesoamerican creation.", "reference", "knowledge", False,
     [("Popol Vuh", "publication"), ("Quiche Maya", "organization"), ("Hero Twins", "concept"), ("Mesoamerican creation", "concept")],
     [],
     "which colonial Quiche Maya book preserves the Hero Twins creation cycle",
     "Popol Vuh Quiche Maya Hero Twins creation manuscript colonial"),
    # --- 30 ---
    ("Ifa divination, centred on the Yoruba babalawo tradition of West Africa, reads 256 odu signatures cast with palm nuts or the opele chain.", "fact", "knowledge", False,
     [("Ifa divination", "method"), ("Yoruba", "organization"), ("babalawo", "person"), ("West Africa", "place"), ("odu", "concept"), ("opele chain", "tool")],
     [],
     "which West African divination system interprets 256 odu signatures cast with palm nuts",
     "Yoruba Ifa babalawo odu palm nut opele West Africa"),
    # --- 31 ---
    ("Mircea Eliade's The Sacred and the Profane, published in 1957, articulates a phenomenology of religion built on hierophanies and sacred space.", "reference", "knowledge", False,
     [("Mircea Eliade", "person"), ("The Sacred and the Profane", "publication"), ("1957", "date"), ("hierophanies", "concept"), ("sacred space", "concept")],
     [("The Sacred and the Profane", "Mircea Eliade", "AUTHORED_BY")],
     "which 1957 book systematised a phenomenology of religion around hierophany",
     "Eliade sacred profane hierophany phenomenology book year"),
    # --- 32 ---
    ("Ninian Smart's seven dimensions of religion, proposed in the 1970s, improves on belief-only definitions by adding ritual, narrative, material, and social dimensions.", "reference", "knowledge", False,
     [("Ninian Smart", "person"), ("seven dimensions of religion", "framework"), ("belief-only definitions", "concept")],
     [("seven dimensions of religion", "Ninian Smart", "AUTHORED_BY"), ("seven dimensions of religion", "belief-only definitions", "IMPROVES_ON")],
     "whose multidimensional schema refined belief-centric definitions of religion",
     "Ninian Smart seven dimensions ritual narrative material model"),
    # --- 33 ---
    ("The 2014 Pew Religious Landscape Study surveyed over 35,000 Americans to map denominational affiliation, switching, and disaffiliation patterns.", "reference", "knowledge", False,
     [("Pew Religious Landscape Study", "publication"), ("2014", "date"), ("denominational affiliation", "finding")],
     [],
     "which large 2014 survey mapped American religious affiliation and switching in detail",
     "Pew Religious Landscape American affiliation switching survey year"),
    # --- 34. noise ---
    ("Hmm, I need to verify which recension of that sutra the commentary actually cites.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Jose Casanova's Public Religions in the Modern World, published in 1994, revised the secularisation thesis by distinguishing its three analytically separable claims.", "reference", "knowledge", False,
     [("Jose Casanova", "person"), ("Public Religions in the Modern World", "publication"), ("1994", "date"), ("secularisation thesis", "theory")],
     [("Public Religions in the Modern World", "Jose Casanova", "AUTHORED_BY"), ("Public Religions in the Modern World", "secularisation thesis", "IMPROVES_ON")],
     "which 1994 book recast the secularisation thesis into separable analytic claims",
     "Casanova public religions secularisation deprivatisation book year"),
    # --- 36 ---
    ("Robert Orsi's lived religion approach studies devotional practice in kitchens, streets, and shrines rather than official doctrine.", "preference", "knowledge", False,
     [("Robert Orsi", "person"), ("lived religion", "method"), ("devotional practice", "concept"), ("official doctrine", "concept")],
     [("lived religion", "Robert Orsi", "AUTHORED_BY"), ("lived religion", "official doctrine", "PREFERS")],
     "whose ethnographic approach favours kitchen and street piety over doctrine",
     "Orsi lived religion everyday practice ethnography approach"),
    # --- 37 ---
    ("Rudolf Otto's Das Heilige of 1917 frames religious experience around the mysterium tremendum et fascinans, an encounter with the numinous.", "reference", "knowledge", False,
     [("Rudolf Otto", "person"), ("Das Heilige", "publication"), ("1917", "date"), ("mysterium tremendum et fascinans", "concept"), ("numinous", "concept")],
     [("Das Heilige", "Rudolf Otto", "AUTHORED_BY")],
     "which 1917 German book theorised religion around the numinous and mysterium tremendum",
     "Otto idea holy numinous mysterium tremendum fascinans year"),
    # --- 38 ---
    ("Wilfred Cantwell Smith's The Meaning and End of Religion, published in 1962, proposes replacing the reified noun religion with faith and cumulative tradition.", "decision", "knowledge", False,
     [("Wilfred Cantwell Smith", "person"), ("The Meaning and End of Religion", "publication"), ("1962", "date"), ("religion", "concept"), ("cumulative tradition", "concept")],
     [("The Meaning and End of Religion", "Wilfred Cantwell Smith", "AUTHORED_BY"), ("cumulative tradition", "religion", "REPLACES")],
     "which 1962 comparative-religion book urged dropping the reified noun religion",
     "Cantwell Smith faith cumulative tradition reified noun year"),
    # --- 39 ---
    ("Talal Asad's Genealogies of Religion, published in 1993, argues that the modern concept of religion is a product of Western Christian history rather than a universal category.", "reference", "knowledge", False,
     [("Talal Asad", "person"), ("Genealogies of Religion", "publication"), ("1993", "date"), ("modern concept of religion", "claim")],
     [("Genealogies of Religion", "Talal Asad", "AUTHORED_BY")],
     "which 1993 anthropological book argued religion is a Western Christian artefact rather than universal",
     "Asad genealogies religion Western Christian construction year"),
    # --- 40 ---
    ("Theravada Buddhism preserves the Pali Canon and centres on the arhat ideal, remaining the dominant tradition of Sri Lanka and mainland Southeast Asia.", "fact", "knowledge", False,
     [("Theravada Buddhism", "concept"), ("Pali Canon", "publication"), ("arhat", "concept"), ("Sri Lanka", "place"), ("Southeast Asia", "place")],
     [],
     "which southern Buddhist school anchors the island and mainland countries below the Himalayas",
     "Theravada Pali Canon arhat southern transmission continental"),
    # --- 41 ---
    ("Martin Luther's posting of the Ninety-Five Theses at Wittenberg in 1517 is conventionally treated as the flashpoint of the Protestant Reformation.", "milestone", "knowledge", False,
     [("Martin Luther", "person"), ("Ninety-Five Theses", "publication"), ("Wittenberg", "place"), ("1517", "date"), ("Protestant Reformation", "event")],
     [("Ninety-Five Theses", "Martin Luther", "AUTHORED_BY")],
     "when did Luther's Ninety-Five Theses surface at Wittenberg",
     "Wittenberg Luther Theses indulgences reformation flashpoint year"),
    # --- 42 ---
    ("The Great Schism of 1054 formalised the split between the Roman Catholic and Eastern Orthodox churches over filioque, papal primacy, and leavened bread.", "milestone", "knowledge", False,
     [("Great Schism", "event"), ("1054", "date"), ("Roman Catholic", "organization"), ("Eastern Orthodox", "organization"), ("filioque", "concept"), ("papal primacy", "concept")],
     [],
     "which eleventh-century schism separated the Roman and Eastern churches over filioque and papal primacy",
     "East West 1054 schism filioque papal primacy leavened bread"),
    # --- 43 ---
    ("The Dead Sea Scrolls, recovered from Qumran caves between 1947 and 1956, dramatically reshaped scholarly understanding of Second Temple Judaism.", "milestone", "knowledge", False,
     [("Dead Sea Scrolls", "publication"), ("Qumran", "place"), ("1947", "date"), ("1956", "date"), ("Second Temple Judaism", "concept")],
     [],
     "which mid-twentieth-century manuscript recoveries overhauled Second Temple Judaism studies",
     "Qumran Dead Sea Scrolls recovery Second Temple discovery years"),
    # --- 44 ---
    ("Dogen's Shobogenzo, compiled in thirteenth-century Japan, grounds Soto Zen in the practice of shikantaza, or just sitting.", "reference", "knowledge", False,
     [("Dogen", "person"), ("Shobogenzo", "publication"), ("Japan", "place"), ("Soto Zen", "concept"), ("shikantaza", "method")],
     [("Shobogenzo", "Dogen", "AUTHORED_BY"), ("Soto Zen", "shikantaza", "DEPENDS_ON")],
     "which medieval Japanese Zen master grounded Soto practice in shikantaza",
     "Dogen Shobogenzo shikantaza just sitting Soto Japanese Zen"),
    # --- 45 ---
    ("The Rinzai Zen lineage, carried to Japan by Eisai in 1191, prefers koan introspection over the quiet sitting emphasised by the later Soto stream.", "preference", "knowledge", False,
     [("Rinzai Zen", "concept"), ("Eisai", "person"), ("Japan", "place"), ("1191", "date"), ("koan introspection", "method"), ("quiet sitting", "method")],
     [("Rinzai Zen", "Eisai", "AUTHORED_BY"), ("koan introspection", "quiet sitting", "PREFERS")],
     "which Japanese Zen lineage leans on koan study rather than silent sitting",
     "Rinzai Eisai koan Japan transmission year preference"),
    # --- 46 ---
    ("Moses Maimonides's Guide for the Perplexed, completed around 1190, reconciles Aristotelian philosophy with rabbinic Judaism and enumerates thirteen principles of faith.", "reference", "knowledge", False,
     [("Moses Maimonides", "person"), ("Guide for the Perplexed", "publication"), ("1190", "date"), ("Aristotelian philosophy", "field"), ("rabbinic Judaism", "concept")],
     [("Guide for the Perplexed", "Moses Maimonides", "AUTHORED_BY")],
     "which twelfth-century work harmonised Aristotelian thought with rabbinic Judaism",
     "Maimonides Guide Perplexed Aristotelian rabbinic thirteen principles year"),
    # --- 47 ---
    ("Ibn Arabi's Fusus al-Hikam, composed in 1229, became the theoretical spine of the wahdat al-wujud or unity of being school in Sufi metaphysics.", "reference", "knowledge", False,
     [("Ibn Arabi", "person"), ("Fusus al-Hikam", "publication"), ("1229", "date"), ("wahdat al-wujud", "theory")],
     [("Fusus al-Hikam", "Ibn Arabi", "AUTHORED_BY"), ("wahdat al-wujud", "Ibn Arabi", "AUTHORED_BY")],
     "which thirteenth-century Sufi treatise anchors the unity-of-being school",
     "Ibn Arabi Fusus Bezels wahdat al wujud Sufi metaphysics year"),
    # --- 48 ---
    ("Pope Francis's encyclical Laudato Si, issued in 2015, extends Catholic social teaching to include climate and ecological obligation.", "milestone", "knowledge", False,
     [("Pope Francis", "person"), ("Laudato Si", "publication"), ("2015", "date"), ("Catholic social teaching", "concept")],
     [("Laudato Si", "Pope Francis", "AUTHORED_BY"), ("Laudato Si", "Catholic social teaching", "BUILDS_ON")],
     "which 2015 papal encyclical pulled climate and ecology into Catholic social teaching",
     "Laudato Si ecology encyclical Catholic social teaching year"),
    # --- 49 ---
    ("The Gwangmyeong-era canon of Cheondogyo, reorganised by Son Byong-hi in 1905, rebranded the nineteenth-century Donghak movement as a modern Korean religion.", "fact", "knowledge", False,
     [("Cheondogyo", "concept"), ("Son Byong-hi", "person"), ("1905", "date"), ("Donghak", "concept"), ("Korean religion", "concept")],
     [("Cheondogyo", "Donghak", "REPLACES")],
     "which 1905 reorganisation turned the Donghak movement into the Cheondogyo religion",
     "Cheondogyo Son Byong hi Donghak Korean religion year"),
    # --- 50 ---
    ("J. Z. Smith's Imagining Religion of 1982 argues that religion is a scholarly category constructed by comparison rather than an object simply found in the world.", "reference", "knowledge", False,
     [("J. Z. Smith", "person"), ("Imagining Religion", "publication"), ("1982", "date"), ("religion", "concept")],
     [("Imagining Religion", "J. Z. Smith", "AUTHORED_BY")],
     "which 1982 book argued that religion is a scholarly construct rather than a found object",
     "Jonathan Z Smith imagining religion category construction comparative year"),
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
