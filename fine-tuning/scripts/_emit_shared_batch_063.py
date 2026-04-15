"""One-off emitter for shared-base batch-063 — knowledge domain (astronomy, astrophysics, cosmology).

Writes 50 rows with ids shared-03101..03150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_063.tmp.jsonl"
ID_OFFSET = 3100

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Edwin Hubble's 1929 paper in PNAS reported the linear distance-velocity relation for galaxies, providing the empirical basis for cosmic expansion.", "milestone", "knowledge", False,
     [("Edwin Hubble", "person"), ("1929", "date"), ("PNAS", "publication"), ("cosmic expansion", "concept")],
     [("cosmic expansion", "Edwin Hubble", "AUTHORED_BY")],
     "which 1929 paper first reported the linear redshift-distance relation for galaxies",
     "Hubble PNAS distance velocity galaxy expansion year"),
    # --- 2 ---
    ("The LIGO collaboration announced GW150914 in Physical Review Letters in 2016, the first direct detection of gravitational waves from a binary black-hole merger.", "milestone", "knowledge", False,
     [("LIGO", "organization"), ("GW150914", "event"), ("Physical Review Letters", "publication"), ("2016", "date"), ("binary black-hole merger", "concept")],
     [("GW150914", "LIGO", "AUTHORED_BY"), ("GW150914", "Physical Review Letters", "PUBLISHED_IN")],
     "which 2016 announcement marked the first direct gravitational-wave detection",
     "LIGO GW150914 binary black hole merger PRL year"),
    # --- 3 ---
    ("The James Webb Space Telescope, launched on 25 December 2021, replaces Spitzer as NASA's flagship infrared observatory and exceeds it in mirror area by roughly fifty fold.", "fact", "knowledge", False,
     [("James Webb Space Telescope", "infrastructure"), ("25 December 2021", "date"), ("Spitzer", "infrastructure"), ("NASA", "organization")],
     [("James Webb Space Telescope", "Spitzer", "REPLACES")],
     "which 2021 NASA observatory took over from Spitzer as the flagship infrared mission",
     "JWST Spitzer infrared flagship NASA launch year"),
    # --- 4 ---
    ("The Planck satellite's 2018 results in Astronomy & Astrophysics improved on WMAP's CMB temperature and polarisation maps, tightening the six-parameter LambdaCDM fit.", "reference", "knowledge", False,
     [("Planck", "infrastructure"), ("2018", "date"), ("Astronomy & Astrophysics", "publication"), ("WMAP", "infrastructure"), ("CMB", "concept"), ("LambdaCDM", "theory")],
     [("Planck", "WMAP", "IMPROVES_ON"), ("Planck", "Astronomy & Astrophysics", "PUBLISHED_IN")],
     "which 2018 release sharpened CMB constraints beyond the WMAP era",
     "Planck 2018 results CMB WMAP successor LambdaCDM fit"),
    # --- 5 ---
    ("Alan Guth's 1981 Physical Review D paper introduced cosmic inflation to resolve the horizon and flatness problems left unresolved by the standard hot Big Bang.", "reference", "knowledge", False,
     [("Alan Guth", "person"), ("1981", "date"), ("Physical Review D", "publication"), ("cosmic inflation", "theory"), ("hot Big Bang", "theory")],
     [("cosmic inflation", "Alan Guth", "AUTHORED_BY"), ("cosmic inflation", "hot Big Bang", "IMPROVES_ON")],
     "which inflationary proposal first addressed flatness and horizon puzzles in early-universe cosmology",
     "Guth inflation horizon flatness Physical Review D year"),
    # --- 6 ---
    ("Subrahmanyan Chandrasekhar's 1931 ApJ paper derived the upper mass limit of about 1.4 solar masses for stable white dwarfs supported by electron degeneracy.", "reference", "knowledge", False,
     [("Subrahmanyan Chandrasekhar", "person"), ("1931", "date"), ("ApJ", "publication"), ("white dwarfs", "concept"), ("electron degeneracy", "concept")],
     [("ApJ", "Subrahmanyan Chandrasekhar", "AUTHORED_BY")],
     "whose 1931 ApJ paper derived the white-dwarf upper mass limit",
     "Chandrasekhar limit white dwarf 1.4 solar mass year"),
    # --- 7 ---
    ("The radial-velocity method discovered 51 Pegasi b in 1995 when Mayor and Queloz measured periodic Doppler shifts of the host star reported in Nature.", "milestone", "knowledge", False,
     [("radial-velocity method", "method"), ("51 Pegasi b", "concept"), ("1995", "date"), ("Mayor", "person"), ("Queloz", "person"), ("Nature", "publication")],
     [("51 Pegasi b", "Mayor", "AUTHORED_BY"), ("51 Pegasi b", "Nature", "PUBLISHED_IN")],
     "which 1995 Nature paper reported the first main-sequence exoplanet via Doppler shifts",
     "Mayor Queloz 51 Peg b radial velocity Nature year"),
    # --- 8 ---
    ("NASA's Kepler mission used the transit method to discover thousands of exoplanet candidates between 2009 and 2018, replacing earlier ground-based transit surveys as the dominant detection pipeline.", "fact", "knowledge", False,
     [("NASA", "organization"), ("Kepler", "infrastructure"), ("transit method", "method"), ("2009", "date"), ("2018", "date"), ("ground-based transit surveys", "infrastructure")],
     [("Kepler", "ground-based transit surveys", "REPLACES")],
     "which NASA mission dominated transit-based exoplanet discovery from 2009 to 2018",
     "Kepler transit exoplanet survey years NASA mission"),
    # --- 9 ---
    ("The Event Horizon Telescope collaboration published the first resolved image of the M87* supermassive black-hole shadow in ApJ Letters in April 2019.", "milestone", "knowledge", False,
     [("Event Horizon Telescope", "organization"), ("M87*", "concept"), ("supermassive black-hole shadow", "concept"), ("ApJ Letters", "publication"), ("April 2019", "date")],
     [("M87*", "Event Horizon Telescope", "AUTHORED_BY"), ("M87*", "ApJ Letters", "PUBLISHED_IN")],
     "which 2019 ApJ Letters series resolved the first black-hole shadow",
     "EHT M87 black hole shadow ApJL April year"),
    # --- 10. noise ---
    ("Let me re-check whether that distance estimate uses Cepheid or TRGB calibration before I cite it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Vera Rubin and Kent Ford's 1970 ApJ paper on flat rotation curves of Andromeda provided crucial dynamical evidence for the existence of dark matter halos.", "reference", "knowledge", False,
     [("Vera Rubin", "person"), ("Kent Ford", "person"), ("1970", "date"), ("ApJ", "publication"), ("flat rotation curves", "finding"), ("Andromeda", "place"), ("dark matter halos", "concept")],
     [("flat rotation curves", "Vera Rubin", "AUTHORED_BY"), ("flat rotation curves", "ApJ", "PUBLISHED_IN")],
     "which 1970 ApJ paper used Andromeda rotation curves to argue for dark matter",
     "Rubin Ford rotation curve Andromeda dark matter ApJ year"),
    # --- 12 ---
    ("The 1998 High-Z Supernova Search Team paper led by Adam Riess in The Astronomical Journal reported the accelerating expansion of the universe using Type Ia supernovae as standard candles.", "reference", "knowledge", False,
     [("High-Z Supernova Search Team", "organization"), ("Adam Riess", "person"), ("The Astronomical Journal", "publication"), ("1998", "date"), ("Type Ia supernovae", "concept"), ("accelerating expansion", "finding")],
     [("accelerating expansion", "Adam Riess", "AUTHORED_BY"), ("accelerating expansion", "The Astronomical Journal", "PUBLISHED_IN")],
     "which 1998 AJ paper announced cosmic acceleration from Type Ia supernovae",
     "Riess High-Z supernova accelerating expansion AJ year"),
    # --- 13 ---
    ("Saul Perlmutter's Supernova Cosmology Project independently confirmed cosmic acceleration in a 1999 ApJ paper, jointly motivating the 2011 Nobel Prize in Physics.", "milestone", "knowledge", False,
     [("Saul Perlmutter", "person"), ("Supernova Cosmology Project", "organization"), ("1999", "date"), ("ApJ", "publication"), ("cosmic acceleration", "finding"), ("2011 Nobel Prize in Physics", "event")],
     [("cosmic acceleration", "Saul Perlmutter", "AUTHORED_BY"), ("cosmic acceleration", "ApJ", "PUBLISHED_IN")],
     "which 1999 ApJ paper independently confirmed cosmic acceleration",
     "Perlmutter SCP supernova accelerating expansion ApJ year"),
    # --- 14 ---
    ("LambdaCDM cosmology improves on the older Einstein-de Sitter matter-only model by adding a cosmological constant Lambda and cold dark matter to fit CMB and supernova data simultaneously.", "architecture", "knowledge", False,
     [("LambdaCDM", "theory"), ("Einstein-de Sitter", "theory"), ("cosmological constant", "concept"), ("cold dark matter", "concept"), ("CMB", "concept")],
     [("LambdaCDM", "Einstein-de Sitter", "IMPROVES_ON")],
     "which concordance model superseded the matter-only Einstein-de Sitter cosmology",
     "LambdaCDM concordance Einstein de Sitter matter only successor"),
    # --- 15 ---
    ("The COBE satellite's 1992 FIRAS instrument confirmed the CMB blackbody spectrum to extraordinary precision, while DMR mapped the first temperature anisotropies.", "milestone", "knowledge", False,
     [("COBE", "infrastructure"), ("1992", "date"), ("FIRAS", "tool"), ("CMB blackbody spectrum", "finding"), ("DMR", "tool"), ("temperature anisotropies", "finding")],
     [("temperature anisotropies", "COBE", "AUTHORED_BY")],
     "which 1992 COBE results pinned the CMB blackbody and first anisotropies",
     "COBE FIRAS DMR blackbody anisotropy CMB year"),
    # --- 16 ---
    ("WMAP, launched in 2001, replaced COBE as the primary all-sky CMB anisotropy experiment and constrained the universe's age to within roughly one percent.", "fact", "knowledge", False,
     [("WMAP", "infrastructure"), ("2001", "date"), ("COBE", "infrastructure"), ("CMB anisotropy", "finding")],
     [("WMAP", "COBE", "REPLACES")],
     "which early-2000s NASA mission replaced COBE for all-sky CMB anisotropy mapping",
     "WMAP COBE successor CMB anisotropy launch year"),
    # --- 17 ---
    ("Arno Penzias and Robert Wilson's 1965 ApJ Letters paper reported the 3K microwave background, providing the decisive observational support for the hot Big Bang over Steady State cosmology.", "reference", "knowledge", False,
     [("Arno Penzias", "person"), ("Robert Wilson", "person"), ("1965", "date"), ("ApJ Letters", "publication"), ("microwave background", "finding"), ("hot Big Bang", "theory"), ("Steady State", "theory")],
     [("microwave background", "Arno Penzias", "AUTHORED_BY"), ("microwave background", "ApJ Letters", "PUBLISHED_IN"), ("hot Big Bang", "Steady State", "REPLACES")],
     "which 1965 paper reported the 3K microwave background and sank Steady State",
     "Penzias Wilson CMB ApJL Big Bang Steady State year"),
    # --- 18 ---
    ("Roger Penrose's 1965 Physical Review Letters paper proved that gravitational collapse generically produces a singularity inside a trapped surface.", "reference", "knowledge", False,
     [("Roger Penrose", "person"), ("1965", "date"), ("Physical Review Letters", "publication"), ("gravitational collapse", "concept"), ("singularity", "concept"), ("trapped surface", "concept")],
     [("singularity", "Roger Penrose", "AUTHORED_BY"), ("singularity", "Physical Review Letters", "PUBLISHED_IN")],
     "which 1965 PRL theorem showed gravitational collapse produces a singularity",
     "Penrose singularity theorem trapped surface PRL year"),
    # --- 19 ---
    ("Stephen Hawking's 1974 Nature paper showed that black holes radiate thermally with a temperature inversely proportional to their mass.", "reference", "knowledge", False,
     [("Stephen Hawking", "person"), ("1974", "date"), ("Nature", "publication"), ("black holes", "concept")],
     [("black holes", "Stephen Hawking", "AUTHORED_BY"), ("black holes", "Nature", "PUBLISHED_IN")],
     "which 1974 Nature paper showed black holes radiate thermally",
     "Hawking radiation black hole Nature paper year"),
    # --- 20 ---
    ("Jocelyn Bell Burnell's 1968 Nature paper, co-authored with Antony Hewish, reported the discovery of pulsars, soon identified as rapidly rotating neutron stars.", "milestone", "knowledge", False,
     [("Jocelyn Bell Burnell", "person"), ("1968", "date"), ("Nature", "publication"), ("Antony Hewish", "person"), ("pulsars", "concept"), ("neutron stars", "concept")],
     [("pulsars", "Jocelyn Bell Burnell", "AUTHORED_BY"), ("pulsars", "Nature", "PUBLISHED_IN")],
     "which 1968 Nature paper announced the discovery of pulsars",
     "Bell Burnell Hewish pulsar Nature CP1919 year"),
    # --- 21 ---
    ("Fritz Zwicky's 1933 Helvetica Physica Acta paper inferred the existence of dunkle Materie in the Coma cluster from anomalously high galaxy velocity dispersions.", "reference", "knowledge", False,
     [("Fritz Zwicky", "person"), ("1933", "date"), ("Helvetica Physica Acta", "publication"), ("dunkle Materie", "concept"), ("Coma cluster", "place")],
     [("dunkle Materie", "Fritz Zwicky", "AUTHORED_BY"), ("dunkle Materie", "Helvetica Physica Acta", "PUBLISHED_IN")],
     "which 1933 Zwicky paper inferred dark matter from Coma cluster dynamics",
     "Zwicky Coma cluster dunkle Materie Helvetica year"),
    # --- 22 ---
    ("The MACHO and EROS microlensing surveys ruled out compact halo objects as the dominant dark matter component in the Milky Way through the late 1990s.", "fact", "knowledge", False,
     [("MACHO", "project"), ("EROS", "project"), ("microlensing surveys", "method"), ("compact halo objects", "concept"), ("Milky Way", "place")],
     [("MACHO", "microlensing surveys", "USES"), ("EROS", "microlensing surveys", "USES")],
     "which late-1990s microlensing programs ruled out MACHOs as Milky Way dark matter",
     "MACHO EROS microlensing halo dark matter Milky Way"),
    # --- 23 ---
    ("XENONnT, operating underground at Gran Sasso, supersedes XENON1T as the leading direct dark matter search using a multi-tonne liquid xenon time projection chamber.", "fact", "knowledge", False,
     [("XENONnT", "infrastructure"), ("Gran Sasso", "place"), ("XENON1T", "infrastructure"), ("liquid xenon time projection chamber", "tool")],
     [("XENONnT", "XENON1T", "REPLACES")],
     "which Gran Sasso experiment now leads liquid-xenon dark matter direct detection",
     "XENONnT XENON1T Gran Sasso liquid xenon TPC successor"),
    # --- 24 ---
    ("The Hertzsprung-Russell diagram organises stars by luminosity and effective temperature, framing stellar evolution along the main sequence, giant branch, and white-dwarf cooling track.", "architecture", "knowledge", False,
     [("Hertzsprung-Russell diagram", "concept"), ("luminosity", "concept"), ("effective temperature", "concept"), ("main sequence", "concept"), ("giant branch", "concept"), ("white-dwarf cooling track", "concept")],
     [("Hertzsprung-Russell diagram", "stellar evolution", "APPLIES_TO") if False else ("Hertzsprung-Russell diagram", "main sequence", "HAS_PART")],
     "which luminosity-temperature diagram organises stellar evolutionary tracks",
     "HR diagram luminosity temperature main sequence giant cooling"),
    # --- 25 ---
    ("Type II core-collapse supernovae produce neutron stars or stellar-mass black holes from massive progenitors, with SN 1987A in the Large Magellanic Cloud providing the closest modern example.", "fact", "knowledge", False,
     [("Type II core-collapse supernovae", "concept"), ("neutron stars", "concept"), ("stellar-mass black holes", "concept"), ("SN 1987A", "event"), ("Large Magellanic Cloud", "place")],
     [("Type II core-collapse supernovae", "neutron stars", "PRODUCES")],
     "which nearby 1987 supernova provided the modern benchmark for core-collapse events",
     "SN 1987A LMC core collapse Type II supernova progenitor"),
    # --- 26 ---
    ("The Tully-Fisher relation, introduced in a 1977 Astronomy & Astrophysics paper, links spiral galaxy luminosity to rotation velocity and remains a primary distance indicator.", "reference", "knowledge", False,
     [("Tully-Fisher relation", "concept"), ("1977", "date"), ("Astronomy & Astrophysics", "publication"), ("spiral galaxy", "concept"), ("rotation velocity", "concept")],
     [("Tully-Fisher relation", "Astronomy & Astrophysics", "PUBLISHED_IN")],
     "which 1977 A&A paper tied spiral galaxy luminosity to rotation velocity",
     "Tully Fisher spiral luminosity rotation velocity A&A year"),
    # --- 27 ---
    ("BICEP2's 2014 Physical Review Letters claim of primordial B-mode polarisation was retracted after a joint Planck analysis attributed the signal to galactic dust foregrounds.", "problem", "knowledge", False,
     [("BICEP2", "infrastructure"), ("2014", "date"), ("Physical Review Letters", "publication"), ("primordial B-mode polarisation", "finding"), ("Planck", "infrastructure"), ("galactic dust foregrounds", "concept")],
     [("primordial B-mode polarisation", "Physical Review Letters", "PUBLISHED_IN"), ("Planck", "BICEP2", "CONTRADICTS")],
     "which 2014 BICEP2 PRL claim was undone by joint Planck dust analysis",
     "BICEP2 PRL B mode dust Planck retraction year"),
    # --- 28 ---
    ("Sgr A*, the four-million-solar-mass black hole at the Milky Way centre, was characterised through stellar orbit monitoring by the Keck and VLT teams led by Andrea Ghez and Reinhard Genzel.", "fact", "knowledge", False,
     [("Sgr A*", "concept"), ("Milky Way", "place"), ("Keck", "infrastructure"), ("VLT", "infrastructure"), ("Andrea Ghez", "person"), ("Reinhard Genzel", "person")],
     [("Sgr A*", "Andrea Ghez", "AUTHORED_BY"), ("Sgr A*", "Reinhard Genzel", "AUTHORED_BY")],
     "whose Keck and VLT stellar orbit monitoring established the Milky Way central black hole mass",
     "Sgr A* Galactic centre Ghez Genzel Keck VLT orbits"),
    # --- 29 ---
    ("The Sloan Digital Sky Survey, operating from Apache Point Observatory since 2000, replaces earlier photographic plate surveys as the dominant wide-field optical galaxy catalogue.", "fact", "knowledge", False,
     [("Sloan Digital Sky Survey", "project"), ("Apache Point Observatory", "infrastructure"), ("2000", "date"), ("photographic plate surveys", "method")],
     [("Sloan Digital Sky Survey", "photographic plate surveys", "REPLACES")],
     "which Apache Point survey supplanted photographic plates as the optical galaxy catalogue",
     "SDSS Apache Point wide field galaxy survey successor"),
    # --- 30 ---
    ("Direct collapse and Population III seed scenarios compete to explain the existence of billion-solar-mass quasars observed at redshifts above seven.", "problem", "knowledge", False,
     [("Direct collapse", "theory"), ("Population III", "concept"), ("billion-solar-mass quasars", "concept")],
     [],
     "which competing seeding scenarios try to explain very high redshift supermassive quasars",
     "direct collapse Pop III seed quasar high redshift puzzle"),
    # --- 31 ---
    ("The Atacama Large Millimeter Array, sited at 5,000 metres on the Chajnantor Plateau, replaces single-dish millimetre facilities as the leading interferometer for protoplanetary disk imaging.", "fact", "knowledge", False,
     [("Atacama Large Millimeter Array", "infrastructure"), ("Chajnantor Plateau", "place"), ("single-dish millimetre facilities", "infrastructure"), ("protoplanetary disk imaging", "method")],
     [("Atacama Large Millimeter Array", "single-dish millimetre facilities", "REPLACES")],
     "which Chajnantor interferometer leads modern protoplanetary disk imaging at millimetre wavelengths",
     "ALMA Chajnantor protoplanetary disk millimetre interferometer"),
    # --- 32 ---
    ("Pulsar timing arrays such as NANOGrav reported in a 2023 ApJ Letters paper evidence for a stochastic gravitational-wave background consistent with supermassive black-hole binaries.", "reference", "knowledge", False,
     [("Pulsar timing arrays", "method"), ("NANOGrav", "organization"), ("2023", "date"), ("ApJ Letters", "publication"), ("stochastic gravitational-wave background", "finding"), ("supermassive black-hole binaries", "concept")],
     [("stochastic gravitational-wave background", "NANOGrav", "AUTHORED_BY"), ("stochastic gravitational-wave background", "ApJ Letters", "PUBLISHED_IN")],
     "which 2023 ApJL series reported a stochastic gravitational-wave background",
     "NANOGrav pulsar timing stochastic GW background ApJL year"),
    # --- 33 ---
    ("Karl Schwarzschild's 1916 paper derived the first exact vacuum solution to Einstein's field equations, describing the spacetime around a non-rotating spherical mass.", "reference", "knowledge", False,
     [("Karl Schwarzschild", "person"), ("1916", "date"), ("Einstein", "person"), ("non-rotating spherical mass", "concept")],
     [],
     "which 1916 result yielded the earliest closed-form static spherical metric in general relativity",
     "Schwarzschild solution vacuum Einstein field equations year"),
    # --- 34. noise ---
    ("Quick reminder to confirm whether that mass-radius diagram uses Newtonian or fully relativistic equations of state.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("The Hubble tension describes the persistent four-sigma discrepancy between local distance-ladder measurements of H0 near 73 and Planck CMB inferences near 67 km/s/Mpc.", "problem", "knowledge", False,
     [("Hubble tension", "concept"), ("local distance-ladder measurements", "method"), ("H0", "concept"), ("Planck", "infrastructure"), ("CMB", "concept")],
     [("local distance-ladder measurements", "Planck", "CONTRADICTS")],
     "which present-day tension separates local H0 ladders from CMB inferences",
     "Hubble tension H0 distance ladder Planck CMB discrepancy"),
    # --- 36 ---
    ("The Lyman-alpha forest, observed in high-redshift quasar spectra, traces the cosmic web of intergalactic hydrogen and constrains the matter power spectrum on small scales.", "fact", "knowledge", False,
     [("Lyman-alpha forest", "concept"), ("high-redshift quasar spectra", "tool"), ("cosmic web", "concept"), ("intergalactic hydrogen", "concept"), ("matter power spectrum", "concept")],
     [("Lyman-alpha forest", "matter power spectrum", "APPLIES_TO")],
     "which absorption feature in quasar spectra traces the intergalactic hydrogen web",
     "Lyman alpha forest quasar absorption cosmic web power spectrum"),
    # --- 37 ---
    ("Baryon acoustic oscillations imprint a 150-megaparsec standard ruler in the galaxy distribution, first detected in SDSS galaxy catalogues by Eisenstein and collaborators in a 2005 ApJ paper.", "reference", "knowledge", False,
     [("Baryon acoustic oscillations", "concept"), ("150-megaparsec standard ruler", "concept"), ("SDSS", "project"), ("Eisenstein", "person"), ("2005", "date"), ("ApJ", "publication")],
     [("Baryon acoustic oscillations", "Eisenstein", "AUTHORED_BY"), ("Baryon acoustic oscillations", "ApJ", "PUBLISHED_IN")],
     "which 2005 ApJ paper first detected the BAO ruler in SDSS galaxy clustering",
     "BAO Eisenstein SDSS standard ruler galaxy clustering year"),
    # --- 38 ---
    ("The IceCube neutrino observatory at the South Pole detected a high-energy astrophysical neutrino flux reported in Science in 2013, opening neutrino astronomy at TeV-PeV energies.", "milestone", "knowledge", False,
     [("IceCube", "infrastructure"), ("South Pole", "place"), ("Science", "publication"), ("2013", "date"), ("astrophysical neutrino flux", "finding")],
     [("astrophysical neutrino flux", "IceCube", "AUTHORED_BY"), ("astrophysical neutrino flux", "Science", "PUBLISHED_IN")],
     "which 2013 IceCube Science paper opened high-energy neutrino astronomy",
     "IceCube South Pole astrophysical neutrino TeV PeV year"),
    # --- 39 ---
    ("MOND, proposed by Mordehai Milgrom in a 1983 ApJ paper, modifies Newtonian dynamics at low accelerations and contradicts the standard particle dark matter explanation of galaxy rotation curves.", "reference", "knowledge", False,
     [("MOND", "theory"), ("Mordehai Milgrom", "person"), ("1983", "date"), ("ApJ", "publication"), ("particle dark matter", "concept"), ("galaxy rotation curves", "concept")],
     [("MOND", "Mordehai Milgrom", "AUTHORED_BY"), ("MOND", "particle dark matter", "CONTRADICTS")],
     "which 1983 ApJ proposal modifies Newtonian dynamics instead of invoking particle dark matter",
     "MOND Milgrom modified Newtonian dynamics rotation curves year"),
    # --- 40 ---
    ("The MNRAS-published EAGLE simulation, released in 2015, replaced earlier dark-matter-only N-body runs as a leading hydrodynamical galaxy formation benchmark.", "reference", "knowledge", False,
     [("MNRAS", "publication"), ("EAGLE simulation", "project"), ("2015", "date"), ("dark-matter-only N-body runs", "method"), ("hydrodynamical galaxy formation", "concept")],
     [("EAGLE simulation", "dark-matter-only N-body runs", "REPLACES"), ("EAGLE simulation", "MNRAS", "PUBLISHED_IN")],
     "which 2015 MNRAS hydrodynamical simulation became a leading galaxy formation benchmark",
     "EAGLE simulation MNRAS hydrodynamical galaxy formation year"),
    # --- 41 ---
    ("The IllustrisTNG project extended the original Illustris simulations with magnetohydrodynamics, improving on its predecessor's overcooled disk problem and matching observed galaxy colours more closely.", "reference", "knowledge", False,
     [("IllustrisTNG", "project"), ("Illustris", "project"), ("magnetohydrodynamics", "method"), ("overcooled disk problem", "concept"), ("galaxy colours", "concept")],
     [("IllustrisTNG", "Illustris", "IMPROVES_ON")],
     "which simulation suite improved on Illustris by adding magnetohydrodynamics",
     "IllustrisTNG Illustris MHD overcooled successor galaxy colours"),
    # --- 42 ---
    ("The Gaia mission, launched by ESA in 2013, replaces Hipparcos as the definitive astrometric survey, delivering parallaxes for over a billion Milky Way stars.", "fact", "knowledge", False,
     [("Gaia", "infrastructure"), ("ESA", "organization"), ("2013", "date"), ("Hipparcos", "infrastructure"), ("Milky Way", "place")],
     [("Gaia", "Hipparcos", "REPLACES")],
     "which ESA mission supplanted Hipparcos as the definitive Galactic astrometric survey",
     "Gaia ESA Hipparcos successor parallax Milky Way year"),
    # --- 43 ---
    ("GW170817, a 2017 binary neutron-star merger, produced coincident gravitational-wave and gamma-ray-burst signals reported in ApJ Letters and inaugurated multimessenger astronomy.", "milestone", "knowledge", False,
     [("GW170817", "event"), ("2017", "date"), ("binary neutron-star merger", "concept"), ("gamma-ray-burst signals", "finding"), ("ApJ Letters", "publication"), ("multimessenger astronomy", "field")],
     [("GW170817", "ApJ Letters", "PUBLISHED_IN"), ("GW170817", "gamma-ray-burst signals", "PRODUCES")],
     "which 2017 binary neutron-star merger inaugurated multimessenger astronomy",
     "GW170817 kilonova multimessenger ApJL gamma ray burst year"),
    # --- 44 ---
    ("CMB-S4, a planned ground-based survey at South Pole and Chile, will improve on the Simons Observatory by adding hundreds of thousands of detectors to chase inflationary B-modes.", "decision", "knowledge", False,
     [("CMB-S4", "project"), ("South Pole", "place"), ("Chile", "place"), ("Simons Observatory", "project"), ("inflationary B-modes", "finding")],
     [("CMB-S4", "Simons Observatory", "IMPROVES_ON")],
     "which next-generation CMB program scales up beyond the Simons Observatory for B-mode searches",
     "CMB-S4 Simons Observatory B mode inflation successor"),
    # --- 45 ---
    ("Helioseismology probes the Sun's interior through resonant pressure modes, calibrated against standard solar models such as those benchmarked by John Bahcall to resolve the solar neutrino problem.", "fact", "knowledge", False,
     [("Helioseismology", "field"), ("Sun", "place"), ("standard solar models", "method"), ("John Bahcall", "person"), ("solar neutrino problem", "concept")],
     [("standard solar models", "John Bahcall", "AUTHORED_BY")],
     "which subfield uses pressure modes to probe the Sun and was tied to the solar neutrino problem",
     "helioseismology Sun pressure modes Bahcall solar neutrino problem"),
    # --- 46 ---
    ("Direct imaging campaigns at the SPHERE instrument on the VLT discovered the HR 8799 multi-planet system around a young A-type star, complementing transit and radial-velocity techniques.", "fact", "knowledge", False,
     [("SPHERE", "tool"), ("VLT", "infrastructure"), ("HR 8799", "concept"), ("transit", "method"), ("radial-velocity techniques", "method")],
     [("SPHERE", "VLT", "DEPLOYED_ON"), ("SPHERE", "transit", "RELATED_TO")],
     "which VLT instrument directly imaged the HR 8799 multi-planet system",
     "SPHERE VLT HR 8799 direct imaging exoplanet system"),
    # --- 47 ---
    ("The Vera C. Rubin Observatory, sited at Cerro Pachon in Chile, will run the Legacy Survey of Space and Time and replace the Pan-STARRS sky survey as the leading time-domain optical facility.", "fact", "knowledge", False,
     [("Vera C. Rubin Observatory", "infrastructure"), ("Cerro Pachon", "place"), ("Chile", "place"), ("Legacy Survey of Space and Time", "project"), ("Pan-STARRS", "infrastructure")],
     [("Vera C. Rubin Observatory", "Pan-STARRS", "REPLACES")],
     "which Cerro Pachon facility will succeed Pan-STARRS for time-domain optical survey work",
     "Rubin Observatory LSST Pan-STARRS time domain Chile"),
    # --- 48 ---
    ("Reinhard Genzel and Andrea Ghez shared half of the 2020 Nobel Prize in Physics for their decades of stellar orbit monitoring at the Galactic centre, with Roger Penrose receiving the other half.", "milestone", "knowledge", False,
     [("Reinhard Genzel", "person"), ("Andrea Ghez", "person"), ("2020 Nobel Prize in Physics", "event"), ("Galactic centre", "place"), ("Roger Penrose", "person")],
     [("2020 Nobel Prize in Physics", "Reinhard Genzel", "AUTHORED_BY"), ("2020 Nobel Prize in Physics", "Andrea Ghez", "AUTHORED_BY")],
     "which 2020 Nobel split honoured Galactic centre orbits and Penrose's singularity work",
     "2020 Nobel Physics Genzel Ghez Penrose Galactic centre singularity"),
    # --- 49 ---
    ("The cosmic distance ladder layers parallax, Cepheid period-luminosity relations, and Type Ia supernovae to extend distance measurements from the solar neighbourhood to gigaparsec scales.", "architecture", "knowledge", False,
     [("cosmic distance ladder", "method"), ("parallax", "method"), ("Cepheid period-luminosity relations", "concept"), ("Type Ia supernovae", "concept")],
     [("cosmic distance ladder", "parallax", "HAS_PART"), ("cosmic distance ladder", "Cepheid period-luminosity relations", "HAS_PART"), ("cosmic distance ladder", "Type Ia supernovae", "HAS_PART")],
     "which layered method extends distance from parallax through Cepheids to Type Ia supernovae",
     "cosmic distance ladder parallax Cepheid Type Ia gigaparsec"),
    # --- 50 ---
    ("Eleanor Margaret Burbidge and collaborators' 1957 Reviews of Modern Physics paper B2FH established the canonical theory of stellar nucleosynthesis for elements heavier than helium.", "reference", "knowledge", False,
     [("Eleanor Margaret Burbidge", "person"), ("1957", "date"), ("Reviews of Modern Physics", "publication"), ("B2FH", "publication"), ("stellar nucleosynthesis", "theory")],
     [("B2FH", "Eleanor Margaret Burbidge", "AUTHORED_BY"), ("B2FH", "Reviews of Modern Physics", "PUBLISHED_IN")],
     "which 1957 Reviews of Modern Physics paper canonised stellar nucleosynthesis",
     "B2FH Burbidge Fowler Hoyle nucleosynthesis Reviews Modern Physics year"),
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
