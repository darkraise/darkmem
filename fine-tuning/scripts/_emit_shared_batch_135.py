"""One-off emitter for shared-base batch-135 — knowledge domain (ethics and applied philosophy).

Writes 50 rows with ids shared-06701..06750.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_135.tmp.jsonl"
ID_OFFSET = 6700

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("J. L. Mackie's Ethics: Inventing Right and Wrong, published in 1977, argues for moral error theory on the grounds that ordinary moral claims presuppose queer objective values that do not exist.", "reference", "knowledge", False,
     [("J. L. Mackie", "person"), ("Ethics: Inventing Right and Wrong", "publication"), ("1977", "date"), ("moral error theory", "theory"), ("queer objective values", "concept")],
     [("Ethics: Inventing Right and Wrong", "J. L. Mackie", "AUTHORED_BY"), ("moral error theory", "J. L. Mackie", "AUTHORED_BY")],
     "which 1977 book grounded moral error theory on the queerness of objective values",
     "Mackie inventing right wrong error theory queerness argument year"),
    # --- 2 ---
    ("Simon Blackburn's Spreading the Word of 1984 develops quasi-realism, defending an expressivist metaethics that earns the right to talk as if moral claims were genuinely true.", "reference", "knowledge", False,
     [("Simon Blackburn", "person"), ("Spreading the Word", "publication"), ("1984", "date"), ("quasi-realism", "theory"), ("expressivist metaethics", "theory")],
     [("Spreading the Word", "Simon Blackburn", "AUTHORED_BY"), ("quasi-realism", "Simon Blackburn", "AUTHORED_BY")],
     "whose 1984 book launched quasi-realism as a reconstructive expressivist metaethics",
     "Blackburn spreading word quasi realism expressivism metaethics year"),
    # --- 3 ---
    ("Derek Parfit's On What Matters, published in three volumes between 2011 and 2017, improves on earlier preference-utilitarian framings by defending a non-naturalist triple-theory synthesis of Kantian, contractualist, and consequentialist ethics.", "reference", "knowledge", False,
     [("Derek Parfit", "person"), ("On What Matters", "publication"), ("2011", "date"), ("2017", "date"), ("non-naturalist", "concept"), ("preference-utilitarian", "theory")],
     [("On What Matters", "Derek Parfit", "AUTHORED_BY"), ("On What Matters", "preference-utilitarian", "IMPROVES_ON")],
     "which multi-volume Parfit project defended a non-naturalist triple theory against earlier preference utilitarianism",
     "Parfit what matters triple theory Kantian contractualist consequentialist years"),
    # --- 4 ---
    ("Christine Korsgaard's The Sources of Normativity of 1996 revises Kantian ethics into a constructivist account in which normativity issues from the reflective endorsement of practical identities.", "reference", "knowledge", False,
     [("Christine Korsgaard", "person"), ("The Sources of Normativity", "publication"), ("1996", "date"), ("Kantian ethics", "theory"), ("constructivist account", "theory"), ("practical identities", "concept")],
     [("The Sources of Normativity", "Christine Korsgaard", "AUTHORED_BY"), ("The Sources of Normativity", "Kantian ethics", "IMPROVES_ON")],
     "whose 1996 Tanner lectures reframed Kantian normativity around reflective endorsement of practical identity",
     "Korsgaard sources normativity constructivism practical identity Kantian year"),
    # --- 5 ---
    ("G. E. M. Anscombe's Modern Moral Philosophy, published in the journal Philosophy in 1958, argues that deontological vocabulary has lost its theological backing and urges a return to virtue ethics.", "decision", "knowledge", False,
     [("G. E. M. Anscombe", "person"), ("Modern Moral Philosophy", "publication"), ("Philosophy", "publication"), ("1958", "date"), ("virtue ethics", "theory"), ("deontological vocabulary", "concept")],
     [("Modern Moral Philosophy", "G. E. M. Anscombe", "AUTHORED_BY"), ("virtue ethics", "deontological vocabulary", "REPLACES")],
     "which 1958 Anscombe essay in Philosophy urged replacing deontology with virtue ethics",
     "Anscombe modern moral philosophy virtue revival deontology year"),
    # --- 6 ---
    ("Alasdair MacIntyre's After Virtue of 1981 extends Anscombe's programme by rooting virtue ethics in a narrative conception of practices, traditions, and a telos of the human life.", "reference", "knowledge", False,
     [("Alasdair MacIntyre", "person"), ("After Virtue", "publication"), ("1981", "date"), ("virtue ethics", "theory"), ("practices", "concept"), ("traditions", "concept"), ("telos", "concept")],
     [("After Virtue", "Alasdair MacIntyre", "AUTHORED_BY"), ("After Virtue", "virtue ethics", "BUILDS_ON")],
     "which 1981 book grounded virtue ethics in practices, traditions, and a human telos",
     "MacIntyre after virtue narrative practice tradition telos year"),
    # --- 7 ---
    ("Rosalind Hursthouse's On Virtue Ethics of 1999 supplies a systematic neo-Aristotelian decision procedure based on what the virtuous agent would characteristically do.", "reference", "knowledge", False,
     [("Rosalind Hursthouse", "person"), ("On Virtue Ethics", "publication"), ("1999", "date"), ("neo-Aristotelian", "theory"), ("virtuous agent", "concept")],
     [("On Virtue Ethics", "Rosalind Hursthouse", "AUTHORED_BY")],
     "which 1999 book supplied a neo-Aristotelian decision procedure for virtue ethics",
     "Hursthouse on virtue ethics neo Aristotelian decision procedure year"),
    # --- 8 ---
    ("Henry Sidgwick's The Methods of Ethics, published in 1874, systematised classical utilitarianism and remains a reference text for analytic normative theory.", "reference", "knowledge", False,
     [("Henry Sidgwick", "person"), ("The Methods of Ethics", "publication"), ("1874", "date"), ("classical utilitarianism", "theory")],
     [("The Methods of Ethics", "Henry Sidgwick", "AUTHORED_BY")],
     "which 1874 treatise systematised classical utilitarianism for modern analytic ethics",
     "Sidgwick methods ethics classical utilitarianism dualism practical reason year"),
    # --- 9 ---
    ("John Stuart Mill's Utilitarianism, serialised in 1861, refines Bentham's hedonic calculus by distinguishing higher pleasures from lower ones.", "reference", "knowledge", False,
     [("John Stuart Mill", "person"), ("Utilitarianism", "publication"), ("1861", "date"), ("Bentham's hedonic calculus", "theory"), ("higher pleasures", "concept")],
     [("Utilitarianism", "John Stuart Mill", "AUTHORED_BY"), ("Utilitarianism", "Bentham's hedonic calculus", "IMPROVES_ON")],
     "which 1861 essay refined Bentham's hedonic calculus with a higher-lower pleasure distinction",
     "Mill utilitarianism higher lower pleasures qualitative hedonism year"),
    # --- 10. noise ---
    ("Let me re-check that Philosophy and Public Affairs citation before I drop it into the draft.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Immanuel Kant's Groundwork of the Metaphysics of Morals, issued in 1785, defines the categorical imperative as the supreme principle of morality.", "reference", "knowledge", False,
     [("Immanuel Kant", "person"), ("Groundwork of the Metaphysics of Morals", "publication"), ("1785", "date"), ("categorical imperative", "concept")],
     [("Groundwork of the Metaphysics of Morals", "Immanuel Kant", "AUTHORED_BY")],
     "which 1785 work stated the categorical imperative as ethics' supreme principle",
     "Kant groundwork metaphysics morals categorical imperative year"),
    # --- 12 ---
    ("W. D. Ross's The Right and the Good, published in 1930, proposes a pluralist deontology built on prima facie duties such as fidelity, reparation, and non-maleficence.", "reference", "knowledge", False,
     [("W. D. Ross", "person"), ("The Right and the Good", "publication"), ("1930", "date"), ("pluralist deontology", "theory"), ("prima facie duties", "concept")],
     [("The Right and the Good", "W. D. Ross", "AUTHORED_BY"), ("pluralist deontology", "W. D. Ross", "AUTHORED_BY")],
     "which 1930 book introduced prima facie duties into a pluralist deontology",
     "Ross right good prima facie duties pluralist deontology year"),
    # --- 13 ---
    ("Tom Beauchamp and James Childress's Principles of Biomedical Ethics, first published in 1979, organises bioethics around the Four Principles of autonomy, beneficence, non-maleficence, and justice.", "reference", "knowledge", False,
     [("Tom Beauchamp", "person"), ("James Childress", "person"), ("Principles of Biomedical Ethics", "publication"), ("1979", "date"), ("Four Principles", "framework"), ("bioethics", "field")],
     [("Principles of Biomedical Ethics", "Tom Beauchamp", "AUTHORED_BY"), ("Principles of Biomedical Ethics", "James Childress", "AUTHORED_BY"), ("Four Principles", "Principles of Biomedical Ethics", "DEPENDS_ON")],
     "who authored the canonical 1979 principlist textbook now at the core of clinical bioethics teaching",
     "Beauchamp Childress biomedical ethics four principles year"),
    # --- 14 ---
    ("The Four Principles framework replaces earlier casuistic bioethics by providing, across modern bioethics, a shared mid-level vocabulary that clinicians of differing ethical traditions can deliberate with.", "decision", "knowledge", False,
     [("Four Principles", "framework"), ("casuistic bioethics", "theory"), ("bioethics", "field")],
     [("Four Principles", "casuistic bioethics", "REPLACES")],
     "which principlist framework replaced older casuistic bioethics as the shared mid-level vocabulary",
     "principlism casuistry mid level bioethics replacement"),
    # --- 15 ---
    ("Peter Singer's Animal Liberation, published in 1975, argues from a preference-utilitarian basis that speciesism is morally analogous to racism and sexism.", "reference", "knowledge", False,
     [("Peter Singer", "person"), ("Animal Liberation", "publication"), ("1975", "date"), ("preference-utilitarian", "theory"), ("speciesism", "concept")],
     [("Animal Liberation", "Peter Singer", "AUTHORED_BY")],
     "which 1975 book argued from preference utilitarianism against speciesism",
     "Singer animal liberation speciesism preference utilitarian year"),
    # --- 16 ---
    ("Tom Regan's The Case for Animal Rights of 1983 grounds animal ethics in a rights-based deontological framework rather than Singer's utilitarian calculus.", "decision", "knowledge", False,
     [("Tom Regan", "person"), ("The Case for Animal Rights", "publication"), ("1983", "date"), ("rights-based deontological framework", "theory"), ("Singer's utilitarian calculus", "theory")],
     [("The Case for Animal Rights", "Tom Regan", "AUTHORED_BY"), ("rights-based deontological framework", "Singer's utilitarian calculus", "PREFERS")],
     "which 1983 Regan book favoured rights deontology over Singer's utilitarian calculus for animal ethics",
     "Regan case animal rights deontology subject of life year"),
    # --- 17 ---
    ("Christine Korsgaard's Fellow Creatures of 2018 extends Kantian constructivism to animals, treating them as ends in themselves with claims upon rational agents.", "reference", "knowledge", False,
     [("Christine Korsgaard", "person"), ("Fellow Creatures", "publication"), ("2018", "date"), ("Kantian constructivism", "theory"), ("rational agents", "concept")],
     [("Fellow Creatures", "Christine Korsgaard", "AUTHORED_BY"), ("Fellow Creatures", "Kantian constructivism", "BUILDS_ON")],
     "which 2018 book extended Kantian constructivism to the moral standing of animals",
     "Korsgaard fellow creatures Kantian constructivism animals year"),
    # --- 18 ---
    ("Nick Bostrom's Superintelligence, published in 2014, foregrounds existential risk from unaligned artificial general intelligence and frames the control and value-loading problems.", "reference", "knowledge", False,
     [("Nick Bostrom", "person"), ("Superintelligence", "publication"), ("2014", "date"), ("artificial general intelligence", "concept"), ("value-loading problems", "concept")],
     [("Superintelligence", "Nick Bostrom", "AUTHORED_BY")],
     "which 2014 book set the AI-ethics agenda around control and value loading for superintelligence",
     "Bostrom superintelligence existential risk AGI control problem year"),
    # --- 19 ---
    ("Stuart Russell's Human Compatible of 2019 revises classical AI objectives by proposing provably beneficial AI built around uncertainty over human preferences.", "reference", "knowledge", False,
     [("Stuart Russell", "person"), ("Human Compatible", "publication"), ("2019", "date"), ("classical AI objectives", "concept"), ("provably beneficial AI", "concept")],
     [("Human Compatible", "Stuart Russell", "AUTHORED_BY"), ("Human Compatible", "classical AI objectives", "IMPROVES_ON")],
     "which 2019 book recasts AI design around uncertainty about human preferences",
     "Russell human compatible beneficial AI inverse reward year"),
    # --- 20 ---
    ("Margaret Mitchell and colleagues introduced Model Cards in their 2019 FAT ACM paper to document intended use, performance, and ethical considerations of machine learning models.", "reference", "knowledge", False,
     [("Margaret Mitchell", "person"), ("Model Cards", "method"), ("2019", "date"), ("FAT ACM", "event"), ("machine learning models", "concept")],
     [("Model Cards", "Margaret Mitchell", "AUTHORED_BY")],
     "which 2019 FAT ACM paper introduced Model Cards for documenting ML ethics and scope",
     "Mitchell model cards FAT ACM documentation machine learning year"),
    # --- 21 ---
    ("Aldo Leopold's A Sand County Almanac, published posthumously in 1949, formulates the land ethic in which ethical standing extends to soils, waters, plants, and animals.", "reference", "knowledge", False,
     [("Aldo Leopold", "person"), ("A Sand County Almanac", "publication"), ("1949", "date"), ("land ethic", "theory")],
     [("A Sand County Almanac", "Aldo Leopold", "AUTHORED_BY"), ("land ethic", "Aldo Leopold", "AUTHORED_BY")],
     "which 1949 posthumous book introduced the land ethic into environmental thought",
     "Leopold sand county almanac land ethic biotic community year"),
    # --- 22 ---
    ("Arne Naess coined deep ecology in a 1973 Inquiry paper, distinguishing it from shallow reform environmentalism by its commitment to biospherical egalitarianism.", "reference", "knowledge", False,
     [("Arne Naess", "person"), ("deep ecology", "theory"), ("1973", "date"), ("Inquiry", "publication"), ("shallow reform environmentalism", "theory"), ("biospherical egalitarianism", "concept")],
     [("deep ecology", "Arne Naess", "AUTHORED_BY"), ("deep ecology", "shallow reform environmentalism", "PREFERS")],
     "which 1973 Inquiry article introduced deep ecology against shallow environmentalism",
     "Naess deep ecology Inquiry shallow biospherical egalitarianism year"),
    # --- 23 ---
    ("Allen Thompson's work in environmental virtue ethics, developed across essays in the 2010s, reframes climate obligations as requirements of character rather than calculation.", "reference", "knowledge", False,
     [("Allen Thompson", "person"), ("environmental virtue ethics", "theory"), ("2010s", "date"), ("climate obligations", "concept"), ("character", "concept")],
     [("environmental virtue ethics", "Allen Thompson", "AUTHORED_BY")],
     "whose 2010s work reframed climate obligations as matters of virtue rather than calculation",
     "Thompson environmental virtue ethics climate character decade"),
    # --- 24 ---
    ("Andrew Crane and Dirk Matten's Business Ethics textbook, first published in 2004, integrates stakeholder theory, corporate citizenship, and globalisation into a European-oriented framework.", "reference", "knowledge", False,
     [("Andrew Crane", "person"), ("Dirk Matten", "person"), ("Business Ethics", "publication"), ("2004", "date"), ("stakeholder theory", "theory"), ("corporate citizenship", "concept")],
     [("Business Ethics", "Andrew Crane", "AUTHORED_BY"), ("Business Ethics", "Dirk Matten", "AUTHORED_BY")],
     "who wrote the European-oriented 2004 text that folded stakeholder models and corporate citizenship into a global frame",
     "Crane Matten business ethics stakeholder corporate citizenship year"),
    # --- 25 ---
    ("Thomas Donaldson and Thomas Dunfee's Integrative Social Contracts Theory, articulated in Ties That Bind in 1999, grounds business ethics in hypernorms and local community consent.", "reference", "knowledge", False,
     [("Thomas Donaldson", "person"), ("Thomas Dunfee", "person"), ("Integrative Social Contracts Theory", "theory"), ("Ties That Bind", "publication"), ("1999", "date"), ("hypernorms", "concept")],
     [("Ties That Bind", "Thomas Donaldson", "AUTHORED_BY"), ("Ties That Bind", "Thomas Dunfee", "AUTHORED_BY"), ("Integrative Social Contracts Theory", "hypernorms", "DEPENDS_ON")],
     "which 1999 book grounded business ethics in hypernorms and local community consent",
     "Donaldson Dunfee integrative social contracts hypernorms year"),
    # --- 26 ---
    ("Albert Jonsen, Mark Siegler, and William Winslade's Clinical Ethics, first published in 1982, supplies the four-box method of medical indications, patient preferences, quality of life, and contextual features.", "reference", "knowledge", False,
     [("Albert Jonsen", "person"), ("Mark Siegler", "person"), ("William Winslade", "person"), ("Clinical Ethics", "publication"), ("1982", "date"), ("four-box method", "framework")],
     [("Clinical Ethics", "Albert Jonsen", "AUTHORED_BY"), ("Clinical Ethics", "Mark Siegler", "AUTHORED_BY"), ("Clinical Ethics", "William Winslade", "AUTHORED_BY"), ("four-box method", "Clinical Ethics", "DEPENDS_ON")],
     "which 1982 casebook introduced the four-box method of clinical ethics consultation",
     "Jonsen Siegler Winslade clinical ethics four box casuistry year"),
    # --- 27 ---
    ("Michael Walzer's Just and Unjust Wars, published in 1977, restates just-war theory through historical case analysis and defends the moral equality of combatants.", "reference", "knowledge", False,
     [("Michael Walzer", "person"), ("Just and Unjust Wars", "publication"), ("1977", "date"), ("just-war theory", "theory"), ("moral equality of combatants", "concept")],
     [("Just and Unjust Wars", "Michael Walzer", "AUTHORED_BY"), ("just-war theory", "Michael Walzer", "BUILDS_ON")],
     "which 1977 book restated just-war theory through historical case analysis",
     "Walzer just unjust wars moral equality combatants year"),
    # --- 28 ---
    ("Judith Jarvis Thomson's A Defense of Abortion, published in Philosophy & Public Affairs in 1971, introduced the violinist thought experiment into applied ethics.", "reference", "knowledge", False,
     [("Judith Jarvis Thomson", "person"), ("A Defense of Abortion", "publication"), ("Philosophy & Public Affairs", "publication"), ("1971", "date"), ("violinist thought experiment", "concept")],
     [("A Defense of Abortion", "Judith Jarvis Thomson", "AUTHORED_BY")],
     "who authored the 1971 applied-ethics piece whose famous kidnapped-violinist case became standard in abortion debate",
     "Thomson defense abortion violinist Philosophy Public Affairs year"),
    # --- 29 ---
    ("Philippa Foot's The Problem of Abortion and the Doctrine of Double Effect, published in the Oxford Review in 1967, framed the original trolley case that seeded the experimental trolley-problem literature.", "reference", "knowledge", False,
     [("Philippa Foot", "person"), ("The Problem of Abortion and the Doctrine of Double Effect", "publication"), ("Oxford Review", "publication"), ("1967", "date"), ("trolley case", "concept")],
     [("The Problem of Abortion and the Doctrine of Double Effect", "Philippa Foot", "AUTHORED_BY"), ("trolley case", "Philippa Foot", "AUTHORED_BY")],
     "which 1967 Foot paper introduced the original trolley case into ethics",
     "Foot double effect abortion Oxford Review trolley year"),
    # --- 30 ---
    ("Joshua Greene's fMRI study, published in Science in 2001, distinguishes personal from impersonal trolley dilemmas by differential engagement of emotional and cognitive control regions.", "reference", "knowledge", False,
     [("Joshua Greene", "person"), ("fMRI study", "method"), ("Science", "publication"), ("2001", "date"), ("trolley dilemmas", "concept"), ("emotional", "concept"), ("cognitive control regions", "concept")],
     [("fMRI study", "Joshua Greene", "AUTHORED_BY")],
     "whose early neuroimaging work tied moral judgement differences in the trolley literature to emotional versus controlled processing",
     "Greene 2001 Science fMRI personal impersonal trolley emotional year"),
    # --- 31 ---
    ("John Mikhail's Elements of Moral Cognition, published in 2011, models trolley-problem intuitions as the output of an innate moral grammar analogous to generative linguistics.", "reference", "knowledge", False,
     [("John Mikhail", "person"), ("Elements of Moral Cognition", "publication"), ("2011", "date"), ("innate moral grammar", "theory"), ("generative linguistics", "field")],
     [("Elements of Moral Cognition", "John Mikhail", "AUTHORED_BY"), ("innate moral grammar", "John Mikhail", "AUTHORED_BY")],
     "which 2011 book modelled moral cognition as an innate grammar on analogy with linguistics",
     "Mikhail elements moral cognition universal grammar trolley year"),
    # --- 32 ---
    ("T. M. Scanlon's What We Owe to Each Other, published in 1998, founds moral contractualism on principles no one could reasonably reject.", "reference", "knowledge", False,
     [("T. M. Scanlon", "person"), ("What We Owe to Each Other", "publication"), ("1998", "date"), ("moral contractualism", "theory")],
     [("What We Owe to Each Other", "T. M. Scanlon", "AUTHORED_BY"), ("moral contractualism", "T. M. Scanlon", "AUTHORED_BY")],
     "whose late-1990s Harvard monograph grounded contractualist morality in the reasonable-rejection test",
     "Scanlon what we owe contractualism reasonable rejection year"),
    # --- 33 ---
    ("Bernard Williams's Ethics and the Limits of Philosophy of 1985 rejects the ambitions of systematic moral theory in favour of thick ethical concepts and reflective practical life.", "decision", "knowledge", False,
     [("Bernard Williams", "person"), ("Ethics and the Limits of Philosophy", "publication"), ("1985", "date"), ("systematic moral theory", "theory"), ("thick ethical concepts", "concept")],
     [("Ethics and the Limits of Philosophy", "Bernard Williams", "AUTHORED_BY"), ("thick ethical concepts", "systematic moral theory", "PREFERS")],
     "which 1985 book rejected systematic moral theory in favour of thick ethical concepts",
     "Williams ethics limits philosophy thick concepts system year"),
    # --- 34. noise ---
    ("I should reread the footnote on section four before deciding how strong the rejoinder really is.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Martha Nussbaum's Frontiers of Justice of 2006 extends the capabilities approach to disability, species membership, and global justice, positioning it against purely contractarian frameworks.", "reference", "knowledge", False,
     [("Martha Nussbaum", "person"), ("Frontiers of Justice", "publication"), ("2006", "date"), ("capabilities approach", "theory"), ("contractarian frameworks", "theory")],
     [("Frontiers of Justice", "Martha Nussbaum", "AUTHORED_BY"), ("capabilities approach", "contractarian frameworks", "PREFERS")],
     "whose 2006 monograph widened the capabilities account to cover cognitive impairment, non-human animals, and transnational obligations",
     "Nussbaum frontiers justice capabilities disability species global year"),
    # --- 36 ---
    ("The journal Ethics, founded in 1890 as the International Journal of Ethics at the University of Chicago, remains a flagship outlet for analytic moral and political philosophy.", "reference", "knowledge", False,
     [("Ethics", "publication"), ("1890", "date"), ("International Journal of Ethics", "publication"), ("University of Chicago", "organization")],
     [("Ethics", "International Journal of Ethics", "REPLACES")],
     "which flagship moral philosophy journal began in 1890 as the International Journal of Ethics",
     "Ethics journal Chicago International Journal Ethics flagship year"),
    # --- 37 ---
    ("Philosophy & Public Affairs, launched by Princeton University Press in 1971, pioneered the application of analytic philosophy to live policy questions.", "reference", "knowledge", False,
     [("Philosophy & Public Affairs", "publication"), ("Princeton University Press", "organization"), ("1971", "date"), ("analytic philosophy", "field")],
     [("Philosophy & Public Affairs", "Princeton University Press", "AUTHORED_BY")],
     "which flagship Princeton quarterly launched at the start of the 1970s as the venue for analytic work on concrete social questions",
     "Philosophy Public Affairs Princeton applied analytic policy year"),
    # --- 38 ---
    ("The Journal of Philosophy, published continuously since 1904, serves as a primary venue for analytic metaethical and normative papers in the United States.", "reference", "knowledge", False,
     [("Journal of Philosophy", "publication"), ("1904", "date"), ("United States", "place")],
     [],
     "which long-running American journal since 1904 publishes analytic metaethics and normative theory",
     "Journal of Philosophy analytic metaethics normative US year"),
    # --- 39 ---
    ("Utilitas, established in 1989 and published by Cambridge University Press, concentrates scholarship on utilitarian and consequentialist ethics.", "reference", "knowledge", False,
     [("Utilitas", "publication"), ("1989", "date"), ("Cambridge University Press", "organization"), ("utilitarian", "theory"), ("consequentialist ethics", "theory")],
     [("Utilitas", "Cambridge University Press", "AUTHORED_BY")],
     "which Cambridge journal launched in 1989 specialises in utilitarian and consequentialist ethics",
     "Utilitas Cambridge journal utilitarian consequentialist scholarship year"),
    # --- 40 ---
    ("The Belmont Report, issued by the National Commission for the Protection of Human Subjects in 1979, distilled research ethics into respect for persons, beneficence, and justice.", "milestone", "knowledge", False,
     [("Belmont Report", "publication"), ("National Commission for the Protection of Human Subjects", "organization"), ("1979", "date"), ("research ethics", "field")],
     [("Belmont Report", "National Commission for the Protection of Human Subjects", "AUTHORED_BY")],
     "which 1979 US report distilled research ethics into three foundational principles",
     "Belmont report respect persons beneficence justice research year"),
    # --- 41 ---
    ("The Nuremberg Code, articulated by the Nuremberg Military Tribunal in 1947, first codified voluntary informed consent as an absolute requirement of human experimentation.", "milestone", "knowledge", False,
     [("Nuremberg Code", "publication"), ("Nuremberg Military Tribunal", "organization"), ("1947", "date"), ("voluntary informed consent", "concept"), ("human experimentation", "concept")],
     [("Nuremberg Code", "Nuremberg Military Tribunal", "AUTHORED_BY")],
     "which 1947 tribunal-issued code first codified voluntary informed consent in research",
     "Nuremberg Code tribunal informed consent experimentation year"),
    # --- 42 ---
    ("Onora O'Neill's Constructions of Reason, published in 1989, reinterprets Kant's ethics as a constructivist account of public reason rather than a derivation from metaphysical premises.", "reference", "knowledge", False,
     [("Onora O'Neill", "person"), ("Constructions of Reason", "publication"), ("1989", "date"), ("Kant's ethics", "theory"), ("constructivist account", "theory"), ("public reason", "concept")],
     [("Constructions of Reason", "Onora O'Neill", "AUTHORED_BY"), ("Constructions of Reason", "Kant's ethics", "IMPROVES_ON")],
     "which 1989 O'Neill book recast Kantian ethics as public-reason constructivism",
     "O'Neill constructions reason Kantian constructivism public reason year"),
    # --- 43 ---
    ("Carol Gilligan's In a Different Voice of 1982 seeded care ethics by contrasting a relational ethic of care with Kohlberg's justice-focused stage theory of moral development.", "reference", "knowledge", False,
     [("Carol Gilligan", "person"), ("In a Different Voice", "publication"), ("1982", "date"), ("care ethics", "theory"), ("Kohlberg's justice-focused stage theory", "theory")],
     [("In a Different Voice", "Carol Gilligan", "AUTHORED_BY"), ("care ethics", "Kohlberg's justice-focused stage theory", "PREFERS")],
     "whose early-1980s monograph opened the feminist care tradition by challenging Kohlberg's developmental stage model",
     "Gilligan different voice care ethics Kohlberg justice year"),
    # --- 44 ---
    ("Virginia Held's The Ethics of Care of 2006 defends care ethics as a distinct moral theory rather than a supplement to Kantian or utilitarian frameworks.", "decision", "knowledge", False,
     [("Virginia Held", "person"), ("The Ethics of Care", "publication"), ("2006", "date"), ("care ethics", "theory"), ("Kantian", "theory"), ("utilitarian frameworks", "theory")],
     [("The Ethics of Care", "Virginia Held", "AUTHORED_BY")],
     "which 2006 Held book defended care ethics as an independent normative theory",
     "Held ethics of care independent theory Kantian utilitarian year"),
    # --- 45 ---
    ("Sharon Street's A Darwinian Dilemma for Realist Theories of Value, published in Philosophical Studies in 2006, argues that evolutionary debunking pressures push metaethics away from moral realism and toward constructivism.", "reference", "knowledge", False,
     [("Sharon Street", "person"), ("A Darwinian Dilemma for Realist Theories of Value", "publication"), ("Philosophical Studies", "publication"), ("2006", "date"), ("evolutionary debunking", "method"), ("moral realism", "theory"), ("constructivism", "theory")],
     [("A Darwinian Dilemma for Realist Theories of Value", "Sharon Street", "AUTHORED_BY"), ("constructivism", "moral realism", "PREFERS")],
     "whose mid-2000s journal article pressed a selection-based genealogy to undercut stance-independent value claims",
     "Street Darwinian dilemma debunking realism constructivism year"),
    # --- 46 ---
    ("Russ Shafer-Landau's Moral Realism: A Defence of 2003 rebuts debunking and error-theory attacks by defending a non-naturalist stance-independent conception of moral facts.", "reference", "knowledge", False,
     [("Russ Shafer-Landau", "person"), ("Moral Realism: A Defence", "publication"), ("2003", "date"), ("non-naturalist", "theory"), ("moral facts", "concept")],
     [("Moral Realism: A Defence", "Russ Shafer-Landau", "AUTHORED_BY")],
     "which 2003 book defended non-naturalist moral realism against debunking and error theory",
     "Shafer Landau moral realism defence non naturalist year"),
    # --- 47 ---
    ("Allan Gibbard's Wise Choices, Apt Feelings of 1990 develops a norm-expressivist metaethics on which moral judgements express acceptance of norms for feelings and action.", "reference", "knowledge", False,
     [("Allan Gibbard", "person"), ("Wise Choices, Apt Feelings", "publication"), ("1990", "date"), ("norm-expressivist metaethics", "theory")],
     [("Wise Choices, Apt Feelings", "Allan Gibbard", "AUTHORED_BY"), ("norm-expressivist metaethics", "Allan Gibbard", "AUTHORED_BY")],
     "which 1990 book set out norm-expressivism as acceptance of norms for feeling and action",
     "Gibbard wise choices apt feelings norm expressivism year"),
    # --- 48 ---
    ("Shelly Kagan's The Limits of Morality of 1989 presses consequentialism against common-sense morality by rejecting agent-centred options and constraints.", "reference", "knowledge", False,
     [("Shelly Kagan", "person"), ("The Limits of Morality", "publication"), ("1989", "date"), ("consequentialism", "theory"), ("agent-centred options", "concept")],
     [("The Limits of Morality", "Shelly Kagan", "AUTHORED_BY")],
     "whose 1989 study squeezed common-sense morality by denying any room for agent-relative permissions or prohibitions",
     "Kagan limits morality agent centred options consequentialism year"),
    # --- 49 ---
    ("Frances Kamm's Intricate Ethics of 2007 develops a deontological case-method ethics built on the Doctrine of Double Effect and the Principle of Permissible Harm.", "reference", "knowledge", False,
     [("Frances Kamm", "person"), ("Intricate Ethics", "publication"), ("2007", "date"), ("Doctrine of Double Effect", "concept"), ("Principle of Permissible Harm", "concept")],
     [("Intricate Ethics", "Frances Kamm", "AUTHORED_BY"), ("Principle of Permissible Harm", "Frances Kamm", "AUTHORED_BY")],
     "which 2007 Kamm book anchored deontological case ethics in double effect and permissible harm",
     "Kamm intricate ethics double effect permissible harm year"),
    # --- 50 ---
    ("Peter Railton's Moral Realism, published in the Philosophical Review in 1986, defends a naturalistic reductive realism that identifies moral goodness with what would be rationally desired under idealisation.", "reference", "knowledge", False,
     [("Peter Railton", "person"), ("Moral Realism", "publication"), ("Philosophical Review", "publication"), ("1986", "date"), ("naturalistic reductive realism", "theory")],
     [("Moral Realism", "Peter Railton", "AUTHORED_BY"), ("naturalistic reductive realism", "Peter Railton", "AUTHORED_BY")],
     "which 1986 Philosophical Review paper defended naturalistic reductive moral realism",
     "Railton moral realism Philosophical Review naturalistic reductive year"),
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
