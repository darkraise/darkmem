"""One-off emitter for shared-base batch-266 — knowledge domain (art history: Renaissance through contemporary).

Writes 50 rows to data/v2/shared/batch_266.tmp.jsonl with ids shared-13251..13300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_266.tmp.jsonl"
ID_OFFSET = 13250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Giotto's Scrovegni Chapel fresco cycle in Padua reset the Western pictorial tradition by giving figures tangible weight and an interior life that the flat Byzantine icon style never attempted.", "decision", "knowledge", False,
     [("Giotto", "person"), ("Scrovegni Chapel", "place"), ("Padua", "place"), ("Byzantine", "concept")],
     [("Scrovegni Chapel", "Giotto", "AUTHORED_BY"), ("Scrovegni Chapel", "Padua", "LOCATED_IN")],
     "which fresco cycle by Giotto in Padua broke with the flat Byzantine icon tradition",
     "giotto scrovegni chapel padua fresco byzantine naturalism weight"),
    # --- 2 ---
    ("Masaccio's Brancacci Chapel panels introduced single-point perspective and cast shadow to Florentine painting, and later Renaissance masters treated them as required study on their way through the city.", "fact", "knowledge", False,
     [("Masaccio", "person"), ("Brancacci Chapel", "place"), ("single-point perspective", "concept"), ("Florentine", "concept")],
     [("Masaccio", "single-point perspective", "USES"), ("Brancacci Chapel", "Masaccio", "AUTHORED_BY")],
     "which Florentine chapel cycle taught later Renaissance painters linear perspective and cast shadow",
     "masaccio brancacci perspective shadow florence renaissance study"),
    # --- 3 ---
    ("Brunelleschi won the 1418 competition for the Duomo of Florence with a double-shell dome design that used a herringbone brick pattern to rise without conventional wooden centring.", "milestone", "knowledge", False,
     [("Brunelleschi", "person"), ("Duomo", "place"), ("Florence", "place"), ("double-shell dome", "concept"), ("herringbone", "pattern")],
     [("Duomo", "Brunelleschi", "AUTHORED_BY"), ("Duomo", "Florence", "LOCATED_IN"), ("Duomo", "herringbone", "USES")],
     "which engineering trick let Brunelleschi raise the Florence cathedral dome without wooden centring",
     "brunelleschi duomo florence double shell herringbone dome 1418"),
    # --- 4 ---
    ("Donatello's bronze David, cast in the 1440s for the Medici courtyard, was the first free-standing nude male bronze since antiquity and reintroduced classical contrapposto to Italian sculpture.", "decision", "knowledge", False,
     [("Donatello", "person"), ("David", "publication"), ("Medici", "person"), ("contrapposto", "concept")],
     [("David", "Donatello", "AUTHORED_BY"), ("Donatello", "contrapposto", "USES")],
     "which Donatello bronze brought back the free-standing classical nude for the Medici",
     "donatello david medici bronze nude contrapposto 1440 antiquity"),
    # --- 5 ---
    ("Botticelli's Primavera, painted around 1482 for a Medici cousin, encodes a Neoplatonic allegory of Venus and the Graces that circulated in Ficino's philosophical circle.", "fact", "knowledge", False,  # keep fact
     [("Botticelli", "person"), ("Primavera", "publication"), ("Venus", "concept"), ("Ficino", "person"), ("Neoplatonic", "concept")],
     [("Primavera", "Botticelli", "AUTHORED_BY"), ("Primavera", "Neoplatonic", "RELATED_TO")],
     "which Medici-commissioned Botticelli panel encodes Ficino's Neoplatonic Venus allegory",
     "botticelli primavera medici venus ficino neoplatonic allegory 1482"),
    # --- 6 ---
    ("Leonardo da Vinci painted the Last Supper in oil and tempera directly onto a dry wall at Santa Maria delle Grazie, and the experimental technique began flaking within his own lifetime.", "problem", "knowledge", False,
     [("Leonardo da Vinci", "person"), ("Last Supper", "publication"), ("Santa Maria delle Grazie", "place"), ("oil", "concept"), ("tempera", "concept")],
     [("Last Supper", "Leonardo da Vinci", "AUTHORED_BY"), ("Last Supper", "Santa Maria delle Grazie", "LOCATED_IN")],
     "why did Leonardo's Last Supper start deteriorating in his own lifetime",
     "leonardo last supper santa maria grazie oil tempera dry wall flake"),
    # --- 7 ---
    ("The Mona Lisa sits in the Louvre behind bulletproof glass at climate-controlled humidity; the curators cite the poplar panel's movement as the primary conservation risk rather than the paint layer itself.", "architecture", "knowledge", False,
     [("Mona Lisa", "publication"), ("Louvre", "place"), ("poplar panel", "concept"), ("humidity", "concept")],
     [("Mona Lisa", "Louvre", "LOCATED_IN")],
     "which physical property drives Louvre conservation rules for the Mona Lisa",
     "mona lisa louvre poplar panel humidity glass climate conservation"),
    # --- 8 ---
    ("Leonardo's Vitruvian Man drawing synthesises Vitruvius's human-in-a-circle-and-square proportion scheme from De Architectura with Leonardo's own cadaver-based anatomy study.", "architecture", "knowledge", False,
     [("Vitruvian Man", "publication"), ("Vitruvius", "person"), ("Leonardo", "person"), ("De Architectura", "publication"), ("anatomy", "concept")],
     [("Vitruvian Man", "Leonardo", "AUTHORED_BY"), ("Vitruvian Man", "De Architectura", "BUILDS_ON"), ("De Architectura", "Vitruvius", "AUTHORED_BY")],
     "which ancient treatise on proportion did Leonardo diagram in the Vitruvian Man",
     "vitruvian man leonardo vitruvius de architectura proportion anatomy"),
    # --- 9 ---
    ("Michelangelo painted the Sistine Chapel ceiling between 1508 and 1512 on a scaffold he designed himself after refusing Bramante's hanging rig; the buon fresco technique meant a day's giornata had to be completed before the plaster set.", "milestone", "knowledge", False,
     [("Michelangelo", "person"), ("Sistine Chapel", "place"), ("Bramante", "person"), ("buon fresco", "concept"), ("giornata", "concept")],
     [("Sistine Chapel", "Michelangelo", "AUTHORED_BY"), ("Michelangelo", "buon fresco", "USES")],
     "which fresco technique forced Michelangelo to finish each Sistine section in a single day",
     "michelangelo sistine ceiling bramante scaffold buon fresco giornata 1508"),
    # --- 10. noise ---
    ("The cafeteria's espresso machine has been making a grinding noise for two weeks and nobody has put in a ticket.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Michelangelo's David was carved from a single flawed Carrara marble block abandoned by two earlier sculptors; the 1504 unveiling placed it outside the Palazzo Vecchio as a civic symbol of the Florentine Republic.", "fact", "knowledge", False,
     [("Michelangelo", "person"), ("David", "publication"), ("Carrara", "place"), ("Palazzo Vecchio", "place"), ("Florentine Republic", "organization")],
     [("David", "Michelangelo", "AUTHORED_BY"), ("David", "Palazzo Vecchio", "LOCATED_IN")],
     "which flawed marble did Michelangelo rescue for his Florentine David statue",
     "michelangelo david carrara marble palazzo vecchio republic 1504"),
    # --- 12 ---
    ("Raphael's School of Athens in the Stanza della Segnatura stages Plato and Aristotle at the vanishing point and reportedly gives Plato Leonardo's features as a tribute.", "decision", "knowledge", False,
     [("Raphael", "person"), ("School of Athens", "publication"), ("Stanza della Segnatura", "place"), ("Plato", "person"), ("Aristotle", "person"), ("Leonardo", "person")],
     [("School of Athens", "Raphael", "AUTHORED_BY"), ("School of Athens", "Stanza della Segnatura", "LOCATED_IN")],
     "which two philosophers anchor the vanishing point of Raphael's School of Athens",
     "raphael school athens stanza segnatura plato aristotle leonardo portrait"),
    # --- 13 ---
    ("Titian's late poesie for Philip II abandoned sharp outline for broken impasto applied with bristle ends and fingers; the technique anticipates Rembrandt and Velázquez by a full century.", "preference", "knowledge", False,
     [("Titian", "person"), ("Philip II", "person"), ("impasto", "concept"), ("Rembrandt", "person"), ("Velázquez", "person")],
     [("Titian", "impasto", "USES"), ("Rembrandt", "Titian", "BUILDS_ON"), ("Velázquez", "Titian", "BUILDS_ON")],
     "which late Titian technique prefigured Rembrandt and Velázquez by a century",
     "titian philip ii poesie impasto broken outline rembrandt velazquez"),
    # --- 14 ---
    ("Albrecht Dürer's Melencolia I engraving of 1514 encodes a 4-by-4 magic square whose bottom row contains 15 and 14, marking the year of the print.", "reference", "knowledge", False,
     [("Albrecht Dürer", "person"), ("Melencolia I", "publication"), ("magic square", "concept")],
     [("Melencolia I", "Albrecht Dürer", "AUTHORED_BY"), ("Melencolia I", "magic square", "USES")],
     "which hidden numerical device in Dürer's Melencolia I dates the print to 1514",
     "durer melencolia engraving magic square 1514 bottom row date"),
    # --- 15 ---
    ("Caravaggio's tenebrism — a near-black ground lit by a single raking light — became the decisive Baroque lighting grammar and was copied across Naples, Utrecht, and Seville within a decade.", "architecture", "knowledge", False,
     [("Caravaggio", "person"), ("tenebrism", "concept"), ("Baroque", "concept"), ("Naples", "place"), ("Utrecht", "place"), ("Seville", "place")],
     [("Caravaggio", "tenebrism", "USES"), ("tenebrism", "Baroque", "APPLIES_TO")],
     "which lighting system from Caravaggio became Baroque grammar across Europe",
     "caravaggio tenebrism baroque raking light naples utrecht seville"),
    # --- 16 ---
    ("Bernini preferred pairing sculpture with a staged architectural setting: the Ecstasy of Saint Teresa in the Cornaro Chapel is framed by a hidden overhead light well and theatre-box galleries of Cornaro family figures.", "decision", "knowledge", False,
     [("Bernini", "person"), ("Ecstasy of Saint Teresa", "publication"), ("Cornaro Chapel", "place"), ("light well", "concept")],
     [("Ecstasy of Saint Teresa", "Bernini", "AUTHORED_BY"), ("Ecstasy of Saint Teresa", "Cornaro Chapel", "LOCATED_IN")],
     "which Bernini sculpture relies on a hidden overhead light well inside the Cornaro Chapel",
     "bernini ecstasy saint teresa cornaro chapel light well theatre box"),
    # --- 17 ---
    ("Velázquez's Las Meninas, completed in 1656 and now at the Prado, builds a triangulated gaze between the Infanta Margarita, the painter at his easel, and the mirrored royal couple on the back wall.", "reference", "knowledge", False,
     [("Velázquez", "person"), ("Las Meninas", "publication"), ("Prado", "place"), ("Infanta Margarita", "person")],
     [("Las Meninas", "Velázquez", "AUTHORED_BY"), ("Las Meninas", "Prado", "LOCATED_IN")],
     "which three focal points form the gaze triangle of Las Meninas",
     "velazquez las meninas prado infanta margarita mirror royal couple"),
    # --- 18 ---
    ("Rembrandt's Night Watch was cropped on all four sides in 1715 when it was moved into Amsterdam's town hall, and the Rijksmuseum's 2021 Operation Night Watch used AI plus a Lundens copy to reconstruct the missing figures digitally.", "milestone", "knowledge", False,
     [("Rembrandt", "person"), ("Night Watch", "publication"), ("Amsterdam", "place"), ("Rijksmuseum", "place"), ("Operation Night Watch", "project"), ("Lundens", "person")],
     [("Night Watch", "Rembrandt", "AUTHORED_BY"), ("Night Watch", "Rijksmuseum", "LOCATED_IN"), ("Operation Night Watch", "Night Watch", "APPLIES_TO")],
     "how did the Rijksmuseum reconstruct the cropped edges of Rembrandt's Night Watch in 2021",
     "rembrandt night watch rijksmuseum operation lundens copy crop 1715"),
    # --- 19 ---
    ("Vermeer's Girl with a Pearl Earring is a tronie rather than a commissioned portrait; the lapis-lazuli turban and natural ultramarine were unusual luxury for a 17th-century Delft interior painter.", "architecture", "knowledge", False,
     [("Vermeer", "person"), ("Girl with a Pearl Earring", "publication"), ("tronie", "concept"), ("lapis-lazuli", "concept"), ("ultramarine", "concept"), ("Delft", "place")],
     [("Girl with a Pearl Earring", "Vermeer", "AUTHORED_BY"), ("Girl with a Pearl Earring", "tronie", "IS_A")],
     "which pigment luxury and genre category does Vermeer's Girl with a Pearl Earring belong to",
     "vermeer girl pearl earring tronie lapis lazuli ultramarine delft"),
    # --- 20 ---
    ("Goya's Black Paintings, executed directly on the plaster walls of the Quinta del Sordo, were transferred to canvas in 1874 and now hang at the Prado; the transfer process likely smeared the original palette.", "problem", "knowledge", False,
     [("Goya", "person"), ("Black Paintings", "publication"), ("Quinta del Sordo", "place"), ("Prado", "place")],
     [("Black Paintings", "Goya", "AUTHORED_BY"), ("Black Paintings", "Prado", "LOCATED_IN")],
     "which transfer from plaster to canvas likely distorted Goya's Black Paintings palette",
     "goya black paintings quinta del sordo plaster transfer prado 1874"),
    # --- 21 ---
    ("J. M. W. Turner's late atmospheric seascapes dissolved form into chromatic mist and shaped Monet's London Houses of Parliament series directly; Monet studied them at the National Gallery during his 1870 exile.", "decision", "knowledge", False,
     [("J. M. W. Turner", "person"), ("Monet", "person"), ("Houses of Parliament", "publication"), ("National Gallery", "place")],
     [("Monet", "J. M. W. Turner", "BUILDS_ON"), ("Houses of Parliament", "Monet", "AUTHORED_BY")],
     "which Turner paintings did Monet study in London during his 1870 exile",
     "turner seascape monet houses parliament national gallery 1870 exile"),
    # --- 22 ---
    ("Caspar David Friedrich's Wanderer above the Sea of Fog formalised the Rückenfigur device — a contemplative figure seen from behind — as the visual signature of German Romantic landscape.", "decision", "knowledge", False,
     [("Caspar David Friedrich", "person"), ("Wanderer above the Sea of Fog", "publication"), ("Rückenfigur", "concept"), ("Romantic", "concept")],
     [("Wanderer above the Sea of Fog", "Caspar David Friedrich", "AUTHORED_BY"), ("Wanderer above the Sea of Fog", "Rückenfigur", "USES")],
     "which compositional device did Friedrich turn into the signature of German Romantic landscape",
     "caspar david friedrich wanderer fog ruckenfigur romantic landscape"),
    # --- 23 ---
    ("Delacroix painted Liberty Leading the People in 1830 in direct response to the July Revolution in Paris; the French state bought it, hid it during the restored monarchy, and it finally entered the Louvre in 1874.", "decision", "knowledge", False,
     [("Delacroix", "person"), ("Liberty Leading the People", "publication"), ("July Revolution", "event"), ("Paris", "place"), ("Louvre", "place")],
     [("Liberty Leading the People", "Delacroix", "AUTHORED_BY"), ("Liberty Leading the People", "Louvre", "LOCATED_IN"), ("Liberty Leading the People", "July Revolution", "RELATED_TO")],
     "which 1830 revolt prompted Delacroix's Liberty Leading the People and delayed its display",
     "delacroix liberty leading people july revolution 1830 paris louvre"),
    # --- 24 ---
    ("Monet's Water Lilies at the Orangerie were painted specifically for two elliptical rooms whose curved walls dissolve the horizon line; the installation was conceived with Clemenceau as a memorial to the end of the First World War.", "architecture", "knowledge", False,
     [("Monet", "person"), ("Water Lilies", "publication"), ("Orangerie", "place"), ("Clemenceau", "person"), ("First World War", "event")],
     [("Water Lilies", "Monet", "AUTHORED_BY"), ("Water Lilies", "Orangerie", "LOCATED_IN"), ("Water Lilies", "First World War", "RELATED_TO")],
     "why did Monet design the Orangerie Water Lilies rooms as ellipses with Clemenceau",
     "monet water lilies orangerie clemenceau first world war ellipse horizon"),
    # --- 25 ---
    ("Manet's Le Déjeuner sur l'herbe scandalised the 1863 Salon des Refusés because the nude woman met the viewer's eye directly while clothed men picnicked around her, breaking the academic mythological alibi.", "decision", "knowledge", False,
     [("Manet", "person"), ("Le Déjeuner sur l'herbe", "publication"), ("Salon des Refusés", "event"), ("academic", "concept")],
     [("Le Déjeuner sur l'herbe", "Manet", "AUTHORED_BY"), ("Le Déjeuner sur l'herbe", "Salon des Refusés", "RELATED_TO")],
     "why did Manet's Déjeuner scandalise the 1863 Salon des Refusés",
     "manet dejeuner herbe salon refuses 1863 nude gaze academic"),
    # --- 26 ---
    ("Degas preferred the backstage and rehearsal rooms of the Paris Opera over stage scenes and worked largely in pastel; the off-balance compositions borrow cropping directly from Japanese ukiyo-e prints.", "preference", "knowledge", False,
     [("Degas", "person"), ("Paris Opera", "place"), ("pastel", "concept"), ("ukiyo-e", "concept")],
     [("Degas", "pastel", "USES"), ("Degas", "ukiyo-e", "BUILDS_ON"), ("Degas", "Paris Opera", "VISITED")],
     "which Parisian venue and Japanese tradition shaped Degas's cropping choices",
     "degas paris opera rehearsal pastel ukiyo e japanese cropping"),
    # --- 27 ---
    ("Renoir's Bal du moulin de la Galette captures dappled open-air sunlight through sycamore leaves and was painted on a series of Sunday afternoons at a Montmartre dance hall.", "reference", "knowledge", False,
     [("Renoir", "person"), ("Bal du moulin de la Galette", "publication"), ("Montmartre", "place")],
     [("Bal du moulin de la Galette", "Renoir", "AUTHORED_BY"), ("Bal du moulin de la Galette", "Montmartre", "LOCATED_IN")],
     "which Montmartre dance hall did Renoir paint on Sunday afternoons for Bal du moulin",
     "renoir bal moulin galette montmartre dappled sunlight sycamore"),
    # --- 28 ---
    ("Pissarro was the only painter to exhibit in all eight Impressionist group shows between 1874 and 1886 and quietly mentored both Cézanne and Gauguin during their formative years.", "decision", "knowledge", False,
     [("Pissarro", "person"), ("Impressionist", "concept"), ("Cézanne", "person"), ("Gauguin", "person")],
     [("Pissarro", "Impressionist", "APPLIES_TO"), ("Cézanne", "Pissarro", "KNOWS"), ("Gauguin", "Pissarro", "KNOWS")],
     "which Impressionist painter showed in all eight group exhibitions and mentored Cézanne",
     "pissarro impressionist group show 1874 1886 cezanne gauguin mentor"),
    # --- 29 ---
    ("Mary Cassatt was the only American invited into the Impressionist circle and pushed the Havemeyer collection toward Degas and Manet, seeding what became the Met's French 19th-century holdings.", "reference", "knowledge", False,
     [("Mary Cassatt", "person"), ("Impressionist", "concept"), ("Havemeyer", "person"), ("Met", "place"), ("Degas", "person"), ("Manet", "person")],
     [("Mary Cassatt", "Impressionist", "APPLIES_TO"), ("Havemeyer", "Mary Cassatt", "KNOWS"), ("Havemeyer", "Met", "RELATED_TO")],
     "how did Mary Cassatt shape the Met's French 19th-century collection",
     "mary cassatt american impressionist havemeyer met degas manet"),
    # --- 30 ---
    ("Van Gogh painted The Starry Night in June 1889 from a memory of the view from his asylum window at Saint-Rémy-de-Provence; the work entered MoMA in 1941 and has been a pilgrimage point ever since.", "fact", "knowledge", False,
     [("Van Gogh", "person"), ("The Starry Night", "publication"), ("Saint-Rémy-de-Provence", "place"), ("MoMA", "place")],
     [("The Starry Night", "Van Gogh", "AUTHORED_BY"), ("The Starry Night", "MoMA", "LOCATED_IN"), ("Van Gogh", "Saint-Rémy-de-Provence", "LIVES_IN")],
     "where did Van Gogh paint The Starry Night and when did MoMA acquire it",
     "van gogh starry night saint remy asylum moma 1889 1941 memory"),
    # --- 31 ---
    ("Cézanne's late Mont Sainte-Victoire canvases modulate colour planes rather than outlining form; Picasso and Braque cited these directly as the entry point to analytic Cubism a decade later.", "fact", "knowledge", False,  # keep fact
     [("Cézanne", "person"), ("Mont Sainte-Victoire", "place"), ("Picasso", "person"), ("Braque", "person"), ("analytic Cubism", "concept")],
     [("Picasso", "Cézanne", "BUILDS_ON"), ("Braque", "Cézanne", "BUILDS_ON"), ("analytic Cubism", "Cézanne", "BUILDS_ON")],
     "which late Cézanne series did Picasso and Braque credit as the start of Cubism",
     "cezanne mont sainte victoire colour plane picasso braque cubism"),
    # --- 32 ---
    ("Gauguin left Paris for Tahiti in 1891 in pursuit of what he imagined as a pre-industrial sensibility; the flat colour fields and synthetist outline he developed there directly fed Matisse and the Fauves.", "preference", "knowledge", False,
     [("Gauguin", "person"), ("Tahiti", "place"), ("synthetist", "concept"), ("Matisse", "person"), ("Fauves", "concept")],
     [("Gauguin", "Tahiti", "LIVES_IN"), ("Matisse", "Gauguin", "BUILDS_ON"), ("Fauves", "synthetist", "BUILDS_ON")],
     "which Gauguin move and technique seeded Matisse and the Fauves",
     "gauguin tahiti 1891 synthetist flat colour matisse fauves"),
    # --- 33 ---
    ("Seurat's A Sunday on La Grande Jatte applied divisionist dots per his reading of Chevreul's chromatic theory; he called the method chromoluminarism rather than the pointillism label critics later attached to it.", "architecture", "knowledge", False,
     [("Seurat", "person"), ("A Sunday on La Grande Jatte", "publication"), ("Chevreul", "person"), ("chromoluminarism", "concept"), ("pointillism", "concept")],
     [("A Sunday on La Grande Jatte", "Seurat", "AUTHORED_BY"), ("chromoluminarism", "Chevreul", "BUILDS_ON"), ("Seurat", "chromoluminarism", "USES")],
     "which colour theorist did Seurat draw on for the dots in La Grande Jatte",
     "seurat grande jatte chevreul chromoluminarism pointillism divisionist"),
    # --- 34 ---
    ("Picasso's Les Demoiselles d'Avignon, painted in 1907 but hidden in his studio until 1916, reworked a brothel scene through Iberian sculpture and African-mask faces and pushed the group toward analytic Cubism.", "milestone", "knowledge", False,
     [("Picasso", "person"), ("Les Demoiselles d'Avignon", "publication"), ("Iberian sculpture", "concept"), ("African-mask", "concept"), ("analytic Cubism", "concept")],
     [("Les Demoiselles d'Avignon", "Picasso", "AUTHORED_BY"), ("Les Demoiselles d'Avignon", "Iberian sculpture", "BUILDS_ON"), ("analytic Cubism", "Les Demoiselles d'Avignon", "BUILDS_ON")],
     "which 1907 Picasso canvas bridges Iberian and African masks with analytic Cubism",
     "picasso demoiselles avignon 1907 iberian african mask cubism brothel"),
    # --- 35 ---
    ("Picasso's Guernica was painted in 1937 for the Spanish pavilion at the Paris World's Fair in reaction to the Luftwaffe's bombing of the Basque town; it only returned to Spain in 1981 after Franco's death.", "milestone", "knowledge", False,
     [("Picasso", "person"), ("Guernica", "publication"), ("Paris World's Fair", "event"), ("Luftwaffe", "organization"), ("Franco", "person"), ("Spain", "place")],
     [("Guernica", "Picasso", "AUTHORED_BY"), ("Guernica", "Paris World's Fair", "RELATED_TO"), ("Guernica", "Spain", "LOCATED_IN")],
     "which 1937 bombing prompted Guernica and when did it return to Spain",
     "picasso guernica paris world fair 1937 luftwaffe basque franco 1981"),
    # --- 36 ---
    ("Matisse cut painted paper with scissors in his late bedridden years and called the gouaches découpées drawing with colour; The Snail of 1953 at Tate Modern is the largest surviving example.", "preference", "knowledge", False,
     [("Matisse", "person"), ("gouaches découpées", "concept"), ("The Snail", "publication"), ("Tate Modern", "place")],
     [("The Snail", "Matisse", "AUTHORED_BY"), ("The Snail", "Tate Modern", "LOCATED_IN"), ("Matisse", "gouaches découpées", "USES")],
     "which late Matisse technique produced The Snail at Tate Modern",
     "matisse gouache decoupee cut paper snail tate modern 1953 colour"),
    # --- 37 ---
    ("Kandinsky argued in On the Spiritual in Art that colour and form could resonate without representing anything; his Bauhaus years from 1922 to 1933 systematised the position into a teaching curriculum.", "architecture", "knowledge", False,
     [("Kandinsky", "person"), ("On the Spiritual in Art", "publication"), ("Bauhaus", "organization")],
     [("On the Spiritual in Art", "Kandinsky", "AUTHORED_BY"), ("Kandinsky", "Bauhaus", "WORKS_AT")],
     "which Kandinsky treatise and teaching post systematised non-representational abstraction",
     "kandinsky spiritual art bauhaus 1922 1933 abstract non representation"),
    # --- 38 ---
    ("Mondrian's neoplasticism stripped painting to black grid, primary colour, and white field; he insisted the diagonal was forbidden and broke with Theo van Doesburg over the rule.", "decision", "knowledge", False,
     [("Mondrian", "person"), ("neoplasticism", "concept"), ("Theo van Doesburg", "person")],
     [("Mondrian", "neoplasticism", "USES"), ("Mondrian", "Theo van Doesburg", "CONTRADICTS")],
     "which rule in Mondrian's neoplasticism triggered the split with Theo van Doesburg",
     "mondrian neoplasticism grid primary colour diagonal van doesburg split"),
    # --- 39 ---
    ("Duchamp's Fountain — a men's urinal signed R. Mutt and submitted to the 1917 Society of Independent Artists in New York — is the founding readymade and the pivot from craft to concept in Western art.", "milestone", "knowledge", False,
     [("Duchamp", "person"), ("Fountain", "publication"), ("R. Mutt", "person"), ("Society of Independent Artists", "organization"), ("New York", "place"), ("readymade", "concept")],
     [("Fountain", "Duchamp", "AUTHORED_BY"), ("Fountain", "readymade", "IS_A"), ("Fountain", "Society of Independent Artists", "RELATED_TO")],
     "which 1917 Duchamp submission is the founding readymade of conceptual art",
     "duchamp fountain r mutt 1917 society independent artists readymade"),
    # --- 40 ---
    ("Malevich's Black Square, first shown in the Last Futurist Exhibition 0.10 in Petrograd in 1915, was hung in a corner like an Orthodox icon to mark a deliberate liturgical break.", "milestone", "knowledge", False,
     [("Malevich", "person"), ("Black Square", "publication"), ("0.10", "event"), ("Petrograd", "place"), ("Orthodox icon", "concept")],
     [("Black Square", "Malevich", "AUTHORED_BY"), ("Black Square", "0.10", "RELATED_TO"), ("0.10", "Petrograd", "LOCATED_IN")],
     "which 1915 Petrograd exhibition staged Malevich's Black Square as an icon",
     "malevich black square 0 10 petrograd 1915 orthodox icon corner"),
    # --- 41 ---
    ("Magritte's The Treachery of Images undercuts the viewer's reflex to read paint as object; the inscribed Ceci n'est pas une pipe became shorthand for the sign-referent problem in semiotics.", "decision", "knowledge", False,
     [("Magritte", "person"), ("The Treachery of Images", "publication"), ("Ceci n'est pas une pipe", "concept"), ("semiotics", "concept")],
     [("The Treachery of Images", "Magritte", "AUTHORED_BY"), ("The Treachery of Images", "semiotics", "APPLIES_TO")],
     "which Magritte inscription became the canonical semiotic example of sign versus referent",
     "magritte treachery images ceci pas pipe semiotics sign referent"),
    # --- 42 ---
    ("Dalí's The Persistence of Memory with its melting pocket-watches is paraphrase of Einsteinian relativity, which Dalí claimed in interviews was his primary source; MoMA acquired it as a gift in 1934.", "architecture", "knowledge", False,
     [("Dalí", "person"), ("The Persistence of Memory", "publication"), ("Einstein", "person"), ("MoMA", "place")],
     [("The Persistence of Memory", "Dalí", "AUTHORED_BY"), ("The Persistence of Memory", "MoMA", "LOCATED_IN"), ("The Persistence of Memory", "Einstein", "BUILDS_ON")],
     "which scientific theory did Dalí credit for the melting watches in The Persistence of Memory",
     "dali persistence memory melting watch einstein relativity moma 1934"),
    # --- 43. noise ---
    ("The museum gift shop sold out of the resin T. rex keychain again and the buyer has a rebuy order in with the vendor.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Jackson Pollock's drip paintings from 1947 to 1950 were poured from household enamel with hardware sticks on unstretched canvas laid on the barn floor in Springs; the process photos by Hans Namuth shaped the public image of Abstract Expressionism.", "decision", "knowledge", False,
     [("Jackson Pollock", "person"), ("drip paintings", "concept"), ("Springs", "place"), ("Hans Namuth", "person"), ("Abstract Expressionism", "concept")],
     [("Jackson Pollock", "drip paintings", "USES"), ("Hans Namuth", "Jackson Pollock", "KNOWS"), ("Jackson Pollock", "Abstract Expressionism", "APPLIES_TO")],
     "which photographer's documentation shaped the public image of Pollock's drip method",
     "pollock drip enamel springs hans namuth abstract expressionism barn"),
    # --- 45 ---
    ("Mark Rothko designed the Seagram murals for the Four Seasons restaurant, then withdrew them in protest and sent nine to Tate Gallery in 1969; they arrived in London on the day Rothko took his own life.", "reference", "knowledge", False,
     [("Mark Rothko", "person"), ("Seagram murals", "publication"), ("Four Seasons", "place"), ("Tate Gallery", "place")],
     [("Seagram murals", "Mark Rothko", "AUTHORED_BY"), ("Seagram murals", "Tate Gallery", "LOCATED_IN")],
     "why did Rothko pull the Seagram murals from the Four Seasons and where did they go",
     "rothko seagram mural four seasons tate 1969 withdraw protest london"),
    # --- 46 ---
    ("Willem de Kooning's Woman series from the early 1950s broke the Abstract Expressionist gentlemen's agreement against figuration; Greenberg dismissed it as a relapse and Rosenberg defended it as action painting.", "architecture", "knowledge", False,
     [("Willem de Kooning", "person"), ("Woman", "publication"), ("Abstract Expressionist", "concept"), ("Greenberg", "person"), ("Rosenberg", "person"), ("action painting", "concept")],
     [("Woman", "Willem de Kooning", "AUTHORED_BY"), ("Woman", "Abstract Expressionist", "CONTRADICTS"), ("Rosenberg", "Woman", "SUPPORTS")],
     "which de Kooning series broke the Abstract Expressionist agreement against figuration",
     "de kooning woman 1950s abstract expressionist greenberg rosenberg action"),
    # --- 47 ---
    ("Andy Warhol's Campbell's Soup Cans of 1962 consisted of 32 hand-painted canvases — one per Campbell's variety then on sale — shown in a shelf-like row at Ferus Gallery in Los Angeles.", "fact", "knowledge", False,  # keep fact
     [("Andy Warhol", "person"), ("Campbell's Soup Cans", "publication"), ("Campbell's", "organization"), ("Ferus Gallery", "place"), ("Los Angeles", "place")],
     [("Campbell's Soup Cans", "Andy Warhol", "AUTHORED_BY"), ("Campbell's Soup Cans", "Ferus Gallery", "LOCATED_IN"), ("Ferus Gallery", "Los Angeles", "LOCATED_IN")],
     "how did Warhol stage Campbell's Soup Cans at the 1962 Ferus Gallery show",
     "warhol campbell soup cans 32 ferus gallery los angeles 1962 shelf"),
    # --- 48 ---
    ("Roy Lichtenstein's Benday-dot canvases translated comic-strip panels by Irv Novick and Russ Heath into large-scale oil and Magna; the source artists were unacknowledged during Lichtenstein's lifetime and attribution debates continue.", "problem", "knowledge", False,
     [("Roy Lichtenstein", "person"), ("Benday-dot", "concept"), ("Irv Novick", "person"), ("Russ Heath", "person"), ("Magna", "concept")],
     [("Roy Lichtenstein", "Benday-dot", "USES"), ("Roy Lichtenstein", "Irv Novick", "BUILDS_ON"), ("Roy Lichtenstein", "Russ Heath", "BUILDS_ON")],
     "which comic-strip artists did Lichtenstein redraw without credit in his Benday-dot canvases",
     "lichtenstein benday dot comic strip irv novick russ heath magna"),
    # --- 49 ---
    ("Jean-Michel Basquiat's crown motif appeared first in SAMO graffiti tags on lower-Manhattan walls before migrating into gallery canvases and into the three-way collaboration with Warhol in 1985.", "fact", "knowledge", False,  # keep fact
     [("Jean-Michel Basquiat", "person"), ("SAMO", "concept"), ("crown", "concept"), ("Warhol", "person"), ("Manhattan", "place")],
     [("Jean-Michel Basquiat", "SAMO", "USES"), ("Jean-Michel Basquiat", "Warhol", "KNOWS"), ("Jean-Michel Basquiat", "crown", "USES")],
     "where did Basquiat's crown motif first appear before reaching gallery canvases",
     "basquiat samo graffiti crown manhattan warhol 1985 collaboration"),
    # --- 50 ---
    ("Barbara Kruger's red-bar pronouns like I shop therefore I am superimposed over black-and-white photographs pull directly from the editorial layout conventions she learned as a designer at Condé Nast.", "reference", "knowledge", False,
     [("Barbara Kruger", "person"), ("red-bar", "concept"), ("Condé Nast", "organization")],
     [("Barbara Kruger", "Condé Nast", "WORKS_AT"), ("Barbara Kruger", "red-bar", "USES")],
     "which commercial design training shaped Kruger's red-bar pronoun layout",
     "kruger red bar pronoun shop therefore am conde nast editorial layout"),
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
