"""One-off emitter for retrieval aug batch-006 (typo-kind queries).

Reads 200 source rows from `data/v2/retrieval/aug_sources/aug_006.jsonl`
and emits one retrieval top-up row per source with a short,
plausibly-misspelled query. Output is written to
`data/v2/retrieval/aug_006.tmp.jsonl` with ids ret-03951..ret-04150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_006.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_006.tmp.jsonl"

QUERY_KIND = "typo"

# One typo-kind query per source row (200 entries, 1-3 realistic typos each).
QUERIES: list[str] = [
    "power et al 2022 grokking papr from openai delayd generalisaton",  # 3951 grokking
    "korsgaards sorces of normativty 1996 constructvist kantan ethics",  # 3952 korsgaard
    "wienberg 1967 physial review leters model of leptns higgs",  # 3953 weinberg
    "consort statment jama 1996 revsed 2010 25-item checklst flow diagam",  # 3954 consort
    "podcst learnng stak 2026 q2 philosphy no gaps ezra klien",  # 3955 podcast stack
    "clinicaltrials gov us natinal library medcine 2000 icmje registy",  # 3956 clinicaltrials
    "fruit tre prunng schedlue taped inisde shed dor apples febuary",  # 3957 pruning
    "heck reation 1972 journl organic chem palladum aryl halids alkens",  # 3958 heck
    "ibm carbon desgin system grid brakepoints tokens file tailwnd scrns",  # 3959 carbon
    "mond milgrom 1983 apj modifes newtonan dynamcs low accelertions",  # 3960 MOND
    "mums medcation list donepzil memantne amlodpine atorvstatin gp revew",  # 3961 meds
    "ginzburgs chese and the worms 1976 sixteenth centur miller microhistry",  # 3962 ginzburg
    "fanons wrethced of the earth 1961 anti-colonal revoluton theroy",  # 3963 fanon
    "wai-aria 1.2 spec plus authorng pratices guide apg componnt docs",  # 3964 ARIA
    "borad-game night diatery cheatsheat dani gluen free theo walnts iris",  # 3965 cheat sheet
    "ibn arabis fusus al-hikam 1229 wahdat al-wujd sufi metaphsics",  # 3966 ibn arabi
    "illutrisTNG projet magnetohydrodynmics overcoled disk galxy clours",  # 3967 illustris
    "glasersflds radical contructivsm 1990s lerners activly constuct",  # 3968 glasersfeld
    "househld altar southest alcve christ pantocrator bewax candl grandma rosa",  # 3969 altar
    "eliades sacred and the profne 1957 phenomenolgy religon hierphanies",  # 3970 eliade
    "letrs from granpa dad savd navy yers 1953 to 1957",  # 3971 letters
    "data journlism handbok oreily 2012 eurpean journalism centr methds",  # 3972 data journalism
    "enloes bananas beches and bass 1989 genderd labor internatinal politcs",  # 3973 enloe
    "comon sense meida revw page sister noor nephw dara ipad aps",  # 3974 common sense
    "incose systms engneering handbok intrnational councl 1998 practce",  # 3975 incose
    "barrngton mores social orgns dictatorsip and democrcy 1966 agarian",  # 3976 moore
    "simon levn 1992 macartur award pattern and scle in ecolgy",  # 3977 levin
    "shmuras 1971 book introductn to arithmtic theroy automrphic functons princton",  # 3978 shimura
    "hartshones algebaric geomery springer 1977 chaptr iii shaf cohomology",  # 3979 hartshorne
    "money guy show finacial order of oprations 2026 savngs waterfal hsa",  # 3980 money guy
    "carl schmits politcal theolgy 1922 sovereinty descison on the exceptin",  # 3981 schmitt
    "geotraces progrm 2010 maps trce elemnts isotops ocean basns",  # 3982 geotraces
    "cambrige handbok of computng eduction pinnd in zotro cogntive load",  # 3983 cambridge handbook
    "hendrik bodes 1940 bell systm technial journl bod plot frequncy",  # 3984 bode
    "preformance review priya 2025-12-15 metng heavy calendr deep wrok",  # 3985 perf review
    "kahnemns thinkng fst and slw 2011 sytem 1 sytem 2 cognton",  # 3986 kahneman
    "sidey tarows power in movment 1994 contentus politcs opportuniy structre",  # 3987 tarrow
    "tao and vu 2010 universlity resuts rndom matrces acta mathmatica",  # 3988 tao vu
    "mackies ethcs inventng rigt and wrog 1977 mroal erorr theroy",  # 3989 mackie
    "tilmans resource-ratoi hypothsis 1982 lotka volterra r-star coexistnce",  # 3990 tilman
    "mcluhans undertanding meida 1964 medum is the mesage medum theroy",  # 3991 mcluhan
    "home asistant energy dashbord canonical refernce solar heat pump payback",  # 3992 HA energy
    "shanons 1949 prceedings ire paper sampling thorem nyquist digtal signl",  # 3993 shannon
    "currry-howard corespondnce design dcuo typed pipline proof of state transiton",  # 3994 curry howard
    "vygotskys thouht and langauge 1934 sociocultural devlopment stag theries",  # 3995 vygotsky
    "parish smal group mnday nights 31 laurel close nt wrigt simply christan",  # 3996 small group
    "morgan and shanahan 1999 meta-analyis cultivation theroy gerbner demogrphics",  # 3997 morgan shanahan
    "pragmatc programer broken windw principl pr revew nits trival cleanps",  # 3998 pragmatic
    "snoball erth hypothsis hofman schrag 1998 cap carbontes cryogenian",  # 3999 snowball earth
    "lewis et al retrevial augmentd generaton neurips 2020 dense retriver seq2seq",  # 4000 RAG
    "rudolph ottos das heilge 1917 mystrium tremenduom fascinans numinus",  # 4001 otto
    "2014 pew religius landscape study 35000 amercans denomnational afilliation",  # 4002 pew
    "slep hygene ruls from cbti bed only fixd wake no clck-watching",  # 4003 CBTi
    "shafer-landus moral reaism defence 2003 debunkng non-naturlist stance indpendent",  # 4004 shafer-landau
    "jane lubchencos rocy intertdal experments new england 1970s herbivre algl",  # 4005 lubchenco
    "corotine context swiching python asyncio evnt loop 200 ns budet callbck",  # 4006 asyncio
    "mr money mustche 4 prcent rule pst projecton lab savngs rte 55",  # 4007 MMM
    "bird stewart lightfoot transprt phenomna 1960 momentm heat mass chemcal eng",  # 4008 BSL
    "pontryagins maxmum principl 1956 sovit doklady optmal contrl dynmic systms",  # 4009 pontryagin
    "human conectome projet washingtn univerity 2010 funcional mri thousnd adlts",  # 4010 HCP
    "powrs ngos as newsmkers colubia press 2018 humanitran organsations foregn corespondnt",  # 4011 powers
    "comute chaged moved offce rosemnt march 52 minte train 40 min drve",  # 4012 commute
    "bostoms superintelgence 2014 existntial risk unalinged agi controll value lodaing",  # 4013 bostrom
    "foots problm of abrtion doctrne of doble efect 1967 oxford revew trolly",  # 4014 foot
    "tea cremony host hirko in uji matca sorce 2026-03-02 two tns",  # 4015 hiroko
    "mrc crash-2 trail lancet 2010 tranxamic acd trama patiens blleding",  # 4016 crash-2
    "kydland prescot 1977 ruls rather than discreton tme inconsistncy centrl bnk",  # 4017 kydland
    "cb500f 16-ltire tnk fll log smal notebok glvebox 58 mpg 1200 mles",  # 4018 CB500F
    "lewellyns bramle bush 1930 amercan legl realsm situaton-sens common law",  # 4019 llewellyn
    "strucalist naratology propp 1928 morpholgy folk tles genetes narative discorse 1972",  # 4020 structuralist
    "mintzbergs structrng of organzations 1979 machne bureacracy adhocrcy divisonalised",  # 4021 mintzberg
    "freuds 1900 interpretaton of drams vienna psychoanalsis unconcious wsh",  # 4022 freud
    "mnih et al deep q-netwrk papr natur 2015 q-lerning convolutonal atari pxels",  # 4023 DQN
    "kants grondwork of the metaphyscs of morls 1785 categrical imperatve",  # 4024 kant groundwork
    "donldson dunfe integratve socil contrcts theroy ties that bnd 1999 hypernrms",  # 4025 ISCT
    "failre-mde catlogue paymnts srvice downsteam mitigaton owner runboks rep",  # 4026 failure mode
    "shalahs 1978 classfication theroy north-holand first ordr theries stabilty",  # 4027 shelah
    "kne-to-hip strenth imbalnce physio it band flare-us sinle leg brides",  # 4028 physio
    "john hart elys democrcy and distrst 1980 procss-based judical revew",  # 4029 ely
    "ecologcal stoichometry sterner elser 2002 princton carbn nitrgen phospours food webs",  # 4030 stoichiometry
    "wrold justce projet rul of law indx 2010 140 jurisdctions eight factrs",  # 4031 WJP
    "airbnb welcme note templte notin hostng loft welcme dtch gests 2025-09",  # 4032 airbnb
    "tidyng approch mari kondo chaptr life-chaning magc",  # 4033 konmari
    "cyert and march behavoral theroy of the frim 1963 coalitons goals uncertanty",  # 4034 cyert march
    "zwickys 1933 helvetca physca acta dunke materi cma clustr galxy vlocity",  # 4035 zwicky
    "heckmans 1979 selectn corection sampl selecton bas paricipation outcme",  # 4036 heckman
    "benjmains wrk of art ag of mechancal reprodction 1935 artwrk aura",  # 4037 benjamin
    "bommasani et al 2021 stanfrd paper oportunities risks foundaton modls",  # 4038 bommasani
    "raft consnsus ppr diego ongaro ousteroth etc clustr desgn",  # 4039 raft
    "stuart halls encodng decodng esay 1973 cccs audiance domint negotated oppsitional",  # 4040 hall
    "theo no longr tokn buld opton style dictnary absorbed salesfrce 2022 migrtion guide",  # 4041 theo
    "thrifting habt thre shops saturdya loop crsis finsbury marys primros hil holoway",  # 4042 thrift
    "fritz habrs 1918 nobel prze citaton synthsis amonia from elemnts agricltural",  # 4043 haber
    "dogens shobgenzo thirtnth centuy japn sot zen shikantza just sitting",  # 4044 dogen
    "mary main judth solmon 1990 chaptr preschol years ainswrth disorganisd attachmnt",  # 4045 main solomon
    "atomc habts implementaton intenton templte rafaels sundya chore checkist aple remindrs",  # 4046 atomic habits
    "al-shafis risla 820 ce islmic legl theroy qurn sunah consesus analgy",  # 4047 al-shafi
    "htp/3 spec is rfc 9114 qpck hedaer compresion rfc 9204",  # 4048 HTTP/3
    "journl of fuid mechancs cambrige press geoge batchlor 1956 peer revewed fluid dynmics",  # 4049 JFM
    "womns helth initative trail 2002 combned hormone replacment therpy brest cancr",  # 4050 WHI
    "chickn piccta recipe bon apettite magaine november 2023 isue",  # 4051 piccata
    "alexandr wendts socil theroy of internatinal polics 1999 anarchy is what stats make",  # 4052 wendt
    "interntional coveant civil politcal rigts 1966 force 1976 humn rigts comittee",  # 4053 ICCPR
    "delibrate pratice chaptr peak anders ericson code revew sesions",  # 4054 peak
    "freedm blok profle calld deep work 9 to 12 weekdys reddt hackernws youtbe",  # 4055 freedom
    "poppers falsifability criteron 1959 logc of scientfic discvery unflsifiable",  # 4056 popper
    "ramn at menya saim sapporo refernce bowl jude evry mso broth",  # 4057 ramen
    "comunity gardn plot allnby felds bed 14 eigt sqare metrs dev thre-sistr",  # 4058 garden
    "iea net zro by 2050 roadmp 2021 sectral milstones 1.5c warmng",  # 4059 IEA
    "vacination schedle dr hamd fridge 12 mnth mmr 2025-11-03 pre-schol bostr leo",  # 4060 vaccination
    "steve reichs musc for 18 muscians 1976 phse pulse minmalism elevn chrd cycls",  # 4061 reich
    "paulngs nture of the chemcal bond 1939 cornel valnce bnd electronegativty resonnce",  # 4062 pauling
    "mark deuzes meida wrk polty 2007 jourlnalists occupatonal speces meida industres labr",  # 4063 deuze
    "jose casanvas public relgions modrn wrold 1994 securalisaton theis thre clams",  # 4064 casanova
    "aron becks 1967 depresion causes and treatmnt cognitve modl negtive schemas",  # 4065 beck
    "geroge c wiliams adaption and naturl selction 1966 gene level seleciton grup",  # 4066 williams
    "richrd mayrs cogntive theroy multmedia lerning 2001 twleve princiles dual channl",  # 4067 mayer
    "mochis liter setup two tryas hih sided ikea vargn worlds bst clumpng corn",  # 4068 mochi
    "john finnis naturl law and naturl rigts 1980 classcal sven basc gods flourshing",  # 4069 finnis
    "tuly fisher relaton 1977 astrnomy astrphysics spirl galxy lumnosity rotaton vlocity",  # 4070 tully fisher
    "coupels holidya calender 2026 two weks japn october four uk wekend breks",  # 4071 holiday
    "katz lazrsfelds persnal influnce 1955 two-stp flow modl hypodrmic needl mass",  # 4072 katz lazarsfeld
    "slep stdy st marys 2025-10-22 ruled ot apne delayd sleep phse",  # 4073 sleep study
    "posners atention framwork alrting orientng exectuive contrl netwroks neual",  # 4074 posner
    "anserni refernce toolkit reproducng bm25 baselns trec topcs 0.5 ndcg",  # 4075 anserini
    "beyondcrp-style acces corprate netwrk hostle internl dns mtls devce trst",  # 4076 beyondcorp
    "shely kagns limts of morlity 1989 cosequentialism agent-centrd optons constrants",  # 4077 kagan
    "angrst and krueger 1991 quartr of brth instrmnt returnes to schooling compulsry",  # 4078 angrist krueger
    "frstons fre-enrgy principl perception actin variatnal fre enrgy hirearchical",  # 4079 friston
    "helfat colegues dynmic capabilites understandng strategc chane 2007 operationlised",  # 4080 helfat
    "masoretc text tankh tiberan scribs seventh to tenth centures hebrew vocalistion",  # 4081 masoretic
    "britsh psychlogical sociey britsh jorunal psycology 1904 britsh clncial psycology",  # 4082 BPS
    "gary beckrs humn captial 1964 eduction trainng invsstment decions labor economcs",  # 4083 becker
    "milion womn stdy valeri beral 1996 uk milion wmn 50 brest cancr hormne",  # 4084 million women
    "hospce voluntr inducton st bedes 2026-01-22 safegurding manual handlng thre hors",  # 4085 hospice
    "1960 valdvia earthquke chle moment magntude 9.5 usgs cataloge intrumental",  # 4086 valdivia
    "von nemann morgnstern theroy of gmes econmic behvior 1944 expcted utilty coperative",  # 4087 vnm
    "supersymetry wess zumno 1974 nuclar physcs b bson frmionic partnr hirearchy",  # 4088 susy
    "kubrnetes cri stbale intrface kubelet runtme contanerd cri-o dockerd-shm",  # 4089 CRI
    "change of adress lst 23 organistions bnk hmrc dvla gp dentst subsciption",  # 4090 address change
    "fadev popv ghsts 1967 physcs letrs b unitariy non-abelan guage theroy",  # 4091 faddeev popov
    "compartive manifeso projet 1979 ian budg hand codes party platfroms left rigt",  # 4092 CMP
    "papers mindsotrms 1980 constructionsm shareble artfacts logo programg tradtion",  # 4093 papert
    "suprglue relesed 2019 wng et al replces saturted glue hardr languge tsks",  # 4094 superglue
    "i bnd ladr strted 2024-10-01 10000 yaer treasurydirct trache purchse date",  # 4095 I bond
    "waristn inventry check in 2026-04-11 90 minutes 47 phtos six scufs dishwshr",  # 4096 inventory
    "iee transctions on autmatic contrl 1956 liner systms robst contrl estmation",  # 4097 IEEE TAC
    "atl gawandes checklst philsophy pre-fligt chcks deploymnt pipline",  # 4098 gawande
    "gettxt legcy pythn web ui xgettex msgmrge msgft chck relese gte po fles",  # 4099 gettext
    "scylldb shrd per cre modl cassndra thred pool nvme sestar framwork reactr",  # 4100 scylla
    "dexerto artcle 2026-04-07 marvel rivls competitve bn wve chet engne easyantichet",  # 4101 dexerto
    "nih opn acces polcy peer revewed manuscrpts pubmd centrl 12 monts",  # 4102 NIH
    "schwarzschld 1916 papr exct vacum soluton einsten feild equtions nonrotating sphercal",  # 4103 schwarzschild
    "converss 1964 esay natrue of belif systms mas publcs consitutional ideologcal",  # 4104 converse
    "levitsy way competitve authoritarism 2010 hybrd regms uneven electons biniary",  # 4105 levitsky way
    "anthny downs econmic theroy of democrcy 1957 medain votr theoem spatal modl",  # 4106 downs
    "cochrne handbok chaptr 10 dichtomous outcmes inclded trials",  # 4107 cochrane
    "brce ackermns we the peopl foundatons 1991 dulist democrcy consttutional momnets",  # 4108 ackerman
    "going hme for chrstmas budet 2400 euros 2026 flihts gfts tita celia envlope",  # 4109 christmas
    "orgnization sciece 1990 infroms multidisciplnary micro macro organsational resarch",  # 4110 org science
    "amrtya sns ida of justce 2009 rawls transcndental institutonalism comprative",  # 4111 sen
    "olson et al 2022 inducton hads ppr anthrpic in-cotnext lerning cirucit transfrmers",  # 4112 olsson
    "pikettys captal in the twnety first centry 2014 retur on capial exceds grwth",  # 4113 piketty
    "sidey wintr 2003 stratgic managment journl dynmic capbilities operatng routnes",  # 4114 winter
    "coctail party hedcount cp 18 cot situtation 21:00 arival wve hal jam",  # 4115 cocktail
    "donghue v stvenson 1932 hose of lrds tort of neglignce atkins neigbor principl",  # 4116 donoghue
    "lefflers preponderance of pwer 1992 post revsionist cold wr trumn era natinal scurity",  # 4117 leffler
    "rorbert dahls polyrachy 1971 democrtic theroy contestaton inclsiveness abstact",  # 4118 dahl
    "pancke sundya famly tradion predats marriag decde linda batar maple syrp",  # 4119 pancake
    "knts critque of judgment aesthetc judgemnt disintersted plesure fre play faclties",  # 4120 kant judgment
    "wintr tyers nero michlin crossclimte 2 215/60 r17 swap 1 novmber 1 aprl",  # 4121 tyres
    "hck reactor sofware engineing programe on site intrview 2026-04-22 14:00 july cohrt",  # 4122 hack reactor
    "bennts indxing hypothsis 1990 journl comuncation us nws frams elit debte",  # 4123 bennett
    "hitchi airhme 3000 speced 8 kw afer het loss survey 6.4 kw utiliy romo",  # 4124 hitachi
    "lyapnovs 1892 doctoral diseration kharkv stabilty theroy nonliner contrl",  # 4125 lyapunov
    "comon law traditon bractons thirtenth centry treatse laws and custms englnd precdent",  # 4126 common law
    "alfrd chandler strategy and structre 1962 histrical thess organztional structre",  # 4127 chandler
    "sundya self-compasion brek kristn nefs thre stps momnt of sufering kind myslef",  # 4128 self-compassion
    "walzrs just and unjust wrs 1977 jst-war theroy moral equlity combatnts",  # 4129 walzer
    "eid al-ftr morning aunt rukhsanas 6:30 sher khurma dentd pot memorsied recipe",  # 4130 eid
    "alan conns noncommutative geomtry standard modl 1996 comunications mathmatical physcs spectral tripl",  # 4131 connes
    "fukyamas end of hstory and the lst mn 1992 liberl democrcy termnal ideologcal",  # 4132 fukuyama
    "nambu jona lasinio 1961 physcal revew dynamcal symetry brekaing chiral qcd",  # 4133 nambu
    "rul of 25 targt for cost-fi 1.1 milion at age 45 projecton spredsheet age 46",  # 4134 rule of 25
    "pulsr timing aras nanograv 2023 apj leters stochstic gravitationl wave smbh binres",  # 4135 pulsar
    "ahmd zewail femtosecnd spectrocopy caltch 1987 journl chemcal physcs nobl 1999",  # 4136 zewail
    "ipc ar6 workng grop i 2021 humn influnce climte systm uneuivocal",  # 4137 IPCC
    "kuhns strucutre of scientfic revoluions paradigm shfts vocabuary scientfic chane",  # 4138 kuhn
    "c elgans conectome whte colleges 1986 whle-animl wirng diagrm synptic resoluton",  # 4139 connectome
    "mncur olsns logc of colectve acton 1965 ltent grups publc gods selectve incntives",  # 4140 olson
    "vygotky zne of proxmal devlopment mnd in sociaty 1978 indpendnt asisted",  # 4141 vygotsky zpd
    "diabtes controll and compications tril nejm 1993 intensve insuln type 1",  # 4142 DCCT
    "koblbs experintial lerning 1984 fur stge cycl concret reflective abstract active",  # 4143 kolb
    "pfefr salncik externl contrl of organsations 1978 resorce dependnce theroy",  # 4144 pfeffer
    "drei monte frst abmeldung lisbn 2026-07 deregistraton befor i leve",  # 4145 abmeldung
    "parnt techer conferece brokside 2026-03-28 mayas readng handwrting pencl hgger",  # 4146 parent teacher
    "jensn and meckling 1976 journl financal economcs agncy theroy shrholder manger",  # 4147 jensen meckling
    "trcks fir progres as percenage 1.4 milion targt 62 perent 2026-03-31",  # 4148 fire tracking
    "banduras 1977 socil learnng theroy modeling self-eficacy behaviur chane",  # 4149 bandura
    "sharpless asymetric dihydroxylation jcs 1988 osmum cinchoa enantipure dils 2001 nobl",  # 4150 sharpless
]


def _load_sources() -> list[dict]:
    with SRC.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def emit() -> int:
    if len(QUERIES) != 200:
        raise ValueError(f"expected 200 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 200:
        raise ValueError(f"expected 200 source rows, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (5 <= word_count <= 15):
                raise ValueError(
                    f"query {i} has {word_count} words, out of 5-15 range: {query!r}"
                )
            row = {
                "id": src["new_id"],
                "source_id": src["source_id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
