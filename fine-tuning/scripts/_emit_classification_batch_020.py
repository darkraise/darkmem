"""One-off emitter for classification top-up batch-020 - contrastive_reference_fact mode, social science / psychology slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_020.tmp.jsonl with ids class-01901..02000.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_020.tmp.jsonl"
ID_OFFSET = 1900
PAIR_OFFSET = 700

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text cites a named psychology/sociology paper, named study, or journal.
# fact_text asserts the same behavioural or social claim without the citation.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Milgram obedience (social psych)
    (
        "Stanley Milgram, 'Behavioral Study of Obedience', Journal of Abnormal and Social Psychology 67 (1963) 371-378, reported that 65 percent of adult participants continued to deliver what they believed were increasingly severe electric shocks to a confederate at the instruction of an experimenter.",
        "knowledge",
        "Under direct instruction from a perceived authority figure, a large majority of ordinary adults are willing to administer what they believe are dangerous electric shocks to another person.",
        "knowledge",
    ),
    # 2. Bandura Bobo doll (developmental / social learning)
    (
        "Bandura, Ross, and Ross, 'Transmission of Aggression through Imitation of Aggressive Models', Journal of Abnormal and Social Psychology 63 (1961) 575-582, showed that children who observed an adult model attack a Bobo doll later reproduced the same aggressive behaviour more often than control children.",
        "knowledge",
        "Young children who watch adults behave aggressively toward an inflatable doll are substantially more likely to imitate that aggression themselves when given the opportunity.",
        "knowledge",
    ),
    # 3. Baumeister & Leary belongingness (social psych / personality)
    (
        "Baumeister and Leary, 'The Need to Belong: Desire for Interpersonal Attachments as a Fundamental Human Motivation', Psychological Bulletin 117 (1995) 497-529, argued that the need for stable, caring social bonds is a pervasive and fundamental human motive with broad cognitive, emotional, and health consequences.",
        "knowledge",
        "The drive to form and maintain lasting interpersonal bonds is a basic human motivation, and persistent failure to satisfy it is linked to poorer mental and physical health outcomes.",
        "knowledge",
    ),
    # 4. Kahneman & Tversky heuristics (behavioural economics)
    (
        "Tversky and Kahneman, 'Judgment under Uncertainty: Heuristics and Biases', Science 185 (1974) 1124-1131, described how people rely on a small number of cognitive heuristics - representativeness, availability, and anchoring - that produce systematic deviations from normative probability judgments.",
        "knowledge",
        "When estimating probabilities people rely on mental shortcuts such as how typical an example seems, how easily instances come to mind, and whichever number was suggested first, leading to predictable biases.",
        "knowledge",
    ),
    # 5. Kahneman & Tversky prospect theory (behavioural economics)
    (
        "Kahneman and Tversky, 'Prospect Theory: An Analysis of Decision under Risk', Econometrica 47 (1979) 263-292, introduced a model in which people evaluate outcomes as gains or losses from a reference point and are roughly twice as sensitive to losses as to equivalent gains.",
        "knowledge",
        "People evaluate risky outcomes relative to a reference point rather than in terms of final wealth, and a loss of a given size generally feels about twice as intense as a gain of the same size.",
        "knowledge",
    ),
    # 6. Asch conformity (social psych)
    (
        "Solomon Asch, 'Studies of Independence and Conformity: A Minority of One Against a Unanimous Majority', Psychological Monographs 70 (1956), reported that about one-third of participants conformed to a unanimous but clearly incorrect group judgment on a simple line-matching task.",
        "knowledge",
        "When a unanimous group gives an obviously wrong answer on a simple perceptual task, a substantial fraction of individuals will publicly agree with the group rather than report what they actually see.",
        "knowledge",
    ),
    # 7. Festinger cognitive dissonance (social psych)
    (
        "Festinger and Carlsmith, 'Cognitive Consequences of Forced Compliance', Journal of Abnormal and Social Psychology 58 (1959) 203-210, found that participants paid only one dollar to describe a boring task as enjoyable later rated the task more favorably than those paid twenty dollars.",
        "knowledge",
        "People who are induced to publicly endorse a position for a small reward later come to hold that position more sincerely than people paid a large reward for the same endorsement.",
        "knowledge",
    ),
    # 8. Zimbardo Stanford Prison (social psych)
    (
        "Haney, Banks, and Zimbardo, 'Interpersonal Dynamics in a Simulated Prison', International Journal of Criminology and Penology 1 (1973) 69-97, reported that college students randomly assigned to guard and prisoner roles rapidly adopted abusive and submissive behaviour, forcing early termination of the study.",
        "knowledge",
        "Assigning ordinary people to strong social roles such as guard and prisoner in a simulated institution can rapidly produce coercive behaviour on one side and submission on the other.",
        "knowledge",
    ),
    # 9. Rosenhan being sane in insane places (clinical psych)
    (
        "David Rosenhan, 'On Being Sane in Insane Places', Science 179 (1973) 250-258, described how pseudopatients who briefly feigned a single symptom were admitted to psychiatric hospitals and then diagnosed as mentally ill despite subsequently behaving normally.",
        "knowledge",
        "Once people are labelled as psychiatric patients, staff in mental hospitals tend to reinterpret their normal behaviour through the lens of the diagnosis and have difficulty recognising them as sane.",
        "knowledge",
    ),
    # 10. Ainsworth Strange Situation (developmental psych)
    (
        "Ainsworth, Blehar, Waters, and Wall, Patterns of Attachment (Lawrence Erlbaum, 1978), introduced the Strange Situation procedure and classified infant-caregiver attachment as secure, anxious-resistant, or anxious-avoidant.",
        "knowledge",
        "Infants' responses to brief separation from and reunion with a caregiver fall into recognisable attachment patterns, including secure, anxious-resistant, and anxious-avoidant styles.",
        "knowledge",
    ),
    # 11. Piaget conservation (developmental psych)
    (
        "Jean Piaget, The Child's Conception of Number (Routledge and Kegan Paul, 1952), documented that children below about seven years typically fail conservation-of-number tasks in which physical rearrangement changes perceived quantity.",
        "knowledge",
        "Young children under roughly seven years of age often judge that the number of objects has changed when the objects are simply spread out or rearranged in space.",
        "knowledge",
    ),
    # 12. Harlow surrogate mothers (developmental / comparative psych)
    (
        "Harry Harlow, 'The Nature of Love', American Psychologist 13 (1958) 673-685, reported that infant rhesus monkeys strongly preferred a cloth surrogate mother that provided contact comfort over a wire surrogate that provided food.",
        "knowledge",
        "Infant monkeys separated from their mothers prefer a soft cloth-covered surrogate that offers contact comfort over a wire surrogate that only provides food.",
        "knowledge",
    ),
    # 13. Seligman learned helplessness (clinical psych)
    (
        "Seligman and Maier, 'Failure to Escape Traumatic Shock', Journal of Experimental Psychology 74 (1967) 1-9, showed that dogs exposed to inescapable shock later failed to escape or avoid shocks they could control, a phenomenon termed learned helplessness.",
        "knowledge",
        "Animals and humans repeatedly exposed to aversive events they cannot control tend to stop trying to escape such events even when escape later becomes possible.",
        "knowledge",
    ),
    # 14. Beck cognitive therapy for depression (clinical psych)
    (
        "Aaron Beck, 'Thinking and Depression: Idiosyncratic Content and Cognitive Distortions', Archives of General Psychiatry 9 (1963) 324-333, proposed that depression is maintained by systematic negative distortions in automatic thoughts about the self, the world, and the future.",
        "knowledge",
        "Depression is sustained in part by systematic negative biases in how people think about themselves, their circumstances, and their future prospects.",
        "knowledge",
    ),
    # 15. Big Five personality model (personality)
    (
        "Costa and McCrae, 'Four Ways Five Factors are Basic', Personality and Individual Differences 13 (1992) 653-665, consolidated evidence that personality variation in adults is well described by five broad dimensions: openness, conscientiousness, extraversion, agreeableness, and neuroticism.",
        "knowledge",
        "Individual differences in adult personality are largely captured by five broad trait dimensions commonly labelled openness, conscientiousness, extraversion, agreeableness, and neuroticism.",
        "knowledge",
    ),
    # 16. Mischel marshmallow test (personality / developmental)
    (
        "Mischel, Shoda, and Rodriguez, 'Delay of Gratification in Children', Science 244 (1989) 933-938, summarized longitudinal follow-ups of preschool children who waited longer in the marshmallow paradigm and later showed better adolescent cognitive and social competence.",
        "knowledge",
        "Preschool children who can wait longer for a larger delayed reward tend on average to show somewhat better cognitive and social outcomes in adolescence.",
        "knowledge",
    ),
    # 17. Dweck mindset (educational / personality)
    (
        "Carol Dweck, Mindset: The New Psychology of Success (Random House, 2006), synthesized research showing that students who believe intelligence is malleable tend to seek challenge and persist after failure more than those who view intelligence as fixed.",
        "knowledge",
        "Students who believe that intelligence can grow with effort tend to embrace challenging work and recover from setbacks better than students who see intelligence as an unchangeable trait.",
        "knowledge",
    ),
    # 18. Thaler & Sunstein nudges (behavioural economics)
    (
        "Thaler and Sunstein, Nudge: Improving Decisions about Health, Wealth, and Happiness (Yale University Press, 2008), argued that small changes in choice architecture, such as default options, can predictably alter behaviour without restricting freedom of choice.",
        "knowledge",
        "Changing the default option in a decision, such as whether employees are automatically enrolled in a savings plan, can substantially shift participation rates without removing anyone's ability to opt out.",
        "knowledge",
    ),
    # 19. Ariely dishonesty (behavioural economics)
    (
        "Mazar, Amir, and Ariely, 'The Dishonesty of Honest People: A Theory of Self-Concept Maintenance', Journal of Marketing Research 45 (2008) 633-644, reported that many participants cheat by small amounts on anonymous tasks but refrain from large cheating that would threaten their self-image as honest.",
        "knowledge",
        "When given an opportunity to cheat without detection, many otherwise honest people cheat by small amounts but stop short of cheating enough to seriously threaten their view of themselves as good people.",
        "knowledge",
    ),
    # 20. Many Labs replication (behavioural econ / meta-science)
    (
        "Klein et al., 'Investigating Variation in Replicability: A Many Labs Replication Project', Social Psychology 45 (2014) 142-152, coordinated 36 independent labs to replicate 13 classic findings and found that roughly ten of the effects reproduced while others did not.",
        "knowledge",
        "Large coordinated replication efforts have shown that many but not all classic social psychology findings reliably reproduce across samples and laboratories.",
        "knowledge",
    ),
    # 21. Open Science Collaboration replication (meta-science / psych)
    (
        "Open Science Collaboration, 'Estimating the Reproducibility of Psychological Science', Science 349 (2015) aac4716, replicated 100 published psychology studies and found that only about 36 percent yielded statistically significant results in the same direction.",
        "knowledge",
        "In a large replication project covering a hundred published psychology studies, only a little over a third reproduced the original statistically significant finding.",
        "knowledge",
    ),
    # 22. Hawthorne effect (organizational psych)
    (
        "Roethlisberger and Dickson, Management and the Worker (Harvard University Press, 1939), reported that female assembly workers at the Hawthorne Works showed productivity gains that appeared tied to being observed rather than to specific lighting or break manipulations.",
        "knowledge",
        "Workers whose behaviour is being observed as part of a study may increase their productivity simply because they know they are being watched, regardless of the specific conditions being tested.",
        "knowledge",
    ),
    # 23. Herzberg two-factor theory (organizational psych)
    (
        "Frederick Herzberg, 'One More Time: How Do You Motivate Employees?', Harvard Business Review 46 (1968) 53-62, distinguished hygiene factors such as pay and supervision from motivators such as achievement and recognition that drive satisfaction.",
        "knowledge",
        "In workplaces, factors like pay and working conditions mainly prevent dissatisfaction, while genuine motivation tends to come from achievement, recognition, and meaningful work.",
        "knowledge",
    ),
    # 24. Hackman & Oldham job characteristics (organizational psych)
    (
        "Hackman and Oldham, 'Motivation through the Design of Work: Test of a Theory', Organizational Behavior and Human Performance 16 (1976) 250-279, proposed that five core job characteristics - skill variety, task identity, task significance, autonomy, and feedback - shape intrinsic motivation.",
        "knowledge",
        "Jobs that combine varied skills, a clear whole task, meaningful impact, autonomy, and regular feedback tend to produce higher intrinsic motivation in workers.",
        "knowledge",
    ),
    # 25. Meta-analysis of employment interviews (organizational psych)
    (
        "McDaniel, Whetzel, Schmidt, and Maurer, 'The Validity of Employment Interviews: A Comprehensive Review and Meta-Analysis', Journal of Applied Psychology 79 (1994) 599-616, reported that structured interviews predict job performance substantially better than unstructured interviews.",
        "knowledge",
        "Structured employment interviews with standardised questions and scoring rubrics predict later job performance much more accurately than free-form unstructured interviews.",
        "knowledge",
    ),
    # 26. Coleman report on schools (sociology of education)
    (
        "James S. Coleman, Equality of Educational Opportunity (U.S. Government Printing Office, 1966), concluded from a survey of over 600,000 American students that family background accounted for more variance in student achievement than measurable school resources.",
        "knowledge",
        "In large-scale surveys of American schoolchildren, differences in family socioeconomic background account for more of the variation in academic achievement than differences in school resources.",
        "knowledge",
    ),
    # 27. Jencks on inequality (sociology of education)
    (
        "Christopher Jencks et al., Inequality: A Reassessment of the Effect of Family and Schooling in America (Basic Books, 1972), argued that equalizing school quality would produce only modest reductions in overall income inequality.",
        "knowledge",
        "Equalising school resources across neighbourhoods would likely produce only modest reductions in overall adult income inequality because many other factors drive earnings differences.",
        "knowledge",
    ),
    # 28. Bourdieu cultural capital (sociology of education)
    (
        "Pierre Bourdieu, 'Cultural Reproduction and Social Reproduction' in Knowledge, Education and Cultural Change (ed. Brown, 1973), argued that schools reward a cultural capital unevenly distributed by class, reproducing social hierarchy across generations.",
        "knowledge",
        "Schools tend to reward tastes, language, and knowledge that are more common in middle- and upper-class homes, which helps reproduce class advantages across generations.",
        "knowledge",
    ),
    # 29. Granovetter strength of weak ties (economic sociology / networks)
    (
        "Mark Granovetter, 'The Strength of Weak Ties', American Journal of Sociology 78 (1973) 1360-1380, reported that professional and technical workers in the Boston area who found new jobs typically did so through acquaintances rather than through close friends.",
        "knowledge",
        "People looking for jobs more often find useful leads through weak social ties such as acquaintances than through their closest friends, because weak ties connect to different information networks.",
        "knowledge",
    ),
    # 30. Granovetter embeddedness (economic sociology)
    (
        "Mark Granovetter, 'Economic Action and Social Structure: The Problem of Embeddedness', American Journal of Sociology 91 (1985) 481-510, argued that economic transactions are persistently embedded in ongoing networks of interpersonal relations rather than occurring among atomized actors.",
        "knowledge",
        "Economic exchanges are consistently shaped by the ongoing personal relationships and social networks in which the parties are embedded, not by isolated self-interested calculation alone.",
        "knowledge",
    ),
    # 31. Uzzi embeddedness in firms (economic sociology)
    (
        "Brian Uzzi, 'Social Structure and Competition in Interfirm Networks: The Paradox of Embeddedness', Administrative Science Quarterly 42 (1997) 35-67, showed that New York garment firms that relied on a mix of arm's-length and embedded ties outperformed those using only one type of tie.",
        "knowledge",
        "Firms tend to perform best when their supply relationships combine close, trust-based ties with a broader set of more transactional relationships rather than relying on only one mode.",
        "knowledge",
    ),
    # 32. Putnam social capital (political sociology)
    (
        "Robert Putnam, Making Democracy Work: Civic Traditions in Modern Italy (Princeton University Press, 1993), found that regions with denser horizontal civic associations had more effective regional governments than regions with sparser civic life.",
        "knowledge",
        "Regions with stronger traditions of voluntary civic participation tend to have more effective and responsive local government than regions with weaker associational life.",
        "knowledge",
    ),
    # 33. Putnam Bowling Alone (political sociology)
    (
        "Robert Putnam, Bowling Alone: The Collapse and Revival of American Community (Simon and Schuster, 2000), documented long-run declines in membership in civic, religious, and voluntary associations across the United States during the second half of the twentieth century.",
        "knowledge",
        "Participation in American civic, religious, and voluntary associations declined substantially over the second half of the twentieth century.",
        "knowledge",
    ),
    # 34. Wilson truly disadvantaged (urban sociology)
    (
        "William Julius Wilson, The Truly Disadvantaged (University of Chicago Press, 1987), argued that deindustrialization and middle-class outmigration left concentrated urban black neighborhoods with high joblessness and social isolation.",
        "knowledge",
        "The collapse of manufacturing employment and the departure of middle-class residents from many American inner-city neighborhoods left behind concentrated poverty and social isolation.",
        "knowledge",
    ),
    # 35. Massey & Denton residential segregation (demography / urban sociology)
    (
        "Massey and Denton, American Apartheid: Segregation and the Making of the Underclass (Harvard University Press, 1993), used census tract data to show that black Americans faced unusually high and persistent levels of residential segregation compared with other groups.",
        "knowledge",
        "Black Americans have faced unusually high and persistent levels of residential segregation in U.S. metropolitan areas compared with other racial and ethnic groups.",
        "knowledge",
    ),
    # 36. Chetty mobility (economic sociology / demography)
    (
        "Chetty, Hendren, Kline, and Saez, 'Where is the Land of Opportunity? The Geography of Intergenerational Mobility in the United States', Quarterly Journal of Economics 129 (2014) 1553-1623, used tax records for 40 million children and their parents to document large regional differences in upward mobility.",
        "knowledge",
        "Upward economic mobility varies dramatically across U.S. regions, with some metropolitan areas offering much better chances for children from low-income families to reach higher income brackets than others.",
        "knowledge",
    ),
    # 37. Preston causes of death / demographic transition (demography)
    (
        "Samuel Preston, 'The Changing Relation between Mortality and Level of Economic Development', Population Studies 29 (1975) 231-248, showed that life expectancy at a given income level rose substantially during the twentieth century, implying that factors beyond income drove mortality decline.",
        "knowledge",
        "Life expectancy rose at every level of income over the twentieth century, indicating that much of the long-run decline in mortality was driven by factors beyond rising income.",
        "knowledge",
    ),
    # 38. Notestein demographic transition (demography)
    (
        "Frank Notestein, 'Population: The Long View' in Food for the World (ed. Schultz, 1945), articulated the demographic transition theory in which mortality declines precede fertility declines during modernization.",
        "knowledge",
        "During modernization, societies typically experience a fall in death rates before birth rates drop, producing a period of rapid population growth followed by stabilisation at lower vital rates.",
        "knowledge",
    ),
    # 39. Sampson neighborhood effects (criminology / urban sociology)
    (
        "Sampson, Raudenbush, and Earls, 'Neighborhoods and Violent Crime: A Multilevel Study of Collective Efficacy', Science 277 (1997) 918-924, found that neighborhood collective efficacy predicted lower rates of violence in Chicago even after controlling for concentrated disadvantage.",
        "knowledge",
        "Neighborhoods where residents trust one another and are willing to intervene for the common good tend to have lower rates of violent crime, even after accounting for poverty and other disadvantage.",
        "knowledge",
    ),
    # 40. Routine activity theory (criminology)
    (
        "Cohen and Felson, 'Social Change and Crime Rate Trends: A Routine Activity Approach', American Sociological Review 44 (1979) 588-608, argued that predatory crime requires the convergence in time and space of a motivated offender, a suitable target, and the absence of capable guardians.",
        "knowledge",
        "Predatory crime tends to occur when a motivated offender, an attractive target, and a lack of effective guardians come together in the same time and place.",
        "knowledge",
    ),
    # 41. Broken windows (criminology)
    (
        "Wilson and Kelling, 'Broken Windows: The Police and Neighborhood Safety', The Atlantic (March 1982), argued that visible signs of disorder such as broken windows and graffiti signal that no one is in charge and encourage more serious crime.",
        "knowledge",
        "Visible signs of neighborhood disorder such as broken windows, graffiti, and litter can signal a lack of social control and encourage additional and more serious criminal behaviour.",
        "knowledge",
    ),
    # 42. Gottfredson & Hirschi self-control (criminology)
    (
        "Gottfredson and Hirschi, A General Theory of Crime (Stanford University Press, 1990), proposed that low self-control, formed in childhood and stable across the life course, is the primary individual-level predictor of criminal behaviour.",
        "knowledge",
        "Individual differences in self-control established in childhood are one of the strongest and most stable individual-level predictors of later involvement in crime.",
        "knowledge",
    ),
    # 43. Verba, Schlozman, Brady participation (political sociology)
    (
        "Verba, Schlozman, and Brady, Voice and Equality: Civic Voluntarism in American Politics (Harvard University Press, 1995), showed that political participation in the United States is strongly stratified by socioeconomic resources, civic skills, and recruitment.",
        "knowledge",
        "Political participation in the United States is strongly tilted toward citizens with higher income, education, and civic skills, and those who are more often recruited into political activity.",
        "knowledge",
    ),
    # 44. Converse mass belief systems (political sociology / psych)
    (
        "Philip Converse, 'The Nature of Belief Systems in Mass Publics' in Ideology and Discontent (ed. Apter, 1964), argued that most ordinary citizens have weakly structured and unstable political belief systems compared with political elites.",
        "knowledge",
        "Most ordinary citizens hold political opinions that are far less internally consistent and stable over time than the opinions held by political elites and activists.",
        "knowledge",
    ),
    # 45. Milgram small world (network analysis)
    (
        "Stanley Milgram, 'The Small-World Problem', Psychology Today 1 (1967) 61-67, reported that chains of acquaintances connecting randomly chosen Americans to a distant target person typically contained only about five or six intermediaries.",
        "knowledge",
        "Chains of acquaintances connecting two random people in a large population often involve only a handful of intermediaries, a pattern popularly summarised as six degrees of separation.",
        "knowledge",
    ),
    # 46. Watts & Strogatz small-world networks (network analysis)
    (
        "Watts and Strogatz, 'Collective Dynamics of Small-World Networks', Nature 393 (1998) 440-442, showed that adding a small number of long-range shortcuts to a regular lattice sharply reduces the average path length while preserving high clustering.",
        "knowledge",
        "Many real social and biological networks combine high local clustering with short average path lengths, a pattern that can emerge when a mostly regular network contains a few long-range connections.",
        "knowledge",
    ),
    # 47. Christakis & Fowler social contagion (network analysis / health)
    (
        "Christakis and Fowler, 'The Spread of Obesity in a Large Social Network over 32 Years', New England Journal of Medicine 357 (2007) 370-379, used Framingham Heart Study data to report that a person's chance of becoming obese rose when a close social contact became obese.",
        "knowledge",
        "A person's likelihood of becoming obese tends to rise when people in their close social network also become obese, suggesting that health behaviours spread through social ties.",
        "knowledge",
    ),
    # 48. Dunbar's number (evolutionary / social psych)
    (
        "Robin Dunbar, 'Neocortex Size as a Constraint on Group Size in Primates', Journal of Human Evolution 22 (1992) 469-493, proposed on the basis of primate neocortex ratios that humans can maintain stable personal relationships with only about 150 other individuals.",
        "knowledge",
        "Humans can typically sustain stable meaningful personal relationships with only about 150 other people, a ceiling that appears linked to the size of our social brain.",
        "knowledge",
    ),
    # 49. Cuddy power posing replication failure (meta-science / social psych)
    (
        "Ranehill et al., 'Assessing the Robustness of Power Posing: No Effect on Hormones and Risk Tolerance in a Large Sample of Men and Women', Psychological Science 26 (2015) 653-656, failed to replicate the hormonal and risk-tolerance effects of expansive postures originally reported by Carney, Cuddy, and Yap.",
        "knowledge",
        "Large replication attempts have failed to reproduce earlier claims that briefly holding expansive body postures meaningfully changes hormone levels or risk-taking behaviour.",
        "knowledge",
    ),
    # 50. Nature Human Behaviour ego depletion replication (behavioural psych)
    (
        "Hagger et al., 'A Multilab Preregistered Replication of the Ego-Depletion Effect', Perspectives on Psychological Science 11 (2016) 546-573, coordinated 23 laboratories and found essentially no evidence for the classic ego-depletion effect on subsequent self-control tasks.",
        "knowledge",
        "A large coordinated replication project found little evidence that briefly exerting self-control measurably degrades performance on a subsequent self-control task, challenging earlier ego-depletion findings.",
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
