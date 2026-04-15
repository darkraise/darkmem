"""Retrieval top-up batch-022: code-switch queries over shared rows 2100..2199."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_022.tmp.jsonl"
ID_OFFSET = 2100
SHARED_OFFSET = 2100
QUERY_KIND = "code-switch"

# 100 code-switch queries, rotating across Spanish (es), French (fr), German (de),
# Japanese romaji (ja), Vietnamese (vi), Portuguese (pt), Mandarin pinyin (zh),
# Hindi romanised (hi), Korean romanised (ko). English technical/proper nouns preserved.
QUERIES: list[str] = [
    # 2100 es
    "cuál es la newborn sleep routine con el 7pm bath feed swaddle y dark room",
    # 2101 fr
    "pourquoi on est passé au Ergobaby carrier après la pediatrician flag sur hip position",
    # 2102 de
    "wie lief das potty-training mit Maya nach der week-three regression ohne sticker rewards",
    # 2103 ja
    "Montessori floor bed ga crib yori naze 14-month-old no falling asleep ni ii",
    # 2104 vi
    "Leo hit first 12 steps ngày nào từ couch sang TV stand và báo grandparents",
    # 2105 pt
    "como funciona a daycare rota entre Little Acorns Nana e Friday home comigo",
    # 2106 zh pinyin
    "weishenme xuan Brookside Primary bi St Anne dui nurture group programme geng hao",
    # 2107 hi
    "bedtime story rule mein Maya ke liye picture books aur Leo ke Narnia chapter kaise hai",
    # 2108 ko
    "Riverside Clinic ui Dr Hamid ga MMR boosters reul eotteoke shared calendar ro gwanrihae",
    # 2109 es (noise)
    "espera un momento, I can hear the baby stirring upstairs",
    # 2110 fr
    "quand Leo a perdu sa first loose tooth dans la slice de pear à table",
    # 2111 de
    "wie ist die screen-time rule weekday 30 minutes weekend 90 minutes nach 6pm nichts",
    # 2112 ja
    "six-month-old to no co-sleeping side-car style ga room-sharing yori naze anzen",
    # 2113 vi
    "Maya first swim lesson tại Waverley Leisure với teacher Jen ngày nào đầu submerged face",
    # 2114 pt
    "qual foi a tantrum strategy com Leo aos 3 nomeando feeling e duas choices",
    # 2115 zh pinyin
    "shenme shihou ba Cocomelon YouTube huan cheng Bluey library gei Maya",
    # 2116 hi
    "Leo aur Maya ka back-bedroom room-share gyarah months baad kyun toota March mein",
    # 2117 ko
    "Fosters wa ui shared nanny arrangement i nursery 1:4 ratio boda wae deo natatteo",
    # 2118 es
    "cuándo aterrizó la first-phone negotiation en el Nokia 2660 flip sin smartphone",
    # 2119 fr
    "pourquoi Leo préfère le baby-led weaning aux spoon-fed purees pour les textures",
    # 2120 de
    "was hat die parent-teacher conference bei Brookside 2026-03-28 über Mayas pencil grip",
    # 2121 ja
    "Dr Hamid no vaccination schedule de 12-month MMR to pre-school booster wa itsu",
    # 2122 vi
    "bedtime rift với Priya 7:30 vs 8:30 được compromise ra sao cho school nights",
    # 2123 pt
    "quanto custou a Leo kindergarten birthday party no Clip n Climb Brookfield 2026-02-15",
    # 2124 zh pinyin
    "weishenme xuan car-seat-free Thule bike trailer dai liang ge haizi bi front-mount",
    # 2125 hi
    "chickenpox bout dono bachchon mein kab tak chala calamine oat baths missed swim lessons",
    # 2126 ko
    "Maya reul Rainbows e deungrokhan nalja i geu church hall Tuesday meeting ga myeot si",
    # 2127 es
    "cómo está estructurada la custody week de Priya desde Monday 8am hasta Sunday 6pm",
    # 2128 fr
    "comment Leo a transitionné hors des naps le 2026-03-30 et allongé son sommeil",
    # 2129 de
    "wer gehört zur playdate rotation Okoye Harris Patel Nguyen alternating Saturdays sugar rule",
    # 2130 ja
    "white-noise machine kara Yoto Mini ni kaeta no wa itsu, Owl Babies audiobook de",
    # 2131 vi
    "vì sao chọn Bulleh Nursery thay Rainbow Cottage dù chênh £40 mỗi tuần",
    # 2132 pt
    "como a homework battle da Maya com spelling se resolveu movendo para pre-dinner",
    # 2133 zh pinyin (noise)
    "deng yixia, the school bus just pulled up outside",
    # 2134 hi
    "Leo ke liye cycle balance bike kyun chuni stabilisers ke bajaye pedals six weeks mein",
    # 2135 ko
    "Maya ui ear infection cycle ga Ellesmere ENT ui grommets hu eotteoke meomchueosseo",
    # 2136 es
    "cómo funciona el car-seat handover con abuela Cybex Solution y la base en su Yaris",
    # 2137 fr
    "pourquoi le solo bus ride du voisin de 13 ans sert de benchmark pour Maya plus tard",
    # 2138 de
    "warum bevorzugt Leo die child-led park hour über dem structured music class Samstags",
    # 2139 ja
    "kids no milk wo cow kara oat ni kaeta toki Maya no eczema ga dou naotta",
    # 2140 vi
    "Aunt Preeti con 17 tuổi first driving lesson ngày nào với RED Driving School",
    # 2141 pt
    "qual é o weekend morning protocol das 7am com cereal fruit e milk jug no chão",
    # 2142 zh pinyin
    "Leo de reading level daoda pink book band shi shenme shihou, Priya zenme jilu",
    # 2143 hi
    "2025-12-19 ki croup episode mein Queen Alexandra A&E jaane se pehle steam bathroom kaise madad ki",
    # 2144 ko
    "Saturday morning pancake ritual i sit-down weekday breakfast boda wae deo joha together time",
    # 2145 es
    "cómo opera el school-run carpool con Harris family en Brookside Monday y Thursday pickups",
    # 2146 fr
    "quelle est la teething relief ladder chilled ring cold flannel puis Calpol après 6pm",
    # 2147 de
    "wann haben wir den SIMS parent portal statt SMS für Mayas school aktiviert",
    # 2148 ja
    "Leo no bath drain no kyoufu ga itsu hajimatta, silicone stopper to rubber duck no taiou",
    # 2149 vi
    "Woodland Adventure summer camp 2026 deposit bao nhiêu và balance đến khi nào",
    # 2150 pt
    "quando movi o emergency fund do Marcus 4.10% pro Wealthfront Cash 4.85%",
    # 2151 zh pinyin
    "household three-fund portfolio shi 60 VTSAX 30 VTIAX 10 VBTLX zenme jidu rebalance",
    # 2152 hi
    "Fidelity par Roth IRA kab khula aur 2025 contribution FZROX mein kitna auto-invest hua",
    # 2153 ko
    "YNAB boda wae Monarch Money reul seontaekhaetna partner view wa auto-categorisation ttaemune",
    # 2154 es
    "por qué pagué el 22.9% Barclaycard de £4,200 antes de volver al brokerage",
    # 2155 fr
    "comment marche la backdoor Roth conversion chaque janvier chez Schwab sans pro-rata",
    # 2156 de
    "wie wird die HSA bei Lively als stealth IRA mit Dropbox receipts und VTI geführt",
    # 2157 ja
    "Rocket de 6.8% mortgage wo 5.375% ni refi shita hi to break-even no tsuki",
    # 2158 vi
    "tax-loss harvesting sweep 2025-12-29 booked bao nhiêu losses và swap sang ITOT thế nào",
    # 2159 pt (noise)
    "espera aí, I want to grab coffee before we open the spreadsheet",
    # 2160 zh pinyin
    "Noah de 529 zai Utah my529 shang Vanguard Moderate age-based auto $400 meiyue",
    # 2161 hi
    "Betterment ke bajaye Fidelity Go taxable brokerage kyun chuna $25,000 ke neeche fee drop",
    # 2162 ko
    "Fidelity Charitable DAF reul eonje yeolgo $15,000 VTSAX appreciated ro grant-out sanyeonae",
    # 2163 es
    "cuál es la cash-flow routine del primer día del mes con 401k HSA y brokerage",
    # 2164 fr
    "pourquoi on a migré de Quicken à Actual Budget self-hosted sur le home NAS",
    # 2165 de
    "warum wechselt man jobs alle drei Jahre für den 24% bump statt internem raise",
    # 2166 ja
    "emergency fund no target ga 3 kagetsu kara 6 kagetsu ni natta no wa itsu Ally CD ladder",
    # 2167 vi
    "Chase 5/24 block sau khi churning retire khi nào, giữ lại Sapphire và AmEx Platinum",
    # 2168 pt
    "como o expense-splitting com Maya funciona no Splitwise e joint Chase settle-up",
    # 2169 zh pinyin
    "net worth chaoguo £500,000 shi nage riqi, brokerage he mortgage zenme gongxian",
    # 2170 hi
    "I Bond ladder TreasuryDirect par 2024-10-01 se $10,000 har saal tagging kaise hoti",
    # 2171 ko
    "crypto exposure ga liquid portfolio ui 2% e cap doego BTC wa ETH Coinbase e sassaeyo",
    # 2172 es
    "cuándo golpeó el 401k el cap de $23,500 en 2025-10-22 y el true-up match siguió",
    # 2173 fr
    "comment EFTPS prélève les quarterly estimated taxes les 15 janvier avril juin septembre",
    # 2174 de
    "warum bevorzugt man die Chase Sapphire Reserve single card über drei mid-tier travel cards",
    # 2175 ja
    "Mum to no inheritance planning call de LPA to will draft wo solicitor Priya Nair ga itsu",
    # 2176 vi
    "Barclaycard Platinum 0% balance transfer kéo dài bao lâu và fee bao nhiêu 2025-09-14",
    # 2177 pt
    "qual é o coast-FI rule-of-25 target em £1.1 million e a idade projetada base",
    # 2178 zh pinyin
    "Schwab UTMA zai 2025-12-01 wei Noah $2,500 SWTSX mai, kiddie-tax zenme bikai",
    # 2179 hi
    "PenFed car refinance 7.2% se 4.9% APR kab hua aur monthly kitna save hota hai",
    # 2180 ko
    "taxable account eseo mutual fund boda ETF reul wae seontaekhaetna ITOT tax-efficiency",
    # 2181 es
    "qué recomendó Alex Chen CFP en la annual financial review sobre la bond glidepath",
    # 2182 fr
    "pourquoi le grocery budget passe de £520 à £640 après l'overrun de 18% au Q4 2025",
    # 2183 de (noise)
    "Moment mal, I need to pull up the statement PDF first",
    # 2184 ja
    "family HSA ni 2026-01-05 de $8,300 wo irete HDHP coverage ga itsu kara",
    # 2185 vi
    "chuyển travel points từ AmEx Membership Rewards sang Chase Ultimate Rewards ngày nào Hyatt",
    # 2186 pt
    "quando o mega-backdoor Roth no 401k abriu com $34,500 after-tax rollout",
    # 2187 zh pinyin
    "Google Sheets li de high-yield-savings tracker yong Bankrate IMPORTHTML meige xingqiyi shuaxin",
    # 2188 hi
    "Maya ke saath dollar-cost averaging 15th date ko lump-sum bonus week se kyun behtar",
    # 2189 ko
    "FSA dependent-care enrolment i 2026 e $5,000 choegodo WEX upload eonje olieosseo",
    # 2190 es
    "cuándo cerré la Wells Fargo checking y por qué pasé el primario a Schwab Bank",
    # 2191 fr
    "quelle est la charitable giving rule 5% du gross income bunched DAF années impaires",
    # 2192 de
    "wann verkaufte ich die letzte Apple Aktie $4,800 vom 2018 ESPP in March 2026",
    # 2193 ja
    "Amex Savings checking no cash-buffer floor ga £2,500 de 25th ni sweeps wa doko ni",
    # 2194 vi
    "Arbor Planning flat-fee review £1,500 ngày nào và written plan giao trong bao lâu",
    # 2195 pt
    "por que prefiro pagar a mortgage biweekly depois da refi trimming thirty-year em quatro",
    # 2196 zh pinyin
    "Chubb umbrella liability $2 million zai 2026-03-05 qi yong nianfei duo shao qian",
    # 2197 hi
    "target-date fund old 401k se Vanguard IRA mein kab rollover hua aur rebalance single screen",
    # 2198 ko
    "E-Trade Solo 401k ga 2025-09-30 yeolligo side consulting $12,400 profit-sharing myeot si",
    # 2199 es
    "cómo rastreo el FIRE progress contra £1.4 million target actualmente 62% en 2026-03-31",
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
