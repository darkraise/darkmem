"""One-off emitter for classification top-up batch-001 — contrastive_reference_fact mode, science and engineering slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_001.tmp.jsonl with ids class-00001..00100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_001.tmp.jsonl"
ID_OFFSET = 0
PAIR_OFFSET = 0

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text MUST contain a citable source (named paper + year, DOI, named standards body, named peer-reviewed journal).
# fact_text MUST NOT contain a citation — it is the same underlying fact stated without the source.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Higgs boson discovery (particle physics)
    (
        "The ATLAS collaboration reported observation of a new boson near 125 GeV in Phys. Lett. B 716 (2012) 1-29, consistent with the Standard Model Higgs. The CMS collaboration independently confirmed the result in the same issue.",
        "knowledge",
        "A Higgs-like boson with a mass near 125 GeV was observed at the Large Hadron Collider in 2012, consistent with the prediction of the Standard Model of particle physics.",
        "knowledge",
    ),
    # 2. Gravitational waves (astrophysics)
    (
        "Abbott et al. (LIGO Scientific Collaboration), Phys. Rev. Lett. 116, 061102 (2016), reported GW150914, the first direct detection of gravitational waves from a binary black hole merger.",
        "knowledge",
        "The first direct detection of gravitational waves came from a binary black hole merger observed in September 2015, confirming a century-old prediction of general relativity.",
        "knowledge",
    ),
    # 3. CRISPR-Cas9 genome editing (molecular biology)
    (
        "Jinek, Chylinski, Fonfara, Hauer, Doudna, and Charpentier demonstrated programmable dual-RNA-guided DNA cleavage by Cas9 in Science 337 (2012) 816-821, enabling modern CRISPR genome editing.",
        "knowledge",
        "A bacterial Cas9 nuclease can be programmed with a guide RNA to cut specific DNA sequences, and this mechanism forms the basis of modern genome editing.",
        "knowledge",
    ),
    # 4. Shannon information theory (CS theory)
    (
        "Claude Shannon's 1948 paper 'A Mathematical Theory of Communication' in the Bell System Technical Journal established channel capacity C = B log2(1 + S/N) for an additive white Gaussian noise channel.",
        "knowledge",
        "The maximum error-free data rate over a bandwidth-limited channel with additive Gaussian noise is proportional to the bandwidth times the logarithm of one plus the signal-to-noise ratio.",
        "knowledge",
    ),
    # 5. Transformer architecture (ML research)
    (
        "Vaswani et al., 'Attention Is All You Need', NeurIPS 2017 (arXiv:1706.03762), introduced the Transformer architecture that replaced recurrence with scaled dot-product self-attention.",
        "ai_coding",
        "The Transformer architecture replaced recurrent connections with a self-attention mechanism and became the dominant backbone for large language models.",
        "ai_coding",
    ),
    # 6. ImageNet / AlexNet (deep learning)
    (
        "Krizhevsky, Sutskever, and Hinton, 'ImageNet Classification with Deep Convolutional Neural Networks', NIPS 2012, achieved a top-5 error of 15.3 percent on ILSVRC, far below the 26.2 percent of the runner-up.",
        "ai_coding",
        "A deep convolutional neural network trained on GPUs dramatically improved image classification accuracy on the ImageNet benchmark in 2012, sparking the modern deep learning era.",
        "ai_coding",
    ),
    # 7. Speed of light (metrology / physics)
    (
        "The 17th CGPM (1983) fixed the speed of light in vacuum at exactly 299,792,458 m/s and redefined the metre accordingly, a definition maintained by the SI brochure published by the BIPM.",
        "knowledge",
        "The speed of light in vacuum is exactly 299,792,458 metres per second, and the metre is defined in terms of this constant.",
        "knowledge",
    ),
    # 8. DNA double helix (structural biology)
    (
        "Watson and Crick described the double-helical structure of DNA with antiparallel strands held by base pairing in Nature 171 (1953) 737-738.",
        "knowledge",
        "Deoxyribonucleic acid is structured as two antiparallel strands wound into a double helix, held together by complementary base pairing.",
        "knowledge",
    ),
    # 9. Expansion of the universe (cosmology)
    (
        "Edwin Hubble's 1929 paper in PNAS 15, 168-173, reported a linear relation between galactic recession velocity and distance, establishing what is now called Hubble's law.",
        "knowledge",
        "Distant galaxies recede from the Milky Way at velocities roughly proportional to their distance, indicating that the universe is expanding.",
        "knowledge",
    ),
    # 10. Plate tectonics (earth science)
    (
        "Vine and Matthews, Nature 199 (1963) 947-949, interpreted symmetric magnetic anomalies flanking mid-ocean ridges as evidence for seafloor spreading, a cornerstone of plate tectonics.",
        "knowledge",
        "Symmetric stripes of alternating magnetic polarity on either side of mid-ocean ridges show that new oceanic crust forms at the ridges and spreads outward.",
        "knowledge",
    ),
    # 11. Graphene isolation (materials science)
    (
        "Novoselov, Geim, and colleagues reported isolation of single-atom-thick graphene by mechanical exfoliation in Science 306 (2004) 666-669, work recognized by the 2010 Nobel Prize in Physics.",
        "knowledge",
        "Graphene, a single-atom-thick sheet of carbon arranged in a hexagonal lattice, was first isolated in 2004 by mechanically exfoliating graphite with adhesive tape.",
        "knowledge",
    ),
    # 12. High-temperature superconductivity (condensed matter)
    (
        "Bednorz and Muller reported superconductivity above 30 K in Ba-La-Cu-O in Z. Phys. B 64 (1986) 189-193, launching the field of high-temperature cuprate superconductors.",
        "knowledge",
        "Certain copper-oxide ceramics become superconducting at temperatures well above the liquid helium range, unlike conventional BCS superconductors.",
        "knowledge",
    ),
    # 13. Ozone hole (atmospheric chemistry)
    (
        "Farman, Gardiner, and Shanklin reported large seasonal losses of total ozone over Halley Bay, Antarctica in Nature 315 (1985) 207-210, the first observation of the ozone hole.",
        "knowledge",
        "A severe seasonal depletion of stratospheric ozone occurs over Antarctica each southern spring, driven largely by chlorine chemistry from human-made halocarbons.",
        "knowledge",
    ),
    # 14. Penicillin (pharmacology / microbiology)
    (
        "Alexander Fleming reported the antibacterial action of a Penicillium mold against staphylococci in Br. J. Exp. Pathol. 10 (1929) 226-236, the foundational paper on penicillin.",
        "knowledge",
        "Penicillin is an antibiotic produced by a Penicillium mold that kills many species of bacteria by disrupting cell wall synthesis.",
        "knowledge",
    ),
    # 15. mRNA vaccines (biotech)
    (
        "Polack et al., NEJM 383 (2020) 2603-2615, reported 95 percent efficacy of the BNT162b2 mRNA vaccine against COVID-19 in a randomized placebo-controlled trial of over 43,000 participants.",
        "knowledge",
        "An mRNA vaccine encoding the SARS-CoV-2 spike protein was shown to be highly effective at preventing symptomatic COVID-19 in large randomized clinical trials.",
        "knowledge",
    ),
    # 16. RSA cryptosystem (cryptography)
    (
        "Rivest, Shamir, and Adleman, 'A Method for Obtaining Digital Signatures and Public-Key Cryptosystems', Commun. ACM 21 (1978) 120-126, introduced the RSA cryptosystem based on the hardness of integer factorization.",
        "technical",
        "The RSA public-key cryptosystem is secure under the assumption that factoring the product of two large primes is computationally intractable.",
        "technical",
    ),
    # 17. AES cipher (cryptography / standards)
    (
        "The Advanced Encryption Standard was specified by NIST in FIPS PUB 197 (2001) based on the Rijndael block cipher designed by Daemen and Rijmen.",
        "technical",
        "The Advanced Encryption Standard is a symmetric block cipher with a 128-bit block and key sizes of 128, 192, or 256 bits, widely used to encrypt data at rest and in transit.",
        "technical",
    ),
    # 18. TCP congestion control (networking)
    (
        "Van Jacobson, 'Congestion Avoidance and Control', SIGCOMM 1988, introduced slow start, congestion avoidance, fast retransmit, and fast recovery, now core to TCP.",
        "technical",
        "TCP detects network congestion from packet loss and duplicate acknowledgements and responds by reducing its sending window, then slowly ramping back up.",
        "technical",
    ),
    # 19. Paxos consensus (distributed systems)
    (
        "Leslie Lamport, 'The Part-Time Parliament', ACM TOCS 16 (1998) 133-169, described the Paxos algorithm for reaching consensus in an asynchronous network with crash failures.",
        "technical",
        "Paxos is a fault-tolerant consensus algorithm that lets a set of distributed processes agree on a single value despite crash failures and message loss.",
        "technical",
    ),
    # 20. MapReduce (distributed systems)
    (
        "Dean and Ghemawat, 'MapReduce: Simplified Data Processing on Large Clusters', OSDI 2004, described Google's programming model for parallel batch processing on commodity clusters.",
        "technical",
        "MapReduce is a programming model for processing large datasets on a cluster by expressing a computation as a map function followed by a shuffle and a reduce function.",
        "technical",
    ),
    # 21. Dijkstra shortest path (algorithms)
    (
        "Edsger Dijkstra, 'A Note on Two Problems in Connexion with Graphs', Numerische Mathematik 1 (1959) 269-271, presented the single-source shortest path algorithm that bears his name.",
        "technical",
        "Dijkstra's algorithm computes shortest paths from a single source in a graph with non-negative edge weights by repeatedly extracting the nearest unvisited vertex.",
        "technical",
    ),
    # 22. Navier-Stokes existence (mathematics / fluid dynamics)
    (
        "The Clay Mathematics Institute lists the existence and smoothness of solutions to the three-dimensional incompressible Navier-Stokes equations as one of the Millennium Prize Problems.",
        "knowledge",
        "Whether smooth global solutions always exist for the three-dimensional incompressible Navier-Stokes equations with smooth initial data remains an open problem in mathematics.",
        "knowledge",
    ),
    # 23. General relativity (gravitation)
    (
        "Einstein presented the field equations of general relativity in Sitzungsber. Preuss. Akad. Wiss. (1915) 844-847, relating spacetime curvature to the stress-energy tensor.",
        "knowledge",
        "General relativity describes gravity as the curvature of four-dimensional spacetime caused by the distribution of energy and momentum.",
        "knowledge",
    ),
    # 24. Exoplanet 51 Pegasi b (astronomy)
    (
        "Mayor and Queloz, Nature 378 (1995) 355-359, reported the discovery of 51 Pegasi b, the first exoplanet detected orbiting a main-sequence star, by radial velocity measurements.",
        "knowledge",
        "The first confirmed exoplanet around a Sun-like star was detected in 1995 by measuring periodic Doppler shifts in the host star's spectrum.",
        "knowledge",
    ),
    # 25. Cosmic microwave background (cosmology)
    (
        "Penzias and Wilson, ApJ 142 (1965) 419-421, reported an isotropic 3.5 K excess antenna temperature at 4080 Mc/s, identified by Dicke et al. as the cosmic microwave background.",
        "knowledge",
        "The cosmic microwave background is a nearly isotropic microwave radiation with a blackbody temperature of about 2.7 Kelvin, a relic of the early hot universe.",
        "knowledge",
    ),
    # 26. Moore's law (semiconductor engineering)
    (
        "Gordon Moore, 'Cramming More Components onto Integrated Circuits', Electronics 38 (1965) 114-117, projected that the number of components per integrated circuit would double roughly every year.",
        "technical",
        "For several decades the number of transistors on a commercial integrated circuit doubled approximately every two years, an empirical trend that shaped the semiconductor industry.",
        "technical",
    ),
    # 27. Quicksort (algorithms)
    (
        "C. A. R. Hoare, 'Quicksort', Computer Journal 5 (1962) 10-16, described the partition-based sorting algorithm with average O(n log n) running time.",
        "technical",
        "Quicksort is a comparison-based sorting algorithm that recursively partitions an array around a pivot and runs in O(n log n) average time.",
        "technical",
    ),
    # 28. Turing machine (computability)
    (
        "Alan Turing, 'On Computable Numbers, with an Application to the Entscheidungsproblem', Proc. London Math. Soc. s2-42 (1937) 230-265, introduced the Turing machine and proved the undecidability of the halting problem.",
        "knowledge",
        "There is no general algorithm that can decide, for every program and input, whether the program eventually halts.",
        "knowledge",
    ),
    # 29. Polymerase chain reaction (molecular biology)
    (
        "Saiki, Mullis et al., Science 230 (1985) 1350-1354, reported the polymerase chain reaction for enzymatic amplification of specific DNA sequences.",
        "knowledge",
        "The polymerase chain reaction exponentially amplifies a targeted DNA segment through repeated cycles of denaturation, primer annealing, and enzymatic extension.",
        "knowledge",
    ),
    # 30. Photovoltaic effect / solar cell (EE / materials)
    (
        "Chapin, Fuller, and Pearson, J. Appl. Phys. 25 (1954) 676-677, described the first practical silicon p-n junction solar cell with about 6 percent efficiency.",
        "technical",
        "A silicon p-n junction exposed to sunlight generates an electric current through the photovoltaic effect, forming the basis of modern solar cells.",
        "technical",
    ),
    # 31. Lithium-ion battery (electrochemistry / EE)
    (
        "Goodenough and co-workers reported the LiCoO2 cathode in Mater. Res. Bull. 15 (1980) 783-789, a foundational result for the commercial lithium-ion battery recognized by the 2019 Nobel Prize in Chemistry.",
        "technical",
        "Modern lithium-ion batteries use a layered lithium cobalt oxide cathode paired with a carbon anode and a lithium-salt electrolyte to achieve high energy density.",
        "technical",
    ),
    # 32. LIGO interferometer design (instrumentation / optics)
    (
        "LIGO Scientific Collaboration, 'Advanced LIGO', Class. Quantum Grav. 32 (2015) 074001, describes the dual-recycled Fabry-Perot Michelson interferometers with 4 km arms.",
        "technical",
        "LIGO detects gravitational waves using kilometre-scale Michelson interferometers with Fabry-Perot cavities in each arm to amplify the signal from passing strains.",
        "technical",
    ),
    # 33. Black hole image (astronomy / imaging)
    (
        "The Event Horizon Telescope Collaboration, ApJ Lett. 875 (2019) L1, published the first resolved image of the supermassive black hole M87* using very long baseline interferometry at 1.3 mm.",
        "knowledge",
        "A global network of millimetre-wavelength radio telescopes produced the first resolved image of the shadow of a supermassive black hole at the centre of the galaxy M87.",
        "knowledge",
    ),
    # 34. James Webb Space Telescope (aerospace / astronomy)
    (
        "Gardner et al., Space Science Reviews 123 (2006) 485-606, described the mission concept for the James Webb Space Telescope, a 6.5 m segmented infrared observatory at Sun-Earth L2.",
        "knowledge",
        "The James Webb Space Telescope is a 6.5 metre segmented infrared observatory parked near the Sun-Earth L2 Lagrange point, designed to observe the early universe.",
        "knowledge",
    ),
    # 35. Apollo 11 lunar landing (aerospace)
    (
        "NASA mission report MR-5, 'Apollo 11 Mission Report' (MSC-00171, 1969), documents the first crewed lunar landing on 20 July 1969 by Armstrong and Aldrin aboard the Eagle lunar module.",
        "knowledge",
        "The first crewed landing on the Moon occurred on 20 July 1969 when the Apollo 11 lunar module Eagle touched down in the Sea of Tranquility.",
        "knowledge",
    ),
    # 36. Bridge collapse / resonance (civil engineering)
    (
        "The Washington State Report, 'The Failure of the Tacoma Narrows Bridge', Federal Works Agency (1941), documented the 7 November 1940 collapse as an aeroelastic flutter failure.",
        "technical",
        "The Tacoma Narrows Bridge collapsed on 7 November 1940 due to aeroelastic flutter, where wind-induced oscillations coupled destructively with the deck's torsional mode.",
        "technical",
    ),
    # 37. Dark matter rotation curves (astrophysics)
    (
        "Rubin and Ford, ApJ 159 (1970) 379-403, measured flat rotation curves of the Andromeda galaxy M31, providing strong evidence for extended dark matter halos.",
        "knowledge",
        "Rotation curves of spiral galaxies stay roughly flat at large radii instead of falling off, implying the presence of an extended halo of unseen matter.",
        "knowledge",
    ),
    # 38. Maxwell's equations (classical EM)
    (
        "James Clerk Maxwell, 'A Dynamical Theory of the Electromagnetic Field', Phil. Trans. R. Soc. 155 (1865) 459-512, unified electricity, magnetism, and light into a single field theory.",
        "knowledge",
        "Electric and magnetic fields are coupled and their dynamics obey a set of four linear partial differential equations, which also predict electromagnetic waves traveling at the speed of light.",
        "knowledge",
    ),
    # 39. Periodic table (chemistry)
    (
        "Dmitri Mendeleev, Zeitschrift fur Chemie 12 (1869) 405-406, proposed the first widely adopted periodic classification of the elements by atomic weight and recurring chemical properties.",
        "knowledge",
        "The chemical elements can be arranged in a table where columns group elements with similar chemical properties and rows correspond to filling of electron shells.",
        "knowledge",
    ),
    # 40. Haber-Bosch process (chemical engineering)
    (
        "Fritz Haber's 1918 Nobel lecture described the synthesis of ammonia from nitrogen and hydrogen over an iron catalyst at high pressure, industrialized by Carl Bosch at BASF.",
        "technical",
        "Ammonia is produced industrially by combining nitrogen and hydrogen gas at high temperature and pressure over an iron-based catalyst, enabling modern fertilizer production.",
        "technical",
    ),
    # 41. Black-Scholes option pricing (quantitative finance / applied math)
    (
        "Black and Scholes, J. Political Economy 81 (1973) 637-654, derived the closed-form price of a European option under geometric Brownian motion and no arbitrage.",
        "knowledge",
        "Under assumptions of geometric Brownian motion for the underlying asset and no arbitrage, the price of a European option is given by a closed-form formula.",
        "knowledge",
    ),
    # 42. BGP routing (internet infrastructure)
    (
        "Rekhter, Li, and Hares, RFC 4271, 'A Border Gateway Protocol 4 (BGP-4)', IETF (2006), specifies the path-vector routing protocol used between autonomous systems on the Internet.",
        "technical",
        "The Border Gateway Protocol is the path-vector routing protocol that exchanges reachability information between autonomous systems and determines the topology of the global Internet.",
        "technical",
    ),
    # 43. TLS 1.3 (security standards)
    (
        "Eric Rescorla, RFC 8446, 'The Transport Layer Security (TLS) Protocol Version 1.3', IETF (2018), specifies the cipher-suite negotiation, handshake, and key schedule for TLS 1.3.",
        "technical",
        "TLS 1.3 reduces the handshake to one round trip, drops legacy cipher suites, and always provides forward secrecy through ephemeral Diffie-Hellman key exchange.",
        "technical",
    ),
    # 44. IEEE 754 floating point (computer arithmetic)
    (
        "IEEE Std 754-2008 specifies the binary and decimal floating-point formats, rounding rules, and exceptional value handling used on essentially all modern CPUs and GPUs.",
        "technical",
        "The widely used binary32 and binary64 floating-point formats define a 1-bit sign, an exponent field, and a fraction field, together with rules for rounding and for infinities and NaNs.",
        "technical",
    ),
    # 45. Nyquist-Shannon sampling theorem (signal processing)
    (
        "Harry Nyquist, Trans. AIEE 47 (1928) 617-644, showed that a band-limited signal of bandwidth B can be reconstructed from samples taken at a rate of at least 2B per second.",
        "technical",
        "A continuous signal that contains no frequencies above B hertz can be perfectly reconstructed from samples taken at a rate of at least twice B per second.",
        "technical",
    ),
    # 46. Protein structure prediction AlphaFold (bioinformatics)
    (
        "Jumper et al., 'Highly accurate protein structure prediction with AlphaFold', Nature 596 (2021) 583-589, reported near-experimental accuracy on the CASP14 targets.",
        "ai_coding",
        "Deep learning models can now predict the three-dimensional structure of most proteins from their amino-acid sequence with accuracy approaching experimental methods.",
        "ai_coding",
    ),
    # 47. Human genome sequencing (genomics)
    (
        "International Human Genome Sequencing Consortium, Nature 409 (2001) 860-921, reported the initial sequence and analysis of the human genome, with Venter et al., Science 291 (2001) 1304-1351, publishing a concurrent private-sector assembly.",
        "knowledge",
        "The human genome comprises roughly three billion base pairs arranged into twenty-three chromosome pairs, with the first working draft published in 2001.",
        "knowledge",
    ),
    # 48. Standard Model of particle physics (theoretical physics)
    (
        "Glashow, Weinberg, and Salam developed the electroweak unification for which they shared the 1979 Nobel Prize in Physics, combined with QCD to form the Standard Model.",
        "knowledge",
        "The Standard Model of particle physics unifies the electromagnetic, weak, and strong interactions as gauge theories and describes all known elementary particles except gravitons.",
        "knowledge",
    ),
    # 49. Mars rover Curiosity landing (aerospace / robotics)
    (
        "NASA/JPL mission report, 'Mars Science Laboratory Entry, Descent, and Landing', JPL D-75929 (2014), describes the sky-crane landing of the Curiosity rover in Gale Crater on 6 August 2012.",
        "technical",
        "NASA's Curiosity rover landed in Gale Crater on Mars on 6 August 2012 using a sky-crane system in which a hovering descent stage lowered the rover to the surface on cables.",
        "technical",
    ),
    # 50. Climate sensitivity (climate science)
    (
        "IPCC AR6 Working Group I report (2021), Chapter 7, assesses the equilibrium climate sensitivity to a doubling of atmospheric CO2 as very likely in the range 2.0 to 5.0 degrees Celsius with a best estimate of 3.0.",
        "knowledge",
        "The equilibrium warming from doubling the atmospheric carbon dioxide concentration is very likely between 2 and 5 degrees Celsius, with a best estimate around 3 degrees.",
        "knowledge",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, ref_domain, fact_text, fact_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            fact_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({
                "id": ref_id,
                "domain": ref_domain,
                "text": ref_text,
                "memory_type": "reference",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "id": fact_id,
                "domain": fact_domain,
                "text": fact_text,
                "memory_type": "fact",
                "pair_id": pair_id,
            }, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
