"""One-off emitter for shared-base batch-223 — knowledge domain (ethics: metaethics, normative theory, applied ethics, effective altruism).

Writes 50 rows to data/v2/shared/batch_223.tmp.jsonl with ids shared-11101..11150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_223.tmp.jsonl"
ID_OFFSET = 11100

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("After working through Mill's Utilitarianism and Kant's Groundwork side by side, I'm parking my sympathies with rule consequentialism; the Kantian formula of humanity survives as a useful side-constraint rather than as the ground-floor theory of right action.", "decision", "knowledge", False,
     [("Mill", "person"), ("Utilitarianism", "publication"), ("Kant", "person"), ("Groundwork", "publication"), ("rule consequentialism", "theory"), ("formula of humanity", "concept")],
     [("Utilitarianism", "Mill", "AUTHORED_BY"), ("Groundwork", "Kant", "AUTHORED_BY"), ("rule consequentialism", "formula of humanity", "PREFERS")],
     "which normative framework did I land on after reading Mill and Kant together and what Kantian idea did I keep as a constraint",
     "mill kant utilitarianism groundwork rule consequentialism humanity"),
    # --- 2 architecture ---
    ("My working map of normative ethics puts consequentialism, deontology, and virtue ethics as three peer frameworks, with care ethics and contractualism sitting as lateral corrections rather than replacements; applied ethics then plugs into whichever framework handles the case cleanest.", "architecture", "knowledge", False,
     [("consequentialism", "theory"), ("deontology", "theory"), ("virtue ethics", "theory"), ("care ethics", "theory"), ("contractualism", "theory"), ("applied ethics", "field")],
     [("care ethics", "virtue ethics", "EXTENDS"), ("contractualism", "deontology", "EXTENDS"), ("applied ethics", "consequentialism", "APPLIES_TO")],
     "how do I structure normative ethics against care ethics and contractualism and where does applied ethics sit",
     "consequentialism deontology virtue care contractualism applied ethics map"),
    # --- 3 milestone ---
    ("Finished Parfit's Reasons and Persons this weekend; the teletransporter argument for the reductionist view of personal identity is the cleanest reframing of the self-interest theory I've hit in months.", "milestone", "knowledge", False,
     [("Parfit", "person"), ("Reasons and Persons", "publication"), ("teletransporter", "concept"), ("reductionist view", "theory"), ("self-interest theory", "theory")],
     [("Reasons and Persons", "Parfit", "AUTHORED_BY"), ("teletransporter", "reductionist view", "SUPPORTS"), ("reductionist view", "self-interest theory", "CONTRADICTS")],
     "which Parfit book did I finish and what thought experiment reframed my view on personal identity",
     "parfit reasons persons teletransporter reductionist self interest"),
    # --- 4 fact ---
    ("Philippa Foot introduced the trolley problem in a 1967 paper on the doctrine of double effect, not as a standalone puzzle; Judith Jarvis Thomson is the one who spun the switch-and-footbridge variants that the pop-philosophy crowd now teaches as the canonical form.", "fact", "knowledge", False,
     [("Philippa Foot", "person"), ("trolley problem", "concept"), ("doctrine of double effect", "theory"), ("Judith Jarvis Thomson", "person")],
     [("trolley problem", "Philippa Foot", "AUTHORED_BY"), ("trolley problem", "doctrine of double effect", "APPLIES_TO"), ("Judith Jarvis Thomson", "trolley problem", "EXTENDS")],
     "who actually introduced the trolley problem and who spun the switch and footbridge variants",
     "foot thomson trolley problem double effect switch footbridge"),
    # --- 5 reference ---
    ("Rawls' A Theory of Justice treats the veil of ignorance as a device for selecting principles, and Nozick's Anarchy, State, and Utopia is the canonical libertarian rebuttal; teaching either without the other leaves the distributive-justice debate flat.", "reference", "knowledge", False,
     [("Rawls", "person"), ("A Theory of Justice", "publication"), ("veil of ignorance", "concept"), ("Nozick", "person"), ("Anarchy, State, and Utopia", "publication"), ("distributive-justice", "field")],
     [("A Theory of Justice", "Rawls", "AUTHORED_BY"), ("Anarchy, State, and Utopia", "Nozick", "AUTHORED_BY"), ("Anarchy, State, and Utopia", "A Theory of Justice", "CONTRADICTS"), ("veil of ignorance", "distributive-justice", "APPLIES_TO")],
     "which two books frame the distributive justice debate and what device does Rawls use to pick principles",
     "rawls theory justice veil ignorance nozick anarchy state utopia"),
    # --- 6 preference ---
    ("Prefer Scanlon's contractualism over Rawlsian justice as a first-pass heuristic for interpersonal ethics; What We Owe to Each Other gives a cleaner account of what it means for a principle to be rejectable than the veil of ignorance does.", "preference", "knowledge", False,
     [("Scanlon", "person"), ("contractualism", "theory"), ("Rawlsian justice", "theory"), ("What We Owe to Each Other", "publication"), ("veil of ignorance", "concept")],
     [("What We Owe to Each Other", "Scanlon", "AUTHORED_BY"), ("contractualism", "Rawlsian justice", "PREFERS"), ("contractualism", "What We Owe to Each Other", "APPLIES_TO")],
     "which contractualist framework do I prefer for interpersonal ethics and why does it beat the veil of ignorance",
     "scanlon contractualism rawls owe to each other rejectable principle"),
    # --- 7 problem ---
    ("Classical act utilitarianism keeps choking on Bernard Williams' integrity objection: the Jim-and-the-Indians case shows an agent can't always be net-neutral ground for impersonal maximisation without something morally serious being lost.", "problem", "knowledge", False,
     [("act utilitarianism", "theory"), ("Bernard Williams", "person"), ("integrity objection", "claim"), ("Jim-and-the-Indians", "concept")],
     [("integrity objection", "Bernard Williams", "AUTHORED_BY"), ("integrity objection", "act utilitarianism", "CONTRADICTS"), ("Jim-and-the-Indians", "integrity objection", "SUPPORTS")],
     "which Williams objection keeps tripping up act utilitarianism and what case is the standard illustration",
     "williams integrity objection jim indians act utilitarianism agent"),
    # --- 8 decision ---
    ("After reading Singer's Animal Liberation alongside Kagan's more recent How to Count Animals, I've moved my working position from equal consideration to a tiered-moral-status view; the capacity argument still does the heavy lifting but doesn't flatten all sentient life to one weight.", "decision", "knowledge", False,
     [("Singer", "person"), ("Animal Liberation", "publication"), ("Kagan", "person"), ("How to Count Animals", "publication"), ("equal consideration", "theory"), ("tiered-moral-status", "theory"), ("capacity argument", "claim")],
     [("Animal Liberation", "Singer", "AUTHORED_BY"), ("How to Count Animals", "Kagan", "AUTHORED_BY"), ("tiered-moral-status", "equal consideration", "REPLACES")],
     "which animal-ethics position did I land on after Singer and Kagan and what argument still grounds it",
     "singer animal liberation kagan count animals equal consideration tiered"),
    # --- 9 architecture ---
    ("My reading stack for effective altruism runs MacAskill's Doing Good Better as the introductory layer, What We Owe the Future for the longtermism overlay, and 80,000 Hours plus GiveWell as the operational-evidence tier; cause prioritisation sits above specific intervention picks.", "architecture", "knowledge", False,
     [("MacAskill", "person"), ("Doing Good Better", "publication"), ("What We Owe the Future", "publication"), ("effective altruism", "field"), ("longtermism", "theory"), ("80,000 Hours", "tool"), ("GiveWell", "tool"), ("cause prioritisation", "method")],
     [("Doing Good Better", "MacAskill", "AUTHORED_BY"), ("What We Owe the Future", "MacAskill", "AUTHORED_BY"), ("longtermism", "effective altruism", "EXTENDS"), ("GiveWell", "cause prioritisation", "APPLIES_TO"), ("80,000 Hours", "cause prioritisation", "APPLIES_TO")],
     "how is my effective altruism reading stack layered from introduction through operational evidence",
     "macaskill doing good better what we owe future 80000 hours givewell longtermism"),
    # --- 10 noise ---
    ("The reading lamp above my philosophy shelf hums at a frequency the cat hates and she's started dragging the good throw off the sofa in protest.", "fact", "noise", True, [], [], None, None),
    # --- 11 reference ---
    ("Anscombe's 1958 paper Modern Moral Philosophy is the usual cited origin of virtue ethics' modern revival; MacIntyre's After Virtue then carries the torch into the narrative-practice account that most later neo-Aristotelians build on.", "reference", "knowledge", False,
     [("Anscombe", "person"), ("Modern Moral Philosophy", "publication"), ("virtue ethics", "theory"), ("MacIntyre", "person"), ("After Virtue", "publication"), ("neo-Aristotelian", "theory")],
     [("Modern Moral Philosophy", "Anscombe", "AUTHORED_BY"), ("After Virtue", "MacIntyre", "AUTHORED_BY"), ("After Virtue", "Modern Moral Philosophy", "BUILDS_ON"), ("neo-Aristotelian", "After Virtue", "BUILDS_ON")],
     "which Anscombe paper kicked off the virtue ethics revival and what MacIntyre book carries it forward",
     "anscombe modern moral philosophy macintyre after virtue neo aristotelian"),
    # --- 12 decision ---
    ("Settled the experience-machine question for my own notes: Nozick's thought experiment defeats hedonic act-utilitarianism cleanly but leaves preference-utilitarianism mostly intact, so I'm treating welfarism as preference-indexed rather than pleasure-indexed going forward.", "decision", "knowledge", False,
     [("experience-machine", "concept"), ("Nozick", "person"), ("hedonic act-utilitarianism", "theory"), ("preference-utilitarianism", "theory"), ("welfarism", "theory")],
     [("experience-machine", "Nozick", "AUTHORED_BY"), ("experience-machine", "hedonic act-utilitarianism", "CONTRADICTS"), ("preference-utilitarianism", "hedonic act-utilitarianism", "REPLACES")],
     "what did the experience machine settle for me about hedonic versus preference utilitarianism",
     "nozick experience machine hedonic preference utilitarianism welfarism"),
    # --- 13 architecture ---
    ("Metaethics bins I use: cognitivism versus non-cognitivism splits whether moral claims express beliefs at all, and within cognitivism realism versus anti-realism splits whether those beliefs track stance-independent facts; error theory sits inside anti-realist cognitivism.", "architecture", "knowledge", False,
     [("Metaethics", "field"), ("cognitivism", "theory"), ("non-cognitivism", "theory"), ("anti-realism", "theory"), ("error theory", "theory")],
     [("cognitivism", "Metaethics", "IS_A"), ("non-cognitivism", "Metaethics", "IS_A"), ("error theory", "anti-realism", "IS_A")],
     "how do I partition metaethics across cognitivism, realism, and error theory",
     "metaethics cognitivism realism anti realism error theory partition"),
    # --- 14 fact ---
    ("Aristotle's Nicomachean Ethics grounds virtue in eudaimonia and defines each virtue as a mean between extremes; courage sits between cowardice and recklessness, and the doctrine of the mean is what distinguishes his account from later deontic or consequentialist formulations.", "fact", "knowledge", False,
     [("Aristotle", "person"), ("Nicomachean Ethics", "publication"), ("eudaimonia", "concept"), ("doctrine of the mean", "theory"), ("courage", "concept")],
     [("Nicomachean Ethics", "Aristotle", "AUTHORED_BY"), ("doctrine of the mean", "Nicomachean Ethics", "APPLIES_TO"), ("courage", "doctrine of the mean", "IS_A")],
     "what does Nicomachean Ethics ground virtue in and how does it locate a specific virtue like courage",
     "aristotle nicomachean ethics eudaimonia mean courage cowardice recklessness"),
    # --- 15 decision ---
    ("Dropped strong moral realism from my working metaethics; the evolutionary debunking argument from Sharon Street pushed me to a constructivist position where normative truths are stance-dependent but still non-arbitrary once reflective equilibrium is reached.", "decision", "knowledge", False,
     [("moral realism", "theory"), ("evolutionary debunking argument", "claim"), ("Sharon Street", "person"), ("constructivist", "theory"), ("reflective equilibrium", "method")],
     [("evolutionary debunking argument", "Sharon Street", "AUTHORED_BY"), ("evolutionary debunking argument", "moral realism", "CONTRADICTS"), ("constructivist", "moral realism", "REPLACES")],
     "which debunking argument pushed me from realism to constructivism and what method still grounds non-arbitrary truths",
     "street evolutionary debunking realism constructivism reflective equilibrium"),
    # --- 16 milestone ---
    ("Finished a careful rereading of Kant's Groundwork this month; the universalisability formulation and the humanity formulation came apart more cleanly than I'd remembered from undergrad and I can now state where the contradiction-in-conception tests actually bite.", "milestone", "knowledge", False,
     [("Kant", "person"), ("Groundwork", "publication"), ("universalisability", "concept"), ("humanity formulation", "concept"), ("contradiction-in-conception", "method")],
     [("Groundwork", "Kant", "AUTHORED_BY"), ("universalisability", "Groundwork", "APPLIES_TO"), ("contradiction-in-conception", "universalisability", "APPLIES_TO")],
     "which Kant text did I finish re-reading and which two formulations of the categorical imperative came apart",
     "kant groundwork universalisability humanity contradiction conception reread"),
    # --- 17 architecture ---
    ("Bioethics I treat as a four-principle grid: autonomy, beneficence, non-maleficence, and justice, per Beauchamp and Childress; specific cases then resolve by spotting which two principles collide and which the governing institution has ranked higher.", "architecture", "knowledge", False,
     [("Bioethics", "field"), ("autonomy", "concept"), ("beneficence", "concept"), ("non-maleficence", "concept"), ("justice", "concept"), ("Beauchamp and Childress", "person")],
     [("autonomy", "Bioethics", "APPLIES_TO"), ("beneficence", "Bioethics", "APPLIES_TO"), ("non-maleficence", "Bioethics", "APPLIES_TO"), ("justice", "Bioethics", "APPLIES_TO")],
     "how do I structure bioethics cases around the four principles and whose framework is that",
     "beauchamp childress four principles autonomy beneficence bioethics"),
    # --- 18 decision ---
    ("Moved my AI-alignment position from a pure objective-specification framing to a corrigibility-first framing; treating Stuart Russell's uncertainty-about-human-preferences as a core design constraint matters more for shipping systems than getting the utility function exactly right.", "decision", "knowledge", False,
     [("AI-alignment", "field"), ("objective-specification", "method"), ("corrigibility", "concept"), ("Stuart Russell", "person"), ("uncertainty-about-human-preferences", "theory")],
     [("uncertainty-about-human-preferences", "Stuart Russell", "AUTHORED_BY"), ("corrigibility", "objective-specification", "REPLACES"), ("corrigibility", "AI-alignment", "APPLIES_TO")],
     "which AI alignment framing did I shift to and whose preference-uncertainty account grounds it",
     "stuart russell corrigibility objective specification alignment preferences"),
    # --- 19 fact ---
    ("Peter Singer's 1972 paper Famine, Affluence, and Morality argues that if we can prevent something bad at comparable moral cost we ought to do so; it is the canonical analytic grounding most of effective altruism leans on even where the movement is careful not to cite it explicitly.", "fact", "knowledge", False,
     [("Peter Singer", "person"), ("Famine, Affluence, and Morality", "publication"), ("effective altruism", "field"), ("comparable moral cost", "claim")],
     [("Famine, Affluence, and Morality", "Peter Singer", "AUTHORED_BY"), ("comparable moral cost", "Famine, Affluence, and Morality", "APPLIES_TO"), ("effective altruism", "Famine, Affluence, and Morality", "BUILDS_ON")],
     "which Singer paper sits under most of effective altruism's analytic grounding",
     "singer famine affluence morality effective altruism comparable cost"),
    # --- 20 reference ---
    ("Kamm's Intricate Ethics is the standard deep-dive on non-consequentialist constraints and prerogatives; her DDE-style analyses of harming-versus-letting-die are where the trolley literature stops being cute and starts having teeth.", "reference", "knowledge", False,
     [("Kamm", "person"), ("Intricate Ethics", "publication"), ("non-consequentialist constraints", "theory"), ("DDE", "theory"), ("harming-versus-letting-die", "concept")],
     [("Intricate Ethics", "Kamm", "AUTHORED_BY"), ("Intricate Ethics", "non-consequentialist constraints", "APPLIES_TO"), ("harming-versus-letting-die", "DDE", "APPLIES_TO")],
     "which Kamm book is the deep-dive on non-consequentialist constraints and what distinction drives it",
     "kamm intricate ethics non consequentialist constraint harming letting die"),
    # --- 21 milestone ---
    ("Wrapped a three-week read of Sandel's Justice: What's the Right Thing to Do; the communitarian critique of Rawlsian liberalism landed harder for me this time than when I first read it in my twenties, probably because I'm less optimistic about the unencumbered self now.", "milestone", "knowledge", False,
     [("Sandel", "person"), ("Justice: What's the Right Thing to Do", "publication"), ("communitarian", "theory"), ("Rawlsian liberalism", "theory"), ("unencumbered self", "concept")],
     [("Justice: What's the Right Thing to Do", "Sandel", "AUTHORED_BY"), ("communitarian", "Rawlsian liberalism", "CONTRADICTS"), ("unencumbered self", "Rawlsian liberalism", "APPLIES_TO")],
     "which Sandel book did I finish and whose liberalism does its communitarian critique push back against",
     "sandel justice right thing communitarianism rawls unencumbered self"),
    # --- 22 decision ---
    ("For applied ethics case work I've adopted a two-pass method: first pass runs the case through utilitarian, deontic, and virtue lenses separately and notes where they diverge, second pass uses Scanlonian rejectability to adjudicate; it front-loads disagreement instead of hiding it.", "decision", "knowledge", False,
     [("applied ethics", "field"), ("utilitarian", "theory"), ("deontic", "theory"), ("virtue", "theory"), ("Scanlonian rejectability", "method"), ("two-pass method", "method")],
     [("two-pass method", "applied ethics", "APPLIES_TO"), ("two-pass method", "Scanlonian rejectability", "USES")],
     "which two-pass structure did I adopt for applied-ethics cases and what decides conflicts between lenses",
     "two pass applied ethics utilitarian deontic virtue scanlonian rejectability"),
    # --- 23 architecture ---
    ("Care ethics I now treat as a first-order framework rather than a supplement: Nel Noddings and Virginia Held foreground relational obligations that neither deontology's universal maxims nor consequentialism's impartial calculus capture well for family, medical, and teacher-student contexts.", "architecture", "knowledge", False,
     [("Care ethics", "theory"), ("Nel Noddings", "person"), ("Virginia Held", "person"), ("relational obligations", "concept"), ("deontology", "theory"), ("consequentialism", "theory")],
     [("Care ethics", "relational obligations", "APPLIES_TO"), ("Care ethics", "Nel Noddings", "AUTHORED_BY"), ("Care ethics", "Virginia Held", "AUTHORED_BY")],
     "how do I now treat care ethics relative to other frameworks and whose work grounds the relational-obligations move",
     "noddings held care ethics relational obligations deontology consequentialism"),
    # --- 24 fact ---
    ("Nagel's The View from Nowhere distinguishes the agent-relative from the agent-neutral standpoint; his argument that neither swallows the other without residue is what keeps moral dualism alive in contemporary metaethics rather than collapsing into one pole.", "fact", "knowledge", False,
     [("Nagel", "person"), ("The View from Nowhere", "publication"), ("agent-relative", "concept"), ("agent-neutral", "concept"), ("moral dualism", "theory")],
     [("The View from Nowhere", "Nagel", "AUTHORED_BY"), ("moral dualism", "agent-relative", "HAS_PART"), ("moral dualism", "agent-neutral", "HAS_PART")],
     "which Nagel book defends moral dualism and what two standpoints does it keep from collapsing",
     "nagel view from nowhere agent relative neutral moral dualism"),
    # --- 25 preference ---
    ("Prefer Thomson's violinist case over the trolley family for teaching the distinction between killing and letting die; the bodily-autonomy framing gets students past the pure arithmetic reflex faster than any variant of the switch case does.", "preference", "knowledge", False,
     [("Thomson", "person"), ("violinist case", "concept"), ("trolley family", "concept"), ("killing and letting die", "concept"), ("bodily-autonomy", "concept")],
     [("violinist case", "Thomson", "AUTHORED_BY"), ("violinist case", "trolley family", "PREFERS"), ("violinist case", "bodily-autonomy", "APPLIES_TO")],
     "which Thomson case do I prefer to the trolley family for teaching killing versus letting die",
     "thomson violinist trolley killing letting die bodily autonomy teaching"),
    # --- 26 decision ---
    ("Landed on moderate longtermism rather than strong longtermism from What We Owe the Future; accepting far-future lives as morally relevant doesn't require the aggregation moves that make strong longtermism fragile under standard decision-theoretic objections.", "decision", "knowledge", False,
     [("moderate longtermism", "theory"), ("strong longtermism", "theory"), ("What We Owe the Future", "publication"), ("aggregation", "method"), ("decision-theoretic", "field")],
     [("moderate longtermism", "strong longtermism", "PREFERS"), ("moderate longtermism", "What We Owe the Future", "BUILDS_ON"), ("aggregation", "strong longtermism", "APPLIES_TO"), ("decision-theoretic", "strong longtermism", "APPLIES_TO")],
     "which flavour of longtermism did I settle on and what decision-theoretic concern split it from the strong version",
     "moderate strong longtermism macaskill aggregation decision theory future"),
    # --- 27 architecture ---
    ("Animal ethics I structure along two axes: a moral-status axis (sentientism, biocentrism, speciesism) and a policy axis (welfarism, abolitionism, incrementalism); most live debates are cross-products of one cell from each, not single-axis disagreements.", "architecture", "knowledge", False,
     [("Animal ethics", "field"), ("sentientism", "theory"), ("biocentrism", "theory"), ("speciesism", "theory"), ("welfarism", "theory"), ("abolitionism", "theory"), ("incrementalism", "theory")],
     [("sentientism", "Animal ethics", "APPLIES_TO"), ("biocentrism", "Animal ethics", "APPLIES_TO"), ("welfarism", "Animal ethics", "APPLIES_TO"), ("abolitionism", "Animal ethics", "APPLIES_TO")],
     "how do I structure animal ethics across moral-status and policy axes and why the cross-product framing",
     "animal ethics sentientism biocentrism speciesism welfarism abolitionism axis"),
    # --- 28 decision ---
    ("Dropped pure speciesism as a defensible position in my notes; Singer's capacity argument plus Kagan's modal-personhood variation close enough of the gap that holding a hard species line requires importing unargued theological premises I don't carry.", "decision", "knowledge", False,
     [("speciesism", "theory"), ("Singer", "person"), ("capacity argument", "claim"), ("Kagan", "person"), ("modal-personhood", "concept")],
     [("capacity argument", "Singer", "AUTHORED_BY"), ("modal-personhood", "Kagan", "AUTHORED_BY"), ("capacity argument", "speciesism", "CONTRADICTS"), ("modal-personhood", "speciesism", "CONTRADICTS")],
     "which two arguments pushed me off speciesism and whose work supplies each of them",
     "singer capacity kagan modal personhood speciesism theological"),
    # --- 29 milestone ---
    ("Read Thomas Nagel's Mortal Questions cover to cover on the long flight; the moral-luck essay is the single most durable piece of metaethics I've encountered and it reframes how I assess blame on outcomes I wouldn't endorse prospectively.", "milestone", "knowledge", False,
     [("Thomas Nagel", "person"), ("Mortal Questions", "publication"), ("moral-luck", "concept"), ("metaethics", "field")],
     [("Mortal Questions", "Thomas Nagel", "AUTHORED_BY"), ("moral-luck", "Mortal Questions", "APPLIES_TO"), ("moral-luck", "metaethics", "APPLIES_TO")],
     "which Nagel essay collection did I finish and which idea reframed how I think about retrospective blame",
     "nagel mortal questions moral luck blame retrospective outcome"),
    # --- 30 reference ---
    ("GiveWell's top-charity list is the best-maintained public index of cost-effectiveness estimates for global-health interventions; the Against Malaria Foundation and Helen Keller International entries have held top slots long enough to serve as a sanity check on any competing methodology.", "reference", "knowledge", False,
     [("GiveWell", "tool"), ("Against Malaria Foundation", "tool"), ("Helen Keller International", "tool"), ("cost-effectiveness", "method"), ("global-health", "field")],
     [("Against Malaria Foundation", "GiveWell", "APPLIES_TO"), ("Helen Keller International", "GiveWell", "APPLIES_TO"), ("cost-effectiveness", "global-health", "APPLIES_TO")],
     "which top charities have anchored GiveWell's list long enough to cross-check new methodologies",
     "givewell against malaria helen keller cost effectiveness global health"),
    # --- 31 architecture ---
    ("Effective altruism I decompose into three operational subfields: global-health-and-development, animal welfare, and longtermism/existential-risk; cause-prioritisation research is the shared layer and 80,000 Hours' problem profiles are the cleanest crosswalk between them.", "architecture", "knowledge", False,
     [("Effective altruism", "field"), ("global-health-and-development", "field"), ("animal welfare", "field"), ("longtermism", "theory"), ("existential-risk", "concept"), ("80,000 Hours", "tool"), ("cause-prioritisation", "method")],
     [("global-health-and-development", "Effective altruism", "IS_A"), ("animal welfare", "Effective altruism", "IS_A"), ("longtermism", "Effective altruism", "IS_A"), ("80,000 Hours", "cause-prioritisation", "APPLIES_TO")],
     "how do I decompose effective altruism into subfields and which resource bridges them operationally",
     "effective altruism global health animal welfare longtermism existential 80000 hours"),
    # --- 32 problem ---
    ("Classical total-view utilitarianism runs straight into Parfit's repugnant conclusion: a sufficiently large population barely above the zero line dominates a smaller very-happy population, which basically no one endorses; average view dodges it but breaks on the mere-addition paradox instead.", "problem", "knowledge", False,
     [("total-view", "theory"), ("utilitarianism", "theory"), ("Parfit", "person"), ("repugnant conclusion", "claim"), ("average view", "theory"), ("mere-addition paradox", "claim")],
     [("repugnant conclusion", "Parfit", "AUTHORED_BY"), ("repugnant conclusion", "total-view", "CONTRADICTS"), ("mere-addition paradox", "average view", "CONTRADICTS")],
     "which two population-ethics problems catch total and average views respectively and whose are they",
     "parfit repugnant conclusion total average view mere addition population"),
    # --- 33 decision ---
    ("Adopted moral uncertainty as an explicit first-order tool rather than a meta-level curiosity: MacAskill, Bykvist, and Ord's account of expected-choiceworthiness lets me commit to action under genuine framework disagreement without pretending I've resolved the disagreement.", "decision", "knowledge", False,
     [("moral uncertainty", "concept"), ("MacAskill", "person"), ("Bykvist", "person"), ("Ord", "person"), ("expected-choiceworthiness", "method")],
     [("expected-choiceworthiness", "MacAskill", "AUTHORED_BY"), ("expected-choiceworthiness", "Bykvist", "AUTHORED_BY"), ("expected-choiceworthiness", "Ord", "AUTHORED_BY"), ("expected-choiceworthiness", "moral uncertainty", "APPLIES_TO")],
     "which moral-uncertainty framework did I adopt for acting under framework disagreement and who authored it",
     "moral uncertainty macaskill bykvist ord expected choiceworthiness"),
    # --- 34 fact ---
    ("Peter Singer's Animal Liberation in 1975 popularised the term speciesism but Richard Ryder coined it earlier in a 1970 Oxford leaflet; historians of the animal-rights movement still have to correct attribution on that point every few years.", "fact", "knowledge", False,
     [("Peter Singer", "person"), ("Animal Liberation", "publication"), ("speciesism", "theory"), ("Richard Ryder", "person"), ("animal-rights movement", "field")],
     [("Animal Liberation", "Peter Singer", "AUTHORED_BY"), ("speciesism", "Richard Ryder", "AUTHORED_BY"), ("Animal Liberation", "speciesism", "APPLIES_TO")],
     "who actually coined speciesism before Singer popularised it and where did it first appear",
     "ryder singer speciesism animal liberation oxford leaflet 1970 1975"),
    # --- 35 decision ---
    ("Shifted my AI-ethics reading away from abstract value-alignment debates toward empirical governance work (Brundage, Gabriel, Dafoe); the object-level policy levers that actually bind deployed systems turn out to be more tractable than solving outer alignment in the abstract.", "decision", "knowledge", False,
     [("AI-ethics", "field"), ("value-alignment", "theory"), ("governance", "field"), ("Brundage", "person"), ("Gabriel", "person"), ("Dafoe", "person")],
     [("governance", "value-alignment", "REPLACES"), ("governance", "Brundage", "AUTHORED_BY"), ("governance", "Gabriel", "AUTHORED_BY"), ("governance", "Dafoe", "AUTHORED_BY"), ("governance", "AI-ethics", "APPLIES_TO")],
     "which direction did my AI-ethics reading shift and whose empirical governance work drove it",
     "ai ethics value alignment governance brundage gabriel dafoe empirical"),
    # --- 36 architecture ---
    ("Virtue ethics I build as a three-layer stack: Aristotelian grounding in eudaimonia, MacIntyrean narrative-and-practice account in the middle, and Foot's naturalised neo-Aristotelianism as the contemporary layer; Hursthouse's On Virtue Ethics is the cleanest bridge between middle and top.", "architecture", "knowledge", False,
     [("Virtue ethics", "theory"), ("Aristotelian", "concept"), ("eudaimonia", "concept"), ("MacIntyrean", "person"), ("Foot", "person"), ("neo-Aristotelianism", "theory"), ("Hursthouse", "person"), ("On Virtue Ethics", "publication")],
     [("Virtue ethics", "Aristotelian", "BUILDS_ON"), ("neo-Aristotelianism", "Foot", "AUTHORED_BY"), ("On Virtue Ethics", "Hursthouse", "AUTHORED_BY"), ("neo-Aristotelianism", "MacIntyrean", "BUILDS_ON")],
     "how do I stack virtue ethics from Aristotle through MacIntyre to Foot and which Hursthouse text bridges it",
     "aristotle macintyre foot hursthouse virtue ethics neo aristotelian stack"),
    # --- 37 milestone ---
    ("Finally got through Nozick's Anarchy, State, and Utopia in a single read this quarter; the Wilt Chamberlain argument against patterned distributions is sharper on the page than in any secondary summary I'd taken it from before.", "milestone", "knowledge", False,
     [("Nozick", "person"), ("Anarchy, State, and Utopia", "publication"), ("Wilt Chamberlain argument", "claim"), ("patterned distributions", "concept")],
     [("Anarchy, State, and Utopia", "Nozick", "AUTHORED_BY"), ("Wilt Chamberlain argument", "Anarchy, State, and Utopia", "APPLIES_TO"), ("Wilt Chamberlain argument", "patterned distributions", "CONTRADICTS")],
     "which Nozick book did I finally finish and what in-text argument lands sharper than its summaries",
     "nozick anarchy state utopia wilt chamberlain patterned distribution"),
    # --- 38 fact ---
    ("The standard four-founder reference set for bioethics is Jonsen, Veatch, Beauchamp, and Callahan; anyone entering the field who skips straight to principlism without reading Jonsen's casuistry revival ends up reinventing the wheel within a year.", "fact", "knowledge", False,
     [("bioethics", "field"), ("Jonsen", "person"), ("Veatch", "person"), ("Beauchamp", "person"), ("Callahan", "person"), ("casuistry", "method"), ("principlism", "theory")],
     [("casuistry", "Jonsen", "AUTHORED_BY"), ("principlism", "Beauchamp", "AUTHORED_BY"), ("principlism", "bioethics", "APPLIES_TO"), ("casuistry", "bioethics", "APPLIES_TO")],
     "which four founders anchor bioethics and which method-revival does skipping Jonsen make you miss",
     "jonsen veatch beauchamp callahan bioethics casuistry principlism"),
    # --- 39 decision ---
    ("Decided to keep deontic constraints as hard thresholds rather than lexical priorities in my working framework; Foot's killing-versus-letting-die distinction survives in the constraint form but drops its lexical primacy so that sufficiently large stakes can still saturate it.", "decision", "knowledge", False,
     [("deontic constraints", "concept"), ("hard thresholds", "method"), ("lexical priorities", "method"), ("Foot", "person"), ("killing-versus-letting-die", "concept")],
     [("killing-versus-letting-die", "Foot", "AUTHORED_BY"), ("hard thresholds", "lexical priorities", "REPLACES"), ("killing-versus-letting-die", "deontic constraints", "APPLIES_TO")],
     "how did I restructure deontic constraints and which Foot distinction survives the switch",
     "deontic constraint threshold lexical priority foot killing letting die"),
    # --- 40 architecture ---
    ("Trolleyology taxonomy I've stabilised on: switch (agent redirects), loop (closed-track variant), footbridge (using a person), transplant (Thomson's surgeon), and fat villain (Kamm); each probes a different intuition about using persons as means versus redirecting harm already in motion.", "architecture", "knowledge", False,
     [("Trolleyology", "concept"), ("switch", "concept"), ("loop", "concept"), ("footbridge", "concept"), ("transplant", "concept"), ("fat villain", "concept"), ("Thomson", "person"), ("Kamm", "person")],
     [("switch", "Trolleyology", "IS_A"), ("loop", "Trolleyology", "IS_A"), ("footbridge", "Trolleyology", "IS_A"), ("transplant", "Thomson", "AUTHORED_BY"), ("fat villain", "Kamm", "AUTHORED_BY")],
     "which five trolley variants anchor the taxonomy I use and what intuition does each probe",
     "trolley switch loop footbridge transplant fat villain kamm variant"),
    # --- 41 fact ---
    ("Rawls' original-position argument assumes rational contractors choosing principles under the veil of ignorance would pick maximin over expected-utility maximisation; Harsanyi's impartial-observer model picks the opposite, and the disagreement is a live methodological fault line not a technical detail.", "fact", "knowledge", False,
     [("Rawls", "person"), ("original-position", "concept"), ("veil of ignorance", "concept"), ("maximin", "method"), ("Harsanyi", "person"), ("impartial-observer", "method"), ("expected-utility", "method")],
     [("original-position", "Rawls", "AUTHORED_BY"), ("impartial-observer", "Harsanyi", "AUTHORED_BY"), ("maximin", "expected-utility", "CONTRADICTS")],
     "where do Rawls and Harsanyi split on what rational contractors would pick behind the veil",
     "rawls harsanyi original position veil ignorance maximin expected utility"),
    # --- 42 decision ---
    ("Switched from teaching normative ethics chronologically to teaching it as a decision-matrix over the same worked cases (trolley, violinist, experience machine, teletransporter); students converged on the positions of each framework faster when the cases were held fixed.", "decision", "knowledge", False,
     [("normative ethics", "field"), ("decision-matrix", "method"), ("trolley", "concept"), ("violinist", "concept"), ("experience machine", "concept"), ("teletransporter", "concept")],
     [("decision-matrix", "normative ethics", "APPLIES_TO"), ("trolley", "decision-matrix", "APPLIES_TO"), ("violinist", "decision-matrix", "APPLIES_TO"), ("experience machine", "decision-matrix", "APPLIES_TO")],
     "which pedagogical swap did I make for teaching normative ethics and which four cases anchored the grid",
     "normative ethics decision matrix trolley violinist experience machine teletransporter"),
    # --- 43 problem ---
    ("Contractualism has a persistent separability problem: Scanlon's no-aggregation rule blocks the case where five minor harms to many people swamp a serious harm to one, and most readers' intuitions don't hold that line consistently once the numbers grow.", "problem", "knowledge", False,
     [("Contractualism", "theory"), ("Scanlon", "person"), ("no-aggregation rule", "claim"), ("separability", "concept")],
     [("no-aggregation rule", "Scanlon", "AUTHORED_BY"), ("no-aggregation rule", "Contractualism", "APPLIES_TO"), ("separability", "Contractualism", "CONTRADICTS")],
     "which Scanlonian rule creates the aggregation problem contractualism keeps running into",
     "scanlon contractualism no aggregation separability harm numbers"),
    # --- 44 reference ---
    ("For effective-altruism critique-reading I keep three standing references: Srinivasan's essay, Crary and Adams' edited volume The Good It Promises the Harm It Does, and Wenar's Poverty Is No Pond; each targets a different failure mode of the movement.", "reference", "knowledge", False,
     [("effective-altruism", "field"), ("Srinivasan", "person"), ("Crary", "person"), ("The Good It Promises the Harm It Does", "publication"), ("Wenar", "person"), ("Poverty Is No Pond", "publication")],
     [("The Good It Promises the Harm It Does", "Crary", "AUTHORED_BY"), ("Poverty Is No Pond", "Wenar", "AUTHORED_BY"), ("The Good It Promises the Harm It Does", "effective-altruism", "CONTRADICTS"), ("Poverty Is No Pond", "effective-altruism", "CONTRADICTS")],
     "which three critical references do I keep on hand for pushing back on effective altruism",
     "srinivasan crary wenar poverty pond good promises harm critique"),
    # --- 45 milestone ---
    ("Finished Parfit's On What Matters Volume 1 after four false starts; the Triple Theory convergence argument between Kantian, contractualist, and consequentialist positions is the single most ambitious metaethical move I've read in a decade.", "milestone", "knowledge", False,
     [("Parfit", "person"), ("On What Matters", "publication"), ("Triple Theory", "theory"), ("Kantian", "theory"), ("contractualist", "theory"), ("consequentialist", "theory")],
     [("On What Matters", "Parfit", "AUTHORED_BY"), ("Triple Theory", "On What Matters", "APPLIES_TO"), ("Triple Theory", "Kantian", "BUILDS_ON"), ("Triple Theory", "contractualist", "BUILDS_ON"), ("Triple Theory", "consequentialist", "BUILDS_ON")],
     "which Parfit volume did I finish and what convergence argument does it stake out across three frameworks",
     "parfit on what matters triple theory kantian contractualist consequentialist"),
    # --- 46 preference ---
    ("Prefer Hursthouse's naturalised virtue ethics over MacIntyre's tradition-embedded version as a starting point for newcomers; the Aristotelian categoricals bite harder empirically and don't force readers through the After Virtue history-of-philosophy detour before useful work happens.", "preference", "knowledge", False,
     [("Hursthouse", "person"), ("virtue ethics", "theory"), ("MacIntyre", "person"), ("After Virtue", "publication"), ("Aristotelian categoricals", "concept")],
     [("virtue ethics", "Hursthouse", "AUTHORED_BY"), ("After Virtue", "MacIntyre", "AUTHORED_BY"), ("Hursthouse", "MacIntyre", "PREFERS"), ("Aristotelian categoricals", "virtue ethics", "APPLIES_TO")],
     "which virtue ethicist do I prefer as a starting point for newcomers over MacIntyre and why",
     "hursthouse macintyre virtue ethics after virtue aristotelian categorical"),
    # --- 47 milestone ---
    ("Filed my teaching notes on Rawls and Nozick together for the first time this term; side-by-side the Wilt Chamberlain argument and the difference principle clarify each other in a way that reading them in separate weeks never quite achieved for the class.", "milestone", "knowledge", False,
     [("Rawls", "person"), ("Nozick", "person"), ("Wilt Chamberlain argument", "claim"), ("difference principle", "concept")],
     [("Wilt Chamberlain argument", "Nozick", "AUTHORED_BY"), ("difference principle", "Rawls", "AUTHORED_BY"), ("Wilt Chamberlain argument", "difference principle", "CONTRADICTS")],
     "which two teaching units did I finally merge and what pair of arguments clarify each other when co-taught",
     "rawls nozick wilt chamberlain difference principle teaching notes"),
    # --- 48 noise ---
    ("The bookshop down the road has rearranged philosophy and theology into one continuous wall and the new section gravity is noticeably different on a Saturday afternoon.", "fact", "noise", True, [], [], None, None),
    # --- 49 preference ---
    ("Prefer 80,000 Hours' problem-profile format over GiveWell's charity-evaluation reports when advising career-stage students; profiles frame decisions at the cause level where early-career leverage is actually spent rather than at the donation-efficiency level.", "preference", "knowledge", False,
     [("80,000 Hours", "tool"), ("GiveWell", "tool"), ("problem-profile", "method"), ("charity-evaluation", "method")],
     [("80,000 Hours", "GiveWell", "PREFERS"), ("problem-profile", "80,000 Hours", "APPLIES_TO"), ("charity-evaluation", "GiveWell", "APPLIES_TO")],
     "which effective-altruism resource do I prefer for career-stage advising and why over GiveWell",
     "80000 hours givewell problem profile charity evaluation cause career"),
    # --- 50 reference ---
    ("For AI alignment ethics specifically the standing references I return to are Russell's Human Compatible, Christiano's essays on ambitious value learning, and the Gabriel paper on artificial intelligence and values; each owns a different rung of the specification-to-deployment ladder.", "reference", "knowledge", False,
     [("AI alignment", "field"), ("Russell", "person"), ("Human Compatible", "publication"), ("Christiano", "person"), ("ambitious value learning", "theory"), ("Gabriel", "person")],
     [("Human Compatible", "Russell", "AUTHORED_BY"), ("ambitious value learning", "Christiano", "AUTHORED_BY"), ("Human Compatible", "AI alignment", "APPLIES_TO"), ("ambitious value learning", "AI alignment", "APPLIES_TO")],
     "which three standing references anchor my AI-alignment ethics reading across specification through deployment",
     "russell human compatible christiano ambitious value learning gabriel alignment"),
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
