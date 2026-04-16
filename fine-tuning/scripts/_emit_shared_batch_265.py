"""One-off emitter for shared-base batch-265 — knowledge domain (political philosophy: thinkers from Plato to Sandel plus core concepts like social contract, liberty, justice, capabilities).

Writes 50 rows to data/v2/shared/batch_265.tmp.jsonl with ids shared-13201..13250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_265.tmp.jsonl"
ID_OFFSET = 13200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Plato argues in the Republic that a just city must be ruled by philosopher-kings whose long education in dialectic turns the soul toward the Form of the Good before they handle political power.", "architecture", "knowledge", False,
     [("Plato", "person"), ("Republic", "publication"), ("philosopher-kings", "concept"), ("Form of the Good", "concept")],
     [("Republic", "Plato", "AUTHORED_BY"), ("philosopher-kings", "Form of the Good", "RELATED_TO")],
     "which ruler class does Plato prescribe in the Republic and what metaphysical object grounds their authority",
     "plato republic philosopher king form good dialectic soul rule"),
    # --- 2 ---
    ("Aristotle's Politics treats the polis as prior to the individual in the order of ends, arguing that humans reach eudaimonia only inside a community organised for shared rational life.", "decision", "knowledge", False,
     [("Aristotle", "person"), ("Politics", "publication"), ("polis", "concept"), ("eudaimonia", "concept")],
     [("Politics", "Aristotle", "AUTHORED_BY"), ("polis", "eudaimonia", "CAUSES")],
     "which political unit does Aristotle treat as prior to the individual and why does he think flourishing needs it",
     "aristotle politics polis eudaimonia community rational prior end"),
    # --- 3 ---
    ("Machiavelli split his political project across two works: The Prince offered a mirror for a new ruler holding unstable power while the Discourses on Livy praised the Roman republic as a durable mixed regime.", "reference", "knowledge", False,
     [("Machiavelli", "person"), ("The Prince", "publication"), ("Discourses on Livy", "publication"), ("Roman republic", "concept")],
     [("The Prince", "Machiavelli", "AUTHORED_BY"), ("Discourses on Livy", "Machiavelli", "AUTHORED_BY")],
     "which two Machiavelli works carry his princely and republican teachings and which model regime did the later book praise",
     "machiavelli prince discourses livy roman republic mixed regime"),
    # --- 4 ---
    ("Hobbes in Leviathan derives sovereign authority from a covenant by which people in the state of nature authorise one representative to secure peace; the alternative is the war of all against all.", "decision", "knowledge", False,
     [("Hobbes", "person"), ("Leviathan", "publication"), ("state of nature", "concept"), ("sovereign", "concept"), ("covenant", "concept")],
     [("Leviathan", "Hobbes", "AUTHORED_BY"), ("covenant", "sovereign", "PRODUCES")],
     "how does Hobbes derive sovereign authority in Leviathan and what is the baseline he contrasts it against",
     "hobbes leviathan covenant sovereign state nature war peace"),
    # --- 5 ---
    ("Locke's Two Treatises grounds legitimate government in consent of the governed and in the prior natural rights to life, liberty, and estate, rejecting Filmer's patriarchal case for absolute monarchy.", "decision", "knowledge", False,
     [("Locke", "person"), ("Two Treatises", "publication"), ("consent", "concept"), ("natural rights", "concept"), ("Filmer", "person")],
     [("Two Treatises", "Locke", "AUTHORED_BY"), ("Two Treatises", "Filmer", "CONTRADICTS")],
     "on which two foundations does Locke rest legitimate government and whose patriarchal thesis was he rebutting",
     "locke two treatises consent natural right life liberty estate filmer"),
    # --- 6 ---
    ("Rousseau in The Social Contract distinguishes the general will, which aims at the common good, from the mere will of all, a statistical sum of private interests that can miss the common good entirely.", "architecture", "knowledge", False,
     [("Rousseau", "person"), ("The Social Contract", "publication"), ("general will", "concept"), ("will of all", "concept"), ("common good", "concept")],
     [("The Social Contract", "Rousseau", "AUTHORED_BY"), ("general will", "common good", "APPLIES_TO")],
     "which distinction does Rousseau draw in The Social Contract between two kinds of collective willing",
     "rousseau social contract general will of all common good private"),
    # --- 7 ---
    ("Montesquieu's Spirit of the Laws argues that liberty depends on the separation of powers across legislative, executive, and judicial branches so that one body never concentrates all three, a structural check on tyranny.", "decision", "knowledge", False,
     [("Montesquieu", "person"), ("Spirit of the Laws", "publication"), ("separation of powers", "concept"), ("tyranny", "concept")],
     [("Spirit of the Laws", "Montesquieu", "AUTHORED_BY"), ("separation of powers", "tyranny", "FIXES")],
     "which structural design in Spirit of the Laws does Montesquieu claim preserves liberty against tyranny",
     "montesquieu spirit laws separation power legislative executive judicial"),
    # --- 8 ---
    ("Adam Smith wrote two complementary books: The Theory of Moral Sentiments described sympathy and the impartial spectator, and The Wealth of Nations traced how a division of labour in markets coordinates strangers.", "reference", "knowledge", False,
     [("Adam Smith", "person"), ("The Theory of Moral Sentiments", "publication"), ("The Wealth of Nations", "publication"), ("impartial spectator", "concept"), ("division of labour", "concept")],
     [("The Theory of Moral Sentiments", "Adam Smith", "AUTHORED_BY"), ("The Wealth of Nations", "Adam Smith", "AUTHORED_BY")],
     "which two Smith books cover moral psychology and political economy and which anchoring idea belongs to each",
     "adam smith moral sentiments wealth nations impartial spectator labour"),
    # --- 9 ---
    ("Burke's Reflections on the Revolution in France attacked the Jacobins' abstract rationalism and defended inherited institutions, prescription, and prejudice as accumulated practical wisdom.", "decision", "knowledge", False,
     [("Burke", "person"), ("Reflections on the Revolution in France", "publication"), ("Jacobins", "organization"), ("prescription", "concept"), ("prejudice", "concept")],
     [("Reflections on the Revolution in France", "Burke", "AUTHORED_BY"), ("Reflections on the Revolution in France", "Jacobins", "CONTRADICTS")],
     "which revolutionary faction did Burke attack in Reflections and which conservative ideas did he defend in reply",
     "burke reflection revolution france jacobin prescription prejudice wisdom"),
    # --- 10. noise ---
    ("The departmental coffee pot in the history building has a rota taped to the wall that nobody has updated since the autumn term.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kant's Perpetual Peace proposes a federation of republican states as the political arrangement most consistent with the categorical imperative applied to relations between peoples.", "decision", "knowledge", False,
     [("Kant", "person"), ("Perpetual Peace", "publication"), ("federation", "concept"), ("republican states", "concept"), ("categorical imperative", "concept")],
     [("Perpetual Peace", "Kant", "AUTHORED_BY"), ("federation", "categorical imperative", "APPLIES_TO")],
     "which international arrangement does Kant's Perpetual Peace recommend and on which moral principle does he ground it",
     "kant perpetual peace federation republican state categorical imperative"),
    # --- 12 ---
    ("Hegel's Philosophy of Right locates freedom not in arbitrary choice but in ethical life: the family, civil society, and the rational state each supply a layer of recognised mutual recognition.", "architecture", "knowledge", False,
     [("Hegel", "person"), ("Philosophy of Right", "publication"), ("ethical life", "concept"), ("civil society", "concept"), ("rational state", "concept")],
     [("Philosophy of Right", "Hegel", "AUTHORED_BY"), ("rational state", "ethical life", "HAS_PART")],
     "where does Hegel's Philosophy of Right locate genuine freedom and which three institutions compose his ethical life",
     "hegel philosophy right ethical life family civil society rational state"),
    # --- 13 ---
    ("Marx and Engels in the Communist Manifesto read history as class struggle, while Capital analyses the commodity form and surplus value to show how wage labour reproduces capitalist domination.", "milestone", "knowledge", False,
     [("Marx", "person"), ("Communist Manifesto", "publication"), ("Capital", "publication"), ("class struggle", "concept"), ("surplus value", "concept")],
     [("Communist Manifesto", "Marx", "AUTHORED_BY"), ("Capital", "Marx", "AUTHORED_BY")],
     "which reading of history does the Manifesto advance and which concept from Capital explains how wage labour produces domination",
     "marx manifesto capital class struggle surplus value wage labour"),
    # --- 14 ---
    ("Mill's On Liberty defends the harm principle: the only purpose for which power can be rightfully exercised over any member of a civilised community against his will is to prevent harm to others.", "decision", "knowledge", False,
     [("Mill", "person"), ("On Liberty", "publication"), ("harm principle", "concept"), ("civilised community", "concept")],
     [("On Liberty", "Mill", "AUTHORED_BY")],
     "which limiting principle does Mill defend in On Liberty for legitimate coercion by society",
     "mill on liberty harm principle coerce power individual society"),
    # --- 15 ---
    ("Bentham grounded legislation in the principle of utility, measuring an action's rightness by the balance of pleasure over pain it produces across all affected parties without weighting by rank.", "decision", "knowledge", False,
     [("Bentham", "person"), ("principle of utility", "concept"), ("pleasure", "concept"), ("pain", "concept")],
     [("principle of utility", "pleasure", "USES")],
     "which criterion does Bentham use to evaluate legislation and what does it deliberately refuse to weight",
     "bentham utility pleasure pain legislation rank impartial calculation"),
    # --- 16 ---
    ("John Dewey in The Public and Its Problems reframed democracy as a way of life rather than a mere voting mechanism, emphasising inquiry, publics formed by shared consequences, and experimental governance.", "architecture", "knowledge", False,
     [("John Dewey", "person"), ("The Public and Its Problems", "publication"), ("democracy", "concept"), ("inquiry", "concept")],
     [("The Public and Its Problems", "John Dewey", "AUTHORED_BY")],
     "how does Dewey reframe democracy beyond voting and which epistemic practice does he foreground",
     "dewey public problems democracy inquiry experiment life shared"),
    # --- 17 ---
    ("Hannah Arendt in The Human Condition distinguishes labour, work, and action; action is the only activity that discloses the agent and founds a political space among equals.", "milestone", "knowledge", False,
     [("Hannah Arendt", "person"), ("The Human Condition", "publication"), ("labour", "concept"), ("work", "concept"), ("action", "concept")],
     [("The Human Condition", "Hannah Arendt", "AUTHORED_BY"), ("action", "labour", "IMPROVES_ON")],
     "which triad does Arendt draw in The Human Condition and which member of it founds the political space",
     "arendt human condition labour work action disclose political space"),
    # --- 18 ---
    ("The Origins of Totalitarianism argues that totalitarian regimes differ from tyranny by aiming at total domination through ideology and terror, dissolving the space of spontaneous action between persons.", "fact", "knowledge", False,
     [("The Origins of Totalitarianism", "publication"), ("totalitarian regimes", "concept"), ("ideology", "concept"), ("terror", "concept")],
     [("totalitarian regimes", "ideology", "USES")],
     "how does The Origins of Totalitarianism distinguish totalitarian rule from ordinary tyranny",
     "arendt origin totalitarianism ideology terror total domination tyranny"),
    # --- 19 ---
    ("Isaiah Berlin's Two Concepts of Liberty separates negative liberty, the absence of interference, from positive liberty, self-mastery, and warns that the positive sense has been twisted into state coercion.", "decision", "knowledge", False,
     [("Isaiah Berlin", "person"), ("Two Concepts of Liberty", "publication"), ("negative liberty", "concept"), ("positive liberty", "concept")],
     [("Two Concepts of Liberty", "Isaiah Berlin", "AUTHORED_BY"), ("negative liberty", "positive liberty", "CONTRADICTS")],
     "which two senses of liberty does Berlin contrast and which one does he warn has been weaponised historically",
     "berlin two concept liberty negative positive interference self mastery"),
    # --- 20 ---
    ("Rawls in A Theory of Justice uses the veil of ignorance thought experiment to derive two principles: equal basic liberties for all, and the difference principle, which permits inequalities only to benefit the worst-off.", "architecture", "knowledge", False,
     [("Rawls", "person"), ("A Theory of Justice", "publication"), ("veil of ignorance", "concept"), ("difference principle", "concept"), ("basic liberties", "concept")],
     [("A Theory of Justice", "Rawls", "AUTHORED_BY"), ("veil of ignorance", "difference principle", "PRODUCES")],
     "which thought experiment does Rawls use to derive his two principles of justice and what does the second principle permit",
     "rawls theory justice veil ignorance difference principle basic liberty"),
    # --- 21 ---
    ("Political Liberalism revised Rawls's project to answer pluralism: stable justice must rest on an overlapping consensus among reasonable comprehensive doctrines rather than on any single metaphysical view.", "milestone", "knowledge", False,
     [("Political Liberalism", "publication"), ("overlapping consensus", "concept"), ("reasonable comprehensive doctrines", "concept"), ("pluralism", "concept")],
     [("Political Liberalism", "overlapping consensus", "USES")],
     "what problem does Political Liberalism answer and which device does Rawls introduce to handle it",
     "rawls political liberalism overlapping consensus pluralism reasonable doctrine"),
    # --- 22 ---
    ("Nozick in Anarchy, State, and Utopia defends a minimal state that enforces property, contract, and protection rights but treats any redistributive taxation of labour as on a par with forced labour.", "decision", "knowledge", False,
     [("Nozick", "person"), ("Anarchy, State, and Utopia", "publication"), ("minimal state", "concept"), ("redistributive taxation", "concept")],
     [("Anarchy, State, and Utopia", "Nozick", "AUTHORED_BY"), ("minimal state", "redistributive taxation", "CONTRADICTS")],
     "which shape of state does Nozick defend in Anarchy, State, and Utopia and how does he characterise redistributive taxation",
     "nozick anarchy state utopia minimal redistribute tax property forced"),
    # --- 23 ---
    ("Habermas built discourse ethics on the ideal speech situation, where norms are legitimate only if all affected parties could accept them in unconstrained rational dialogue free of strategic coercion.", "architecture", "knowledge", False,
     [("Habermas", "person"), ("discourse ethics", "concept"), ("ideal speech situation", "concept"), ("strategic coercion", "concept")],
     [("discourse ethics", "ideal speech situation", "USES")],
     "which normative criterion does Habermas offer for legitimate norms and under which idealised conditions must it be tested",
     "habermas discourse ethic ideal speech norm rational dialogue coerce"),
    # --- 24 ---
    ("G.A. Cohen critiqued Rawls by arguing that the difference principle tolerates an incentives-based inequality that citizens motivated by justice would refuse; ethos, not just institutions, has to realise fairness.", "milestone", "knowledge", False,
     [("G.A. Cohen", "person"), ("difference principle", "concept"), ("incentives-based inequality", "concept"), ("ethos", "concept")],
     [("G.A. Cohen", "difference principle", "CONTRADICTS")],
     "which internal weakness did Cohen identify in Rawls's difference principle and which complement did he say justice required",
     "cohen rawls difference principle incentive inequality ethos citizen"),
    # --- 25 ---
    ("Cass Sunstein and Richard Thaler's nudge programme accepts that policy designers always choose a default and argues for libertarian paternalism: frame choices so people decide better without losing options.", "decision", "knowledge", False,
     [("Cass Sunstein", "person"), ("nudge", "concept"), ("libertarian paternalism", "concept"), ("default", "concept")],
     [("nudge", "libertarian paternalism", "APPLIES_TO")],
     "which policy stance does Sunstein call libertarian paternalism and which unavoidable design element does it exploit",
     "sunstein thaler nudge libertarian paternalism default choice option"),
    # --- 26 ---
    ("Martha Nussbaum's Creating Capabilities lists ten central capabilities, from bodily health to control over one's environment, and argues a just society must secure each above a threshold for every citizen.", "fact", "knowledge", False,
     [("Martha Nussbaum", "person"), ("Creating Capabilities", "publication"), ("capabilities", "concept"), ("threshold", "concept")],
     [("Creating Capabilities", "Martha Nussbaum", "AUTHORED_BY")],
     "which list does Nussbaum present in Creating Capabilities and what threshold obligation does she place on a just society",
     "nussbaum creating capability list ten threshold just society secure"),
    # --- 27 ---
    ("Women and Human Development applied the capabilities approach to gender: uneven access to bodily integrity, education, and political voice shows up as capability failure even where formal income statistics look even.", "milestone", "knowledge", False,
     [("Women and Human Development", "publication"), ("capabilities approach", "concept"), ("bodily integrity", "concept"), ("gender", "concept")],
     [("Women and Human Development", "capabilities approach", "APPLIES_TO")],
     "which population does Women and Human Development focus on and what does the book say income statistics miss about them",
     "nussbaum women human development capability gender integrity income"),
    # --- 28 ---
    ("Amartya Sen's development-as-freedom framing reoriented welfare economics from utility or resources to the real freedoms people have; a famine, he showed, can happen without any fall in per-capita food.", "milestone", "knowledge", False,
     [("Amartya Sen", "person"), ("development-as-freedom", "concept"), ("welfare economics", "field"), ("famine", "concept")],
     [("Amartya Sen", "welfare economics", "IMPROVES_ON")],
     "which reframing did Sen bring to welfare economics and which empirical surprise did his famine analysis expose",
     "sen development freedom welfare economic famine food entitlement"),
    # --- 29 ---
    ("Elizabeth Anderson in Private Government argues that the modern workplace is a tightly hierarchical regime most workers cannot exit cheaply, which makes employer authority a political, not merely contractual, problem.", "fact", "knowledge", False,
     [("Elizabeth Anderson", "person"), ("Private Government", "publication"), ("workplace", "concept"), ("employer authority", "concept")],
     [("Private Government", "Elizabeth Anderson", "AUTHORED_BY")],
     "how does Anderson reframe the authority employers wield in Private Government and why does exit not solve it",
     "anderson private government workplace employer authority exit hierarchy"),
    # --- 30 ---
    ("Michael Sandel's Justice course and book argue against Rawlsian neutrality: a political community cannot bracket the good, so debates on distribution must also ask what virtues and goods a society should cultivate.", "decision", "knowledge", False,
     [("Michael Sandel", "person"), ("Justice", "publication"), ("Rawlsian neutrality", "concept"), ("virtues", "concept")],
     [("Justice", "Michael Sandel", "AUTHORED_BY"), ("Justice", "Rawlsian neutrality", "CONTRADICTS")],
     "which liberal commitment does Sandel reject in Justice and which prior question does he say political philosophy must face",
     "sandel justice rawlsian neutrality virtue good community communitarian"),
    # --- 31 ---
    ("The social contract tradition uses a hypothetical agreement in some initial situation to ground political authority; Hobbes, Locke, and Rousseau each specify the baseline and the agreement differently to get different regimes.", "reference", "knowledge", False,
     [("social contract", "concept"), ("Hobbes", "person"), ("Locke", "person"), ("Rousseau", "person")],
     [("social contract", "Hobbes", "APPLIES_TO"), ("social contract", "Locke", "APPLIES_TO"), ("social contract", "Rousseau", "APPLIES_TO")],
     "which device do Hobbes, Locke, and Rousseau share and which parameter of it drives their divergent conclusions",
     "social contract hobbes locke rousseau hypothetical agreement baseline"),
    # --- 32 ---
    ("In the Pettit and Skinner reading, republicanism defines freedom as non-domination: the absence of arbitrary power over you, whether or not the powerful agent currently chooses to interfere.", "architecture", "knowledge", False,
     [("republicanism", "concept"), ("Pettit", "person"), ("Skinner", "person"), ("non-domination", "concept")],
     [("republicanism", "non-domination", "USES")],
     "which freedom concept defines contemporary republicanism and why is non-interference alone considered insufficient",
     "republicanism pettit skinner non domination arbitrary power freedom"),
    # --- 33 ---
    ("Rights-based libertarianism shares its starting point with liberalism but insists that property rights extend so far that most redistributive and regulatory state action counts as rights violation.", "reference", "knowledge", False,
     [("libertarianism", "concept"), ("property rights", "concept"), ("redistributive", "concept"), ("regulatory state", "concept")],
     [("libertarianism", "property rights", "USES")],
     "which starting point does libertarianism share with liberalism and which political measures does it typically reject as rights violations",
     "libertarianism property right redistribute regulate state liberal rights"),
    # --- 34 ---
    ("In MacIntyre's After Virtue and Taylor's Sources of the Self, communitarianism argues that liberal individualism distorts practical reason by abstracting agents from the traditions and narratives that make their ends intelligible.", "reference", "knowledge", False,
     [("communitarianism", "concept"), ("MacIntyre", "person"), ("After Virtue", "publication"), ("Taylor", "person"), ("Sources of the Self", "publication")],
     [("After Virtue", "MacIntyre", "AUTHORED_BY"), ("Sources of the Self", "Taylor", "AUTHORED_BY"), ("communitarianism", "MacIntyre", "APPLIES_TO")],
     "which two communitarian works attack liberal individualism and on which ground do they say it misreads practical reason",
     "macintyre after virtue taylor sources self communitarian tradition narrative"),
    # --- 35 ---
    ("The programme of deliberative democracy holds that legitimate collective decisions must emerge from reasoned public exchange among free and equal citizens, not merely from aggregating preferences by vote count.", "architecture", "knowledge", False,
     [("deliberative democracy", "concept"), ("legitimate collective decisions", "concept"), ("reasoned public exchange", "concept")],
     [("deliberative democracy", "reasoned public exchange", "USES")],
     "which procedural standard does deliberative democracy set for legitimate decisions and what does it reject as insufficient",
     "deliberative democracy reason public exchange citizen aggregate vote"),
    # --- 36 ---
    ("The capabilities approach, developed by Sen and Nussbaum, evaluates well-being by what people are effectively able to do and be, displacing utility and resource metrics as the primary measure of a life's quality.", "milestone", "knowledge", False,
     [("capabilities approach", "concept"), ("Sen", "person"), ("Nussbaum", "person"), ("well-being", "concept")],
     [("capabilities approach", "Sen", "AUTHORED_BY"), ("capabilities approach", "Nussbaum", "AUTHORED_BY")],
     "which well-being metric does the capabilities approach install and which two metrics does it displace",
     "capabilities approach sen nussbaum wellbeing utility resource metric"),
    # --- 37 ---
    ("Machiavelli's Discourses argues that a mixed regime combining monarchical, aristocratic, and popular elements survives longer than a pure form because each estate checks the corruption peculiar to the others.", "architecture", "knowledge", False,
     [("Discourses", "publication"), ("mixed regime", "concept"), ("monarchical", "concept"), ("aristocratic", "concept"), ("popular", "concept")],
     [("Discourses", "mixed regime", "USES")],
     "which regime type does the Discourses defend as most durable and which mechanism gives it that durability",
     "machiavelli discourses mixed regime monarch aristocrat popular check"),
    # --- 38 ---
    ("Hobbes denied an original common ownership of the earth; in the state of nature everyone has a right to everything, which is exactly why peace requires people to alienate that right to the sovereign.", "fact", "knowledge", False,
     [("Hobbes", "person"), ("common ownership", "concept"), ("state of nature", "concept"), ("alienate", "concept")],
     [("alienate", "state of nature", "FIXES")],
     "why does Hobbes say peace requires alienation rather than retention of original rights",
     "hobbes common ownership state nature right everything alienate sovereign"),
    # --- 39 ---
    ("Locke's labour-mixing theory of property gives each person ownership of what they take from the commons and work on, provided enough and as good is left for others; the proviso tightens once money lifts the spoilage limit.", "fact", "knowledge", False,
     [("Locke", "person"), ("labour-mixing", "concept"), ("commons", "concept"), ("spoilage limit", "concept"), ("money", "concept")],
     [("labour-mixing", "commons", "APPLIES_TO")],
     "by which mechanism does Locke generate private property out of the commons and which proviso constrains the result",
     "locke labour mixing property common proviso spoilage money limit"),
    # --- 40 ---
    ("Rousseau's general will is not a majoritarian outcome but the will that all would have if they reasoned as citizens with the common good in view, which is why a majority vote can be wrong about it.", "fact", "knowledge", False,
     [("Rousseau", "person"), ("general will", "concept"), ("majoritarian outcome", "concept"), ("common good", "concept")],
     [("general will", "majoritarian outcome", "CONTRADICTS")],
     "why is Rousseau's general will not simply the majoritarian outcome and what does that imply about vote counts",
     "rousseau general will majoritarian common good citizen vote wrong"),
    # --- 41 ---
    ("Tocqueville's Democracy in America diagnosed a soft despotism where equality of condition leaves citizens isolated under a mild tutelary power and voluntary associations emerge as the main counterweight.", "reference", "knowledge", False,
     [("Tocqueville", "person"), ("Democracy in America", "publication"), ("soft despotism", "concept"), ("voluntary associations", "concept")],
     [("Democracy in America", "Tocqueville", "AUTHORED_BY"), ("voluntary associations", "soft despotism", "FIXES")],
     "which democratic pathology did Tocqueville name and which civic institution did he call its main brake",
     "tocqueville democracy america soft despotism tutelary voluntary association"),
    # --- 42 ---
    ("The veil of ignorance works as a device by removing knowledge of one's class, talents, conception of the good, and generation, so choosers pick principles they could live with from any social position.", "fact", "knowledge", False,
     [("veil of ignorance", "concept"), ("class", "concept"), ("talents", "concept"), ("conception of the good", "concept")],
     [("veil of ignorance", "class", "APPLIES_TO")],
     "which personal facts does the veil of ignorance strip away and why does removing them matter for principle selection",
     "veil ignorance class talent conception good generation chooser"),
    # --- 43. noise ---
    ("A stray cat adopted the graduate lounge and the etiquette committee is now locked in a protracted argument about whether naming it officially violates the no-pet rule.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Berlin warned that positive liberty as self-mastery can be inflated by rationalist regimes into the claim that they know the citizen's real self better than the citizen does, licensing coercion in the name of freedom.", "problem", "knowledge", False,
     [("Berlin", "person"), ("positive liberty", "concept"), ("self-mastery", "concept"), ("rationalist regimes", "concept")],
     [("rationalist regimes", "positive liberty", "USES")],
     "which slide from positive liberty into coercion did Berlin warn rationalist regimes had historically performed",
     "berlin positive liberty self mastery rationalist regime coerce freedom"),
    # --- 45 ---
    ("Dewey rejected the spectator theory of knowledge in politics: citizens are not passive observers of a finished social order but inquirers who reshape the order through experimental collective action.", "preference", "knowledge", False,
     [("Dewey", "person"), ("spectator theory of knowledge", "concept"), ("citizens", "concept"), ("experimental collective action", "concept")],
     [("Dewey", "spectator theory of knowledge", "CONTRADICTS")],
     "which epistemic stance in politics did Dewey reject and which civic role did he install in its place",
     "dewey spectator knowledge citizen experimental collective action inquiry"),
    # --- 46 ---
    ("Arendt preferred the council system she traced across revolutions, from Paris 1871 to Hungary 1956, over representative party democracy because councils preserved the space for political action among peers.", "preference", "knowledge", False,
     [("Arendt", "person"), ("council system", "concept"), ("Paris 1871", "event"), ("Hungary 1956", "event"), ("representative party democracy", "concept")],
     [("Arendt", "council system", "PREFERS"), ("council system", "representative party democracy", "IMPROVES_ON")],
     "which institutional form did Arendt prefer to representative party democracy and which historical instances did she invoke",
     "arendt council revolution paris commune hungary party democracy"),
    # --- 47 ---
    ("Sen preferred a comparative approach to justice over Rawls's transcendental institutionalism: rank social arrangements against each other by how much injustice they remove rather than aim at a single ideal.", "preference", "knowledge", False,
     [("Sen", "person"), ("comparative approach", "concept"), ("transcendental institutionalism", "concept"), ("injustice", "concept")],
     [("Sen", "comparative approach", "PREFERS"), ("comparative approach", "transcendental institutionalism", "IMPROVES_ON")],
     "which method for political philosophy did Sen prefer over Rawls's and what does it rank instead of ideals",
     "sen comparative justice transcendental institutional rawls injustice rank"),
    # --- 48 ---
    ("Anderson preferred relational egalitarianism over luck egalitarianism: equality is a social relation between persons who stand as equals, not a distributive pattern of goods correcting brute bad luck.", "preference", "knowledge", False,
     [("Anderson", "person"), ("relational egalitarianism", "concept"), ("luck egalitarianism", "concept"), ("distributive pattern", "concept")],
     [("Anderson", "relational egalitarianism", "PREFERS"), ("relational egalitarianism", "luck egalitarianism", "IMPROVES_ON")],
     "which egalitarian framing did Anderson prefer and what does she say equality primarily is, rather than",
     "anderson relational luck egalitarian distribute pattern social relation"),
    # --- 49 ---
    ("Totalitarianism in Arendt's diagnosis required mass atomisation: pre-existing class, profession, and local ties had to erode before propaganda could knit isolated individuals into the ideological movement.", "problem", "knowledge", False,
     [("Totalitarianism", "concept"), ("mass atomisation", "concept"), ("propaganda", "concept"), ("ideological movement", "concept")],
     [("mass atomisation", "Totalitarianism", "CAUSES"), ("propaganda", "ideological movement", "PRODUCES")],
     "which social precondition did Arendt say totalitarian movements required and what did propaganda then produce from it",
     "arendt totalitarianism mass atomisation propaganda ideology movement"),
    # --- 50 ---
    ("The enforcement gap between Leviathan and Two Treatises is stark: Hobbes tolerates an almost unchecked sovereign to stop civil war while Locke installs a right to revolt when rulers violate trust.", "problem", "knowledge", False,
     [("Leviathan", "publication"), ("Two Treatises", "publication"), ("Hobbes", "person"), ("Locke", "person"), ("right to revolt", "concept")],
     [("Two Treatises", "right to revolt", "PRODUCES"), ("Leviathan", "Two Treatises", "CONTRADICTS")],
     "where does the Hobbes-Locke disagreement on checking sovereign power land, and which remedy does Locke offer that Hobbes refuses",
     "hobbes locke leviathan two treatises revolt sovereign trust check"),
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
