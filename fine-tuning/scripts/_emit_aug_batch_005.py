"""One-off emitter for retrieval augmentation batch aug_005 (typo-kind queries).

Reads 300 pre-picked source rows from
`data/v2/retrieval/aug_sources/aug_005.jsonl` and emits one retrieval top-up
row per source with a short, plausibly-misspelled query. Output is written to
`data/v2/retrieval/aug_005.tmp.jsonl` with ids ret-03651..03950 taken from
each source row's `new_id` field.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "v2" / "retrieval" / "aug_sources" / "aug_005.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "aug_005.tmp.jsonl"

QUERY_KIND = "typo"

# One typo-kind query per source row (300 entries, one per new_id ret-03651..03950).
# Each query contains 1-3 realistic typos across content words and stays readable.
QUERIES: list[str] = [
    "pytest --pdb flag drops into debuger on frist failure not colection errors",  # 03651 pytest --pdb
    "hold on pullng up the flaem graph now",  # 03652 flame graph
    "esbuilds plguin api minmal svg-to-compnent loader 80 lines",  # 03653 esbuild plugin
    "type predicats on isOrder narow inbox hadnler no as-cast",  # 03654 type predicates
    "let me pul that thred for a momnet",  # 03655 pull the thread
    "board-gaem cafe outting draghts hackney 2026-04-08 wingspan unfinsihed",  # 03656 board-game cafe
    "mojos mlir-based compie pipline python-like code vendor kernls readable",  # 03657 Mojo MLIR
    "saliance network anterir insla dorsal anterior cingulte gates defalt mode",  # 03658 salience network
    "clor never sole carier of meanng status pils hue icon text labl",  # 03659 color not sole carrier
    "remnd me to re-run modal anlysis damping ratoi lands spec",  # 03660 modal analysis
    "every rfc carres one-line tldr at top reviwers frist paragrph",  # 03661 RFC tl;dr
    "coffe cold agan forgeting to drink while readng dif reviews",  # 03662 coffee cold
    "figur drawng group candid arts mondays improves magzine pose-boks home",  # 03663 figure drawing group
    "gve me a minte i nee to lok that up",  # 03664 give me a minute
    "chantng practce chithrst budhist monstery 2026-04-05 lay precpt summr",  # 03665 chanting practice
    "hold on the cta is at the dor again",  # 03666 cat at the door
    "endosymbitic theroy mitochndria chloropasts descnd from fre-living prokaryotes",  # 03667 endosymbiotic theory
    "resposes emit cache-contrl stale-while-revaldate 60 gets servs stale body",  # 03668 stale-while-revalidate
    "hold on the rebalnce is still chewng through plcement groups",  # 03669 rebalance placement groups
    "gravitymrk rentl aggrgator brother julin go hetzner bet plum guid vrbo sicly",  # 03670 Gravitymark aggregator
    "actully scrach that i ment the othr one",  # 03671 scratch that
    "kettel on thid floor diferent sound depnding how ful it is morning",  # 03672 kettle third floor
    "serach api comits to p99 latency 200 ms queris under ten terms",  # 03673 search API P99
    "chef brno tblisi promsied khinkli leson sprig 2026-04-20 confrim",  # 03674 khinkali lesson
    "bulk endpints acept partial-succes respnse body per-item stats typed bulkresult",  # 03675 bulk endpoints
    "vites plgin ecosystm ssr pwa mdx withot writng custm rollup api",  # 03676 Vite plugin ecosystem
    "neighbouhood assocation meetng scool hall to parsh room 2026-03-11 coffe parking",  # 03677 neighbourhood association
    "let me grb that nte and cirle back",  # 03678 grab that note
    "hmm gve me a momment",  # 03679 give me a moment
    "compst bin officaly half-ful of leaf mould 2025 autmn spred roses april",  # 03680 compost bin
    "lhcb collaboraton natre physcs 2022 lepton-flavur-uniersality b to k* decys",  # 03681 LHCb collaboration
    "bolts dremcast fork bots reliabl steam dek flycast core reicst retroarch",  # 03682 Bolt Dreamcast fork
    "fusion 360 genrated bracket stl bambu x1c 3d-prnt camra rig gopro 1/4-20",  # 03683 Fusion 360 bracket
    "somone kepps movng the spar keybord one dsk over each morning",  # 03684 moving spare keyboard
    "iupac nomenclture orgnic chemstry 1892 geneva congres 1993 recomendations jacs",  # 03685 IUPAC nomenclature
    "sure wil cirle bak aftr this",  # 03686 circle back
    "epidemology incdence measrs new dsease cases prevlnce proportn point",  # 03687 incidence vs prevalence
    "curiousity peked aranet4 home ofice co2 abve 1400 ppm levit core 600s purfier hrv",  # 03688 Aranet4 CO2
    "catalg fils live packages/i18n/catalgs locale po json migraton gettext lingjs",  # 03689 i18n catalog files
    "curry-howrd corespondence identifes proofs intutionistic logc trms typed lamda",  # 03690 Curry-Howard
    "run-clb brekfast after sundya long rn at mne since 2026-01-11 egs fritata seven",  # 03691 run club breakfast
    "antartic ice los dominted ocean-drivn thinng west antrctic shelfs arctic atmospheric",  # 03692 Antarctic ice loss
    "co-pilt cli sugestions gh copilt sugest save man-pag tar flags shel-native paste",  # 03693 gh copilot suggest
    "neighbr two dors down mr akadri chequr-patern lawn-mowng trck 31 yars",  # 03694 Mr Akadiri lawn trick
    "church-trng thesis evry efectively calclable functon computble truing machne",  # 03695 Church-Turing thesis
    "hmm refrees quey abut secnd cohomolgy clas cleaner counterexmple draft",  # 03696 second cohomology class
    "python 312 per-intepreter gil suport pep 684 paralel intrpreters",  # 03697 PEP 684 per-interpreter GIL
    "leos kindrgarten birthdy party 2026-02-15 clip n climb brokfield ten kids 175",  # 03698 Leo's birthday party
    "gve me a sec im tailng the lg",  # 03699 tailing the log
    "let me grb the measurng tap before we contnue",  # 03700 measuring tape
    "sur hapy to hlp with that",  # 03701 happy to help
    "gref after nanas dath 2026-02-11 pushed me lockd day one jornal six weks vaut public",  # 03702 Nana's death journal
    "timeshiter jet-lag plan 2026-06-10 sydny flght shift bedtme hour erlier four ngts",  # 03703 Timeshifter jet-lag
    "jedi-langage-servr stil right pck legcy pythn 27 pockts pyrigt refses",  # 03704 jedi-language-server
    "npx no lngr recmmended runer pnpm dlx and bunx cach more agresively engins",  # 03705 pnpm dlx bunx
    "sol lewits wal drawngs definned by writen instrctions drftsperson prescrbed ruls",  # 03706 Sol LeWitt wall drawings
    "typescript 55 isolatddeclaratons flag anotate public api retrn types declraton emit",  # 03707 TypeScript isolatedDeclarations
    "gve me a sec to grb coffe",  # 03708 grab coffee
    "ansel adamss zne systm divides tonl rnge eleven zns photograhers exposre",  # 03709 Zone System
    "paralel sequental scn only paid of past rougly 2 gb anlytics cluster workr startp",  # 03710 parallel sequential scan
    "focuswritr fullscren mode yeti mic spar room podcst-script studo",  # 03711 FocusWriter Yeti
    "wraping evry externl cal timouterror-then-falback decortor upstrems no p99 slos registry",  # 03712 timeout decorator
    "sory gve me a minte to thnk abut this",  # 03713 minute to think
    "rn out of coffe agan probably tme to ordr next bag",  # 03714 out of coffee
    "longitdinal cohor studies trace sme panel over yers british 1970 birh cohort canonical",  # 03715 British 1970 Birth Cohort
    "let me grb the exat publcation yer from my shlef",  # 03716 publication year
    "datdog watchdg surfcd mysql connection-pol saturaton before human dashbord anomly p95",  # 03717 Datadog Watchdog MySQL
    "doughnt econmics framwork explicity builds planetry boundries ceiling socil equty",  # 03718 doughnut economics
    "hng on let me pul that up",  # 03719 let me pull that up
    "utilty-ai scorer in companon systm weghts threts ammo health float tick csv",  # 03720 utility-AI scorer
    "dg came from kensngton shlter on 2021-04-03",  # 03721 Kensington shelter dog
    "dad birhday falls on 1961-09-12 he trns 65 thsi yar",  # 03722 dad's birthday
    "many lbs 2 project advnces methds pracices psycholgical scince 2018 28 replcations 60 labs",  # 03723 Many Labs 2
    "lucenes fst powred sugest compnent finte state transdcer autosugest 40 mb inste ad 300",  # 03724 Lucene FST suggest
    "okay scrolling thrgh my watchlst now",  # 03725 watchlist
    "ansble playbooks ran bare-metl botstrap proxmx hyprvisors terrform dhcp pxe agent",  # 03726 Ansible Proxmox bootstrap
    "ne sec i nedd to fnd that bechmark lg",  # 03727 benchmark log
    "roldown stil expermental stabl esm libraies chokes commonjs dynamc requir parked",  # 03728 Rolldown experimental
    "let me re-chck wheter that distace estmate uses cephid or trgb calbration befor cite",  # 03729 Cepheid TRGB calibration
    "le chatlers princple predicts equlibrium shifts pertrbed concentraton presure temperture",  # 03730 Le Chatelier's principle
    "ofice plnt by suth windo finaly flowred afer six months polte neglct eveyrone",  # 03731 office plant flowered
    "b3lyp hybrd functonal becke-88 exchnge lee-yang-par corelation gausian 1994 stphens",  # 03732 B3LYP functional
    "adopted pracice of leavng one positve obsrvation per reveiw psycholgical safty junior pr",  # 03733 positive observation review
    "coros traning-hub pce zons beat garmn autodetcted zones lockes threshld lacate test",  # 03734 Coros pace zones
    "torq pro pid librry 2017 ford fusn decded awd rear-diferential tempertur sensr fixd carly",  # 03735 Torque Pro PID 2017 Ford Fusion
    "clustr autoscaler stayd on statful node groups predictble asg shaps karpnter bin-packing",  # 03736 Cluster Autoscaler stateful
    "box-breathng patern 0640 trin four-four-four-four tn cycles longer holds lightheadness",  # 03737 box breathing 06:40 train
    "pyrights narowing isinstnce literl kind tag dispatchr rul engne no cast hot path",  # 03738 Pyright narrowing Literal
    "linx cgrops v2 unfies resorce contrlers single hirarchy systmd delegats slics",  # 03739 Linux cgroups v2
    "nag hamdi coices unerthed 1945 reshpd erly christin diverity gnstic gspel texts",  # 03740 Nag Hammadi codices
    "windsrf cascde mde handls long-horizon refctor beter cursr compser diff plan edits",  # 03741 Windsurf cascade mode
    "breakpint respcts pythonbrakpoint ipython embd drops ipythn insted of pdb",  # 03742 breakpoint() PYTHONBREAKPOINT
    "universl gramar posts inate langage faclty comon all neuotypical humns",  # 03743 Universal Grammar
    "polr h10 chest strp beat appl watch optcal sensor tempo runs wrist hr 30 bpm footstrke",  # 03744 Polar H10 chest strap
    "clickhse simd kerls avx-512 hsts doubld agregation throughpt funel qury avx2 falback",  # 03745 ClickHouse AVX-512
    "penicilin discovry 1928 flemng changed trajctory bacteral infecton treatmnt",  # 03746 Penicillin Fleming 1928
    "golangci-lnt runs tests thrugh test lintr only whn testifylnt checkr enabled",  # 03747 golangci-lint testifylint
    "typscripts nounchckedindexedaccess only checks indx signatres not tupl elemnt acces",  # 03748 noUncheckedIndexedAccess
    "ifa divnation yorba babalwo traditon west africa 256 odu signtures palm nts opele",  # 03749 Ifa divination Yoruba
    "gql trcked iso succesor to opencyphr and pgq team kept qury layer abstrcted migraton",  # 03750 GQL ISO successor
    "koi pnd fts eight adlt fsh at 1500 litrs one inch ten galons spredsheet",  # 03751 koi pond 1500 litres
    "lld stayd on appl silcon buildrs mld mach-o suport experimetal cutovr windo",  # 03752 lld Apple Silicon
    "2011 tohok earthqke nortestern japn 91 magntude fukshima daichi nuclr disastr",  # 03753 2011 Tohoku earthquake
    "configct targting rles resved simplr plan-tire gats no-code editr prodct-ops premim toggl",  # 03754 ConfigCat targeting rules
    "singl transferble vte irsh dail elctions 1922 vtes rnk candidats multi-membr prportional",  # 03755 STV Irish Dail
    "hold on warhouse is queing again might be the autoscler",  # 03756 warehouse queuing autoscaler
    "rernker tokenzer loded with use_fst true avoid 20x slodown on lng inpts",  # 03757 reranker tokenizer use_fast
    "dwnstairs caf strted sellng matcha cokie nobody on team descrbe without gigling",  # 03758 matcha cookie
    "hnge was how clra and i matchd on 2025-09-01 delted both profles mornng canal-walk",  # 03759 Hinge Clara match
    "hold on lt me pul up the fle",  # 03760 pull up the file
    "adovcates of degroth argue planed econmic contractin welthy econmies planetry boundries",  # 03761 degrowth advocates
    "hot-relod of shadr asets ships with regstry watch edit hlsl file-change rload render thred",  # 03762 shader hot-reload HLSL
    "sonta form orgnises clasical movment expsition devlopment recapitlation tonl retrn",  # 03763 sonata form
    "gref wve hit hard 2026-03-30 kitchn snk sat with elven mintes insigt timer no podcst",  # 03764 grief wave Insight Timer
    "hold on i ned a momet to lne that up",  # 03765 line that up
    "kept statc lunr indx as falbak ofline docs tarbals downlodable zip no javscript",  # 03766 static lunr index offline
    "atested artfact provnance github oidc tken cut signng key mangement to zro runnr",  # 03767 GitHub OIDC provenance
    "quartus prim lite staye on cyclne iv bord nextpnr intel suport not redy qurtus",  # 03768 Quartus Prime Lite Cyclone IV
    "gamecube contrler adaper finaly tlks to dolfin macos delfinvin drver arav mumbia cal",  # 03769 GameCube Dolphin Delfinovin
    "festinrs cogntive disonance explins atitude chnge tenson reduction confliting belifs",  # 03770 Festinger cognitive dissonance
    "sprse fieldsts via ?fields= cut mbile payld 60 percnt timelne endpint rejcts unkown",  # 03771 sparse fieldsets
    "tailwnd prefliht selctively overrden email-edtor workspce contentedtable native bulets scopd",  # 03772 Tailwind preflight email editor
    "git log -l calcluateTax tax.py puled full 9-yer chnge histry one functon rondig 2019",  # 03773 git log -L calculateTax
    "externlism abut mentl contnt hlds meaning depnds partly feartures outside thnkers hed",  # 03774 externalism mental content
    "hold on i wnat to dble chck that referance befor i cmit to it",  # 03775 double check reference
    "singl orane pushpn has outlsted evey othr pin shared corkboard thre yers runing",  # 03776 orange pushpin corkboard
    "neighbour upstars flat 7 marcelus plys tromone wednsday evenngs 2130 cut-of sinc 2025-08",  # 03777 Marcellus trombone neighbour
    "golden-fle testng works wel for snpshot-shapd outputs rots fast fromatting tweks reviwer",  # 03778 golden-file testing
    "gve me a sec i ned to fnd where i put my phne",  # 03779 find phone
    "adapive lightng integraton shifts mastr bedrm hue colr tempertur 4000k 7am 1900k 9pm mei",  # 03780 Adaptive Lighting Hue
    "curiosty won snpchat-style tasty ar app rendred ytam otolenghi swet potato chat sheet",  # 03781 Tasty AR Ottolenghi chaat
    "loign endpoits emit retry-after ratelimt heders evry faliure credental-stufing 429",  # 03782 login Retry-After RateLimit
    "homsicness pttern worst lte jnuary short dip noas birhdy may fine rst of yar",  # 03783 homesickness pattern
    "bluecat tutoring progrmme at harbourside pairs tutrs adult lerners six-wek cycle osman",  # 03784 Bluecoat tutoring Harbourside
    "estr eg hnt at pinefild cotage saturdy morning not sundy sinc 2018 churh photos",  # 03785 Easter egg hunt Pinefield
    "diald in rodecstr pro 2 locl history podcsting side projet basemnt sundya eveings",  # 03786 Rodecaster Pro 2 history podcast
    "crnlift backnd wasmtime compield cld functons 6x fastr old lvm pth steady-stte 10 percnt",  # 03787 Cranelift wasmtime LLVM
    "let me reconsdr that fr a momnt",  # 03788 reconsider that
    "2026-04-13 twich drps campign onc human forsen two hours ublock oigin prerol firfox",  # 03789 Twitch Drops Once Human forsen
    "staged redlnd flt for sle 2026-03-15 puled vnyl rug hal blbs warm wite bakd bred",  # 03790 Redland flat staging
    "2026-04-08 pth of exle 2 legue lanch crshed in-game currncy exchange ruthles divne orbs",  # 03791 Path of Exile 2 league
    "remind me to pul appndix tabl frm that handbok chapter befor meeting tomrow",  # 03792 appendix table handbook
    "yom kipur 2025 observd ful 25-hour fst at kehlat or chadsh nelah shofr blst hrder",  # 03793 Yom Kippur Or Chadash
    "legcy vcl stayd on markting pags compute@edge scpd dynmic apis vcls hedr rewrits a/b",  # 03794 Legacy VCL Compute@Edge
    "sory im stil catching up on the quiestion",  # 03795 catching up question
    "asimilation versus integraton convrsation papa manla dinner 2025-12-23 berln-germn adoptn",  # 03796 assimilation vs integration Papa
    "frst drving lson aunt preetis 17 year old 2026-04-05 red drving schol prep mya",  # 03797 Aunt Preeti driving lesson
    "decded fmri kamitnis grup reconstrcts percieved imgs voxel pattrns linar decodrs stmuli",  # 03798 Decoded fMRI Kamitani
    "puled 311 complant csv boston socrta open-dta portl city-councl comment dorchstr pothle",  # 03799 Boston 311 Socrata Dorchester
    "hn dynsty ruled chna from 202 bce to 220 ce consolidting burecratic state east asin",  # 03800 Han dynasty
    "atuin shel histry synk mde ctrl-r spn mahines end-to-end encrypton servr blbs",  # 03801 atuin shell history sync
    "gref since grampas funrl hits hardst thursdya mornngs cruse dop-in st marks pattrn",  # 03802 Cruse grief drop-in St Mark's
    "swftdata under evalaton featre flg prod cor data stck migraton clodkit miring maturng",  # 03803 SwiftData Core Data CloudKit
    "vacinaton coverge metrcs report doses administred eligible popultion herd mesles",  # 03804 vaccination coverage measles
    "craigs intercoption acunt loctes conscus bodly awareness inslar cortx visceral afernts",  # 03805 Craig interoception insular cortex
    "cros-compling to arm macs from linx ci right targt triple clng arm64-apple-darwin rst",  # 03806 cross-compile ARM Macs clang
    "lins torvlds io_uring patches lnded redpnda hot pth brokr rolld kernel 61 2026-02-28 batched",  # 03807 io_uring Redpanda kernel 6.1
    "cros-encodr rernking on tp of bm25 bet dense singl-vector retreival faq benchmrk latenc",  # 03808 cross-encoder FAQ BM25
    "buildroot stil prduces tny recovry initramfs 14 mb iamge botts fild-servc shel eight scnds",  # 03809 Buildroot initramfs recovery
    "pth trversal gurd dowloads route joins base dir pathlib resolve descndant noramlpath windws",  # 03810 path traversal pathlib resolve
    "eva hess proces-based sclptures used latx fibergls cheesecloth material fragilty imprmanence",  # 03811 Eva Hesse latex fibreglass
    "saturdya caligaphy cls at drnk shop and do teachs coperplate obliqe holdrs",  # 03812 Saturday calligraphy class
    "ne momnt let me grb my hedphones",  # 03813 grab headphones
    "hold on i ned to mrk my plac befor i lse the pag",  # 03814 mark my place
    "let me chck wheter that protcol amndment was flied befor or aftr interim anlysis",  # 03815 protocol amendment interim analysis
    "godels frst incomplteness therm implies sufficntly expresive consistnt systm undcidable",  # 03816 Godel's first incompleteness
    "hold tght i ned to pul up event catlog entry befor quting the fcal dpth",  # 03817 event catalog focal depth
    "i wil pt this don in a secnd prmise",  # 03818 put this down
    "solvng exrcises sipsrs theroy of cmputation fstr pumpng lema notes taged obsdian foler",  # 03819 Sipser Theory of Computation
    "recal is hedline retrieval metrc for rag pipline precison fixd llm rernker retrivr recall@50",  # 03820 RAG recall@50
    "permafrst carbn feedbck could releas hundrds gigatones co2 methane frzn orgnic matr arctic",  # 03821 permafrost carbon feedback
    "grmms law describs sysemtic consnant shifts seprated proto-germnic from proto-indo-europn",  # 03822 Grimm's Law
    "gaia mison launchd by esa 2013 replces hipparcs defntive astromtric suvey parlaxes milky way",  # 03823 Gaia mission ESA
    "lunchdarkly imprvs rails flipper at our scale streamng sdk cuts redis round-trip 50 rps 500",  # 03824 LaunchDarkly Rails flipper
    "curiosty drov 2026-02-22 experment pairng leica m11 with voighlander 35 nokton ii aperture q3",  # 03825 Leica M11 Voigtländer Nokton
    "ofice cofee machne now hises singl b-flat whenvr stam wnd runs dry",  # 03826 coffee machine B-flat
    "care-hme contrct oakrdge 1420 wek singl en-sute rom continuing-helthcare ccg outstandig",  # 03827 Oakridge care-home CCG
    "umbrela lablity policy chbb wnt live 2026-03-05 2 milion covrg prmium 410 hom auto bundld",  # 03828 umbrella liability Chubb
    "kdb+ kept high-frequncy tradng desk nansecond tck store q syntx colmnar mem-mapd tsdb latency",  # 03829 Kdb+ HFT tick store
    "nodejs workr threds shar memry via sharedaraybufer not via strctured clne norml objets",  # 03830 Node worker threads SharedArrayBuffer
    "hmm whre did i leve that bokmark",  # 03831 left bookmark
    "first impresion morningsde queiter than brochre 23 bus evry eght minutes banfield bakery",  # 03832 Morningside first impression
    "hering tst amplifon 2025-11-14 mld high-frequncy loss rigt no devce retst yar",  # 03833 Amplifon hearing test
    "sectgo isued ev certicates checkout domin brwser ui green-bar histry trst b2b buyrs",  # 03834 Sectigo EV certs
    "ran atam-style evaluation on ingstion redisgn two scenaro workshps latency rsk throghput",  # 03835 ATAM ingestion redesign
    "miloga nghts at negrcha improv on beginer socls tngo west florcraft clener",  # 03836 Milonga Negracha Tango West
    "okay gve me a momnt to lok that up properly",  # 03837 look that up properly
    "pydntic v2 typeadpter validte bar dataclases wthout subclasing basmodel confg ldaer thrd",  # 03838 Pydantic v2 TypeAdapter
    "adjusted to portgese dnner hours hard way eating 1830 frst yar empty restaurnts 2100 lisbon",  # 03839 Portuguese dinner hours Lisbon
    "pytest-asynico strct mode forces explcit event_lop_policy fxtures catches loop lekage",  # 03840 pytest-asyncio strict mode
    "dtrce on ilumos host showd blck-devce queu depth blowup compaction strm app lgs",  # 03841 dtrace Illumos queue depth
    "that sonds like a resonable strting pont i thnk",  # 03842 reasonable starting point
    "amazn retrn windo gamed 2026-02-20 30-day dysn v15 camila prim studnt 60",  # 03843 Amazon return Dyson V15 Camilla
    "prquet dictonary encodng kicked on lw-cardnality country colmn compresed 11x plain snapy",  # 03844 Parquet dictionary encoding
    "il grab the transcrpt and cme back in five minites",  # 03845 grab transcript five minutes
    "ocen acidifcation rns same prton chmstry carbnate bufer atacks absorbed co2 lowers seawatr ph",  # 03846 ocean acidification
    "ive got the measrng tap somwhere in this pile of bxes gve me a minte",  # 03847 measuring tape boxes
    "mrs hydro ts1000 spectum dta showd 660nm pek aligned flower-trigger 2026-03-05 home asistant 12 hour",  # 03848 Mars Hydro TS1000
    "adlt neuroplaticity resrch extnds hebian learnng cortical remaping critcal periods clse",  # 03849 adult neuroplasticity Hebbian
    "sens enrgy montor main pnel basment dehmidifier burnng 180 kwh month mysa flor-heat retofit",  # 03850 Sense energy Mysa floor-heat
    "mms diagnsis memry asesment servic 2025-06-04 mixd dementa alzhemers vascular mmse 21/30 17/30",  # 03851 mum's dementia diagnosis MMSE
    "proto-indo-europan reconstrcted comon ancester lanugages iclandic bengli comparitve methd",  # 03852 Proto-Indo-European
    "somone lft half-emty bag of jely beans on ops dsk nobody admts to bringing thm",  # 03853 jelly beans ops desk
    "presure-tested stryd powr-pce modl against coros apx 2 pro pce 2026-02-22 hlf mrathon 11 sec",  # 03854 Stryd vs Coros Apex 2 Pro
    "mahyana budhism emrged frst centuries ce foregrunds bodhistva ideal nikya arhat gol",  # 03855 Mahayana Buddhism bodhisattva
    "ockams rzor prefr simpler hypthesis compting explnations ft dta eqully",  # 03856 Occam's razor
    "car-shar car-club membrship enterpris car club reneed 2026-01-20 60 year van-hre allotmnt",  # 03857 Enterprise Car Club allotment
    "culture-shck spke hit around mnth four nt wek one chrstmas 2024 alne lsbon shutrd shops",  # 03858 culture shock Lisbon Christmas 2024
    "disurptive inovation theroy imprves sstaining-innovation acunts ratonal resorce alocation incumbents",  # 03859 disruptive innovation theory
    "actully scrtch that i was thnking of a diferent wek",  # 03860 different week
    "atlantc meridnal overturning circlation or amoc shws proxy-basd weakning twenth centry",  # 03861 AMOC weakening
    "anual flu sht and shingls part-two dos boked at welsprng pharmcy 2026-04-28",  # 03862 flu shot shingles Wellspring
    "zig cros-compilaton tolchans drpped linx binry buid tme secnds libc matrx compilr",  # 03863 Zig cross-compilation
    "anway the alrt just cleard on its own",  # 03864 alert cleared
    "hmm jst ne momnt plse",  # 03865 one moment
    "the litle pper crne on standng dsk survivd anothr ofice move nobdy expctd",  # 03866 paper crane desk
    "flag ths questn for strutural revew meetng thursdya afternon not mndy stndup",  # 03867 structural review meeting Thursday
    "libfuzzr corps pruning -merge=1 shrnk parsr sed bank 12k to 3k inputs coverge fronters",  # 03868 libFuzzer -merge=1
    "conservtive judasim crystlised solmn schechr jewsh theolgcal semnary 1902 reform orthdx",  # 03869 Conservative Judaism Schechter
    "let me reread the methd sectin once mre befor i compare the efect sizs",  # 03870 method section effect sizes
    "sapir-whorf hyphthesis clims gramatical catgories shap habtual thought strng readng abndoned",  # 03871 Sapir-Whorf hypothesis
    "1997-1998 el nno clased as super enso evnt pasific rainfal 34 billon usd gobal damge",  # 03872 1997 El Nino
    "let me re-chck latst ar6 pge numbrs befor i qote them",  # 03873 AR6 page numbers
    "gam theroy suplies formal backbne auctin desgn matchng markts industrial organisatn",  # 03874 game theory auction design
    "autotrder savd-serch for 2023 modl 3 long rang under 32 thosand dolars crigslist pythn 2026-02-18",  # 03875 Autotrader Model 3 Craigslist
    "git worktres let you chck out multple branchs simultanously sharng singl repo objet stre",  # 03876 git worktrees
    "daily shutdwn phrse literaly said alod schdule shutdwn complet tirck deep wrk after-hrs spirl",  # 03877 daily shutdown phrase Deep Work
    "sparking furmnt from tokja on tsting flght outshne evry champgne i brougt hme lst year",  # 03878 sparkling Furmint Tokaj
    "delta trned git pgr into sytax-higlighted side-by-side vew two-lne config gitconfig core.pager",  # 03879 delta git pager syntax
    "beir benchmrk expsed domin gp on dense retrivr recal on fiqa drped 18 pts vs msmarco tuned swp",  # 03880 BEIR FiQA MSMARCO
    "gve me one momnt i nee to dble-chck the sorce",  # 03881 double-check source
    "sonk ahrnss hw to take smrt notes reshapd atomc-note practc 2026-01-18 literture-note permnent",  # 03882 Ahrens Smart Notes
    "tsted githb copilt workspce on rel bug corect pln pach miss two cal sts cody pcked up",  # 03883 GitHub Copilot Workspace vs Cody
    "stylelnt stil bets biome for css-specfic ruls run scnd lint pas untl biomes cs coverge",  # 03884 Stylelint vs Biome CSS
    "cst per resolvd tckt is the busnes metrc lnfuse dshbord divdes daly llm spend suport tcket",  # 03885 LangFuse cost per ticket
    "wait i ned to rechk wheter scaling-law fit used tkens or trining steps on that axs",  # 03886 scaling law tokens vs steps
    "chshti ordr caried into suth asia muin al-din chshti lte twelth centry sufi dlhi sultnate",  # 03887 Chishti Sufi Delhi Sultanate
    "hold on pullng up the playbak lg now",  # 03888 pulling up playback log
    "weavite hybrd bm25 + vectr qury returnd clener top-10 resutls than milvs intrnal evl set serch",  # 03889 Weaviate vs Milvus hybrid
    "let me dble-check wheter that isue of journlism studis is in open-acces tranche befor link",  # 03890 Journalism Studies open access
    "hortskech 2026 succsion plan overlaps with neversnk farms crop mp salnova lettce bed widts",  # 03891 Hortisketch Neversink Salanova
    "swtiched cpython buids prf runs no-gil preiw singl-proces scaling gc tunng tabl",  # 03892 CPython no-GIL preview
    "japnese joinry bench i buit with only hnd tols imprves on dwel-and-glu one frm 2021",  # 03893 Japanese joinery bench
    "typscript projct refrences paid of 14-pckage monrepo tsc --buld only recompils dirty subgraph",  # 03894 TypeScript project references monorepo
    "gve me a tck the rernk batch is queud",  # 03895 rerank batch queued
    "my stpdad ron buils birdhoses in garge on saturdys blu jays tok one lst sprng",  # 03896 stepdad Ron birdhouses
    "post-funrl tea at the anchor 2025-11-22 drew 84 peple cusins tble 1730 lngr than dad pub",  # 03897 Anchor post-funeral tea
    "lichss plus aimchess dashbord made obvios i lse mst gams to tme pressre midleame",  # 03898 Lichess Aimchess middlegame
    "anway whre was i befor the ketle bolied",  # 03899 where was I kettle
    "kotln androd uses standrd res/vlues-es/strings xml layout qunty strings plurals tag cldr",  # 03900 Kotlin Android strings.xml plurals
    "new eyglass prescripton from dr hofman 2026-03-24 -3.75 lft -4.00 right blu-light coatng",  # 03901 Dr Hoffman eyeglass prescription
    "growvg gardn planr caught brassca-famly rotaton violaton in 2026 pln obsidan bed mp",  # 03902 GrowVeg brassica rotation
    "nanis karva chauh fast breks after monrise watr from silvr lota wil nt use stel thermos",  # 03903 Nani Karva Chauth silver lota
    "tvrsky and khneman prospct theroy loses lom twice as large as equivlent gains rsky chice",  # 03904 prospect theory Tversky Kahneman
    "invntiones mathmticae lanched sprngr 1966 flagship europan vnue pur mathmatics",  # 03905 Inventiones Mathematicae
    "prkng permt zne c at 14 marlw avnue reneed 2026-03-01 135 yar two vhicles vistor 20 day-pases",  # 03906 parking permit Marlow Avenue Zone C
    "hardy-weinberg equilbrium popultion genetcs hlds no selecton mutation migraton drift mating",  # 03907 Hardy-Weinberg equilibrium
    "avro unon typs with nul wer scema idom optinal filds protobuf fans unlarn implict-defalt proto3",  # 03908 Avro union types Protobuf
    "cnfirmed roon arc streams nuclus librry over talscale to rentl flt lsbon no routr port-forwrding",  # 03909 Roon ARC Tailscale Lisbon
    "hng on refrshing the conole",  # 03910 refreshing console
    "ramsy theroy clims sufficently large strctures mst contain ordrd substrctures any fxed size",  # 03911 Ramsey theory
    "origmi dragn from robrt lang bok tok four hours ate two sheets of kami papr",  # 03912 Robert Lang origami dragon
    "ne secnd il grb the clpboard frm the car",  # 03913 clipboard from car
    "thrmos on kitchn shlf stil keps cofee ht for exatly six hours forty mintes",  # 03914 thermos six hours forty minutes
    "alrght movng on to the nxt item on the lst",  # 03915 next item list
    "rtx 5060 requires cda 128 instal torch with --indx-url downlod.pytrch.org/whl/cu128",  # 03916 RTX 5060 CUDA 12.8
    "hold on i ned to grb a glss of watr",  # 03917 glass of water
    "excitment spiked whn 2026-04-04 sigur ros annoncement hit bandsntown kngs theatre thre minutes",  # 03918 Sigur Ros Bandsintown Kings Theatre
    "let me pul up the refrnce befor i go furter",  # 03919 pull up reference
    "gve me a sec il flsh the edg cach",  # 03920 flush edge cache
    "andre joyls 2008 theroy of quasi-catgories simplcial hompy thery adopted lurie infinity",  # 03921 Joyal quasi-categories Lurie
    "hmm i shoud rechck whch brodmn ara coresponds to that coordnate",  # 03922 Brodmann area coordinate
    "evry custm icn buton carres aria-lebel only child is svg storybok a11y addn authr tme",  # 03923 aria-label icon button Storybook
    "let me chil the glases frst befor we pr",  # 03924 chill glasses before pour
    "let me tke a quck lok and gt bak to you",  # 03925 quick look get back
    "daily ritul at 0640 kettl on hugo out bak dor mchis wt sachet 10 mintes trning brekfast",  # 03926 06:40 daily ritual Hugo Mochi
    "hold up my ketle is boling",  # 03927 kettle boiling
    "jke nw aprtment lsbon spar rom rady sketchd visit for septmber",  # 03928 Jake's apartment Lisbon September
    "schdinger equaton gverns tme evoluton nonrlativistic wavefuntion for a quntum systm",  # 03929 Schrodinger's equation
    "thundrstorm lst nght knockd out porch ligt blb somehow the wfi held all the way throgh",  # 03930 thunderstorm porch light wifi
    "remnd me to pik up another bag of rce for the week befor paydy runing lw",  # 03931 rice bag payday
    "grcean mxims underpn much pragmatc analyss of impliature neo-gricean relvance-theroetic rivls",  # 03932 Gricean maxims
    "let me pt the ketle on befor we strt",  # 03933 kettle on before start
    "hng on draning the consmer",  # 03934 draining consumer
    "frend-ntwork shrnk aftr 2025 mve brstol to lndon setled fur kept-clos thre drfted two recnnected",  # 03935 Bristol to London friend network
    "akutaga prze gven twice yearly japn 1935 cheif gteway award emerg literry fiction japnese",  # 03936 Akutagawa Prize
    "stdios loby fsh tnk sprang slow lek someone drew chalk outlne of pudle each mornng",  # 03937 studio lobby fish tank leak
    "cpythons adptive intrpreter pep 659 specalised hot atribute-access bytcode numerc loops",  # 03938 CPython PEP 659 adaptive
    "oh wait i ned to pul up the statment pdf frst",  # 03939 statement PDF
    "thredpoolexectuor fixd cap 32 bks reprt renderr bumpng max_worers hgher shiftd botlneck db pool",  # 03940 ThreadPoolExecutor report renderer
    "hold on the dshboard is stil lodng pnels",  # 03941 dashboard loading panels
    "goig bak to manla three weks 2025-12 rst my taglog ttia celia berlin vowels ng sonds",  # 03942 Tagalog reset Manila Tita Celia
    "mod lg in dylio shows sven straigt low-mod days 2026-03-19 thrugh 2026-03-25 wrk revw trgger",  # 03943 Daylio mood log work review
    "honstly i migt jst grb anothr cup of cofee frst",  # 03944 another cup of coffee
    "csmic microwve bakground tempertre sts at 2725 kelvin flcttuations one prt hundrd thousnd",  # 03945 CMB temperature 2.725 kelvin
    "gve me a secnd to flp the pag",  # 03946 flip the page
    "cap theorm mkes impossibilty claim distrbuted store consistecy availibility partion tolernce",  # 03947 CAP theorem
    "coffe machne in the kitchn is back to beping at random intervls agan",  # 03948 coffee machine beeping
    "dendrochronlogy calibrts radicarbon dats cross-matchng tre-ring sequnces twelv thusnd yars eurpean oak",  # 03949 dendrochronology radiocarbon
    "actully leve thos two togther thy wer sitng nxt to each othr befor",  # 03950 leave those two together
]


def _load_sources() -> list[dict]:
    with SOURCES.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def emit() -> int:
    if len(QUERIES) != 300:
        raise ValueError(f"expected 300 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 300:
        raise ValueError(f"expected 300 source rows, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (4 <= word_count <= 18):
                raise ValueError(f"query {i} has {word_count} words, out of 4-18 range: {query!r}")
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
