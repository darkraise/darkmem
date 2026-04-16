"""One-off emitter for shared-base batch-231 — knowledge domain (neuroscience: neurons, synapses, channels, neurotransmitters, LTP/LTD, hippocampus, cortex, basal ganglia, cerebellum, connectomics, optogenetics, imaging, engrams, Free Energy Principle).

Writes 50 rows to data/v2/shared/batch_231.tmp.jsonl with ids shared-11501..11550.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_231.tmp.jsonl"
ID_OFFSET = 11500

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 --- decision
    ("Adopted the Hodgkin-Huxley model as the canonical single-compartment membrane for the tutorial simulator; simpler leaky integrate-and-fire was kept only for the large-network examples where channel detail isn't pedagogically useful.", "decision", "knowledge", False,
     [("Hodgkin-Huxley", "theory"), ("leaky integrate-and-fire", "method")],
     [("Hodgkin-Huxley", "leaky integrate-and-fire", "REPLACES")],
     "which membrane model did the tutorial pick for single-cell detail versus large-network sketches",
     "hodgkin huxley leaky integrate fire membrane model simulator channel"),
    # --- 2 --- architecture
    ("The ionic channel layer composes sodium, potassium, and leak conductances additively on the axon compartment; calcium channels were split out into a separate module so dendritic spikes can be toggled without touching the axon code.", "architecture", "knowledge", False,
     [("sodium", "concept"), ("potassium", "concept"), ("calcium channels", "concept"), ("axon", "concept"), ("dendritic spikes", "concept")],
     [("calcium channels", "dendritic spikes", "APPLIES_TO")],
     "how is the ionic channel composition layered so dendritic calcium spikes can be toggled without touching axon logic",
     "sodium potassium calcium channel axon dendrite spike module conductance"),
    # --- 3 --- fact
    ("Glutamate is the primary excitatory neurotransmitter across cortex and hippocampus, and it signals through AMPA receptors for fast depolarisation and NMDA receptors for coincidence detection tied to plasticity.", "fact", "knowledge", False,
     [("Glutamate", "concept"), ("AMPA receptors", "concept"), ("NMDA receptors", "concept"), ("cortex", "concept"), ("hippocampus", "concept")],
     [("Glutamate", "AMPA receptors", "USES"), ("NMDA receptors", "Glutamate", "APPLIES_TO")],
     "which excitatory transmitter dominates cortex and hippocampus and how do its two main receptor families differ",
     "glutamate ampa nmda excitatory cortex hippocampus coincidence plasticity"),
    # --- 4 --- fact
    ("GABA is the main inhibitory transmitter in the vertebrate brain; GABA-A receptors gate chloride for fast shunting inhibition while GABA-B recruits G-proteins for slower potassium-mediated hyperpolarisation.", "fact", "knowledge", False,
     [("GABA", "concept"), ("GABA-A receptors", "concept"), ("GABA-B", "concept"), ("chloride", "concept"), ("potassium", "concept")],
     [("GABA-A receptors", "chloride", "USES"), ("GABA-B", "potassium", "USES")],
     "how do the two GABA receptor families split fast versus slow inhibition in the vertebrate brain",
     "gaba inhibitory chloride potassium gaba-a gaba-b g protein hyperpolar"),
    # --- 5 --- milestone
    ("Bliss and Lomo reported LTP in the rabbit dentate gyrus in 1973, establishing long-term potentiation as the first durable synaptic change observed after brief high-frequency stimulation of the perforant path.", "milestone", "knowledge", False,
     [("Bliss", "person"), ("Lomo", "person"), ("LTP", "finding"), ("dentate gyrus", "concept"), ("perforant path", "concept")],
     [("LTP", "Bliss", "AUTHORED_BY"), ("LTP", "Lomo", "AUTHORED_BY"), ("LTP", "dentate gyrus", "APPLIES_TO")],
     "who first reported long-term potentiation and in which hippocampal pathway did they see it",
     "bliss lomo ltp 1973 dentate perforant path rabbit synaptic potentiation"),
    # --- 6 --- milestone
    ("John O'Keefe discovered hippocampal place cells in the early 1970s by recording CA1 neurons that fired selectively when a rat occupied a specific location in an open arena.", "milestone", "knowledge", False,
     [("John O'Keefe", "person"), ("place cells", "finding"), ("CA1", "concept"), ("hippocampal", "concept")],
     [("place cells", "John O'Keefe", "AUTHORED_BY"), ("place cells", "CA1", "APPLIES_TO")],
     "who discovered place cells and in which hippocampal subfield were those recordings made",
     "okeefe place cell ca1 hippocampus rat arena location firing"),
    # --- 7 --- milestone
    ("May-Britt Moser and Edvard Moser reported grid cells in the medial entorhinal cortex in 2005; the hexagonal firing lattice gave the spatial coding story a metric that place cells alone could not provide.", "milestone", "knowledge", False,
     [("May-Britt Moser", "person"), ("Edvard Moser", "person"), ("grid cells", "finding"), ("medial entorhinal cortex", "concept")],
     [("grid cells", "May-Britt Moser", "AUTHORED_BY"), ("grid cells", "Edvard Moser", "AUTHORED_BY"), ("grid cells", "medial entorhinal cortex", "APPLIES_TO")],
     "which pair of researchers reported the hexagonal entorhinal firing lattice and in what year",
     "moser grid cell entorhinal 2005 hexagonal lattice spatial metric"),
    # --- 8 --- reference
    ("David Hubel and Torsten Wiesel classified V1 simple and complex cells in the late 1950s and 1960s; oriented bars drove simple cells with phase-sensitive receptive fields while complex cells tolerated translation.", "reference", "knowledge", False,
     [("David Hubel", "person"), ("Torsten Wiesel", "person"), ("V1", "concept"), ("simple cells", "concept"), ("complex cells", "concept")],
     [("simple cells", "David Hubel", "AUTHORED_BY"), ("complex cells", "Torsten Wiesel", "AUTHORED_BY")],
     "who characterised the V1 simple versus complex cell distinction and what stimulus drove the difference",
     "hubel wiesel v1 simple complex cell orientation bar receptive field"),
    # --- 9 --- fact
    ("Vernon Mountcastle described the cortical column as the basic functional unit of neocortex; vertical penetrations through somatosensory cortex yielded neurons sharing modality and receptive-field location, while tangential tracks did not.", "fact", "knowledge", False,
     [("Vernon Mountcastle", "person"), ("cortical column", "theory"), ("neocortex", "concept"), ("somatosensory cortex", "concept")],
     [("cortical column", "Vernon Mountcastle", "AUTHORED_BY")],
     "who proposed the cortical column as a unit of neocortex and what recording geometry anchored the claim",
     "mountcastle cortical column somatosensory neocortex vertical penetration"),
    # --- 10. noise ---
    ("The lab coffee machine developed a wheeze that three postdocs independently diagnosed as a calcified heating element before anyone checked the reservoir.", "fact", "noise", True, [], [], None, None),
    # --- 11 --- reference
    ("Santiago Ramón y Cajal's Golgi-stain drawings of cerebellar and cortical tissue are still cited as foundational evidence for the neuron doctrine; reproductions of the originals remain in circulation via the Cajal Institute archive.", "reference", "knowledge", False,
     [("Santiago Ramón y Cajal", "person"), ("Golgi-stain", "method"), ("neuron doctrine", "theory"), ("Cajal Institute", "organization")],
     [("neuron doctrine", "Santiago Ramón y Cajal", "AUTHORED_BY"), ("Santiago Ramón y Cajal", "Golgi-stain", "USES")],
     "whose stained-tissue drawings underpin the neuron doctrine and where are the originals archived",
     "cajal golgi stain neuron doctrine drawing archive histology institute"),
    # --- 12 --- decision
    ("Picked C. elegans as the first model for the connectomics chapter because White's 1986 reconstruction gives a complete wiring diagram of 302 neurons that students can actually load and query in a single lab session.", "decision", "knowledge", False,
     [("C. elegans", "concept"), ("White", "person"), ("connectomics", "field"), ("wiring diagram", "concept")],
     [("White", "C. elegans", "APPLIES_TO")],
     "which organism opens the connectomics chapter and why is its 1986 reconstruction still the teaching choice",
     "c elegans white 1986 connectome 302 neuron wiring diagram lab"),
    # --- 13 --- decision
    ("Adopted the FlyWire 2024 adult Drosophila connectome as the reference insect dataset for the whole-brain examples; earlier partial hemibrain volumes were retired because stitching them into the cross-hemisphere exercises was too brittle.", "decision", "knowledge", False,
     [("FlyWire", "organization"), ("Drosophila", "concept"), ("connectome", "concept")],
     [("FlyWire", "Drosophila", "APPLIES_TO"), ("FlyWire", "connectome", "PRODUCES")],
     "which project released the first whole-brain insect connectome and roughly how many neurons did it cover",
     "flywire drosophila connectome 2024 adult brain insect whole 140000"),
    # --- 14 --- milestone
    ("The MICrONS consortium published a cubic-millimetre mouse visual cortex reconstruction in 2025; dense EM reconstruction and functional two-photon imaging of the same tissue linked wiring to tuning at scale.", "milestone", "knowledge", False,
     [("MICrONS", "organization"), ("mouse visual cortex", "concept"), ("EM reconstruction", "method"), ("two-photon imaging", "method")],
     [("MICrONS", "mouse visual cortex", "APPLIES_TO"), ("MICrONS", "EM reconstruction", "USES"), ("MICrONS", "two-photon imaging", "USES")],
     "which consortium linked EM wiring with two-photon functional tuning in mouse visual cortex at the cubic-millimetre scale",
     "microns mouse visual cortex em two photon cubic millimetre 2025"),
    # --- 15 --- milestone
    ("Karl Deisseroth's lab established optogenetics as a standard tool by expressing channelrhodopsin-2 in targeted neurons in 2005, allowing millisecond-precise spiking control with blue light.", "milestone", "knowledge", False,
     [("Karl Deisseroth", "person"), ("optogenetics", "method"), ("channelrhodopsin-2", "concept")],
     [("optogenetics", "Karl Deisseroth", "AUTHORED_BY"), ("optogenetics", "channelrhodopsin-2", "USES")],
     "who made optogenetics a standard neural tool and which opsin enabled millisecond spiking control",
     "deisseroth optogenetics channelrhodopsin 2 blue light 2005 precision"),
    # --- 16 --- architecture
    ("The dopamine module in the teaching simulator is split into a VTA source, a nucleus accumbens target, and a prefrontal projection; the prediction-error signal is emitted by the VTA node and consumed by whichever downstream target the scenario selects.", "architecture", "knowledge", False,
     [("dopamine", "concept"), ("VTA", "concept"), ("nucleus accumbens", "concept"), ("prefrontal", "concept"), ("prediction-error", "concept")],
     [("VTA", "dopamine", "USES"), ("VTA", "prediction-error", "USES"), ("prediction-error", "nucleus accumbens", "APPLIES_TO")],
     "how is the dopamine module decomposed in the simulator and which node emits the prediction-error signal",
     "dopamine vta accumbens prefrontal prediction error simulator module"),
    # --- 17 --- milestone
    ("Wolfram Schultz showed in the 1990s that midbrain dopamine neurons encode a reward prediction error, firing to unexpected rewards and falling below baseline when an expected reward was omitted.", "milestone", "knowledge", False,
     [("Wolfram Schultz", "person"), ("dopamine", "concept"), ("reward prediction error", "theory"), ("midbrain", "concept")],
     [("reward prediction error", "Wolfram Schultz", "AUTHORED_BY"), ("dopamine", "reward prediction error", "USES")],
     "who showed midbrain dopamine neurons encode a reward prediction error and what baseline pattern identified it",
     "schultz dopamine reward prediction error midbrain omission baseline"),
    # --- 18 --- fact
    ("Serotonin neurons cluster in the raphe nuclei and project diffusely across cortex and subcortex; the 5-HT1A and 5-HT2A receptor subtypes account for the bulk of psychiatric drug targets.", "fact", "knowledge", False,
     [("Serotonin", "concept"), ("raphe nuclei", "concept"), ("5-HT1A", "concept"), ("5-HT2A", "concept")],
     [("Serotonin", "raphe nuclei", "APPLIES_TO")],
     "which brainstem cluster hosts serotonin cell bodies and which two receptor subtypes dominate psychiatric drug targets",
     "serotonin raphe 5ht1a 5ht2a receptor psychiatric projection diffuse"),
    # --- 19 --- fact
    ("Acetylcholine is the transmitter at the neuromuscular junction and is released by basal forebrain and brainstem nuclei to modulate cortical arousal and attention.", "fact", "knowledge", False,
     [("Acetylcholine", "concept"), ("neuromuscular junction", "concept"), ("basal forebrain", "concept"), ("brainstem", "concept")],
     [("Acetylcholine", "neuromuscular junction", "APPLIES_TO"), ("basal forebrain", "Acetylcholine", "USES")],
     "name the chemical at the muscle-nerve junction plus the forebrain source that tunes wakefulness via the same molecule",
     "ach muscle nerve junction wakeful attention ventral forebrain release"),
    # --- 20 --- fact
    ("Norepinephrine is released by the locus coeruleus and tunes cortical gain; phasic bursts track salient events while tonic levels shift the exploration-exploitation balance in behavioural tasks.", "fact", "knowledge", False,
     [("Norepinephrine", "concept"), ("locus coeruleus", "concept"), ("cortical gain", "concept")],
     [("locus coeruleus", "Norepinephrine", "USES"), ("Norepinephrine", "cortical gain", "APPLIES_TO")],
     "which brainstem nucleus supplies cortical norepinephrine and how do phasic versus tonic firing modes differ",
     "norepinephrine locus coeruleus cortical gain phasic tonic exploration"),
    # --- 21 --- decision
    ("Chose patch-clamp over sharp-electrode recording for the cellular-electrophysiology module; whole-cell access resistance is easier to monitor and the voltage-clamp mode gives clean ionic current traces for NMDA isolation.", "decision", "knowledge", False,
     [("patch-clamp", "method"), ("sharp-electrode", "method"), ("whole-cell", "method"), ("voltage-clamp", "method"), ("NMDA", "concept")],
     [("patch-clamp", "sharp-electrode", "REPLACES"), ("patch-clamp", "voltage-clamp", "USES")],
     "which cellular recording technique did the electrophysiology module adopt and why over sharp electrodes",
     "patch clamp sharp electrode whole cell voltage clamp nmda current"),
    # --- 22 --- decision
    ("Two-photon calcium imaging replaced one-photon wide-field for the intact cortex demos; the scattering-limited depth of one-photon couldn't reach layer 5 without bleaching the surface, while two-photon cleanly imaged 500 micrometres down.", "decision", "knowledge", False,
     [("two-photon", "method"), ("calcium imaging", "method"), ("one-photon", "method"), ("layer 5", "concept")],
     [("two-photon", "one-photon", "REPLACES"), ("two-photon", "layer 5", "APPLIES_TO")],
     "which imaging swap reached layer 5 without bleaching the cortical surface and what depth did it cover",
     "two photon calcium imaging one photon layer 5 depth scatter bleach"),
    # --- 23 --- decision
    ("Picked fMRI BOLD as the whole-brain coverage workhorse for the human-subject chapter; the hemodynamic lag and coarse spatial resolution were acceptable traded against non-invasive whole-brain maps that single-unit approaches can't deliver.", "decision", "knowledge", False,
     [("fMRI", "method"), ("BOLD", "concept"), ("hemodynamic", "concept")],
     [("fMRI", "BOLD", "USES")],
     "which signal does fMRI measure, what lag does it introduce, and how does its resolution trade off against coverage",
     "fmri bold oxygenation hemodynamic lag spatial resolution whole brain"),
    # --- 24 --- decision
    ("Chose MEG over EEG for the attention-timing experiments; both resolve cortical field potentials at millisecond scale but MEG's skull-conductivity immunity gave cleaner source localisation for the frontal generators the study targeted.", "decision", "knowledge", False,
     [("MEG", "method"), ("EEG", "method"), ("cortical field potentials", "concept")],
     [("MEG", "EEG", "PREFERS"), ("MEG", "cortical field potentials", "USES")],
     "which magnetic recording replaced EEG for attention-timing experiments and what advantage closed the choice",
     "meg eeg attention timing cortical field skull conductivity source local"),
    # --- 25 --- architecture
    ("The basal ganglia loop is modelled as a direct pathway that disinhibits thalamus via GPi suppression and an indirect pathway that suppresses thalamus via the subthalamic nucleus; dopamine biases which pathway dominates at the striatal input.", "architecture", "knowledge", False,
     [("basal ganglia", "concept"), ("direct pathway", "concept"), ("indirect pathway", "concept"), ("thalamus", "concept"), ("GPi", "concept"), ("subthalamic nucleus", "concept"), ("striatal", "concept")],
     [("direct pathway", "GPi", "USES"), ("indirect pathway", "subthalamic nucleus", "USES")],
     "how do the direct and indirect basal ganglia pathways arbitrate thalamic output and where does dopamine apply its bias",
     "basal ganglia direct indirect thalamus gpi subthalamic dopamine striatum"),
    # --- 26 --- architecture
    ("The cerebellum is modelled as a three-layer feedforward circuit: mossy-fibre inputs feed granule cells which drive parallel fibres onto Purkinje cells; climbing-fibre error signals from the inferior olive update the parallel-to-Purkinje synapse via LTD.", "architecture", "knowledge", False,
     [("cerebellum", "concept"), ("mossy-fibre", "concept"), ("granule cells", "concept"), ("parallel fibres", "concept"), ("Purkinje cells", "concept"), ("climbing-fibre", "concept"), ("inferior olive", "concept"), ("LTD", "finding")],
     [("climbing-fibre", "LTD", "USES"), ("inferior olive", "climbing-fibre", "USES"), ("granule cells", "parallel fibres", "USES")],
     "how is the cerebellar circuit layered and which synapse does the climbing-fibre error signal update",
     "cerebellum mossy granule parallel purkinje climbing olive ltd layer"),
    # --- 27 --- decision
    ("Modelled LTP and LTD as symmetric calcium-threshold rules at the same NMDA receptors synapse; the simulator dropped the earlier tag-and-capture heuristic because a single calcium threshold already reproduced the AMPA receptor insertion and internalisation trajectories.", "decision", "knowledge", False,
     [("LTP", "finding"), ("LTD", "finding"), ("NMDA receptors", "concept"), ("AMPA receptor", "concept")],
     [("LTP", "NMDA receptors", "USES"), ("LTD", "NMDA receptors", "USES"), ("LTP", "AMPA receptor", "APPLIES_TO")],
     "how do LTP and LTD both depend on NMDA calcium but drive opposite AMPA receptor outcomes at the same synapse",
     "ltp ltd nmda ampa calcium insertion internalisation synapse plasticity"),
    # --- 28 --- milestone
    ("Susumu Tonegawa's group demonstrated memory engrams in 2012 by optogenetically reactivating a sparse hippocampal neuron ensemble that had been tagged during fear conditioning, triggering freezing without the original cue.", "milestone", "knowledge", False,
     [("Susumu Tonegawa", "person"), ("memory engrams", "finding"), ("hippocampal", "concept"), ("fear conditioning", "concept"), ("optogenetically", "method")],
     [("memory engrams", "Susumu Tonegawa", "AUTHORED_BY"), ("memory engrams", "hippocampal", "APPLIES_TO")],
     "which group first reactivated a tagged hippocampal engram to trigger fear behaviour without the original cue",
     "tonegawa engram hippocampus fear conditioning optogenetic reactivate 2012"),
    # --- 29 --- reference
    ("Eve Marder's stomatogastric ganglion work is the reference for degenerate circuit solutions; the STG pyloric rhythm in crabs and lobsters can arise from dramatically different conductance combinations across individuals.", "reference", "knowledge", False,
     [("Eve Marder", "person"), ("stomatogastric ganglion", "concept"), ("pyloric rhythm", "concept"), ("STG", "concept")],
     [("Eve Marder", "stomatogastric ganglion", "APPLIES_TO"), ("stomatogastric ganglion", "pyloric rhythm", "USES")],
     "whose stomatogastric ganglion work anchors the degenerate-circuit story and which rhythm illustrates it",
     "marder stomatogastric stg pyloric rhythm crab lobster degenerate"),
    # --- 30 --- theory fact
    ("Karl Friston's Free Energy Principle frames perception and action as minimisation of variational free energy; predictive coding in cortex and active inference in motor systems are both presented as instances of the same underlying objective.", "fact", "knowledge", False,
     [("Karl Friston", "person"), ("Free Energy Principle", "theory"), ("predictive coding", "theory"), ("active inference", "theory")],
     [("Free Energy Principle", "Karl Friston", "AUTHORED_BY"), ("predictive coding", "Free Energy Principle", "APPLIES_TO"), ("active inference", "Free Energy Principle", "APPLIES_TO")],
     "whose unifying principle frames perception and action as variational free-energy minimisation",
     "friston free energy principle predictive coding active inference"),
    # --- 31 --- reference
    ("Henry Markram's Blue Brain Project published a reconstruction of neocortical microcircuitry in 2015; the paper details cell-type distributions and connectivity rules for a rodent somatosensory cortex volume.", "reference", "knowledge", False,
     [("Henry Markram", "person"), ("Blue Brain Project", "organization"), ("neocortical microcircuitry", "concept"), ("somatosensory cortex", "concept")],
     [("Henry Markram", "Blue Brain Project", "USES"), ("Blue Brain Project", "neocortical microcircuitry", "APPLIES_TO")],
     "which project published the 2015 rodent neocortical microcircuit reconstruction and who led it",
     "markram blue brain neocortical microcircuit 2015 somatosensory rodent"),
    # --- 32 --- reference
    ("The Allen Brain Atlas serves as the go-to reference for mouse-brain gene expression and cell-type taxonomies; its transcriptomic atlas indexes hundreds of excitatory and inhibitory types keyed to anatomical coordinates.", "reference", "knowledge", False,
     [("Allen Brain Atlas", "organization"), ("mouse-brain", "concept"), ("transcriptomic atlas", "publication"), ("cell-type taxonomies", "concept")],
     [("Allen Brain Atlas", "mouse-brain", "APPLIES_TO"), ("Allen Brain Atlas", "transcriptomic atlas", "USES")],
     "which atlas is the canonical reference for mouse-brain gene expression and cell-type taxonomy",
     "allen brain atlas mouse transcriptomic cell type taxonomy anatomy"),
    # --- 33 --- preference
    ("The author prefers introducing plasticity through LTP first and LTD second; the Bliss-Lomo anchor is a cleaner narrative hook than opening with cerebellar LTD, which requires climbing-fibre machinery students haven't seen yet.", "preference", "knowledge", False,
     [("LTP", "finding"), ("LTD", "finding"), ("Bliss-Lomo", "claim"), ("climbing-fibre", "concept")],
     [("LTP", "LTD", "PREFERS")],
     "why does the author introduce LTP before LTD in the plasticity chapter and which anchor does that opening use",
     "ltp ltd bliss lomo narrative cerebellar climbing fibre order teach"),
    # --- 34 --- preference
    ("Calcium imaging is preferred over multi-electrode arrays in the undergraduate lab section because cell-attached MEAs need perfusion chambers while GCaMP-expressing slices run on a standard upright microscope.", "preference", "knowledge", False,
     [("Calcium imaging", "method"), ("multi-electrode arrays", "method"), ("GCaMP", "concept"), ("MEAs", "method")],
     [("Calcium imaging", "multi-electrode arrays", "PREFERS")],
     "which recording technique does the undergraduate lab prefer and what hardware constraint pushed the choice",
     "calcium imaging multi electrode array gcamp slice undergraduate lab"),
    # --- 35 --- preference
    ("For the locomotion chapter the author prefers to frame the basal ganglia as action-selection machinery rather than as a pure reinforcement-learning box; the direct-indirect arbitration is easier to teach before introducing the dopamine prediction error.", "preference", "knowledge", False,
     [("basal ganglia", "concept"), ("action-selection", "theory"), ("reinforcement-learning", "theory"), ("dopamine", "concept"), ("prediction error", "concept")],
     [("action-selection", "reinforcement-learning", "PREFERS")],
     "which framing of the basal ganglia does the author prefer for teaching locomotion and why",
     "basal ganglia action selection reinforcement learning dopamine teach"),
    # --- 36 --- preference
    ("The preferred model organism for the optogenetics demos is the mouse rather than the rat; the transgenic Cre driver lines available for mouse let us target interneuron subclasses without viral infection and the arenas fit on a standard bench.", "preference", "knowledge", False,
     [("mouse", "concept"), ("rat", "concept"), ("optogenetics", "method"), ("Cre driver", "concept")],
     [("mouse", "rat", "PREFERS"), ("Cre driver", "mouse", "APPLIES_TO")],
     "which rodent does the optogenetics chapter prefer and which genetic toolset sealed the pick",
     "mouse rat optogenetics cre driver transgenic interneuron demo arena"),
    # --- 37 --- decision
    ("The synapse chapter uses the tripartite synapse framing where astrocytes actively modulate signalling; the purely-neuronal view was retired because it can't explain glutamate clearance timing or gliotransmission in the slice recordings.", "decision", "knowledge", False,
     [("tripartite synapse", "theory"), ("astrocytes", "concept"), ("gliotransmission", "concept"), ("glutamate clearance", "concept")],
     [("tripartite synapse", "astrocytes", "USES")],
     "which synaptic framing does the chapter adopt and what observations forced the purely-neuronal view out",
     "tripartite synapse astrocyte glia transmission glutamate clearance"),
    # --- 38 --- decision
    ("Chose NEURON over Brian for the multi-compartment modelling tutorials; Brian is cleaner for point neurons but NEURON's cable-equation solver and HOC morphology loader are still the standard for cerebellar Purkinje reconstructions.", "decision", "knowledge", False,
     [("NEURON", "method"), ("Brian", "method"), ("cable-equation", "theory"), ("Purkinje", "concept")],
     [("NEURON", "Brian", "PREFERS"), ("NEURON", "cable-equation", "USES")],
     "which simulator won the multi-compartment pick and why did Brian lose for Purkinje morphologies",
     "neuron brian simulator cable equation purkinje hoc morphology compartment"),
    # --- 39 --- decision
    ("Dropped ratiometric Fura-2 in favour of genetically-encoded GCaMP6f for the in-vivo two-photon demos; bulk loading with Fura-2 diluted signal across non-target cell types and limited long-term imaging windows.", "decision", "knowledge", False,
     [("Fura-2", "concept"), ("GCaMP6f", "concept"), ("two-photon", "method"), ("in-vivo", "concept")],
     [("GCaMP6f", "Fura-2", "REPLACES")],
     "which calcium indicator swap enabled long-term in-vivo two-photon windows and why was the ratiometric option retired",
     "gcamp6f fura 2 two photon in vivo calcium indicator long term"),
    # --- 40 --- decision
    ("Picked channelrhodopsin-2 for excitation and halorhodopsin for inhibition in the behavioural optogenetics chapter; the spectral separation lets the same animal receive opposing manipulations in alternating trials.", "decision", "knowledge", False,
     [("channelrhodopsin-2", "concept"), ("halorhodopsin", "concept"), ("optogenetics", "method")],
     [("optogenetics", "channelrhodopsin-2", "USES"), ("optogenetics", "halorhodopsin", "USES")],
     "which two opsins anchor the excitation and inhibition cases for the behavioural optogenetics chapter",
     "channelrhodopsin halorhodopsin optogenetics excite inhibit spectral trial"),
    # --- 41 --- architecture
    ("The hippocampal memory module is partitioned into CA3 as a recurrent auto-associator and CA1 as a pattern separator-completion readout; dentate gyrus sits upstream as the sparse encoder that feeds CA3 mossy-fibre inputs.", "architecture", "knowledge", False,
     [("hippocampal", "concept"), ("CA3", "concept"), ("CA1", "concept"), ("dentate gyrus", "concept"), ("mossy-fibre", "concept")],
     [("dentate gyrus", "CA3", "USES"), ("CA3", "CA1", "USES")],
     "how is the hippocampal memory module partitioned across dentate gyrus, CA3, and CA1 in the simulator",
     "hippocampus dentate ca3 ca1 recurrent auto associator pattern separate"),
    # --- 42 --- architecture
    ("The primary visual cortex layer pipeline stacks LGN inputs into layer 4 spiny stellate cells, projects to layers 2 and 3 pyramidal cells, and routes back through layer 5 for subcortical output; feedback from higher areas lands on layer 1.", "architecture", "knowledge", False,
     [("primary visual cortex", "concept"), ("LGN", "concept"), ("layer 4", "concept"), ("spiny stellate", "concept"), ("layer 5", "concept"), ("layer 1", "concept")],
     [("LGN", "layer 4", "USES"), ("layer 4", "spiny stellate", "USES")],
     "how does the V1 layer pipeline route LGN inputs through layer 4 and where does feedback from higher areas land",
     "v1 lgn layer 4 spiny stellate pyramidal layer 5 layer 1 feedback"),
    # --- 43. noise ---
    ("The departmental plant by the window has been slowly migrating toward the printer and nobody is willing to admit they're moving it.", "fact", "noise", True, [], [], None, None),
    # --- 44 --- architecture
    ("Prefrontal working-memory in the simulator uses recurrent attractor dynamics gated by dopamine tone; persistent activity during delay periods is maintained by NMDA-dominated recurrence while updates are timed by phasic dopamine bursts.", "architecture", "knowledge", False,
     [("Prefrontal", "concept"), ("working-memory", "concept"), ("attractor dynamics", "theory"), ("dopamine", "concept"), ("NMDA", "concept")],
     [("working-memory", "attractor dynamics", "USES"), ("NMDA", "attractor dynamics", "USES")],
     "which dynamics and transmitter combination holds prefrontal working-memory through delay periods in the simulator",
     "prefrontal working memory attractor dopamine nmda persistent delay"),
    # --- 45 --- architecture
    ("The reward-learning module composes a striatal actor with a dopaminergic critic; temporal-difference error from the critic drives plasticity on the cortico-striatal synapse that parameterises the actor's action policy.", "architecture", "knowledge", False,
     [("striatal actor", "concept"), ("dopaminergic critic", "concept"), ("temporal-difference", "theory"), ("cortico-striatal", "concept")],
     [("dopaminergic critic", "temporal-difference", "USES"), ("temporal-difference", "cortico-striatal", "APPLIES_TO")],
     "how is the actor-critic decomposition wired across striatum and dopamine in the reward-learning module",
     "striatum actor critic temporal difference cortico striatal reward"),
    # --- 46 --- architecture
    ("The sensory-motor loop for reaching tasks composes M1 pyramidal output with cerebellar feedback; cortical commands are sharpened by inverse-model corrections computed in the cerebellum and fed back through the thalamus.", "architecture", "knowledge", False,
     [("sensory-motor", "concept"), ("M1", "concept"), ("cerebellar", "concept"), ("inverse-model", "theory"), ("thalamus", "concept")],
     [("cerebellar", "inverse-model", "USES"), ("cerebellar", "thalamus", "USES")],
     "how does the reaching-task loop sharpen M1 output with cerebellar inverse-model corrections through the thalamus",
     "m1 cerebellum inverse model thalamus reaching pyramidal sensory motor"),
    # --- 47 --- problem
    ("The spike-sorting pipeline misclassified bursts from fast-spiking interneurons as two separate units; the fix clustered features per-channel and introduced a refractory-period sanity check that merged units with overlapping autocorrelograms.", "problem", "knowledge", False,
     [("spike-sorting", "method"), ("fast-spiking interneurons", "concept"), ("refractory-period", "concept"), ("autocorrelogram", "concept")],
     [("refractory-period", "spike-sorting", "FIXES")],
     "which spike-sorting bug split fast-spiking interneuron bursts into extra units and which sanity check corrected it",
     "spike sort fast spiking interneuron burst refractory autocorrelogram"),
    # --- 48 --- problem
    ("Motion artefact in the two-photon stack created phantom calcium transients correlated with the animal's running bouts; a rigid-body registration step followed by a running-speed regressor removed the spurious correlation.", "problem", "knowledge", False,
     [("Motion artefact", "concept"), ("two-photon", "method"), ("calcium transients", "concept"), ("rigid-body registration", "method")],
     [("rigid-body registration", "Motion artefact", "FIXES")],
     "which two-photon artefact produced running-locked phantom calcium transients and which correction retired it",
     "motion artefact two photon calcium run rigid body register regress"),
    # --- 49 --- problem
    ("The fMRI analysis pipeline was overclaiming significance at voxel level because the cluster-forming threshold wasn't corrected for multiple comparisons; switching to a permutation-based threshold-free cluster enhancement analysis restored honest false-positive rates.", "problem", "knowledge", False,
     [("fMRI", "method"), ("cluster-forming threshold", "concept"), ("multiple comparisons", "concept"), ("threshold-free cluster enhancement", "method")],
     [("threshold-free cluster enhancement", "multiple comparisons", "FIXES")],
     "which fMRI statistics bug inflated significance at voxel level and which cluster method fixed the false positives",
     "fmri voxel cluster threshold multiple comparison permutation tfce"),
    # --- 50 --- reference
    ("The Kandel Principles of Neural Science textbook is the default undergraduate reference across the synapse, cortex, and plasticity chapters; the sixth edition adds optogenetics and connectomics sections absent from earlier printings.", "reference", "knowledge", False,
     [("Kandel", "person"), ("Principles of Neural Science", "publication"), ("optogenetics", "method"), ("connectomics", "field")],
     [("Principles of Neural Science", "optogenetics", "APPLIES_TO"), ("Principles of Neural Science", "connectomics", "APPLIES_TO")],
     "which textbook is the undergraduate default across the synapse and cortex chapters and what did the sixth edition add",
     "kandel principles neural science textbook optogenetics connectomics"),
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
