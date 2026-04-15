"""One-off emitter for retrieval top-up batch-008 — typo query_kind.

Writes 100 rows to data/v2/retrieval/batch_008.tmp.jsonl with ids ret-00701..00800.
Each row targets shared rows 700..799 and supplies a typo-laden query (4-18 words,
1-3 typos per query) plus the source text as positive.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_008.tmp.jsonl"
ID_OFFSET = 700
SHARED_OFFSET = 700
QUERY_KIND = "typo"

# One typo query per shared row, aligned by index (offset 700..799).
QUERIES: list[str] = [
    # 700 tabletop RPG Orc's Nest Seb Mothership
    "whos runing the mothershp campaing for our frday rpg gruop",
    # 701 pintxos San Sebastian Calle 31 Agosto
    "witch pinxtos crawl near calle 31 beat my tastng menues",
    # 702 sleeper train Paris Venice
    "sleper train from pari to venic insted of flite",
    # 703 congee Yau Ma Tei Uncle Fung
    "early mornng congee cart yau ma tei uncel fung remembr order",
    # 704 shellfish allergy tom yum Chiang Mai EpiPen
    "shelfish allergy tom yum chang mai epipn on trps",
    # 705 Asador Etxebarri 2027-05-09
    "anniversry diner asadr etxebari booking may 2027",
    # 706 three-cube packing system
    "thre cube packng setup for week long cary on",
    # 707 natural wine Lyon Michelin bouchons
    "naturel wine bars in lyn prefred over michlin bouchns",
    # 708 passport Buenos Aires Iguazu
    "passprt loss buenos aries before iguzu flite embasy delay",
    # 709 Signora Rosa Bologna tortellini ragu
    "signora rosa bolgna cookng clas tortelini real rago",
    # 710 noise
    "doublechek the bookng refernce",
    # 711 riad Fes Marrakech
    "chose riad fs over rsort marakech narow aleys",
    # 712 jet-lag Seoul
    "jetlag reste trik from seul trip no nps daylite walk",
    # 713 Airbnb Rua do Almada Porto cortado
    "airbb above bakry rua do almda porto prefred over hotl",
    # 714 tipping Tokyo
    "tipng in tokio polte mes first nite coins insult",
    # 715 Menya Saimi Sapporo miso ramen
    "menya simi saporo miso ramn benchmarck bowl",
    # 716 Alaska Marine Highway Juneau Whittier
    "alska marin highway junau to wittier thre day leg",
    # 717 Moleskine orange cover carry-on
    "moleskne orng cover noteebook restaraunt log since 2019",
    # 718 no-carb Naples Da Michele pizza keto
    "no-carb expirement ended in napls da micele pizza keto",
    # 719 Caltrain SF Palo Alto
    "caltran prefred over rental car sanfrancisco palo alto corridr",
    # 720 Oaxacan mole Doña Eva
    "oxacan mole clas dona eva seven chiles toastng stags",
    # 721 Bangkok Doha Sydney stopover
    "swaped bankok stopver for doah transit on sidney flite",
    # 722 espresso 14:00 Rome
    "no espreso after 14:00 rule romn sleeples nite lesson",
    # 723 tagine Café Clock Chefchaouen
    "tagne at cafe clok chefchawen thre visits two yeras",
    # 724 Schengen visa London Croatia
    "schengn visa stamp lundon biomteric expirng croata hike",
    # 725 banh mi Hoi An Madam Khanh
    "prefres banh mee hoi an madm khanh cart over hotl bufet",
    # 726 packing cube 2016 rolled-bundle
    "pakng cube systm replced roled bundl methd from 2016 forum",
    # 727 cacao class Ubud Pak Wayan 2026-01-28
    "caco clas ubd pak wyan grindng on stne metate hard",
    # 728 dietary rule abroad
    "dietry rul abroad try weerdest thng once but not travl day",
    # 729 Furmint Tokaj Champagne
    "sparklng furmnt tokaj tastng flite beat champange last yer",
    # 730 Patagonia meniscus Mendoza 2025-11-08
    "droped patgonia hik after torn meniscs flew to mendza",
    # 731 Notion coffee shops Reykjavik
    "logng coffe shops by latitud in notoin after reykjavk trip",
    # 732 Bruno Tbilisi khinkali 2026-04-20
    "chef bruno tbilsi khinkli lessn sprng 2026-04-20 confrm",
    # 733 1998 Saint-Emilion Sam Bordeaux
    "1998 saint emlion sams parnts bordux refrence botle",
    # 734 noise map
    "hmm one momnt pulng up the mp",
    # 735 cash markets Mercado da Ribeira Lisbon
    "cash markets prefered mercdo da ribera saturdy stp lisbn",
    # 736 Tuscany Chianti Maremma 2026-06-01
    "tuscny trip spli chiant and maremma jun 2026 southrn surprse",
    # 737 shoes Vietnam trail runner sandal
    "sho rul vitnam one trial runer one sandl no loafrs",
    # 738 ferry Naxos Santorini catamaran
    "ferry naxs to santorin over high-speed catamran deck chars",
    # 739 sambuca Vulcano Antonio black-sand
    "sambca flite vulcnao antono black-snd beach hilight",
    # 740 50 countries Mongolia 2026-03-30 Ulaanbaatar
    "hit 50 cuntries mongoli visa march 2026 khorkg ulaanbatar",
    # 741 photograph dish overheads
    "photgrphing a dish takes under ten mintes two overhads one side",
    # 742 Trattoria Morgana cacio pepe Roscioli
    "trattoria morgna cacio e pep over carbnara at roscoili",
    # 743 souvenir policy Kyoto 2023
    "souvnir policy one edibl one photo prnt after kioto 2023",
    # 744 oysters Saint-Malo 2025-10-11
    "food poisning raw oystrs sant malo octber 2025 six mnths out",
    # 745 Istanbul Galata urfa biber
    "istnbul spic vendor galta bridg urfa biber lam jar",
    # 746 whisky Islay Speyside Aberlour 2025-08-15
    "whisky prefrnce shifed from ilay peat to speysde aberlur",
    # 747 neighbourhoods Madrid Lavapies Atocha
    "sleep in neighborhods not stations madrd lavapes over atoca hotl",
    # 748 cancelled Marrakech 2026-02-08 desert
    "canceled cookng schol marakech febr 2026 desrt overnite accdent",
    # 749 Vis Villefranche 2025 Croatian island
    "croatin islnd wek vs viefranche 2025 vs over villefrance repat",
    # 750 tea Hiroko Uji matcha 2026-03-02
    "tea cermony hirko ujii match soure two tns a yer",
    # 751 Noether's theorem
    "noethrs theorm links contnuous symmtry to consrved quntity",
    # 752 Griffiths Electrodynamics
    "grifths intro to electrdynamics standrd undergrd maxwll text",
    # 753 laser cooling ultracold
    "ultracld atoms prefer laser coolng over bufer gas coolng",
    # 754 loop quantum gravity
    "lop quantm gravty quantses spacetme geomtry not backgrund feild",
    # 755 CMB 2.725 K
    "cosmc microwve backgrund temp 2.725 kelvn fluctuations",
    # 756 EHT M87 2019-04-10
    "evnt horzon telscope first imge m87 suprmassive black hol april 2019",
    # 757 dark energy Type Ia CMB tension
    "drk energy surveys tensn typ ia supranova calibrtn vs cmb",
    # 758 Rubin rotation curves
    "rubns rotatin curve measurments spral galxies dark mater",
    # 759 IceCube TXS 0506+056 2018
    "iceube neutrno txs 0506 astrphysical surce 2018 confrm",
    # 760 noise pull reference
    "let me pul up the refrence before goin furthr",
    # 761 Bell test
    "bel tst expermnts violate locl-hiden-varaible bunds",
    # 762 NIST atomic clock UTC
    "atomc clok ensembl at nst keps utc 10^-16 stbility",
    # 763 Planck constant 2019 SI
    "planks constnt fixd at 6.62607015e-34 j-s 2019 si redfinition",
    # 764 Peebles Physical Cosmology
    "peeblss physcal cosmlogy friedmann lmaitre framewrk backbne",
    # 765 ICP-MS flame AA trace metals
    "lab prefrs inductvly coupld plasma mass spec over flme atomc absorbtion",
    # 766 Pauling Nature Chemical Bond
    "paulng natur of chemcal bnd hybridisatin and resnance",
    # 767 Suzuki Stille boron toxicity
    "suzki miaura croscoupling betr thn stile for pharmaseutical scle up",
    # 768 benzene Huckel aromaticity
    "benzne aromaticty relys on planr six pi electrn huckls rule",
    # 769 Bartlett xenon hexafluoroplatinate 1962
    "barletts 1962 xenn hexaflouroplatnate showd nobel gasses arent inrt",
    # 770 Le Chatelier
    "le chatlier princpl predcts equlibrium shft undr purturbation",
    # 771 BCA vs Bradford
    "protin quantfication now prefrs bca assy over bradfrd detrgent linerity",
    # 772 endosymbiotic
    "endosymboitic theroy mitchondria chloroplats decend from prokaryots engulffed",
    # 773 Watson Crick 1953 Franklin
    "watson and crik 1953 natur papr dna doule helx franklns data",
    # 774 Kimura neutral theory
    "kimurs neutrl theory claims most genteic variaton is selectvly nutral",
    # 775 PacBio Illumina long-read
    "lng read pacbo replced shrt read illumna for refrence assmbly",
    # 776 ecosystem services double counting
    "ecosstem servce valuton framewrks double-cont provisoning vs reglating",
    # 777 Keeling Mauna Loa 1958
    "keelngs muana loa co2 recrd startd 1958 modern co2 trajctory",
    # 778 ice-core vs tree-ring
    "modrn paleoclmte recons prefr ice-cor isotops over tre-ring widh",
    # 779 Wegener 1915 continental drift
    "wegners 1915 orgin of contnents proposd contnental drft befor seaflor evidnce",
    # 780 thermohaline North Atlantic freshwater
    "thermohline circulaton problms nrth atlntic sinkng weknes frshwter forcng",
    # 781 ocean acidification proton CO2
    "ocen acidfication proton chemstry absrbed co2 lowrs sewater ph",
    # 782 CHIRP radar Mars analog
    "chrp radr on esa misions replced fxed frequncy pulse for ice-sheat sondng mrs",
    # 783 Kepler's three laws
    "keplrs thre laws of planetry motin elipses equl areas period distanc",
    # 784 noise paper
    "hld on lemme grab the papr to confrm the figre",
    # 785 Kepler exoplanet transits
    "exoplnet transt photmetry kepler puhed dozns to thousnds of detctions",
    # 786 Schrodinger equation
    "schrdingrs equaton governs tme evoltion of nonrelativstic wavfunction",
    # 787 GROMACS vs AMBER membrane
    "grup prefrs gromcs over ambr for membrne md simultions",
    # 788 DFT wavefunction methods
    "densty functnl theorey replaced wavfunction methds for ground state propretes",
    # 789 fossil calibration molecular clocks
    "fosil calibrtion of molcular clks introduses large uncertanty on divrgence dats",
    # 790 CERN LHC 27km
    "cern lrge hadron colidr underground synchrtron 27 km supercondcting magnts",
    # 791 Bjerknes 1904 primitive equations
    "bjerkness 1904 papr framd weathr forcasting as inital valu problm",
    # 792 Richter vs moment magnitude
    "richter scle supersded by momnt magntude for larg earthqukes seismolgy",
    # 793 BAS 1985 ozone hole
    "brtish antartic survy detcted sprngtime ozne hole 1985 south pol",
    # 794 Hardy-Weinberg
    "hardy weinbrg equilbrium holds wth no selecton mutaton migraton drif",
    # 795 nanopore direct RNA cDNA
    "grup prefrs nanopre drect rna sequncing over cdna ilumina base modfications",
    # 796 LSST Rubin 2025-10-24
    "lsst vera rubn observtory lgacy survy start 2025-10-24",
    # 797 ATAC-seq DNase-seq
    "lab favrs atac seq over dnase seq for chromtin accssbility profling",
    # 798 Hawaiian hotspot 47 Myr bend
    "mantl plume modls strugle to explan hawaian hotspt bend 47 millon yr",
    # 799 IUPAC nomenclature
    "revewers expct iupac nomenclture for chemcal nams in primry lit",
]


def _load_positives() -> dict[int, str]:
    positives: dict[int, str] = {}
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            rid = row["id"]
            if not rid.startswith("shared-"):
                continue
            try:
                n = int(rid.split("-")[1])
            except (IndexError, ValueError):
                continue
            if SHARED_OFFSET <= n < SHARED_OFFSET + 100:
                positives[n] = row["text"]
    return positives


def emit() -> int:
    positives = _load_positives()
    missing = [SHARED_OFFSET + i for i in range(100) if (SHARED_OFFSET + i) not in positives]
    if missing:
        raise SystemExit(f"missing source rows: {missing[:5]}... ({len(missing)} total)")
    if len(QUERIES) != 100:
        raise SystemExit(f"QUERIES must have 100 entries, got {len(QUERIES)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(100):
            shared_n = SHARED_OFFSET + i
            row = {
                "id": f"ret-{ID_OFFSET + i + 1:05d}",
                "source_id": f"shared-{shared_n:05d}",
                "query": QUERIES[i],
                "positive": positives[shared_n],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
