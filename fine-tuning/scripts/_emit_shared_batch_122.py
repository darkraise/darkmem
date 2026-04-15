"""One-off emitter for shared-base batch-122 — knowledge domain (business/management research and organization theory).

Writes 50 rows with ids shared-06051..06100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_122.tmp.jsonl"
ID_OFFSET = 6050

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Michael Porter's Competitive Strategy, published in 1980, introduced the Five Forces framework for industry structural analysis.", "reference", "knowledge", False,
     [("Michael Porter", "person"), ("Competitive Strategy", "publication"), ("1980", "date"), ("Five Forces", "framework")],
     [("Competitive Strategy", "Michael Porter", "AUTHORED_BY"), ("Five Forces", "Michael Porter", "AUTHORED_BY")],
     "whose early-1980s monograph gave strategy scholarship its dominant structural-analysis template",
     "Harvard scholar industry rivalry buyers suppliers entrants substitutes framework"),
    # --- 2 ---
    ("Porter's generic strategies typology distinguishes cost leadership, differentiation, and focus as mutually exclusive competitive postures.", "fact", "knowledge", False,
     [("Porter", "person"), ("generic strategies", "framework"), ("cost leadership", "concept"), ("differentiation", "concept"), ("focus", "concept")],
     [("generic strategies", "Porter", "AUTHORED_BY")],
     "whose classical typology sorts competitive posture into three exclusive positions",
     "low cost broad differentiation niche segment scope posture choice"),
    # --- 3 ---
    ("Jay Barney's 1991 Journal of Management article codified the resource-based view, arguing that VRIN resources yield sustained competitive advantage.", "reference", "knowledge", False,
     [("Jay Barney", "person"), ("1991", "date"), ("Journal of Management", "publication"), ("resource-based view", "theory"), ("VRIN", "concept")],
     [("resource-based view", "Jay Barney", "AUTHORED_BY")],
     "which 1991 Barney article formalised the resource-based view around VRIN attributes",
     "Barney 1991 RBV VRIN sustained competitive advantage Journal of Management"),
    # --- 4 ---
    ("The resource-based view reframes strategy inward and improves on Porter's positioning school by locating advantage in firm-specific resources rather than industry structure.", "decision", "knowledge", False,
     [("resource-based view", "theory"), ("Porter's positioning school", "theory"), ("firm-specific resources", "concept"), ("industry structure", "concept")],
     [("resource-based view", "Porter's positioning school", "IMPROVES_ON")],
     "which strategy theory relocated advantage from industry structure to firm-specific resources",
     "RBV inside out positioning school resources industry structure"),
    # --- 5 ---
    ("David Teece, Gary Pisano, and Amy Shuen's 1997 Strategic Management Journal article on dynamic capabilities extends the resource-based view to address environmental change.", "reference", "knowledge", False,
     [("David Teece", "person"), ("Gary Pisano", "person"), ("Amy Shuen", "person"), ("1997", "date"), ("Strategic Management Journal", "publication"), ("dynamic capabilities", "theory"), ("resource-based view", "theory")],
     [("dynamic capabilities", "David Teece", "AUTHORED_BY"), ("dynamic capabilities", "resource-based view", "IMPROVES_ON")],
     "which 1997 SMJ paper extended the RBV by theorising dynamic capabilities",
     "Teece Pisano Shuen 1997 SMJ dynamic capabilities extension RBV"),
    # --- 6 ---
    ("Herbert Simon's Administrative Behavior, first published in 1947, grounds organisational decision-making in bounded rationality and satisficing rather than optimisation.", "reference", "knowledge", False,
     [("Herbert Simon", "person"), ("Administrative Behavior", "publication"), ("1947", "date"), ("bounded rationality", "theory"), ("satisficing", "concept")],
     [("Administrative Behavior", "Herbert Simon", "AUTHORED_BY"), ("bounded rationality", "Herbert Simon", "AUTHORED_BY")],
     "which 1947 Simon book founded bounded rationality and satisficing in administrative theory",
     "Simon Administrative Behavior 1947 bounded rationality satisficing decision"),
    # --- 7 ---
    ("James March and Herbert Simon's Organizations, published in 1958, consolidated the Carnegie School's behavioural treatment of firms as coalitions of bounded actors.", "reference", "knowledge", False,
     [("James March", "person"), ("Herbert Simon", "person"), ("Organizations", "publication"), ("1958", "date"), ("Carnegie School", "organization")],
     [("Organizations", "James March", "AUTHORED_BY"), ("Organizations", "Herbert Simon", "AUTHORED_BY")],
     "which 1958 March and Simon book consolidated the Carnegie behavioural view of firms",
     "March Simon Organizations 1958 Carnegie School bounded coalition"),
    # --- 8 ---
    ("Richard Cyert and James March's A Behavioral Theory of the Firm, published in 1963, models firms as coalitions negotiating goals under uncertainty and quasi-resolution of conflict.", "reference", "knowledge", False,
     [("Richard Cyert", "person"), ("James March", "person"), ("A Behavioral Theory of the Firm", "publication"), ("1963", "date"), ("quasi-resolution of conflict", "concept")],
     [("A Behavioral Theory of the Firm", "Richard Cyert", "AUTHORED_BY"), ("A Behavioral Theory of the Firm", "James March", "AUTHORED_BY")],
     "which 1963 Cyert and March book framed firms as coalitions with quasi-resolution of conflict",
     "Cyert March 1963 Behavioral Theory Firm coalition quasi resolution"),
    # --- 9 ---
    ("The behavioural theory of the firm replaces neoclassical profit maximisation with bounded aspiration adjustment and attention-driven search.", "decision", "knowledge", False,
     [("behavioural theory of the firm", "theory"), ("neoclassical profit maximisation", "theory"), ("aspiration adjustment", "concept"), ("attention-driven search", "concept")],
     [("behavioural theory of the firm", "neoclassical profit maximisation", "REPLACES")],
     "what framework swaps out optimising profit assumptions for goal adaptation and local search",
     "Carnegie tradition aspiration level problemistic search coalition bargaining"),
    # --- 10. noise ---
    ("Let me pull the original Academy of Management Review page range before I quote it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Oliver Williamson's Markets and Hierarchies, published in 1975, frames the choice between firms and markets as a transaction-cost minimisation problem.", "reference", "knowledge", False,
     [("Oliver Williamson", "person"), ("Markets and Hierarchies", "publication"), ("1975", "date"), ("transaction-cost", "theory")],
     [("Markets and Hierarchies", "Oliver Williamson", "AUTHORED_BY")],
     "which 1975 Williamson book framed firms versus markets as transaction-cost minimisation",
     "Williamson Markets Hierarchies 1975 transaction cost governance"),
    # --- 12 ---
    ("Williamson's transaction-cost economics builds on Ronald Coase's 1937 article The Nature of the Firm by adding asset specificity and opportunism as governance drivers.", "fact", "knowledge", False,
     [("Williamson", "person"), ("transaction-cost economics", "theory"), ("Ronald Coase", "person"), ("The Nature of the Firm", "publication"), ("1937", "date"), ("asset specificity", "concept"), ("opportunism", "concept")],
     [("transaction-cost economics", "The Nature of the Firm", "BUILDS_ON")],
     "whose governance programme grew out of Coase's 1937 essay by adding specificity and opportunism",
     "transaction cost lineage Coase descendant governance specificity motive"),
    # --- 13 ---
    ("Henry Mintzberg's The Structuring of Organizations, published in 1979, classifies firms into simple structure, machine bureaucracy, professional bureaucracy, divisionalised form, and adhocracy.", "reference", "knowledge", False,
     [("Henry Mintzberg", "person"), ("The Structuring of Organizations", "publication"), ("1979", "date"), ("machine bureaucracy", "concept"), ("adhocracy", "concept")],
     [("The Structuring of Organizations", "Henry Mintzberg", "AUTHORED_BY")],
     "which 1979 Mintzberg book sorted firms into five structural configurations from simple to adhocracy",
     "Mintzberg structuring organizations 1979 configurations adhocracy bureaucracy"),
    # --- 14 ---
    ("Mintzberg's 1973 The Nature of Managerial Work replaces Henri Fayol's planning-organising-commanding portrait with ten empirically observed managerial roles.", "decision", "knowledge", False,
     [("Mintzberg", "person"), ("The Nature of Managerial Work", "publication"), ("1973", "date"), ("Henri Fayol", "person"), ("ten empirically observed managerial roles", "framework")],
     [("The Nature of Managerial Work", "Mintzberg", "AUTHORED_BY"), ("ten empirically observed managerial roles", "Henri Fayol", "REPLACES")],
     "which Mintzberg study replaced Fayol's classical functions with ten observed managerial roles",
     "Mintzberg 1973 managerial work Fayol functions ten roles replacement"),
    # --- 15 ---
    ("Peter Drucker's The Age of Discontinuity, published in 1969, coined the term knowledge worker and predicted the rise of the knowledge economy.", "milestone", "knowledge", False,
     [("Peter Drucker", "person"), ("The Age of Discontinuity", "publication"), ("1969", "date"), ("knowledge worker", "concept"), ("knowledge economy", "concept")],
     [("The Age of Discontinuity", "Peter Drucker", "AUTHORED_BY"), ("knowledge worker", "Peter Drucker", "AUTHORED_BY")],
     "whose late-1960s volume gave us the vocabulary of post-industrial intellectual labour",
     "Vienna born management thinker post industrial intellect labour vocabulary"),
    # --- 16 ---
    ("John Kotter's Leading Change, published in 1996, presented an eight-step sequence running from establishing urgency to anchoring gains in culture.", "reference", "knowledge", False,
     [("John Kotter", "person"), ("Leading Change", "publication"), ("1996", "date"), ("eight-step sequence", "framework")],
     [("Leading Change", "John Kotter", "AUTHORED_BY"), ("eight-step sequence", "John Kotter", "AUTHORED_BY")],
     "which 1996 Kotter book laid out the eight-step change sequence from urgency to anchoring",
     "Kotter Leading Change 1996 eight step urgency anchoring change model"),
    # --- 17 ---
    ("Kathleen Eisenhardt and Shona Brown's 1998 Competing on the Edge proposes an eight-step change programme that improves on Kotter by emphasising continuous edge-of-chaos adaptation.", "reference", "knowledge", False,
     [("Kathleen Eisenhardt", "person"), ("Shona Brown", "person"), ("Competing on the Edge", "publication"), ("1998", "date"), ("eight-step change programme", "framework"), ("Kotter", "person")],
     [("Competing on the Edge", "Kathleen Eisenhardt", "AUTHORED_BY"), ("eight-step change programme", "Kotter", "IMPROVES_ON")],
     "which 1998 Eisenhardt and Brown book updates Kotter's change sequence for continuous adaptation",
     "Eisenhardt Brown Competing Edge 1998 eight step edge chaos Kotter"),
    # --- 18 ---
    ("Clayton Christensen's The Innovator's Dilemma, published in 1997, introduced disruptive innovation theory and the mechanism by which incumbent firms lose markets to low-end entrants.", "reference", "knowledge", False,
     [("Clayton Christensen", "person"), ("The Innovator's Dilemma", "publication"), ("1997", "date"), ("disruptive innovation", "theory"), ("low-end entrants", "concept")],
     [("The Innovator's Dilemma", "Clayton Christensen", "AUTHORED_BY"), ("disruptive innovation", "Clayton Christensen", "AUTHORED_BY")],
     "which 1997 Christensen book introduced disruptive innovation theory of incumbent failure",
     "Christensen Innovator Dilemma 1997 disruptive innovation low end incumbent"),
    # --- 19 ---
    ("Disruptive innovation theory improves on sustaining-innovation accounts by explaining why rational resource allocation causes successful incumbents to vacate low-end segments.", "fact", "knowledge", False,
     [("Disruptive innovation theory", "theory"), ("sustaining-innovation accounts", "theory"), ("rational resource allocation", "concept"), ("incumbents", "concept")],
     [("Disruptive innovation theory", "sustaining-innovation accounts", "IMPROVES_ON")],
     "which innovation theory explains rational incumbents losing low-end segments better than sustaining accounts",
     "disruptive sustaining innovation resource allocation incumbent exit"),
    # --- 20 ---
    ("Daniel Katz and Robert Kahn's The Social Psychology of Organizations, published in 1966, imported open-systems theory from biology into organisational analysis.", "reference", "knowledge", False,
     [("Daniel Katz", "person"), ("Robert Kahn", "person"), ("The Social Psychology of Organizations", "publication"), ("1966", "date"), ("open-systems theory", "theory")],
     [("The Social Psychology of Organizations", "Daniel Katz", "AUTHORED_BY"), ("The Social Psychology of Organizations", "Robert Kahn", "AUTHORED_BY")],
     "whose mid-1960s volume brought biological open-systems reasoning into firm-level analysis",
     "biology borrowed cycles environment exchange sociology firm"),
    # --- 21 ---
    ("Katz and Kahn's open-systems view replaces closed-system machine models of organisation with input-throughput-output cycles that exchange with their environment.", "decision", "knowledge", False,
     [("Katz and Kahn", "person"), ("open-systems view", "theory"), ("closed-system machine models", "theory"), ("input-throughput-output cycles", "concept")],
     [("open-systems view", "closed-system machine models", "REPLACES")],
     "which organisational perspective displaced closed machine models with input-output cycles",
     "open closed systems machine models Katz Kahn throughput"),
    # --- 22 ---
    ("Geert Hofstede's Culture's Consequences, published in 1980, operationalised national culture along power distance, individualism, masculinity, and uncertainty-avoidance dimensions.", "reference", "knowledge", False,
     [("Geert Hofstede", "person"), ("Culture's Consequences", "publication"), ("1980", "date"), ("power distance", "concept"), ("individualism", "concept"), ("uncertainty-avoidance", "concept")],
     [("Culture's Consequences", "Geert Hofstede", "AUTHORED_BY")],
     "which 1980 Hofstede book quantified national culture along four canonical dimensions",
     "Hofstede Culture Consequences 1980 power distance individualism masculinity"),
    # --- 23 ---
    ("Bruce Tuckman's 1965 Psychological Bulletin article proposed the forming-storming-norming-performing sequence of small-group development.", "reference", "knowledge", False,
     [("Bruce Tuckman", "person"), ("1965", "date"), ("Psychological Bulletin", "publication"), ("forming-storming-norming-performing", "framework")],
     [("forming-storming-norming-performing", "Bruce Tuckman", "AUTHORED_BY")],
     "whose mid-1960s review article laid out the canonical stage sequence for small-team growth",
     "group development four stages small team canonical sequence review"),
    # --- 24 ---
    ("Michael Tushman and Charles O'Reilly's ambidexterity theory, developed through the 1990s, argues that long-lived firms must simultaneously exploit current businesses and explore new ones.", "fact", "knowledge", False,
     [("Michael Tushman", "person"), ("Charles O'Reilly", "person"), ("ambidexterity theory", "theory"), ("exploit", "concept"), ("explore", "concept")],
     [("ambidexterity theory", "Michael Tushman", "AUTHORED_BY"), ("ambidexterity theory", "Charles O'Reilly", "AUTHORED_BY")],
     "whose organisational framework pairs refinement of current business with discovery of new ones",
     "dual structure long lived firm balance refinement discovery"),
    # --- 25 ---
    ("James March's 1991 Organization Science article Exploration and Exploitation in Organizational Learning anchors ambidexterity theory in a learning trade-off.", "reference", "knowledge", False,
     [("James March", "person"), ("1991", "date"), ("Organization Science", "publication"), ("Exploration and Exploitation in Organizational Learning", "publication"), ("ambidexterity theory", "theory")],
     [("Exploration and Exploitation in Organizational Learning", "James March", "AUTHORED_BY"), ("ambidexterity theory", "Exploration and Exploitation in Organizational Learning", "BUILDS_ON")],
     "which 1991 March article in Organization Science underpinned ambidexterity with an exploration-exploitation trade-off",
     "March 1991 exploration exploitation Organization Science learning trade off"),
    # --- 26 ---
    ("Eric Ries's The Lean Startup, published in 2011, reframes new-venture management around validated learning and build-measure-learn loops, later studied in academic entrepreneurship research.", "reference", "knowledge", False,
     [("Eric Ries", "person"), ("The Lean Startup", "publication"), ("2011", "date"), ("validated learning", "concept"), ("build-measure-learn", "framework"), ("entrepreneurship research", "field")],
     [("The Lean Startup", "Eric Ries", "AUTHORED_BY")],
     "which 2011 Ries book framed startups around validated learning and build-measure-learn",
     "Ries Lean Startup 2011 validated learning build measure learn entrepreneurship"),
    # --- 27 ---
    ("The lean startup approach improves on traditional business-plan-first venture models by privileging experimentation and pivot decisions over upfront forecasting.", "decision", "knowledge", False,
     [("lean startup approach", "method"), ("traditional business-plan-first venture models", "method"), ("experimentation", "concept"), ("pivot decisions", "concept"), ("upfront forecasting", "concept")],
     [("lean startup approach", "traditional business-plan-first venture models", "IMPROVES_ON"), ("experimentation", "upfront forecasting", "PREFERS")],
     "which venture approach displaces upfront business-plan forecasting with experimentation and pivots",
     "lean startup business plan first pivot experimentation forecasting"),
    # --- 28 ---
    ("The Academy of Management Review, established in 1976, is the flagship journal for conceptual and theoretical contributions in management scholarship.", "reference", "knowledge", False,
     [("Academy of Management Review", "publication"), ("1976", "date"), ("management scholarship", "field")],
     [],
     "which 1976 journal serves as the flagship outlet for management theory development",
     "Academy of Management Review AMR 1976 theoretical management journal"),
    # --- 29 ---
    ("Administrative Science Quarterly, launched from Cornell in 1956, became the leading outlet for sociologically oriented organisation theory.", "reference", "knowledge", False,
     [("Administrative Science Quarterly", "publication"), ("Cornell", "organization"), ("1956", "date"), ("organisation theory", "field")],
     [],
     "which mid-1950s Cornell-based quarterly anchors sociologically oriented firm research",
     "Ithaca founded quarterly sociology anchored field organisation studies"),
    # --- 30 ---
    ("The Strategic Management Journal, founded in 1980, consolidated strategy research as a distinct scholarly field with its own methodological standards.", "reference", "knowledge", False,
     [("Strategic Management Journal", "publication"), ("1980", "date"), ("strategy research", "field")],
     [],
     "which early-1980s periodical turned corporate-strategy work into its own scholarly field",
     "founding strategy periodical discipline crystallisation methodology early 80s"),
    # --- 31 ---
    ("Organization Science, launched in 1990 by INFORMS, positioned itself as a multidisciplinary outlet for rigorous micro and macro organisational research.", "reference", "knowledge", False,
     [("Organization Science", "publication"), ("1990", "date"), ("INFORMS", "organization"), ("organisational research", "field")],
     [],
     "which 1990 INFORMS journal framed itself around multidisciplinary organisational research",
     "Organization Science 1990 INFORMS multidisciplinary micro macro"),
    # --- 32 ---
    ("Michael Hannan and John Freeman's 1977 American Journal of Sociology article The Population Ecology of Organizations founded organisational ecology by applying density-dependent selection to firm populations.", "reference", "knowledge", False,
     [("Michael Hannan", "person"), ("John Freeman", "person"), ("1977", "date"), ("American Journal of Sociology", "publication"), ("The Population Ecology of Organizations", "publication"), ("organisational ecology", "theory"), ("density-dependent selection", "concept")],
     [("The Population Ecology of Organizations", "Michael Hannan", "AUTHORED_BY"), ("The Population Ecology of Organizations", "John Freeman", "AUTHORED_BY")],
     "which 1977 Hannan and Freeman article founded organisational ecology around density dependence",
     "Hannan Freeman 1977 population ecology organisations density dependent"),
    # --- 33 ---
    ("Paul DiMaggio and Walter Powell's 1983 ASQ article The Iron Cage Revisited theorised coercive, mimetic, and normative institutional isomorphism among organisations.", "reference", "knowledge", False,
     [("Paul DiMaggio", "person"), ("Walter Powell", "person"), ("1983", "date"), ("ASQ", "publication"), ("The Iron Cage Revisited", "publication"), ("institutional isomorphism", "theory")],
     [("The Iron Cage Revisited", "Paul DiMaggio", "AUTHORED_BY"), ("The Iron Cage Revisited", "Walter Powell", "AUTHORED_BY"), ("institutional isomorphism", "Paul DiMaggio", "AUTHORED_BY")],
     "which early-1980s cage-revisiting paper introduced the three-pressure model of firm convergence",
     "coercive mimetic normative pressures convergence firms cage revisited"),
    # --- 34. noise ---
    ("I should recheck whether that SMJ issue is the May or August number before pulling the citation.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Jeffrey Pfeffer and Gerald Salancik's The External Control of Organizations, published in 1978, articulated resource-dependence theory as an alternative to closed rational models.", "reference", "knowledge", False,
     [("Jeffrey Pfeffer", "person"), ("Gerald Salancik", "person"), ("The External Control of Organizations", "publication"), ("1978", "date"), ("resource-dependence theory", "theory"), ("closed rational models", "theory")],
     [("The External Control of Organizations", "Jeffrey Pfeffer", "AUTHORED_BY"), ("resource-dependence theory", "closed rational models", "IMPROVES_ON")],
     "which 1978 Pfeffer and Salancik book framed resource-dependence theory against closed rational models",
     "Pfeffer Salancik 1978 External Control resource dependence closed rational"),
    # --- 36 ---
    ("Alfred Chandler's Strategy and Structure, published in 1962, established the historical thesis that organisational structure follows strategic choice in large diversified firms.", "reference", "knowledge", False,
     [("Alfred Chandler", "person"), ("Strategy and Structure", "publication"), ("1962", "date"), ("organisational structure", "concept"), ("strategic choice", "concept")],
     [("Strategy and Structure", "Alfred Chandler", "AUTHORED_BY")],
     "which 1962 Chandler book argued that organisational structure follows strategic choice",
     "Chandler Strategy Structure 1962 diversified firm structure follows"),
    # --- 37 ---
    ("Edith Penrose's The Theory of the Growth of the Firm, published in 1959, anticipated the resource-based view by locating growth limits in managerial and resource capabilities.", "reference", "knowledge", False,
     [("Edith Penrose", "person"), ("The Theory of the Growth of the Firm", "publication"), ("1959", "date"), ("resource-based view", "theory"), ("managerial and resource capabilities", "concept")],
     [("The Theory of the Growth of the Firm", "Edith Penrose", "AUTHORED_BY"), ("resource-based view", "The Theory of the Growth of the Firm", "BUILDS_ON")],
     "which 1959 Penrose book foreshadowed the RBV by locating growth in managerial capabilities",
     "Penrose 1959 Theory Growth Firm managerial capabilities resource"),
    # --- 38 ---
    ("Karl Weick's The Social Psychology of Organizing, first published in 1969, recentered organisation theory on ongoing sensemaking rather than on fixed structures.", "decision", "knowledge", False,
     [("Karl Weick", "person"), ("The Social Psychology of Organizing", "publication"), ("1969", "date"), ("organisation theory", "field"), ("sensemaking", "concept"), ("fixed structures", "concept")],
     [("The Social Psychology of Organizing", "Karl Weick", "AUTHORED_BY"), ("sensemaking", "fixed structures", "PREFERS")],
     "which Weick book shifted organisation theory from fixed structure toward ongoing sensemaking",
     "Weick 1969 Social Psychology Organizing sensemaking structure shift"),
    # --- 39 ---
    ("Robert Kaplan and David Norton's 1992 Harvard Business Review article introduced the Balanced Scorecard as a multi-dimensional performance-measurement framework.", "reference", "knowledge", False,
     [("Robert Kaplan", "person"), ("David Norton", "person"), ("1992", "date"), ("Harvard Business Review", "publication"), ("Balanced Scorecard", "framework"), ("performance-measurement framework", "concept")],
     [("Balanced Scorecard", "Robert Kaplan", "AUTHORED_BY"), ("Balanced Scorecard", "David Norton", "AUTHORED_BY")],
     "whose early-1990s HBR essay unveiled a multi-perspective dashboard for gauging firm performance",
     "accounting scholars dashboard multi perspective early 90s Review"),
    # --- 40 ---
    ("W. Chan Kim and Renee Mauborgne's Blue Ocean Strategy, published in 2005, argues for creating uncontested market space instead of competing within Porter-style industry boundaries.", "decision", "knowledge", False,
     [("W. Chan Kim", "person"), ("Renee Mauborgne", "person"), ("Blue Ocean Strategy", "publication"), ("2005", "date"), ("uncontested market space", "concept"), ("Porter-style industry boundaries", "concept")],
     [("Blue Ocean Strategy", "W. Chan Kim", "AUTHORED_BY"), ("uncontested market space", "Porter-style industry boundaries", "PREFERS")],
     "which 2005 Kim and Mauborgne book favoured uncontested market space over Porter-style competition",
     "Kim Mauborgne 2005 Blue Ocean uncontested Porter industry boundaries"),
    # --- 41 ---
    ("Michael Jensen and William Meckling's 1976 Journal of Financial Economics article formalised agency theory around shareholder-manager conflicts and monitoring costs.", "reference", "knowledge", False,
     [("Michael Jensen", "person"), ("William Meckling", "person"), ("1976", "date"), ("Journal of Financial Economics", "publication"), ("agency theory", "theory"), ("monitoring costs", "concept")],
     [("agency theory", "Michael Jensen", "AUTHORED_BY"), ("agency theory", "William Meckling", "AUTHORED_BY")],
     "whose mid-1970s finance paper formalised principal-agent tensions inside the modern corporation",
     "principal agent finance paper mid 70s ownership control separation"),
    # --- 42 ---
    ("R. Edward Freeman's Strategic Management: A Stakeholder Approach, published in 1984, argued that firms should be accountable to a broader set of stakeholders than shareholders alone.", "reference", "knowledge", False,
     [("R. Edward Freeman", "person"), ("Strategic Management: A Stakeholder Approach", "publication"), ("1984", "date"), ("stakeholders", "concept"), ("shareholders", "concept")],
     [("Strategic Management: A Stakeholder Approach", "R. Edward Freeman", "AUTHORED_BY")],
     "which 1984 Freeman book founded stakeholder theory against a shareholder-only view",
     "Freeman 1984 Stakeholder Approach stakeholder shareholder accountability"),
    # --- 43 ---
    ("Stakeholder theory improves on shareholder-primacy doctrine by incorporating normative claims from employees, customers, suppliers, and communities into strategy.", "fact", "knowledge", False,
     [("Stakeholder theory", "theory"), ("shareholder-primacy doctrine", "theory"), ("employees", "concept"), ("customers", "concept"), ("suppliers", "concept"), ("communities", "concept")],
     [("Stakeholder theory", "shareholder-primacy doctrine", "IMPROVES_ON")],
     "which strategy theory widened the firm's obligations beyond shareholders to other stakeholders",
     "stakeholder theory shareholder primacy employees customers communities"),
    # --- 44 ---
    ("Raymond Miles and Charles Snow's 1978 book Organizational Strategy, Structure, and Process classified firms as defenders, prospectors, analysers, or reactors.", "reference", "knowledge", False,
     [("Raymond Miles", "person"), ("Charles Snow", "person"), ("1978", "date"), ("Organizational Strategy, Structure, and Process", "publication"), ("defenders", "concept"), ("prospectors", "concept"), ("analysers", "concept"), ("reactors", "concept")],
     [("Organizational Strategy, Structure, and Process", "Raymond Miles", "AUTHORED_BY"), ("Organizational Strategy, Structure, and Process", "Charles Snow", "AUTHORED_BY")],
     "which 1978 Miles and Snow book sorted firms into defenders, prospectors, analysers, and reactors",
     "Miles Snow 1978 defender prospector analyser reactor typology"),
    # --- 45 ---
    ("John Child's 1972 article Organizational Structure, Environment, and Performance introduced strategic choice as a corrective to environmental-determinism in contingency theory.", "reference", "knowledge", False,
     [("John Child", "person"), ("1972", "date"), ("Organizational Structure, Environment, and Performance", "publication"), ("strategic choice", "concept"), ("environmental-determinism", "theory"), ("contingency theory", "theory")],
     [("Organizational Structure, Environment, and Performance", "John Child", "AUTHORED_BY"), ("strategic choice", "environmental-determinism", "IMPROVES_ON")],
     "which early-1970s paper pushed back against deterministic contingency by foregrounding managerial choice",
     "managerial agency pushback against deterministic contingency early 70s"),
    # --- 46 ---
    ("Ikujiro Nonaka's 1994 Organization Science article A Dynamic Theory of Organizational Knowledge Creation modelled the SECI spiral of tacit-explicit knowledge conversion.", "reference", "knowledge", False,
     [("Ikujiro Nonaka", "person"), ("1994", "date"), ("Organization Science", "publication"), ("A Dynamic Theory of Organizational Knowledge Creation", "publication"), ("SECI spiral", "framework")],
     [("A Dynamic Theory of Organizational Knowledge Creation", "Ikujiro Nonaka", "AUTHORED_BY"), ("SECI spiral", "Ikujiro Nonaka", "AUTHORED_BY")],
     "which 1994 Nonaka article modelled tacit-explicit knowledge conversion as the SECI spiral",
     "Nonaka 1994 Organization Science SECI tacit explicit knowledge"),
    # --- 47 ---
    ("Rosabeth Moss Kanter's Men and Women of the Corporation, published in 1977, empirically linked tokenism and opportunity structures to gendered behaviour inside firms.", "reference", "knowledge", False,
     [("Rosabeth Moss Kanter", "person"), ("Men and Women of the Corporation", "publication"), ("1977", "date"), ("tokenism", "concept"), ("opportunity structures", "concept")],
     [("Men and Women of the Corporation", "Rosabeth Moss Kanter", "AUTHORED_BY")],
     "which 1977 Kanter book tied tokenism and opportunity structure to gendered corporate behaviour",
     "Kanter 1977 Men Women Corporation tokenism opportunity structures"),
    # --- 48 ---
    ("Kathleen Eisenhardt's 1989 Academy of Management Review article Building Theories from Case Study Research codified inductive theory-building from small-N cases.", "reference", "knowledge", False,
     [("Kathleen Eisenhardt", "person"), ("1989", "date"), ("Academy of Management Review", "publication"), ("Building Theories from Case Study Research", "publication"), ("inductive theory-building", "method")],
     [("Building Theories from Case Study Research", "Kathleen Eisenhardt", "AUTHORED_BY"), ("inductive theory-building", "Kathleen Eisenhardt", "AUTHORED_BY")],
     "which 1989 Eisenhardt AMR article codified inductive theory-building from case studies",
     "Eisenhardt 1989 AMR case study inductive theory building"),
    # --- 49 ---
    ("Constance Helfat and colleagues' Dynamic Capabilities: Understanding Strategic Change in Organizations, published in 2007, operationalised dynamic capabilities for empirical research.", "reference", "knowledge", False,
     [("Constance Helfat", "person"), ("Dynamic Capabilities: Understanding Strategic Change in Organizations", "publication"), ("2007", "date"), ("dynamic capabilities", "theory"), ("empirical research", "field")],
     [("Dynamic Capabilities: Understanding Strategic Change in Organizations", "Constance Helfat", "AUTHORED_BY"), ("Dynamic Capabilities: Understanding Strategic Change in Organizations", "dynamic capabilities", "BUILDS_ON")],
     "which 2007 Helfat-led book operationalised dynamic capabilities for empirical strategy research",
     "Helfat 2007 dynamic capabilities strategic change empirical operationalisation"),
    # --- 50 ---
    ("Sidney Winter's 2003 Strategic Management Journal article Understanding Dynamic Capabilities distinguished ordinary operating routines from higher-order dynamic capabilities.", "reference", "knowledge", False,
     [("Sidney Winter", "person"), ("2003", "date"), ("Strategic Management Journal", "publication"), ("Understanding Dynamic Capabilities", "publication"), ("operating routines", "concept"), ("dynamic capabilities", "theory")],
     [("Understanding Dynamic Capabilities", "Sidney Winter", "AUTHORED_BY")],
     "whose early-2000s evolutionary-economics paper clarified the hierarchy of firm routines and capabilities",
     "evolutionary economics hierarchy routines capabilities early 2000s paper"),
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
