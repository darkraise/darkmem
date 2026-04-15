"""One-off emitter for classification top-up batch-019 — contrastive_reference_fact mode, environmental / climate slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_019.tmp.jsonl with ids class-01801..01900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_019.tmp.jsonl"
ID_OFFSET = 1800
PAIR_OFFSET = 650

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text MUST contain a citable source (IPCC AR5/AR6 chapter, NOAA/NASA/EPA/EEA/ECMWF publication,
# named peer-reviewed paper in Nature, Nature Climate Change, PNAS, ERL, GRL, Science, or a cited treaty).
# fact_text MUST NOT contain a citation — it is the same underlying claim stated without the source.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Global surface warming since pre-industrial (atmospheric science)
    (
        "IPCC AR6 Working Group I Summary for Policymakers (2021), statement A.1.2, reports that global surface temperature increased by 1.09 degrees Celsius in 2011 to 2020 relative to 1850 to 1900.",
        "knowledge",
        "Global mean surface temperature in the 2011 to 2020 decade was about 1.1 degrees Celsius higher than the 1850 to 1900 pre-industrial baseline.",
        "knowledge",
    ),
    # 2. Anthropogenic attribution (atmospheric science)
    (
        "IPCC AR6 WGI Summary for Policymakers (2021), statement A.1, concludes that it is unequivocal that human influence has warmed the atmosphere, ocean, and land.",
        "knowledge",
        "Human activities are the dominant cause of observed warming of the atmosphere, ocean, and land since the mid-twentieth century.",
        "knowledge",
    ),
    # 3. CO2 concentration record (carbon cycle)
    (
        "NOAA Global Monitoring Laboratory data from the Mauna Loa Observatory reported a 2023 annual mean atmospheric CO2 mole fraction of 421.1 parts per million, the highest in the instrumental record.",
        "knowledge",
        "The annual mean atmospheric carbon dioxide concentration at Mauna Loa reached about 421 parts per million in 2023, the highest level ever directly measured.",
        "knowledge",
    ),
    # 4. Ice-core CO2 baseline (paleoclimate)
    (
        "Luthi et al., Nature 453 (2008) 379-382, extended the EPICA Dome C ice core CO2 record to 800,000 years and showed atmospheric CO2 stayed between 172 and 300 parts per million across that interval.",
        "knowledge",
        "Ice core records show that atmospheric carbon dioxide remained between roughly 170 and 300 parts per million throughout the past 800,000 years, well below present levels.",
        "knowledge",
    ),
    # 5. Ocean heat content (ocean science)
    (
        "Cheng et al., Advances in Atmospheric Sciences 40 (2023) 963-974, reported that global ocean heat content in the upper 2000 metres reached a new record in 2022, with 2022 exceeding 2021 by 10.9 zettajoules.",
        "knowledge",
        "The heat content of the upper 2000 metres of the global ocean reached a new record high in 2022, continuing a multi-decadal warming trend.",
        "knowledge",
    ),
    # 6. Ocean acidification (ocean science)
    (
        "IPCC AR6 WGI Chapter 5 (2021) assesses that the surface open ocean pH has declined by approximately 0.017 to 0.027 units per decade since the late 1980s due to uptake of anthropogenic CO2.",
        "knowledge",
        "Uptake of human-emitted carbon dioxide has lowered surface ocean pH by roughly 0.02 units per decade since the 1980s, a process known as ocean acidification.",
        "knowledge",
    ),
    # 7. Arctic sea ice decline (cryosphere)
    (
        "NSIDC Sea Ice Index v3 records show the September Arctic sea ice extent has declined at about 12.6 percent per decade relative to the 1981 to 2010 mean.",
        "knowledge",
        "September Arctic sea ice extent has been shrinking at roughly 13 percent per decade relative to the late twentieth century average.",
        "knowledge",
    ),
    # 8. Greenland ice sheet mass loss (cryosphere)
    (
        "The IMBIE Team, Nature 579 (2020) 233-239, estimated that the Greenland Ice Sheet lost 3902 plus-or-minus 342 gigatonnes of ice between 1992 and 2018, contributing 10.8 millimetres to global sea level.",
        "knowledge",
        "The Greenland Ice Sheet lost nearly 4000 gigatonnes of mass between 1992 and 2018, raising global mean sea level by about 11 millimetres.",
        "knowledge",
    ),
    # 9. Antarctic ice sheet mass loss (cryosphere)
    (
        "The IMBIE Team, Nature 558 (2018) 219-222, reported that the Antarctic Ice Sheet lost 2720 plus-or-minus 1390 gigatonnes between 1992 and 2017, with accelerating losses from West Antarctica.",
        "knowledge",
        "The Antarctic Ice Sheet has lost mass since 1992 with an accelerating trend driven primarily by ice shelf thinning and glacier retreat in West Antarctica.",
        "knowledge",
    ),
    # 10. Sea level rise (ocean science)
    (
        "IPCC AR6 WGI Chapter 9 (2021) assesses that global mean sea level rose by 0.20 metres between 1901 and 2018 and that the rate accelerated to 3.7 millimetres per year during 2006 to 2018.",
        "knowledge",
        "Global mean sea level rose about 20 centimetres between 1901 and 2018, with the rate accelerating to nearly 4 millimetres per year after 2006.",
        "knowledge",
    ),
    # 11. Paris Agreement temperature goal (mitigation policy)
    (
        "Article 2 of the Paris Agreement (UNFCCC, 2015) sets the long-term goal of holding the increase in global average temperature to well below 2 degrees Celsius above pre-industrial levels and pursuing efforts to limit warming to 1.5 degrees.",
        "knowledge",
        "Parties to the Paris Agreement committed to holding global warming well below 2 degrees Celsius above pre-industrial levels while pursuing efforts to limit it to 1.5 degrees.",
        "knowledge",
    ),
    # 12. Montreal Protocol phase-out (mitigation policy)
    (
        "The Montreal Protocol on Substances that Deplete the Ozone Layer (UNEP, 1987) mandated the phased elimination of chlorofluorocarbons and other ozone-depleting substances, with subsequent amendments including the 2016 Kigali Amendment on hydrofluorocarbons.",
        "knowledge",
        "An international treaty phased out chlorofluorocarbons and related ozone-depleting substances, later extended to cover hydrofluorocarbons, which are potent greenhouse gases.",
        "knowledge",
    ),
    # 13. Ozone layer recovery (atmospheric science)
    (
        "WMO Scientific Assessment of Ozone Depletion 2022 projects that Antarctic springtime ozone will return to 1980 values around 2066 if current compliance with the Montreal Protocol continues.",
        "knowledge",
        "Antarctic springtime stratospheric ozone is projected to recover to its 1980 values around the mid-2060s if nations continue to comply with the existing ozone-protection treaty.",
        "knowledge",
    ),
    # 14. 1.5 C carbon budget (mitigation policy)
    (
        "IPCC AR6 WGI Chapter 5 Table 5.8 (2021) estimates the remaining carbon budget from the start of 2020 for a 50 percent chance of limiting warming to 1.5 degrees at 500 gigatonnes of CO2.",
        "knowledge",
        "The remaining budget of carbon dioxide emissions consistent with a 50 percent chance of staying under 1.5 degrees of warming was about 500 gigatonnes as of the start of 2020.",
        "knowledge",
    ),
    # 15. Fossil-fuel share of emissions (carbon cycle)
    (
        "Friedlingstein et al., 'Global Carbon Budget 2023', Earth System Science Data 15 (2023) 5301-5369, report that fossil CO2 emissions reached 36.8 gigatonnes in 2022 and constitute about 90 percent of total anthropogenic CO2 emissions.",
        "knowledge",
        "Fossil fuel combustion and industrial processes released about 37 gigatonnes of carbon dioxide in 2022 and account for roughly 90 percent of all human-caused CO2 emissions.",
        "knowledge",
    ),
    # 16. Land and ocean sinks (carbon cycle)
    (
        "Friedlingstein et al., 'Global Carbon Budget 2023', ESSD 15 (2023) 5301-5369, estimate that land and ocean sinks together absorbed about 54 percent of anthropogenic CO2 emissions over 2013 to 2022.",
        "knowledge",
        "Natural land and ocean sinks together remove roughly half of human-emitted carbon dioxide from the atmosphere each year, slowing the build-up of atmospheric CO2.",
        "knowledge",
    ),
    # 17. Tropical deforestation (forestry / land use)
    (
        "Hansen et al., Science 342 (2013) 850-853, mapped global forest cover change at 30 metre resolution and estimated a gross loss of 2.3 million square kilometres of tree cover between 2000 and 2012.",
        "knowledge",
        "Roughly 2.3 million square kilometres of tree cover were lost worldwide between 2000 and 2012, with hotspots concentrated in the tropics.",
        "knowledge",
    ),
    # 18. Amazon carbon flux (forestry / biodiversity)
    (
        "Gatti et al., Nature 595 (2021) 388-393, used aircraft observations to show that the southeastern Amazon has become a net source of atmospheric CO2, driven by deforestation and climate warming.",
        "knowledge",
        "Parts of the southeastern Amazon rainforest have switched from net carbon sink to net source in recent years, largely due to deforestation and warming.",
        "knowledge",
    ),
    # 19. Coral reef bleaching (biodiversity / ocean)
    (
        "Hughes et al., Nature 543 (2017) 373-377, documented mass bleaching of the Great Barrier Reef in 2016, with 91 percent of surveyed reefs showing bleaching and strong correlation with degree-heating-weeks.",
        "knowledge",
        "A 2016 marine heatwave triggered widespread coral bleaching on the Great Barrier Reef, affecting more than 90 percent of the reefs that were surveyed.",
        "knowledge",
    ),
    # 20. Biodiversity loss (biodiversity)
    (
        "IPBES Global Assessment Report on Biodiversity and Ecosystem Services (2019) estimates that around one million animal and plant species are threatened with extinction, many within decades.",
        "knowledge",
        "Roughly one million animal and plant species are currently at risk of extinction, many within the coming decades, according to global biodiversity assessments.",
        "knowledge",
    ),
    # 21. Insect decline (biodiversity)
    (
        "Hallmann et al., PLOS ONE 12 (2017) e0185809, reported a 76 percent decline in total flying insect biomass in German protected areas over 27 years of Malaise-trap sampling.",
        "knowledge",
        "Long-term monitoring in German nature reserves recorded a decline of roughly three-quarters in flying insect biomass over 27 years.",
        "knowledge",
    ),
    # 22. Marine heatwaves (ocean science)
    (
        "Oliver et al., Nature Communications 9 (2018) 1324, analysed satellite records and reported that marine heatwave days increased by 54 percent globally between 1925 and 2016.",
        "knowledge",
        "The number of marine heatwave days worldwide has risen by more than half over the past century as the ocean surface has warmed.",
        "knowledge",
    ),
    # 23. Tropical cyclone intensification (atmospheric science)
    (
        "Kossin et al., PNAS 117 (2020) 11975-11980, found a global increase in the probability of major tropical cyclone intensity of about 8 percent per decade over 1979 to 2017 in satellite-derived data.",
        "knowledge",
        "The share of tropical cyclones reaching major hurricane intensity has increased by roughly 8 percent per decade since 1979.",
        "knowledge",
    ),
    # 24. European heatwave attribution (adaptation research)
    (
        "Philip et al., Earth System Dynamics 13 (2022) 1689-1713, attributed the 2022 western European heatwave to human-induced climate change, concluding such events are now about ten times more likely than in a pre-industrial climate.",
        "knowledge",
        "Heatwaves as severe as the 2022 western European event are now roughly ten times more likely than they would have been without human-caused climate change.",
        "knowledge",
    ),
    # 25. Extreme precipitation scaling (atmospheric science)
    (
        "IPCC AR6 WGI Chapter 11 (2021) assesses that heavy precipitation events over most land areas have intensified at a rate broadly consistent with the Clausius-Clapeyron scaling of about 7 percent per degree of warming.",
        "knowledge",
        "Heavy precipitation events over most land areas have become more intense, with atmospheric water vapour capacity increasing by roughly 7 percent for each degree of warming.",
        "knowledge",
    ),
    # 26. Drought in the U.S. Southwest (paleoclimate)
    (
        "Williams et al., Nature Climate Change 12 (2022) 232-234, concluded that the 2000 to 2021 drought in southwestern North America was the driest 22-year period in at least 1200 years as reconstructed from tree rings.",
        "knowledge",
        "The 2000 to 2021 drought in southwestern North America was the driest 22-year span in the region in at least twelve centuries.",
        "knowledge",
    ),
    # 27. AMOC weakening (ocean science)
    (
        "Caesar et al., Nature Geoscience 14 (2021) 118-120, reconstructed the Atlantic Meridional Overturning Circulation from proxies and reported that it is at its weakest in more than a millennium.",
        "knowledge",
        "The Atlantic Meridional Overturning Circulation is now weaker than at any point in the past thousand years, based on multi-proxy reconstructions.",
        "knowledge",
    ),
    # 28. Permafrost carbon (carbon cycle / cryosphere)
    (
        "Schuur et al., Nature 520 (2015) 171-179, estimated that northern permafrost soils contain about 1460 to 1600 petagrams of organic carbon, nearly twice the current atmospheric carbon pool.",
        "knowledge",
        "Northern permafrost soils store roughly 1500 petagrams of organic carbon, almost double the amount currently in the atmosphere.",
        "knowledge",
    ),
    # 29. Methane growth (atmospheric chemistry)
    (
        "NOAA Global Monitoring Laboratory data show that globally averaged atmospheric methane increased by 18.0 parts per billion in 2021, the largest annual growth in the modern record beginning in 1983.",
        "knowledge",
        "Atmospheric methane grew by 18 parts per billion in 2021, the largest one-year increase observed since systematic global measurements began in 1983.",
        "knowledge",
    ),
    # 30. Stratospheric water vapour (atmospheric science)
    (
        "Solomon et al., Science 327 (2010) 1219-1223, showed that a decline in stratospheric water vapour after 2000 slowed the rate of surface warming by about 25 percent relative to the preceding decade.",
        "knowledge",
        "A post-2000 decline in stratospheric water vapour temporarily reduced the rate of global surface warming compared with the 1990s.",
        "knowledge",
    ),
    # 31. Aerosol forcing (air quality)
    (
        "Bellouin et al., Reviews of Geophysics 58 (2020) e2019RG000660, assessed the effective radiative forcing from aerosol-cloud interactions as minus 1.0 watts per square metre with a range from minus 1.7 to minus 0.3.",
        "knowledge",
        "Aerosol-cloud interactions exert a net cooling influence on Earth's energy balance of roughly one watt per square metre, partially offsetting greenhouse warming.",
        "knowledge",
    ),
    # 32. PM2.5 mortality (air quality)
    (
        "The WHO Global Air Quality Guidelines 2021 lowered the annual mean PM2.5 guideline to 5 micrograms per cubic metre, citing cumulative evidence that ambient fine particle pollution causes millions of premature deaths annually.",
        "knowledge",
        "The World Health Organization sets the annual safe limit for fine particulate matter at 5 micrograms per cubic metre; exposure above this level causes millions of premature deaths worldwide each year.",
        "knowledge",
    ),
    # 33. NOx and ground-level ozone (air quality)
    (
        "EPA Integrated Science Assessment for Ozone and Related Photochemical Oxidants (EPA/600/R-20/012, 2020) concludes that short-term ozone exposure causes respiratory morbidity and premature mortality.",
        "knowledge",
        "Short-term exposure to ground-level ozone increases respiratory illness and premature mortality, particularly in vulnerable populations.",
        "knowledge",
    ),
    # 34. Solar photovoltaic cost decline (renewable energy)
    (
        "IRENA, 'Renewable Power Generation Costs in 2022' (2023), reports the global weighted-average levelised cost of electricity from utility-scale solar photovoltaics fell from USD 0.445 per kilowatt-hour in 2010 to USD 0.049 per kilowatt-hour in 2022.",
        "knowledge",
        "The global average cost of electricity from utility-scale solar photovoltaics dropped roughly ninefold between 2010 and 2022, falling below five US cents per kilowatt-hour.",
        "knowledge",
    ),
    # 35. Wind-power cost decline (renewable energy)
    (
        "IRENA, 'Renewable Power Generation Costs in 2022' (2023), reports that the global weighted-average LCOE of onshore wind fell from USD 0.107 per kWh in 2010 to USD 0.033 per kWh in 2022.",
        "knowledge",
        "The global average cost of onshore wind electricity has fallen by nearly 70 percent since 2010 to around three US cents per kilowatt-hour.",
        "knowledge",
    ),
    # 36. EV adoption (mitigation policy)
    (
        "IEA, 'Global EV Outlook 2023', reports that electric car sales reached 10 million in 2022, raising their share of new car sales to 14 percent globally.",
        "knowledge",
        "Electric cars accounted for about 14 percent of new passenger car sales worldwide in 2022, with total annual sales reaching 10 million units.",
        "knowledge",
    ),
    # 37. Coal phase-down (mitigation policy)
    (
        "The Glasgow Climate Pact, adopted at UNFCCC COP26 in 2021, calls on parties to accelerate efforts toward the phase-down of unabated coal power and phase-out of inefficient fossil-fuel subsidies.",
        "knowledge",
        "Parties at the 2021 UN climate summit agreed to accelerate the phase-down of unabated coal power and phase out inefficient fossil-fuel subsidies.",
        "knowledge",
    ),
    # 38. Carbon capture deployment (mitigation technology)
    (
        "IEA, 'CCUS in Clean Energy Transitions' (2023), reports that around 45 commercial facilities capture about 45 million tonnes of CO2 per year globally, well below the scale envisaged in net-zero scenarios.",
        "knowledge",
        "Operating carbon-capture facilities worldwide remove around 45 million tonnes of CO2 per year, a small fraction of what net-zero scenarios require.",
        "knowledge",
    ),
    # 39. Solar geoengineering (geoengineering debates)
    (
        "The National Academies of Sciences, Engineering, and Medicine, 'Reflecting Sunlight' (2021), recommends a cautious, federally coordinated research programme on solar geoengineering while emphasising that it is not a substitute for emissions reduction.",
        "knowledge",
        "Expert panels recommend cautious, government-coordinated research on solar geoengineering while stressing that it cannot substitute for cutting greenhouse-gas emissions.",
        "knowledge",
    ),
    # 40. Stratospheric aerosol injection (geoengineering debates)
    (
        "Tilmes et al., JGR Atmospheres 123 (2018) 4616-4641, used CESM1 simulations to show that stratospheric aerosol injection could offset tropospheric warming but would alter regional precipitation and monsoon circulations.",
        "knowledge",
        "Model studies indicate stratospheric aerosol injection could partially offset surface warming, but would also disrupt regional precipitation patterns and monsoon systems.",
        "knowledge",
    ),
    # 41. Water stress (water)
    (
        "WRI Aqueduct 4.0 (2023) estimates that 25 countries, home to a quarter of the world's population, face extremely high water stress, with withdrawals exceeding 80 percent of renewable supply.",
        "knowledge",
        "About a quarter of the world's population lives in 25 countries where water withdrawals exceed 80 percent of renewable supply, classified as extremely high water stress.",
        "knowledge",
    ),
    # 42. Glacier contribution to sea level (cryosphere)
    (
        "Hugonnet et al., Nature 592 (2021) 726-731, used satellite stereo imagery to estimate that glaciers outside the ice sheets lost 267 gigatonnes per year between 2000 and 2019, contributing 0.74 millimetres per year to sea level rise.",
        "knowledge",
        "Mountain glaciers outside the great ice sheets lost mass at about 267 gigatonnes per year over 2000 to 2019, adding roughly 0.7 millimetres per year to global sea level.",
        "knowledge",
    ),
    # 43. Wildfire carbon emissions (forestry / carbon cycle)
    (
        "Copernicus Atmosphere Monitoring Service press release (2023) reported that Canadian wildfires released about 480 megatonnes of carbon in 2023, more than double the previous annual record for the country.",
        "knowledge",
        "The 2023 Canadian wildfire season released roughly 480 megatonnes of carbon, more than double any previous year on record for the country.",
        "knowledge",
    ),
    # 44. European drought 2022 (adaptation research)
    (
        "The European Commission Joint Research Centre report, 'Drought in Europe August 2022' (JRC130738, 2022), concluded that 47 percent of the territory of the European Union was under drought warning conditions in August 2022, the worst in at least 500 years.",
        "knowledge",
        "Nearly half of the European Union faced drought warning conditions in August 2022, making it the continent's worst drought in at least five centuries.",
        "knowledge",
    ),
    # 45. Mangrove carbon storage (biodiversity / carbon cycle)
    (
        "Donato et al., Nature Geoscience 4 (2011) 293-297, showed that mangroves store 1023 megagrams of carbon per hectare on average, among the most carbon-rich forests in the tropics.",
        "knowledge",
        "Mangrove forests store on the order of 1000 tonnes of carbon per hectare, making them one of the most carbon-dense ecosystems in the tropics.",
        "knowledge",
    ),
    # 46. Nitrogen cycle disruption (biogeochemistry)
    (
        "Rockstrom et al., Nature 461 (2009) 472-475, identified the anthropogenic nitrogen fixation rate of about 121 teragrams per year as exceeding the proposed planetary boundary of 35 teragrams per year.",
        "knowledge",
        "Humans fix reactive nitrogen at roughly three times the rate considered safe for ecosystems, driving widespread eutrophication and pollution of waterways.",
        "knowledge",
    ),
    # 47. Mass balance of ice shelves (cryosphere)
    (
        "Rignot et al., Science 341 (2013) 266-270, used satellite data to estimate that Antarctic ice-shelf basal melting accounts for 1325 gigatonnes per year, exceeding iceberg calving as the main mass-loss process.",
        "knowledge",
        "Basal melting beneath Antarctic ice shelves now removes more ice per year than iceberg calving, with a combined loss of over 1300 gigatonnes annually.",
        "knowledge",
    ),
    # 48. Surface albedo feedback (cryosphere / atmospheric science)
    (
        "Pistone, Eisenman, and Ramanathan, PNAS 111 (2014) 3322-3326, used CERES satellite data to estimate that loss of Arctic sea ice from 1979 to 2011 caused a globally averaged radiative forcing of 0.21 watts per square metre.",
        "knowledge",
        "Loss of reflective Arctic sea ice since 1979 has added about 0.2 watts per square metre to Earth's energy imbalance, amplifying greenhouse-gas warming.",
        "knowledge",
    ),
    # 49. El Nino teleconnections (atmospheric science)
    (
        "NOAA Climate Prediction Center diagnostics and the ECMWF SEAS5 seasonal forecasts indicated in mid-2023 that a strong El Nino event had developed in the tropical Pacific, consistent with widespread warm and dry anomalies across many regions.",
        "knowledge",
        "A strong El Nino event developed in the tropical Pacific during 2023, driving warm and dry anomalies across many regions of the world.",
        "knowledge",
    ),
    # 50. Kyoto Protocol emission commitments (mitigation policy)
    (
        "The Kyoto Protocol to the UNFCCC (1997), Annex B, set binding quantified emission-limitation commitments for industrialised countries, averaging a 5 percent reduction below 1990 levels over 2008 to 2012.",
        "knowledge",
        "The Kyoto Protocol bound industrialised countries to reduce their greenhouse-gas emissions by an average of 5 percent below 1990 levels during 2008 to 2012.",
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
