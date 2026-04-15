"""One-off emitter for document-stub batch-002.

Writes 50 rows to data/v2/documents/batch_002.tmp.jsonl with ids
doc-00051..doc-00100. Covers three document types: reference_doc (17),
news (17), recipe (16). Each row: {id, doc_type, text}.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "documents" / "batch_002.tmp.jsonl"
ID_OFFSET = 50

# Each row: (text, doc_type)
# doc_type in {reference_doc, news, recipe}. Text 40-120 words.
ROWS: list[tuple[str, str]] = [
    # ------------------------------------------------------------------
    # reference_doc (17)
    # ------------------------------------------------------------------
    (
        "collections.deque(iterable=[], maxlen=None) returns a new deque object initialized left-to-right from iterable. Deques support thread-safe, memory-efficient appends and pops from either side with roughly O(1) performance. If maxlen is not specified, deques may grow to an arbitrary length; otherwise the deque is bounded, and new items added while the deque is full cause a corresponding number of items to be discarded from the opposite end. Key methods include append, appendleft, pop, popleft, extend, extendleft, rotate, and clear.",
        "reference_doc",
    ),
    (
        "numpy.linalg.svd(a, full_matrices=True, compute_uv=True, hermitian=False) factors a matrix A into U, S, Vh such that A equals U @ diag(S) @ Vh. When full_matrices is True the returned U and Vh have shapes (M, M) and (N, N); when False they have shapes (M, K) and (K, N) where K equals min(M, N). The singular values S are always returned in descending order. Setting hermitian=True uses a faster eigenvalue decomposition path for Hermitian matrices.",
        "reference_doc",
    ),
    (
        "torch.nn.LayerNorm(normalized_shape, eps=1e-5, elementwise_affine=True) applies Layer Normalization over a mini-batch. The mean and standard deviation are computed over the last D dimensions, where D is the length of normalized_shape. Unlike BatchNorm, statistics are computed per sample rather than across the batch, which makes LayerNorm suitable for sequence models and variable batch sizes. When elementwise_affine is True the module contains learnable per-element scale (gamma) and bias (beta) tensors with the same shape as normalized_shape.",
        "reference_doc",
    ),
    (
        "Glossary term: Referential integrity. A database property that ensures relationships between tables remain consistent. Specifically, if a foreign key column references a primary key in a parent table, every non-null value in the foreign key must match an existing primary-key value. Referential integrity is typically enforced by FOREIGN KEY constraints, which may define ON DELETE and ON UPDATE actions such as CASCADE, SET NULL, SET DEFAULT, RESTRICT, or NO ACTION to control propagation of changes across related rows.",
        "reference_doc",
    ),
    (
        "HTTP/1.1 status code 429 Too Many Requests indicates that the user has sent too many requests in a given amount of time. Servers SHOULD include a Retry-After header field in the response, which can be either an HTTP-date or an integer number of seconds after which the client may retry. The 429 status is intentionally generic: servers are not required to reveal the rate-limiting policy, though many APIs return supplementary headers such as X-RateLimit-Remaining and X-RateLimit-Reset to help clients self-regulate.",
        "reference_doc",
    ),
    (
        "pandas.DataFrame.groupby(by=None, level=None, as_index=True, sort=True, dropna=True) groups a DataFrame using a mapper or by a series of columns. The returned GroupBy object supports aggregation via agg, transformation via transform, filtering via filter, and iteration over (group_key, sub_frame) pairs. When as_index is False, the grouped columns become regular columns in the result rather than the index. Passing dropna=False preserves NaN groups, which is useful for audit-style aggregations that must account for missing keys.",
        "reference_doc",
    ),
    (
        "Rust trait std::iter::Iterator defines a method next(&mut self) -> Option<Self::Item>. Implementors must provide next; adapter methods such as map, filter, take, skip, chain, zip, and collect are supplied by default implementations. Iterators are lazy: no work is performed until a consuming method such as collect, count, sum, or for_each is called. Many adapters return their own Iterator types, enabling composition without heap allocation. The IntoIterator trait converts a type into an iterator and underpins Rust's for loop.",
        "reference_doc",
    ),
    (
        "PostgreSQL function jsonb_path_query(target jsonb, path jsonpath [, vars jsonb [, silent bool]]) returns all JSON items produced by applying the given jsonpath expression to the target. The optional vars argument supplies named parameters referenced in the path as $name. When silent is true, errors raised during path evaluation are suppressed. For a single-result variant use jsonb_path_query_first, and for membership tests use jsonb_path_exists, which returns a boolean instead of expanding matches.",
        "reference_doc",
    ),
    (
        "React hook useEffect(setup, dependencies?) runs the setup function after the component commits to the DOM. If setup returns a cleanup function, React calls it before the next setup run and again when the component unmounts. Dependencies control re-execution: passing an empty array runs setup only once after mount, passing a non-empty array runs setup whenever any referenced value changes by Object.is comparison, and omitting the argument runs setup after every render. Avoid object identity pitfalls by memoizing non-primitive dependencies.",
        "reference_doc",
    ),
    (
        "Glossary term: Idempotent operation. An operation that produces the same result whether applied once or many times with the same input. In HTTP, the methods GET, HEAD, PUT, DELETE, and OPTIONS are defined as idempotent, while POST is not. Idempotency is a property of the effect on server state, not the response body. Clients use idempotency to safely retry requests after network failures; servers often support idempotency keys so that duplicate POST submissions are coalesced server-side.",
        "reference_doc",
    ),
    (
        "Go package context provides Context values that carry deadlines, cancellation signals, and request-scoped values across API boundaries. context.Background returns an empty root Context, while context.TODO signals an unfinished design decision. Derived contexts are created by WithCancel, WithDeadline, WithTimeout, and WithValue. Callers must invoke the returned cancel function to release resources associated with the derived context, typically via defer. A Context becomes Done when any ancestor is cancelled or its deadline expires, and the Err method reports the cause.",
        "reference_doc",
    ),
    (
        "Kubernetes resource HorizontalPodAutoscaler automatically scales the number of pods in a workload based on observed metrics. The spec fields minReplicas and maxReplicas bound the replica count; metrics list the signals used for scaling, such as Resource CPU utilization, Object metrics from a named resource, or External metrics from a metrics adapter. The behavior field under HPA v2 controls scale-up and scale-down policies, including stabilization windows that dampen rapid oscillations. The controller reconciles desired replicas every 15 seconds by default.",
        "reference_doc",
    ),
    (
        "scikit-learn class sklearn.preprocessing.StandardScaler(copy=True, with_mean=True, with_std=True) standardizes features by removing the mean and scaling to unit variance. The fit method computes the mean and standard deviation per feature on the training set; transform applies the learned statistics. For sparse matrices, set with_mean=False to avoid densifying the data. The scaler exposes mean_, scale_, and var_ attributes after fitting. inverse_transform recovers the original scale, which is useful when predictions must be returned in the original feature units.",
        "reference_doc",
    ),
    (
        "Glossary term: Two-phase commit (2PC). A distributed-transaction protocol coordinating commit across multiple resource managers. In the prepare phase, the coordinator asks each participant to durably record intent to commit and reply prepared or abort. If all reply prepared, the coordinator writes a commit record and sends commit messages; otherwise it sends abort. 2PC guarantees atomicity under the assumption of durable logs and eventually reachable participants, but it blocks indefinitely if the coordinator fails after some participants have acknowledged prepare.",
        "reference_doc",
    ),
    (
        "Linux system call epoll_ctl(int epfd, int op, int fd, struct epoll_event *event) modifies the set of file descriptors monitored by an epoll instance. The op argument is EPOLL_CTL_ADD, EPOLL_CTL_MOD, or EPOLL_CTL_DEL. The events field of struct epoll_event is a bitmask including EPOLLIN, EPOLLOUT, EPOLLRDHUP, EPOLLPRI, EPOLLERR, EPOLLHUP, EPOLLET for edge-triggered mode, and EPOLLONESHOT. The data field is an opaque user token returned by epoll_wait when the descriptor becomes ready.",
        "reference_doc",
    ),
    (
        "TypeScript utility type Partial<T> constructs a type with all properties of T set to optional. It is implemented as { [P in keyof T]?: T[P] }. Related helpers include Required<T>, which strips optionality, Readonly<T>, which makes properties read-only, and Pick<T, K>, which selects a subset of keys. These mapped types compose with conditional types such as Exclude<T, U> and Extract<T, U> to express richer transformations, enabling API authors to derive patch, view, and update types from a single source of truth.",
        "reference_doc",
    ),
    (
        "Redis command ZADD key [NX | XX] [GT | LT] [CH] [INCR] score member [score member ...] adds members with scores to the sorted set stored at key. NX only adds new elements; XX only updates existing ones; GT updates a score only if the new one is greater; LT only if lesser. CH changes the reply to the number of elements added or updated rather than just added. INCR, valid for a single score-member pair, increments the score instead of replacing it and returns the new score.",
        "reference_doc",
    ),
    # ------------------------------------------------------------------
    # news (17)
    # ------------------------------------------------------------------
    (
        "BRUSSELS, April 14 — European Union lawmakers approved a revised package of clean-industry subsidies on Monday, giving member states expanded authority to match state aid offered by competitors in the United States and China. The measure, backed by a 412-163 vote in the European Parliament, covers battery plants, green hydrogen, and grid-scale storage. Commission Vice-President Maros Sefcovic told reporters the package would unlock an estimated 180 billion euros of investment by 2030. Environmental groups criticized the deal for loosening limits on fossil-based hydrogen.",
        "news",
    ),
    (
        "SAN FRANCISCO — A federal appeals court on Tuesday reinstated a class-action lawsuit against a major rideshare platform, ruling that drivers may pursue claims they were misclassified as independent contractors. The three-judge panel of the Ninth Circuit reversed a lower-court order compelling arbitration, citing a 2024 state statute that exempts gig-economy disputes from mandatory arbitration clauses. The plaintiffs, represented by the worker advocacy group Rideshare United, said the ruling could affect more than 300,000 drivers statewide. The company said it would appeal.",
        "news",
    ),
    (
        "TOKYO, April 15 — The Bank of Japan held its benchmark short-term rate at 0.5 percent on Thursday, citing softening wage growth and uneven household spending. Governor Kazuo Ueda told a post-meeting news conference that the central bank would wait for more data before considering a further move. The yen weakened to 156.30 against the dollar after the announcement. Analysts at Nomura said they now expect the next rate decision to come in July rather than June, as markets had priced in earlier this month.",
        "news",
    ),
    (
        "NAIROBI — Kenya's Ministry of Health reported on Friday that a cholera outbreak in the coastal county of Kilifi has grown to 1,240 confirmed cases and 22 deaths since early March. Health Cabinet Secretary Susan Nakhumicha said mobile treatment units had been deployed in three affected sub-counties and that the World Health Organization was supplying oral rehydration salts. Officials traced the outbreak to contaminated boreholes damaged during recent floods. A vaccination campaign targeting 250,000 residents is expected to begin next week, the ministry added.",
        "news",
    ),
    (
        "LONDON — Shares in British engineering firm Rolls-Royce rose 4.8 percent on Wednesday after the company raised its full-year profit forecast, citing stronger aftermarket demand for its civil aerospace engines. Chief Executive Tufan Erginbilgic told investors the Trent XWB fleet had flown 14 percent more hours in the first quarter than a year earlier. The FTSE 100 component now expects underlying operating profit of between 2.7 and 2.9 billion pounds for 2026, up from a prior range of 2.5 to 2.7 billion. Competitors Safran and Pratt & Whitney also gained.",
        "news",
    ),
    (
        "WASHINGTON — The Federal Trade Commission sued a leading grocery-delivery platform on Monday, accusing it of using dark patterns to enroll customers in an auto-renewing membership and making cancellation unreasonably difficult. The complaint, filed in the U.S. District Court for the Northern District of California, seeks civil penalties and refunds for affected consumers. FTC Chair Lina Khan said the case reflected the agency's broader push against subscription traps. The company denied wrongdoing and said it would vigorously defend its signup and cancellation flows in court.",
        "news",
    ),
    (
        "SEOUL, April 12 — South Korean automaker Hyundai Motor announced Saturday it will invest 4.6 trillion won, about 3.4 billion dollars, in a new electric-vehicle plant in Ulsan that is scheduled to begin production in late 2028. The facility will have annual capacity of 200,000 vehicles and will produce the company's next-generation SUV platform. Labor union officials welcomed the decision after weeks of uncertainty about domestic manufacturing commitments. Trade Minister Ahn Duk-geun said the project would create roughly 2,500 direct jobs in the southeastern industrial region.",
        "news",
    ),
    (
        "OTTAWA — Canada's statistics agency said inflation eased to 2.4 percent year-over-year in March, down from 2.7 percent in February, bringing the rate closer to the Bank of Canada's 2 percent target. Shelter costs remained the largest contributor, rising 5.1 percent, while gasoline prices fell 3.8 percent. Economists polled by Reuters had expected 2.5 percent. Governor Tiff Macklem reiterated last week that rate decisions would remain data-dependent. Markets now price a roughly 60 percent probability of a 25-basis-point cut at the Bank's June meeting.",
        "news",
    ),
    (
        "CAPE CANAVERAL, Fla. — A SpaceX Falcon 9 rocket lifted off from Launch Complex 40 at 3:17 a.m. local time Thursday, carrying 22 Starlink satellites into low Earth orbit. The first-stage booster, making its 19th flight, landed on the droneship A Shortfall of Gravitas in the Atlantic eight minutes after liftoff. Thursday's mission brought the operational Starlink constellation above 6,800 active satellites. Company President Gwynne Shotwell said a follow-up launch from Vandenberg Space Force Base is scheduled for Saturday.",
        "news",
    ),
    (
        "GENEVA — The World Trade Organization on Friday downgraded its forecast for global merchandise-trade growth in 2026 to 2.1 percent from an earlier projection of 3.0 percent, citing heightened tariff uncertainty and weaker demand in Europe. Director-General Ngozi Okonjo-Iweala told a briefing the downgrade underscored the need for renewed multilateral cooperation. The report singled out a deceleration in semiconductor and automotive shipments. Trade between North America and Asia nonetheless continued to expand, partially offsetting softer European activity, WTO economists said in the accompanying outlook.",
        "news",
    ),
    (
        "JAKARTA — Indonesia's parliament passed a long-debated personal data protection amendment on Wednesday, imposing fines of up to 2 percent of annual global turnover on companies that mishandle citizens' data. The bill also creates a new supervisory authority under the Ministry of Communication and Informatics. Minister Budi Arie Setiadi said enforcement would begin in January 2027 after a nine-month transition. Industry group APJII cautiously welcomed the framework but warned that small businesses would need technical guidance to comply with the breach-notification rules.",
        "news",
    ),
    (
        "MEXICO CITY — Mexican oil company Pemex reported a first-quarter net loss of 43.7 billion pesos on Tuesday, narrower than the 79.9-billion-peso loss a year earlier, as higher crude prices offset declining output. Production averaged 1.76 million barrels per day, down 2.4 percent year-over-year. Chief Executive Octavio Romero told reporters the company was on track to meet its 1.8-million-barrel target by year-end. Finance Minister Rogelio Ramirez de la O reiterated that the federal government would continue supporting Pemex with targeted capital injections.",
        "news",
    ),
    (
        "BERLIN — Germany's Federal Cartel Office on Monday opened an investigation into a leading food-delivery aggregator over concerns about restrictive clauses imposed on partner restaurants. Authority President Andreas Mundt said the probe would examine whether most-favored-nation clauses prevent restaurants from offering lower prices on their own websites. The company said it would cooperate fully and believed its practices complied with German and EU competition law. A preliminary decision is expected within nine months, the regulator said in its statement.",
        "news",
    ),
    (
        "SYDNEY — Australian researchers reported Thursday that the Great Barrier Reef is experiencing its most severe bleaching event on record, with aerial surveys showing bleaching across 73 percent of the 1,200 reefs assessed. Dr. Neal Cantin of the Australian Institute of Marine Science said sustained sea-surface temperatures more than 2 degrees Celsius above the March average were the primary driver. Environment Minister Tanya Plibersek pledged an additional 150 million Australian dollars for reef-resilience programs. Recovery will depend on whether cooler autumn temperatures arrive within three weeks.",
        "news",
    ),
    (
        "ATHENS — Greek firefighters battled a wildfire on the island of Rhodes for a third day on Sunday, with gusts of up to 80 kilometers per hour hampering containment efforts. Civil Protection Minister Vassilis Kikilias said 420 firefighters, 12 aircraft, and 4 helicopters were deployed; approximately 1,300 residents and tourists were evacuated from three villages. No fatalities have been reported. Prime Minister Kyriakos Mitsotakis declared a state of emergency for the southern part of the island and requested assistance under the EU Civil Protection Mechanism.",
        "news",
    ),
    (
        "NEW DELHI — India's Election Commission announced Friday that phase four of the general election will be held on April 29, covering 96 parliamentary constituencies across 10 states. Chief Election Commissioner Rajiv Kumar said more than 177 million voters would be eligible to cast ballots at 101,000 polling stations. Security forces from 11 states will be redeployed to ensure peaceful voting. Final results for the seven-phase nationwide vote are scheduled to be released on June 4 alongside counts from the earlier phases.",
        "news",
    ),
    (
        "STOCKHOLM — Ericsson reported a 15 percent drop in first-quarter sales on Tuesday, citing continued weakness in North American 5G investments. Net sales fell to 53.3 billion Swedish crowns, broadly matching analyst expectations, while adjusted operating margin improved to 9.5 percent thanks to cost cuts announced last year. Chief Executive Borje Ekholm said demand would stabilize in the second half as operators began planning 5G Advanced rollouts. Shares fell 2 percent in early Stockholm trading before partially recovering in afternoon sessions.",
        "news",
    ),
    # ------------------------------------------------------------------
    # recipe (16)
    # ------------------------------------------------------------------
    (
        "Classic Tomato Bruschetta. Ingredients: 4 ripe Roma tomatoes diced, 2 tablespoons extra-virgin olive oil, 6 fresh basil leaves chiffonade, 1 garlic clove minced, half a teaspoon kosher salt, a quarter teaspoon black pepper, 1 baguette sliced 1.5 centimeters thick. Steps: 1. Combine tomatoes, basil, garlic, oil, salt, and pepper in a bowl; let rest 15 minutes. 2. Heat a grill pan over medium-high heat, brush bread with oil, and toast 90 seconds per side. 3. Spoon tomato mixture onto warm toasts and serve immediately.",
        "recipe",
    ),
    (
        "Weeknight Miso Soup. Ingredients: 4 cups dashi stock, 3 tablespoons white miso paste, 150 grams soft silken tofu cubed, 2 tablespoons dried wakame, 2 scallions sliced thin. Steps: 1. Rehydrate wakame in cold water 5 minutes, then drain. 2. Bring dashi to a gentle simmer, about 85 degrees Celsius; do not boil. 3. Whisk miso with a ladle of warm dashi in a small bowl until smooth, then stir back into the pot. 4. Add tofu and wakame, warm 2 minutes, top with scallions, and serve.",
        "recipe",
    ),
    (
        "Lemon-Garlic Roast Chicken. Ingredients: 1 whole chicken about 1.6 kilograms, 1 lemon halved, 6 garlic cloves smashed, 3 tablespoons olive oil, 1 tablespoon kosher salt, 2 teaspoons black pepper, 4 thyme sprigs. Steps: 1. Preheat oven to 220 degrees Celsius. 2. Pat the chicken dry, rub with oil, salt, and pepper, and stuff cavity with lemon, garlic, and thyme. 3. Roast breast-up on a rack for 55 to 65 minutes until a thigh thermometer reads 74 degrees Celsius. 4. Rest 10 minutes before carving.",
        "recipe",
    ),
    (
        "Chickpea Curry (Chana Masala). Ingredients: 2 cans chickpeas drained, 1 large onion diced, 3 garlic cloves minced, a 2-centimeter piece of ginger grated, 1 can diced tomatoes, 2 teaspoons garam masala, 1 teaspoon cumin, half a teaspoon turmeric, 3 tablespoons vegetable oil, salt to taste. Steps: 1. Heat oil in a deep pan, saute onion until golden, about 8 minutes. 2. Add garlic, ginger, and spices; cook 1 minute until fragrant. 3. Stir in tomatoes and chickpeas; simmer uncovered 20 minutes until thickened. 4. Season and serve with rice.",
        "recipe",
    ),
    (
        "Buttermilk Pancakes. Ingredients: 250 grams all-purpose flour, 2 tablespoons sugar, 1 teaspoon baking powder, half a teaspoon baking soda, half a teaspoon salt, 480 milliliters buttermilk, 2 large eggs, 60 grams melted butter. Steps: 1. Whisk dry ingredients together. 2. In a second bowl whisk buttermilk, eggs, and butter. 3. Fold wet into dry until just combined; small lumps are fine. 4. Rest batter 10 minutes. 5. Cook quarter-cup portions on a 180-degree-Celsius griddle until bubbles pop and edges set, about 2 minutes, then flip and finish 1 minute.",
        "recipe",
    ),
    (
        "Garlic Shrimp Linguine. Ingredients: 350 grams linguine, 450 grams peeled shrimp, 4 garlic cloves sliced, a quarter teaspoon red pepper flakes, 120 milliliters dry white wine, 3 tablespoons butter, 3 tablespoons olive oil, the zest and juice of 1 lemon, 2 tablespoons chopped parsley. Steps: 1. Boil pasta in salted water until al dente, reserving a cup of cooking water. 2. Saute garlic and chili in oil 1 minute. 3. Add shrimp, cook 2 minutes per side. 4. Pour wine, reduce 1 minute, swirl in butter, toss with pasta and lemon, and serve.",
        "recipe",
    ),
    (
        "Overnight Oats. Ingredients: 80 grams rolled oats, 200 milliliters milk, 60 grams Greek yogurt, 1 tablespoon chia seeds, 2 teaspoons maple syrup, a quarter teaspoon vanilla extract, 80 grams mixed berries. Steps: 1. In a 350-milliliter jar, combine oats, milk, yogurt, chia, maple syrup, and vanilla; stir well. 2. Cover and refrigerate at least 6 hours or up to 48 hours. 3. Stir before serving to loosen; top with berries. For a thicker texture use an additional teaspoon of chia. Keeps in the refrigerator up to three days.",
        "recipe",
    ),
    (
        "Beef Stew. Ingredients: 900 grams beef chuck cut into 4-centimeter cubes, 3 tablespoons flour, 3 tablespoons oil, 1 large onion diced, 3 carrots sliced, 2 celery ribs sliced, 3 garlic cloves, 240 milliliters red wine, 720 milliliters beef stock, 2 tablespoons tomato paste, 2 bay leaves, salt and pepper. Steps: 1. Toss beef with flour and brown in oil in batches. 2. Saute aromatics 5 minutes. 3. Deglaze with wine, scraping the fond. 4. Add stock, tomato paste, and bay; simmer covered at 160 degrees Celsius for 2 hours until fork-tender.",
        "recipe",
    ),
    (
        "No-Knead Bread. Ingredients: 400 grams bread flour, 8 grams fine sea salt, 2 grams instant yeast, 320 milliliters lukewarm water. Steps: 1. Mix flour, salt, yeast, and water with a spatula until a shaggy dough forms. 2. Cover and let rise at room temperature 12 to 18 hours. 3. Turn onto a floured surface, shape into a round, and proof 90 minutes on parchment. 4. Preheat a Dutch oven to 245 degrees Celsius for 30 minutes. 5. Bake covered 30 minutes, uncover and bake 15 more minutes until deep golden.",
        "recipe",
    ),
    (
        "Thai Green Curry. Ingredients: 3 tablespoons green curry paste, 400 milliliters coconut milk, 500 grams chicken thigh sliced, 1 Thai eggplant cubed, 100 grams bamboo shoots, 1 tablespoon fish sauce, 2 teaspoons palm sugar, 6 Thai basil leaves, 2 kaffir lime leaves. Steps: 1. Fry paste in 3 tablespoons of thick coconut cream over medium heat 2 minutes until aromatic. 2. Add chicken; stir 3 minutes. 3. Pour remaining coconut milk, bring to a gentle simmer. 4. Add vegetables; cook 10 minutes. 5. Season with fish sauce, sugar, and basil; serve with jasmine rice.",
        "recipe",
    ),
    (
        "Caesar Salad. Ingredients: 1 romaine heart chopped, 60 grams parmesan shaved, 80 grams croutons. Dressing: 2 anchovy fillets, 1 garlic clove, 1 egg yolk, 1 teaspoon Dijon mustard, 1 tablespoon lemon juice, 1 teaspoon Worcestershire, 120 milliliters neutral oil, salt and pepper. Steps: 1. Mash anchovies and garlic into a paste. 2. Whisk in yolk, mustard, lemon juice, and Worcestershire. 3. Drizzle oil in slowly while whisking to emulsify. 4. Toss romaine with dressing, season, and top with parmesan and croutons just before serving.",
        "recipe",
    ),
    (
        "Chocolate Chip Cookies. Ingredients: 225 grams butter softened, 200 grams light brown sugar, 100 grams granulated sugar, 2 large eggs, 2 teaspoons vanilla, 320 grams all-purpose flour, 1 teaspoon baking soda, 1 teaspoon salt, 300 grams chocolate chips. Steps: 1. Cream butter and sugars 3 minutes until fluffy. 2. Beat in eggs and vanilla. 3. Mix in flour, soda, and salt until just combined, then fold in chips. 4. Chill dough 30 minutes. 5. Scoop 45-gram balls onto lined trays and bake at 190 degrees Celsius for 11 minutes until edges set.",
        "recipe",
    ),
    (
        "Greek Tzatziki. Ingredients: 300 grams thick Greek yogurt, half an English cucumber grated, 2 garlic cloves grated, 1 tablespoon olive oil, 1 tablespoon lemon juice, 2 teaspoons chopped dill, half a teaspoon salt. Steps: 1. Squeeze cucumber firmly in a clean towel to remove as much liquid as possible, yielding roughly 80 grams of flesh. 2. Combine all ingredients in a bowl and stir well. 3. Cover and chill at least 1 hour so the garlic mellows. 4. Taste and adjust salt and lemon before serving with warm pita or grilled meats.",
        "recipe",
    ),
    (
        "Shakshuka. Ingredients: 2 tablespoons olive oil, 1 onion diced, 1 red pepper diced, 3 garlic cloves minced, 2 teaspoons smoked paprika, 1 teaspoon cumin, 1 can (400 grams) crushed tomatoes, 4 large eggs, 60 grams feta crumbled, 2 tablespoons chopped parsley. Steps: 1. Heat oil in a 25-centimeter skillet, saute onion and pepper 8 minutes. 2. Add garlic and spices; cook 1 minute. 3. Pour tomatoes, simmer 10 minutes until thickened. 4. Make 4 wells, crack an egg into each, cover, and cook 6 minutes until whites set. 5. Top with feta and parsley.",
        "recipe",
    ),
    (
        "Banana Bread. Ingredients: 3 very ripe bananas mashed, 115 grams melted butter, 150 grams brown sugar, 2 large eggs, 1 teaspoon vanilla, 220 grams flour, 1 teaspoon baking soda, half a teaspoon salt, 80 grams chopped walnuts. Steps: 1. Preheat oven to 175 degrees Celsius and grease a 23-by-13-centimeter loaf pan. 2. Whisk bananas, butter, sugar, eggs, and vanilla. 3. Fold in flour, soda, and salt until just combined; stir in walnuts. 4. Pour into pan and bake 55 to 65 minutes until a skewer emerges clean. 5. Cool 15 minutes before slicing.",
        "recipe",
    ),
    (
        "Vietnamese Pickled Carrots and Daikon (Do Chua). Ingredients: 250 grams carrots julienned, 250 grams daikon julienned, 1 tablespoon salt, 180 milliliters rice vinegar, 180 milliliters warm water, 100 grams sugar. Steps: 1. Toss carrot and daikon with salt; let sit 15 minutes, then squeeze gently and rinse. 2. Whisk vinegar, water, and sugar until the sugar dissolves. 3. Pack vegetables into a 750-milliliter jar and pour brine to cover. 4. Refrigerate at least 1 hour before use; flavor peaks at 48 hours and keeps up to 3 weeks.",
        "recipe",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, doc_type) in enumerate(ROWS, start=1):
            row = {
                "id": f"doc-{(ID_OFFSET + i):05d}",
                "doc_type": doc_type,
                "text": text,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
