"""Retrieval top-up batch-023: code-switch queries over shared rows 2200..2299."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_023.tmp.jsonl"
ID_OFFSET = 2200
SHARED_OFFSET = 2200
QUERY_KIND = "code-switch"

# 100 code-switch queries, rotating across Spanish (es), French (fr), German (de),
# Japanese romaji (ja), Vietnamese (vi), Portuguese (pt), Mandarin pinyin (zh),
# Hindi romanised (hi), Korean romanised (ko). English technical/proper nouns preserved.
QUERIES: list[str] = [
    # 2200 es — Trussell Harbourside food-bank rotation
    "cada cuándo rota el food-bank shift at Trussell Harbourside y qué hora empieza",
    # 2201 fr — poll worker 2026-05-07 Elmwood Library
    "quand commence la poll worker shift at Elmwood Library pour l'election du 2026-05-07",
    # 2202 de — neighbourhood association parish room move 2026-03-11
    "warum zog das neighbourhood association meeting am 2026-03-11 zum parish room um",
    # 2203 ja — Meals on Wheels Tuesday vs Friday route
    "doushite Tuesday route no Meals on Wheels ga Friday list yori tsukaiyasui no",
    # 2204 vi — HOA chair 2026-02-18 bin-store rebuild
    "tôi lên chair của HOA meeting ngày nào và bin-store rebuild vote passed khi nào",
    # 2205 pt — Allenby Fields bed 14 three-sister rotation with Dev
    "como o community garden plot bed 14 em Allenby Fields divide o three-sister rotation com Dev",
    # 2206 zh pinyin — switched door-knock to phone-bank, bad knees
    "weishenme wo ba council byelection canvassing cong door-knock huan cheng phone-bank",
    # 2207 hi — charity 5k 2026-06-13 twenty-two marshals layout
    "charity 5k ke liye 2026-06-13 par kitne marshals chahiye aur corner stations kahaan lagne hain",
    # 2208 ko — Priya meal train 14 slots vegetarian no nuts
    "Priya ne meal train i 2026-04-20 buteo eonje kkaji dolgo sseulteu myeot gae inji",
    # 2209 es (noise) — sign-up sheet double-check
    "espera, déjame double-check the sign-up sheet antes de finalise",
    # 2210 fr — Habitat for Humanity 2026-03-28 framing nails shortage
    "pourquoi le Habitat for Humanity build day du 2026-03-28 a manqué de framing nails",
    # 2211 de — animal-shelter cat room vs dog kennels Saturday
    "warum arbeitet sie lieber im animal-shelter cat room als in den dog kennels am Saturday",
    # 2212 ja — Osman ESL tutoring Harbourside Thursday 19:00
    "Osman to no ESL tutoring wa maishuu Thursday no nanji kara Harbourside Community Centre de aru",
    # 2213 vi — Little Free Library Marlow Avenue Jim handover
    "Little Free Library ở Marlow Avenue được take over từ Jim khi nào và check stock mỗi bao lâu",
    # 2214 de — Ward 7 mutual-aid pod 41 neighbours storm cover
    "wie teilt der Ward 7 mutual-aid pod mit 41 neighbours die winter storm cover duties auf",
    # 2215 pt — St Bede's hospice induction 2026-01-22 three hours
    "quanto tempo durou a hospice volunteer induction at St Bede's no 2026-01-22",
    # 2216 zh pinyin — Friends of Stanpit Marsh over Wildlife Trust
    "weishenme wo xuan Friends of Stanpit Marsh er bu xuan the wider Wildlife Trust",
    # 2217 hi — St Mary's Primary book drive 612 titles 2026-03-31
    "St Mary's Primary book drive ne 2026-03-31 tak 500 ke target par kitni books collect kiye",
    # 2218 ko — tree-planting 2026-02-07 brook corridor 240 whips
    "tree-planting day e brook corridor e 240 whip eul eotteoke neohgo back-fill reul haesseo",
    # 2219 es — town council office-hour 2026-03-04 Cheviot Row Sunday
    "por qué fui al town council office-hour el 2026-03-04 sobre Cheviot Row parking-free Sunday",
    # 2220 fr — 2025 blood donation four Westfield Tuesday whole-blood
    "combien de fois j'ai fait du blood donation at Westfield Centre en 2025 et quels soirs",
    # 2221 de — Queensdown Meadow park clean-up first Saturday
    "wann findet der Queensdown Meadow park clean-up statt und wo endet die runde",
    # 2222 ja — library friends membership 2026-01-09 £25 AGM rights
    "library friends group ga 2026-01-09 ni £25 de renew sareta koto no benefit wa nani",
    # 2223 vi — paper sign-in preferred over QR code community centre
    "tại sao mình prefer paper sign-in sheets hơn QR code tại community centre",
    # 2224 pt — HOA bin-store rebuild 2026-03-05 £3,200 Rambridge
    "por que a Rambridge Joinery ganhou o bin-store rebuild contract a £3,200 no 2026-03-05",
    # 2225 zh pinyin — canvassing clipboard kit hall cupboard contents
    "hall cupboard li de canvassing clipboard kit you shenme, door-hanger dou fang ji zhang",
    # 2226 hi — 2025 town-hall attendance eight of twelve months missed
    "2025 mein town-hall meetings ke kitne sessions miss kiye aur kaunse mahine miss hue",
    # 2227 ko — 36 Acacia Drive block-party bylaws 23:00 cut-off
    "36 Acacia Drive block-party bylaws e music cut-off neun myeot si iya wae no-alcohol tables",
    # 2228 es — Amnesty to climate-justice chapter after 2025-11
    "por qué dejé Amnesty local group letter-writing por la climate-justice chapter en 2025-11",
    # 2229 fr — Prop 14 research binder kitchen drawer library teach-in
    "où est rangé le Prop 14 research binder et qu'est-ce qu'il contient as notes",
    # 2230 de — time-bank hour-swap Raul piano lessons gate
    "warum bevorzugt sie die time-bank hour-swap mit Raul statt den handyman zu bezahlen",
    # 2231 ja — storm 2026-01-12 neighbour-coordinator 14 households east side
    "storm no hi 2026-01-12 ni neighbour-coordinator toshite nan ken no household wo check shita",
    # 2232 vi — community garden Saturday slot vs Sunday dig-over
    "vì sao chọn Saturday slot thay vì Sunday slot tại community garden Allenby Fields",
    # 2233 pt (noise) — grab clipboard from car
    "espera um segundo, vou grab the clipboard from the car",
    # 2234 zh pinyin — PTA treasurer handover 2026-02-25 Marianne Barclays
    "2026-02-25 PTA treasurer handover shi Marianne jiao gei wo shenme, Barclays zhanghu ma",
    # 2235 hi — Cheviot Row petition 312 signatures by 2026-04-10
    "Cheviot Row parking-free blocks ki petition ne 2026-04-10 tak kitne signatures hasil kiye",
    # 2236 ko — Allenby Fields compost bay turn fortnightly no citrus
    "Allenby Fields ui compost bay neun eolmana jaju turn haeya haji wae citrus peel eun neoh eumyeon andwae",
    # 2237 es — library teach-ins vs Facebook group threads preference
    "por qué prefiere library teach-ins on ballot measures sobre los Facebook group threads del barrio",
    # 2238 fr — hospice shift pattern two three-hour visits continuity
    "quel est le hospice shift pattern de deux three-hour visits et pourquoi favorise la continuité",
    # 2239 de — food-bank Google Sheet 2026-02-02 no-show halved
    "wie hat der Google Sheet volunteer rota ab 2026-02-02 die no-show rate at the food bank verändert",
    # 2240 ja — Bluecoat tutoring Harbourside six-week cycle Osman
    "Bluecoat tutoring programme no six-week cycle de Osman to wa dai ikutsu me no cycle desu ka",
    # 2241 vi — daytime prescription-run over evening food-drop pharmacies
    "tại sao chọn daytime mutual-aid prescription-run thay vì evening food-drop rota vì pharmacy hours",
    # 2242 pt — Queensdown Meadow March vs September clean-up ground firm
    "por que prefiro a March clean-up at Queensdown Meadow em vez da September round",
    # 2243 zh pinyin — 2026 association budget £4,800 bin-store £2,200
    "2026 neighbourhood association budget yi gong £4,800, bin-store rebuild fenpei le duoshao",
    # 2244 hi — 2026-01-30 admin phone died three rotating admins
    "2026-01-30 ki storm mein mutual-aid signal thread kyun break hua aur kitne admins rotate kiye",
    # 2245 ko — St Mary's school governor 2026-04-06 Priya Raul DBS
    "St Mary's Primary school governor application eul 2026-04-06 e eolmana jaryo wa hamkke neotneunji",
    # 2246 es — paper blood-donation card over NHS Give Blood app
    "por qué prefiere la paper blood-donation appointment card al NHS Give Blood app",
    # 2247 fr — ward councillor surgery first Tuesday Crown pub 18:00
    "quand se tient la ward councillor surgery at The Crown pub et quel est le horaire walk-in",
    # 2248 de — charity 5k committee Wednesday 19:30 rugby clubhouse
    "wo trifft sich das charity 5k organising committee jeden Wednesday um 19:30 abends",
    # 2249 ja — 2026-04-25 Westfield 17:40 donation iron level fine
    "2026-04-25 no Westfield Centre blood donation wa 17:40 kara de iron level wa doudatta",
    # 2250 vi — Friston free-energy variational hierarchical generative
    "Karl Friston của free-energy principle giải thích perception và action qua variational free energy như thế nào",
    # 2251 pt — predictive-coding top-down prediction bottom-up error
    "como o predictive-coding framework substitui o feedforward feature-detector account no córtex",
    # 2252 zh pinyin — O'Keefe 1971 hippocampal place cells rats
    "O'Keefe yu 1971 nian zenme zai freely moving rats shang faxian le hippocampal place cells",
    # 2253 hi — Moser entorhinal grid cells 2005 hexagonal
    "Moser ne entorhinal grid cells 2005 mein kaise identify kiye aur hexagonal map kya batati hai",
    # 2254 ko — Bliss Lomo 1973 LTP synaptic strengthening
    "Bliss wa Lomo ga 1973 nyeon e long-term potentiation eul cheoeum eotteoke demonstrate haesseo",
    # 2255 es — adolescent synaptic pruning prefrontal reshapes
    "cómo el adolescent synaptic pruning remodela los prefrontal circuits eliminando connections débiles",
    # 2256 fr — default mode network Raichle 2001 rest internal thought
    "comment Raichle a cartographié le default mode network vers 2001 lors du rest et de la pensée interne",
    # 2257 de — salience network insula ACC switching DMN executive
    "wie schaltet das salience network zwischen default mode und executive control via insula und ACC",
    # 2258 ja — Schultz 1990s dopamine RPE temporal-difference
    "Schultz no 1990-nendai midbrain dopamine recording ga temporal-difference RPE to dou itchi shita",
    # 2259 vi (noise) — double-check striatum anatomy
    "khoan, cho mình double-check the striatum anatomy trước khi commit tag đó",
    # 2260 pt — canonical microcircuit layered cortical motif repeated
    "como a canonical microcircuit hypothesis propõe um motivo cortical em camadas repetido entre áreas",
    # 2261 zh pinyin — C. elegans connectome White 1986 wiring diagram
    "White deng ren 1986 nian wanchengle C. elegans connectome, na shi shenme yangde wiring diagram",
    # 2262 hi — MICrONS cubic millimetre mouse visual cortex IARPA
    "MICrONS project ne mouse visual cortex ka cubic millimetre kaunse imaging se reconstruct kiya",
    # 2263 ko — optogenetics Deisseroth Boyden 2005 microbial opsins
    "Deisseroth wa Boyden i 2005 nyeon jjeum optogenetics reul eotteoke gaebal haesseo microbial opsin ro",
    # 2264 es — two-photon calcium GCaMP infrared awake
    "cómo two-photon calcium imaging con GCaMP resuelve cientos de neuronas en awake animals con excitation infrared",
    # 2265 fr — Neuropixels 2017 SfN hundreds cortical units
    "pourquoi les Neuropixels probes lancées en 2017 à la Society for Neuroscience ont transformé le cortical recording",
    # 2266 de — fMRI BOLD haemodynamic slow seconds resolution
    "warum begrenzt das haemodynamic BOLD signal die fMRI temporal resolution auf die Grössenordnung von Sekunden",
    # 2267 ja — Kamitani decoded fMRI linear decoder voxel
    "Kamitani no decoded fMRI ga voxel pattern kara perceived image wo dou saikousei suru",
    # 2268 vi — Lancaster Knoblich 2013 iPSC brain organoids
    "Lancaster và Knoblich đã report brain organoids từ iPSCs năm nào và cortical tissue ra sao",
    # 2269 pt — MEG millisecond shielded-room vs EEG portable
    "por que o MEG prefere a millisecond temporal resolution mesmo perdendo a portability do EEG",
    # 2270 zh pinyin — slow-wave sleep hippocampal replay neocortical
    "slow-wave sleep zenme rang hippocampal traces reactivate bing xiang neocortical long-term memory zhuan",
    # 2271 hi — sharp-wave ripples Buzsaki offline replay
    "Buzsaki group ne hippocampal sharp-wave ripples kaise record kiye aur offline replay kya karte hain",
    # 2272 ko — Craig interoception insular cortex visceral
    "Craig ui interoception account i wae conscious bodily awareness reul insular cortex e nohneunji",
    # 2273 es — Posner alerting orienting executive attention
    "cómo Posner descompone la attention en alerting, orienting y executive control con substratos neurales",
    # 2274 fr — embodied cognition perceptual motor vs amodal
    "pourquoi l'embodied cognition rejette les amodal symbols au profit des perceptual motor simulations",
    # 2275 de — Tulving 1972 episodic vs semantic memory
    "wie hat Tulving 1972 episodic memory von semantic memory sauber getrennt",
    # 2276 ja — Cowan four chunks vs Baddeley multi-component
    "Cowan no embedded-processes model ga working-memory capacity wo yottsu no chunk ni naze settei suru",
    # 2277 vi — Fuster prefrontal delay-activity single units
    "Fuster đã record prefrontal delay-activity neurons như thế nào để ground working-memory theory",
    # 2278 pt — Glimcher neuroeconomics basal-ganglia RPE value
    "como a neuroeconomics de Glimcher aproveita o basal-ganglia prediction error para value learning",
    # 2279 zh pinyin — Rizzolatti mirror neurons premotor action
    "Rizzolatti 1990 niandai de mirror-neuron jiashuo zenme yong premotor neurons jieshi action understanding",
    # 2280 hi — Hubel Wiesel kittens monocular deprivation columns
    "Hubel aur Wiesel ke kitten critical-period experiments ne ocular-dominance columns par kya prove kiya",
    # 2281 ko — adult neuroplasticity Hebbian use-dependent remapping
    "adult neuroplasticity ga Hebbian learning eul eotteoke hwakdaehae use-dependent cortical remap eul bojueo",
    # 2282 es — Dehaene global workspace frontoparietal ignition
    "cómo la global neuronal workspace theory de Dehaene explica el conscious access vía frontoparietal ignition",
    # 2283 fr (noise) — recheck Brodmann area coordinate
    "un instant, je dois recheck which Brodmann area corresponds to that coordinate",
    # 2284 de — Tononi 2004 IIT phi irreducible causal
    "wie quantifiziert Tononis integrated information theory von 2004 das Bewusstsein mit phi",
    # 2285 ja — Shallice Warrington 1970 KF short-term long-term
    "Shallice to Warrington no 1970 patient KF ga tanki to choki memory no bunri wo dou shimesu",
    # 2286 vi — Damasio somatic-marker ventromedial prefrontal
    "Damasio somatic-marker hypothesis giải thích decision-making qua ventromedial prefrontal cortex ra sao",
    # 2287 pt — Kanwisher 1997 fusiform face area selective
    "como Kanwisher identificou em 1997 a fusiform face area seletiva para faces em vez de objetos",
    # 2288 zh pinyin — Kahneman 2011 System 1 System 2
    "Kahneman 2011 nian Thinking Fast and Slow zenme ba cognition fen cheng System 1 he System 2",
    # 2289 hi — Human Connectome Project 2010 thousand adults fMRI
    "Human Connectome Project ne 2010 se Washington University par kitne healthy adults ko scan kiya",
    # 2290 ko — Tsodyks spiking recurrent vs rate-coded working memory
    "Tsodyks geu rup eun wae rate-coded boda spiking recurrent network reul working-memory persistence e seonhohae",
    # 2291 es — Bayesian brain posterior inference sensory causes
    "cómo los Bayesian brain accounts generalizan predictive coding vía posterior inference sobre causas sensoriales",
    # 2292 fr — CLARITY Chung Deisseroth 2013 Stanford transparent
    "comment la technique CLARITY de Chung et Deisseroth en 2013 à Stanford rend le brain transparent",
    # 2293 de — active inference motor commands minimise surprise
    "wie erweitert active inference das free-energy principle auf motor commands, die sensory surprise minimieren",
    # 2294 ja — Allen Brain Observatory 2016 mouse visual Neuropixels
    "Allen Brain Observatory ga 2016-nen irai mouse visual system no dono data wo public ni shiteiru",
    # 2295 vi — Diamond ferret retinal auditory thalamus rewiring
    "Diamond ferret rewiring experiment chứng minh auditory cortex có thể phát visual response như thế nào",
    # 2296 pt — STDP Bi Poo 1998 millisecond pre-post
    "como a spike-timing-dependent plasticity descrita por Bi e Poo em 1998 depende da ordem millisecond",
    # 2297 zh pinyin — patch-clamp Neher Sakmann 1970s single channel
    "Neher he Sakmann 1970 niandai mo qi kaifa de patch-clamp zenme jilu single ion channel currents",
    # 2298 hi — Buckner DMN dysfunction Alzheimer amyloid midline
    "Buckner ke research ne default mode network dysfunction ko early Alzheimer amyloid se kaise jodha",
    # 2299 ko — DTI tractography anisotropic diffusion white matter
    "DTI tractography ga anisotropic water diffusion eul model hae white-matter pathway reul in vivo ro boyeojueo",
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
