"""One-off emitter for shared-base batch-087 — ai_coding domain (type-driven development and type systems in code: TS strict, Python typing, Pydantic, runtime validators, Rust newtype, Haskell ADTs, Scala/Kotlin sealed/enums, branded ids, exhaustiveness, type-level tests, generics, narrowing, Result-of-T types, schema-first codegen).

Writes 50 rows to data/v2/shared/batch_087.tmp.jsonl with ids shared-04301..04350.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_087.tmp.jsonl"
ID_OFFSET = 4300

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Flipped the web app's tsconfig to strict: true and noUncheckedIndexedAccess; the array-subscript narrowing alone surfaced four real undefined-deref bugs the day it landed.", "milestone", "ai_coding", False,
     [("tsconfig", "config"), ("strict", "config"), ("noUncheckedIndexedAccess", "config")],
     [("noUncheckedIndexedAccess", "tsconfig", "CONFIGURES")],
     "which TypeScript strictness flag exposed a stash of undefined-array bugs the day we enabled it",
     "tsconfig strict no unchecked indexed access array narrow undefined"),
    # --- 2 ---
    ("Pydantic models in the ingestion service were upgraded from v1 to v2; the new core_schema validator API is faster and the model_validator decorator replaced root_validator across the package.", "decision", "ai_coding", False,
     [("Pydantic", "library"), ("v1", "config"), ("v2", "config"), ("model_validator", "method"), ("root_validator", "method")],
     [("v2", "v1", "REPLACES"), ("model_validator", "root_validator", "REPLACES")],
     "which Pydantic upgrade landed in the ingestion service and which decorator swap did it force",
     "pydantic v2 upgrade core schema model validator root validator port"),
    # --- 3 ---
    ("Replaced Joi with Zod across the Express handlers; one schema now drives both runtime validation and the static request type via z.infer.", "decision", "ai_coding", False,
     [("Joi", "library"), ("Zod", "library"), ("Express", "framework"), ("z.infer", "method")],
     [("Zod", "Joi", "REPLACES")],
     "which validator did the Express handlers swap to so that runtime and static types share a single source",
     "zod replace joi express schema z infer runtime static type share"),
    # --- 4 ---
    ("Switched the bundle-sensitive checkout SPA from Zod to Valibot; the tree-shaken validators trimmed forty kilobytes off the gzipped checkout chunk.", "decision", "ai_coding", False,
     [("Zod", "library"), ("Valibot", "library"), ("checkout SPA", "project")],
     [("Valibot", "Zod", "REPLACES")],
     "which validator swap shaved 40 kB off the checkout SPA's gzipped bundle",
     "valibot replace zod tree shake bundle checkout spa kb gzipped"),
    # --- 5 ---
    ("pyright is now the editor type-checker and CI gate; mypy stayed in nightly for a week of parity-diffing before we cut it from the pre-commit hook.", "decision", "ai_coding", False,
     [("pyright", "tool"), ("mypy", "tool"), ("pre-commit", "tool")],
     [("pyright", "mypy", "IMPROVES_ON")],
     "which Python type-checker replaced mypy in the pre-commit hook and how did we de-risk the swap",
     "pyright replace mypy editor latency pre commit parity diff cut"),
    # --- 6 ---
    ("Tried pyrefly on the analytics service for a week; the speed was promising but third-party stubs lagged so we parked the migration until coverage catches up.", "problem", "ai_coding", False,
     [("pyrefly", "tool"), ("analytics service", "service")],
     [],
     "why did the pyrefly trial on the analytics service get parked despite the speed wins",
     "pyrefly trial analytics third party stub coverage park migration"),
    # --- 7 ---
    ("UserId, OrderId, and TenantId are branded types in TypeScript via a unique-symbol tag; passing a raw string where an OrderId is expected now fails at compile time.", "architecture", "ai_coding", False,
     [("UserId", "pattern"), ("OrderId", "pattern"), ("TenantId", "pattern"), ("TypeScript", "language"), ("branded types", "pattern")],
     [],
     "which TypeScript pattern stops a raw string from masquerading as an OrderId across function boundaries",
     "branded type unique symbol user id order id tenant id compile fail"),
    # --- 8 ---
    ("Rust newtype wrappers replaced the bare u64 ids on the billing crate; AccountId(u64) and InvoiceId(u64) can no longer be swapped at a call site by accident.", "architecture", "ai_coding", False,
     [("Rust", "language"), ("newtype", "pattern"), ("AccountId", "pattern"), ("InvoiceId", "pattern"), ("billing", "service")],
     [],
     "which Rust pattern stopped accidental swaps between AccountId and InvoiceId in the billing crate",
     "rust newtype wrapper account id invoice id u64 swap call site"),
    # --- 9 ---
    ("The discriminated unions on the order events use a literal kind field; the reducer's switch ends in an exhaustiveness check that assigns to a never-typed local.", "architecture", "ai_coding", False,
     [("discriminated unions", "pattern"), ("kind", "pattern"), ("never", "pattern"), ("reducer", "pattern")],
     [],
     "which TypeScript idiom guarantees the order-event reducer breaks the build when a new event variant lands",
     "discriminated union kind tag exhaustiveness never reducer switch"),
    # --- 10. noise ---
    ("The ficus by the printer rotated itself to face the south window again, which is funny because nobody moved it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Kotlin sealed classes now model the payment outcome; the when-expression on Outcome enforces exhaustiveness and the compiler complains the moment we add a Refunded case.", "architecture", "ai_coding", False,
     [("Kotlin", "language"), ("sealed classes", "pattern"), ("when", "pattern"), ("Outcome", "pattern")],
     [],
     "which Kotlin construct guarantees the payment-outcome handler stays exhaustive when we add new cases",
     "kotlin sealed class when exhaustive payment outcome refunded compiler"),
    # --- 12 ---
    ("Scala 3 enums replaced the old sealed-trait plus case-object boilerplate for the workflow state; the derives Eq, Show line removed a hundred lines of typeclass plumbing.", "decision", "ai_coding", False,
     [("Scala 3", "language"), ("enums", "pattern"), ("sealed-trait", "pattern"), ("derives", "pattern")],
     [("enums", "sealed-trait", "REPLACES")],
     "which Scala 3 feature collapsed the workflow-state sealed-trait boilerplate and what did derives buy us",
     "scala 3 enum derive eq show sealed trait case object replace"),
    # --- 13 ---
    ("Haskell ADT for the parser tree uses a recursive Term constructor with strict fields; -Wall plus -Wincomplete-patterns catches missing match arms in CI.", "architecture", "ai_coding", False,
     [("Haskell", "language"), ("ADT", "pattern"), ("Term", "pattern"), ("-Wincomplete-patterns", "config")],
     [],
     "which Haskell warnings did we enable so the parser-tree match arms stay exhaustive in CI",
     "haskell adt term recursive incomplete pattern wall warning ci"),
    # --- 14 ---
    ("OpenAPI types are generated by openapi-typescript on every spec change; the generated d.ts is committed so codegen drift shows up in PR review.", "preference", "ai_coding", False,
     [("OpenAPI", "protocol"), ("openapi-typescript", "tool"), ("d.ts", "file")],
     [("openapi-typescript", "OpenAPI", "USES")],
     "how does the frontend keep its request and response types in sync with the OpenAPI spec",
     "openapi typescript codegen d ts commit drift pr review spec change"),
    # --- 15 ---
    ("GraphQL Codegen produces typed hooks via the client-preset; useOrderQuery now returns a fully typed data field and the old any-typed responses were deleted.", "milestone", "ai_coding", False,
     [("GraphQL Codegen", "tool"), ("client-preset", "config"), ("useOrderQuery", "method")],
     [],
     "which GraphQL tooling change gave us typed hooks and let us delete the any-typed query responses",
     "graphql codegen client preset typed hook order query any delete"),
    # --- 16 ---
    ("Prisma schema drives the database types and the TypeScript client; the generated PrismaClient narrows where-clauses by table so a typo on column name fails at build.", "fact", "ai_coding", False,
     [("PrismaClient", "library"), ("Prisma", "tool"), ("TypeScript", "language")],
     [("Prisma", "PrismaClient", "PRODUCES")],
     "how does Prisma keep TypeScript narrowed enough to fail the build on a misspelled column name",
     "prisma schema generate client typescript where narrow column typo"),
    # --- 17 ---
    ("Generic Result<T, E> on the order service replaced thrown exceptions for expected failure paths; the type forces every caller to handle the Err arm explicitly.", "architecture", "ai_coding", False,
     [("Result<T, E>", "pattern"), ("order service", "service"), ("Err", "pattern")],
     [("Result<T, E>", "Err", "HAS_PART")],
     "which generic type expresses the order service's expected failures so callers cannot ignore them",
     "result generic err arm typed failure replace exception order service"),
    # --- 18 ---
    ("Type-level tests live next to the runtime tests using tsd; the dtslint files assert that infer'd schemas resolve to the exact branded shape.", "preference", "ai_coding", False,
     [("tsd", "tool"), ("dtslint", "file"), ("infer", "method")],
     [],
     "which tool runs the type-level tests that assert inferred schema shapes match our branded types",
     "tsd type level test dtslint infer branded shape assert next to"),
    # --- 19 ---
    ("Adopted expect-type for the SDK package; expectTypeOf<Foo>().toEqualTypeOf<Bar>() reads better than dtslint comments and the failure messages point at the diff line.", "preference", "ai_coding", False,
     [("expect-type", "library"), ("expectTypeOf", "method"), ("dtslint", "tool")],
     [("expect-type", "dtslint", "PREFERS")],
     "which type-assertion library replaced dtslint comments in the SDK package and why",
     "expect type to equal type of dtslint comment readable diff sdk"),
    # --- 20 ---
    ("Higher-kinded shape via fp-ts's HKT trick let the repository combinator stay polymorphic across Task and Either; the team accepted the encoding overhead for the reuse.", "decision", "ai_coding", False,
     [("fp-ts", "library"), ("HKT", "concept"), ("Task", "pattern"), ("Either", "pattern")],
     [("fp-ts", "HKT", "USES")],
     "which TypeScript encoding gave the repository combinator higher-kinded polymorphism across Task and Either",
     "fp ts hkt encode higher kinded repository combinator task either"),
    # --- 21 ---
    ("Pyright's narrowing on isinstance plus a Literal['kind'] tag drives the dispatcher in the rule engine; the engine no longer needs cast() calls in the hot path.", "fact", "ai_coding", False,
     [("Pyright", "tool"), ("isinstance", "method"), ("Literal", "pattern"), ("rule engine", "service")],
     [],
     "which combination of Python typing features killed the cast() noise in the rule engine's dispatcher",
     "pyright narrow isinstance literal kind dispatcher cast remove"),
    # --- 22 ---
    ("Adopted typing.assert_never at the bottom of every match-statement on Event subtypes; mypy and pyright both flag the missing arm at the call site when a new Event lands.", "architecture", "ai_coding", False,
     [("typing.assert_never", "method"), ("match-statement", "pattern"), ("Event", "pattern"), ("mypy", "tool"), ("pyright", "tool")],
     [],
     "which Python typing helper enforces match-statement exhaustiveness on Event subtypes across both checkers",
     "assert never match statement event subtype mypy pyright exhaustive"),
    # --- 23 ---
    ("Replaced the home-grown opaque-id helper in TypeScript with ts-brand; the new lib supplies make and brand helpers and the call sites lost a stash of as-cast lines.", "decision", "ai_coding", False,
     [("ts-brand", "library"), ("opaque-id", "pattern"), ("TypeScript", "language"), ("as-cast", "pattern")],
     [("ts-brand", "opaque-id", "REPLACES")],
     "which library replaced our hand-rolled opaque-id helper and what did the call sites lose",
     "ts brand opaque id make brand helper as cast remove call site"),
    # --- 24 ---
    ("io-ts is on the way out; the auth service migrated its codecs to Zod for editor-tooling parity, and the remaining io-ts decoders are tagged with a deprecation comment.", "milestone", "ai_coding", False,
     [("io-ts", "library"), ("Zod", "library"), ("auth service", "service")],
     [("Zod", "io-ts", "REPLACES")],
     "which validator migration is in flight on the auth service and what drove the choice",
     "io ts zod migrate auth service editor tooling parity decoder"),
    # --- 25 ---
    ("The conditional types on the SDK's Endpoint<TPath, TMethod> derive the request and response types from the literal route; the IDE now autocompletes paths from the spec.", "fact", "ai_coding", False,
     [("conditional types", "pattern"), ("Endpoint", "pattern"), ("TPath", "pattern"), ("TMethod", "pattern")],
     [],
     "which TypeScript feature drives the SDK's Endpoint<TPath, TMethod> derivation of request and response types",
     "conditional type endpoint t path t method literal route ide auto"),
    # --- 26 ---
    ("The TypeScript template-literal types on the routing builder concatenate base and segment at the type level; mistyped path strings light up red in the editor before the test even runs.", "fact", "ai_coding", False,
     [("template-literal types", "pattern"), ("routing builder", "service"), ("TypeScript", "language")],
     [],
     "which TypeScript feature catches mistyped route segments in the editor before tests run",
     "template literal type route builder concat segment editor red"),
    # --- 27 ---
    ("The variance annotations landed on the cache combinator; the in T and out T markers caught a covariance bug in the Reader subtype that the unit tests had missed.", "problem", "ai_coding", False,
     [("variance annotations", "pattern"), ("in T", "pattern"), ("out T", "pattern"), ("Reader", "pattern")],
     [],
     "which TypeScript variance markers caught a Reader covariance bug the unit tests had missed",
     "variance annotation in out reader covariance cache combinator bug"),
    # --- 28 ---
    ("The type predicates on isOrder(value) drive narrowing inside the inbox handler; the handler body now sees an Order without a single as-cast on the path.", "fact", "ai_coding", False,
     [("type predicates", "pattern"), ("isOrder", "method"), ("inbox handler", "service"), ("Order", "pattern")],
     [],
     "which TypeScript narrowing primitive replaced the as-casts in the inbox handler body",
     "type predicate is order narrow inbox handler as cast remove"),
    # --- 29 ---
    ("Kotlin value classes wrap the cents-as-Long money primitive; @JvmInline keeps the runtime cost flat while the type stops cents-versus-dollars mix-ups in arithmetic.", "architecture", "ai_coding", False,
     [("Kotlin", "language"), ("value classes", "pattern"), ("@JvmInline", "config"), ("Long", "pattern")],
     [],
     "which Kotlin feature gives the cents-as-Long money primitive a real type without runtime overhead",
     "kotlin value class jvm inline money cents long arithmetic mix up"),
    # --- 30 ---
    ("Rust phantom types on Connection<Open> and Connection<Closed> encode the protocol state in the type; calling send on a Closed connection no longer compiles.", "architecture", "ai_coding", False,
     [("Rust", "language"), ("phantom types", "pattern"), ("Connection<Open>", "pattern"), ("Connection<Closed>", "pattern")],
     [],
     "which idiom did the team adopt so calls like send on a finished socket are rejected at build time",
     "typestate marker generic parameter session open shut transition compile"),
    # --- 31 ---
    ("Haskell GADT lets the query AST carry its result type; runQuery :: Query a -> IO a now has nothing to fall back to, so the reader can't accidentally Stringify a count.", "architecture", "ai_coding", False,
     [("Haskell", "language"), ("GADT", "pattern"), ("runQuery", "method"), ("Query", "pattern")],
     [],
     "which Haskell extension lets the query AST carry its result type into runQuery's signature",
     "haskell gadt query ast result type run query stringify count"),
    # --- 32 ---
    ("Switched ts-pattern in for nested if/else on the Notification union; the .with arms cover every variant and the .exhaustive() call fails the build on a missing case.", "decision", "ai_coding", False,
     [("ts-pattern", "library"), ("Notification", "pattern"), (".exhaustive()", "method")],
     [],
     "which library replaced nested if/else on the Notification union and how does it enforce exhaustiveness",
     "ts pattern with exhaustive notification union variant if else swap"),
    # --- 33 ---
    ("Pydantic v2 discriminated union on the Event field uses Field(discriminator='kind'); validation is faster and the OpenAPI export now lists every concrete subtype.", "fact", "ai_coding", False,
     [("Pydantic v2", "library"), ("discriminated union", "pattern"), ("Field", "method"), ("OpenAPI", "protocol")],
     [],
     "which Pydantic v2 feature speeds up Event validation and surfaces the variants in OpenAPI",
     "pydantic v2 discriminator field event union openapi subtype list"),
    # --- 34 ---
    ("typed-dict TypedDict variants with NotRequired keys replaced the optional kwargs soup on the search client; the IDE finally suggests the right keys per call site.", "preference", "ai_coding", False,
     [("TypedDict", "pattern"), ("NotRequired", "method"), ("search client", "service")],
     [],
     "which Python typing construct replaced the optional kwargs soup on the search client API",
     "typed dict not required optional kwargs search client ide suggest"),
    # --- 35 ---
    ("ParamSpec on the retry decorator preserves wrapped function signatures; the IDE now shows the original argument names instead of (*args, **kwargs) on the call site.", "fact", "ai_coding", False,
     [("ParamSpec", "method"), ("retry decorator", "pattern"), ("*args", "pattern")],
     [],
     "which typing primitive lets the retry decorator pass through the wrapped function's exact signature",
     "param spec retry decorator wrap signature args kwargs ide name"),
    # --- 36 ---
    ("TypeScript's satisfies operator on the route table catches typos without widening the literal types; the build broke twice during rollout, both times legitimately.", "milestone", "ai_coding", False,
     [("satisfies", "method"), ("route table", "pattern"), ("TypeScript", "language")],
     [],
     "which TypeScript operator catches typos in the route table without losing the literal narrowing",
     "satisfies operator route table literal narrow typo widen rollout"),
    # --- 37 ---
    ("Refinement types on the Email and PhoneNumber primitives go through a parse-don't-validate factory; downstream code receives the branded value or never starts.", "architecture", "ai_coding", False,
     [("Email", "pattern"), ("PhoneNumber", "pattern"), ("parse-don't-validate", "concept")],
     [],
     "which discipline keeps Email and PhoneNumber refinement types honest from boundary to call site",
     "parse don't validate refinement email phone branded factory boundary"),
    # --- 38 ---
    ("Pinned mypy --strict on new packages and grandfathered the legacy ones at --strict-optional only; the per-package overrides live in pyproject.toml under tool.mypy.overrides.", "preference", "ai_coding", False,
     [("mypy", "tool"), ("--strict-optional", "config"), ("--strict", "config"), ("pyproject.toml", "file")],
     [],
     "how is mypy strictness staged across new and legacy packages and where does the config live",
     "mypy strict optional override pyproject toml package legacy stage"),
    # --- 39 ---
    ("Effect-TS landed on the new orchestration module; the Effect<R, E, A> type makes dependencies, errors, and success values all visible in the function signature.", "decision", "ai_coding", False,
     [("Effect-TS", "library"), ("Effect<R, E, A>", "pattern"), ("orchestration", "service")],
     [],
     "which library shipped on the orchestration module and what does its three-parameter Effect type encode",
     "effect ts r e a dependency error success orchestration signature"),
    # --- 40 ---
    ("The generic constraints on Repository<T extends { id: Brand<string, 'Id'> }> stop the team from instantiating the repo with an unbranded id type by accident.", "fact", "ai_coding", False,
     [("Repository", "pattern"), ("Brand", "pattern"), ("generic constraints", "pattern")],
     [],
     "which TypeScript constraint on Repository<T> blocks instantiation with an unbranded id type",
     "generic constraint repository brand id extends instantiate block"),
    # --- 41 ---
    ("Pydantic v2's Annotated[int, Field(gt=0)] replaced the post-validator gt-zero checks; the constraint surfaces in the JSON schema now too.", "decision", "ai_coding", False,
     [("Pydantic v2", "library"), ("Annotated", "pattern"), ("Field", "method"), ("JSON schema", "protocol")],
     [("Annotated", "Field", "USES")],
     "which Pydantic v2 form replaced post-validator gt-zero checks and what extra payoff did it bring",
     "pydantic annotated field gt zero json schema post validator export"),
    # --- 42 ---
    ("Replaced runtypes with Zod on the legacy gateway; matching errors and inferred TS types in one place beat the dual-source we had before.", "decision", "ai_coding", False,
     [("runtypes", "library"), ("Zod", "library"), ("gateway", "service")],
     [("Zod", "runtypes", "REPLACES")],
     "which validator replaced runtypes on the legacy gateway and what was the win",
     "zod runtypes gateway replace error inferred ts dual source merge"),
    # --- 43 ---
    ("Type-driven design referenced Wlaschin's Domain Modeling Made Functional for the booking service; the make-illegal-states-unrepresentable rule shaped half the ADTs.", "reference", "ai_coding", False,
     [("Domain Modeling Made Functional", "publication"), ("Wlaschin", "person"), ("booking service", "service"), ("ADTs", "pattern")],
     [("booking service", "Domain Modeling Made Functional", "BUILDS_ON")],
     "which book guided the booking service's ADT design and which rule shaped most of the types",
     "domain modeling made functional wlaschin illegal state booking adt"),
    # --- 44 ---
    ("Cited the Curry-Howard correspondence in the design doc to justify treating the workflow's typed pipeline as a proof of state-transition validity.", "reference", "ai_coding", False,
     [("Curry-Howard correspondence", "theory"), ("workflow", "pattern")],
     [],
     "which type-theory result did the design doc cite to defend the typed-pipeline-as-proof framing",
     "curry howard correspondence proof type workflow pipeline state cite"),
    # --- 45 ---
    ("Quicktype generates Kotlin data classes from the partner JSON contracts; the generated files live in build/generated and are excluded from the formatter.", "preference", "ai_coding", False,
     [("Quicktype", "tool"), ("Kotlin", "language"), ("data classes", "pattern"), ("build/generated", "file")],
     [("Quicktype", "Kotlin", "PRODUCES")],
     "which tool produces Kotlin data classes from the partner JSON contracts and where do they land",
     "quicktype kotlin data class json contract build generated formatter"),
    # --- 46 ---
    ("Replaced JSON Schema hand-writing with TypeBox; @sinclair/typebox emits both runtime validators and TS types from a single Type.Object declaration.", "decision", "ai_coding", False,
     [("JSON Schema", "protocol"), ("TypeBox", "library"), ("Type.Object", "method")],
     [("TypeBox", "JSON Schema", "REPLACES")],
     "which library replaced hand-written JSON Schema and what does its Type.Object declaration produce",
     "typebox json schema type object runtime validator ts type single"),
    # --- 47 ---
    ("The module augmentation on Express's Request adds a typed user field; the global declare-module file lives in src/types and the eslint rule pins one augmentation per file.", "architecture", "ai_coding", False,
     [("module augmentation", "pattern"), ("Express", "framework"), ("Request", "pattern"), ("src/types", "file")],
     [],
     "how does the codebase add a typed user field to Express's Request without polluting unrelated modules",
     "module augmentation express request user typed src types eslint"),
    # --- 48 ---
    ("Higher-kinded helpers in Scala 3 use the type lambda [X] =>> F[X] form; the cleaner syntax got the team to stop reaching for the kind-projector plugin.", "decision", "ai_coding", False,
     [("Scala 3", "language"), ("type lambda", "pattern"), ("kind-projector", "library")],
     [("type lambda", "kind-projector", "REPLACES")],
     "which Scala 3 syntax retired the kind-projector plugin for higher-kinded helpers",
     "scala 3 type lambda kind projector plugin higher kinded retire"),
    # --- 49. noise ---
    ("Someone hung a hand-drawn portrait of the office cat above the snack shelf and nobody admits to it.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Compile-time string parsing in Rust on the units crate uses const generics to attach a unit to f64 at the type level; mixing meters and seconds in arithmetic just doesn't compile.", "fact", "ai_coding", False,
     [("const generics", "pattern"), ("units crate", "project"), ("f64", "pattern"), ("Rust", "language")],
     [],
     "which Rust feature lets the units crate refuse to compile arithmetic between meters and seconds",
     "const generics units crate f64 type level meter second compile fail"),
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
