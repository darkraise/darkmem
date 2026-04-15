"""Retrieval top-up batch-024: code-switch queries over shared rows 2300..2399."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_024.tmp.jsonl"
ID_OFFSET = 2300
SHARED_OFFSET = 2300
QUERY_KIND = "code-switch"

# 100 code-switch queries, rotating across Spanish (es), French (fr), German (de),
# Japanese romaji (ja), Vietnamese (vi), Portuguese (pt), Mandarin pinyin (zh),
# Hindi romanised (hi), Korean romanised (ko), Italian (it). English technical
# terms, proper nouns, and acronyms are preserved verbatim.
QUERIES: list[str] = [
    # 2300 es — Keeling Curve Mauna Loa 1958
    "por qué la Keeling Curve en Mauna Loa desde 1958 es el record CO2 mas largo continuo",
    # 2301 fr — IPCC AR6 WGI 2021 human influence unequivocal
    "quand IPCC AR6 Working Group I a conclu que human influence sur le climate est unequivocal",
    # 2302 de — SSP replaces RCP for CMIP6
    "warum ersetzt die SSP scenario family die alten RCP labels fuer CMIP6 projections mit narratives",
    # 2303 ja — Hansen 1981 Science paper warming signal
    "Hansen no 1981 Science paper ga anthropogenic warming signal wo itsu made ni emerge suru to yosoku",
    # 2304 vi — Michael Mann hockey stick 1998
    "hockey stick reconstruction của Michael Mann năm 1998 đã show twentieth-century warming ra sao",
    # 2305 pt — World Weather Attribution rapid studies
    "como a World Weather Attribution roda rapid attribution studies para extreme events individuais",
    # 2306 zh — planetary boundaries Rockstrom 2009 nine processes
    "Johan Rockstrom 2009 de planetary boundaries framework weishenme ding le nine Earth system processes",
    # 2307 hi — Doughnut Economics Kate Raworth 2017
    "Kate Raworth ki Doughnut Economics 2017 mein planetary ceiling ke saath social foundation kaise jodti hai",
    # 2308 ko — CMIP6 coordinates climate models IPCC
    "CMIP6 ga jeonsegye climate models reul eotteoke coordinate haeseo IPCC assessments reul jiwonhae",
    # 2309 it (noise) — re-check AR6 page numbers
    "aspetta un momento, let me re-check the AR6 page numbers prima di citarli",
    # 2310 es — AMOC weakening proxy evidence
    "qué dice la proxy evidence sobre el AMOC weakening over the twentieth century en Atlantico",
    # 2311 fr — coral bleaching SST summer max plus 1C
    "pourquoi le mass coral bleaching se declenche quand la SST depasse le summer maximum d'environ 1C",
    # 2312 de — permafrost carbon feedback
    "wie viele Gigatonnen CO2 und Methan kann der permafrost carbon feedback aus dem Arctic freisetzen",
    # 2313 ja — IEA Net Zero by 2050 roadmap 2021
    "IEA Net Zero by 2050 roadmap 2021 ga 1.5C keep suru tame no sectoral milestones wo douyatte mapped",
    # 2314 vi — Science Based Targets initiative well below 2C
    "Science Based Targets initiative đã validate corporate emissions targets well below 2C như thế nào",
    # 2315 pt — Climeworks prefers modular DAC over point-source
    "por que a Climeworks prefere modular direct air capture em vez de point-source capture para legacy emissions",
    # 2316 zh — Carbon Engineering DAC Texas megatonne
    "Carbon Engineering zai Texas de direct air capture plant zenme shexiang yi megatonne CO2 per year",
    # 2317 hi — enhanced rock weathering basalt farmland
    "enhanced rock weathering farmland par crushed basalt phailakar CO2 ko kaise lock karta hai carbonates mein",
    # 2318 ko — biochar pyrolysis soil carbon decades
    "biochar ga pyrolysis ro mandeureojyeoseo soil e biogenic carbon reul decades dongan stabilise haneun iyu",
    # 2319 it — IPCC afforestation reforestation avoided deforestation
    "come distingue l'IPCC tra afforestation, reforestation e avoided deforestation per land-use accounting",
    # 2320 es — soil carbon permanence contested cycles back decades
    "por qué la soil carbon permanence sigue contested cuando los studies muestran cycling back dentro de decadas",
    # 2321 fr — PAS 2060 ISO 14064 GHG accounting
    "comment PAS 2060 couvre les carbon neutrality claims pendant que ISO 14064 standardise le GHG accounting",
    # 2322 de — GHG Protocol Scope 1 Scope 2 Scope 3
    "wie teilt das GHG Protocol corporate emissions in Scope 1 direct, Scope 2 energy und Scope 3 value chain",
    # 2323 ja — voluntary carbon offsets inflated claims
    "voluntary carbon offsets ga compliance markets no soto de inflated reduction claims de hihan sareru riyuu",
    # 2324 vi — IPCC AR6 remaining carbon budget 500 Gt from 2020
    "IPCC AR6 nói remaining carbon budget khoảng 500 gigatonnes CO2 từ 2020 cho 1.5C ra sao",
    # 2325 pt — cloud feedback uncertainty ECS spread
    "por que o residual cloud feedback uncertainty domina o spread de equilibrium climate sensitivity entre models",
    # 2326 zh — anthropogenic aerosol cooling brighter clouds
    "anthropogenic aerosol cooling zenme tongguo scattering sunlight he brighter clouds yanmo greenhouse warming",
    # 2327 hi — satellite methane budgets oil gas leaks
    "satellite retrievals ke mutabik oil aur gas operations official inventories se kitna zyada methane leak karte hain",
    # 2328 ko — Hansen 2023 Earth Energy Imbalance paper
    "Hansen 2023 Earth's Energy Imbalance paper ga aerosol cleanup ro near-term warming i deo ppareudago juseokhaneun iyu",
    # 2329 it (noise) — re-read methods section
    "devo rileggere la methods section before paraphrasing that climate claim, un attimo",
    # 2330 es — West Antarctic ocean-driven vs Arctic atmospheric
    "por qué la Antarctic ice loss es dominada por ocean-driven thinning mientras que la Arctic es atmospheric",
    # 2331 fr — Argo float array ocean heat content 90 percent
    "comment l'array Argo mesure le ocean heat content qui absorbe plus de 90 percent de l'excess energy anthropique",
    # 2332 de — World Glacier Monitoring Service since 1894
    "wie zeigt der World Glacier Monitoring Service seit 1894 accelerating loss an fast jedem reference glacier",
    # 2333 ja — degrowth planned contraction wealthy economies
    "degrowth no ronjoku ga wealthy economies ni naze planned contraction wo yoseru no ka planetary boundaries tame",
    # 2334 vi — attribution 2003 European heatwave twice as likely
    "attribution science đã show 2003 European heatwave được made at least twice as likely by human influence",
    # 2335 pt — IPBES Global Assessment 2019 one million species
    "por que o IPBES Global Assessment de 2019 concluiu que cerca de one million species enfrentam extinction",
    # 2336 zh — biodiversity hotspots Norman Myers 1988
    "Norman Myers 1988 biodiversity hotspots gainian zenme youxian endemism gao he habitat loss yanzhong quyu",
    # 2337 hi — ISO 14040 ISO 14044 life cycle assessment
    "life-cycle assessment mein ISO 14040 aur ISO 14044 system boundaries aur impact allocation kaise govern karte hain",
    # 2338 ko — event-based probabilistic vs trend detection
    "attribution science ga event-based probabilistic studies reul trend-focused detection boda wae seonhohae public communication",
    # 2339 it — sea level rise 1.4 to 3.7 mm per year
    "perche il global sea level rise e accelerato da circa 1.4 mm/anno a 3.7 mm/anno secondo IPCC AR6",
    # 2340 es — IPCC SR15 2018 1.5C versus 2C distinct
    "cómo el IPCC SR15 2018 enmarco el 1.5C goal como materialmente distinto de 2C para ecosystems humanos",
    # 2341 fr — AR7 accelerated cycle WGI late 2020s
    "quand est prevue la sortie de AR7 Working Group I dans le cycle accelere de la fin des annees 2020",
    # 2342 de — early IPCC energy balance to coupled AOGCM
    "wie wurden early energy-balance models der IPCC durch coupled atmosphere-ocean general circulation models ersetzt",
    # 2343 ja — carbon pricing over voluntary offsets tradable sector
    "carbon pricing ga voluntary offsets yori tradable-sector emissions no decarbonisation ni mukuru riyuu",
    # 2344 vi — doughnut extends planetary boundaries social equity
    "doughnut economics framework đã extend planetary boundaries ceiling hướng tới social equity như thế nào",
    # 2345 pt — cumulative emissions budgets multi-decade trajectories
    "por que os modeladores de net-zero pathway passaram de single-year targets para full cumulative budgets multi-decade",
    # 2346 zh — Paris Agreement 2015 well below 2C efforts 1.5C
    "Paris Agreement 2015 nian dingle well below 2C de mubiao bing nuli xianzhi warming dao 1.5C",
    # 2347 hi — GRACE satellite ice sheet mass gravity 2002
    "GRACE satellite 2002 se Earth gravity field changes dekhkar ice-sheet mass loss ka estimate kaise deti hai",
    # 2348 ko — Argo near-global coverage 2007 ocean heat
    "Argo autonomous float programme i 2007 nyeon geuncheo global coverage e dodalhan hu ocean heat content datasets i eotteoke gaeseon",
    # 2349 it — Pacala Socolow stabilisation wedges 2004
    "perche Pacala e Socolow nel 2004 hanno proposto le stabilisation wedges per decomporre la mitigation challenge",
    # 2350 es — Axial Age Jaspers 800 to 200 BCE
    "por qué Karl Jaspers situa el Axial Age entre 800 y 200 BCE across Greece Israel India y China",
    # 2351 fr — Upanishadic turn atman brahman
    "comment la Upanishadic turn a deplace la religion vedique du ritual sacrificiel vers l'identification atman avec brahman",
    # 2352 de — Mahayana bodhisattva vs Nikaya arhat
    "wann entstand Mahayana Buddhism und wie stellt das bodhisattva ideal sich gegen das arhat goal der Nikaya Schulen",
    # 2353 ja — Nagarjuna Mulamadhyamakakarika emptiness
    "Nagarjuna no Mulamadhyamakakarika ga Madhyamaka philosophy wo inherent existence no emptiness ni kiseki suru riyuu",
    # 2354 vi — Yogacara Asanga Vasubandhu alayavijnana
    "Yogacara philosophy của Asanga và Vasubandhu đã reframe experience quanh alayavijnana storehouse consciousness ra sao",
    # 2355 pt — Bodhidharma Chan China 520 CE Zen Japan
    "como Bodhidharma trouxe Chan Buddhism da India para a China em 520 CE antes de virar Zen no Japao",
    # 2356 zh — Council of Nicaea 325 homoousios Arian
    "325 nian Council of Nicaea weihe chansheng Nicene Creed bing jiejue Arian controversy homoousios gongshi",
    # 2357 hi — Masoretic Text Tiberian Hebrew
    "Tiberian scribes ne Masoretic Text ko saatvi se dasvi century mein vocalisation aur cantillation ke saath kaise tai kiya",
    # 2358 ko — Athanasius Easter Letter 367 canon
    "Athanasius ui 367 CE Easter Letter ga wae twenty-seven New Testament books reul canonical ro listed haneun oldest document",
    # 2359 it (noise) — verify ordination date diocesan
    "un momento, devo verificare quella ordination date contro l'archivio diocesano prima di citarla",
    # 2360 es — Abu Hanifa Hanafi 8th century Kufa reasoned analogy
    "por qué Abu Hanifa en Kufa del siglo ocho privilegio reasoned analogy junto al Quran y hadith en Hanafi",
    # 2361 fr — al-Shafi'i Risala 820 four sources
    "comment la Risala d'al-Shafi'i vers 820 CE a classe Quran sunnah consensus et analogy comme les quatre sources",
    # 2362 de — Naqshbandi Baha al-Din silent dhikr
    "warum bevorzugt der Naqshbandi Sufi order um Baha al-Din Naqshband silent dhikr statt vokaler remembrance",
    # 2363 ja — Chishti Muin al-Din Delhi Sultanate
    "Chishti order wa Muin al-Din Chishti ni yotte late twelfth century ni South Asia he hakobare Delhi Sultanate ni dou",
    # 2364 vi — Reform Judaism 1885 Pittsburgh Platform
    "Pittsburgh Platform năm 1885 đã formalise Reform Judaism và thu hẹp halakhic observance ra sao",
    # 2365 pt — Conservative Judaism Schechter JTS 1902
    "como Conservative Judaism em torno de Solomon Schechter e do JTS desde 1902 se posiciona entre Reform e Orthodox",
    # 2366 zh — Second Vatican Council 1962 1965 vernacular
    "Second Vatican Council zai 1962 dao 1965 zenme yong vernacular worship tidai Tridentine Latin liturgy",
    # 2367 hi — Pentecostalism Azusa Street 1906 Seymour
    "Pentecostalism ki modern origin William J. Seymour ke 1906 Azusa Street revival Los Angeles se kaise judi hai",
    # 2368 ko — Gustavo Gutierrez A Theology of Liberation 1971
    "Gustavo Gutierrez ui 1971 A Theology of Liberation i wae Christian theology ga oppressed poor ui gwanjeom eseo sijakhaeyahanda",
    # 2369 it — Whitehead process theology 1929
    "come Alfred North Whitehead in Process and Reality del 1929 concepisce un Dio dipolare che co-evolve con la creazione",
    # 2370 es — Joseph Smith Book of Mormon 1829 gold plates
    "por qué Joseph Smith dicto el Book of Mormon en 1829 cerca de Palmyra reclamando translation de gold plates",
    # 2371 fr — Baha'u'llah Baghdad Ridvan 1863
    "quand Baha'u'llah a declare sa mission prophetique dans le Baghdad Garden of Ridvan fondant la Baha'i Faith",
    # 2372 de — Guru Gobind Singh Khalsa 1699 five Ks
    "wie gruendete Guru Gobind Singh 1699 in Anandpur Sahib die Khalsa und konsolidierte Sikh identity um die five Ks",
    # 2373 ja — Jain Digambara Svetambara schism first century
    "Jain schism no Digambara to Svetambara ga monastic nudity to women no liberation wo megutte itsu wakareta",
    # 2374 vi — State Shinto Meiji 1868 disestablished 1945
    "State Shinto được Meiji government dựng 1868 thành imperial civic cult rồi disestablished năm 1945 thế nào",
    # 2375 pt — Poetic Edda Codex Regius 13th century Norse
    "como o Poetic Edda preservado no Codex Regius do seculo treze ancora os ciclos mitologicos nordicos sobreviventes",
    # 2376 zh — Hesiod Theogony 700 BCE Chaos Zeus
    "Hesiod de Theogony yue 700 BCE chuangzuo, xushu cong Chaos dao Zeus de Greek divine succession",
    # 2377 hi — Mahabharata Vyasa Kurukshetra 400 BCE 400 CE
    "Mahabharata ko Vyasa ne 400 BCE se 400 CE ke beech mein Kurukshetra war ke ethical discourse mein kaise piroya",
    # 2378 ko — Popol Vuh Quiche Maya Hero Twins
    "Popol Vuh ga 18 segi cho Quiche Maya manuscript ro Mesoamerican Hero Twins changjo iyagi reul eotteoke jeonhae",
    # 2379 it — Ifa Yoruba babalawo 256 odu palm nuts
    "come la divinazione Ifa della tradizione babalawo Yoruba legge 256 odu con palm nuts o la catena opele",
    # 2380 es — Mircea Eliade Sacred and Profane 1957 hierophany
    "por qué The Sacred and the Profane de Mircea Eliade 1957 articula una phenomenology basada en hierophanies",
    # 2381 fr — Ninian Smart seven dimensions 1970s
    "comment les seven dimensions de Ninian Smart des annees 1970 ajoutent ritual narrative material et social aux definitions",
    # 2382 de — Pew Religious Landscape 2014 35000 Americans
    "wie hat die 2014 Pew Religious Landscape Study ueber 35000 Americans zu denominational affiliation und switching mapped",
    # 2383 ja (noise) — verify sutra recension citation
    "chotto matte, dono sutra no recension wo commentary ga cite shite iru ka kakunin shinakereba narimasen",
    # 2384 vi — Casanova Public Religions 1994 secularisation
    "Jose Casanova 1994 Public Religions in the Modern World đã revise secularisation thesis thành three claims như nào",
    # 2385 pt — Robert Orsi lived religion kitchens streets
    "como o lived religion approach de Robert Orsi estuda devotional practice em cozinhas ruas e shrines em vez de doctrine",
    # 2386 zh — Rudolf Otto Das Heilige 1917 mysterium tremendum
    "Rudolf Otto zai 1917 nian Das Heilige li zenme ba religious experience kuangding zai mysterium tremendum et fascinans",
    # 2387 hi — Wilfred Cantwell Smith 1962 faith cumulative tradition
    "Wilfred Cantwell Smith 1962 Meaning and End of Religion mein religion ko faith aur cumulative tradition se badla",
    # 2388 ko — Talal Asad Genealogies 1993 Western Christian
    "Talal Asad ui 1993 Genealogies of Religion i modern religion gaenyeom i Western Christian yeoksa ui sanmul iranago juseokhaeyo",
    # 2389 it — Theravada Pali Canon arhat Sri Lanka
    "perche il Theravada Buddhism conserva il Pali Canon e centra l'arhat ideal in Sri Lanka e Sud-est asiatico continentale",
    # 2390 es — Martin Luther 95 Theses Wittenberg 1517
    "por qué el posting de las Ninety-Five Theses por Martin Luther en Wittenberg 1517 suele marcar la Reformation",
    # 2391 fr — Great Schism 1054 filioque papal primacy
    "comment le Great Schism de 1054 a formalise le split entre Catholic et Eastern Orthodox sur filioque et papal primacy",
    # 2392 de — Dead Sea Scrolls Qumran 1947 1956
    "wie haben die Dead Sea Scrolls aus Qumran 1947 bis 1956 das Verstaendnis des Second Temple Judaism veraendert",
    # 2393 ja — Dogen Shobogenzo Soto shikantaza
    "Dogen no Shobogenzo ga thirteenth-century Japan de Soto Zen wo shikantaza no jissen ni kiseki suru houhou",
    # 2394 vi — Rinzai Eisai 1191 koan vs Soto
    "dòng Rinzai Zen được Eisai mang về Nhật 1191 ưa koan introspection thay vì quiet sitting của Soto ra sao",
    # 2395 pt — Maimonides Guide Perplexed 1190 thirteen principles
    "como o Guide for the Perplexed de Maimonides por volta de 1190 reconcilia Aristoteles com o Judaismo rabinico",
    # 2396 zh — Ibn Arabi Fusus al-Hikam 1229 wahdat al-wujud
    "Ibn Arabi 1229 nian de Fusus al-Hikam zenme chengwei wahdat al-wujud unity of being xuepai de lilun jigan",
    # 2397 hi — Pope Francis Laudato Si 2015 ecological
    "Pope Francis ki 2015 Laudato Si encyclical Catholic social teaching mein climate aur ecological obligation kaise jodti hai",
    # 2398 ko — Cheondogyo Son Byong-hi 1905 Donghak
    "Son Byong-hi ga 1905 nyeon Gwangmyeong-era canon euro Donghak movement eul Cheondogyo ro rebrand han banghyang",
    # 2399 it — J. Z. Smith Imagining Religion 1982 constructed
    "perche J. Z. Smith in Imagining Religion del 1982 sostiene che religion sia una categoria costruita dallo scholar",
]


def load_shared() -> list[dict]:
    with SHARED.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    for q in QUERIES:
        wc = len(q.split())
        if not (5 <= wc <= 20):
            raise ValueError(f"query word count {wc} out of 5..20: {q!r}")

    rows = load_shared()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(100):
            src = rows[SHARED_OFFSET + i]
            new_id = f"ret-{ID_OFFSET + i + 1:05d}"
            record = {
                "id": new_id,
                "source_id": src["id"],
                "query": QUERIES[i],
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
