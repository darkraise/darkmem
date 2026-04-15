"""One-off emitter for document-stub batch-001 — article, paper, tutorial mix.

Writes 50 rows to data/v2/documents/batch_001.tmp.jsonl with ids doc-00001..00050.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "documents" / "batch_001.tmp.jsonl"
ID_OFFSET = 0

# (text, doc_type) — 17 article + 17 paper + 16 tutorial
ROWS: list[tuple[str, str]] = [
    # ---------- 17 articles ----------
    (
        "When the last espresso machine in the neighborhood cafe finally hissed its goodbye, "
        "the regulars reacted with something between grief and mild panic. For three decades, "
        "the corner shop on Linden Street had been a refuge for writers, freelancers, and "
        "the occasional philosopher. Its closure says something larger about what rising rents "
        "are doing to our communal third spaces. Talk to any barista who survived the pandemic "
        "and you will hear the same story: margins thinner than the crema on their flat whites.",
        "article",
    ),
    (
        "Silicon Valley's latest obsession is not another chatbot, but the humble pickleball court. "
        "Executives who once filled their calendars with golf outings now schedule dawn doubles "
        "matches before boardroom battles. Some call it networking theater; others insist the "
        "sport's low barrier to entry makes it a genuine equalizer. Whatever the motive, the "
        "industry has already attracted venture capital, celebrity investors, and enough merch "
        "to outfit a small city. Whether the craze endures beyond a few summer seasons, however, "
        "remains anyone's guess.",
        "article",
    ),
    (
        "It is tempting to dismiss the so-called slow reading movement as nostalgia dressed up "
        "in Scandinavian minimalism. But spend an afternoon at one of their monthly salons and "
        "you will find thoughtful people wrestling, genuinely, with ideas that do not fit in a "
        "tweet. The movement rejects skim culture without moralizing about it. That restraint, "
        "I think, is why it is catching on. In a year of shouting, a room full of people turning "
        "paper pages feels almost radical.",
        "article",
    ),
    (
        "The northern lights came for Kansas this week, and nobody was prepared. Farmers "
        "stepping out to check their cattle reported skies of impossible green, streaked with "
        "pinks that rivaled any postcard from Tromso. Space weather forecasters had warned of "
        "a severe geomagnetic storm, yet the geographic reach still stunned observers. For a "
        "region that rarely makes astronomy headlines, it was a reminder that the sun keeps its "
        "own schedule, indifferent to ours.",
        "article",
    ),
    (
        "Ask any veteran sportswriter what killed the beat reporter, and they will point first "
        "at the collapse of classified ads, then at social media, and finally at ownership "
        "groups who mistake cost cutting for strategy. What gets lost is the slow accumulation "
        "of knowledge: the sources cultivated over decades, the quiet interviews in empty "
        "clubhouses. A team's press release cannot replace that texture, even if the analytics "
        "dashboard pretends otherwise.",
        "article",
    ),
    (
        "Reykjavik in November feels like a city holding its breath. The sun barely clears the "
        "harbor before retreating, and locals move through blue twilight with the quiet "
        "competence of people who have negotiated darkness their whole lives. Tourists expect "
        "gloom. What they find instead is a capital lit from within, its bookshops and swimming "
        "pools glowing like lanterns. You leave with the sense that the Icelanders have figured "
        "out something the rest of us missed.",
        "article",
    ),
    (
        "The new wave of mid-budget films is quietly rescuing cinema from its blockbuster funk. "
        "Directors who spent a decade pitching to streamers are rediscovering the theatrical "
        "window, armed with budgets modest enough to take creative risks. Audiences, for their "
        "part, seem grateful for stories that do not involve multiverses or costumes that weigh "
        "more than the actors wearing them. Whether studios learn from the trend or suffocate "
        "it is an open question.",
        "article",
    ),
    (
        "My grandmother kept a notebook of every loaf of bread she ever baked. Flour brand, "
        "hydration, weather, the mood of the kitchen. I found it last week, tucked behind a "
        "stack of seed catalogs, and spent an evening reading entries from 1974. The precision "
        "stunned me. She had been doing data science before anyone called it that, and her "
        "sourdough, I now understand, was the output of a forty-year experiment.",
        "article",
    ),
    (
        "Downtown's newest gallery has no walls. Instead, the curator hangs paintings from "
        "suspended cables in a converted foundry, inviting visitors to weave between canvases "
        "as if walking through a forest. Critics are split: some call it gimmickry, others a "
        "genuine rethinking of how we encounter art. Attendance numbers, at least, do not lie. "
        "The opening drew lines around the block in a neighborhood that had not seen a queue "
        "for culture in years.",
        "article",
    ),
    (
        "Electric vans are finally making sense for the people who actually need them. Ask a "
        "plumber doing six jobs a day across town, and the math now pencils out where it did "
        "not eighteen months ago. Fleet managers have noticed too, quietly swapping diesel "
        "workhorses for battery models that cost less to fuel and almost nothing to service. "
        "The revolution, as usual, is arriving through the service entrance rather than the "
        "showroom.",
        "article",
    ),
    (
        "There is a particular kind of bookstore that cannot be replicated online, and Powell's "
        "is the archetype. Walk in on a rainy afternoon and you enter a warren of rooms where "
        "the categories bleed into each other and a clerk with ink-stained fingers will "
        "cheerfully argue that you are wrong about Bolano. Amazon sells more books. Powell's "
        "sells the afternoon.",
        "article",
    ),
    (
        "The cycling boom of the early twenties left a peculiar legacy: a generation of adults "
        "who suddenly remember, viscerally, what freedom felt like at eleven. City planners "
        "have scrambled to catch up, paving protected lanes at a pace unthinkable a decade ago. "
        "Detractors grumble about parking. Proponents point to the children now riding to "
        "school unaccompanied, a small miracle many of us had written off as impossible in the "
        "age of the SUV.",
        "article",
    ),
    (
        "There was a time when every small town had a mayor who could name half the residents "
        "on sight. That era is not quite dead, but it is wheezing. As hollowed-out downtowns "
        "give way to dollar stores and drive-thrus, the civic rituals that once stitched "
        "communities together have thinned. The question is whether the new crop of young "
        "candidates, many of them returning from big cities, can reweave what was lost.",
        "article",
    ),
    (
        "I spent a week at a silent retreat in the Catskills and came home convinced my phone "
        "had been lying to me. Not about anything specific, just in the general sense that its "
        "endless notifications were passing themselves off as urgency when they were mostly "
        "noise. A friend asked me afterward whether the silence was boring. It was not. It was "
        "the first time in years my thoughts had room to finish themselves.",
        "article",
    ),
    (
        "The farmer's market on Saturday mornings has become an unlikely political institution. "
        "Between the heirloom tomatoes and the sourdough stand, you can find petition tables, "
        "mayoral candidates pressing flesh, and retirees mapping out neighborhood watch routes. "
        "It is not the forum the founders imagined, but it may be the one we have. Democracy, "
        "like produce, is better when local.",
        "article",
    ),
    (
        "Country music has always been a genre that claims to distrust change while quietly "
        "absorbing it. The latest crop of young artists out of East Nashville are the proof: "
        "pedal steel over trap drums, lyrics that quote both Townes Van Zandt and a group text. "
        "Purists hate it. Record labels cannot press vinyl fast enough. The tradition, as ever, "
        "survives by refusing to stand still.",
        "article",
    ),
    (
        "Last winter's ice storm took out the power for six days, and my neighborhood learned "
        "something our grandparents knew: the grid is a promise, not a guarantee. By day three "
        "we were cooking communal meals over propane burners in the driveway. By day five, the "
        "teenagers had organized a library run for the elderly couple on the corner. The lights "
        "came back eventually. The street, for a while, did not need them.",
        "article",
    ),
    # ---------- 17 papers ----------
    (
        "We present a novel attention mechanism for long-context language models that reduces "
        "memory overhead by a factor of 4.2x without significant degradation in perplexity. "
        "Our method, termed sparse-banded attention, restricts the attention matrix to a "
        "block-diagonal structure learned jointly with the input embeddings. Experiments on "
        "the PG-19 and Long Range Arena benchmarks demonstrate parity with dense attention at "
        "context lengths up to 32,768 tokens. We release code and pretrained checkpoints to "
        "facilitate reproducibility.",
        "paper",
    ),
    (
        "Abstract. This study investigates the role of soil microbial diversity in mediating "
        "nitrogen retention under elevated atmospheric carbon dioxide. Using a randomized "
        "block design across twelve temperate grassland plots, we quantify shifts in bacterial "
        "and fungal community composition via 16S and ITS amplicon sequencing. Results "
        "indicate a statistically significant (p < 0.01) increase in nitrogen immobilization "
        "correlated with fungal-to-bacterial ratio. These findings refine existing biogeochemical "
        "models and suggest that microbial community structure is a non-negligible parameter in "
        "climate projections.",
        "paper",
    ),
    (
        "We propose a new estimator for causal effects under partial interference that relaxes "
        "the stable unit treatment value assumption (SUTVA). Theoretical analysis establishes "
        "consistency and asymptotic normality under mild regularity conditions. Monte Carlo "
        "simulations across 1,000 replications demonstrate lower mean squared error than "
        "standard inverse probability weighting, particularly in settings with clustered "
        "treatment assignment. We apply the method to a large-scale vaccine trial and report "
        "revised estimates of indirect protective effects.",
        "paper",
    ),
    (
        "This paper derives closed-form expressions for the equilibrium price in a continuous-time "
        "limit order book under the assumption of risk-neutral market makers with bounded "
        "inventory. The proposed model generalizes prior work by Almgren and Chriss to "
        "heterogeneous informed trading. We prove existence and uniqueness of the equilibrium "
        "via a fixed-point argument on the space of admissible strategies. Empirical calibration "
        "to high-frequency NASDAQ data yields parameter estimates consistent with theoretical "
        "predictions within a 95% confidence interval.",
        "paper",
    ),
    (
        "Abstract. We report the synthesis and characterization of a novel metal-organic "
        "framework (MOF-217) exhibiting selective carbon dioxide uptake at ambient temperature "
        "and pressure. Single-crystal X-ray diffraction reveals a previously unreported "
        "topology with pore diameters of 5.8 angstroms. Breakthrough experiments demonstrate "
        "a CO2/N2 selectivity of 142, surpassing benchmark materials Mg-MOF-74 and zeolite 13X. "
        "Density functional theory calculations rationalize the observed selectivity via "
        "favorable electrostatic interactions with open metal sites.",
        "paper",
    ),
    (
        "We investigate the convergence properties of stochastic gradient descent under "
        "heavy-tailed noise distributions. Prior analyses typically assume sub-Gaussian or "
        "bounded-variance gradients; we relax this assumption to the class of alpha-stable "
        "distributions with 1 < alpha <= 2. Under this setting, we establish an expected "
        "regret bound of O(T^((alpha-1)/alpha)) and demonstrate tightness via a matching lower "
        "bound. Empirical results on deep neural network training corroborate the theoretical "
        "scaling.",
        "paper",
    ),
    (
        "Abstract. This longitudinal cohort study (N = 4,872) examines the association between "
        "adolescent screen time and depressive symptomatology over a six-year follow-up period. "
        "Using cross-lagged panel models with fixed effects for individual heterogeneity, we "
        "find a small but statistically significant bidirectional relationship (standardized "
        "beta = 0.08, p < 0.001). Effect sizes do not support causal interpretations commonly "
        "advanced in the popular press. We discuss implications for clinical guidance and "
        "public health messaging.",
        "paper",
    ),
    (
        "We introduce a differentially private mechanism for federated learning that achieves "
        "(epsilon, delta)-privacy with improved utility relative to prior art. Our construction "
        "combines local Gaussian noise injection with a secure aggregation protocol, yielding "
        "a privacy amplification factor of sqrt(n) for n participating clients. Experiments on "
        "FEMNIST and Shakespeare benchmarks demonstrate accuracy within 1.3% of non-private "
        "baselines at epsilon = 1.0. We provide formal proofs and open-source implementations.",
        "paper",
    ),
    (
        "Abstract. We present a phylogenetic analysis of 312 complete mitochondrial genomes "
        "from extant and extinct Equidae, incorporating newly recovered ancient DNA from three "
        "Pleistocene specimens. Bayesian inference under a relaxed molecular clock places the "
        "divergence of modern horses and asses at approximately 4.7 million years before "
        "present (95% highest posterior density: 4.1-5.3 Mya). These results revise earlier "
        "estimates and have implications for our understanding of late Miocene grassland "
        "expansion.",
        "paper",
    ),
    (
        "This paper examines the welfare effects of minimum wage increases using a "
        "difference-in-differences design leveraging geographic variation in state-level "
        "policy between 2012 and 2022. Employing administrative payroll records covering "
        "27 million workers, we estimate employment elasticities in the range of -0.08 to "
        "-0.15, with heterogeneity across industry and firm size. Our findings are robust to "
        "alternative control group specifications and to the synthetic control method of "
        "Abadie et al. (2010).",
        "paper",
    ),
    (
        "We describe a novel fault-tolerant quantum error correction scheme based on "
        "low-density parity-check codes on hyperbolic surfaces. The construction achieves a "
        "constant encoding rate of 1/12 and a threshold of approximately 0.7% under "
        "circuit-level depolarizing noise, as determined by Monte Carlo simulation of the "
        "belief propagation decoder. These results represent, to our knowledge, the first "
        "demonstration that hyperbolic LDPC codes outperform the surface code in the "
        "asymptotic regime.",
        "paper",
    ),
    (
        "Abstract. We conducted a double-blind, randomized controlled trial (N = 248) to "
        "evaluate the efficacy of a twelve-week mindfulness-based stress reduction program on "
        "cortisol awakening response in adults with chronic insomnia. The intervention group "
        "exhibited a 23% reduction in morning cortisol relative to active control (p = 0.003, "
        "Cohen's d = 0.42). Secondary outcomes included self-reported sleep quality and "
        "actigraphic measures. We discuss limitations and directions for future research.",
        "paper",
    ),
    (
        "This work presents a theoretical framework for analyzing the expressivity of graph "
        "neural networks beyond the Weisfeiler-Lehman hierarchy. We introduce a family of "
        "higher-order message-passing architectures parameterized by a locality radius k and "
        "prove a strict separation result: for every k there exists a graph distinguishable "
        "by our model but not by any k-WL-equivalent architecture. Experimental evaluation on "
        "molecular property prediction benchmarks confirms the theoretical advantage.",
        "paper",
    ),
    (
        "Abstract. Using high-resolution satellite imagery and convolutional neural networks, "
        "we produce the first continuous estimate of urban tree canopy cover across 102 "
        "African cities. Results indicate a median canopy cover of 8.3%, with substantial "
        "inter-city variation (interquartile range: 4.1%-14.7%). Canopy cover correlates "
        "negatively with population density (Spearman's rho = -0.51) and positively with "
        "per-capita income. We discuss implications for urban heat mitigation and climate "
        "adaptation policy.",
        "paper",
    ),
    (
        "We formalize and study the problem of online bipartite matching under adversarial "
        "vertex arrivals with predictions. Our main contribution is a learning-augmented "
        "algorithm achieving a competitive ratio of 1 - 1/e + Omega(eta), where eta "
        "characterizes prediction accuracy. The bound interpolates smoothly between the "
        "classical RANKING result and the optimal offline solution. We complement the upper "
        "bound with a matching lower bound up to lower-order terms.",
        "paper",
    ),
    (
        "Abstract. This paper reports results from a field experiment (N = 3,214 households) "
        "evaluating the impact of behavioral nudges on residential energy consumption. "
        "Treatment households received monthly social comparison reports benchmarking their "
        "usage against efficient neighbors. We observe an average reduction of 2.1% over the "
        "twelve-month study period (95% CI: 1.4%-2.8%), with persistent effects eighteen "
        "months after intervention cessation. Cost-effectiveness calculations suggest the "
        "program is competitive with traditional energy efficiency rebates.",
        "paper",
    ),
    (
        "We propose a unified variational framework for approximate Bayesian inference in "
        "state-space models with non-Gaussian observation noise. The method extends "
        "existing stochastic variational inference to handle heavy-tailed and discrete "
        "emissions via a reparameterized score-function estimator. Simulation studies "
        "demonstrate improved accuracy over particle filtering at comparable computational "
        "cost. We illustrate applicability on a neural spike train dataset and a financial "
        "volatility forecasting task.",
        "paper",
    ),
    # ---------- 16 tutorials ----------
    (
        "In this tutorial you will set up a Python virtual environment and install the "
        "requests library. Step 1: Open your terminal and navigate to your project folder. "
        "Step 2: Run `python -m venv .venv` to create the environment. Step 3: Activate it "
        "with `source .venv/bin/activate` on macOS or Linux, or `.venv\\Scripts\\activate` "
        "on Windows. Step 4: Install the package by running `pip install requests`. Step 5: "
        "Verify the install with `python -c \"import requests; print(requests.__version__)\"`.",
        "tutorial",
    ),
    (
        "Let's build a simple REST endpoint with FastAPI. First, install the framework: "
        "`pip install fastapi uvicorn`. Next, create a file named `main.py` and add the "
        "following code: `from fastapi import FastAPI\\napp = FastAPI()\\n@app.get('/')\\n"
        "def root(): return {'hello': 'world'}`. Now start the server with "
        "`uvicorn main:app --reload`. Finally, open http://127.0.0.1:8000 in your browser. "
        "You should see the JSON response. In the next section we will add a POST route.",
        "tutorial",
    ),
    (
        "This guide walks you through baking a basic sourdough loaf. Step 1: Mix 500 g of "
        "bread flour, 350 g of water, and 100 g of active starter in a large bowl. Step 2: "
        "Let the dough rest for 30 minutes, then add 10 g of salt. Step 3: Perform four sets "
        "of stretch-and-folds, spaced 30 minutes apart. Step 4: Bulk ferment until the dough "
        "has risen by about 50%. Step 5: Shape, cold-proof overnight, then bake at 475F in a "
        "preheated Dutch oven for 25 minutes covered and 20 minutes uncovered.",
        "tutorial",
    ),
    (
        "To clone a Git repository and create your first branch, follow these steps. First, "
        "copy the repo URL from your provider. Then run `git clone <url>` in your terminal. "
        "Next, change into the new directory with `cd <repo-name>`. Now create a branch by "
        "running `git checkout -b feature/my-change`. Make your edits, stage them with "
        "`git add .`, and commit using `git commit -m \"describe your change\"`. Finally, "
        "push the branch to the remote with `git push -u origin feature/my-change`.",
        "tutorial",
    ),
    (
        "In this walkthrough you will deploy a static website to Netlify. Step 1: Sign in to "
        "Netlify and click \"Add new site\". Step 2: Connect your GitHub account and select "
        "the repository. Step 3: Set the build command to `npm run build` and the publish "
        "directory to `dist`. Step 4: Click \"Deploy site\" and wait for the build to "
        "complete. Step 5: Once the status turns green, visit the generated URL to confirm "
        "your site is live. To add a custom domain, proceed to the Domain settings panel.",
        "tutorial",
    ),
    (
        "Let's configure SSH key authentication for GitHub. First, generate a new key pair "
        "by running `ssh-keygen -t ed25519 -C \"you@example.com\"`. Accept the default path "
        "and set a strong passphrase. Next, start the SSH agent with `eval \"$(ssh-agent -s)\"` "
        "and add the key using `ssh-add ~/.ssh/id_ed25519`. Then copy the public key with "
        "`cat ~/.ssh/id_ed25519.pub` and paste it into GitHub under Settings > SSH keys. "
        "Finally, verify with `ssh -T git@github.com`.",
        "tutorial",
    ),
    (
        "This tutorial shows you how to make pour-over coffee. Step 1: Bring 400 g of water "
        "to 205F. Step 2: Weigh out 25 g of medium-coarse ground coffee into the filter. "
        "Step 3: Place the dripper on your carafe and rinse the filter with hot water, then "
        "discard. Step 4: Pour 50 g of water in a slow circle to bloom the grounds for 30 "
        "seconds. Step 5: Continue pouring in three pulses until you hit 400 g total. Step 6: "
        "Allow the drawdown to finish, then swirl and serve.",
        "tutorial",
    ),
    (
        "To create your first Docker container, follow these steps. First, install Docker "
        "Desktop from docker.com and verify with `docker --version`. Next, create a file "
        "named `Dockerfile` with the contents `FROM python:3.11-slim\\nCMD [\"python\", \"-c\", "
        "\"print('hello')\"]`. Then build the image by running `docker build -t hello .` in "
        "the same directory. Finally, run the container with `docker run --rm hello`. You "
        "should see the greeting printed. Remove the image later with `docker rmi hello`.",
        "tutorial",
    ),
    (
        "In this section we will write your first unit test with pytest. Step 1: Install "
        "pytest by running `pip install pytest`. Step 2: Create a file named `test_math.py` "
        "and add the following: `def test_addition(): assert 1 + 1 == 2`. Step 3: Run the "
        "test suite with `pytest`. Step 4: Confirm you see `1 passed` in the output. Step 5: "
        "Add a failing test to see what errors look like, then correct it. You now have a "
        "working test harness to build on.",
        "tutorial",
    ),
    (
        "Let's set up a simple cron job on Linux to back up a folder nightly. First, open "
        "your crontab for editing with `crontab -e`. Next, add the following line: "
        "`0 2 * * * tar -czf /backup/home-$(date +\\%F).tar.gz /home/user`. This runs every "
        "night at 2 AM. Save and exit the editor. Verify the job is installed by running "
        "`crontab -l`. Finally, check `/backup` the next morning to confirm the archive was "
        "created. Rotate or prune older archives with a second cron entry if needed.",
        "tutorial",
    ),
    (
        "To install Node.js using nvm, follow these steps. Step 1: Download the installer "
        "with `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | "
        "bash`. Step 2: Close and reopen your terminal, or run `source ~/.bashrc`. Step 3: "
        "Confirm nvm is available by running `nvm --version`. Step 4: Install the latest "
        "LTS release with `nvm install --lts`. Step 5: Verify the Node version with "
        "`node --version`. You can switch versions later using `nvm use <version>`.",
        "tutorial",
    ),
    (
        "This guide teaches you to whip up homemade pesto. Step 1: In a food processor, "
        "combine two cups of fresh basil leaves, three cloves of garlic, and a quarter cup "
        "of pine nuts. Step 2: Pulse until coarsely chopped. Step 3: With the motor running, "
        "slowly drizzle in half a cup of olive oil. Step 4: Stop the processor and stir in "
        "half a cup of grated Parmesan cheese. Step 5: Season with salt and black pepper to "
        "taste. Toss immediately with warm pasta and serve.",
        "tutorial",
    ),
    (
        "Let's configure a PostgreSQL database for local development. First, install the "
        "server using your package manager, for example `brew install postgresql@16`. Next, "
        "start the service with `brew services start postgresql@16`. Then create a new "
        "database by running `createdb mydevdb`. Connect to it using `psql mydevdb` and "
        "create a test table with `CREATE TABLE items (id SERIAL PRIMARY KEY, name TEXT);`. "
        "Exit the shell with `\\q`. Finally, confirm persistence by reconnecting and running "
        "`\\dt` to list your tables.",
        "tutorial",
    ),
    (
        "In this tutorial you will train a basic linear regression model with scikit-learn. "
        "Step 1: Install the library with `pip install scikit-learn`. Step 2: Import the "
        "model and load data: `from sklearn.linear_model import LinearRegression`. Step 3: "
        "Prepare your X and y arrays as NumPy arrays. Step 4: Instantiate the model with "
        "`model = LinearRegression()` and call `model.fit(X, y)`. Step 5: Make predictions "
        "using `model.predict(X_new)`. Step 6: Evaluate with `model.score(X_test, y_test)` "
        "to get the coefficient of determination.",
        "tutorial",
    ),
    (
        "To change a flat bicycle tire, follow these steps. First, flip the bike upside down "
        "and release the brakes. Then loosen the wheel's quick release and remove the wheel. "
        "Next, use tire levers to pry one edge of the tire off the rim. Pull out the old "
        "tube and inspect the inside of the tire for the cause of the puncture. Insert a "
        "new tube, seat both edges of the tire back onto the rim, and inflate to the pressure "
        "printed on the sidewall. Finally, remount the wheel and re-engage the brakes.",
        "tutorial",
    ),
    (
        "Let's create a simple React component from scratch. Step 1: Start a new project by "
        "running `npm create vite@latest my-app -- --template react`. Step 2: Change into "
        "the directory with `cd my-app` and install dependencies using `npm install`. "
        "Step 3: Open `src/App.jsx` and replace its contents with "
        "`export default function App() { return <h1>Hello</h1>; }`. Step 4: Start the dev "
        "server with `npm run dev`. Step 5: Visit the printed URL to see your component "
        "render in the browser. Edit the file to see hot reload in action.",
        "tutorial",
    ),
]

def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, doc_type) in enumerate(ROWS, start=1):
            row = {
                "id": f"doc-{ID_OFFSET + i:05d}",
                "doc_type": doc_type,
                "text": text,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written

if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
