"""One-off emitter for shared-base batch-078 — knowledge domain (AI/ML as a research field).

Writes 50 rows with ids shared-03851..03900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_078.tmp.jsonl"
ID_OFFSET = 3850

ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Vaswani et al.'s Attention Is All You Need, presented at NeurIPS 2017, introduced the Transformer architecture and replaced recurrent encoders with pure self-attention.", "reference", "knowledge", False,
     [("Vaswani", "person"), ("Attention Is All You Need", "publication"), ("NeurIPS", "event"), ("2017", "date"), ("Transformer", "algorithm"), ("self-attention", "method"), ("recurrent encoders", "algorithm")],
     [("Attention Is All You Need", "Vaswani", "AUTHORED_BY"), ("Attention Is All You Need", "NeurIPS", "PUBLISHED_IN"), ("Transformer", "recurrent encoders", "REPLACES")],
     "which 2017 NeurIPS paper introduced the Transformer by replacing recurrence with self-attention",
     "Vaswani attention transformer NeurIPS self attention recurrent replacement year"),
    # --- 2 ---
    ("Krizhevsky, Sutskever, and Hinton's AlexNet, presented at NeurIPS 2012, cut ImageNet top-5 error dramatically and launched the deep learning resurgence in computer vision.", "milestone", "knowledge", False,
     [("Krizhevsky", "person"), ("Sutskever", "person"), ("Hinton", "person"), ("AlexNet", "algorithm"), ("NeurIPS", "event"), ("2012", "date"), ("ImageNet", "publication")],
     [("AlexNet", "Krizhevsky", "AUTHORED_BY"), ("AlexNet", "NeurIPS", "PUBLISHED_IN"), ("AlexNet", "ImageNet", "APPLIES_TO")],
     "which 2012 NeurIPS paper triggered the deep learning revolution on ImageNet",
     "AlexNet Krizhevsky Sutskever Hinton ImageNet 2012 deep learning launch"),
    # --- 3 ---
    ("He et al.'s ResNet, introduced at CVPR 2016, enabled networks over a hundred layers deep via residual connections and improves on the vanishing-gradient behaviour of plain CNN stacks.", "reference", "knowledge", False,
     [("He", "person"), ("ResNet", "algorithm"), ("CVPR", "event"), ("2016", "date"), ("residual connections", "concept"), ("plain CNN stacks", "algorithm")],
     [("ResNet", "He", "AUTHORED_BY"), ("ResNet", "CVPR", "PUBLISHED_IN"), ("ResNet", "plain CNN stacks", "IMPROVES_ON")],
     "which CVPR 2016 paper enabled very deep networks through residual connections",
     "ResNet He residual skip connections deep CVPR year plain CNN"),
    # --- 4 ---
    ("DeepMind's AlphaGo defeated Lee Sedol 4-1 in Seoul in March 2016, the first program to beat a top human Go professional on a full nineteen by nineteen board.", "milestone", "knowledge", False,
     [("DeepMind", "organization"), ("AlphaGo", "algorithm"), ("Lee Sedol", "person"), ("Seoul", "place"), ("March 2016", "date")],
     [("AlphaGo", "DeepMind", "AUTHORED_BY"), ("AlphaGo", "Seoul", "LOCATED_IN")],
     "when did DeepMind's AlphaGo defeat Lee Sedol in a full Go match",
     "AlphaGo Lee Sedol Seoul Go match DeepMind year"),
    # --- 5 ---
    ("DeepMind's AlphaFold 2, published in Nature in 2021, solved the protein structure prediction problem at CASP14 accuracy comparable to experimental crystallography.", "milestone", "knowledge", False,
     [("DeepMind", "organization"), ("AlphaFold 2", "algorithm"), ("Nature", "publication"), ("2021", "date"), ("CASP14", "event"), ("protein structure prediction", "concept")],
     [("AlphaFold 2", "DeepMind", "AUTHORED_BY"), ("AlphaFold 2", "Nature", "PUBLISHED_IN"), ("AlphaFold 2", "protein structure prediction", "APPLIES_TO")],
     "which 2021 DeepMind system effectively solved protein structure prediction at CASP14",
     "AlphaFold CASP14 protein structure DeepMind Nature year"),
    # --- 6 ---
    ("OpenAI's InstructGPT paper of 2022 shows that reinforcement learning from human feedback fine-tunes GPT-3 to follow instructions more reliably than pure supervised fine-tuning.", "reference", "knowledge", False,
     [("OpenAI", "organization"), ("InstructGPT", "publication"), ("2022", "date"), ("reinforcement learning from human feedback", "method"), ("GPT-3", "algorithm"), ("supervised fine-tuning", "method")],
     [("InstructGPT", "OpenAI", "AUTHORED_BY"), ("reinforcement learning from human feedback", "supervised fine-tuning", "IMPROVES_ON")],
     "which 2022 OpenAI paper showed RLHF beats plain supervised fine-tuning for instruction following",
     "InstructGPT RLHF OpenAI supervised fine tuning GPT-3 year"),
    # --- 7 ---
    ("Kaplan et al.'s Scaling Laws for Neural Language Models, posted to arXiv in 2020 from OpenAI, established power-law relationships between loss, parameters, data, and compute.", "reference", "knowledge", False,
     [("Kaplan", "person"), ("Scaling Laws for Neural Language Models", "publication"), ("arXiv", "platform"), ("2020", "date"), ("OpenAI", "organization"), ("power-law", "concept")],
     [("Scaling Laws for Neural Language Models", "Kaplan", "AUTHORED_BY"), ("Scaling Laws for Neural Language Models", "OpenAI", "AUTHORED_BY")],
     "which 2020 OpenAI paper formalised neural language model scaling as power laws",
     "Kaplan scaling laws OpenAI power law parameters compute year"),
    # --- 8 ---
    ("Hoffmann et al.'s Chinchilla paper from DeepMind in 2022 revised compute-optimal scaling, arguing that data should scale roughly in proportion to parameters and improving on Kaplan scaling laws.", "reference", "knowledge", False,
     [("Hoffmann", "person"), ("Chinchilla", "algorithm"), ("DeepMind", "organization"), ("2022", "date"), ("Kaplan scaling laws", "theory")],
     [("Chinchilla", "Hoffmann", "AUTHORED_BY"), ("Chinchilla", "DeepMind", "AUTHORED_BY"), ("Chinchilla", "Kaplan scaling laws", "IMPROVES_ON")],
     "which 2022 DeepMind paper updated compute-optimal scaling against Kaplan",
     "Chinchilla Hoffmann DeepMind compute optimal data parameter scaling year"),
    # --- 9 ---
    ("Wei et al.'s Chain-of-Thought Prompting paper at NeurIPS 2022 showed that prompting large models to produce intermediate reasoning steps improves arithmetic and commonsense benchmarks.", "reference", "knowledge", False,
     [("Wei", "person"), ("Chain-of-Thought Prompting", "publication"), ("NeurIPS", "event"), ("2022", "date"), ("intermediate reasoning steps", "method")],
     [("Chain-of-Thought Prompting", "Wei", "AUTHORED_BY"), ("Chain-of-Thought Prompting", "NeurIPS", "PUBLISHED_IN")],
     "which 2022 NeurIPS paper introduced chain-of-thought prompting for large language models",
     "Wei chain of thought prompting NeurIPS reasoning steps year"),
    # --- 10. noise ---
    ("Let me double-check whether that arXiv number is for the v1 preprint or the camera-ready.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Geoffrey Hinton, Yann LeCun, and Yoshua Bengio shared the 2018 ACM Turing Award for foundational work on deep learning.", "milestone", "knowledge", False,
     [("Geoffrey Hinton", "person"), ("Yann LeCun", "person"), ("Yoshua Bengio", "person"), ("2018 ACM Turing Award", "event"), ("deep learning", "field")],
     [],
     "which three researchers shared the 2018 ACM Turing Award for deep learning",
     "Hinton LeCun Bengio Turing Award deep learning year"),
    # --- 12 ---
    ("Juergen Schmidhuber's group at IDSIA published the LSTM paper with Sepp Hochreiter in Neural Computation in 1997, addressing the vanishing-gradient problem in recurrent networks.", "reference", "knowledge", False,
     [("Juergen Schmidhuber", "person"), ("IDSIA", "organization"), ("LSTM", "algorithm"), ("Sepp Hochreiter", "person"), ("Neural Computation", "publication"), ("1997", "date"), ("vanishing-gradient problem", "concept")],
     [("LSTM", "Juergen Schmidhuber", "AUTHORED_BY"), ("LSTM", "Sepp Hochreiter", "AUTHORED_BY"), ("LSTM", "Neural Computation", "PUBLISHED_IN")],
     "who introduced LSTM in Neural Computation in 1997",
     "Hochreiter Schmidhuber LSTM Neural Computation 1997 vanishing gradient"),
    # --- 13 ---
    ("Ilya Sutskever co-founded OpenAI in 2015 and served as its chief scientist through the GPT-2, GPT-3, and GPT-4 projects.", "fact", "knowledge", False,
     [("Ilya Sutskever", "person"), ("OpenAI", "organization"), ("2015", "date"), ("GPT-2", "algorithm"), ("GPT-3", "algorithm"), ("GPT-4", "algorithm")],
     [("Ilya Sutskever", "OpenAI", "WORKS_AT")],
     "which cofounder served as the lab's head of science from its 2015 inception through the GPT-4 release",
     "cofounder chief scientist lab mid decade LLM series inception"),
    # --- 14 ---
    ("Andrej Karpathy served as head of AI at Tesla from 2017 to 2022 and is widely read for his educational nanoGPT and micrograd projects.", "fact", "knowledge", False,
     [("Andrej Karpathy", "person"), ("Tesla", "organization"), ("2017", "date"), ("2022", "date"), ("nanoGPT", "project"), ("micrograd", "project")],
     [("Andrej Karpathy", "Tesla", "WORKS_AT")],
     "which ex-OpenAI researcher ran a five-year stint as director of a car maker's autonomy group",
     "automotive autonomy director educational small GPT builder teacher tenure"),
    # --- 15 ---
    ("Richard Sutton's essay The Bitter Lesson, posted in 2019, argues that general methods leveraging computation ultimately beat hand-crafted human priors.", "reference", "knowledge", False,
     [("Richard Sutton", "person"), ("The Bitter Lesson", "publication"), ("2019", "date"), ("hand-crafted human priors", "concept")],
     [("The Bitter Lesson", "Richard Sutton", "AUTHORED_BY")],
     "which 2019 essay by Sutton argues compute-heavy general methods beat handcrafted priors",
     "Sutton bitter lesson compute general methods hand crafted year"),
    # --- 16 ---
    ("The International Conference on Learning Representations, known as ICLR, was founded by Yann LeCun and Yoshua Bengio in 2013 to focus on representation learning.", "milestone", "knowledge", False,
     [("ICLR", "event"), ("Yann LeCun", "person"), ("Yoshua Bengio", "person"), ("2013", "date"), ("representation learning", "field")],
     [("ICLR", "Yann LeCun", "AUTHORED_BY"), ("ICLR", "Yoshua Bengio", "AUTHORED_BY")],
     "who founded ICLR and in what year",
     "ICLR LeCun Bengio representation learning founding year"),
    # --- 17 ---
    ("The ImageNet Large Scale Visual Recognition Challenge, curated by Fei-Fei Li's group, ran annually from 2010 through 2017 as the defining computer vision benchmark of the decade.", "reference", "knowledge", False,
     [("ImageNet Large Scale Visual Recognition Challenge", "event"), ("Fei-Fei Li", "person"), ("2010", "date"), ("2017", "date"), ("computer vision", "field")],
     [("ImageNet Large Scale Visual Recognition Challenge", "Fei-Fei Li", "AUTHORED_BY")],
     "which benchmark curated by Fei-Fei Li defined computer vision from 2010 to 2017",
     "ImageNet ILSVRC Fei-Fei Li computer vision benchmark years"),
    # --- 18 ---
    ("SuperGLUE, released in 2019 by Wang et al., replaces the saturated GLUE benchmark with harder language understanding tasks.", "reference", "knowledge", False,
     [("SuperGLUE", "publication"), ("2019", "date"), ("Wang", "person"), ("GLUE", "publication"), ("language understanding tasks", "concept")],
     [("SuperGLUE", "Wang", "AUTHORED_BY"), ("SuperGLUE", "GLUE", "REPLACES")],
     "which 2019 benchmark replaced saturated GLUE with harder NLU tasks",
     "SuperGLUE GLUE Wang benchmark replacement NLU year"),
    # --- 19 ---
    ("Hendrycks et al.'s MMLU benchmark, introduced in 2020, measures zero-shot and few-shot accuracy across fifty-seven academic subjects.", "reference", "knowledge", False,
     [("Hendrycks", "person"), ("MMLU", "publication"), ("2020", "date"), ("zero-shot", "method"), ("few-shot", "method")],
     [("MMLU", "Hendrycks", "AUTHORED_BY")],
     "which 2020 Hendrycks benchmark spans fifty-seven academic subjects for zero-shot testing",
     "MMLU Hendrycks fifty seven subjects academic benchmark year"),
    # --- 20 ---
    ("Belkin et al.'s 2019 PNAS paper on double descent showed that test error can fall again as models cross the interpolation threshold, contradicting classical bias-variance intuition.", "reference", "knowledge", False,
     [("Belkin", "person"), ("PNAS", "publication"), ("double descent", "theory"), ("2019", "date"), ("interpolation threshold", "concept"), ("bias-variance", "theory")],
     [("double descent", "Belkin", "AUTHORED_BY"), ("double descent", "PNAS", "PUBLISHED_IN"), ("double descent", "bias-variance", "CONTRADICTS")],
     "which 2019 PNAS paper formalised the double descent phenomenon against bias-variance intuition",
     "Belkin double descent PNAS interpolation bias variance year"),
    # --- 21 ---
    ("Power et al.'s 2022 grokking paper from OpenAI describes delayed generalisation long after perfect training accuracy on small algorithmic tasks.", "reference", "knowledge", False,
     [("Power", "person"), ("grokking", "theory"), ("OpenAI", "organization"), ("2022", "date"), ("delayed generalisation", "finding")],
     [("grokking", "Power", "AUTHORED_BY"), ("grokking", "OpenAI", "AUTHORED_BY")],
     "which 2022 OpenAI paper described delayed generalisation as grokking",
     "Power grokking OpenAI delayed generalisation algorithmic task year"),
    # --- 22 ---
    ("Frankle and Carbin's 2019 ICLR paper, The Lottery Ticket Hypothesis, claims that dense networks contain sparse subnetworks trainable to comparable accuracy.", "reference", "knowledge", False,
     [("Frankle", "person"), ("Carbin", "person"), ("ICLR", "event"), ("The Lottery Ticket Hypothesis", "publication"), ("2019", "date"), ("sparse subnetworks", "concept")],
     [("The Lottery Ticket Hypothesis", "Frankle", "AUTHORED_BY"), ("The Lottery Ticket Hypothesis", "Carbin", "AUTHORED_BY"), ("The Lottery Ticket Hypothesis", "ICLR", "PUBLISHED_IN")],
     "which 2019 ICLR paper introduced the lottery ticket hypothesis for sparse subnetworks",
     "Frankle Carbin lottery ticket hypothesis ICLR sparse subnetwork year"),
    # --- 23 ---
    ("Elhage et al.'s 2022 Anthropic paper on toy models of superposition grounds mechanistic interpretability in the idea that features are encoded in directions rather than neurons.", "reference", "knowledge", False,
     [("Elhage", "person"), ("Anthropic", "organization"), ("2022", "date"), ("toy models of superposition", "publication"), ("mechanistic interpretability", "field"), ("features", "concept")],
     [("toy models of superposition", "Elhage", "AUTHORED_BY"), ("toy models of superposition", "Anthropic", "AUTHORED_BY")],
     "which 2022 Anthropic paper grounded mechanistic interpretability in superposition",
     "Elhage Anthropic toy models superposition mechanistic interpretability year"),
    # --- 24 ---
    ("Olsson et al.'s 2022 induction-heads paper from Anthropic identifies a recurring in-context learning circuit that matches and copies token patterns inside Transformers.", "reference", "knowledge", False,
     [("Olsson", "person"), ("Anthropic", "organization"), ("2022", "date"), ("induction-heads", "finding"), ("in-context learning", "concept"), ("Transformers", "algorithm")],
     [("induction-heads", "Olsson", "AUTHORED_BY"), ("induction-heads", "Anthropic", "AUTHORED_BY")],
     "which 2022 Anthropic paper identified induction heads as an in-context learning circuit",
     "Olsson Anthropic induction heads in context learning circuit year"),
    # --- 25 ---
    ("Paul Christiano's alignment research on iterated amplification, developed at OpenAI in 2018, scaffolds human oversight of increasingly capable agents.", "reference", "knowledge", False,
     [("Paul Christiano", "person"), ("iterated amplification", "method"), ("OpenAI", "organization"), ("2018", "date"), ("human oversight", "concept")],
     [("iterated amplification", "Paul Christiano", "AUTHORED_BY"), ("iterated amplification", "OpenAI", "AUTHORED_BY")],
     "who proposed iterated amplification as an alignment method at OpenAI",
     "Christiano iterated amplification alignment OpenAI oversight year"),
    # --- 26 ---
    ("Ian Goodfellow et al.'s Generative Adversarial Networks paper at NeurIPS 2014 introduced the GAN framework of a generator trained against a discriminator.", "reference", "knowledge", False,
     [("Ian Goodfellow", "person"), ("Generative Adversarial Networks", "publication"), ("NeurIPS", "event"), ("2014", "date"), ("GAN", "algorithm"), ("generator", "concept"), ("discriminator", "concept")],
     [("Generative Adversarial Networks", "Ian Goodfellow", "AUTHORED_BY"), ("Generative Adversarial Networks", "NeurIPS", "PUBLISHED_IN")],
     "which 2014 NeurIPS paper introduced GANs with a generator-discriminator pair",
     "Goodfellow GAN NeurIPS generator discriminator year"),
    # --- 27 ---
    ("Ho et al.'s Denoising Diffusion Probabilistic Models paper at NeurIPS 2020 revived diffusion modelling as a practical alternative to GANs for image generation.", "reference", "knowledge", False,
     [("Ho", "person"), ("Denoising Diffusion Probabilistic Models", "publication"), ("NeurIPS", "event"), ("2020", "date"), ("diffusion modelling", "method"), ("GANs", "algorithm")],
     [("Denoising Diffusion Probabilistic Models", "Ho", "AUTHORED_BY"), ("Denoising Diffusion Probabilistic Models", "NeurIPS", "PUBLISHED_IN"), ("diffusion modelling", "GANs", "REPLACES")],
     "which 2020 NeurIPS paper revived diffusion models as an alternative to GANs",
     "Ho DDPM diffusion NeurIPS GAN replacement year image"),
    # --- 28 ---
    ("Kingma and Ba's Adam optimiser, introduced at ICLR 2015, improves on plain SGD by combining momentum with per-parameter adaptive learning rates.", "reference", "knowledge", False,
     [("Kingma", "person"), ("Ba", "person"), ("Adam", "algorithm"), ("ICLR", "event"), ("2015", "date"), ("plain SGD", "algorithm"), ("momentum", "concept")],
     [("Adam", "Kingma", "AUTHORED_BY"), ("Adam", "Ba", "AUTHORED_BY"), ("Adam", "ICLR", "PUBLISHED_IN"), ("Adam", "plain SGD", "IMPROVES_ON")],
     "which ICLR 2015 paper introduced the Adam optimiser as an improvement over SGD",
     "Kingma Ba Adam optimiser ICLR momentum adaptive SGD year"),
    # --- 29 ---
    ("Devlin et al.'s BERT paper at NAACL 2019 replaced left-to-right language modelling with bidirectional masked-token pretraining for natural language understanding.", "reference", "knowledge", False,
     [("Devlin", "person"), ("BERT", "algorithm"), ("NAACL", "event"), ("2019", "date"), ("left-to-right language modelling", "method"), ("bidirectional masked-token pretraining", "method")],
     [("BERT", "Devlin", "AUTHORED_BY"), ("BERT", "NAACL", "PUBLISHED_IN"), ("bidirectional masked-token pretraining", "left-to-right language modelling", "REPLACES")],
     "which NAACL 2019 paper replaced left-to-right LMs with bidirectional masked pretraining",
     "Devlin BERT NAACL masked bidirectional pretraining year"),
    # --- 30 ---
    ("OpenAI's GPT-3 paper, titled Language Models are Few-Shot Learners, appeared at NeurIPS 2020 and showed that a 175 billion parameter model learns tasks from prompts alone.", "reference", "knowledge", False,
     [("OpenAI", "organization"), ("GPT-3", "algorithm"), ("Language Models are Few-Shot Learners", "publication"), ("NeurIPS", "event"), ("2020", "date"), ("175 billion parameter", "concept")],
     [("Language Models are Few-Shot Learners", "OpenAI", "AUTHORED_BY"), ("Language Models are Few-Shot Learners", "NeurIPS", "PUBLISHED_IN")],
     "which NeurIPS 2020 OpenAI paper introduced GPT-3 as a 175 billion parameter few-shot learner",
     "GPT-3 OpenAI few shot learners NeurIPS 175 billion year"),
    # --- 31 ---
    ("Facebook AI Research, commonly known as FAIR, was established by Yann LeCun in 2013 and has since released PyTorch, fastText, and Llama.", "fact", "knowledge", False,
     [("Facebook AI Research", "organization"), ("FAIR", "organization"), ("Yann LeCun", "person"), ("2013", "date"), ("PyTorch", "framework"), ("fastText", "library"), ("Llama", "algorithm")],
     [("FAIR", "Yann LeCun", "AUTHORED_BY"), ("PyTorch", "FAIR", "AUTHORED_BY")],
     "which industrial lab did Yann LeCun start in 2013 that later released PyTorch and Llama",
     "FAIR Facebook AI Research LeCun PyTorch Llama founding year"),
    # --- 32 ---
    ("Anthropic was founded in 2021 in San Francisco by former OpenAI researchers including Dario Amodei and Daniela Amodei, focusing on AI safety research.", "milestone", "knowledge", False,
     [("Anthropic", "organization"), ("2021", "date"), ("San Francisco", "place"), ("OpenAI", "organization"), ("Dario Amodei", "person"), ("Daniela Amodei", "person"), ("AI safety", "field")],
     [("Anthropic", "Dario Amodei", "AUTHORED_BY"), ("Anthropic", "San Francisco", "LOCATED_IN")],
     "when and where was Anthropic founded and by whom",
     "Anthropic founding Dario Daniela Amodei San Francisco safety year"),
    # --- 33 ---
    ("Mila, the Quebec Artificial Intelligence Institute, was founded by Yoshua Bengio in Montreal in 1993 and has become one of the largest academic deep learning groups.", "fact", "knowledge", False,
     [("Mila", "organization"), ("Quebec Artificial Intelligence Institute", "organization"), ("Yoshua Bengio", "person"), ("Montreal", "place"), ("1993", "date"), ("deep learning", "field")],
     [("Mila", "Yoshua Bengio", "AUTHORED_BY"), ("Mila", "Montreal", "LOCATED_IN")],
     "which Montreal academic deep learning institute did Bengio start in 1993",
     "Mila Bengio Quebec Montreal academic deep learning founding year"),
    # --- 34. noise ---
    ("Hmm, I should double-check whether that ablation was in the appendix or the main text.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("Bommasani et al.'s 2021 Stanford paper On the Opportunities and Risks of Foundation Models coined the term foundation model for large pretrained systems.", "reference", "knowledge", False,
     [("Bommasani", "person"), ("Stanford", "organization"), ("On the Opportunities and Risks of Foundation Models", "publication"), ("2021", "date"), ("foundation model", "concept")],
     [("On the Opportunities and Risks of Foundation Models", "Bommasani", "AUTHORED_BY"), ("On the Opportunities and Risks of Foundation Models", "Stanford", "AUTHORED_BY")],
     "which 2021 Stanford paper coined the term foundation model",
     "Bommasani Stanford foundation models opportunities risks year"),
    # --- 36 ---
    ("Bender et al.'s Stochastic Parrots paper at FAccT 2021 critiqued scaling language models on environmental, social, and epistemic grounds.", "reference", "knowledge", False,
     [("Bender", "person"), ("Stochastic Parrots", "publication"), ("FAccT", "event"), ("2021", "date"), ("scaling language models", "claim")],
     [("Stochastic Parrots", "Bender", "AUTHORED_BY"), ("Stochastic Parrots", "FAccT", "PUBLISHED_IN"), ("Stochastic Parrots", "scaling language models", "CONTRADICTS")],
     "which 2021 FAccT paper critiqued scaling language models as stochastic parrots",
     "Bender stochastic parrots FAccT language model scaling year"),
    # --- 37 ---
    ("Volodymyr Mnih et al.'s Deep Q-Network paper in Nature 2015 fused Q-learning with convolutional networks to play Atari games from raw pixels.", "reference", "knowledge", False,
     [("Volodymyr Mnih", "person"), ("Deep Q-Network", "algorithm"), ("Nature", "publication"), ("2015", "date"), ("Q-learning", "method"), ("Atari", "platform")],
     [("Deep Q-Network", "Volodymyr Mnih", "AUTHORED_BY"), ("Deep Q-Network", "Nature", "PUBLISHED_IN"), ("Deep Q-Network", "Q-learning", "BUILDS_ON")],
     "which 2015 Nature paper used deep Q-learning to play Atari from raw pixels",
     "Mnih DQN Nature Atari Q learning pixels year"),
    # --- 38 ---
    ("Silver et al.'s 2017 Nature paper introduced AlphaZero, which learned chess, shogi, and Go from self-play alone and replaces the hand-engineered evaluations of Stockfish-style engines.", "reference", "knowledge", False,
     [("Silver", "person"), ("AlphaZero", "algorithm"), ("Nature", "publication"), ("2017", "date"), ("self-play", "method"), ("Stockfish-style engines", "algorithm")],
     [("AlphaZero", "Silver", "AUTHORED_BY"), ("AlphaZero", "Nature", "PUBLISHED_IN"), ("AlphaZero", "Stockfish-style engines", "REPLACES")],
     "which 2017 Nature paper introduced self-play AlphaZero across chess, shogi, and Go",
     "Silver AlphaZero Nature self play chess shogi Go year"),
    # --- 39 ---
    ("Radford et al.'s CLIP paper, released by OpenAI in 2021, learned joint image-text representations from four hundred million web pairs using contrastive objectives.", "reference", "knowledge", False,
     [("Radford", "person"), ("CLIP", "algorithm"), ("OpenAI", "organization"), ("2021", "date"), ("image-text representations", "concept"), ("contrastive objectives", "method")],
     [("CLIP", "Radford", "AUTHORED_BY"), ("CLIP", "OpenAI", "AUTHORED_BY")],
     "which 2021 OpenAI paper introduced CLIP as a contrastive image-text model",
     "Radford CLIP OpenAI contrastive image text pairs year"),
    # --- 40 ---
    ("The Gemini 1.5 technical report, released by Google DeepMind in December 2023, documents a natively multimodal family that improves on the text-only Gemini-Pro predecessor on several benchmarks.", "reference", "knowledge", False,
     [("Gemini 1.5 technical report", "publication"), ("Google DeepMind", "organization"), ("December 2023", "date"), ("Gemini-Pro", "algorithm")],
     [("Gemini 1.5 technical report", "Google DeepMind", "AUTHORED_BY"), ("Gemini 1.5 technical report", "Gemini-Pro", "IMPROVES_ON")],
     "which December 2023 Google DeepMind report introduced the multimodal Gemini family",
     "Gemini Google DeepMind technical report multimodal year"),
    # --- 41 ---
    ("Ouyang et al.'s 2022 InstructGPT paper formalised a three-stage RLHF recipe of supervised fine-tuning, reward modelling, and PPO optimisation.", "architecture", "knowledge", False,
     [("Ouyang", "person"), ("InstructGPT", "publication"), ("2022", "date"), ("RLHF", "method"), ("supervised fine-tuning", "method"), ("reward modelling", "method"), ("PPO", "algorithm")],
     [("InstructGPT", "Ouyang", "AUTHORED_BY"), ("RLHF", "PPO", "USES")],
     "which 2022 paper formalised the three-stage RLHF recipe used in InstructGPT",
     "Ouyang InstructGPT RLHF SFT reward PPO three stage year"),
    # --- 42 ---
    ("Hu et al.'s LoRA paper at ICLR 2022 introduced low-rank adapters that fine-tune large language models at a fraction of the full-parameter cost.", "reference", "knowledge", False,
     [("Hu", "person"), ("LoRA", "method"), ("ICLR", "event"), ("2022", "date"), ("low-rank adapters", "concept"), ("large language models", "concept")],
     [("LoRA", "Hu", "AUTHORED_BY"), ("LoRA", "ICLR", "PUBLISHED_IN"), ("LoRA", "large language models", "APPLIES_TO")],
     "which ICLR 2022 paper introduced low-rank adapters under the name LoRA",
     "Hu LoRA low rank adapters ICLR fine tuning year"),
    # --- 43 ---
    ("Rafailov et al.'s Direct Preference Optimization paper at NeurIPS 2023 replaces the PPO stage of RLHF with a simpler closed-form preference objective.", "reference", "knowledge", False,
     [("Rafailov", "person"), ("Direct Preference Optimization", "publication"), ("NeurIPS", "event"), ("2023", "date"), ("PPO", "algorithm"), ("RLHF", "method")],
     [("Direct Preference Optimization", "Rafailov", "AUTHORED_BY"), ("Direct Preference Optimization", "NeurIPS", "PUBLISHED_IN"), ("Direct Preference Optimization", "PPO", "REPLACES")],
     "who proposed a closed-form preference objective that supplants the PPO stage of RLHF",
     "Rafailov DPO closed form preference objective NeurIPS proximal policy drop"),
    # --- 44 ---
    ("Lewis et al.'s Retrieval-Augmented Generation paper at NeurIPS 2020 combined a dense retriever with a seq2seq generator to ground open-domain question answering in external text.", "reference", "knowledge", False,
     [("Lewis", "person"), ("Retrieval-Augmented Generation", "publication"), ("NeurIPS", "event"), ("2020", "date"), ("dense retriever", "method"), ("seq2seq generator", "algorithm"), ("open-domain question answering", "concept")],
     [("Retrieval-Augmented Generation", "Lewis", "AUTHORED_BY"), ("Retrieval-Augmented Generation", "NeurIPS", "PUBLISHED_IN")],
     "which NeurIPS 2020 paper introduced retrieval-augmented generation for open-domain QA",
     "Lewis RAG retrieval augmented generation NeurIPS seq2seq year"),
    # --- 45 ---
    ("The ACL conference, organised by the Association for Computational Linguistics, is the primary venue for natural language processing research alongside EMNLP and NAACL.", "fact", "knowledge", False,
     [("ACL", "event"), ("Association for Computational Linguistics", "organization"), ("natural language processing", "field"), ("EMNLP", "event"), ("NAACL", "event")],
     [("ACL", "Association for Computational Linguistics", "AUTHORED_BY")],
     "which conference organised by the ACL association anchors NLP research",
     "ACL EMNLP NAACL computational linguistics venues NLP"),
    # --- 46 ---
    ("ICML, the International Conference on Machine Learning, has run since 1980 and is co-equal with NeurIPS as the flagship general-purpose machine learning venue.", "fact", "knowledge", False,
     [("ICML", "event"), ("International Conference on Machine Learning", "event"), ("1980", "date"), ("NeurIPS", "event"), ("machine learning", "field")],
     [],
     "which flagship ML conference has run since 1980 alongside NeurIPS",
     "ICML International Conference Machine Learning NeurIPS flagship year"),
    # --- 47 ---
    ("David Silver leads DeepMind's reinforcement learning group and co-authored the AlphaGo, AlphaZero, and MuZero lines of research.", "fact", "knowledge", False,
     [("David Silver", "person"), ("DeepMind", "organization"), ("reinforcement learning", "field"), ("AlphaGo", "algorithm"), ("AlphaZero", "algorithm"), ("MuZero", "algorithm")],
     [("David Silver", "DeepMind", "WORKS_AT"), ("MuZero", "AlphaZero", "BUILDS_ON")],
     "who directs the RL programme behind the Go, chess, and model-based game-playing agents at DeepMind",
     "Silver RL London lab Go chess model based game playing lineage"),
    # --- 48 ---
    ("Dosovitskiy et al.'s Vision Transformer paper at ICLR 2021 showed that pure Transformer encoders can match or beat convolutional networks on large-scale image classification.", "reference", "knowledge", False,
     [("Dosovitskiy", "person"), ("Vision Transformer", "algorithm"), ("ICLR", "event"), ("2021", "date"), ("Transformer encoders", "algorithm"), ("convolutional networks", "algorithm")],
     [("Vision Transformer", "Dosovitskiy", "AUTHORED_BY"), ("Vision Transformer", "ICLR", "PUBLISHED_IN"), ("Vision Transformer", "convolutional networks", "IMPROVES_ON")],
     "which ICLR 2021 paper showed pure Transformers can match CNNs on image classification",
     "Dosovitskiy ViT Vision Transformer ICLR ImageNet CNN year"),
    # --- 49 ---
    ("Chris Olah's distill.pub articles on circuits and feature visualisation, published between 2017 and 2020, seeded the modern mechanistic interpretability programme.", "reference", "knowledge", False,
     [("Chris Olah", "person"), ("distill.pub", "publication"), ("circuits", "concept"), ("feature visualisation", "method"), ("2017", "date"), ("2020", "date"), ("mechanistic interpretability", "field")],
     [("distill.pub", "Chris Olah", "AUTHORED_BY")],
     "whose distill.pub writings seeded modern mechanistic interpretability between 2017 and 2020",
     "Olah distill pub circuits feature visualisation interpretability years"),
    # --- 50. noise ---
    ("Wait, I need to recheck whether the scaling-law fit used tokens or training steps on that axis.", "fact", "noise", True, [], [], None, None),
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
