"""One-off emitter for shared-base batch-280 — knowledge domain (20th-century world history: WWI, Versailles, Russian Revolution, Weimar, Great Depression, WWII, Cold War, decolonisation, 1989-1995).

Writes 50 rows to data/v2/shared/batch_280.tmp.jsonl with ids shared-13951..14000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_280.tmp.jsonl"
ID_OFFSET = 13950

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
# Target mix (48 non-noise): decision 12, architecture 9, milestone 7, fact 7, reference 6, preference 4, problem 3.
ENTRIES: list[tuple] = [
    # --- 1 milestone ---
    ("The assassination of Archduke Franz Ferdinand in Sarajevo on 28 June 1914 detonated the network of alliances that pulled the great powers into the First World War within six weeks.", "milestone", "knowledge", False,
     [("Archduke Franz Ferdinand", "person"), ("Sarajevo", "place"), ("First World War", "event"), ("28 June 1914", "date")],
     [("Archduke Franz Ferdinand", "First World War", "CAUSES"), ("Archduke Franz Ferdinand", "Sarajevo", "LOCATED_IN")],
     "which Sarajevo killing in June 1914 triggered the alliance cascade into the First World War",
     "franz ferdinand sarajevo 1914 alliance first world war trigger"),
    # --- 2 fact ---
    ("Trench warfare on the Western Front locked France and Germany into a three-year stalemate where machine guns and barbed wire turned every attempt at breakthrough into a casualty bill in the hundreds of thousands.", "fact", "knowledge", False,
     [("Trench warfare", "concept"), ("Western Front", "place"), ("France", "place"), ("Germany", "place"), ("machine guns", "tool")],
     [("Trench warfare", "Western Front", "APPLIES_TO"), ("France", "Germany", "RELATED_TO")],
     "which Western Front tactics kept France and Germany in stalemate during the First World War",
     "trench warfare western front france germany machine gun stalemate"),
    # --- 3 decision ---
    ("The Treaty of Versailles signed in June 1919 pinned war guilt on Germany, capped the Reichswehr at 100,000 men, and imposed reparations that shaped European diplomacy for a generation.", "decision", "knowledge", False,
     [("Treaty of Versailles", "event"), ("Germany", "place"), ("Reichswehr", "organization"), ("reparations", "concept"), ("June 1919", "date")],
     [("Treaty of Versailles", "Germany", "APPLIES_TO"), ("Treaty of Versailles", "reparations", "CAUSES")],
     "which 1919 treaty pinned war guilt on Germany and capped its army at 100,000 men",
     "treaty versailles 1919 germany war guilt reichswehr reparation"),
    # --- 4 milestone ---
    ("The October Revolution of 1917 put the Bolsheviks in power in Petrograd; Lenin returned from Swiss exile in a sealed train and Trotsky organised the Red Guard that stormed the Winter Palace.", "milestone", "knowledge", False,
     [("October Revolution", "event"), ("Bolsheviks", "organization"), ("Petrograd", "place"), ("Lenin", "person"), ("Trotsky", "person"), ("Red Guard", "organization"), ("Winter Palace", "place")],
     [("Lenin", "Bolsheviks", "WORKS_AT"), ("Trotsky", "Red Guard", "WORKS_AT"), ("October Revolution", "Petrograd", "LOCATED_IN")],
     "which 1917 Petrograd seizure of power did Lenin and Trotsky lead for the Bolsheviks",
     "october revolution 1917 bolshevik lenin trotsky petrograd winter palace"),
    # --- 6 fact ---
    ("Weimar hyperinflation peaked in November 1923 when one US dollar fetched 4.2 trillion marks; wheelbarrows of cash bought loaves of bread and savings of the middle class evaporated inside a year.", "fact", "knowledge", False,
     [("Weimar", "organization"), ("November 1923", "date"), ("US dollar", "concept"), ("mark", "concept"), ("hyperinflation", "concept")],
     [("hyperinflation", "Weimar", "APPLIES_TO")],
     "how extreme did the Weimar mark collapse get in November 1923 against the US dollar",
     "weimar hyperinflation 1923 mark dollar bread savings middle class"),
    # --- 7 milestone ---
    ("Black Tuesday on 29 October 1929 crashed the Wall Street market and wiped out fourteen billion dollars of paper value in a single session, seeding the Great Depression across the industrial world.", "milestone", "knowledge", False,
     [("Black Tuesday", "event"), ("29 October 1929", "date"), ("Wall Street", "place"), ("Great Depression", "event")],
     [("Black Tuesday", "Wall Street", "LOCATED_IN"), ("Black Tuesday", "Great Depression", "CAUSES")],
     "which single October 1929 trading session destroyed fourteen billion dollars on Wall Street",
     "black tuesday 1929 wall street crash depression industrial"),
    # --- 8 decision ---
    ("Franklin Delano Roosevelt launched the New Deal in 1933 to pull the United States out of the Great Depression; the Civilian Conservation Corps and the Works Progress Administration together put millions back to work on public projects.", "decision", "knowledge", False,
     [("Franklin Delano Roosevelt", "person"), ("New Deal", "event"), ("United States", "place"), ("Great Depression", "event"), ("Civilian Conservation Corps", "organization"), ("Works Progress Administration", "organization")],
     [("Franklin Delano Roosevelt", "New Deal", "PRODUCES"), ("New Deal", "Great Depression", "FIXES")],
     "which 1933 Roosevelt programme put Americans back to work to counter the Great Depression",
     "new deal roosevelt 1933 ccc wpa great depression public work"),
    # --- 9 fact ---
    ("The Spanish Civil War from 1936 to 1939 ended with Franco's Nationalists victorious over the Republic; Guernica was bombed by the Luftwaffe's Condor Legion in April 1937 as a rehearsal for later blitzkrieg tactics.", "fact", "knowledge", False,
     [("Spanish Civil War", "event"), ("Franco", "person"), ("Nationalists", "organization"), ("Guernica", "place"), ("Condor Legion", "organization"), ("April 1937", "date")],
     [("Franco", "Nationalists", "WORKS_AT"), ("Condor Legion", "Guernica", "APPLIES_TO")],
     "which 1936 to 1939 conflict ended with Franco's Nationalists and saw Guernica bombed in 1937",
     "spanish civil war franco guernica condor legion 1937 blitzkrieg"),
    # --- 10 noise ---
    ("The cafeteria at the Belle Époque museum still serves the same oat biscuit recipe the founder's mother used in 1912 and there is a small plaque above the counter that says so.", "fact", "noise", True, [], [], None, None),
    # --- 11 milestone ---
    ("Adolf Hitler was appointed Chancellor of Germany on 30 January 1933; the Reichstag Fire Decree a month later suspended civil liberties and the Enabling Act in March let the Nazi cabinet legislate without the Reichstag.", "milestone", "knowledge", False,
     [("Adolf Hitler", "person"), ("Germany", "place"), ("30 January 1933", "date"), ("Reichstag Fire Decree", "event"), ("Enabling Act", "event"), ("Nazi", "organization"), ("Reichstag", "organization")],
     [("Adolf Hitler", "Nazi", "WORKS_AT"), ("Enabling Act", "Reichstag", "REPLACES")],
     "which January 1933 appointment and two decrees that spring let Hitler rule Germany without parliament",
     "hitler chancellor 1933 reichstag fire enabling act nazi germany"),
    # --- 12 fact ---
    ("The Japanese Kwantung Army invaded Manchuria in September 1931 and installed the puppet state of Manchukuo; the League of Nations condemned the move, Japan withdrew from the League in 1933, and the body lost its last credibility.", "fact", "knowledge", False,
     [("Kwantung Army", "organization"), ("Manchuria", "place"), ("Manchukuo", "place"), ("League of Nations", "organization"), ("Japan", "place"), ("September 1931", "date")],
     [("Kwantung Army", "Manchuria", "APPLIES_TO"), ("Japan", "League of Nations", "CONTRADICTS")],
     "which 1931 Japanese invasion and puppet state broke the League of Nations credibility",
     "kwantung manchuria 1931 manchukuo league nations japan withdraw"),
    # --- 13 decision ---
    ("Chamberlain returned from the Munich Conference on 30 September 1938 waving a paper that ceded the Sudetenland to Hitler and promising peace for our time; Czechoslovakia was dismembered within six months.", "decision", "knowledge", False,
     [("Chamberlain", "person"), ("Munich Conference", "event"), ("Sudetenland", "place"), ("Hitler", "person"), ("Czechoslovakia", "place"), ("30 September 1938", "date")],
     [("Chamberlain", "Munich Conference", "WORKS_AT"), ("Munich Conference", "Czechoslovakia", "APPLIES_TO")],
     "which September 1938 conference ceded the Sudetenland to Hitler under Chamberlain's signature",
     "munich 1938 chamberlain sudetenland hitler czechoslovakia appeasement"),
    # --- 14 milestone ---
    ("The Japanese Imperial Navy struck Pearl Harbor on 7 December 1941, sinking four battleships and pulling the United States into the Second World War; Roosevelt called it a date which will live in infamy.", "milestone", "knowledge", False,
     [("Imperial Navy", "organization"), ("Pearl Harbor", "place"), ("7 December 1941", "date"), ("United States", "place"), ("Second World War", "event"), ("Roosevelt", "person")],
     [("Imperial Navy", "Pearl Harbor", "APPLIES_TO"), ("Pearl Harbor", "Second World War", "CAUSES")],
     "which 7 December 1941 naval strike pulled the United States into the Second World War",
     "pearl harbor 1941 imperial navy roosevelt infamy battleship"),
    # --- 15 milestone ---
    ("The Battle of Stalingrad ended on 2 February 1943 with Field Marshal Paulus surrendering the Sixth Army to the Red Army; the Wehrmacht never recovered the strategic initiative in the east after Midway and Stalingrad reversed both fronts the same winter.", "milestone", "knowledge", False,
     [("Battle of Stalingrad", "event"), ("Paulus", "person"), ("Sixth Army", "organization"), ("Red Army", "organization"), ("Wehrmacht", "organization"), ("2 February 1943", "date"), ("Midway", "event")],
     [("Paulus", "Sixth Army", "WORKS_AT"), ("Red Army", "Sixth Army", "REPLACES")],
     "which February 1943 surrender by Paulus ended the strategic initiative of the Wehrmacht in the east",
     "stalingrad 1943 paulus sixth army red army wehrmacht midway surrender"),
    # --- 17 architecture ---
    ("The D-Day landing on 6 June 1944 was organised into five Normandy beaches with dedicated landing forces per beach; the joint command structure combined naval bombardment, airborne drops inland, and armoured waves in a single layered assault against Nazi Germany.", "architecture", "knowledge", False,
     [("D-Day", "event"), ("6 June 1944", "date"), ("Normandy", "place"), ("airborne drops", "concept"), ("Nazi Germany", "place")],
     [("D-Day", "Normandy", "LOCATED_IN"), ("D-Day", "Nazi Germany", "APPLIES_TO"), ("airborne drops", "D-Day", "HAS_PART")],
     "how was the D-Day landing structured across five Normandy beaches with combined naval, airborne, and armoured forces",
     "d day 1944 normandy five beach airborne armoured structure"),
    # --- 18 reference ---
    ("Reference timeline for V-E Day: 8 May 1945 marked the unconditional surrender of Nazi Germany to the Allies; Hitler had killed himself in the Führerbunker eight days earlier as the Red Army closed on Berlin.", "reference", "knowledge", False,
     [("V-E Day", "event"), ("8 May 1945", "date"), ("Nazi Germany", "place"), ("Hitler", "person"), ("Führerbunker", "place"), ("Red Army", "organization"), ("Berlin", "place")],
     [("V-E Day", "Nazi Germany", "APPLIES_TO"), ("Red Army", "Berlin", "APPLIES_TO")],
     "which 8 May 1945 day marked Nazi Germany's unconditional surrender after Hitler's suicide",
     "ve day 1945 nazi germany surrender hitler fuhrerbunker berlin"),
    # --- 19 decision ---
    ("Truman authorised atomic bombs on Hiroshima on 6 August and Nagasaki on 9 August 1945; Japan announced surrender on 15 August and signed it aboard the USS Missouri on 2 September.", "decision", "knowledge", False,
     [("Truman", "person"), ("Hiroshima", "place"), ("Nagasaki", "place"), ("Japan", "place"), ("USS Missouri", "tool"), ("6 August", "date"), ("9 August 1945", "date")],
     [("Truman", "Hiroshima", "APPLIES_TO"), ("Truman", "Nagasaki", "APPLIES_TO")],
     "which two August 1945 atomic strikes authorised by Truman pushed Japan to surrender aboard the USS Missouri",
     "hiroshima nagasaki 1945 atomic bomb japan missouri truman surrender"),
    # --- 20 reference ---
    ("Reference entry for the Nuremberg trials: they opened in November 1945 before an international military tribunal; twelve defendants including Göring were sentenced to death, and the proceedings established crimes against humanity as a legal category.", "reference", "knowledge", False,
     [("Nuremberg trials", "event"), ("November 1945", "date"), ("Göring", "person"), ("crimes against humanity", "concept")],
     [("Nuremberg trials", "crimes against humanity", "PRODUCES")],
     "which November 1945 tribunal sentenced Göring to death and coined crimes against humanity as a legal category",
     "nuremberg 1945 tribunal goering crimes humanity international"),
    # --- 21 decision ---
    ("The Bretton Woods conference in July 1944 pegged currencies to a dollar-gold exchange system, founded the International Monetary Fund, and chartered the World Bank to rebuild post-war economies.", "decision", "knowledge", False,
     [("Bretton Woods", "event"), ("International Monetary Fund", "organization"), ("World Bank", "organization"), ("dollar-gold exchange", "concept"), ("July 1944", "date")],
     [("Bretton Woods", "International Monetary Fund", "PRODUCES"), ("Bretton Woods", "World Bank", "PRODUCES")],
     "which July 1944 conference pegged currencies to the dollar and founded the IMF and World Bank",
     "bretton woods 1944 imf world bank dollar gold exchange"),
    # --- 22 architecture ---
    ("The United Nations structure rests on a General Assembly of all members and a Security Council where five permanent members hold a veto; founded in San Francisco on 24 October 1945, it replaced the failed League of Nations.", "architecture", "knowledge", False,
     [("United Nations", "organization"), ("General Assembly", "organization"), ("Security Council", "organization"), ("San Francisco", "place"), ("24 October 1945", "date"), ("League of Nations", "organization")],
     [("United Nations", "League of Nations", "REPLACES"), ("Security Council", "United Nations", "HAS_PART"), ("General Assembly", "United Nations", "HAS_PART")],
     "how is the United Nations structured through General Assembly and Security Council and what did it replace",
     "united nations general assembly security council san francisco league"),
    # --- 23 milestone ---
    ("India gained independence from Britain at midnight on 15 August 1947; the partition drew a border through Punjab and Bengal that displaced roughly fourteen million people and cost a million lives in communal violence.", "milestone", "knowledge", False,
     [("India", "place"), ("Britain", "place"), ("15 August 1947", "date"), ("Punjab", "place"), ("Bengal", "place"), ("partition", "event")],
     [("India", "Britain", "REPLACES"), ("partition", "Punjab", "APPLIES_TO")],
     "which August 1947 independence and partition split Punjab and Bengal and displaced fourteen million people",
     "india partition 1947 britain punjab bengal independence violence"),
    # --- 24 architecture ---
    ("The Indian independence settlement split leadership three ways: Gandhi had led the non-violent movement, Nehru became the first prime minister of the new republic, and Jinnah became the first governor-general of a separate Muslim Pakistan.", "architecture", "knowledge", False,
     [("Gandhi", "person"), ("Nehru", "person"), ("Jinnah", "person"), ("Pakistan", "place"), ("India", "place")],
     [("Nehru", "India", "WORKS_AT"), ("Jinnah", "Pakistan", "WORKS_AT"), ("Gandhi", "India", "APPLIES_TO")],
     "how did the three-way leadership split between Gandhi, Nehru, and Jinnah shape the India-Pakistan settlement",
     "gandhi nehru jinnah india pakistan independence three way split"),
    # --- 25 decision ---
    ("Sukarno declared Indonesian independence on 17 August 1945; after a four-year colonial war the Dutch conceded sovereignty at the December 1949 Round Table Conference in The Hague.", "decision", "knowledge", False,
     [("Sukarno", "person"), ("Indonesia", "place"), ("Dutch", "organization"), ("Round Table Conference", "event"), ("The Hague", "place"), ("17 August 1945", "date")],
     [("Sukarno", "Indonesia", "WORKS_AT"), ("Round Table Conference", "Indonesia", "APPLIES_TO")],
     "which Sukarno declaration and which 1949 Hague conference transferred sovereignty from the Dutch to Indonesia",
     "sukarno indonesia 1945 dutch round table hague 1949 independence"),
    # --- 26 decision ---
    ("Ghana became the first sub-Saharan African colony to gain independence on 6 March 1957 under Kwame Nkrumah; he pressed a pan-African programme until a coup pushed him out in 1966.", "decision", "knowledge", False,
     [("Ghana", "place"), ("Kwame Nkrumah", "person"), ("pan-African", "concept"), ("6 March 1957", "date")],
     [("Kwame Nkrumah", "Ghana", "WORKS_AT"), ("Kwame Nkrumah", "pan-African", "SUPPORTS")],
     "which 1957 independence put Nkrumah in charge of Ghana and which 1966 coup pushed him out",
     "ghana 1957 nkrumah pan african coup 1966 sub saharan"),
    # --- 27 decision ---
    ("Algeria won independence from France on 5 July 1962 after the FLN fought an eight-year war that killed hundreds of thousands and pushed de Gaulle to negotiate the Évian Accords.", "decision", "knowledge", False,
     [("Algeria", "place"), ("France", "place"), ("FLN", "organization"), ("de Gaulle", "person"), ("Évian Accords", "event"), ("5 July 1962", "date")],
     [("FLN", "France", "CONTRADICTS"), ("Évian Accords", "Algeria", "APPLIES_TO")],
     "which July 1962 accord ended the eight-year FLN war and gave Algeria independence from France",
     "algeria 1962 fln france de gaulle evian accords independence"),
    # --- 28 problem ---
    ("Congo gained independence from Belgium on 30 June 1960 under Patrice Lumumba; he was deposed within months and murdered in January 1961 with Belgian and CIA complicity during the Katanga secession crisis.", "problem", "knowledge", False,
     [("Congo", "place"), ("Belgium", "place"), ("Patrice Lumumba", "person"), ("Katanga", "place"), ("CIA", "organization"), ("30 June 1960", "date")],
     [("Patrice Lumumba", "Congo", "WORKS_AT"), ("CIA", "Patrice Lumumba", "REPLACES")],
     "which 1960 Congo independence ended in Lumumba's murder with Belgian and CIA complicity",
     "congo 1960 lumumba belgium katanga cia murder january 1961"),
    # --- 29 architecture ---
    ("NATO was founded on 4 April 1949 with twelve member states including the United States, Britain, France, and Canada to guarantee collective defence against Soviet expansion in Europe.", "architecture", "knowledge", False,
     [("NATO", "organization"), ("4 April 1949", "date"), ("United States", "place"), ("Britain", "place"), ("France", "place"), ("Canada", "place"), ("Soviet", "place"), ("collective defence", "concept")],
     [("NATO", "Soviet", "CONTRADICTS"), ("NATO", "collective defence", "SUPPORTS")],
     "which April 1949 treaty organisation guaranteed collective defence against Soviet expansion with twelve members",
     "nato 1949 collective defence soviet europe united states britain"),
    # --- 30 architecture ---
    ("The Warsaw Pact was signed on 14 May 1955 by the Soviet Union and seven Eastern Bloc states as a direct counter to NATO after West Germany was admitted to the western alliance.", "architecture", "knowledge", False,
     [("Warsaw Pact", "organization"), ("14 May 1955", "date"), ("Soviet Union", "place"), ("Eastern Bloc", "concept"), ("NATO", "organization"), ("West Germany", "place")],
     [("Warsaw Pact", "NATO", "CONTRADICTS"), ("West Germany", "NATO", "APPLIES_TO")],
     "which May 1955 Soviet-led pact responded to West Germany joining NATO",
     "warsaw pact 1955 soviet eastern bloc nato west germany"),
    # --- 31 fact ---
    ("The Korean War ran from June 1950 to the armistice at Panmunjom in July 1953; the border settled near the 38th parallel where it stood at the start and no peace treaty was ever signed.", "fact", "knowledge", False,
     [("Korean War", "event"), ("Panmunjom", "place"), ("38th parallel", "place"), ("July 1953", "date")],
     [("Korean War", "Panmunjom", "APPLIES_TO"), ("Korean War", "38th parallel", "LOCATED_IN")],
     "which 1950 to 1953 war ended at Panmunjom with no peace treaty and the border back at the 38th parallel",
     "korean war 1950 1953 panmunjom 38th parallel armistice"),
    # --- 32 decision ---
    ("The Cuban Missile Crisis in October 1962 brought the United States and Soviet Union within days of nuclear war; Kennedy's naval quarantine forced Khrushchev to withdraw missiles from Cuba in exchange for a secret removal of US Jupiters from Turkey.", "decision", "knowledge", False,
     [("Cuban Missile Crisis", "event"), ("United States", "place"), ("Soviet Union", "place"), ("Kennedy", "person"), ("Khrushchev", "person"), ("Cuba", "place"), ("Jupiter", "tool"), ("Turkey", "place")],
     [("Kennedy", "Khrushchev", "CONTRADICTS"), ("Jupiter", "Turkey", "LOCATED_IN")],
     "which October 1962 quarantine by Kennedy traded Soviet missiles in Cuba for US Jupiters in Turkey",
     "cuban missile 1962 kennedy khrushchev cuba turkey jupiter quarantine"),
    # --- 33 architecture ---
    ("The Berlin Wall went up overnight on 13 August 1961 as a concrete-and-barbed-wire ring around West Berlin, with an inner death strip, watchtowers, and vehicle traps designed to stop the bleed of East Germany to the West.", "architecture", "knowledge", False,
     [("Berlin Wall", "event"), ("13 August 1961", "date"), ("East Germany", "place"), ("West Berlin", "place"), ("death strip", "concept")],
     [("Berlin Wall", "West Berlin", "LOCATED_IN"), ("death strip", "Berlin Wall", "HAS_PART")],
     "how was the Berlin Wall structured with death strip and watchtowers to stop East German emigration",
     "berlin wall 1961 east germany west berlin death strip watchtower"),
    # --- 34 decision ---
    ("The Suez Crisis in October 1956 saw Britain, France, and Israel invade Egypt after Nasser nationalised the Suez Canal; US pressure forced a humiliating withdrawal and marked the end of Britain as a first-rank imperial power.", "decision", "knowledge", False,
     [("Suez Crisis", "event"), ("Britain", "place"), ("France", "place"), ("Israel", "place"), ("Egypt", "place"), ("Nasser", "person"), ("Suez Canal", "place"), ("October 1956", "date")],
     [("Nasser", "Suez Canal", "APPLIES_TO"), ("Britain", "Egypt", "CONTRADICTS")],
     "which October 1956 crisis followed Nasser's canal nationalisation and ended British imperial power",
     "suez 1956 nasser canal britain france israel egypt withdrawal"),
    # --- 35 fact ---
    ("The Vietnam War escalated after the Gulf of Tonkin resolution in August 1964; US troop strength peaked at 543,000 in 1969 and the last Americans evacuated Saigon by helicopter from the embassy roof on 30 April 1975.", "fact", "knowledge", False,
     [("Vietnam War", "event"), ("Gulf of Tonkin", "place"), ("Saigon", "place"), ("30 April 1975", "date"), ("August 1964", "date")],
     [("Vietnam War", "Saigon", "APPLIES_TO"), ("Gulf of Tonkin", "Vietnam War", "CAUSES")],
     "which 1964 Gulf of Tonkin resolution began the American escalation that ended on the Saigon embassy roof in April 1975",
     "vietnam war tonkin 1964 saigon embassy 1975 helicopter evacuation"),
    # --- 36 problem ---
    ("Prague Spring in 1968 under Alexander Dubček tried to build socialism with a human face; Warsaw Pact tanks rolled into Czechoslovakia on 20 August and crushed the reform programme within a week.", "problem", "knowledge", False,
     [("Prague Spring", "event"), ("Alexander Dubček", "person"), ("Warsaw Pact", "organization"), ("Czechoslovakia", "place"), ("20 August", "date")],
     [("Alexander Dubček", "Prague Spring", "WORKS_AT"), ("Warsaw Pact", "Czechoslovakia", "APPLIES_TO")],
     "which 1968 Dubček reform programme was crushed when Warsaw Pact tanks rolled into Czechoslovakia",
     "prague spring 1968 dubcek warsaw pact czechoslovakia tank socialism"),
    # --- 38 decision ---
    ("The Shah of Iran fled on 16 January 1979 and Ayatollah Khomeini returned from Paris exile two weeks later to lead the Islamic Revolution; a referendum in April declared the Islamic Republic.", "decision", "knowledge", False,
     [("Shah of Iran", "person"), ("Ayatollah Khomeini", "person"), ("Paris", "place"), ("Islamic Revolution", "event"), ("Islamic Republic", "organization"), ("16 January 1979", "date")],
     [("Ayatollah Khomeini", "Shah of Iran", "REPLACES"), ("Ayatollah Khomeini", "Islamic Republic", "WORKS_AT")],
     "which January 1979 flight and Paris return replaced the Shah with Khomeini and founded the Islamic Republic",
     "shah iran 1979 khomeini paris islamic republic revolution"),
    # --- 39 fact ---
    ("Nelson Mandela was imprisoned on Robben Island in 1964 on Rivonia Trial sabotage charges; he served eighteen of his twenty-seven years there before his release by F. W. de Klerk in February 1990.", "fact", "knowledge", False,
     [("Nelson Mandela", "person"), ("Robben Island", "place"), ("Rivonia Trial", "event"), ("F. W. de Klerk", "person"), ("February 1990", "date")],
     [("Nelson Mandela", "Robben Island", "LOCATED_IN"), ("F. W. de Klerk", "Nelson Mandela", "CAUSES")],
     "which 1964 Rivonia conviction put Mandela on Robben Island and which 1990 de Klerk move freed him",
     "mandela robben island 1964 rivonia de klerk 1990 release"),
    # --- 40 architecture ---
    ("Solidarity grew as the first independent trade union in a Warsaw Pact country: founded at the Gdańsk shipyard in August 1980 under Lech Wałęsa, it pulled in ten million members across Polish workplaces before martial law drove it underground.", "architecture", "knowledge", False,
     [("Solidarity", "organization"), ("Gdańsk", "place"), ("Lech Wałęsa", "person"), ("Warsaw Pact", "organization"), ("Polish", "concept"), ("August 1980", "date")],
     [("Lech Wałęsa", "Solidarity", "WORKS_AT"), ("Solidarity", "Polish", "LOCATED_IN")],
     "how was Solidarity structured as a ten-million-member independent trade union in a Warsaw Pact country",
     "solidarity gdansk 1980 walesa warsaw pact polish ten million"),
    # --- 41 reference ---
    ("Reference entry for the fall of the Berlin Wall: the wall fell on the night of 9 November 1989 after an East German spokesman botched a press briefing; crowds flooded the checkpoints and East Germany effectively ceased to exist over the next eleven months.", "reference", "knowledge", False,
     [("Berlin Wall", "event"), ("9 November 1989", "date"), ("East Germany", "place")],
     [("Berlin Wall", "East Germany", "APPLIES_TO")],
     "which November 1989 press briefing slip triggered the fall of the Berlin Wall and the end of East Germany",
     "berlin wall 1989 east germany press briefing checkpoint"),
    # --- 42 reference ---
    ("Reference timeline for the USSR dissolution: the Soviet Union dissolved on 26 December 1991, Gorbachev had resigned the previous day, and the Belavezha Accords signed by Russia, Ukraine, and Belarus three weeks earlier had replaced the union with a loose Commonwealth of Independent States.", "reference", "knowledge", False,
     [("Soviet Union", "place"), ("26 December 1991", "date"), ("Gorbachev", "person"), ("Belavezha Accords", "event"), ("Russia", "place"), ("Ukraine", "place"), ("Belarus", "place"), ("Commonwealth of Independent States", "organization")],
     [("Belavezha Accords", "Soviet Union", "REPLACES"), ("Commonwealth of Independent States", "Soviet Union", "REPLACES")],
     "which December 1991 dissolution followed the Belavezha Accords and Gorbachev's resignation",
     "soviet union 1991 gorbachev belavezha russia ukraine belarus cis"),
    # --- 43 noise ---
    ("The archive reading room in the old library still requires white cotton gloves and a pencil, and the radiator under the west window rattles loud enough that researchers avoid the nearest desk.", "fact", "noise", True, [], [], None, None),
    # --- 44 problem ---
    ("The Rwanda genocide between April and July 1994 killed roughly 800,000 Tutsis and moderate Hutus in a hundred days; the UNAMIR force had been pulled down to a token strength and did not intervene.", "problem", "knowledge", False,
     [("Rwanda", "place"), ("Tutsi", "concept"), ("Hutu", "concept"), ("UNAMIR", "organization"), ("April", "date")],
     [("Hutu", "Tutsi", "CONTRADICTS"), ("UNAMIR", "Rwanda", "APPLIES_TO")],
     "which hundred-day 1994 genocide killed 800,000 Tutsis and moderate Hutus while UNAMIR stood down",
     "rwanda 1994 tutsi hutu genocide unamir hundred day"),
    # --- 45 decision ---
    ("The Dayton Accords in November 1995 ended the three-and-a-half-year Bosnian War; Milošević, Tuđman, and Izetbegović signed at Wright-Patterson Air Force Base in Ohio and partitioned Bosnia between a Federation and Republika Srpska.", "decision", "knowledge", False,
     [("Dayton Accords", "event"), ("Bosnian War", "event"), ("Milošević", "person"), ("Tuđman", "person"), ("Izetbegović", "person"), ("Wright-Patterson Air Force Base", "place"), ("Republika Srpska", "place"), ("November 1995", "date")],
     [("Dayton Accords", "Bosnian War", "FIXES"), ("Dayton Accords", "Republika Srpska", "PRODUCES")],
     "which November 1995 Ohio accords ended the Bosnian War and split Bosnia with Republika Srpska",
     "dayton 1995 bosnia milosevic tudjman izetbegovic wright patterson"),
    # --- 46 reference ---
    ("Reference entry for the Cold War: a forty-five-year stand-off from 1945 to 1991 between the United States and the Soviet Union fought through proxy wars, space race milestones, and nuclear deterrence, never through direct combat between the principals.", "reference", "knowledge", False,
     [("Cold War", "event"), ("United States", "place"), ("Soviet Union", "place"), ("proxy war", "concept"), ("space race", "concept")],
     [("United States", "Soviet Union", "CONTRADICTS"), ("proxy war", "Cold War", "APPLIES_TO")],
     "which forty-five-year stand-off pitted the United States against the Soviet Union through proxy wars and the space race",
     "cold war 1945 1991 united states soviet proxy space nuclear"),
    # --- 48 reference ---
    ("Reference entry for NATO enlargement: the founding twelve in 1949 grew by Greece and Turkey in 1952, West Germany in 1955, and Spain in 1982; eastward expansion into former Warsaw Pact states began with Poland, Hungary, and the Czech Republic in 1999.", "reference", "knowledge", False,
     [("NATO", "organization"), ("Greece", "place"), ("Turkey", "place"), ("West Germany", "place"), ("Spain", "place"), ("Poland", "place"), ("Hungary", "place"), ("Czech Republic", "place")],
     [("Greece", "NATO", "APPLIES_TO"), ("Poland", "NATO", "APPLIES_TO"), ("Hungary", "NATO", "APPLIES_TO")],
     "which NATO enlargement waves added members from 1952 to 1999 from Greece through to the Czech Republic",
     "nato enlargement greece turkey west germany spain poland hungary czech"),
    # --- 49 architecture ---
    ("Decolonisation followed a regional clock: Asia broke from European empires in the late 1940s, Africa from the late 1950s into the 1960s, and the Portuguese holdouts of Angola and Mozambique finally gained independence in 1975.", "architecture", "knowledge", False,
     [("Decolonisation", "concept"), ("Asia", "place"), ("Africa", "place"), ("Angola", "place"), ("Mozambique", "place"), ("Portuguese", "organization"), ("1975", "date")],
     [("Angola", "Portuguese", "REPLACES"), ("Mozambique", "Portuguese", "REPLACES"), ("Decolonisation", "Asia", "APPLIES_TO")],
     "how did the regional clock of decolonisation move from Asia in the 1940s through Africa and to Angola and Mozambique in 1975",
     "decolonisation 1945 1975 asia africa angola mozambique portuguese"),
    # --- 50 architecture ---
    ("The post-crisis nuclear risk-reduction layer built after the Cuban Missile Crisis rested on two pieces: the Moscow-Washington hotline installed in June 1963 as a direct voice link, and the Partial Test Ban Treaty signed that August barring atmospheric, underwater, and outer-space nuclear tests.", "architecture", "knowledge", False,
     [("Cuban Missile Crisis", "event"), ("Moscow-Washington hotline", "tool"), ("Partial Test Ban Treaty", "event"), ("June 1963", "date")],
     [("Cuban Missile Crisis", "Moscow-Washington hotline", "CAUSES"), ("Cuban Missile Crisis", "Partial Test Ban Treaty", "CAUSES")],
     "which two-piece nuclear risk-reduction layer came out of the Cuban Missile Crisis in 1963",
     "hotline 1963 partial test ban treaty cuban missile architecture"),
    # --- 51 preference ---
    ("Preference note from the 20th-century syllabus committee: teach the First World War through the July Crisis and trench letters rather than a grand-strategy map lecture, since primary sources land harder with undergraduates.", "preference", "knowledge", False,
     [("First World War", "event"), ("July Crisis", "event"), ("trench letters", "concept")],
     [("trench letters", "First World War", "APPLIES_TO")],
     "which teaching approach does the syllabus committee prefer for undergraduates studying the First World War",
     "syllabus preference first world war july crisis trench letter primary"),
    # --- 52 preference ---
    ("Preference note for the decolonisation unit: centre the Algerian War through FLN and French settler perspectives in parallel, rather than presenting either side as the default voice of the conflict.", "preference", "knowledge", False,
     [("Algerian War", "event"), ("FLN", "organization"), ("French settler", "concept")],
     [("FLN", "Algerian War", "APPLIES_TO"), ("French settler", "Algerian War", "APPLIES_TO")],
     "which paired-perspective preference does the decolonisation unit apply to teaching the Algerian War",
     "preference algerian war fln french settler parallel perspective"),
    # --- 53 preference ---
    ("Preference note for the Cold War unit: teach the Cuban Missile Crisis through released ExComm tapes and Soviet Presidium minutes rather than retrospective memoirs, since the real-time anxiety of the thirteen days only comes through in the primary documents.", "preference", "knowledge", False,
     [("Cold War", "event"), ("Cuban Missile Crisis", "event"), ("ExComm", "organization"), ("Soviet Presidium", "organization")],
     [("ExComm", "Cuban Missile Crisis", "APPLIES_TO"), ("Soviet Presidium", "Cuban Missile Crisis", "APPLIES_TO")],
     "which primary-source preference does the syllabus apply when teaching the Cuban Missile Crisis",
     "preference cold war excomm presidium tape minutes thirteen days"),
    # --- 54 preference ---
    ("Preference note for the WWII unit: always pair Pacific and European theatre chronologies side by side rather than teaching one before the other, since students otherwise miss that Stalingrad and Midway ran concurrently.", "preference", "knowledge", False,
     [("WWII", "event"), ("Pacific", "place"), ("European theatre", "place"), ("Stalingrad", "place"), ("Midway", "place")],
     [("Stalingrad", "European theatre", "LOCATED_IN"), ("Midway", "Pacific", "LOCATED_IN")],
     "which pairing preference does the WWII unit apply between Pacific and European theatre chronologies",
     "preference wwii pacific european theatre parallel stalingrad midway"),
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
