"""One-off emitter for shared-base batch-046 — knowledge domain (neuroscience and cognitive science).

Writes 50 rows with ids shared-02251..02300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_046.tmp.jsonl"
ID_OFFSET = 2250

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Karl Friston's free-energy principle casts perception and action as the minimisation of variational free energy across a hierarchical generative model.", "reference", "knowledge", False,
     [("Karl Friston", "person"), ("free-energy principle", "theory"), ("variational free energy", "concept"), ("generative model", "concept")],
     [("free-energy principle", "Karl Friston", "AUTHORED_BY")],
     "whose unifying brain theory recasts perception as minimising surprise over a hierarchical model",
     "variational free energy generative hierarchical surprise minimisation framework"),
    # --- 2 ---
    ("The predictive-coding framework replaces feedforward feature-detector accounts by treating cortical traffic as top-down predictions and bottom-up prediction errors.", "decision", "knowledge", False,
     [("predictive-coding framework", "theory"), ("feedforward feature-detector accounts", "theory"), ("prediction errors", "concept")],
     [("predictive-coding framework", "feedforward feature-detector accounts", "REPLACES")],
     "which cortical theory supplanted pure feedforward accounts with top-down prediction and error signals",
     "top down prediction error feedback cortex processing account"),
    # --- 3 ---
    ("O'Keefe discovered hippocampal place cells in 1971 by recording single units in freely moving rats during spatial exploration.", "milestone", "knowledge", False,
     [("O'Keefe", "person"), ("place cells", "concept"), ("1971", "date"), ("hippocampal", "concept")],
     [("place cells", "O'Keefe", "AUTHORED_BY")],
     "when were hippocampal cells that fire at specific locations first reported in rodents",
     "hippocampus spatial firing single unit rat exploration year"),
    # --- 4 ---
    ("The Mosers identified entorhinal grid cells in 2005, revealing a periodic hexagonal map of space upstream of the hippocampus.", "milestone", "knowledge", False,
     [("Mosers", "person"), ("grid cells", "concept"), ("2005", "date"), ("hippocampus", "concept")],
     [("grid cells", "Mosers", "AUTHORED_BY")],
     "when did researchers uncover hexagonal spatial tuning in the entorhinal cortex",
     "entorhinal hexagonal spatial map upstream hippocampus discovery year"),
    # --- 5 ---
    ("Long-term potentiation, first demonstrated by Bliss and Lomo in 1973, provides the dominant cellular model for experience-dependent synaptic strengthening.", "reference", "knowledge", False,
     [("Long-term potentiation", "concept"), ("Bliss", "person"), ("Lomo", "person"), ("1973", "date")],
     [("Long-term potentiation", "Bliss", "AUTHORED_BY")],
     "which 1973 finding still anchors cellular accounts of learning-related synaptic strengthening",
     "LTP synaptic strengthening Bliss Lomo hippocampus discovery year"),
    # --- 6 ---
    ("Adolescent synaptic pruning reshapes prefrontal circuits by eliminating weakly used connections while sparing actively reinforced ones.", "fact", "knowledge", False,
     [("Adolescent synaptic pruning", "concept"), ("prefrontal circuits", "concept")],
     [],
     "which developmental process trims weakly used prefrontal connections during the teenage years",
     "pruning adolescence prefrontal cortex use dependent elimination synapse"),
    # --- 7 ---
    ("The default mode network, mapped by Raichle's team around 2001, activates during rest and internally directed thought rather than external tasks.", "milestone", "knowledge", False,
     [("default mode network", "concept"), ("Raichle", "person"), ("2001", "date")],
     [("default mode network", "Raichle", "AUTHORED_BY")],
     "when was the resting-state brain network linked to mind-wandering first described",
     "DMN resting state mind wandering internal thought discovery year"),
    # --- 8 ---
    ("The salience network, anchored in anterior insula and dorsal anterior cingulate, gates switching between the default mode and executive control systems.", "fact", "knowledge", False,
     [("salience network", "concept"), ("anterior insula", "concept"), ("dorsal anterior cingulate", "concept"), ("default mode", "concept"), ("executive control", "concept")],
     [("salience network", "anterior insula", "DEPENDS_ON")],
     "which network toggles the brain between introspective rest and external task engagement",
     "insula cingulate switch network triple network salience gating"),
    # --- 9 ---
    ("Schultz's recordings of midbrain dopamine neurons in the 1990s showed firing patterns matching the temporal-difference reward prediction error.", "milestone", "knowledge", False,
     [("Schultz", "person"), ("dopamine neurons", "concept"), ("1990s", "date"), ("temporal-difference", "algorithm"), ("reward prediction error", "concept")],
     [("reward prediction error", "Schultz", "AUTHORED_BY")],
     "whose monkey recordings matched dopamine firing to a reinforcement-learning error signal",
     "midbrain dopamine TD error monkey recording reward prediction nineties"),
    # --- 10. noise ---
    ("Let me double-check the striatum anatomy before I commit to that label.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The canonical microcircuit hypothesis argues a single layered cortical motif is repeated across sensory, motor, and associative areas.", "fact", "knowledge", False,
     [("canonical microcircuit hypothesis", "theory"), ("cortical motif", "concept"), ("sensory", "concept"), ("motor", "concept")],
     [],
     "which hypothesis claims a single repeating layered circuit underlies most of the cortex",
     "canonical cortex laminar circuit repeat sensory motor association motif"),
    # --- 12 ---
    ("The C. elegans connectome, completed by White and colleagues in 1986, remains the first whole-animal wiring diagram at synaptic resolution.", "reference", "knowledge", False,
     [("C. elegans", "concept"), ("connectome", "concept"), ("White", "person"), ("1986", "date")],
     [("connectome", "White", "AUTHORED_BY")],
     "which 1986 wiring diagram provided the first whole-animal synaptic map",
     "nematode full wiring diagram synaptic connectome whole animal year"),
    # --- 13 ---
    ("The MICrONS project, funded under the IARPA initiative, reconstructed a cubic millimetre of mouse visual cortex by aligning two-photon imaging with nanometre electron microscopy.", "milestone", "knowledge", False,
     [("MICrONS", "project"), ("IARPA", "organization"), ("mouse visual cortex", "concept"), ("two-photon imaging", "method"), ("electron microscopy", "method")],
     [("MICrONS", "IARPA", "DEPENDS_ON")],
     "which multi-lab project mapped a cubic millimetre of visual cortex at electron-microscope detail",
     "cubic millimetre mouse visual cortex electron microscopy two photon co registration"),
    # --- 14 ---
    ("Optogenetics, pioneered by Deisseroth and Boyden around 2005, inserts microbial opsins so that millisecond-precise light pulses can drive or silence specific neurons.", "milestone", "knowledge", False,
     [("Optogenetics", "method"), ("Deisseroth", "person"), ("Boyden", "person"), ("2005", "date"), ("microbial opsins", "concept")],
     [("Optogenetics", "Deisseroth", "AUTHORED_BY")],
     "when did light-controlled opsin tools for targeted neural activation become available",
     "opsin channelrhodopsin light activation neural control method year"),
    # --- 15 ---
    ("Two-photon calcium imaging resolves activity from hundreds of individual neurons in awake animals by pairing GCaMP indicators with infrared excitation.", "fact", "knowledge", False,
     [("Two-photon calcium imaging", "method"), ("GCaMP", "tool"), ("infrared excitation", "concept")],
     [("Two-photon calcium imaging", "GCaMP", "DEPENDS_ON")],
     "which optical method records from many neurons in behaving animals using calcium-sensitive probes",
     "GCaMP calcium imaging awake behaving cranial window infrared two photon"),
    # --- 16 ---
    ("Neuropixels probes, released at the 2017 Society for Neuroscience meeting, record hundreds of cortical units simultaneously on a single silicon shank with integrated CMOS electronics.", "milestone", "knowledge", False,
     [("Neuropixels", "tool"), ("2017", "date"), ("Society for Neuroscience meeting", "event"), ("silicon shank", "concept"), ("CMOS electronics", "technology")],
     [],
     "when did high-density single-shank silicon probes for large-scale unit recording ship widely",
     "silicon probe high density electrophysiology release year CMOS"),
    # --- 17 ---
    ("The fMRI BOLD signal reflects a slow haemodynamic proxy for neural activity, limiting temporal resolution to the order of seconds regardless of field strength.", "problem", "knowledge", False,
     [("fMRI", "method"), ("BOLD signal", "concept"), ("haemodynamic proxy", "concept")],
     [("BOLD signal", "haemodynamic proxy", "DEPENDS_ON")],
     "which methodological limit caps the temporal resolution of functional MRI regardless of scanner strength",
     "BOLD haemodynamic temporal resolution seconds fMRI limit signal"),
    # --- 18 ---
    ("Decoded fMRI, developed by Kamitani's group, reconstructs perceived images from voxel patterns by training linear decoders on known stimuli.", "fact", "knowledge", False,
     [("Decoded fMRI", "method"), ("Kamitani", "person"), ("voxel patterns", "concept"), ("linear decoders", "algorithm")],
     [("Decoded fMRI", "Kamitani", "AUTHORED_BY")],
     "whose Japanese lab rebuilds viewed pictures out of scanner data by training weighted readouts",
     "voxel decoding image reconstruction brain reading linear decoder Japan"),
    # --- 19 ---
    ("Brain organoids derived from iPSCs, reported by Lancaster and Knoblich in 2013, self-organise into layered cortical tissue useful for developmental study.", "milestone", "knowledge", False,
     [("Brain organoids", "concept"), ("iPSCs", "concept"), ("Lancaster", "person"), ("Knoblich", "person"), ("2013", "date")],
     [("Brain organoids", "Lancaster", "AUTHORED_BY")],
     "when did self-organising cerebral organoids from stem cells enter mainstream neuroscience",
     "cerebral organoid iPSC Lancaster Knoblich self organising year"),
    # --- 20 ---
    ("MEG preserves millisecond temporal resolution and shallow-source spatial detail, trading EEG's portability for shielded-room magnetic sensing.", "preference", "knowledge", False,
     [("MEG", "method"), ("EEG", "method"), ("magnetic sensing", "concept"), ("portability", "concept")],
     [("MEG", "EEG", "PREFERS")],
     "which neuroimaging modality trades portability for shielded millisecond magnetic detail at shallow sources",
     "magnetoencephalography shielded room millisecond superficial source MEG choice"),
    # --- 21 ---
    ("Sleep and memory consolidation theory argues slow-wave sleep reactivates hippocampal traces, reshaping them into neocortical long-term representations.", "fact", "knowledge", False,
     [("slow-wave sleep", "concept"), ("hippocampal traces", "concept"), ("neocortical long-term representations", "concept")],
     [],
     "which theory links slow-wave sleep replay to moving memories from hippocampus into neocortex",
     "sleep consolidation slow wave replay hippocampus neocortex transfer theory"),
    # --- 22 ---
    ("Hippocampal sharp-wave ripples, recorded by Buzsaki's group, compress behavioural sequences into millisecond bursts that are believed to coordinate offline replay.", "fact", "knowledge", False,
     [("sharp-wave ripples", "concept"), ("Buzsaki", "person"), ("behavioural sequences", "concept"), ("offline replay", "concept")],
     [("sharp-wave ripples", "Buzsaki", "AUTHORED_BY")],
     "which hippocampal oscillations compress prior trajectories into bursts suited for offline replay",
     "SWR hippocampus replay compressed sequence Buzsaki ripple"),
    # --- 23 ---
    ("Craig's interoception account locates conscious bodily awareness in the insular cortex, where visceral afferents are integrated into felt states.", "fact", "knowledge", False,
     [("Craig", "person"), ("interoception", "concept"), ("insular cortex", "concept"), ("visceral afferents", "concept")],
     [("interoception", "Craig", "AUTHORED_BY")],
     "whose account places felt bodily states in the insula via integrated visceral inputs",
     "interoception insula visceral afferent felt state Craig account"),
    # --- 24 ---
    ("Posner's attention framework decomposes attention into alerting, orienting, and executive control networks with dissociable neural substrates.", "reference", "knowledge", False,
     [("Posner", "person"), ("attention framework", "framework"), ("alerting", "concept"), ("orienting", "concept"), ("executive control", "concept")],
     [("attention framework", "Posner", "AUTHORED_BY")],
     "whose taxonomy carves focus into three separable neural subsystems for vigilance, shifting, and top-down biasing",
     "alerting orienting executive network attention framework Posner taxonomy"),
    # --- 25 ---
    ("Embodied cognition argues that perceptual and motor simulations, not amodal symbols, constitute the substrate of conceptual thought.", "decision", "knowledge", False,
     [("Embodied cognition", "theory"), ("motor simulations", "concept"), ("amodal symbols", "concept")],
     [("Embodied cognition", "amodal symbols", "REPLACES")],
     "which cognitive theory swaps amodal symbols for perception-and-action-based simulation",
     "embodied grounded cognition simulation sensorimotor amodal symbol rival"),
    # --- 26 ---
    ("Tulving's 1972 distinction separates episodic memory for personally experienced events from semantic memory for general world knowledge.", "milestone", "knowledge", False,
     [("Tulving", "person"), ("1972", "date"), ("episodic memory", "concept"), ("semantic memory", "concept")],
     [("episodic memory", "Tulving", "AUTHORED_BY")],
     "when did the episodic versus semantic memory distinction enter the canonical lexicon",
     "Tulving episodic semantic declarative memory split taxonomy year"),
    # --- 27 ---
    ("Cowan's embedded-processes model pegs working-memory capacity at roughly four chunks, competing with Baddeley's multi-component account.", "decision", "knowledge", False,
     [("Cowan", "person"), ("embedded-processes model", "theory"), ("working-memory capacity", "concept"), ("Baddeley", "person")],
     [("embedded-processes model", "Cowan", "AUTHORED_BY")],
     "whose four-chunk account of working memory challenges the multi-component view",
     "working memory capacity four chunk Cowan Baddeley debate account"),
    # --- 28 ---
    ("Fuster's prefrontal delay-activity recordings showed neurons sustaining firing across the gap between stimulus and response, grounding working-memory theory in single units.", "fact", "knowledge", False,
     [("Fuster", "person"), ("prefrontal delay-activity", "concept"), ("working-memory", "concept")],
     [("prefrontal delay-activity", "Fuster", "AUTHORED_BY")],
     "whose single-neuron recordings tied sustained prefrontal firing to working-memory maintenance",
     "prefrontal delay activity sustained firing working memory Fuster monkey"),
    # --- 29 ---
    ("Glimcher's neuroeconomics builds on temporal-difference dopamine accounts by treating basal-ganglia prediction error as the substrate of value learning.", "architecture", "knowledge", False,
     [("Glimcher", "person"), ("neuroeconomics", "field"), ("temporal-difference dopamine accounts", "theory"), ("basal-ganglia prediction error", "concept")],
     [("neuroeconomics", "temporal-difference dopamine accounts", "BUILDS_ON")],
     "which field extends dopamine reward-error theory into the economics of value-based choice",
     "neuroeconomics basal ganglia prediction error value learning dopamine extension"),
    # --- 30 ---
    ("The mirror-neuron hypothesis, advanced by Rizzolatti in the 1990s, claims premotor neurons firing for both self-action and observed action underpin action understanding.", "fact", "knowledge", False,
     [("mirror-neuron hypothesis", "theory"), ("Rizzolatti", "person"), ("1990s", "date"), ("premotor neurons", "concept")],
     [("mirror-neuron hypothesis", "Rizzolatti", "AUTHORED_BY")],
     "whose 1990s proposal tied premotor firing during observed action to action understanding",
     "mirror neuron premotor observation imitation Rizzolatti hypothesis macaque"),
    # --- 31 ---
    ("Hubel and Wiesel's critical-period experiments in kittens, published in the 1960s, showed that monocular deprivation permanently reshapes ocular-dominance columns.", "milestone", "knowledge", False,
     [("Hubel", "person"), ("Wiesel", "person"), ("critical-period experiments", "method"), ("1960s", "date"), ("ocular-dominance columns", "concept")],
     [("critical-period experiments", "Hubel", "AUTHORED_BY")],
     "whose 1960s kitten deprivation studies exposed a critical period in visual cortex wiring",
     "monocular deprivation ocular dominance kitten critical period sixties"),
    # --- 32 ---
    ("Adult neuroplasticity research extends Hebbian learning by showing that use-dependent cortical remapping continues long after developmental critical periods close.", "fact", "knowledge", False,
     [("Adult neuroplasticity", "concept"), ("Hebbian learning", "theory"), ("cortical remapping", "concept"), ("developmental critical periods", "concept")],
     [("Adult neuroplasticity", "Hebbian learning", "BUILDS_ON")],
     "which research programme extends Hebbian principles into adult cortical remapping after critical periods",
     "adult plasticity Hebbian remapping use dependent post critical period learning"),
    # --- 33 ---
    ("Dehaene's global neuronal workspace theory holds that conscious access arises from ignition of a distributed frontoparietal network broadcasting information to specialised modules.", "architecture", "knowledge", False,
     [("Dehaene", "person"), ("global neuronal workspace theory", "theory"), ("frontoparietal network", "concept"), ("conscious access", "concept")],
     [("global neuronal workspace theory", "Dehaene", "AUTHORED_BY")],
     "whose model ties awareness to a widespread prefrontal and parietal broadcast event",
     "global workspace ignition frontoparietal consciousness broadcasting Dehaene"),
    # --- 34. noise ---
    ("Hmm, I should recheck which Brodmann area corresponds to that coordinate.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Integrated information theory, formulated by Tononi in 2004, quantifies consciousness as the irreducible causal power phi of a physical system.", "milestone", "knowledge", False,
     [("Integrated information theory", "theory"), ("Tononi", "person"), ("2004", "date"), ("phi", "concept")],
     [("Integrated information theory", "Tononi", "AUTHORED_BY")],
     "when did the phi-based mathematical theory of consciousness first appear",
     "IIT phi integrated information Tononi consciousness measure year"),
    # --- 36 ---
    ("Shallice and Warrington's patient KF, reported in 1970, dissociated impaired short-term storage from intact long-term learning, challenging unitary memory models.", "fact", "knowledge", False,
     [("Shallice", "person"), ("Warrington", "person"), ("patient KF", "concept"), ("1970", "date")],
     [("patient KF", "Shallice", "AUTHORED_BY")],
     "which 1970 patient case separated short-term storage deficits from intact long-term learning",
     "patient KF short term long term dissociation neuropsychology year"),
    # --- 37 ---
    ("The Damasio somatic-marker hypothesis proposes that bodily feeling states bias decision-making via ventromedial prefrontal cortex.", "fact", "knowledge", False,
     [("Damasio", "person"), ("somatic-marker hypothesis", "theory"), ("ventromedial prefrontal cortex", "concept")],
     [("somatic-marker hypothesis", "Damasio", "AUTHORED_BY")],
     "whose hypothesis routes bodily feelings through vmPFC to bias rational choice",
     "somatic marker vmPFC feeling decision making Damasio hypothesis"),
    # --- 38 ---
    ("Kanwisher's 1997 report identified the fusiform face area as a cortical region selectively engaged by face stimuli relative to objects.", "milestone", "knowledge", False,
     [("Kanwisher", "person"), ("1997", "date"), ("fusiform face area", "concept")],
     [("fusiform face area", "Kanwisher", "AUTHORED_BY")],
     "when was a category-selective face-processing patch in fusiform cortex first pinpointed",
     "FFA fusiform face selective cortex Kanwisher fMRI year"),
    # --- 39 ---
    ("Kahneman's Thinking, Fast and Slow, published in 2011, split cognition into intuitive System 1 and deliberative System 2 modes of reasoning.", "reference", "knowledge", False,
     [("Kahneman", "person"), ("Thinking, Fast and Slow", "publication"), ("2011", "date"), ("System 1", "concept"), ("System 2", "concept")],
     [("Thinking, Fast and Slow", "Kahneman", "AUTHORED_BY")],
     "whose popular book contrasts snap-judgement thinking against painstaking analytic thought",
     "System 1 System 2 dual process fast slow Kahneman reasoning"),
    # --- 40 ---
    ("The Human Connectome Project, launched from Washington University in 2010, acquired high-resolution functional MRI from over a thousand healthy adults to map macroscale wiring.", "reference", "knowledge", False,
     [("Human Connectome Project", "project"), ("Washington University", "organization"), ("2010", "date"), ("functional MRI", "method")],
     [("Human Connectome Project", "Washington University", "DEPENDS_ON")],
     "which 2010 initiative scanned over a thousand adults to chart human macroscale brain wiring",
     "HCP diffusion functional MRI thousand adult macroscale wiring launch year"),
    # --- 41 ---
    ("Tsodyks and colleagues prefer spiking recurrent network models over rate-coded abstractions for capturing working-memory persistent activity.", "preference", "knowledge", False,
     [("Tsodyks", "person"), ("spiking recurrent network models", "method"), ("rate-coded abstractions", "method")],
     [("spiking recurrent network models", "rate-coded abstractions", "PREFERS")],
     "which modelling style does Tsodyks favour over rate-coded abstractions for persistent activity",
     "spiking recurrent network persistent activity working memory rate coded alternative"),
    # --- 42 ---
    ("Bayesian brain accounts generalise predictive coding by modelling perception as posterior inference over causes of sensory input.", "architecture", "knowledge", False,
     [("Bayesian brain accounts", "theory"), ("predictive coding", "theory"), ("posterior inference", "concept")],
     [("Bayesian brain accounts", "predictive coding", "BUILDS_ON")],
     "which statistical-inference view of the mind subsumes hierarchical prediction as a special case",
     "Bayesian brain posterior inference perception generative extension predictive"),
    # --- 43 ---
    ("CLARITY tissue clearing, introduced by Chung and Deisseroth at Stanford in 2013, renders intact brains optically transparent while preserving molecular architecture.", "milestone", "knowledge", False,
     [("CLARITY", "method"), ("Chung", "person"), ("Deisseroth", "person"), ("Stanford", "place"), ("2013", "date")],
     [("CLARITY", "Chung", "AUTHORED_BY")],
     "when did whole-brain optical clearing for intact-tissue imaging become available",
     "tissue clearing transparent brain intact molecular CLARITY year"),
    # --- 44 ---
    ("Friston's active-inference framework extends the free-energy principle to action, treating motor commands as predictions that the body fulfils to minimise sensory surprise.", "fact", "knowledge", False,
     [("active-inference framework", "framework"), ("free-energy principle", "theory"), ("motor commands", "concept")],
     [("active-inference framework", "free-energy principle", "BUILDS_ON")],
     "which extension of the free-energy principle reframes motor commands as self-fulfilling predictions",
     "active inference motor prediction free energy action framework extension"),
    # --- 45 ---
    ("Allen Brain Observatory data releases since 2016 provide standardised two-photon and Neuropixels recordings from the mouse visual system under common stimuli.", "reference", "knowledge", False,
     [("Allen Brain Observatory", "organization"), ("2016", "date"), ("two-photon", "method"), ("Neuropixels", "tool"), ("mouse visual system", "concept")],
     [],
     "which open initiative has shared standardised mouse visual cortex recordings since 2016",
     "Allen observatory open dataset mouse visual cortex standard stimulus release"),
    # --- 46 ---
    ("Diamond's ferret rewiring experiments in the late 1990s showed that retinal inputs routed to auditory thalamus can induce visual response properties in auditory cortex.", "fact", "knowledge", False,
     [("Diamond", "person"), ("ferret rewiring experiments", "method"), ("1990s", "date"), ("auditory cortex", "concept")],
     [("ferret rewiring experiments", "Diamond", "AUTHORED_BY")],
     "whose late-1990s ferret experiments showed auditory cortex adopting visual properties when rewired",
     "ferret rewiring cross modal auditory cortex visual input plasticity late nineties"),
    # --- 47 ---
    ("Spike-timing-dependent plasticity, characterised by Bi and Poo in 1998, updates synaptic weights according to the millisecond order of pre- and post-synaptic firing.", "milestone", "knowledge", False,
     [("Spike-timing-dependent plasticity", "concept"), ("Bi", "person"), ("Poo", "person"), ("1998", "date")],
     [("Spike-timing-dependent plasticity", "Bi", "AUTHORED_BY")],
     "when was synaptic weight change tied to millisecond spike timing order first quantified",
     "STDP pre post synaptic timing millisecond plasticity rule discovery year"),
    # --- 48 ---
    ("Patch-clamp electrophysiology, developed by Neher and Sakmann in the late 1970s, records ionic currents through single membrane channels.", "milestone", "knowledge", False,
     [("Patch-clamp electrophysiology", "method"), ("Neher", "person"), ("Sakmann", "person"), ("1970s", "date")],
     [("Patch-clamp electrophysiology", "Neher", "AUTHORED_BY")],
     "when did single-channel ionic-current recording via patch-clamp first become feasible",
     "patch clamp ionic current single channel Neher Sakmann seventies membrane"),
    # --- 49 ---
    ("Buckner's ageing and memory work links default mode network dysfunction to early Alzheimer amyloid deposition along the same cortical midline regions.", "fact", "knowledge", False,
     [("Buckner", "person"), ("default mode network", "concept"), ("Alzheimer", "concept"), ("amyloid deposition", "concept")],
     [("default mode network", "amyloid deposition", "DEPENDS_ON")],
     "whose senescence studies tie resting-network failure to where plaque shows up first in dementia",
     "Buckner ageing amyloid default mode Alzheimer midline deposition"),
    # --- 50 ---
    ("DTI tractography reconstructs white-matter pathways by modelling anisotropic water diffusion, enabling in vivo mapping of long-range fibre bundles.", "fact", "knowledge", False,
     [("DTI tractography", "method"), ("white-matter pathways", "concept"), ("anisotropic water diffusion", "concept")],
     [("DTI tractography", "anisotropic water diffusion", "DEPENDS_ON")],
     "which in-vivo method reconstructs long-range fibre bundles by modelling anisotropic water diffusion",
     "diffusion tensor tractography white matter anisotropic fibre bundle in vivo"),
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
