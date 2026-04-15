"""One-off emitter for classification top-up batch-026 — short_ambiguous mode, knowledge slice.

Writes 100 rows to data/v2/classification/batch_026.tmp.jsonl with ids class-02501..02600.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_026.tmp.jsonl"
ID_OFFSET = 2500

# (text, domain, memory_type) — no pair_id
ROWS: list[tuple[str, str, str]] = [
    # --- fact (~14) ---
    ("Water boils at 100 degrees Celsius at sea level.", "knowledge", "fact"),
    ("Mitochondria produce ATP in eukaryotic cells.", "knowledge", "fact"),
    ("The Berlin Wall fell in 1989.", "knowledge", "fact"),
    ("Light travels roughly 300,000 kilometers per second.", "knowledge", "fact"),
    ("Humans share about 98% of DNA with chimpanzees.", "knowledge", "fact"),
    ("Jupiter is the largest planet in the solar system.", "knowledge", "fact"),
    ("The Roman Empire split permanently in 395 AD.", "knowledge", "fact"),
    ("Insulin regulates blood glucose levels.", "knowledge", "fact"),
    ("Prime numbers have exactly two divisors.", "knowledge", "fact"),
    ("Shakespeare died in 1616.", "knowledge", "fact"),
    ("Sound travels faster in water than in air.", "knowledge", "fact"),
    ("The human brain contains about 86 billion neurons.", "knowledge", "fact"),
    ("Mandarin has four tones plus a neutral tone.", "knowledge", "fact"),
    ("Gold has atomic number 79.", "knowledge", "fact"),

    # --- decision (~14) ---
    ("The Fed decided to hold rates steady.", "knowledge", "decision"),
    ("Caesar chose to cross the Rubicon.", "knowledge", "decision"),
    ("The committee adopted the metric system nationwide.", "knowledge", "decision"),
    ("Darwin delayed publishing On the Origin of Species.", "knowledge", "decision"),
    ("The university switched to a pass-fail grading policy.", "knowledge", "decision"),
    ("NASA chose Falcon 9 for crew transport.", "knowledge", "decision"),
    ("The ECB voted to cut rates by 25 basis points.", "knowledge", "decision"),
    ("The board approved funding the new particle collider.", "knowledge", "decision"),
    ("The WHO declared the outbreak a pandemic.", "knowledge", "decision"),
    ("The journal retracted the disputed paper.", "knowledge", "decision"),
    ("The court ruled in favor of the defendant.", "knowledge", "decision"),
    ("The APA adopted new diagnostic criteria for PTSD.", "knowledge", "decision"),
    ("Congress passed the Civil Rights Act in 1964.", "knowledge", "decision"),
    ("The IAU reclassified Pluto as a dwarf planet.", "knowledge", "decision"),

    # --- preference (~14) ---
    ("Aristotle preferred deduction over induction.", "knowledge", "preference"),
    ("Keynesians favor fiscal stimulus during recessions.", "knowledge", "preference"),
    ("Structuralists prefer systemic explanations.", "knowledge", "preference"),
    ("Behaviorists favor observable over mental phenomena.", "knowledge", "preference"),
    ("Formalists prefer syntax over semantics.", "knowledge", "preference"),
    ("Clinicians prefer ICD-11 over DSM-5 in Europe.", "knowledge", "preference"),
    ("Bayesians prefer priors to frequentist intervals.", "knowledge", "preference"),
    ("Continental philosophers lean toward phenomenology.", "knowledge", "preference"),
    ("Physicists prefer SI units over imperial.", "knowledge", "preference"),
    ("Ecologists favor long-term field studies.", "knowledge", "preference"),
    ("Historians prefer primary sources when available.", "knowledge", "preference"),
    ("Monetarists favor controlling the money supply.", "knowledge", "preference"),
    ("Cognitivists prefer mental models to stimulus-response.", "knowledge", "preference"),
    ("Mathematicians prefer constructive proofs when possible.", "knowledge", "preference"),

    # --- problem (~14) ---
    ("The replication crisis plagues social psychology.", "knowledge", "problem"),
    ("Dark matter remains undetected directly.", "knowledge", "problem"),
    ("Antibiotic resistance is rising globally.", "knowledge", "problem"),
    ("The P versus NP question is still open.", "knowledge", "problem"),
    ("Inflation eroded real wages last decade.", "knowledge", "problem"),
    ("Coral reefs are bleaching at record rates.", "knowledge", "problem"),
    ("Alzheimer's has no disease-modifying cure.", "knowledge", "problem"),
    ("Measurement of consciousness remains elusive.", "knowledge", "problem"),
    ("The Riemann hypothesis resists proof.", "knowledge", "problem"),
    ("Pollination is declining with bee populations.", "knowledge", "problem"),
    ("Historical sources on prehistory are sparse.", "knowledge", "problem"),
    ("Supply chains buckled during the pandemic.", "knowledge", "problem"),
    ("Language endangerment threatens half of world tongues.", "knowledge", "problem"),
    ("Sepsis remains a leading ICU killer.", "knowledge", "problem"),

    # --- reference (~14) ---
    ("See Principia Mathematica for the classical formulation.", "knowledge", "reference"),
    ("System 1 and System 2, per Kahneman 2011.", "knowledge", "reference"),
    ("Loss aversion, per Kahneman 2011.", "knowledge", "reference"),
    ("Opportunity cost, per Mankiw textbook chapter 1.", "knowledge", "reference"),
    ("Per Einstein 1905, time is relative.", "knowledge", "reference"),
    ("The Krebs cycle, per Lehninger 8th edition.", "knowledge", "reference"),
    ("Per Piaget 1952, children construct schemas.", "knowledge", "reference"),
    ("Universal grammar, per Chomsky 1965.", "knowledge", "reference"),
    ("Per Darwin 1859, species descend with modification.", "knowledge", "reference"),
    ("Germ theory, per Pasteur's 1861 experiments.", "knowledge", "reference"),
    ("Per Hubble 1929, galaxies recede proportionally.", "knowledge", "reference"),
    ("The invisible hand, per Smith 1776.", "knowledge", "reference"),
    ("Per Turing 1936, some problems are undecidable.", "knowledge", "reference"),
    ("Cognitive dissonance, per Festinger 1957.", "knowledge", "reference"),

    # --- architecture (~14) ---
    ("Neurons connect via synapses into cortical circuits.", "knowledge", "architecture"),
    ("The cell membrane is a phospholipid bilayer.", "knowledge", "architecture"),
    ("The Roman Senate sat atop the cursus honorum.", "knowledge", "architecture"),
    ("Markets aggregate signals through the price system.", "knowledge", "architecture"),
    ("Plato's tripartite soul layers reason, spirit, appetite.", "knowledge", "architecture"),
    ("Working memory feeds into long-term consolidation.", "knowledge", "architecture"),
    ("Syntax trees branch from phrases into heads.", "knowledge", "architecture"),
    ("The heart pumps blood through two parallel circuits.", "knowledge", "architecture"),
    ("Axiomatic systems build theorems from primitive rules.", "knowledge", "architecture"),
    ("Stars form in molecular clouds and ignite fusion.", "knowledge", "architecture"),
    ("DNA winds around histones into nucleosomes.", "knowledge", "architecture"),
    ("The feudal pyramid placed lords above vassals.", "knowledge", "architecture"),
    ("Central banks sit atop commercial banking systems.", "knowledge", "architecture"),
    ("Phonemes combine into morphemes then words.", "knowledge", "architecture"),

    # --- milestone (~16 to reach 100) ---
    ("Humans first walked on the Moon in 1969.", "knowledge", "milestone"),
    ("Smallpox was declared eradicated in 1980.", "knowledge", "milestone"),
    ("The Human Genome Project finished in 2003.", "knowledge", "milestone"),
    ("The Higgs boson was confirmed in 2012.", "knowledge", "milestone"),
    ("Gravitational waves were first detected in 2015.", "knowledge", "milestone"),
    ("Penicillin entered mass production in 1944.", "knowledge", "milestone"),
    ("Fermat's Last Theorem was proved in 1994.", "knowledge", "milestone"),
    ("Rosetta Stone was deciphered by Champollion in 1822.", "knowledge", "milestone"),
    ("Double helix structure was published in 1953.", "knowledge", "milestone"),
    ("The first black hole was imaged in 2019.", "knowledge", "milestone"),
    ("Germany reunified on October 3, 1990.", "knowledge", "milestone"),
    ("The euro entered circulation in 2002.", "knowledge", "milestone"),
    ("AlphaFold solved protein folding in 2021.", "knowledge", "milestone"),
    ("The Magna Carta was sealed in 1215.", "knowledge", "milestone"),
    ("General relativity was published in 1915.", "knowledge", "milestone"),
    ("The first CRISPR edit in humans was reported in 2016.", "knowledge", "milestone"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
