"""One-off emitter for shared-base batch-108 — knowledge domain (psychology as a research field: behavioural, clinical, developmental).

Writes 50 rows with ids shared-05351..05400.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_108.tmp.jsonl"
ID_OFFSET = 5350

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Daniel Kahneman and Amos Tversky's 1974 Science paper Judgment under Uncertainty introduced the availability, representativeness, and anchoring heuristics as systematic departures from rational choice.", "reference", "knowledge", False,
     [("Daniel Kahneman", "person"), ("Amos Tversky", "person"), ("Judgment under Uncertainty", "publication"), ("1974", "date"), ("Science", "publication"), ("availability", "concept"), ("representativeness", "concept"), ("anchoring", "concept")],
     [("Judgment under Uncertainty", "Daniel Kahneman", "AUTHORED_BY"), ("Judgment under Uncertainty", "Amos Tversky", "AUTHORED_BY")],
     "which 1974 Science article introduced the representativeness and anchoring heuristics in human judgment",
     "heuristics biases availability representativeness anchoring Science article year"),
    # --- 2 ---
    ("Kahneman and Tversky's 1979 prospect theory, published in Econometrica, improves on expected utility by modelling loss aversion and a reference-dependent value function.", "reference", "knowledge", False,
     [("Kahneman", "person"), ("Tversky", "person"), ("prospect theory", "theory"), ("1979", "date"), ("Econometrica", "publication"), ("expected utility", "theory"), ("loss aversion", "concept")],
     [("prospect theory", "Kahneman", "AUTHORED_BY"), ("prospect theory", "expected utility", "IMPROVES_ON")],
     "which 1979 Econometrica paper replaced expected utility with a reference-dependent value function",
     "prospect theory loss aversion reference point Econometrica year"),
    # --- 3 ---
    ("Albert Bandura's 1961 Bobo doll experiments at Stanford demonstrated that children acquire aggressive behaviour through observational learning rather than direct reinforcement alone.", "milestone", "knowledge", False,
     [("Albert Bandura", "person"), ("Bobo doll experiments", "event"), ("1961", "date"), ("Stanford", "organization"), ("observational learning", "concept")],
     [("Bobo doll experiments", "Albert Bandura", "AUTHORED_BY")],
     "which 1961 Stanford study showed that children imitate aggressive models without direct reinforcement",
     "Bandura Bobo doll imitation observational learning Stanford year"),
    # --- 4 ---
    ("Bandura's 1977 book Social Learning Theory broadened behaviourist accounts by adding modelling and self-efficacy as core mechanisms of behaviour change.", "reference", "knowledge", False,
     [("Bandura", "person"), ("Social Learning Theory", "publication"), ("1977", "date"), ("modelling", "concept"), ("self-efficacy", "concept"), ("behaviourist", "concept")],
     [("Social Learning Theory", "Bandura", "AUTHORED_BY"), ("Social Learning Theory", "behaviourist", "IMPROVES_ON")],
     "which 1977 book extended behaviourism with modelling and self-efficacy",
     "Bandura social learning self efficacy modelling book year"),
    # --- 5 ---
    ("B. F. Skinner's 1938 The Behavior of Organisms formalised operant conditioning around reinforcement schedules studied in the Skinner box.", "reference", "knowledge", False,
     [("B. F. Skinner", "person"), ("The Behavior of Organisms", "publication"), ("1938", "date"), ("operant conditioning", "theory"), ("Skinner box", "tool")],
     [("The Behavior of Organisms", "B. F. Skinner", "AUTHORED_BY")],
     "which 1938 monograph formalised operant conditioning and the analysis of reinforcement schedules",
     "Skinner operant conditioning Behavior of Organisms reinforcement schedule year"),
    # --- 6 ---
    ("Ivan Pavlov's salivation studies on dogs, reported from 1897 at the Imperial Military Medical Academy in Saint Petersburg, established classical conditioning as a core learning mechanism.", "milestone", "knowledge", False,
     [("Ivan Pavlov", "person"), ("1897", "date"), ("Imperial Military Medical Academy", "organization"), ("Saint Petersburg", "place"), ("classical conditioning", "theory")],
     [("classical conditioning", "Ivan Pavlov", "AUTHORED_BY")],
     "whose late-nineteenth-century dog experiments in Saint Petersburg founded classical conditioning",
     "Pavlov salivation dogs classical conditioning Saint Petersburg year"),
    # --- 7 ---
    ("John Watson's 1920 Little Albert study at Johns Hopkins extended Pavlovian conditioning to human emotional responses by pairing a white rat with a startling noise.", "reference", "knowledge", False,
     [("John Watson", "person"), ("Little Albert", "event"), ("1920", "date"), ("Johns Hopkins", "organization"), ("Pavlovian conditioning", "theory")],
     [("Little Albert", "John Watson", "AUTHORED_BY"), ("Little Albert", "Pavlovian conditioning", "BUILDS_ON")],
     "which 1920 Johns Hopkins study applied classical conditioning to a child's fear response",
     "Watson Little Albert conditioned fear Johns Hopkins year"),
    # --- 8 ---
    ("Mary Ainsworth's Strange Situation procedure, described in her 1978 book Patterns of Attachment, operationalised secure, avoidant, and ambivalent infant attachment styles.", "reference", "knowledge", False,
     [("Mary Ainsworth", "person"), ("Strange Situation", "method"), ("Patterns of Attachment", "publication"), ("1978", "date"), ("attachment styles", "concept")],
     [("Patterns of Attachment", "Mary Ainsworth", "AUTHORED_BY"), ("Strange Situation", "Mary Ainsworth", "AUTHORED_BY")],
     "which 1978 book operationalised infant attachment through the Strange Situation procedure",
     "Ainsworth Strange Situation secure avoidant ambivalent book year"),
    # --- 9 ---
    ("John Bowlby's Attachment trilogy, published between 1969 and 1980 with the Tavistock Clinic, reframed early caregiver bonds in ethological terms.", "reference", "knowledge", False,
     [("John Bowlby", "person"), ("Attachment trilogy", "publication"), ("1969", "date"), ("1980", "date"), ("Tavistock Clinic", "organization"), ("ethological", "concept")],
     [("Attachment trilogy", "John Bowlby", "AUTHORED_BY")],
     "whose Tavistock-based trilogy recast early caregiver bonds in ethological terms",
     "Bowlby attachment trilogy Tavistock ethology caregiver years"),
    # --- 10. noise ---
    ("Let me reread the method section once more before I compare the effect sizes.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Sigmund Freud's 1900 The Interpretation of Dreams, written in Vienna, launched psychoanalysis by positing unconscious wish fulfilment as the engine of dream content.", "reference", "knowledge", False,
     [("Sigmund Freud", "person"), ("The Interpretation of Dreams", "publication"), ("1900", "date"), ("Vienna", "place"), ("psychoanalysis", "theory")],
     [("The Interpretation of Dreams", "Sigmund Freud", "AUTHORED_BY"), ("psychoanalysis", "Sigmund Freud", "AUTHORED_BY")],
     "which 1900 Viennese book inaugurated psychoanalysis around unconscious wish fulfilment",
     "Freud Interpretation of Dreams Vienna psychoanalysis founding year"),
    # --- 12 ---
    ("Carl Jung's 1912 break with Freud seeded analytical psychology, recentred on collective unconscious archetypes articulated in works such as The Archetypes and the Collective Unconscious.", "decision", "knowledge", False,
     [("Carl Jung", "person"), ("Freud", "person"), ("1912", "date"), ("analytical psychology", "theory"), ("archetypes", "concept"), ("The Archetypes and the Collective Unconscious", "publication")],
     [("analytical psychology", "Carl Jung", "AUTHORED_BY"), ("analytical psychology", "Freud", "REPLACES")],
     "which 1912 split produced analytical psychology organised around archetypes",
     "Jung Freud split archetypes collective unconscious analytical psychology year"),
    # --- 13 ---
    ("Carl Rogers's 1951 book Client-Centered Therapy shifted mid-century clinical practice from directive interpretation toward empathic, non-directive facilitation.", "preference", "knowledge", False,
     [("Carl Rogers", "person"), ("Client-Centered Therapy", "publication"), ("1951", "date"), ("non-directive facilitation", "method"), ("directive interpretation", "method")],
     [("Client-Centered Therapy", "Carl Rogers", "AUTHORED_BY"), ("non-directive facilitation", "directive interpretation", "PREFERS")],
     "whose 1951 humanistic manual reoriented mid-century psychotherapy away from directive interpretation",
     "Rogers client centered humanistic empathy mid century manual year"),
    # --- 14 ---
    ("Aaron Beck's 1967 Depression: Causes and Treatment replaced the dominant psychoanalytic account of depression with a cognitive model built on negative schemas.", "reference", "knowledge", False,
     [("Aaron Beck", "person"), ("Depression: Causes and Treatment", "publication"), ("1967", "date"), ("psychoanalytic account", "theory"), ("cognitive model", "theory"), ("negative schemas", "concept")],
     [("Depression: Causes and Treatment", "Aaron Beck", "AUTHORED_BY"), ("cognitive model", "psychoanalytic account", "REPLACES")],
     "which 1967 book replaced psychoanalytic accounts of depression with a schema-based cognitive model",
     "Beck cognitive therapy depression negative schema book year"),
    # --- 15 ---
    ("Albert Ellis's rational emotive behaviour therapy, formulated from 1955 at his New York institute, anchors CBT's rationalist lineage alongside Beck's cognitive therapy.", "reference", "knowledge", False,
     [("Albert Ellis", "person"), ("rational emotive behaviour therapy", "method"), ("1955", "date"), ("New York", "place"), ("CBT", "method"), ("Beck", "person")],
     [("rational emotive behaviour therapy", "Albert Ellis", "AUTHORED_BY"), ("CBT", "rational emotive behaviour therapy", "BUILDS_ON")],
     "which 1950s New York clinician founded rational emotive therapy as a CBT ancestor",
     "Ellis REBT rational emotive CBT lineage New York year"),
    # --- 16 ---
    ("Marsha Linehan's 1993 Cognitive-Behavioral Treatment of Borderline Personality Disorder improves on classical CBT by folding mindfulness and dialectical balance into the third-wave family.", "reference", "knowledge", False,
     [("Marsha Linehan", "person"), ("Cognitive-Behavioral Treatment of Borderline Personality Disorder", "publication"), ("1993", "date"), ("classical CBT", "method"), ("mindfulness", "concept"), ("third-wave", "concept")],
     [("Cognitive-Behavioral Treatment of Borderline Personality Disorder", "Marsha Linehan", "AUTHORED_BY"), ("third-wave", "classical CBT", "IMPROVES_ON")],
     "which 1993 dialectical-behaviour-therapy manual extended CBT into the third wave",
     "Linehan DBT dialectical behavior therapy third wave borderline year"),
    # --- 17 ---
    ("The American Psychiatric Association published DSM-5 in 2013, replacing DSM-IV-TR and dropping the multi-axial assessment framework used since 1980.", "decision", "knowledge", False,
     [("American Psychiatric Association", "organization"), ("DSM-5", "publication"), ("2013", "date"), ("DSM-IV-TR", "publication"), ("multi-axial assessment", "framework"), ("1980", "date")],
     [("DSM-5", "American Psychiatric Association", "AUTHORED_BY"), ("DSM-5", "DSM-IV-TR", "REPLACES")],
     "which 2013 manual replaced DSM-IV-TR and retired the multi-axial framework",
     "DSM-5 APA manual multi axial retirement year"),
    # --- 18 ---
    ("The World Health Organization's ICD-11, ratified in 2019 and coming into force in 2022, replaced ICD-10 chapters on mental and behavioural disorders with a revised classification aligned partly with DSM-5.", "decision", "knowledge", False,
     [("World Health Organization", "organization"), ("ICD-11", "publication"), ("2019", "date"), ("2022", "date"), ("ICD-10", "publication"), ("DSM-5", "publication")],
     [("ICD-11", "World Health Organization", "AUTHORED_BY"), ("ICD-11", "ICD-10", "REPLACES")],
     "which 2019 WHO revision replaced ICD-10's mental-disorders chapters and aligned partly with DSM-5",
     "ICD-11 WHO mental disorders classification ICD-10 replacement year"),
    # --- 19 ---
    ("The Open Science Collaboration's 2015 Reproducibility Project: Psychology, published in Science, replicated only 36 of 100 prominent findings and crystallised the replication crisis.", "milestone", "knowledge", False,
     [("Open Science Collaboration", "organization"), ("Reproducibility Project: Psychology", "publication"), ("2015", "date"), ("Science", "publication"), ("replication crisis", "concept")],
     [("Reproducibility Project: Psychology", "Open Science Collaboration", "AUTHORED_BY")],
     "which 2015 Science paper replicated only 36 of 100 psychology findings and defined the replication crisis",
     "Open Science Collaboration Reproducibility Project Psychology Science year"),
    # --- 20 ---
    ("The Many Labs 2 project, reported in Advances in Methods and Practices in Psychological Science in 2018, contradicted several celebrated single-lab effects by running 28 replications across 60-plus labs.", "fact", "knowledge", False,
     [("Many Labs 2", "event"), ("Advances in Methods and Practices in Psychological Science", "publication"), ("2018", "date")],
     [("Many Labs 2", "Advances in Methods and Practices in Psychological Science", "PUBLISHED_IN")],
     "which 2018 multi-lab project contradicted celebrated single-lab effects across 28 replications",
     "Many Labs 2 multi lab replication AMPPS year"),
    # --- 21 ---
    ("Daryl Bem's 2011 Feeling the Future paper in the Journal of Personality and Social Psychology claimed evidence for precognition and directly triggered replication and meta-science reforms.", "problem", "knowledge", False,
     [("Daryl Bem", "person"), ("Feeling the Future", "publication"), ("2011", "date"), ("Journal of Personality and Social Psychology", "publication"), ("precognition", "concept")],
     [("Feeling the Future", "Daryl Bem", "AUTHORED_BY"), ("Feeling the Future", "Journal of Personality and Social Psychology", "PUBLISHED_IN")],
     "which 2011 JPSP paper claimed precognition and catalysed replication reforms",
     "Bem Feeling Future JPSP precognition replication trigger year"),
    # --- 22 ---
    ("The American Psychological Association's flagship journals include Psychological Review, founded in 1894 by James Mark Baldwin and James McKeen Cattell, and American Psychologist.", "reference", "knowledge", False,
     [("American Psychological Association", "organization"), ("Psychological Review", "publication"), ("1894", "date"), ("James Mark Baldwin", "person"), ("James McKeen Cattell", "person"), ("American Psychologist", "publication")],
     [("Psychological Review", "James Mark Baldwin", "AUTHORED_BY"), ("Psychological Review", "James McKeen Cattell", "AUTHORED_BY")],
     "which 1894 theoretical journal co-founded by Baldwin and Cattell remains an APA flagship",
     "Psychological Review APA Baldwin Cattell founding year"),
    # --- 23 ---
    ("The British Psychological Society publishes the British Journal of Psychology, founded in 1904, and the British Journal of Clinical Psychology as core disciplinary outlets.", "reference", "knowledge", False,
     [("British Psychological Society", "organization"), ("British Journal of Psychology", "publication"), ("1904", "date"), ("British Journal of Clinical Psychology", "publication")],
     [("British Journal of Psychology", "British Psychological Society", "AUTHORED_BY")],
     "which 1904 BPS journal alongside its clinical sibling serves as a core British outlet",
     "British Journal Psychology BPS clinical outlets founding year"),
    # --- 24 ---
    ("Anthony Greenwald, Debbie McGhee, and Jordan Schwartz introduced the Implicit Association Test in a 1998 Journal of Personality and Social Psychology paper that operationalised implicit social cognition via reaction times.", "reference", "knowledge", False,
     [("Anthony Greenwald", "person"), ("Debbie McGhee", "person"), ("Jordan Schwartz", "person"), ("Implicit Association Test", "method"), ("1998", "date"), ("Journal of Personality and Social Psychology", "publication")],
     [("Implicit Association Test", "Anthony Greenwald", "AUTHORED_BY"), ("Implicit Association Test", "Journal of Personality and Social Psychology", "PUBLISHED_IN")],
     "which 1998 JPSP paper introduced the IAT to operationalise implicit social cognition",
     "Greenwald McGhee Schwartz IAT JPSP implicit cognition year"),
    # --- 25 ---
    ("Hart Blanton and James Jaccard's 2006 American Psychologist critique argued the Implicit Association Test lacks the meaningful zero point needed to license its standard diagnostic claims.", "problem", "knowledge", False,
     [("Hart Blanton", "person"), ("James Jaccard", "person"), ("2006", "date"), ("American Psychologist", "publication"), ("Implicit Association Test", "method")],
     [("Hart Blanton", "Implicit Association Test", "CONTRADICTS"), ("James Jaccard", "Implicit Association Test", "CONTRADICTS")],
     "which 2006 American Psychologist critique argued the IAT lacks a meaningful zero point",
     "Blanton Jaccard IAT zero point critique American Psychologist year"),
    # --- 26 ---
    ("Patrick Forscher and colleagues' 2019 meta-analysis in the Journal of Personality and Social Psychology found weak IAT-behaviour correlations, contradicting stronger earlier claims by Greenwald and co-authors.", "fact", "knowledge", False,
     [("Patrick Forscher", "person"), ("2019", "date"), ("Journal of Personality and Social Psychology", "publication"), ("IAT", "method"), ("Greenwald", "person")],
     [("Patrick Forscher", "IAT", "CONTRADICTS")],
     "which 2019 JPSP meta-analysis found weak IAT-behaviour correlations against earlier stronger claims",
     "Forscher meta analysis IAT behaviour weak correlation year"),
    # --- 27 ---
    ("Martin Seligman and Mihaly Csikszentmihalyi's 2000 American Psychologist special issue launched positive psychology as a programmatic reorientation of the discipline toward flourishing and strengths.", "milestone", "knowledge", False,
     [("Martin Seligman", "person"), ("Mihaly Csikszentmihalyi", "person"), ("2000", "date"), ("American Psychologist", "publication"), ("positive psychology", "concept")],
     [("positive psychology", "Martin Seligman", "AUTHORED_BY"), ("positive psychology", "Mihaly Csikszentmihalyi", "AUTHORED_BY")],
     "whose joint 2000 editorial reoriented mainstream research toward human flourishing and strengths",
     "Seligman Csikszentmihalyi flourishing strengths editorial millennium year"),
    # --- 28 ---
    ("Seligman's 2011 Flourish revised his earlier authentic-happiness account by replacing it with the five-element PERMA model of well-being.", "decision", "knowledge", False,
     [("Seligman", "person"), ("Flourish", "publication"), ("2011", "date"), ("authentic-happiness account", "theory"), ("PERMA model", "framework")],
     [("Flourish", "Seligman", "AUTHORED_BY"), ("PERMA model", "authentic-happiness account", "REPLACES")],
     "which 2011 Seligman book replaced authentic happiness with the PERMA model",
     "Seligman Flourish PERMA well being authentic happiness replacement year"),
    # --- 29 ---
    ("Stanley Milgram's obedience experiments, reported from 1963 at Yale, demonstrated that ordinary adults would administer apparently dangerous shocks under authority pressure.", "reference", "knowledge", False,
     [("Stanley Milgram", "person"), ("obedience experiments", "event"), ("1963", "date"), ("Yale", "organization")],
     [("obedience experiments", "Stanley Milgram", "AUTHORED_BY")],
     "which 1963 Yale experiments showed ordinary adults obeying authority to deliver shocks",
     "Milgram obedience Yale authority shock experiments year"),
    # --- 30 ---
    ("Gina Perry's 2013 book Behind the Shock Machine, based on Milgram's Yale archive, contradicted the tidy obedience narrative by documenting participant scepticism and procedural deviations.", "fact", "knowledge", False,
     [("Gina Perry", "person"), ("Behind the Shock Machine", "publication"), ("2013", "date"), ("Milgram", "person"), ("Yale archive", "publication")],
     [("Behind the Shock Machine", "Gina Perry", "AUTHORED_BY"), ("Behind the Shock Machine", "Milgram", "CONTRADICTS")],
     "which 2013 archival book challenged the clean obedience narrative around Milgram",
     "Perry Behind Shock Machine Milgram archive critique year"),
    # --- 31 ---
    ("Philip Zimbardo's 1971 Stanford Prison Experiment is now routinely reframed as an ethically compromised demonstration rather than the definitive situationist study its original reports claimed.", "problem", "knowledge", False,
     [("Philip Zimbardo", "person"), ("Stanford Prison Experiment", "event"), ("1971", "date")],
     [("Stanford Prison Experiment", "Philip Zimbardo", "AUTHORED_BY")],
     "which 1971 Zimbardo study is now reread as an ethically compromised demonstration",
     "Zimbardo Stanford Prison Experiment situationism ethics year"),
    # --- 32 ---
    ("Thibault Le Texier's 2019 book Histoire d'un mensonge, based on the Stanford archives, contradicted the Stanford Prison Experiment's self-reported spontaneity by documenting staged coaching of guards.", "fact", "knowledge", False,
     [("Thibault Le Texier", "person"), ("Histoire d'un mensonge", "publication"), ("2019", "date"), ("Stanford archives", "publication"), ("Stanford Prison Experiment", "event")],
     [("Histoire d'un mensonge", "Thibault Le Texier", "AUTHORED_BY"), ("Histoire d'un mensonge", "Stanford Prison Experiment", "CONTRADICTS")],
     "which 2019 archival book contradicted the Stanford Prison Experiment's claim of spontaneous behaviour",
     "Le Texier Histoire mensonge Stanford Prison archive coaching year"),
    # --- 33 ---
    ("Jeff Greenberg, Sheldon Solomon, and Tom Pyszczynski's 1986 chapter in Public Self and Private Self formulated terror management theory around mortality salience effects.", "reference", "knowledge", False,
     [("Jeff Greenberg", "person"), ("Sheldon Solomon", "person"), ("Tom Pyszczynski", "person"), ("Public Self and Private Self", "publication"), ("1986", "date"), ("terror management theory", "theory"), ("mortality salience", "concept")],
     [("terror management theory", "Jeff Greenberg", "AUTHORED_BY"), ("terror management theory", "Sheldon Solomon", "AUTHORED_BY")],
     "whose late-1980s chapter built a social-psychology framework around death-awareness effects",
     "Greenberg Solomon Pyszczynski death awareness framework chapter late 1980s"),
    # --- 34. noise ---
    ("Let me pull up the codebook before I touch that coding scheme again.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("A 2022 registered-replication report in Nature Human Behaviour found only small and heterogeneous mortality-salience effects, complicating strong terror management claims.", "fact", "knowledge", False,
     [("registered-replication report", "method"), ("2022", "date"), ("Nature Human Behaviour", "publication"), ("mortality-salience", "concept"), ("terror management", "theory")],
     [("registered-replication report", "Nature Human Behaviour", "PUBLISHED_IN"), ("registered-replication report", "terror management", "CONTRADICTS")],
     "what did the early-2020s multi-site replication in a Nature sister journal reveal about death-awareness effect sizes",
     "multi site replication death awareness effect size sister journal early 2020s"),
    # --- 36 ---
    ("Jean Piaget's 1936 The Origins of Intelligence in Children articulated the four-stage developmental sequence from sensorimotor to formal operational thought.", "reference", "knowledge", False,
     [("Jean Piaget", "person"), ("The Origins of Intelligence in Children", "publication"), ("1936", "date"), ("sensorimotor", "concept"), ("formal operational", "concept")],
     [("The Origins of Intelligence in Children", "Jean Piaget", "AUTHORED_BY")],
     "which 1936 Piaget book set out the four-stage developmental sequence",
     "genetic epistemology stages child cognition Geneva monograph interwar"),
    # --- 37 ---
    ("Lev Vygotsky's Thought and Language, published posthumously in 1934, advanced a sociocultural account of development that improves on strictly individualist stage theories.", "reference", "knowledge", False,
     [("Lev Vygotsky", "person"), ("Thought and Language", "publication"), ("1934", "date"), ("sociocultural account", "theory"), ("individualist stage theories", "theory")],
     [("Thought and Language", "Lev Vygotsky", "AUTHORED_BY"), ("sociocultural account", "individualist stage theories", "IMPROVES_ON")],
     "which 1934 posthumous book framed development in sociocultural terms against individualist stages",
     "Vygotsky Thought Language sociocultural development year"),
    # --- 38 ---
    ("Lawrence Kohlberg's 1969 stage theory of moral reasoning, built on Piaget, was challenged by Carol Gilligan's 1982 In a Different Voice for privileging a male justice orientation.", "problem", "knowledge", False,
     [("Lawrence Kohlberg", "person"), ("1969", "date"), ("Piaget", "person"), ("Carol Gilligan", "person"), ("In a Different Voice", "publication"), ("1982", "date"), ("male justice orientation", "concept")],
     [("In a Different Voice", "Carol Gilligan", "AUTHORED_BY")],
     "which 1982 book challenged Kohlberg's moral-reasoning stages for privileging a male orientation",
     "Kohlberg Gilligan In Different Voice moral development critique year"),
    # --- 39 ---
    ("Mary Main and Judith Solomon's 1990 chapter in Attachment in the Preschool Years improves on Ainsworth's tripartite scheme by adding the disorganised attachment category.", "reference", "knowledge", False,
     [("Mary Main", "person"), ("Judith Solomon", "person"), ("1990", "date"), ("Attachment in the Preschool Years", "publication"), ("Ainsworth", "person"), ("disorganised attachment", "concept")],
     [("Attachment in the Preschool Years", "Mary Main", "AUTHORED_BY"), ("disorganised attachment", "Ainsworth", "IMPROVES_ON")],
     "which 1990 chapter added disorganised attachment to Ainsworth's tripartite scheme",
     "Main Solomon disorganised attachment Ainsworth extension chapter year"),
    # --- 40 ---
    ("Paul Meehl's 1954 Clinical Versus Statistical Prediction argued that simple actuarial rules systematically outperform unaided clinical judgment in diagnostic tasks.", "reference", "knowledge", False,
     [("Paul Meehl", "person"), ("Clinical Versus Statistical Prediction", "publication"), ("1954", "date"), ("actuarial rules", "method"), ("clinical judgment", "method")],
     [("Clinical Versus Statistical Prediction", "Paul Meehl", "AUTHORED_BY"), ("actuarial rules", "clinical judgment", "PREFERS")],
     "which 1954 Meehl book argued actuarial rules beat unaided clinical judgment",
     "Meehl clinical statistical prediction actuarial diagnosis year"),
    # --- 41 ---
    ("Elizabeth Loftus and John Palmer's 1974 Journal of Verbal Learning and Verbal Behavior paper demonstrated that leading questions systematically distort eyewitness memory.", "reference", "knowledge", False,
     [("Elizabeth Loftus", "person"), ("John Palmer", "person"), ("Journal of Verbal Learning and Verbal Behavior", "publication"), ("1974", "date"), ("eyewitness memory", "concept")],
     [("Journal of Verbal Learning and Verbal Behavior", "Elizabeth Loftus", "AUTHORED_BY")],
     "which 1974 Loftus and Palmer paper showed leading questions distort eyewitness memory",
     "Loftus Palmer eyewitness leading questions verbal learning year"),
    # --- 42 ---
    ("The DSM-III, published by the American Psychiatric Association in 1980, replaced the psychodynamically flavoured DSM-II with an operationalised, criterion-based system that reshaped clinical psychology.", "milestone", "knowledge", False,
     [("DSM-III", "publication"), ("American Psychiatric Association", "organization"), ("1980", "date"), ("DSM-II", "publication"), ("criterion-based system", "framework"), ("clinical psychology", "field")],
     [("DSM-III", "American Psychiatric Association", "AUTHORED_BY"), ("DSM-III", "DSM-II", "REPLACES")],
     "which 1980 manual replaced the psychodynamic DSM-II with operationalised criteria",
     "DSM-III DSM-II APA criterion based operationalised year"),
    # --- 43 ---
    ("Hans Eysenck's 1952 Journal of Consulting Psychology paper claimed psychotherapy showed no net benefit over spontaneous remission, provoking decades of outcome research.", "problem", "knowledge", False,
     [("Hans Eysenck", "person"), ("1952", "date"), ("Journal of Consulting Psychology", "publication"), ("psychotherapy", "concept"), ("spontaneous remission", "concept")],
     [("Journal of Consulting Psychology", "Hans Eysenck", "AUTHORED_BY")],
     "which 1952 Eysenck paper provoked decades of psychotherapy outcome research",
     "Eysenck 1952 psychotherapy effectiveness spontaneous remission year"),
    # --- 44 ---
    ("Mary Smith and Gene Glass's 1977 American Psychologist meta-analysis of 375 studies contradicted Eysenck's earlier claim by reporting a robust aggregate effect of psychotherapy.", "fact", "knowledge", False,
     [("Mary Smith", "person"), ("Gene Glass", "person"), ("1977", "date"), ("American Psychologist", "publication"), ("Eysenck", "person"), ("psychotherapy", "concept")],
     [("American Psychologist", "Mary Smith", "AUTHORED_BY"), ("Gene Glass", "Eysenck", "CONTRADICTS")],
     "which 1977 meta-analysis contradicted Eysenck's claim of zero psychotherapy benefit",
     "Smith Glass meta analysis psychotherapy Eysenck American Psychologist year"),
    # --- 45 ---
    ("Walter Mischel's 1968 Personality and Assessment challenged cross-situational trait consistency and reoriented personality psychology toward person-by-situation interactionism.", "decision", "knowledge", False,
     [("Walter Mischel", "person"), ("Personality and Assessment", "publication"), ("1968", "date"), ("cross-situational trait consistency", "concept"), ("interactionism", "theory")],
     [("Personality and Assessment", "Walter Mischel", "AUTHORED_BY"), ("interactionism", "cross-situational trait consistency", "REPLACES")],
     "which 1968 Mischel book pushed personality psychology toward person-by-situation interactionism",
     "Mischel Personality Assessment cross situational interactionism year"),
    # --- 46 ---
    ("Paul Costa and Robert McCrae's NEO-PI inventory, formalised in a 1985 manual, operationalised the five-factor model that now dominates trait-personality research.", "reference", "knowledge", False,
     [("Paul Costa", "person"), ("Robert McCrae", "person"), ("NEO-PI", "tool"), ("1985", "date"), ("five-factor model", "framework"), ("trait-personality research", "field")],
     [("NEO-PI", "Paul Costa", "AUTHORED_BY"), ("NEO-PI", "Robert McCrae", "AUTHORED_BY")],
     "which 1985 Costa and McCrae manual operationalised the five-factor personality model",
     "NEO-PI Costa McCrae five factor personality inventory year"),
    # --- 47 ---
    ("The APA-published journal Psychological Science in the Public Interest, launched in 2000, serves as the discipline's venue for consensus reviews on policy-relevant questions.", "reference", "knowledge", False,
     [("Psychological Science in the Public Interest", "publication"), ("2000", "date"), ("APA", "organization")],
     [("Psychological Science in the Public Interest", "APA", "AUTHORED_BY")],
     "which 2000-launched APA journal publishes consensus reviews on policy-relevant psychology",
     "Psychological Science Public Interest APA consensus reviews year"),
    # --- 48 ---
    ("Brian Nosek and colleagues' 2015 Science paper Promoting an Open Research Culture proposed the TOP Guidelines to standardise transparency across psychology journals.", "decision", "knowledge", False,
     [("Brian Nosek", "person"), ("2015", "date"), ("Science", "publication"), ("Promoting an Open Research Culture", "publication"), ("TOP Guidelines", "framework")],
     [("Promoting an Open Research Culture", "Brian Nosek", "AUTHORED_BY"), ("TOP Guidelines", "Brian Nosek", "AUTHORED_BY")],
     "which 2015 Science paper proposed the TOP Guidelines for journal transparency",
     "Nosek TOP Guidelines Science transparency openness year"),
    # --- 49 ---
    ("Chris Chambers's 2013 Cortex editorial formalised the registered-report format, which replaces results-contingent acceptance with pre-analysis peer review of methods.", "decision", "knowledge", False,
     [("Chris Chambers", "person"), ("2013", "date"), ("Cortex", "publication"), ("registered-report format", "method"), ("results-contingent acceptance", "method")],
     [("Cortex", "Chris Chambers", "AUTHORED_BY"), ("registered-report format", "results-contingent acceptance", "REPLACES")],
     "whose 2013 journal editorial codified pre-analysis peer review against outcome-based acceptance",
     "Chambers pre analysis review outcome independent editorial year"),
    # --- 50 ---
    ("Barbara Fredrickson's 1998 Review of General Psychology paper on the broaden-and-build theory reframes positive emotions as resources that widen momentary thought-action repertoires.", "reference", "knowledge", False,
     [("Barbara Fredrickson", "person"), ("Review of General Psychology", "publication"), ("1998", "date"), ("broaden-and-build theory", "theory"), ("positive emotions", "concept")],
     [("broaden-and-build theory", "Barbara Fredrickson", "AUTHORED_BY"), ("Review of General Psychology", "Barbara Fredrickson", "AUTHORED_BY")],
     "whose late-1990s paper framed upbeat affect as widening momentary thought-action repertoires",
     "Fredrickson affect widening thought action repertoire late 1990s paper"),
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
