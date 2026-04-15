"""One-off emitter for shared-base batch-136 — knowledge domain (engineering as a research discipline).

Writes 50 rows with ids shared-06751..06800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_136.tmp.jsonl"
ID_OFFSET = 6750

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Stephen Timoshenko's 1921 beam theory extends Euler-Bernoulli analysis by incorporating shear deformation and rotary inertia for stubby beams.", "reference", "knowledge", False,
     [("Stephen Timoshenko", "person"), ("1921", "date"), ("Euler-Bernoulli analysis", "theory"), ("shear deformation", "concept"), ("rotary inertia", "concept")],
     [("Stephen Timoshenko", "Euler-Bernoulli analysis", "IMPROVES_ON")],
     "which 1921 beam formulation refined Euler-Bernoulli theory by adding shear and rotary terms",
     "Timoshenko beam shear rotary inertia stubby correction year"),
    # --- 2 ---
    ("Olek Zienkiewicz's The Finite Element Method, first issued in 1967, codified FEA as a general-purpose structural analysis tool across engineering disciplines.", "reference", "knowledge", False,
     [("Olek Zienkiewicz", "person"), ("The Finite Element Method", "publication"), ("1967", "date"), ("FEA", "method")],
     [("The Finite Element Method", "Olek Zienkiewicz", "AUTHORED_BY")],
     "which 1967 textbook codified the finite element method as a general-purpose engineering tool",
     "Zienkiewicz finite element textbook engineering codification year"),
    # --- 3 ---
    ("Finite element analysis replaces closed-form analytic beam and plate solutions for complex geometries, anisotropic materials, and nonlinear regimes.", "decision", "knowledge", False,
     [("Finite element analysis", "method"), ("closed-form analytic beam and plate solutions", "method"), ("anisotropic materials", "concept")],
     [("Finite element analysis", "closed-form analytic beam and plate solutions", "IMPROVES_ON")],
     "which numerical method supplanted closed-form analytic solutions for complex structural geometries",
     "FEA numerical replacement analytic beam plate nonlinear geometry"),
    # --- 4 ---
    ("Osborne Reynolds's 1883 experiments at Manchester established the dimensionless Reynolds number as the governing parameter of laminar-to-turbulent transition.", "milestone", "knowledge", False,
     [("Osborne Reynolds", "person"), ("1883", "date"), ("Manchester", "place"), ("Reynolds number", "concept"), ("laminar-to-turbulent transition", "concept")],
     [("Reynolds number", "Osborne Reynolds", "AUTHORED_BY")],
     "which Victorian-era Manchester experiments fixed the dimensionless criterion of pipe flow transition",
     "Reynolds 1883 Manchester pipe flow transition dimensionless"),
    # --- 5 ---
    ("Ludwig Prandtl's 1904 Heidelberg lecture introduced boundary layer theory, splitting viscous near-wall flow from an outer inviscid region.", "milestone", "knowledge", False,
     [("Ludwig Prandtl", "person"), ("1904", "date"), ("Heidelberg", "place"), ("boundary layer theory", "theory")],
     [("boundary layer theory", "Ludwig Prandtl", "AUTHORED_BY")],
     "which 1904 Heidelberg lecture launched aerodynamic boundary layer theory",
     "Prandtl Heidelberg boundary layer aerodynamics viscous year"),
    # --- 6 ---
    ("The NACA four-digit airfoil series, published by the National Advisory Committee for Aeronautics in 1933, parameterises camber and thickness through compact numerical codes.", "reference", "knowledge", False,
     [("NACA four-digit airfoil series", "framework"), ("National Advisory Committee for Aeronautics", "organization"), ("1933", "date"), ("camber", "concept"), ("thickness", "concept")],
     [("NACA four-digit airfoil series", "National Advisory Committee for Aeronautics", "AUTHORED_BY")],
     "which 1933 airfoil coding scheme parameterised camber and thickness for aerodynamic research",
     "NACA four digit airfoil camber thickness parameterisation year"),
    # --- 7 ---
    ("Ove Arup founded his London consultancy in 1946 and pioneered total design, integrating structural engineering with architectural collaboration on projects such as the Sydney Opera House.", "milestone", "knowledge", False,
     [("Ove Arup", "person"), ("London", "place"), ("1946", "date"), ("total design", "concept"), ("Sydney Opera House", "publication")],
     [("total design", "Ove Arup", "AUTHORED_BY")],
     "which post-war London engineer championed total design across structural and architectural teams",
     "Arup London total design Sydney Opera House consultancy year"),
    # --- 8 ---
    ("Gustave Eiffel's wrought-iron tower, completed in Paris in 1889, demonstrated wind-load analysis and riveted lattice design at unprecedented scale.", "milestone", "knowledge", False,
     [("Gustave Eiffel", "person"), ("Paris", "place"), ("1889", "date"), ("wind-load analysis", "method"), ("riveted lattice design", "concept")],
     [],
     "which 1889 Parisian landmark advanced structural aerodynamics at an unprecedented scale",
     "Eiffel Paris nineteenth century iron tower riveted lattice wind"),
    # --- 9 ---
    ("Zdenek Bazant's creep and shrinkage model, formalised in the B3 and B4 series from the 1990s onward, supplanted earlier ACI empirical fits for long-term concrete deformation.", "reference", "knowledge", False,
     [("Zdenek Bazant", "person"), ("B3 and B4 series", "framework"), ("1990s", "date"), ("ACI empirical fits", "method"), ("concrete deformation", "concept")],
     [("B3 and B4 series", "ACI empirical fits", "IMPROVES_ON")],
     "whose B3 and B4 creep models displaced ACI empirical curves for concrete long-term deformation",
     "Bazant creep shrinkage B3 B4 concrete deformation ACI"),
    # --- 10. noise ---
    ("Let me double-check that load combination against the latest annex before citing the clause number.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Eurocode, adopted across the European Union from 2010, replaces older national structural codes with a harmonised limit-state design framework.", "decision", "knowledge", False,
     [("Eurocode", "framework"), ("European Union", "organization"), ("2010", "date"), ("national structural codes", "framework"), ("limit-state design", "method")],
     [("Eurocode", "national structural codes", "REPLACES")],
     "which 2010 pan-European standard displaced older national structural design codes",
     "Eurocode EU 2010 national codes limit state harmonisation"),
    # --- 12 ---
    ("ASCE 7, maintained by the American Society of Civil Engineers, provides the minimum design loads referenced by the International Building Code in the United States.", "reference", "knowledge", False,
     [("ASCE 7", "framework"), ("American Society of Civil Engineers", "organization"), ("International Building Code", "framework"), ("United States", "place")],
     [("ASCE 7", "American Society of Civil Engineers", "AUTHORED_BY")],
     "which American structural-loads standard underpins the International Building Code in the US",
     "ASCE 7 American structural loads IBC United States"),
    # --- 13 ---
    ("Seismic design codes evolved after the 1971 San Fernando earthquake drove the adoption of capacity design and ductile detailing principles in reinforced concrete.", "fact", "knowledge", False,
     [("Seismic design codes", "framework"), ("1971 San Fernando earthquake", "event"), ("capacity design", "concept"), ("ductile detailing", "method"), ("reinforced concrete", "concept")],
     [],
     "which 1971 Californian earthquake triggered the shift toward capacity design and ductile detailing",
     "San Fernando 1971 seismic capacity design ductile concrete"),
    # --- 14 ---
    ("Nikola Tesla's alternating current system prevailed over Thomas Edison's direct current grid after the 1893 Chicago World's Fair contract and the Niagara Falls hydroelectric project.", "milestone", "knowledge", False,
     [("Nikola Tesla", "person"), ("alternating current system", "concept"), ("Thomas Edison", "person"), ("direct current grid", "concept"), ("1893 Chicago World's Fair", "event"), ("Niagara Falls", "place")],
     [("alternating current system", "direct current grid", "REPLACES")],
     "which late-nineteenth-century current war ended with AC winning over Edison's DC",
     "Tesla Edison AC DC war currents Chicago Niagara year"),
    # --- 15 ---
    ("Claude Shannon's 1949 Proceedings of the IRE paper formalised the sampling theorem, now known as the Shannon-Nyquist theorem, as the foundation of digital signal processing.", "reference", "knowledge", False,
     [("Claude Shannon", "person"), ("1949", "date"), ("Proceedings of the IRE", "publication"), ("Shannon-Nyquist theorem", "theory"), ("digital signal processing", "field")],
     [("Shannon-Nyquist theorem", "Claude Shannon", "AUTHORED_BY")],
     "which 1949 IRE paper fixed the sampling theorem underpinning digital signal processing",
     "Shannon Nyquist sampling 1949 IRE digital signal processing"),
    # --- 16 ---
    ("Hendrik Bode's 1940 Bell System Technical Journal papers introduced the Bode plot as the standard graphical tool for frequency-domain feedback analysis.", "reference", "knowledge", False,
     [("Hendrik Bode", "person"), ("1940", "date"), ("Bell System Technical Journal", "publication"), ("Bode plot", "method"), ("frequency-domain feedback analysis", "method")],
     [("Bode plot", "Hendrik Bode", "AUTHORED_BY")],
     "which 1940 Bell Labs papers introduced the Bode plot as a frequency-domain engineering tool",
     "Bode plot 1940 Bell Labs frequency domain feedback"),
    # --- 17 ---
    ("IEEE Transactions on Power Electronics, launched in 1986, anchors peer-reviewed research on switched-mode converters, motor drives, and grid-connected inverters.", "reference", "knowledge", False,
     [("IEEE Transactions on Power Electronics", "publication"), ("1986", "date"), ("switched-mode converters", "concept"), ("grid-connected inverters", "concept")],
     [],
     "which 1986 IEEE journal became the anchor venue for power electronics research",
     "IEEE Transactions Power Electronics 1986 inverter converter research"),
    # --- 18 ---
    ("The McCabe-Thiele graphical method, published by Warren McCabe and Ernest Thiele in 1925, lets chemical engineers size binary distillation columns by stepping between equilibrium and operating lines.", "reference", "knowledge", False,
     [("McCabe-Thiele graphical method", "method"), ("Warren McCabe", "person"), ("Ernest Thiele", "person"), ("1925", "date"), ("binary distillation columns", "concept")],
     [("McCabe-Thiele graphical method", "Warren McCabe", "AUTHORED_BY"), ("McCabe-Thiele graphical method", "Ernest Thiele", "AUTHORED_BY")],
     "which 1925 graphical construction lets engineers size binary distillation columns by stages",
     "McCabe Thiele 1925 distillation binary graphical stage"),
    # --- 19 ---
    ("R. Byron Bird, Warren Stewart, and Edwin Lightfoot's Transport Phenomena, first issued in 1960, unified momentum, heat, and mass transfer as a single chemical engineering discipline.", "reference", "knowledge", False,
     [("R. Byron Bird", "person"), ("Warren Stewart", "person"), ("Edwin Lightfoot", "person"), ("Transport Phenomena", "publication"), ("1960", "date"), ("chemical engineering", "field")],
     [("Transport Phenomena", "R. Byron Bird", "AUTHORED_BY"), ("Transport Phenomena", "Warren Stewart", "AUTHORED_BY"), ("Transport Phenomena", "Edwin Lightfoot", "AUTHORED_BY")],
     "which 1960 textbook unified momentum, heat, and mass transfer under chemical engineering",
     "Bird Stewart Lightfoot Transport Phenomena 1960 chemical engineering"),
    # --- 20 ---
    ("SpaceX's Raptor engine, first fired in 2016, adopts full-flow staged combustion of methalox propellant to improve reuse economics over kerolox first stages.", "decision", "knowledge", False,
     [("SpaceX", "organization"), ("Raptor engine", "concept"), ("2016", "date"), ("methalox propellant", "concept"), ("kerolox first stages", "concept")],
     [("methalox propellant", "kerolox first stages", "IMPROVES_ON"), ("Raptor engine", "SpaceX", "AUTHORED_BY")],
     "which SpaceX engine adopted methalox over kerolox for better reuse economics",
     "SpaceX Raptor methalox kerolox full flow staged combustion reuse"),
    # --- 21 ---
    ("NASA's Space Launch System, first flown on the Artemis I mission in November 2022, provides the heavy-lift vehicle for the Artemis lunar programme.", "milestone", "knowledge", False,
     [("NASA", "organization"), ("Space Launch System", "concept"), ("Artemis I", "event"), ("November 2022", "date"), ("Artemis", "concept")],
     [("Space Launch System", "NASA", "AUTHORED_BY")],
     "which NASA heavy-lift vehicle flew its inaugural Artemis I mission in late 2022",
     "SLS Artemis I November 2022 heavy lift lunar"),
    # --- 22 ---
    ("The INCOSE Systems Engineering Handbook, maintained by the International Council on Systems Engineering since 1998, consolidates systems engineering practice across industries.", "reference", "knowledge", False,
     [("INCOSE Systems Engineering Handbook", "publication"), ("International Council on Systems Engineering", "organization"), ("1998", "date"), ("systems engineering", "field")],
     [("INCOSE Systems Engineering Handbook", "International Council on Systems Engineering", "AUTHORED_BY")],
     "which cross-industry handbook by the international council has anchored practice since the late 1990s",
     "INCOSE reference volume cross industry consolidation discipline"),
    # --- 23 ---
    ("Model-based systems engineering using SysML, standardised by the OMG in 2007, replaces document-heavy specifications with graphical models of system structure and behaviour.", "decision", "knowledge", False,
     [("Model-based systems engineering", "method"), ("SysML", "framework"), ("OMG", "organization"), ("2007", "date"), ("document-heavy specifications", "method")],
     [("Model-based systems engineering", "document-heavy specifications", "REPLACES"), ("SysML", "OMG", "AUTHORED_BY")],
     "which 2007 OMG standard displaced document-heavy specs with graphical SysML models",
     "MBSE SysML OMG 2007 documents graphical model"),
    # --- 24 ---
    ("Rudolf Kalman's 1960 Journal of Basic Engineering paper A New Approach to Linear Filtering and Prediction Problems introduced the recursive filter now ubiquitous in aerospace guidance.", "reference", "knowledge", False,
     [("Rudolf Kalman", "person"), ("1960", "date"), ("Journal of Basic Engineering", "publication"), ("A New Approach to Linear Filtering and Prediction Problems", "publication"), ("aerospace guidance", "field")],
     [("A New Approach to Linear Filtering and Prediction Problems", "Rudolf Kalman", "AUTHORED_BY")],
     "which 1960 Kalman paper introduced the recursive filter now standard in guidance systems",
     "Kalman 1960 Journal Basic Engineering recursive filter aerospace"),
    # --- 25 ---
    ("Aleksandr Lyapunov's 1892 doctoral dissertation at Kharkov established the stability theory that now underpins nonlinear control analysis.", "reference", "knowledge", False,
     [("Aleksandr Lyapunov", "person"), ("1892", "date"), ("Kharkov", "place"), ("stability theory", "theory"), ("nonlinear control analysis", "field")],
     [("stability theory", "Aleksandr Lyapunov", "AUTHORED_BY")],
     "whose late-nineteenth-century Ukrainian doctoral work underpins modern nonlinear controller analysis",
     "Lyapunov Kharkov dissertation century stability criterion controller"),
    # --- 26 ---
    ("Model predictive control, matured in Jan Maciejowski's 2002 Cambridge textbook, improves on classical PID tuning for plants with hard input and state constraints.", "decision", "knowledge", False,
     [("Model predictive control", "method"), ("Jan Maciejowski", "person"), ("2002", "date"), ("Cambridge", "place"), ("classical PID tuning", "method")],
     [("Model predictive control", "classical PID tuning", "IMPROVES_ON")],
     "which constrained control method surpasses classical PID for plants with hard input bounds",
     "MPC Maciejowski 2002 Cambridge PID constrained plant"),
    # --- 27 ---
    ("Lev Pontryagin's maximum principle, published in 1956 in the Soviet Doklady Akademii Nauk, provides the necessary conditions for optimal control of dynamic systems.", "reference", "knowledge", False,
     [("Lev Pontryagin", "person"), ("maximum principle", "theory"), ("1956", "date"), ("Doklady Akademii Nauk", "publication"), ("optimal control", "field")],
     [("maximum principle", "Lev Pontryagin", "AUTHORED_BY")],
     "which 1956 Soviet result supplied necessary conditions for optimal dynamic control",
     "Pontryagin maximum principle 1956 Doklady optimal control"),
    # --- 28 ---
    ("The Journal of Fluid Mechanics, founded at Cambridge University Press by George Batchelor in 1956, remains the flagship peer-reviewed venue for research fluid dynamics.", "reference", "knowledge", False,
     [("Journal of Fluid Mechanics", "publication"), ("Cambridge University Press", "organization"), ("George Batchelor", "person"), ("1956", "date"), ("research fluid dynamics", "field")],
     [("Journal of Fluid Mechanics", "George Batchelor", "AUTHORED_BY")],
     "which 1956 Cambridge journal founded by Batchelor anchors fluid mechanics research",
     "Journal Fluid Mechanics Batchelor 1956 Cambridge flagship"),
    # --- 29 ---
    ("IEEE Transactions on Automatic Control, published since 1956, hosts foundational papers across linear systems, robust control, and estimation theory.", "reference", "knowledge", False,
     [("IEEE Transactions on Automatic Control", "publication"), ("1956", "date"), ("robust control", "field"), ("estimation theory", "field")],
     [],
     "which long-running IEEE journal anchors research in control and estimation theory",
     "IEEE Transactions Automatic Control 1956 robust estimation"),
    # --- 30 ---
    ("The ASME Journal of Mechanical Design, launched in 1977, publishes research on design methodology, optimisation, and mechanism synthesis across mechanical engineering.", "reference", "knowledge", False,
     [("ASME Journal of Mechanical Design", "publication"), ("1977", "date"), ("design methodology", "field"), ("mechanism synthesis", "field")],
     [],
     "which 1977 ASME journal anchors mechanical design and mechanism research",
     "ASME JMD mechanical design optimisation mechanism 1977"),
    # --- 31 ---
    ("Theodore von Karman's 1911 paper on the vortex street bearing his name quantified the shedding frequency behind bluff bodies and seeded aeroelastic engineering.", "reference", "knowledge", False,
     [("Theodore von Karman", "person"), ("1911", "date"), ("vortex street", "concept"), ("aeroelastic engineering", "field")],
     [("vortex street", "Theodore von Karman", "AUTHORED_BY")],
     "whose 1911 paper named the vortex street and launched aeroelastic engineering",
     "von Karman vortex street 1911 aeroelastic bluff body"),
    # --- 32 ---
    ("Norbert Wiener's 1948 book Cybernetics framed feedback and communication as a shared engineering discipline spanning servomechanisms, biology, and society.", "reference", "knowledge", False,
     [("Norbert Wiener", "person"), ("1948", "date"), ("Cybernetics", "publication"), ("servomechanisms", "concept")],
     [("Cybernetics", "Norbert Wiener", "AUTHORED_BY")],
     "which 1948 MIT book framed feedback and servomechanisms as the shared core of cybernetics",
     "Wiener 1948 Cybernetics feedback servomechanisms engineering"),
    # --- 33 ---
    ("Willis Carrier's 1902 air-conditioning patent introduced controlled dehumidification to industrial printing and seeded the HVAC research field.", "milestone", "knowledge", False,
     [("Willis Carrier", "person"), ("1902", "date"), ("air-conditioning patent", "publication"), ("HVAC", "field")],
     [("air-conditioning patent", "Willis Carrier", "AUTHORED_BY")],
     "which early-twentieth-century patent for industrial printing seeded modern climate-control research",
     "Carrier early century humidity print shop climate control discipline"),
    # --- 34. noise ---
    ("Remind me to re-run the modal analysis once the revised damping ratio lands in the spec.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Barnes Wallis's geodetic airframe design, first used on the Vickers Wellington bomber from 1936, improved damage tolerance compared to earlier monocoque structures.", "decision", "knowledge", False,
     [("Barnes Wallis", "person"), ("geodetic airframe design", "concept"), ("Vickers Wellington", "concept"), ("1936", "date"), ("monocoque structures", "concept")],
     [("geodetic airframe design", "monocoque structures", "IMPROVES_ON"), ("geodetic airframe design", "Barnes Wallis", "AUTHORED_BY")],
     "which Wallis airframe scheme improved damage tolerance over earlier monocoque designs",
     "Wallis geodetic Wellington 1936 damage tolerance monocoque"),
    # --- 36 ---
    ("George Stephenson's Rocket locomotive, victor of the 1829 Rainhill Trials, fixed the multi-tube boiler and blast pipe as standard steam-locomotive engineering practice.", "milestone", "knowledge", False,
     [("George Stephenson", "person"), ("Rocket locomotive", "concept"), ("1829", "date"), ("Rainhill Trials", "event"), ("multi-tube boiler", "concept"), ("blast pipe", "concept")],
     [("Rocket locomotive", "George Stephenson", "AUTHORED_BY")],
     "which early-Victorian competition winner established the multi-tube boiler configuration for rail traction",
     "Stephenson Rainhill nineteenth century rail traction boiler configuration winner"),
    # --- 37 ---
    ("Rudolf Diesel's compression-ignition engine, patented in 1893, replaces spark ignition with compressive heating and dominates heavy-duty transport and stationary power.", "decision", "knowledge", False,
     [("Rudolf Diesel", "person"), ("compression-ignition engine", "concept"), ("1893", "date"), ("spark ignition", "concept"), ("heavy-duty transport", "field")],
     [("compression-ignition engine", "spark ignition", "REPLACES"), ("compression-ignition engine", "Rudolf Diesel", "AUTHORED_BY")],
     "which 1893 Diesel patent replaced spark ignition with compression ignition in heavy-duty power",
     "Diesel 1893 compression ignition spark heavy duty engine"),
    # --- 38 ---
    ("Charles Parsons's 1884 axial-flow steam turbine supplanted reciprocating steam engines in ship propulsion and central-station power plants within two decades.", "decision", "knowledge", False,
     [("Charles Parsons", "person"), ("1884", "date"), ("axial-flow steam turbine", "concept"), ("reciprocating steam engines", "concept"), ("central-station power plants", "concept")],
     [("axial-flow steam turbine", "reciprocating steam engines", "REPLACES"), ("axial-flow steam turbine", "Charles Parsons", "AUTHORED_BY")],
     "whose late-Victorian rotary prime mover ousted piston engines from ships and utility stations",
     "Parsons axial marine propulsion central station displacement two decades"),
    # --- 39 ---
    ("Frank Whittle's 1930 British patent on the turbojet engine laid the propulsion groundwork eventually flown on the Gloster E.28/39 in 1941.", "reference", "knowledge", False,
     [("Frank Whittle", "person"), ("1930", "date"), ("turbojet engine", "concept"), ("Gloster E.28/39", "concept"), ("1941", "date")],
     [("turbojet engine", "Frank Whittle", "AUTHORED_BY")],
     "whose 1930 British patent seeded the turbojet engine first flown in 1941",
     "Whittle 1930 turbojet patent Gloster E28 1941"),
    # --- 40 ---
    ("Werner von Braun led the Saturn V launch vehicle development at NASA Marshall, producing the only vehicle to loft crews to the Moon between 1969 and 1972.", "reference", "knowledge", False,
     [("Werner von Braun", "person"), ("Saturn V", "concept"), ("NASA Marshall", "organization"), ("1969", "date"), ("1972", "date")],
     [("Saturn V", "Werner von Braun", "AUTHORED_BY")],
     "which NASA Marshall programme under von Braun delivered Saturn V for the Apollo lunar missions",
     "von Braun Saturn V NASA Marshall Apollo 1969 1972"),
    # --- 41 ---
    ("The IEEE 802.3 Ethernet standard, first ratified in 1983, replaced earlier Xerox and DEC proprietary LAN cabling schemes in enterprise networking engineering.", "decision", "knowledge", False,
     [("IEEE 802.3", "framework"), ("Ethernet", "concept"), ("1983", "date"), ("proprietary LAN cabling schemes", "concept"), ("enterprise networking engineering", "field")],
     [("IEEE 802.3", "proprietary LAN cabling schemes", "REPLACES")],
     "which 1983 IEEE standard displaced Xerox and DEC proprietary LAN schemes with Ethernet",
     "IEEE 802.3 Ethernet 1983 Xerox DEC LAN standard"),
    # --- 42 ---
    ("Nigel Shadbolt and Tim Berners-Lee's work on Web engineering is published in venues such as ACM Transactions on the Web, which was established in 2007.", "reference", "knowledge", False,
     [("Nigel Shadbolt", "person"), ("Tim Berners-Lee", "person"), ("Web engineering", "field"), ("ACM Transactions on the Web", "publication"), ("2007", "date")],
     [],
     "which 2007 ACM journal anchors peer-reviewed research on Web engineering",
     "ACM Transactions Web 2007 Shadbolt Berners Lee engineering"),
    # --- 43 ---
    ("The Tacoma Narrows Bridge collapse of November 1940 drove aeroelastic research and forced civil engineering to adopt wind-tunnel testing of long-span bridge decks.", "problem", "knowledge", False,
     [("Tacoma Narrows Bridge", "concept"), ("November 1940", "date"), ("aeroelastic research", "field"), ("wind-tunnel testing", "method"), ("long-span bridge decks", "concept")],
     [],
     "which 1940 suspension-bridge failure pushed civil engineers into wind-tunnel aeroelastic testing",
     "Tacoma Narrows 1940 bridge collapse aeroelastic wind tunnel"),
    # --- 44 ---
    ("Haber and Bosch's ammonia synthesis, industrialised at BASF Oppau in 1913, replaced atmospheric saltpetre extraction as the dominant route to fixed nitrogen for fertiliser.", "decision", "knowledge", False,
     [("Haber and Bosch's ammonia synthesis", "method"), ("BASF Oppau", "organization"), ("1913", "date"), ("atmospheric saltpetre extraction", "method"), ("fixed nitrogen", "concept")],
     [("Haber and Bosch's ammonia synthesis", "atmospheric saltpetre extraction", "REPLACES")],
     "which 1913 BASF process displaced saltpetre mining as the main route to fixed nitrogen",
     "Haber Bosch 1913 BASF Oppau ammonia saltpetre nitrogen"),
    # --- 45 ---
    ("Fritz Haber's 1918 Nobel Prize citation honoured the synthesis of ammonia from its elements, a chemical engineering breakthrough of enormous agricultural impact.", "reference", "knowledge", False,
     [("Fritz Haber", "person"), ("1918", "date"), ("Nobel Prize", "publication"), ("ammonia", "concept")],
     [],
     "which 1918 Nobel Prize honoured the chemical-engineering breakthrough of synthetic ammonia",
     "Haber 1918 Nobel ammonia synthesis agricultural"),
    # --- 46 ---
    ("Jack Kilby's 1958 working integrated circuit at Texas Instruments improved on discrete-component circuit boards by fusing multiple devices onto a single germanium die.", "decision", "knowledge", False,
     [("Jack Kilby", "person"), ("1958", "date"), ("integrated circuit", "concept"), ("Texas Instruments", "organization"), ("discrete-component circuit boards", "concept"), ("germanium die", "concept")],
     [("integrated circuit", "discrete-component circuit boards", "IMPROVES_ON"), ("integrated circuit", "Jack Kilby", "AUTHORED_BY")],
     "which 1958 Texas Instruments demonstrator fused multiple devices onto a single die",
     "Kilby 1958 Texas Instruments integrated circuit germanium discrete"),
    # --- 47 ---
    ("The ACI 318 Building Code Requirements for Structural Concrete, maintained by the American Concrete Institute since 1941, codifies reinforced concrete design in the United States.", "reference", "knowledge", False,
     [("ACI 318", "framework"), ("American Concrete Institute", "organization"), ("1941", "date"), ("reinforced concrete design", "field"), ("United States", "place")],
     [("ACI 318", "American Concrete Institute", "AUTHORED_BY")],
     "which ACI code has codified US reinforced-concrete design since 1941",
     "ACI 318 American Concrete Institute reinforced concrete 1941"),
    # --- 48 ---
    ("The Materials Research Society, founded in 1973 at Penn State, convenes engineering research bridging metallurgy, ceramics, and semiconductor processing.", "milestone", "knowledge", False,
     [("Materials Research Society", "organization"), ("1973", "date"), ("Penn State", "organization"), ("semiconductor processing", "field")],
     [],
     "which early-1970s American scholarly body unites metals, ceramic, and chip-fab research",
     "MRS early 1970s Pennsylvania scholarly body metals ceramic chip fab"),
    # --- 49 ---
    ("George Box and Norman Draper's 1987 book Empirical Model-Building and Response Surfaces made response surface methodology standard in industrial process engineering.", "reference", "knowledge", False,
     [("George Box", "person"), ("Norman Draper", "person"), ("1987", "date"), ("Empirical Model-Building and Response Surfaces", "publication"), ("response surface methodology", "method"), ("industrial process engineering", "field")],
     [("Empirical Model-Building and Response Surfaces", "George Box", "AUTHORED_BY"), ("Empirical Model-Building and Response Surfaces", "Norman Draper", "AUTHORED_BY")],
     "which late-1980s statistics-in-industry volume popularised fitted surface experiment design",
     "Box Draper late eighties fitted surface experiment plant optimisation"),
    # --- 50. noise ---
    ("Flag this question for the structural review meeting on Thursday afternoon, not the Monday standup.", "fact", "noise", True, [], [], None, None),
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
