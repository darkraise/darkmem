"""One-off emitter for retrieval top-up batch-020 (typo-kind queries).

Reads shared rows at 0-indexed line offsets 1900..1999 from
`data/v2/shared/shared.jsonl` and emits one retrieval top-up row per
source with a short, plausibly-misspelled query. Output is written to
`data/v2/retrieval/batch_020.tmp.jsonl` with ids ret-01901..02000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_020.tmp.jsonl"

ID_OFFSET = 1900
SHARED_OFFSET = 1900
QUERY_KIND = "typo"

# One typo-kind query per source row (100 entries, matching shared lines 1900..1999).
# Each query contains 1-3 realistic typos across content words and stays readable.
QUERIES: list[str] = [
    "esp32 s3 dual core firwmare pinned wifi stack to cor0 sensor loop cor1",  # 1901
    "esp idf replced arduino esp32 for telmetry firmware componet manager",  # 1902
    "rasbperry pi pico sdk paris freertos second cor usb cdc logging core 0",  # 1903
    "zehpyr rtos device tre overlays custm board pinmux vendor hal edits removd",  # 1904
    "embasy async rust on rp2040 replcaed bespoke coperative scheudler",  # 1905
    "rtic framwork prefered over bare metal interupts for priorty scheduling",  # 1906
    "nrf52840 won low powr telemtry design over stm32l0 efm32 ble satck",  # 1907
    "lorawan gatway moved from things netowrk to self hosted chripstack helium",  # 1908
    "mater over thred replced propertary zigbe lighting brdige apple tv",  # 1909
    "hold on lett me reflow taht jont",  # 1910
    "ble gatt profie design telemtry indicate onley charactristics notfy flood",  # 1911
    "mqtt topic hierachy reshufled to site device metric flat device id schme",  # 1912
    "opc ua replced raw modbus tcp produciton line typed adres space discovry",  # 1913
    "ota updat strategy moved to a b partitons with mcuboot auto roll back",  # 1914
    "u boot stayd on imx8 gatway corboot evalauted board suport not upstreem",  # 1915
    "jtag debuging with pemicro multlink unblocekd clok tree bug k22f swd",  # 1916
    "openocd with ft2232h adapter replced segger jlink fab bench licence counts",  # 1917
    "salae logic pro 16 caputred i2c gltch power sequener rise tiem sda 3.3v",  # 1918
    "dslogic plus took over everday caputres saleae shelfed dsview ran ofline",  # 1919
    "signal integrty check can bus msvo5074 differntial probe ringing termniation",  # 1920
    "kicad 8 replced altium new brakout board solder mask expanson jlcpcb",  # 1921
    "eagle retird after autodesk lisencing chnage legacy schemtics convrt kicad",  # 1922
    "jlcpcb handeled five off prototyp run half osh park qoute panelisaton",  # 1923
    "osh park still wins on purpel four layr boards fine line routng rf",  # 1924
    "smd reflwo on pcbit hot plate beat toster oven 0402 pasives thermocuple",  # 1925
    "controlo3 driven oven took ovr manul hot plate reflow lead fre profiles",  # 1926
    "yosys plus nextpnr synthsised ecp5 desing end to end lattice diamnd ip",  # 1927
    "quartus prime lite staid on cycone iv board nextpnr intel suport ntot ready",  # 1928
    "latice ecp5 evn dev baord drove frist verilator co sim harness waveforms",  # 1929
    "verilator 5 cycle accurate modles replced questasim nigtly regresion ci",  # 1930
    "risc v vector exntension 1.0 landd in soc desing convoluton inner loop third",  # 1931
    "tok os consdered for secure elment firwmare zepyhr driver catalog won",  # 1932
    "nordics nrf conect sdk wraps zephyr connectvity stacks mesh sample lighting",  # 1933
    "give me a minut to wigle the prob",  # 1934
    "stm32cubide droped for g4 motor board platfomio cmake fit bazel monrepo",  # 1935
    "px4 autopilt firwmare flashd pixhawk 6x survey dron uorb message bus",  # 1936
    "yocto projct built varicite imx8 image buildrot faster yocot sbom",  # 1937
    "buildrot stil prodcues tiny recovry initramfs 14 mb image boots eight seconds",  # 1938
    "can fd replced clasical can trailor harness 2mbs data phse diagnsotic window",  # 1939
    "tsn factry ethernt ring bonded latncy motion controler ptp grandmstr switch",  # 1940
    "zigbe pro retird from 2026 product lien mater over thred native smart home",  # 1941
    "litlefs replced spifs on esp32 prodct power fail safty smallr code fotprint",  # 1942
    "tinyusb drov composit cdc plus hid devce rp2040 vendor stack timng windws",  # 1943
    "segger emwin droped for lvgl hmi dsiplay flash fotprint fel 40 percent",  # 1944
    "protothredas powrd legacy avr firwmare msp430 port keeps them rust rewrit",  # 1945
    "nordic thingy 91 protoyped cellular iot node lte m nrf cloud provisoning",  # 1946
    "particl boron rejcted in favor nordic quectel bg95 bom cost long term",  # 1947
    "seger systemview traced freerots task churn priorty invrsion spi isr sensor",  # 1948
    "perceipio tracelayzer evalauted agnst systemview rp2040 suport low overhead",  # 1949
    "renod simluated nrf52 plus bme280 board in ci 2026 02 18 hil queus draind",  # 1950
    "carvd biling surface out of monlith behind strangler fig proxy in kong",  # 1951
    "ran githb scientst exprimnt six weeks pricing calcultor 99.4 percnt match",  # 1952
    "introduced paymetn gatway abstracton seam stripe to adyen branch by abstracton",  # 1953
    "dark launchd new serach service alongsid elasticsearh a month responses loged",  # 1954
    "expand contract rname on users email adress colum took thre releses",  # 1955
    "parralel write pattern postgres to citus migraton cught three ordering bugs",  # 1956
    "contract first extractin payed off generted openapi cleint from spec first",  # 1957
    "git log dash l calcualtetax tax py pulled nien year change histroy one function",  # 1958
    "git log dash s legacy bonus calc expsoed helper not refrenced since 2021",  # 1959
    "cofees cold agian i keep forgeting to drnik it while reding diff revews",  # 1960
    "telemtry driven dead cod removal logged entry point hits six monts 48 files",  # 1961
    "shiped pendo in app baner v1 api six month sunset clok tikets droped 80%",  # 1962
    "deprectation warnigs via warnings warn deprecatonwarning staclevel 2 calers",  # 1963
    "ran libsct codemod replce 2300 instnces of old loger import cst trailng commas",  # 1964
    "bowler let intrns wrte refactr scripts withot undrstanding python ast visitrs",  # 1965
    "ts morph mad legacy react clas to funciton codemod tractble typechecker",  # 1966
    "coexisited sqlachemy 14 and 20 style apis in same codbase eight monhts future",  # 1967
    "replced custm di containr with stdlib functols partial explict wiring 1100 lines",  # 1968
    "scaled past orm droped to raw sql reprots query six months later sqlalchmey core",  # 1969
    "strangller migraton of legacy php app wraped 2026 03 12 after 14 monhts symfony",  # 1970
    "two phse deply split migraton phse one shiped new cod path of by dfault",  # 1971
    "kiled legcy checkout featur flag 2026 03 28 after thre months 100 pecent rollout",  # 1972
    "intrnal sdk v2 sunst plan banner v1 docs 90 days monhtly email renvoate",  # 1973
    "branch by abstracton around cache layr swaped memcahed for reids trunk based",  # 1974
    "contrct tests via pact cught silent respnse shape drfit day we extracted invntory",  # 1975
    "archvied six no longer usd intrnal pakages 2026 02 05 renvoate zero consmers",  # 1976
    "legacy cron jobs migarted to temporl workflows one at a time behnd dispatchr",  # 1977
    "blue green was overkil for databse cutover expand contract read only window",  # 1978
    "sprng boot 2 to 3 migraton leand on openrewrte recipes javax to jakart 600 files",  # 1979
    "junit 4 to junit 5 happend incremntally thnaks to vintage engne last runwth gone",  # 1980
    "git filter repo cleand 2gb of old binry assets monrepo force push re clone 40 eng",  # 1981
    "djanog 3 to djanog 4 migraton legacy crm kept use deprected pytz two sprnts",  # 1982
    "ruby on rails 6 to 7 upgrad dual booting with apprasial gemfile variants ci",  # 1983
    "legcy stored procedre logic movd to pyhton workr via shadow tabel sync db cpu",  # 1984
    "prefr retirng a servie over rewritng it usaage data two customrs dashbord",  # 1985
    "hexogonal extracton of notfication domain staled legacy repo owend user row",  # 1986
    "replced custom workfow dsl with plan python plus decortors legacy parsr 4k lines",  # 1987
    "paralel deploy paymnts service shiped trafic at 1 percnt weigthed envy split",  # 1988
    "tidy frist comit hygine split refactr comits from behavior chnage comits 30% fastr",  # 1989
    "adpoted previw deplys per pr every legcy extracton exerised end to end staging",  # 1990
    "legacy mysql colation utf8 vs utf8mb4 surfcaed schmea migraton convrt using",  # 1991
    "droped legacy soap endpoitn 2026 01 15 after six monhts 0 rps monitroing abandomnt",  # 1992
    "wrote smal ts morph scrpt convrt commonjs reqire calls to esm imprts 320 files",  # 1993
    "sunstet v0 graphql schma switchng depreacted resaon strings exact new field",  # 1994
    "exracted recomendations engne via seam frist refactor intrface adaptr replcament",  # 1995
    "coexistng two orms hurt prismo owned new writs typorm legacy reads sesion bugs",  # 1996
    "consumr deprectation campains work best replcement exists old thing has clok",  # 1997
    "ran sceintist style double cal agianst legacy fraud servce four weks 0.3% mismach",  # 1998
    "big bang orm rewrte rejceted after one wek spike cross cuting sesion assumtions",  # 1999
    "retird telemtry of old metrcs cleint once promethus scraping coverd same signls",  # 2000
]


def _load_sources() -> list[dict]:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    slice_ = lines[SHARED_OFFSET:SHARED_OFFSET + 100]
    return [json.loads(line) for line in slice_]


def emit() -> int:
    if len(QUERIES) != 100:
        raise ValueError(f"expected 100 queries, got {len(QUERIES)}")
    sources = _load_sources()
    if len(sources) != 100:
        raise ValueError(f"expected 100 source rows at offset {SHARED_OFFSET}, got {len(sources)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (src, query) in enumerate(zip(sources, QUERIES), start=1):
            word_count = len(query.split())
            if not (4 <= word_count <= 18):
                raise ValueError(f"query {i} has {word_count} words, out of 4-18 range: {query!r}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
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
