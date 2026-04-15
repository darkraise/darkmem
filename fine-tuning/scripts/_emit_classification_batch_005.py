"""One-off emitter for classification top-up batch-005 — 50 contrastive reference/fact pairs (100 rows).

Historical and cultural slice: each pair contains one `reference` row citing a real
historical primary source or named scholarly work, paired with a `fact` row asserting
the same historical fact without the citation. Covers antiquity, medieval, early-modern,
modern, 20th-century, non-Western, cultural history, and archaeology.

Writes to data/v2/classification/batch_005.tmp.jsonl with ids class-00401..00500 and
pair_ids cls-pair-00201..00250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_005.tmp.jsonl"
ID_OFFSET = 400
PAIR_OFFSET = 200

# Each tuple: (reference_text_with_citation, fact_text_without_citation, domain)
PAIRS: list[tuple[str, str, str]] = [
    # --- 1 (antiquity — Tacitus on the Great Fire of Rome)
    ("According to Tacitus in the Annals Book 15 chapters 38 to 44, Emperor Nero blamed the Christians of Rome for the fire that broke out in July of 64 CE and subjected them to elaborate public executions in the imperial gardens.",
     "After the Great Fire of Rome broke out in July 64 CE, Emperor Nero blamed the city's Christian population and had many of them executed in brutal public spectacles held in the imperial gardens.",
     "knowledge"),
    # --- 2 (antiquity — Thucydides on the plague of Athens)
    ("Thucydides, in History of the Peloponnesian War Book 2 chapter 47, records that a devastating pestilence struck Athens in the second year of the war, beginning in Piraeus and sweeping through the overcrowded city during the summer of 430 BCE.",
     "A devastating plague struck Athens in 430 BCE during the second year of the Peloponnesian War, first appearing in the port of Piraeus before sweeping through the overcrowded city.",
     "knowledge"),
    # --- 3 (antiquity — Herodotus on Thermopylae)
    ("Herodotus records in Histories Book 7 chapter 228 that King Leonidas and three hundred Spartans died holding the pass at Thermopylae against Xerxes' invading Persian army in 480 BCE.",
     "In 480 BCE King Leonidas led three hundred Spartans to their deaths defending the narrow pass at Thermopylae against the invading Persian army of Xerxes.",
     "knowledge"),
    # --- 4 (antiquity — Plutarch on Caesar's assassination)
    ("Plutarch's Life of Caesar chapter 66 narrates that on the Ides of March in 44 BCE a conspiracy of senators led by Brutus and Cassius stabbed Julius Caesar to death at the foot of Pompey's statue in the Curia.",
     "On the Ides of March in 44 BCE a conspiracy of Roman senators led by Brutus and Cassius assassinated Julius Caesar at the foot of Pompey's statue inside the Curia.",
     "knowledge"),
    # --- 5 (antiquity — Suetonius on Caligula)
    ("Suetonius in The Twelve Caesars, Life of Caligula chapter 55, reports that the emperor Caligula lavished such affection on his racehorse Incitatus that he gave the animal a marble stable, purple blankets, and reportedly intended to appoint it to the consulship.",
     "The emperor Caligula was said to have given his racehorse Incitatus a marble stable with purple blankets and to have planned to appoint the animal to the Roman consulship.",
     "knowledge"),
    # --- 6 (antiquity — Josephus on the fall of Jerusalem)
    ("Flavius Josephus records in The Jewish War Book 6 that Roman legions under Titus breached the walls of Jerusalem and destroyed the Second Temple during the siege of 70 CE.",
     "In 70 CE Roman legions commanded by Titus breached the walls of Jerusalem and destroyed the Second Temple during the final siege of the city.",
     "knowledge"),
    # --- 7 (antiquity — Livy on Hannibal crossing the Alps)
    ("Livy's Ab Urbe Condita Book 21 recounts that in the autumn of 218 BCE Hannibal led a Carthaginian army together with war elephants over the Alps into northern Italy, opening the Second Punic War on Roman soil.",
     "In the autumn of 218 BCE Hannibal led a Carthaginian army and his war elephants across the Alps into northern Italy to open the Second Punic War on Roman territory.",
     "knowledge"),
    # --- 8 (medieval — Bede on the Synod of Whitby)
    ("Bede's Ecclesiastical History of the English People Book 3 chapter 25 describes the Synod of Whitby in 664, where King Oswiu of Northumbria ruled in favour of Roman practice for calculating the date of Easter over the Ionan Celtic custom.",
     "At the Synod of Whitby in 664 King Oswiu of Northumbria decided in favour of the Roman method for calculating the date of Easter over the Ionan Celtic custom.",
     "knowledge"),
    # --- 9 (medieval — Anglo-Saxon Chronicle on the Viking raid of Lindisfarne)
    ("The Anglo-Saxon Chronicle entry for the year 793 reports that heathen men miserably destroyed God's church on the island of Lindisfarne through rapine and slaughter on the eighth of June.",
     "On 8 June 793 Viking raiders sacked the monastery on the island of Lindisfarne, an event widely taken to mark the opening of the Viking Age in the British Isles.",
     "knowledge"),
    # --- 10 (medieval — Einhard on Charlemagne's coronation)
    ("Einhard's Vita Karoli Magni chapter 28 describes how Pope Leo III placed a crown on the head of Charlemagne in Saint Peter's Basilica on Christmas Day of the year 800, acclaiming him emperor of the Romans.",
     "On Christmas Day in the year 800 Pope Leo III crowned Charlemagne emperor of the Romans in Saint Peter's Basilica in Rome.",
     "knowledge"),
    # --- 11 (medieval — William of Malmesbury on Hastings)
    ("William of Malmesbury in Gesta Regum Anglorum Book 3 describes how William the Conqueror defeated King Harold Godwinson at the Battle of Hastings on 14 October 1066, with Harold slain as the English line broke at dusk.",
     "At the Battle of Hastings on 14 October 1066 William the Conqueror defeated King Harold Godwinson, who was killed as the English shield wall collapsed at dusk.",
     "knowledge"),
    # --- 12 (medieval — Marco Polo on Kublai Khan)
    ("Marco Polo's The Travels Book 2 describes the splendour of Kublai Khan's summer capital at Xanadu, where the Great Khan maintained a pleasure palace of marble and gold surrounded by a walled hunting park.",
     "Kublai Khan maintained a summer capital at Xanadu containing a marble and gold pleasure palace set within a walled hunting park.",
     "knowledge"),
    # --- 13 (medieval — Ibn Battuta on Mali)
    ("Ibn Battuta's Rihla recounts his visit to the Mali Empire in 1352 and 1353, where he described the court of Mansa Sulayman and praised the safety of travel and the strict administration of justice in the realm.",
     "Between 1352 and 1353 the traveller Ibn Battuta visited the Mali Empire and remarked on the safety of its roads and the strict administration of justice under Mansa Sulayman.",
     "knowledge"),
    # --- 14 (medieval — Jean Froissart on Crecy)
    ("Jean Froissart's Chronicles Book 1 describes how English longbowmen under King Edward III cut down the flower of French chivalry at the Battle of Crecy on 26 August 1346.",
     "At the Battle of Crecy on 26 August 1346 English longbowmen serving King Edward III decimated the French mounted knights during the Hundred Years War.",
     "knowledge"),
    # --- 15 (medieval — Magna Carta)
    ("The text of Magna Carta as sealed at Runnymede on 15 June 1215 constrains King John in clause 39 to judge no free man except by the lawful judgement of his peers or by the law of the land.",
     "On 15 June 1215 at Runnymede King John sealed Magna Carta, whose clause 39 barred the king from judging any free man except by the lawful judgement of his peers or by the law of the land.",
     "knowledge"),
    # --- 16 (early-modern — Bartolome de las Casas on the Americas)
    ("Bartolome de las Casas in A Short Account of the Destruction of the Indies, published in 1552, catalogued the massacres, enslavement, and forced labour inflicted by Spanish conquerors on the indigenous peoples of Hispaniola and Cuba.",
     "Spanish colonists during the early sixteenth century inflicted massacres, enslavement, and forced labour on the indigenous peoples of Hispaniola and Cuba during the conquest of the Caribbean.",
     "knowledge"),
    # --- 17 (early-modern — Bernal Diaz on Tenochtitlan)
    ("Bernal Diaz del Castillo in The True History of the Conquest of New Spain chapter 87 recounts the awed first sight of Tenochtitlan in November 1519, with its causeways and lake city appearing to the Spaniards like an enchantment from the tale of Amadis.",
     "In November 1519 the Spanish expedition under Hernan Cortes first glimpsed the Aztec capital Tenochtitlan rising from Lake Texcoco with its long stone causeways.",
     "knowledge"),
    # --- 18 (early-modern — Samuel Pepys on the Great Fire of London)
    ("Samuel Pepys' diary entry for 2 September 1666 records that a fire beginning in a baker's shop on Pudding Lane spread rapidly through the timber houses of the City of London while the Lord Mayor dithered.",
     "On 2 September 1666 the Great Fire of London broke out in a baker's shop on Pudding Lane and spread rapidly through the timber buildings of the City.",
     "knowledge"),
    # --- 19 (early-modern — Galileo's Dialogue)
    ("Galileo Galilei's Dialogue Concerning the Two Chief World Systems, published in Florence in 1632, presents Salviati, Sagredo, and Simplicio arguing over three days on the merits of the Ptolemaic and Copernican cosmologies.",
     "Galileo Galilei published the Dialogue Concerning the Two Chief World Systems in Florence in 1632, staging a three-day debate between defenders of the Ptolemaic and Copernican cosmologies.",
     "knowledge"),
    # --- 20 (early-modern — Hobbes' Leviathan)
    ("Thomas Hobbes in Leviathan chapter 13, first published in 1651, argues that life outside political society is solitary, poor, nasty, brutish, and short.",
     "Thomas Hobbes argued in 1651 that human life outside organised political society would be solitary, poor, nasty, brutish, and short.",
     "knowledge"),
    # --- 21 (early-modern — Locke's Two Treatises)
    ("John Locke in the Second Treatise of Government chapter 5, published in 1689, argues that property originates in the labour that a person mixes with previously common resources.",
     "John Locke argued in 1689 that private property originates when a person mixes their own labour with previously common resources.",
     "knowledge"),
    # --- 22 (early-modern — Gibbon on the fall of Rome)
    ("Edward Gibbon in The History of the Decline and Fall of the Roman Empire chapter 38, published between 1776 and 1789, attributes the long decline of Rome to the triumph of barbarism and religion.",
     "Edward Gibbon famously attributed the long decline of Rome to what he called the triumph of barbarism and religion.",
     "knowledge"),
    # --- 23 (modern — Thomas Paine's Common Sense)
    ("Thomas Paine's pamphlet Common Sense, published anonymously in Philadelphia in January 1776, argued that hereditary monarchy was an absurdity and that the American colonies should declare independence from Great Britain.",
     "In January 1776 Thomas Paine anonymously published a pamphlet in Philadelphia arguing against hereditary monarchy and for American independence from Great Britain.",
     "knowledge"),
    # --- 24 (modern — de Tocqueville on America)
    ("Alexis de Tocqueville in Democracy in America Volume 1, published in 1835, observes that the equality of social conditions is the generative fact from which all the peculiarities of American political life proceed.",
     "Alexis de Tocqueville argued in 1835 that the equality of social conditions was the foundational feature from which the peculiarities of American political life flowed.",
     "knowledge"),
    # --- 25 (modern — Marx and Engels' Manifesto)
    ("Karl Marx and Friedrich Engels in The Communist Manifesto, first printed in London in February 1848, opened with the declaration that a spectre was haunting Europe, namely the spectre of communism.",
     "Karl Marx and Friedrich Engels published The Communist Manifesto in London in February 1848, famously opening with the image of communism as a spectre haunting Europe.",
     "knowledge"),
    # --- 26 (modern — Darwin's Origin of Species)
    ("Charles Darwin's On the Origin of Species, published by John Murray on 24 November 1859, set out a theory of descent with modification by means of natural selection operating on heritable variation.",
     "Charles Darwin's On the Origin of Species, released on 24 November 1859, presented the theory of descent with modification through natural selection acting on heritable variation.",
     "knowledge"),
    # --- 27 (modern — Frederick Douglass)
    ("Frederick Douglass' Narrative of the Life of Frederick Douglass, an American Slave, published in Boston in 1845, recounts his birth into slavery on a Maryland plantation and his eventual escape north in 1838.",
     "Frederick Douglass was born into slavery on a Maryland plantation and escaped north in 1838 before becoming a leading abolitionist orator and writer.",
     "knowledge"),
    # --- 28 (modern — Lincoln's Gettysburg Address)
    ("The text of Abraham Lincoln's Gettysburg Address as delivered on 19 November 1863 at the dedication of the Soldiers' National Cemetery dedicates the nation to the unfinished work of ensuring that government of the people, by the people, and for the people shall not perish from the earth.",
     "On 19 November 1863 Abraham Lincoln delivered the Gettysburg Address at the dedication of the Soldiers' National Cemetery, closing with a pledge that government of the people, by the people, and for the people shall not perish from the earth.",
     "knowledge"),
    # --- 29 (modern — Engels on the English working class)
    ("Friedrich Engels in The Condition of the Working Class in England in 1844, published in German in Leipzig in 1845, catalogued the slums, disease, and child labour produced by the industrial economy of Manchester.",
     "Friedrich Engels in 1845 catalogued the slums, disease, and child labour produced by the industrial economy of Manchester in the early years of the factory system.",
     "knowledge"),
    # --- 30 (20C — Hobsbawm on the short twentieth century)
    ("Eric Hobsbawm in Age of Extremes: The Short Twentieth Century 1914-1991, published in 1994, argued that the period between the outbreak of the First World War and the dissolution of the Soviet Union formed a coherent historical epoch.",
     "The historian Eric Hobsbawm argued that the years from the outbreak of the First World War in 1914 to the dissolution of the Soviet Union in 1991 constituted a coherent short twentieth century.",
     "knowledge"),
    # --- 31 (20C — Churchill's history)
    ("Winston Churchill in The Second World War Volume 1 chapter 19 describes the policy of appeasement pursued by Neville Chamberlain at the Munich Conference of September 1938, which ceded the Sudetenland to Nazi Germany without Czech consent.",
     "At the Munich Conference of September 1938 Neville Chamberlain pursued a policy of appeasement that ceded the Czechoslovak Sudetenland to Nazi Germany without Czech consent.",
     "knowledge"),
    # --- 32 (20C — Shirer on the Third Reich)
    ("William Shirer in The Rise and Fall of the Third Reich, published in 1960, recounts how the Reichstag fire on the night of 27 February 1933 was used by the Nazi leadership to justify emergency decrees suspending German civil liberties.",
     "The Reichstag fire on the night of 27 February 1933 was used by the Nazi leadership as pretext for emergency decrees that suspended German civil liberties.",
     "knowledge"),
    # --- 33 (20C — Primo Levi on Auschwitz)
    ("Primo Levi in If This Is a Man, first published in Italian as Se questo e un uomo in 1947, records his deportation to the Auschwitz Monowitz labour camp in February 1944 and his survival until liberation by Soviet forces in January 1945.",
     "The chemist Primo Levi was deported to the Auschwitz Monowitz labour camp in February 1944 and survived until the camp's liberation by Soviet forces in January 1945.",
     "knowledge"),
    # --- 34 (20C — Kennan's Long Telegram)
    ("George Kennan's Long Telegram, sent from the United States embassy in Moscow on 22 February 1946, argued that Soviet conduct was driven by a traditional Russian insecurity overlaid with Marxist ideology and recommended a policy of long-term patient containment.",
     "On 22 February 1946 the American diplomat George Kennan argued from Moscow that Soviet conduct was driven by traditional Russian insecurity and Marxist ideology, and he proposed a policy of long-term containment.",
     "knowledge"),
    # --- 35 (20C — Taylor on the origins of WW2)
    ("A. J. P. Taylor in The Origins of the Second World War, published in 1961, provocatively argued that Hitler was in many respects an ordinary opportunist German statesman rather than a uniquely demonic planner of general war.",
     "The historian A. J. P. Taylor provocatively argued in 1961 that Adolf Hitler behaved in many respects as an opportunistic German statesman rather than as a uniquely premeditated planner of general war.",
     "knowledge"),
    # --- 36 (20C — Kolko on Vietnam)
    ("Gabriel Kolko in Anatomy of a War: Vietnam, the United States, and the Modern Historical Experience, published in 1985, argued that American intervention in Vietnam grew out of a broader Cold War strategy of managing Third World nationalism.",
     "The historian Gabriel Kolko argued that American intervention in Vietnam grew out of a broader Cold War strategy aimed at managing Third World nationalism.",
     "knowledge"),
    # --- 37 (non-Western — Ibn Khaldun's Muqaddimah)
    ("Ibn Khaldun in the Muqaddimah, completed in 1377, develops the concept of asabiyyah or group solidarity as the engine by which rural tribal coalitions conquer sedentary dynasties and in turn decline after three generations.",
     "The fourteenth-century historian Ibn Khaldun developed the concept of asabiyyah, a form of group solidarity by which rural tribal coalitions conquered settled dynasties before themselves declining after about three generations.",
     "knowledge"),
    # --- 38 (non-Western — Sima Qian's Shiji)
    ("Sima Qian in the Shiji or Records of the Grand Historian, completed around 94 BCE, narrates the unification of China under the First Emperor of Qin in 221 BCE and the standardisation of script, currency, and axle widths.",
     "The First Emperor of Qin unified China in 221 BCE and ordered the standardisation of script, currency, and cart axle widths across his new empire.",
     "knowledge"),
    # --- 39 (non-Western — Nihon Shoki on Japanese origins)
    ("The Nihon Shoki, completed in 720 CE, records the traditional date of 660 BCE for the accession of the legendary emperor Jimmu as the first sovereign of Yamato Japan.",
     "Japanese imperial tradition, as preserved in eighth-century chronicles, assigned the year 660 BCE to the accession of the legendary emperor Jimmu as first sovereign of Yamato.",
     "knowledge"),
    # --- 40 (non-Western — Wang Gungwu on overseas Chinese)
    ("Wang Gungwu in The Chinese Overseas: From Earthbound China to the Quest for Autonomy, published in 2000, traces the long history of Chinese migration to Southeast Asia from the maritime networks of the Ming dynasty through the coolie trade of the nineteenth century.",
     "Chinese migration to Southeast Asia stretches from the maritime trading networks of the Ming dynasty through the nineteenth-century coolie trade to the modern diaspora communities of the region.",
     "knowledge"),
    # --- 41 (cultural — Burckhardt on the Renaissance)
    ("Jacob Burckhardt in The Civilization of the Renaissance in Italy, published in Basel in 1860, argued that fifteenth-century Italy was the birthplace of the modern conception of the individual as distinct from the corporate and religious identities of medieval Europe.",
     "The Swiss historian Jacob Burckhardt argued in 1860 that fifteenth-century Italy gave birth to the modern conception of the individual distinct from medieval corporate and religious identities.",
     "knowledge"),
    # --- 42 (cultural — Huizinga's Waning of the Middle Ages)
    ("Johan Huizinga in The Autumn of the Middle Ages, first published in Dutch in 1919 as Herfsttij der Middeleeuwen, portrayed fourteenth and fifteenth-century Burgundy and France as an overripe culture preoccupied with death, chivalric ritual, and spectacle.",
     "The historian Johan Huizinga portrayed fourteenth and fifteenth-century Burgundy and France as an overripe culture preoccupied with death, chivalric ritual, and elaborate public spectacle.",
     "knowledge"),
    # --- 43 (cultural — Thompson on the English working class)
    ("E. P. Thompson in The Making of the English Working Class, published in 1963, argued that the English working class was not passively produced by industrialisation but actively made itself through political struggle between 1780 and 1832.",
     "The historian E. P. Thompson argued that the English working class actively made itself through political struggle between roughly 1780 and 1832 rather than being passively produced by industrialisation.",
     "knowledge"),
    # --- 44 (cultural — Said's Orientalism)
    ("Edward Said in Orientalism, published in 1978, argued that European scholarship about the Middle East from the late eighteenth century onward constructed the Orient as the West's civilisational opposite in order to legitimise imperial rule.",
     "Edward Said argued in 1978 that European scholarship about the Middle East from the late eighteenth century onward constructed the Orient as a civilisational opposite of the West in ways that legitimised imperial rule.",
     "knowledge"),
    # --- 45 (cultural — Braudel's Mediterranean)
    ("Fernand Braudel in The Mediterranean and the Mediterranean World in the Age of Philip II, published in French in 1949, divided historical time into three layers: the longue duree of geography, the medium-term rhythms of social and economic structure, and the short-term events of political history.",
     "Fernand Braudel's 1949 study of the sixteenth-century Mediterranean introduced a three-layered conception of historical time that distinguished geographical longue duree, medium-term socioeconomic rhythms, and short-term political events.",
     "knowledge"),
    # --- 46 (archaeology — Woolley on Ur)
    ("Leonard Woolley's Ur Excavations Volume 2: The Royal Cemetery, published in 1934, documents sixteen richly furnished royal tombs at Ur dating to around 2600 BCE, including that of Queen Puabi with her gold headdress and accompanying retainers.",
     "Excavations at Ur uncovered sixteen richly furnished royal tombs dating to around 2600 BCE, among them the burial of Queen Puabi with her gold headdress and the remains of accompanying retainers.",
     "knowledge"),
    # --- 47 (archaeology — Howard Carter's Tutankhamun)
    ("Howard Carter in The Tomb of Tutankhamen Volume 1, published in 1923, describes opening the sealed door of KV62 in the Valley of the Kings on 26 November 1922 and glimpsing wonderful things by the light of a candle.",
     "On 26 November 1922 the archaeologist Howard Carter opened the sealed door of tomb KV62 in the Valley of the Kings and famously reported seeing wonderful things in the antechamber of Tutankhamun.",
     "knowledge"),
    # --- 48 (archaeology — Schliemann at Troy)
    ("Heinrich Schliemann in Troy and Its Remains, published in 1875, reports his discovery of a hoard of gold jewellery at the site of Hisarlik in 1873 which he identified, incorrectly, with the treasure of King Priam of Homeric Troy.",
     "In 1873 Heinrich Schliemann uncovered a hoard of gold jewellery at the site of Hisarlik and mistakenly identified it with the treasure of King Priam of Homeric Troy.",
     "knowledge"),
    # --- 49 (archaeology — Rosetta Stone decipherment)
    ("Jean-Francois Champollion announced in his Lettre a M. Dacier of September 1822 that the hieroglyphic, demotic, and Greek registers of the Rosetta Stone could be decoded through phonetic readings of royal cartouches such as those of Ptolemy and Cleopatra.",
     "In September 1822 the French scholar Jean-Francois Champollion announced that Egyptian hieroglyphs could be deciphered through phonetic readings of royal cartouches such as those of Ptolemy and Cleopatra on the Rosetta Stone.",
     "knowledge"),
    # --- 50 (archaeology — Mary Leakey at Laetoli)
    ("Mary Leakey in a 1979 article in National Geographic Magazine reported the discovery of a 27 metre trail of hominin footprints preserved in volcanic ash at Laetoli in Tanzania, dated to approximately 3.6 million years ago.",
     "In 1979 Mary Leakey announced the discovery at Laetoli in Tanzania of a 27 metre trail of hominin footprints preserved in volcanic ash dated to approximately 3.6 million years ago.",
     "knowledge"),
]


def emit() -> int:
    assert len(PAIRS) == 50, f"expected 50 pairs, got {len(PAIRS)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, fact_text, domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_row = {
                "id": f"class-{ID_OFFSET + (2 * i - 1):05d}",
                "domain": domain,
                "text": ref_text,
                "memory_type": "reference",
                "pair_id": pair_id,
            }
            fact_row = {
                "id": f"class-{ID_OFFSET + (2 * i):05d}",
                "domain": domain,
                "text": fact_text,
                "memory_type": "fact",
                "pair_id": pair_id,
            }
            f.write(json.dumps(ref_row, ensure_ascii=False) + "\n")
            f.write(json.dumps(fact_row, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
