"""One-off emitter for classification top-up batch-016 — contrastive_reference_fact mode, philosophy and ethics slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_016.tmp.jsonl with ids class-01501..01600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_016.tmp.jsonl"
ID_OFFSET = 1500
PAIR_OFFSET = 500

# Each pair is: (ref_text, ref_domain, fact_text, fact_domain)
# ref_text MUST name a real philosophical work, author, year, or journal.
# fact_text MUST restate the same philosophical claim without citing the source.
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. Kant's categorical imperative (normative ethics / deontology)
    (
        "Immanuel Kant, Groundwork of the Metaphysics of Morals (1785), formulates the categorical imperative as acting only on that maxim whereby one can at the same time will that it should become a universal law.",
        "knowledge",
        "A moral agent ought to act only on maxims that the agent can consistently will to hold as universal laws binding on every rational being.",
        "knowledge",
    ),
    # 2. Rawls's original position (political philosophy)
    (
        "John Rawls, A Theory of Justice (Harvard University Press, 1971), argues that principles of justice are those that would be chosen by rational parties behind a veil of ignorance in the original position.",
        "knowledge",
        "Fair principles of social justice are the principles that rational people would agree to if they had to choose without knowing their own social position, talents, or conception of the good.",
        "knowledge",
    ),
    # 3. Parfit on personal identity (metaphysics of self)
    (
        "Derek Parfit, Reasons and Persons (Oxford University Press, 1984), argues that personal identity over time consists in psychological continuity and connectedness rather than in a further fact about a persisting self.",
        "knowledge",
        "The persistence of a person over time is constituted by overlapping chains of memory, intention, and psychological connection rather than by any extra metaphysical fact about a continuing self.",
        "knowledge",
    ),
    # 4. Anscombe virtue ethics revival (metaethics)
    (
        "G. E. M. Anscombe, 'Modern Moral Philosophy', Philosophy 33 (1958) 1-19, argues that the concepts of moral obligation and moral duty should be jettisoned until an adequate philosophy of psychology is available.",
        "knowledge",
        "The modern vocabulary of moral obligation and moral duty makes little sense outside a theological framework, and ethics should be rebuilt on a theory of human flourishing and the virtues.",
        "knowledge",
    ),
    # 5. Gettier problem (epistemology)
    (
        "Edmund Gettier, 'Is Justified True Belief Knowledge?', Analysis 23 (1963) 121-123, presents counterexamples showing that justified true belief is insufficient for knowledge.",
        "knowledge",
        "A person can have a justified true belief without having knowledge, because the belief can be true only by accident relative to its justification.",
        "knowledge",
    ),
    # 6. Nagel bat (philosophy of mind / consciousness)
    (
        "Thomas Nagel, 'What Is It Like to Be a Bat?', The Philosophical Review 83 (1974) 435-450, argues that consciousness has an essentially subjective character that escapes any objective physicalist reduction.",
        "knowledge",
        "Conscious experience has an irreducibly subjective character, and no purely objective description of neural or physical processes can fully capture what it is like to be a conscious subject.",
        "knowledge",
    ),
    # 7. Chalmers hard problem (philosophy of mind)
    (
        "David Chalmers, 'Facing Up to the Problem of Consciousness', Journal of Consciousness Studies 2 (1995) 200-219, distinguishes the easy problems of cognition from the hard problem of explaining phenomenal experience.",
        "knowledge",
        "Explaining why physical processes in the brain are accompanied by subjective experience at all is a distinct and harder problem than explaining cognitive functions like attention or reportability.",
        "knowledge",
    ),
    # 8. Jackson knowledge argument (philosophy of mind)
    (
        "Frank Jackson, 'Epiphenomenal Qualia', Philosophical Quarterly 32 (1982) 127-136, presents the Mary thought experiment to argue that complete physical knowledge leaves out facts about phenomenal experience.",
        "knowledge",
        "A scientist raised in a black-and-white room who knows every physical fact about color vision still learns something new when she sees red for the first time, suggesting that not all facts are physical facts.",
        "knowledge",
    ),
    # 9. Putnam Twin Earth (philosophy of language)
    (
        "Hilary Putnam, 'The Meaning of Meaning', in Mind, Language and Reality (Cambridge University Press, 1975), uses the Twin Earth thought experiment to argue that meanings are not purely in the head.",
        "knowledge",
        "Two speakers in internally identical brain states can nonetheless mean different things by the same word when their physical and social environments differ, so linguistic meaning depends in part on the external world.",
        "knowledge",
    ),
    # 10. Kripke naming (philosophy of language)
    (
        "Saul Kripke, Naming and Necessity (Harvard University Press, 1980), defends a causal-historical theory of reference for proper names against the descriptivist view.",
        "knowledge",
        "Proper names typically refer to their bearers through a causal-historical chain reaching back to an initial baptism, rather than by expressing some set of descriptions that uniquely identify the bearer.",
        "knowledge",
    ),
    # 11. Quine Two Dogmas (philosophy of language / epistemology)
    (
        "W. V. O. Quine, 'Two Dogmas of Empiricism', The Philosophical Review 60 (1951) 20-43, attacks the analytic-synthetic distinction and reductionist verificationism.",
        "knowledge",
        "There is no principled distinction between purely analytic truths and synthetic empirical truths, and our beliefs face the tribunal of experience only as a holistic web rather than one by one.",
        "knowledge",
    ),
    # 12. Kuhn paradigms (philosophy of science)
    (
        "Thomas Kuhn, The Structure of Scientific Revolutions (University of Chicago Press, 1962), argues that mature sciences develop through alternating periods of normal science and revolutionary paradigm shifts.",
        "knowledge",
        "Scientific progress is not uniformly cumulative but proceeds through long stretches of normal puzzle-solving within a shared framework punctuated by revolutionary changes in fundamental assumptions.",
        "knowledge",
    ),
    # 13. Popper falsification (philosophy of science)
    (
        "Karl Popper, The Logic of Scientific Discovery (Hutchinson, 1959), argues that the distinctive mark of scientific theories is falsifiability rather than verifiability.",
        "knowledge",
        "A theory counts as genuinely scientific only if it makes predictions that could in principle be falsified by observation, since no finite set of confirming instances can establish a universal claim.",
        "knowledge",
    ),
    # 14. Hume is-ought (metaethics)
    (
        "David Hume, A Treatise of Human Nature (1739-40), Book III, Part I, Section I, observes the shift from 'is' to 'ought' propositions and questions its justification.",
        "knowledge",
        "A normative conclusion about what ought to be the case cannot be validly derived from purely descriptive premises about what is the case without the aid of some further normative premise.",
        "knowledge",
    ),
    # 15. Moore open question (metaethics)
    (
        "G. E. Moore, Principia Ethica (Cambridge University Press, 1903), deploys the open-question argument against identifying the good with any natural property.",
        "knowledge",
        "For any proposed natural property identified with goodness, it remains a genuinely open question whether things with that property are good, suggesting that goodness is not identical with any such property.",
        "knowledge",
    ),
    # 16. Mill utilitarianism (normative ethics)
    (
        "John Stuart Mill, Utilitarianism (Parker, Son and Bourn, 1863), defends the greatest happiness principle as the foundation of morals.",
        "knowledge",
        "Actions are right in proportion as they tend to promote happiness and wrong as they tend to produce the reverse of happiness, with happiness understood as pleasure and the absence of pain.",
        "knowledge",
    ),
    # 17. Bentham hedonic calculus (normative ethics)
    (
        "Jeremy Bentham, An Introduction to the Principles of Morals and Legislation (1789), proposes a felicific calculus measuring pleasures and pains by intensity, duration, certainty, and related features.",
        "knowledge",
        "The moral evaluation of an action depends on the aggregate of pleasures and pains it produces, assessed along dimensions such as intensity, duration, certainty, propinquity, fecundity, purity, and extent.",
        "knowledge",
    ),
    # 18. Aristotle eudaimonia (virtue ethics)
    (
        "Aristotle, Nicomachean Ethics, Book I, identifies the human good with eudaimonia, understood as activity of the soul in accordance with virtue over a complete life.",
        "knowledge",
        "The human good is a life of activity exercising the characteristic excellences of a rational being, sustained throughout a complete life rather than experienced in isolated moments.",
        "knowledge",
    ),
    # 19. Singer famine relief (applied ethics)
    (
        "Peter Singer, 'Famine, Affluence, and Morality', Philosophy and Public Affairs 1 (1972) 229-243, argues that affluent people are morally obligated to give substantially to prevent suffering from famine.",
        "knowledge",
        "If one can prevent serious suffering at no comparable moral cost, one is morally required to do so, which implies that affluent individuals are obligated to donate a large share of their resources to relieve extreme poverty.",
        "knowledge",
    ),
    # 20. Thomson violinist (applied ethics)
    (
        "Judith Jarvis Thomson, 'A Defense of Abortion', Philosophy and Public Affairs 1 (1971) 47-66, uses the violinist thought experiment to argue that even granting fetal personhood, abortion can be morally permissible.",
        "knowledge",
        "Even if the fetus is granted the moral status of a person, a pregnant person is not always morally required to sustain that life with her own body, because no one has an unconditional right to use another person's body.",
        "knowledge",
    ),
    # 21. Foot trolley problem (applied / normative ethics)
    (
        "Philippa Foot, 'The Problem of Abortion and the Doctrine of the Double Effect', Oxford Review 5 (1967) 5-15, introduces the trolley case and distinguishes doing from allowing harm.",
        "knowledge",
        "There is a morally significant distinction between directly killing a smaller number of people as a means and merely diverting a harm so that a smaller number are killed as a side effect.",
        "knowledge",
    ),
    # 22. Nozick entitlement theory (political philosophy)
    (
        "Robert Nozick, Anarchy, State, and Utopia (Basic Books, 1974), defends a minimal state and an entitlement theory of distributive justice based on just acquisition and transfer.",
        "knowledge",
        "A distribution of holdings is just if it arises from an initially just acquisition of unowned resources followed by voluntary transfers, and redistribution beyond what a minimal state requires violates individual rights.",
        "knowledge",
    ),
    # 23. Dworkin rights as trumps (political / legal philosophy)
    (
        "Ronald Dworkin, Taking Rights Seriously (Harvard University Press, 1977), argues that individual rights function as trumps over collective goals grounded in background utility.",
        "knowledge",
        "Individual moral rights set side constraints that override ordinary appeals to aggregate welfare, so a government may not violate an individual's right merely because doing so would maximize overall social utility.",
        "knowledge",
    ),
    # 24. Mill liberty principle (political philosophy)
    (
        "John Stuart Mill, On Liberty (John W. Parker and Son, 1859), defends the harm principle as the sole legitimate ground for coercive interference with individual liberty.",
        "knowledge",
        "The only ground on which society is entitled to restrict an adult's liberty against his will is to prevent harm to others, and neither his own good nor moral disapproval by others suffices.",
        "knowledge",
    ),
    # 25. Hart-Fuller debate (legal philosophy)
    (
        "H. L. A. Hart, 'Positivism and the Separation of Law and Morals', Harvard Law Review 71 (1958) 593-629, defends legal positivism against Lon Fuller's natural law critique.",
        "knowledge",
        "The existence and content of a legal system is one question and its moral merit is another, so a rule can be legally valid even when it fails to satisfy moral demands.",
        "knowledge",
    ),
    # 26. Searle Chinese Room (philosophy of mind / AI)
    (
        "John Searle, 'Minds, Brains, and Programs', Behavioral and Brain Sciences 3 (1980) 417-457, uses the Chinese Room thought experiment to argue that syntactic symbol manipulation is insufficient for semantic understanding.",
        "knowledge",
        "A system that produces intelligent-seeming responses purely by manipulating symbols according to formal rules does not thereby understand the language it appears to use, because syntax does not suffice for semantics.",
        "knowledge",
    ),
    # 27. Turing test (philosophy of mind / AI)
    (
        "Alan Turing, 'Computing Machinery and Intelligence', Mind 59 (1950) 433-460, proposes the imitation game as an operational test for machine intelligence.",
        "knowledge",
        "A reasonable operational criterion for machine intelligence is whether a machine can hold a text-based conversation indistinguishable from that of a human interlocutor to a blinded judge.",
        "knowledge",
    ),
    # 28. Dennett intentional stance (philosophy of mind)
    (
        "Daniel Dennett, The Intentional Stance (MIT Press, 1987), argues that ascribing beliefs and desires is a predictive strategy rather than the discovery of intrinsic mental states.",
        "knowledge",
        "Treating a system as a rational agent that holds beliefs and desires is a predictive strategy that works whenever doing so yields reliable predictions of behavior, independently of the system's internal composition.",
        "knowledge",
    ),
    # 29. Lewis modal realism (metaphysics)
    (
        "David Lewis, On the Plurality of Worlds (Blackwell, 1986), defends modal realism on which possible worlds are concrete entities as real as our own world.",
        "knowledge",
        "A claim that something is possible is to be analyzed as saying that there is some concrete world, spatiotemporally isolated from ours, in which that thing is the case.",
        "knowledge",
    ),
    # 30. Kripke necessary a posteriori (metaphysics / philosophy of language)
    (
        "Saul Kripke, Naming and Necessity (Harvard University Press, 1980), argues that identity statements involving rigid designators, such as 'water is H2O', are necessary a posteriori truths.",
        "knowledge",
        "Some truths can be known only through empirical investigation and yet are necessary, because an identity between two rigid designators holds in every possible world in which either refers.",
        "knowledge",
    ),
    # 31. Quine ontological commitment (metaphysics)
    (
        "W. V. O. Quine, 'On What There Is', Review of Metaphysics 2 (1948) 21-38, proposes that to be is to be the value of a bound variable in our best regimented theory.",
        "knowledge",
        "Our ontological commitments are just those entities that must be taken to exist for our best regimented theories of the world to come out true, identified by what their quantifiers range over.",
        "knowledge",
    ),
    # 32. Hume induction problem (epistemology)
    (
        "David Hume, An Enquiry Concerning Human Understanding (1748), Section IV, poses the problem of the rational justification of inductive inference.",
        "knowledge",
        "No non-circular argument shows that the future will resemble the past, since any such argument either presupposes induction or relies on an ungrounded principle of the uniformity of nature.",
        "knowledge",
    ),
    # 33. Goodman new riddle (epistemology / philosophy of science)
    (
        "Nelson Goodman, Fact, Fiction, and Forecast (Harvard University Press, 1955), introduces the predicate 'grue' to pose the new riddle of induction.",
        "knowledge",
        "Any body of evidence that confirms 'all emeralds are green' equally confirms a gerrymandered hypothesis such as 'all emeralds are grue', so inductive support depends on which predicates are taken as projectible.",
        "knowledge",
    ),
    # 34. Williams internal reasons (metaethics)
    (
        "Bernard Williams, 'Internal and External Reasons', in Moral Luck (Cambridge University Press, 1981), argues that all genuine reasons for action must connect to an agent's existing motivational set.",
        "knowledge",
        "A consideration counts as a reason for an agent to act only if a sound deliberative route leads from that agent's existing desires, commitments, and projects to the action in question.",
        "knowledge",
    ),
    # 35. Scanlon contractualism (normative ethics)
    (
        "T. M. Scanlon, What We Owe to Each Other (Harvard University Press, 1998), defends a contractualist account on which an act is wrong if its performance would be disallowed by any principle no one could reasonably reject.",
        "knowledge",
        "An act is morally wrong just when it is forbidden by some principle for the general regulation of behavior that no one, suitably motivated to find terms of cooperation, could reasonably reject.",
        "knowledge",
    ),
    # 36. Nagel view from nowhere (metaphysics / ethics)
    (
        "Thomas Nagel, The View from Nowhere (Oxford University Press, 1986), explores the tension between subjective and objective standpoints in epistemology, metaphysics, and ethics.",
        "knowledge",
        "Human thought occupies both an engaged, subjective standpoint and a detached, impersonal standpoint, and many philosophical problems arise from the difficulty of integrating the two views.",
        "knowledge",
    ),
    # 37. Plato Republic justice (political / moral philosophy)
    (
        "Plato, Republic, Books II-IV, argues that justice in the soul consists in each part performing its proper function under the rule of reason.",
        "knowledge",
        "Justice in the individual consists in a harmonious ordering of rational, spirited, and appetitive parts of the soul, with reason ruling the other two parts.",
        "knowledge",
    ),
    # 38. Aquinas natural law (ethics / philosophy of religion)
    (
        "Thomas Aquinas, Summa Theologiae I-II, q. 94, articulates natural law as the rational creature's participation in the eternal law.",
        "knowledge",
        "Basic moral principles are grasped by practical reason reflecting on the natural inclinations of rational beings toward goods such as life, sociability, and knowledge.",
        "knowledge",
    ),
    # 39. Hobbes state of nature (political philosophy)
    (
        "Thomas Hobbes, Leviathan (Andrew Crooke, 1651), Part I Chapter 13, describes life in the state of nature as 'solitary, poor, nasty, brutish, and short'.",
        "knowledge",
        "In the absence of a common power able to enforce peace, human beings would live in a condition of war of all against all in which life would be insecure, impoverished, and brief.",
        "knowledge",
    ),
    # 40. Locke property theory (political philosophy)
    (
        "John Locke, Two Treatises of Government (Awnsham Churchill, 1689), Second Treatise Chapter V, grounds private property in the mixing of one's labor with an unowned thing.",
        "knowledge",
        "A person acquires a rightful property in a previously unowned natural resource when he mixes his own labor with it, provided that enough and as good is left for others.",
        "knowledge",
    ),
    # 41. Rousseau general will (political philosophy)
    (
        "Jean-Jacques Rousseau, Du Contrat Social (Marc-Michel Rey, 1762), argues that legitimate political authority rests on the general will of the people.",
        "knowledge",
        "Legitimate political authority is grounded in a general will that aims at the common good of the political community, as distinct from the aggregated private wills of its members.",
        "knowledge",
    ),
    # 42. Hegel master slave (political philosophy / phenomenology)
    (
        "G. W. F. Hegel, Phenomenology of Spirit (1807), Section IV.A, presents the master-slave dialectic as a stage in the development of self-consciousness through mutual recognition.",
        "knowledge",
        "Self-consciousness develops through a struggle for recognition in which the relation between a dominating and a dominated consciousness ultimately proves unstable because genuine self-understanding requires recognition by an equal.",
        "knowledge",
    ),
    # 43. Nietzsche genealogy of morals (metaethics)
    (
        "Friedrich Nietzsche, On the Genealogy of Morality (C. G. Naumann, 1887), traces the historical origins of moral concepts such as good, evil, guilt, and bad conscience.",
        "knowledge",
        "Modern moral concepts have a contingent historical origin in particular social practices and psychological dynamics, and tracing that origin can expose their tacit assumptions and power relations.",
        "knowledge",
    ),
    # 44. Wittgenstein private language (philosophy of language / mind)
    (
        "Ludwig Wittgenstein, Philosophical Investigations (Blackwell, 1953), sections 243-315, presents the private language argument against the possibility of a purely private sensation language.",
        "knowledge",
        "A language whose words refer only to sensations knowable to a single speaker cannot support a genuine distinction between correctly and incorrectly applying a term, and so cannot be a language at all.",
        "knowledge",
    ),
    # 45. Frege sense and reference (philosophy of language)
    (
        "Gottlob Frege, 'Uber Sinn und Bedeutung', Zeitschrift fur Philosophie und philosophische Kritik 100 (1892) 25-50, distinguishes sense (Sinn) from reference (Bedeutung) for linguistic expressions.",
        "knowledge",
        "Two expressions can share a referent while differing in the cognitive mode of presentation associated with them, so the meaning of an expression includes more than just the object it picks out.",
        "knowledge",
    ),
    # 46. Hempel deductive nomological (philosophy of science)
    (
        "Carl Hempel and Paul Oppenheim, 'Studies in the Logic of Explanation', Philosophy of Science 15 (1948) 135-175, articulate the deductive-nomological model of scientific explanation.",
        "knowledge",
        "On one influential view, a scientific explanation of an event is a sound deductive argument whose premises include at least one general law and whose conclusion is a statement of the event to be explained.",
        "knowledge",
    ),
    # 47. Hume miracles (philosophy of religion / epistemology)
    (
        "David Hume, An Enquiry Concerning Human Understanding (1748), Section X, argues that testimony can never establish a miracle as more probable than its violation of the laws of nature.",
        "knowledge",
        "Since a miracle by definition is a violation of a well-established law of nature, the evidence against such a violation is always stronger than any human testimony in its favor, so belief in miracles on testimony alone is unwarranted.",
        "knowledge",
    ),
    # 48. Dewey aesthetics (aesthetics)
    (
        "John Dewey, Art as Experience (Minton, Balch, 1934), argues that aesthetic value consists in the consummatory quality of an experience rather than in intrinsic features of a privileged class of objects.",
        "knowledge",
        "What makes an experience aesthetic is its having a unified, consummatory quality in which means and ends are integrated, rather than the presence of some special class of fine-art objects.",
        "knowledge",
    ),
    # 49. Kant sublime (aesthetics)
    (
        "Immanuel Kant, Critique of the Power of Judgment (1790), Book II, analyzes the feeling of the sublime as a response to objects that exceed our capacity for sensible representation.",
        "knowledge",
        "The feeling of the sublime arises when the imagination is overwhelmed by something vast or powerful, and reason then recognizes its own supersensible vocation in the very failure of sensory grasp.",
        "knowledge",
    ),
    # 50. Wollstonecraft rights of women (political philosophy / ethics)
    (
        "Mary Wollstonecraft, A Vindication of the Rights of Woman (J. Johnson, 1792), argues that women, as rational beings, are entitled to the same education and moral standing as men.",
        "knowledge",
        "Since women share with men the rational nature on which moral agency and civic participation depend, any system of education or law that systematically restricts women on the basis of sex alone is unjust.",
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
