"""One-off emitter for shared-base batch-092 — knowledge domain (earth sciences: solid-earth and ocean physics).

Writes 50 rows with ids shared-04551..04600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_092.tmp.jsonl"
ID_OFFSET = 4550

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Alfred Wegener's Die Entstehung der Kontinente und Ozeane, published in 1915, argued for continental drift decades before a viable driving mechanism was identified.", "reference", "knowledge", False,
     [("Alfred Wegener", "person"), ("Die Entstehung der Kontinente und Ozeane", "publication"), ("1915", "date"), ("continental drift", "theory")],
     [("Die Entstehung der Kontinente und Ozeane", "Alfred Wegener", "AUTHORED_BY")],
     "which 1915 German book first laid out the case for continental drift",
     "Wegener Entstehung Kontinente Ozeane continental drift year"),
    # --- 2 ---
    ("Harry Hess's 1962 History of Ocean Basins paper proposed seafloor spreading, supplying the mechanism that Wegener's continental drift had lacked.", "milestone", "knowledge", False,
     [("Harry Hess", "person"), ("History of Ocean Basins", "publication"), ("1962", "date"), ("seafloor spreading", "theory"), ("continental drift", "theory")],
     [("History of Ocean Basins", "Harry Hess", "AUTHORED_BY"), ("seafloor spreading", "continental drift", "IMPROVES_ON")],
     "which 1962 paper introduced seafloor spreading as the missing mechanism for drift",
     "Hess ocean basins seafloor spreading mechanism year"),
    # --- 3 ---
    ("The Vine-Matthews-Morley hypothesis of 1963 read symmetric magnetic stripes flanking mid-ocean ridges as direct evidence for seafloor spreading.", "reference", "knowledge", False,
     [("Vine-Matthews-Morley hypothesis", "theory"), ("1963", "date"), ("magnetic stripes", "finding"), ("mid-ocean ridges", "concept"), ("seafloor spreading", "theory")],
     [("Vine-Matthews-Morley hypothesis", "seafloor spreading", "SUPPORTS")],
     "which 1963 hypothesis linked symmetric magnetic stripes to ocean-floor spreading",
     "Vine Matthews Morley magnetic stripes ridge spreading year"),
    # --- 4 ---
    ("J. Tuzo Wilson's 1965 transform fault paper in Nature unified ridges, trenches, and strike-slip faults as the three boundary types of rigid lithospheric plates.", "milestone", "knowledge", False,
     [("J. Tuzo Wilson", "person"), ("transform fault", "concept"), ("1965", "date"), ("Nature", "publication"), ("lithospheric plates", "concept")],
     [("transform fault", "J. Tuzo Wilson", "AUTHORED_BY"), ("transform fault", "Nature", "PUBLISHED_IN")],
     "which 1965 Nature paper introduced transform faults as a third plate boundary type",
     "Wilson transform fault Nature plate boundary year"),
    # --- 5 ---
    ("The Wilson cycle, named for J. Tuzo Wilson, describes the opening and closing of ocean basins over roughly 300 to 500 million year intervals.", "reference", "knowledge", False,
     [("Wilson cycle", "theory"), ("J. Tuzo Wilson", "person"), ("ocean basins", "concept")],
     [("Wilson cycle", "J. Tuzo Wilson", "AUTHORED_BY")],
     "which supercontinent-scale cycle bears the name of the Canadian geophysicist who defined transform faults",
     "Wilson cycle supercontinent opening closing ocean basin"),
    # --- 6 ---
    ("The theory of plate tectonics, consolidated between 1965 and 1968, replaced the older geosyncline theory that had dominated mid-twentieth-century structural geology.", "decision", "knowledge", False,
     [("plate tectonics", "theory"), ("geosyncline theory", "theory"), ("structural geology", "field"), ("1968", "date")],
     [("plate tectonics", "geosyncline theory", "REPLACES")],
     "which late-1960s paradigm supplanted geosyncline theory in structural geology",
     "plate tectonics geosyncline replacement paradigm year"),
    # --- 7 ---
    ("Marie Tharp's hand-drawn bathymetric maps of the 1950s revealed the Mid-Atlantic Ridge rift valley, evidence that helped convince skeptics of seafloor spreading.", "milestone", "knowledge", False,
     [("Marie Tharp", "person"), ("Mid-Atlantic Ridge", "place"), ("rift valley", "concept"), ("seafloor spreading", "theory")],
     [("Mid-Atlantic Ridge", "Marie Tharp", "AUTHORED_BY")],
     "which mid-century cartographer revealed the Mid-Atlantic Ridge rift valley by hand",
     "Tharp bathymetric map Mid-Atlantic Ridge rift valley"),
    # --- 8 ---
    ("Inge Lehmann's 1936 paper identified the Earth's solid inner core by analysing P-wave travel times through the shadow zone.", "milestone", "knowledge", False,
     [("Inge Lehmann", "person"), ("1936", "date"), ("solid inner core", "finding"), ("P-wave", "concept"), ("shadow zone", "concept")],
     [("solid inner core", "Inge Lehmann", "AUTHORED_BY")],
     "which 1936 seismological paper identified the Earth's solid inner core",
     "Lehmann inner core P wave shadow zone discovery year"),
    # --- 9 ---
    ("The moment magnitude scale, introduced by Hiroo Kanamori in 1977, improves on the Richter scale by remaining accurate for very large earthquakes.", "reference", "knowledge", False,
     [("moment magnitude scale", "method"), ("Hiroo Kanamori", "person"), ("1977", "date"), ("Richter scale", "method")],
     [("moment magnitude scale", "Hiroo Kanamori", "AUTHORED_BY"), ("moment magnitude scale", "Richter scale", "IMPROVES_ON")],
     "which 1977 magnitude scale supplanted the Richter scale for great earthquakes",
     "Kanamori moment magnitude Mw Richter saturation year"),
    # --- 10. noise ---
    ("Hold tight, I need to pull up the event catalog entry before quoting the focal depth.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The 1960 Valdivia earthquake off Chile reached moment magnitude 9.5, still the largest instrumentally recorded seismic event in the USGS catalogue.", "reference", "knowledge", False,
     [("1960 Valdivia earthquake", "event"), ("Chile", "place"), ("USGS catalogue", "publication"), ("moment magnitude 9.5", "finding")],
     [("1960 Valdivia earthquake", "Chile", "LOCATED_IN")],
     "which 1960 Chilean earthquake remains the largest in the USGS instrumental record",
     "Valdivia 1960 Chile Mw 9.5 USGS instrumental record"),
    # --- 12 ---
    ("The 2011 Tohoku earthquake off northeastern Japan reached moment magnitude 9.1 and triggered the Fukushima Daiichi nuclear disaster.", "fact", "knowledge", False,
     [("2011 Tohoku earthquake", "event"), ("Japan", "place"), ("Fukushima Daiichi", "place"), ("moment magnitude 9.1", "finding")],
     [("2011 Tohoku earthquake", "Fukushima Daiichi", "CAUSES")],
     "which magnitude-9 event in 2011 led to the meltdown at a coastal reactor complex",
     "Tohoku event reactor meltdown coastal Honshu"),
    # --- 13 ---
    ("The Epidemic Type Aftershock Sequence model, formulated by Yosihiko Ogata in 1988, replaces simple Omori decay with a branching point process for aftershock forecasting.", "reference", "knowledge", False,
     [("Epidemic Type Aftershock Sequence model", "method"), ("Yosihiko Ogata", "person"), ("1988", "date"), ("Omori decay", "method"), ("aftershock forecasting", "concept")],
     [("Epidemic Type Aftershock Sequence model", "Yosihiko Ogata", "AUTHORED_BY"), ("Epidemic Type Aftershock Sequence model", "Omori decay", "IMPROVES_ON")],
     "which 1988 statistical model supplanted plain Omori decay for aftershock forecasting",
     "ETAS Ogata branching Omori aftershock forecast year"),
    # --- 14 ---
    ("The 1991 eruption of Mount Pinatubo in the Philippines injected roughly 20 megatons of sulfur dioxide into the stratosphere, cooling global surface temperature by about 0.5 degrees Celsius.", "fact", "knowledge", False,
     [("Mount Pinatubo", "place"), ("Philippines", "place"), ("1991", "date"), ("sulfur dioxide", "concept"), ("stratosphere", "concept")],
     [("Mount Pinatubo", "Philippines", "LOCATED_IN")],
     "which 1991 Philippine eruption cooled global surface temperature by about half a degree",
     "Pinatubo 1991 Philippines stratospheric sulfur cooling"),
    # --- 15 ---
    ("The 1815 eruption of Mount Tambora on Sumbawa registered VEI 7 and produced the 1816 Year Without a Summer across the Northern Hemisphere.", "fact", "knowledge", False,
     [("Mount Tambora", "place"), ("Sumbawa", "place"), ("1815", "date"), ("VEI 7", "concept"), ("Year Without a Summer", "event")],
     [("Mount Tambora", "Sumbawa", "LOCATED_IN"), ("Mount Tambora", "Year Without a Summer", "CAUSES")],
     "which 1815 Indonesian eruption produced the following Year Without a Summer",
     "Tambora 1815 Sumbawa VEI 7 Year Without Summer"),
    # --- 16 ---
    ("The 1883 eruption of Krakatoa in the Sunda Strait killed more than 36,000 people, mostly through caldera-collapse tsunamis that reached South Africa.", "fact", "knowledge", False,
     [("Krakatoa", "place"), ("Sunda Strait", "place"), ("1883", "date"), ("caldera-collapse tsunamis", "concept"), ("South Africa", "place")],
     [("Krakatoa", "Sunda Strait", "LOCATED_IN"), ("Krakatoa", "caldera-collapse tsunamis", "CAUSES")],
     "which nineteenth-century Indonesian volcano produced long-distance ocean waves that reached the Cape",
     "Indonesian volcano 19th century long distance wave Cape"),
    # --- 17 ---
    ("The 2022 Hunga Tonga-Hunga Ha'apai eruption generated a Lamb wave that circled the globe several times and lofted water vapour into the mesosphere.", "milestone", "knowledge", False,
     [("Hunga Tonga-Hunga Ha'apai", "place"), ("2022", "date"), ("Lamb wave", "concept"), ("mesosphere", "concept")],
     [("Hunga Tonga-Hunga Ha'apai", "Lamb wave", "CAUSES")],
     "which 2022 submarine eruption launched a Lamb wave around the globe",
     "Hunga Tonga 2022 Lamb wave mesosphere water vapour"),
    # --- 18 ---
    ("The Volcanic Explosivity Index, introduced by Chris Newhall and Steve Self in 1982, ranks eruptions on a logarithmic scale from 0 to 8 by tephra volume and plume height.", "reference", "knowledge", False,
     [("Volcanic Explosivity Index", "method"), ("Chris Newhall", "person"), ("Steve Self", "person"), ("1982", "date"), ("tephra volume", "concept")],
     [("Volcanic Explosivity Index", "Chris Newhall", "AUTHORED_BY")],
     "which 1982 index ranks eruptions from 0 to 8 by tephra volume and plume height",
     "VEI Newhall Self 1982 eruption scale tephra"),
    # --- 19 ---
    ("The Walker circulation, identified by Jacob Bjerknes in 1969, couples east-west tropical Pacific pressure anomalies to sea-surface temperature in the ENSO system.", "reference", "knowledge", False,
     [("Walker circulation", "concept"), ("Jacob Bjerknes", "person"), ("1969", "date"), ("tropical Pacific", "place"), ("ENSO", "concept")],
     [("Walker circulation", "Jacob Bjerknes", "AUTHORED_BY"), ("Walker circulation", "ENSO", "RELATED_TO")],
     "whose 1969 paper first linked the Walker circulation to ENSO dynamics",
     "Bjerknes Walker circulation ENSO tropical Pacific coupling year"),
    # --- 20 ---
    ("The 1997-1998 El Nino, classed as a super ENSO event, shifted Pacific rainfall patterns and caused an estimated 34 billion USD in global damage.", "fact", "knowledge", False,
     [("1997-1998 El Nino", "event"), ("ENSO", "concept"), ("Pacific", "place")],
     [("1997-1998 El Nino", "ENSO", "IS_A")],
     "which 1997-1998 ENSO event ranks among the strongest on record",
     "1997 1998 El Nino super ENSO Pacific rainfall"),
    # --- 21 ---
    ("The Atlantic Meridional Overturning Circulation transports roughly 17 sverdrups of warm surface water northward and is central to Quaternary abrupt-climate theory.", "reference", "knowledge", False,
     [("Atlantic Meridional Overturning Circulation", "concept"), ("sverdrups", "concept"), ("Quaternary", "concept")],
     [],
     "which thermohaline cell figures heavily in debates over abrupt climate change",
     "AMOC thermohaline deep water formation North Atlantic"),
    # --- 22 ---
    ("The GEOTRACES program, launched internationally in 2010, systematically maps trace elements and isotopes across all major ocean basins.", "reference", "knowledge", False,
     [("GEOTRACES", "project"), ("2010", "date"), ("trace elements", "concept"), ("ocean basins", "concept")],
     [],
     "which international program launched in 2010 maps ocean trace elements and isotopes",
     "GEOTRACES trace elements isotopes ocean basins 2010"),
    # --- 23 ---
    ("The Argo float array, now comprising nearly 4,000 autonomous profilers, replaces expedition-only ocean observation with near-real-time upper-ocean coverage.", "milestone", "knowledge", False,
     [("Argo float array", "infrastructure"), ("autonomous profilers", "tool"), ("expedition-only ocean observation", "method")],
     [("Argo float array", "expedition-only ocean observation", "REPLACES")],
     "which autonomous float array supplanted expedition-only ocean observation",
     "Argo float array 4000 profiler ocean coverage"),
    # --- 24 ---
    ("Alvin, the deep-submergence vehicle operated by Woods Hole Oceanographic Institution since 1964, discovered hydrothermal vents at the Galapagos Rift in 1977.", "milestone", "knowledge", False,
     [("Alvin", "tool"), ("Woods Hole Oceanographic Institution", "organization"), ("1964", "date"), ("hydrothermal vents", "finding"), ("Galapagos Rift", "place"), ("1977", "date")],
     [("Alvin", "Woods Hole Oceanographic Institution", "WORKS_AT"), ("Alvin", "hydrothermal vents", "PRODUCES")],
     "which long-running American deep-diving vessel found chimney fauna off the equator in the late seventies",
     "American deep dive vessel equatorial chimney fauna seventies"),
    # --- 25 ---
    ("The Jiaolong submersible, operated by China's State Oceanic Administration, reached 7,062 metres in the Mariana Trench in 2012.", "fact", "knowledge", False,
     [("Jiaolong", "tool"), ("State Oceanic Administration", "organization"), ("Mariana Trench", "place"), ("2012", "date")],
     [("Jiaolong", "State Oceanic Administration", "WORKS_AT"), ("Jiaolong", "Mariana Trench", "VISITED")],
     "which Chinese crewed deep-diving platform achieved a seven-kilometre dive early in the 2010s",
     "Beijing SOA manned submersible Pacific trench record"),
    # --- 26 ---
    ("The Vostok ice core, drilled between 1970 and 1998 at the Russian Vostok station in East Antarctica, recovered a 420,000-year climate archive.", "milestone", "knowledge", False,
     [("Vostok ice core", "publication"), ("Vostok station", "place"), ("East Antarctica", "place"), ("1998", "date")],
     [("Vostok ice core", "Vostok station", "LOCATED_IN")],
     "which Antarctic ice core recovered a 420,000-year climate archive by 1998",
     "Vostok ice core East Antarctica 420 kyr 1998"),
    # --- 27 ---
    ("The EPICA Dome C ice core, completed in 2004, extended the continuous Antarctic climate record to 800,000 years and superseded Vostok as the deepest archive.", "milestone", "knowledge", False,
     [("EPICA Dome C ice core", "publication"), ("2004", "date"), ("Vostok", "place")],
     [("EPICA Dome C ice core", "Vostok", "REPLACES")],
     "which 2004 ice core project pushed the continuous Antarctic record back to 800,000 years",
     "EPICA Dome C 800 kyr 2004 Vostok extension"),
    # --- 28 ---
    ("The oxygen isotope ratios in benthic foraminifera, systematised by Nicholas Shackleton in 1967, serve as a primary paleoclimate proxy for global ice volume.", "reference", "knowledge", False,
     [("oxygen isotope ratios", "method"), ("benthic foraminifera", "concept"), ("Nicholas Shackleton", "person"), ("1967", "date"), ("global ice volume", "concept")],
     [("oxygen isotope ratios", "Nicholas Shackleton", "AUTHORED_BY")],
     "whose 1967 work made benthic foraminiferal delta-18-O a primary ice volume proxy",
     "Shackleton 1967 benthic foram delta 18 O ice volume"),
    # --- 29 ---
    ("The Milankovitch theory of orbital forcing, published by Milutin Milankovitch in 1941, attributes Quaternary glacial cycles to eccentricity, obliquity, and precession.", "reference", "knowledge", False,
     [("Milankovitch theory", "theory"), ("Milutin Milankovitch", "person"), ("1941", "date"), ("Quaternary", "concept"), ("eccentricity", "concept"), ("obliquity", "concept")],
     [("Milankovitch theory", "Milutin Milankovitch", "AUTHORED_BY")],
     "which 1941 theory attributed Quaternary ice ages to orbital eccentricity and obliquity",
     "Milankovitch 1941 orbital forcing Quaternary glacial cycles"),
    # --- 30 ---
    ("The Hays-Imbrie-Shackleton 1976 Science paper titled Variations in the Earth's Orbit: Pacemaker of the Ice Ages confirmed the Milankovitch theory with deep-sea sediment spectra.", "milestone", "knowledge", False,
     [("Hays-Imbrie-Shackleton", "publication"), ("1976", "date"), ("Science", "publication"), ("Milankovitch theory", "theory")],
     [("Hays-Imbrie-Shackleton", "Science", "PUBLISHED_IN"), ("Hays-Imbrie-Shackleton", "Milankovitch theory", "SUPPORTS")],
     "which 1976 Science paper confirmed Milankovitch forcing using deep-sea sediment spectra",
     "Hays Imbrie Shackleton 1976 Science pacemaker ice ages"),
    # --- 31 ---
    ("The USGS National Earthquake Information Center in Golden, Colorado operates the Advanced National Seismic System catalogue that underpins modern hazard maps.", "architecture", "knowledge", False,
     [("USGS National Earthquake Information Center", "organization"), ("Golden", "place"), ("Colorado", "place"), ("Advanced National Seismic System", "infrastructure")],
     [("USGS National Earthquake Information Center", "Golden", "LOCATED_IN"), ("USGS National Earthquake Information Center", "Advanced National Seismic System", "USES")],
     "which USGS center in Golden Colorado runs the ANSS seismic catalogue",
     "NEIC USGS Golden Colorado ANSS catalogue"),
    # --- 32 ---
    ("Earth Surface Processes and Landforms, founded in 1976 by Michael J. Kirkby, became a core journal for geomorphology and surface-process modelling.", "reference", "knowledge", False,
     [("Earth Surface Processes and Landforms", "publication"), ("1976", "date"), ("Michael J. Kirkby", "person"), ("geomorphology", "field")],
     [("Earth Surface Processes and Landforms", "Michael J. Kirkby", "AUTHORED_BY")],
     "which 1976 journal anchors geomorphology and surface-process modelling",
     "Earth Surface Processes Landforms 1976 Kirkby geomorphology"),
    # --- 33 ---
    ("The journal Earth and Planetary Science Letters, founded in 1966 by Elsevier, publishes short-format papers across geochemistry, geophysics, and planetary science.", "reference", "knowledge", False,
     [("Earth and Planetary Science Letters", "publication"), ("1966", "date"), ("Elsevier", "organization"), ("geochemistry", "field"), ("geophysics", "field")],
     [("Earth and Planetary Science Letters", "Elsevier", "AUTHORED_BY")],
     "which 1966 Elsevier journal anchors short-format geochemistry and geophysics papers",
     "EPSL Earth Planetary Science Letters 1966 Elsevier short format"),
    # --- 34. noise ---
    ("Give me a moment to cross-reference that stratigraphic column before I commit to a formation name.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Journal of Geophysical Research, launched by the American Geophysical Union in 1949, split into multiple sections including Solid Earth and Oceans as the field diversified.", "reference", "knowledge", False,
     [("Journal of Geophysical Research", "publication"), ("American Geophysical Union", "organization"), ("1949", "date"), ("Solid Earth", "field"), ("Oceans", "field")],
     [("Journal of Geophysical Research", "American Geophysical Union", "AUTHORED_BY")],
     "which AGU journal, launched in 1949, later split into Solid Earth and Oceans sections",
     "JGR American Geophysical Union 1949 Solid Earth Oceans"),
    # --- 36 ---
    ("Nature Geoscience, launched in 2008, became a high-impact venue for short-format solid-earth, ocean, and atmospheric papers within the Nature family.", "reference", "knowledge", False,
     [("Nature Geoscience", "publication"), ("2008", "date")],
     [],
     "which 2008 Nature spinoff serves short-format earth-science papers",
     "Nature Geoscience 2008 launch solid earth ocean atmospheric"),
    # --- 37 ---
    ("The Deep Sea Drilling Project, operating the Glomar Challenger from 1968 to 1983, recovered sediment cores that confirmed seafloor-spreading rates across the major ocean basins.", "milestone", "knowledge", False,
     [("Deep Sea Drilling Project", "project"), ("Glomar Challenger", "tool"), ("1968", "date"), ("1983", "date"), ("seafloor-spreading rates", "finding")],
     [("Deep Sea Drilling Project", "Glomar Challenger", "USES"), ("Deep Sea Drilling Project", "seafloor-spreading rates", "PRODUCES")],
     "which 1968-1983 drilling program used the Glomar Challenger to confirm spreading rates",
     "DSDP Glomar Challenger 1968 1983 seafloor spreading rates"),
    # --- 38 ---
    ("The Ocean Drilling Program, running from 1985 to 2003 aboard the JOIDES Resolution, succeeded DSDP and extended scientific drilling into the Cretaceous rock record.", "milestone", "knowledge", False,
     [("Ocean Drilling Program", "project"), ("JOIDES Resolution", "tool"), ("1985", "date"), ("2003", "date"), ("DSDP", "project"), ("Cretaceous", "concept")],
     [("Ocean Drilling Program", "JOIDES Resolution", "USES"), ("Ocean Drilling Program", "DSDP", "REPLACES")],
     "which 1985-2003 program aboard JOIDES Resolution succeeded the DSDP",
     "ODP JOIDES Resolution 1985 2003 DSDP successor"),
    # --- 39 ---
    ("The International Ocean Discovery Program, launched in 2013, now coordinates the JOIDES Resolution, Chikyu, and mission-specific platforms for scientific ocean drilling.", "architecture", "knowledge", False,
     [("International Ocean Discovery Program", "project"), ("JOIDES Resolution", "tool"), ("Chikyu", "tool"), ("2013", "date")],
     [("International Ocean Discovery Program", "JOIDES Resolution", "USES"), ("International Ocean Discovery Program", "Chikyu", "USES")],
     "which 2013 program coordinates JOIDES Resolution and Chikyu for ocean drilling",
     "IODP 2013 JOIDES Resolution Chikyu mission specific"),
    # --- 40 ---
    ("Keiiti Aki's 1967 formulation of the omega-squared source spectrum became the standard model for earthquake source radiation in modern seismology.", "reference", "knowledge", False,
     [("Keiiti Aki", "person"), ("1967", "date"), ("omega-squared source spectrum", "method"), ("seismology", "field")],
     [("omega-squared source spectrum", "Keiiti Aki", "AUTHORED_BY")],
     "whose late-1960s paper defined the canonical falloff spectrum used for quake source radiation",
     "canonical falloff spectrum source radiation late 1960s Japanese seismologist"),
    # --- 41 ---
    ("The Gutenberg-Richter law, formalised in 1944, relates earthquake magnitude to frequency through a log-linear b-value that modern catalog analysis still uses.", "reference", "knowledge", False,
     [("Gutenberg-Richter law", "theory"), ("1944", "date"), ("b-value", "concept")],
     [],
     "which 1944 statistical law links earthquake magnitude to frequency through a b-value",
     "Gutenberg Richter 1944 b value magnitude frequency"),
    # --- 42 ---
    ("Walter Munk's 1950 wave-forecasting methods improved on amateur ocean-swell estimates and underpinned D-day surf prediction at Normandy.", "milestone", "knowledge", False,
     [("Walter Munk", "person"), ("1950", "date"), ("wave-forecasting methods", "method"), ("D-day surf prediction", "event"), ("Normandy", "place")],
     [("wave-forecasting methods", "Walter Munk", "AUTHORED_BY"), ("wave-forecasting methods", "D-day surf prediction", "APPLIES_TO")],
     "whose 1950 work formalised ocean wave forecasting from storm observations",
     "Munk 1950 wave forecasting D-day Normandy surf"),
    # --- 43 ---
    ("Henry Stommel's 1948 paper explained why western boundary currents like the Gulf Stream intensify, grounding modern dynamical oceanography.", "reference", "knowledge", False,
     [("Henry Stommel", "person"), ("1948", "date"), ("western boundary currents", "concept"), ("Gulf Stream", "place"), ("dynamical oceanography", "field")],
     [("western boundary currents", "Henry Stommel", "AUTHORED_BY")],
     "whose postwar paper solved the intensification puzzle for currents on the west side of basins",
     "postwar intensification puzzle basin west side current paper"),
    # --- 44 ---
    ("Munk and Wunsch's 1998 paper Abyssal Recipes II argued that tidal mixing supplies roughly half of the 2.1 terawatts needed to sustain the abyssal overturning circulation.", "reference", "knowledge", False,
     [("Munk", "person"), ("Wunsch", "person"), ("Abyssal Recipes II", "publication"), ("1998", "date"), ("tidal mixing", "concept"), ("abyssal overturning circulation", "concept")],
     [("Abyssal Recipes II", "Munk", "AUTHORED_BY"), ("Abyssal Recipes II", "Wunsch", "AUTHORED_BY")],
     "which 1998 paper attributed much of abyssal mixing power to internal tides",
     "Munk Wunsch 1998 Abyssal Recipes II tidal mixing 2.1 TW"),
    # --- 45 ---
    ("The Darcy law for groundwater flow, formulated by Henry Darcy in 1856, remains the linear-flow foundation of quantitative hydrology.", "reference", "knowledge", False,
     [("Darcy law", "theory"), ("Henry Darcy", "person"), ("1856", "date"), ("groundwater flow", "concept"), ("hydrology", "field")],
     [("Darcy law", "Henry Darcy", "AUTHORED_BY")],
     "which 1856 law gave hydrology its linear groundwater flow relation",
     "Darcy 1856 law groundwater hydrology linear"),
    # --- 46 ---
    ("The GRACE satellite mission, flown by NASA and DLR between 2002 and 2017, measured month-to-month variations in terrestrial water storage from gravity anomalies.", "milestone", "knowledge", False,
     [("GRACE", "project"), ("NASA", "organization"), ("DLR", "organization"), ("2002", "date"), ("2017", "date"), ("terrestrial water storage", "concept")],
     [("GRACE", "NASA", "WORKS_AT"), ("GRACE", "DLR", "WORKS_AT"), ("GRACE", "terrestrial water storage", "PRODUCES")],
     "which 2002-2017 NASA-DLR satellite mission mapped terrestrial water storage from gravity",
     "GRACE 2002 2017 NASA DLR gravity water storage"),
    # --- 47 ---
    ("The Richter scale, defined by Charles Richter in 1935, was originally calibrated for Wood-Anderson seismographs in southern California and saturates above magnitude 7.", "reference", "knowledge", False,
     [("Richter scale", "method"), ("Charles Richter", "person"), ("1935", "date"), ("Wood-Anderson seismographs", "tool"), ("southern California", "place")],
     [("Richter scale", "Charles Richter", "AUTHORED_BY"), ("Richter scale", "Wood-Anderson seismographs", "USES")],
     "which pre-war California magnitude scale saturates above the mid-sevens",
     "pre war California magnitude scale mid seven saturation"),
    # --- 48 ---
    ("Frank Press's 1960s free-oscillation studies of the 1960 Chile earthquake confirmed the Earth's normal-mode spectrum predicted by Horace Lamb in 1882.", "fact", "knowledge", False,
     [("Frank Press", "person"), ("1960 Chile earthquake", "event"), ("Horace Lamb", "person"), ("1882", "date"), ("normal-mode spectrum", "concept")],
     [("normal-mode spectrum", "Horace Lamb", "AUTHORED_BY")],
     "whose free-oscillation measurements of the 1960 Chile event confirmed Lamb's 1882 spectrum",
     "Frank Press free oscillation 1960 Chile Lamb 1882 normal modes"),
    # --- 49 ---
    ("The Snowball Earth hypothesis, revived by Paul Hoffman and Daniel Schrag in 1998, interprets Neoproterozoic cap carbonates as evidence of near-global Cryogenian glaciation.", "reference", "knowledge", False,
     [("Snowball Earth hypothesis", "theory"), ("Paul Hoffman", "person"), ("Daniel Schrag", "person"), ("1998", "date"), ("Neoproterozoic", "concept"), ("cap carbonates", "concept")],
     [("Snowball Earth hypothesis", "Paul Hoffman", "AUTHORED_BY"), ("Snowball Earth hypothesis", "Daniel Schrag", "AUTHORED_BY")],
     "whose 1998 revival argued Neoproterozoic cap carbonates record near-global glaciation",
     "Hoffman Schrag 1998 Snowball Earth Neoproterozoic cap carbonate"),
    # --- 50 ---
    ("InSAR interferometry, pioneered for coseismic deformation by Didier Massonnet on the 1992 Landers earthquake, largely replaces single-point GPS campaigns for mapping surface rupture fields.", "milestone", "knowledge", False,
     [("InSAR interferometry", "method"), ("Didier Massonnet", "person"), ("1992 Landers earthquake", "event"), ("GPS campaigns", "method")],
     [("InSAR interferometry", "Didier Massonnet", "AUTHORED_BY"), ("InSAR interferometry", "GPS campaigns", "REPLACES")],
     "whose 1992 Landers study established InSAR for mapping coseismic deformation",
     "Massonnet 1992 Landers InSAR interferometry GPS campaign"),
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
