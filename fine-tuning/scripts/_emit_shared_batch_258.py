"""One-off emitter for shared-base batch-258 — technical domain (Android development and Kotlin: K2 compiler, coroutines, Flow, Jetpack Compose, KMP, KSP, Hilt, Room, Ktor, R8, Baseline Profiles, Play Store).

Writes 50 rows to data/v2/shared/batch_258.tmp.jsonl with ids shared-12851..12900.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_258.tmp.jsonl"
ID_OFFSET = 12850

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Flipped the module to the Kotlin 2.0 K2 compiler after the stable release landed; clean-build time on the app module dropped by about a third and the old FIR quirks we were tracking no longer reproduce.", "milestone", "technical", False,
     [("Kotlin 2.0", "technology"), ("K2 compiler", "tool"), ("FIR", "concept")],
     [("K2 compiler", "Kotlin 2.0", "APPLIES_TO")],
     "which compiler swap cut clean-build time on the app module by a third and what tech version shipped it",
     "kotlin 2 k2 compiler fir clean build time app module stable"),
    # --- 2 ---
    ("Replaced the hand-rolled RxJava chains in the sync layer with Kotlin coroutines and Flow; structured concurrency via CoroutineScope made cancellation on screen teardown actually work instead of leaking subscriptions.", "decision", "technical", False,
     [("RxJava", "library"), ("Kotlin coroutines", "technology"), ("Flow", "api"), ("CoroutineScope", "api")],
     [("Kotlin coroutines", "RxJava", "REPLACES"), ("CoroutineScope", "Flow", "APPLIES_TO")],
     "which async stack replaced RxJava in the sync layer and how did cancellation stop leaking on teardown",
     "kotlin coroutines flow rxjava structured concurrency coroutinescope cancel leak"),
    # --- 3 ---
    ("StateFlow replaced the LiveData exposure on every ViewModel in the feed module; Compose collects it with collectAsStateWithLifecycle and the nullability gymnastics from LiveData just evaporated.", "architecture", "technical", False,
     [("StateFlow", "api"), ("LiveData", "api"), ("ViewModel", "api"), ("Compose", "framework"), ("collectAsStateWithLifecycle", "method")],
     [("StateFlow", "LiveData", "REPLACES"), ("Compose", "collectAsStateWithLifecycle", "USES")],
     "which observable type replaced LiveData on feed ViewModels and how does Compose collect it safely",
     "stateflow livedata viewmodel compose collect state with lifecycle null"),
    # --- 4 ---
    ("SharedFlow with a replay of zero and BufferOverflow.DROP_OLDEST drives the one-shot navigation events bus; the old LiveData SingleLiveEvent hack dropped events on rotation which caused the checkout loop bug.", "reference", "technical", False,
     [("SharedFlow", "api"), ("BufferOverflow.DROP_OLDEST", "api"), ("SingleLiveEvent", "pattern"), ("LiveData", "api")],
     [("SharedFlow", "SingleLiveEvent", "REPLACES")],
     "which flow type replaced the SingleLiveEvent hack for one-shot navigation and which bug did it close",
     "sharedflow replay buffer overflow drop oldest single live event navigation"),
    # --- 5 ---
    ("Pinned network calls to Dispatchers.IO and DB writes stay on Dispatchers.IO too; Dispatchers.Main is reserved for UI state emission and Dispatchers.Default runs the JSON parsing pool.", "fact", "technical", False,
     [("Dispatchers.IO", "api"), ("Dispatchers.Main", "api"), ("Dispatchers.Default", "api"), ("JSON", "technology")],
     [],
     "how are the three coroutine dispatchers split across network, database, UI, and parsing work",
     "dispatchers io main default coroutine network db json parse split"),
    # --- 6 ---
    ("Suspending functions replaced the callback-per-retry pattern in the auth client; the caller just awaits refresh() and the exponential-backoff retry logic hides behind one suspend point.", "decision", "technical", False,
     [("Suspending functions", "api"), ("auth client", "project"), ("exponential-backoff", "pattern")],
     [("Suspending functions", "auth client", "APPLIES_TO")],
     "which Kotlin feature replaced the callback-per-retry pattern in the auth client",
     "suspend function auth client callback retry exponential backoff await"),
    # --- 7 ---
    ("Modeled the payment state as a sealed class hierarchy with Idle, Loading, Success, and Failure; exhaustive when branches in Compose let the compiler catch the missing PendingReview state we added in v4.", "architecture", "technical", False,
     [("sealed class", "api"), ("Compose", "framework"), ("payment state", "pattern"), ("v4", "date")],
     [("sealed class", "payment state", "APPLIES_TO")],
     "which Kotlin type system feature caught the missing PendingReview state when v4 added it",
     "sealed class when exhaustive payment state idle loading success failure"),
    # --- 8 ---
    ("Every DTO in the responses package is a data class with val properties; copy and destructuring got rid of the manual Builder pattern that used to crowd the network models.", "fact", "technical", False,
     [("data class", "api"), ("Builder", "pattern"), ("DTO", "concept")],
     [("data class", "Builder", "REPLACES")],
     "which Kotlin class flavour replaced the manual Builder pattern across the network DTOs",
     "data class val copy destructuring builder dto network response"),
    # --- 9 ---
    ("Introduced value classes to wrap UserId, OrderId, and Email so a raw String cannot sneak into an id slot; the overhead is zero at runtime because the compiler inlines them at call sites.", "decision", "technical", False,
     [("value classes", "api"), ("UserId", "concept"), ("OrderId", "concept"), ("Email", "concept")],
     [("value classes", "UserId", "APPLIES_TO")],
     "which Kotlin feature stops a raw String from being passed into a UserId slot at zero runtime cost",
     "value class inline userid orderid email raw string type safe"),
    # --- 10. noise ---
    ("The breakroom espresso machine has a sticky note taped to the portafilter that just says \"don't\" and nobody remembers who wrote it.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Migrated annotation processing from kapt to KSP across every module; incremental build after a touch on the Room DAO went from forty seconds to about eight on the CI box.", "milestone", "technical", False,
     [("kapt", "tool"), ("KSP", "tool"), ("Room", "library"), ("DAO", "pattern")],
     [("KSP", "kapt", "REPLACES")],
     "which annotation processor replaced kapt and what incremental build win did it unlock",
     "ksp kapt annotation processor room dao incremental build ci"),
    # --- 12 ---
    ("Preferred kotlin-inject over Hilt on the Compose Multiplatform module because Hilt is Android-only and the shared graph has to compile on iOS and Desktop too.", "decision", "technical", False,
     [("kotlin-inject", "library"), ("Hilt", "framework"), ("Compose Multiplatform", "framework"), ("iOS", "platform"), ("Desktop", "platform")],
     [("kotlin-inject", "Hilt", "PREFERS"), ("Compose Multiplatform", "iOS", "APPLIES_TO")],
     "which DI library beat Hilt on the multiplatform module and why could Hilt not be used there",
     "kotlin inject hilt compose multiplatform ios desktop shared graph"),
    # --- 13 ---
    ("Consolidated the Android-only modules on Hilt rather than keeping the legacy Dagger2 components; the generated SubcomponentFactory boilerplate shrunk by roughly sixty percent after the migration.", "decision", "technical", False,
     [("Hilt", "framework"), ("Dagger2", "framework"), ("SubcomponentFactory", "api")],
     [("Hilt", "Dagger2", "REPLACES")],
     "which DI framework replaced raw Dagger2 components on Android-only modules and what boilerplate shrank",
     "hilt dagger2 subcomponent factory android di boilerplate shrink"),
    # --- 14 ---
    ("Rewrote the profile screen in Jetpack Compose; the old XML plus RecyclerView plus DiffUtil combo got replaced by LazyColumn with keys, and screenshot tests became easy to set up.", "architecture", "technical", False,
     [("Jetpack Compose", "framework"), ("RecyclerView", "api"), ("DiffUtil", "api"), ("LazyColumn", "api")],
     [("Jetpack Compose", "RecyclerView", "REPLACES"), ("LazyColumn", "DiffUtil", "REPLACES")],
     "which Compose primitive replaced RecyclerView with DiffUtil on the rewritten profile screen",
     "jetpack compose lazy column recycler view diff util profile screen"),
    # --- 15 ---
    ("Pulled ViewModel, Navigation, and Lifecycle from Android Jetpack into every feature module via the BOM so version drift across feature teams stopped happening after the 2.7 release.", "fact", "technical", False,
     [("ViewModel", "api"), ("Navigation", "api"), ("Lifecycle", "api"), ("Android Jetpack", "framework"), ("BOM", "tool"), ("2.7", "date")],
     [("Android Jetpack", "BOM", "USES")],
     "which release mechanism keeps ViewModel, Navigation, and Lifecycle versions aligned across teams",
     "android jetpack bom viewmodel navigation lifecycle version drift feature"),
    # --- 16 ---
    ("WorkManager now handles the photo-upload queue with a unique ExistingWorkPolicy.KEEP job per album; the previous JobScheduler setup dropped constraints on Doze wakeups across certain OEM skins.", "decision", "technical", False,
     [("WorkManager", "api"), ("ExistingWorkPolicy.KEEP", "api"), ("JobScheduler", "api"), ("Doze", "concept")],
     [("WorkManager", "JobScheduler", "REPLACES")],
     "which Jetpack scheduler replaced JobScheduler for photo uploads and which OEM issue forced the switch",
     "workmanager job scheduler existing work policy keep doze oem photo"),
    # --- 17 ---
    ("Room owns the local cache now; the hand-written SQLiteOpenHelper plus Cursor mapping layer got deleted and the schema migrations run via AutoMigration annotations instead of manual Migration classes.", "architecture", "technical", False,
     [("Room", "library"), ("SQLiteOpenHelper", "api"), ("AutoMigration", "api"), ("Cursor", "api")],
     [("Room", "SQLiteOpenHelper", "REPLACES"), ("AutoMigration", "Room", "APPLIES_TO")],
     "which persistence library replaced SQLiteOpenHelper and how do schema migrations run now",
     "room sqliteopenhelper cursor auto migration schema local cache"),
    # --- 18 ---
    ("Paging 3 with RemoteMediator drives the feed; the old PagedList + DataSource.Factory pipeline was retired because the new Flow<PagingData> cooperates with StateFlow-based ViewModels natively.", "decision", "technical", False,
     [("Paging 3", "library"), ("RemoteMediator", "api"), ("PagedList", "api"), ("DataSource.Factory", "api"), ("StateFlow", "api")],
     [("Paging 3", "PagedList", "REPLACES")],
     "which paging library replaced PagedList and which observable type does its PagingData cooperate with",
     "paging 3 remote mediator pagedlist datasource factory feed stateflow"),
    # --- 19 ---
    ("Migrated preference storage from SharedPreferences to Proto DataStore; the typed schema kills the stringly-typed get/put pairs and a corrupted file on launch now surfaces as a typed exception rather than a silent default.", "decision", "technical", False,
     [("SharedPreferences", "api"), ("Proto DataStore", "api")],
     [("Proto DataStore", "SharedPreferences", "REPLACES")],
     "which storage API replaced SharedPreferences and how does a corrupted file surface now",
     "proto datastore shared preferences preference typed schema corrupt exception"),
    # --- 20 ---
    ("Shipping the design system as a Compose Multiplatform module so Android, iOS, Desktop, and the Wasm web target share the same buttons and typography tokens; a regression on one platform now shows up across all four.", "milestone", "technical", False,
     [("Compose Multiplatform", "framework"), ("Android", "platform"), ("iOS", "platform"), ("Desktop", "platform"), ("Wasm", "technology")],
     [("Compose Multiplatform", "Wasm", "APPLIES_TO")],
     "which framework lets the design system ship to four targets including the Wasm web build",
     "compose multiplatform android ios desktop wasm design system token"),
    # --- 21 ---
    ("Kotlin Multiplatform holds the shared business logic under a commonMain source set; expect/actual declarations route to AndroidManifest-aware implementations on Android and NSUserDefaults on iOS for the keystore shim.", "milestone", "technical", False,
     [("Kotlin Multiplatform", "framework"), ("expect/actual", "api"), ("commonMain", "pattern"), ("NSUserDefaults", "api")],
     [("expect/actual", "Kotlin Multiplatform", "APPLIES_TO")],
     "which KMP mechanism routes platform-specific keystore implementations from commonMain to Android and iOS",
     "kotlin multiplatform kmp expect actual commonmain nsuserdefaults keystore"),
    # --- 22 ---
    ("SQLDelight generates typed query APIs from .sq files in the shared module; switching from the previous hand-written JDBC wrapper cut per-call boilerplate and compile-time-checked every column reference.", "reference", "technical", False,
     [("SQLDelight", "library"), (".sq", "file"), ("JDBC", "api")],
     [("SQLDelight", "JDBC", "REPLACES")],
     "which multiplatform DB library replaced the hand-written JDBC wrapper and what compile-time guarantees did it add",
     "sqldelight sq file jdbc wrapper typed query compile check column"),
    # --- 23 ---
    ("Ktor client replaces Retrofit on the shared KMP module because Retrofit is JVM-only; the native iOS target now speaks HTTP through the Darwin engine without a separate Swift networking layer.", "reference", "technical", False,
     [("Ktor", "library"), ("Retrofit", "library"), ("KMP", "framework"), ("Darwin", "platform"), ("Swift", "language")],
     [("Ktor", "Retrofit", "REPLACES")],
     "which networking library replaced Retrofit on the KMP module and which iOS engine does it use",
     "ktor retrofit kmp darwin swift http client native ios shared"),
    # --- 24 ---
    ("Retrofit plus OkHttp still own the Android-only REST layer because the existing interceptor stack for auth, logging, and cache is mature; swapping to Ktor inside Android showed no material win.", "preference", "technical", False,
     [("Retrofit", "library"), ("OkHttp", "library"), ("Ktor", "library")],
     [("Retrofit", "OkHttp", "USES")],
     "why did the Android-only REST layer stay on Retrofit plus OkHttp instead of moving to Ktor",
     "retrofit okhttp ktor android rest interceptor auth log cache mature"),
    # --- 25 ---
    ("Dropped Moshi in favour of kotlinx.serialization across every module; one codegen path now covers both JSON and Protobuf and the Kotlin-aware nullability handling matches the rest of the stack.", "reference", "technical", False,
     [("Moshi", "library"), ("kotlinx.serialization", "library")],
     [("kotlinx.serialization", "Moshi", "REPLACES")],
     "which serialisation library replaced Moshi and what formats does its one codegen path cover",
     "kotlinx serialization moshi json protobuf codegen null kotlin"),
    # --- 26 ---
    ("Coil handles image loading across the Compose UI after Glide stopped feeling at home with suspend APIs; AsyncImage with a placeholder composable replaced the ImageView + target callbacks pattern wholesale.", "decision", "technical", False,
     [("Coil", "library"), ("Glide", "library"), ("AsyncImage", "api"), ("ImageView", "api")],
     [("Coil", "Glide", "REPLACES"), ("AsyncImage", "ImageView", "REPLACES")],
     "which image loader replaced Glide in the Compose UI and which composable replaced ImageView plus callbacks",
     "coil glide async image compose image view target callback suspend"),
    # --- 27 ---
    ("Timber stays on as the logging facade because the tree-per-build-type pattern is battle-tested; debug builds plant a DebugTree while release planting a CrashlyticsTree keeps PII out of logcat.", "preference", "technical", False,
     [("Timber", "library"), ("DebugTree", "api"), ("CrashlyticsTree", "api"), ("logcat", "tool")],
     [("Timber", "DebugTree", "USES")],
     "which logging facade stayed on because of the tree-per-build-type pattern and what does each tree do",
     "timber debug tree crashlytics tree log facade build type pii"),
    # --- 28 ---
    ("Android Studio Ladybug landed and we locked the team to the Iguana AGP minimum for six weeks; the Gemini-in-IDE completions are off by policy because of the contract review still pending.", "decision", "technical", False,
     [("Android Studio", "tool"), ("Ladybug", "date"), ("Iguana", "date"), ("AGP", "tool"), ("Gemini", "technology")],
     [],
     "which Android Studio version did the team lock to and why are the in-IDE AI completions disabled",
     "android studio ladybug iguana agp gemini ide completion policy"),
    # --- 29 ---
    ("All build scripts are Gradle Kotlin DSL now; the Groovy holdouts for the legacy modules got converted during the version-catalog migration so build logic gets the same IDE assists as app code.", "milestone", "technical", False,
     [("Gradle Kotlin DSL", "tool"), ("Groovy", "language"), ("version-catalog", "pattern")],
     [("Gradle Kotlin DSL", "Groovy", "REPLACES")],
     "which build script flavour replaced Groovy in the legacy modules and which migration made it easy",
     "gradle kotlin dsl groovy version catalog build script ide assist"),
    # --- 30 ---
    ("The release config runs R8 in full-mode shrinking with startup-optimized dex layout; the APK size dropped by about eighteen percent and a handful of keep rules got added for reflection on the JSON adapters.", "fact", "technical", False,
     [("R8", "tool"), ("dex", "technology"), ("APK", "technology")],
     [("R8", "APK", "APPLIES_TO")],
     "which shrinker runs in full-mode on release and what APK size delta did it produce",
     "r8 full mode shrink dex apk size keep rule reflection json"),
    # --- 31 ---
    ("Retired the last ProGuard rules file after moving all keep declarations to R8-aware consumer-rules.pro blocks inside each library module; the top-level proguard-rules.pro is empty save for a comment pointing at the new layout.", "architecture", "technical", False,
     [("ProGuard", "tool"), ("R8", "tool"), ("consumer-rules.pro", "file"), ("proguard-rules.pro", "file")],
     [("R8", "ProGuard", "REPLACES")],
     "how did the project retire top-level ProGuard rules while keeping R8 keep declarations organised",
     "proguard r8 consumer rules pro keep library module retire"),
    # --- 32 ---
    ("Baseline Profiles cut cold-start on Pixel 6 from roughly nine hundred milliseconds to about five hundred after a full Macrobenchmark sweep; the profile gets regenerated in CI on every release branch.", "milestone", "technical", False,
     [("Baseline Profiles", "tool"), ("Pixel 6", "platform"), ("Macrobenchmark", "tool"), ("CI", "tool")],
     [("Baseline Profiles", "Pixel 6", "APPLIES_TO")],
     "which profiling feature cut Pixel 6 cold-start roughly in half and what regenerates it each release",
     "baseline profile macro benchmark pixel 6 cold start ci release"),
    # --- 33 ---
    ("Macrobenchmark runs Startup and Scroll tests on the nightly Firebase Test Lab slice; a regression greater than ten percent on FrameMetrics fails the build so performance regressions never merge to main.", "fact", "technical", False,
     [("Macrobenchmark", "tool"), ("Firebase Test Lab", "service"), ("FrameMetrics", "api")],
     [("Macrobenchmark", "Firebase Test Lab", "DEPLOYED_ON")],
     "which benchmarking tool runs nightly on Firebase Test Lab and what metric fails the build on regression",
     "macrobenchmark firebase test lab frame metrics scroll startup nightly"),
    # --- 34 ---
    ("Default ADB workflow uses adb reverse for the dev server so the emulator and physical Pixel share one backend URL; the old build-time BASE_URL swap scheme got deleted after it desynced once too often.", "reference", "technical", False,
     [("ADB", "tool"), ("adb reverse", "method"), ("Pixel", "platform"), ("BASE_URL", "config")],
     [("adb reverse", "BASE_URL", "REPLACES")],
     "which ADB feature lets emulator and Pixel share a backend URL instead of a build-time BASE_URL swap",
     "adb reverse pixel emulator base url dev server build time swap"),
    # --- 35 ---
    ("Espresso still owns the critical path flows because the tests are fast and deterministic on CI; the flakier bits that touched SurfaceView pieces moved to UiAutomator instead of being forced into Espresso.", "preference", "technical", False,
     [("Espresso", "tool"), ("UiAutomator", "tool"), ("SurfaceView", "api")],
     [("UiAutomator", "Espresso", "REPLACES")],
     "which instrumentation framework owns the critical path and where did the flaky SurfaceView bits move",
     "espresso uiautomator surface view critical path flake ci instrumentation"),
    # --- 36 ---
    ("Robolectric runs the pure-JVM unit tests that poke Android framework classes without an emulator; the shadow approach is fast enough on CI that we prefer it over a managed virtual device for unit-layer checks.", "preference", "technical", False,
     [("Robolectric", "tool"), ("CI", "tool"), ("managed virtual device", "tool")],
     [("Robolectric", "managed virtual device", "PREFERS")],
     "which JVM test runner handles Android framework classes without an emulator and why is it preferred on CI",
     "robolectric shadow jvm android framework unit ci managed virtual device"),
    # --- 37 ---
    ("Firebase App Distribution handles internal beta drops from the CI pipeline; testers get the build in under ten minutes after a merge and the tester-group rules replaced the email-attachment-with-APK habit that QA hated.", "architecture", "technical", False,
     [("Firebase App Distribution", "service"), ("CI", "tool"), ("APK", "technology"), ("QA", "organization")],
     [("Firebase App Distribution", "CI", "DEPLOYED_ON")],
     "which service replaced emailing APKs to QA for internal beta drops and how fast does the pipeline deliver",
     "firebase app distribution ci internal beta tester group apk qa"),
    # --- 38 ---
    ("Play Store releases go out as an Android App Bundle with per-language and per-density splits; the universal APK still drops from CI as a QA artifact but it never sees the production channel.", "architecture", "technical", False,
     [("Play Store", "service"), ("Android App Bundle", "technology"), ("APK", "technology"), ("CI", "tool")],
     [("Android App Bundle", "APK", "REPLACES")],
     "which artifact ships to Play Store for releases and where does the universal APK still get built",
     "play store android app bundle aab split language density apk qa"),
    # --- 39 ---
    ("Staged rollout on the Play Console starts at one percent and doubles daily if Crashlytics velocity stays flat; the old fixed ten percent day-one rollout missed a Samsung-specific regression in release 5.2.0.", "reference", "technical", False,
     [("Play Console", "service"), ("Crashlytics", "service"), ("Samsung", "platform"), ("5.2.0", "date")],
     [("Play Console", "Crashlytics", "USES")],
     "which staged rollout curve replaced the fixed ten percent day-one plan and what regression forced the change",
     "play console staged rollout crashlytics samsung regression 5 2 0"),
    # --- 40 ---
    ("Replaced the ad-hoc Parcelable writeToParcel overrides with @Parcelize across every data class that crosses process boundaries; kotlin-parcelize plugin generates the boilerplate and one off-by-one on readString got retired with it.", "fact", "technical", False,
     [("Parcelable", "api"), ("@Parcelize", "api"), ("kotlin-parcelize", "tool"), ("writeToParcel", "method")],
     [("@Parcelize", "writeToParcel", "REPLACES")],
     "which annotation replaced hand-written writeToParcel overrides and which plugin generates the boilerplate",
     "parcelize parcelable write to parcel kotlin plugin data class boilerplate"),
    # --- 41 ---
    ("Compose navigation runs on type-safe routes generated from kotlinx.serialization @Serializable destinations; the stringly-typed NavHost builder with manual argument extraction got retired during the Navigation 2.8 bump.", "milestone", "technical", False,
     [("Compose navigation", "api"), ("kotlinx.serialization", "library"), ("@Serializable", "api"), ("NavHost", "api"), ("Navigation 2.8", "date")],
     [("@Serializable", "NavHost", "REPLACES")],
     "which typed-route mechanism replaced the stringly-typed NavHost builder and in which Navigation release",
     "compose navigation type safe route serializable navhost argument 2 8"),
    # --- 42 ---
    ("Lifecycle-aware coroutine collection uses repeatOnLifecycle(Lifecycle.State.STARTED); the older lifecycleScope.launch without repeatOnLifecycle leaked work between stop and start on configuration changes.", "problem", "technical", False,
     [("repeatOnLifecycle", "api"), ("Lifecycle.State.STARTED", "api"), ("lifecycleScope", "api")],
     [("repeatOnLifecycle", "lifecycleScope", "IMPROVES_ON")],
     "which lifecycle-aware collector replaced a bare lifecycleScope.launch and which leak did it close",
     "repeat on lifecycle state started lifecycle scope launch leak config"),
    # --- 43. noise ---
    ("The office plant on the north windowsill has outgrown two pots this year and the facilities team stopped pretending anyone else would adopt it.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Strict-mode crashes on main-thread disk reads started masking real bugs on OEM skins that preload content providers; moved the DataStore warm-up to a coroutine on Dispatchers.IO during Application.onCreate.", "problem", "technical", False,
     [("Strict-mode", "api"), ("DataStore", "api"), ("Dispatchers.IO", "api"), ("Application.onCreate", "method")],
     [("Dispatchers.IO", "Strict-mode", "FIXES")],
     "which warm-up move fixed the OEM strict-mode crashes triggered by preloaded content providers",
     "strict mode data store dispatchers io application oncreate oem warm"),
    # --- 45 ---
    ("Instrumented Hilt modules with @TestInstallIn to swap the real NetworkModule for a fake one in the androidTest source set; the old Robolectric-only fake-network approach missed a real-device bug on HTTP/2 trailers.", "decision", "technical", False,
     [("Hilt", "framework"), ("@TestInstallIn", "api"), ("NetworkModule", "project"), ("Robolectric", "tool"), ("HTTP/2", "protocol")],
     [("@TestInstallIn", "NetworkModule", "APPLIES_TO")],
     "which Hilt annotation swaps the NetworkModule in androidTest and which real-device bug forced the move",
     "hilt test install in network module robolectric android test http 2"),
    # --- 46 ---
    ("The feature-flag plumbing uses a Firebase Remote Config adapter behind a pure-Kotlin FeatureFlag interface in commonMain; the KMP layout means iOS gets the same flags without a second integration to maintain.", "architecture", "technical", False,
     [("Firebase Remote Config", "service"), ("FeatureFlag", "api"), ("commonMain", "pattern"), ("KMP", "framework"), ("iOS", "platform")],
     [("Firebase Remote Config", "FeatureFlag", "APPLIES_TO")],
     "which multiplatform layout lets iOS reuse the Android feature-flag pipeline without a second integration",
     "firebase remote config feature flag commonmain kmp ios shared"),
    # --- 47 ---
    ("Gradle configuration cache is on by default in CI; a handful of tasks that read System.getenv at configuration time got refactored to use providers, and clean-configuration time dropped by about four seconds per run.", "fact", "technical", False,
     [("Gradle configuration cache", "tool"), ("CI", "tool"), ("System.getenv", "method"), ("providers", "api")],
     [("providers", "System.getenv", "REPLACES")],
     "which Gradle feature cut configuration time in CI and what refactor did tasks reading env vars need",
     "gradle configuration cache providers system getenv ci clean configure"),
    # --- 48 ---
    ("Detekt and ktlint both run in the pre-commit hook; ktlint owns formatting while detekt catches the Kotlin-specific code smells that ktlint ignores, like long parameter lists and complex conditions.", "architecture", "technical", False,
     [("Detekt", "tool"), ("ktlint", "tool"), ("pre-commit", "tool")],
     [("Detekt", "ktlint", "APPLIES_TO")],
     "how do Detekt and ktlint split responsibilities in the pre-commit hook on the Kotlin codebase",
     "detekt ktlint pre commit format code smell parameter list condition"),
    # --- 49 ---
    ("Chose kotest over JUnit5 for the shared module tests because the DescribeSpec style reads cleaner for the multiplatform fixtures; JUnit5 stays on the Android instrumented side for now.", "decision", "technical", False,
     [("kotest", "library"), ("JUnit5", "library"), ("DescribeSpec", "api")],
     [("kotest", "JUnit5", "PREFERS")],
     "which test framework did the shared module pick over JUnit5 and which spec style drove the choice",
     "kotest junit5 describe spec shared module multiplatform fixture"),
    # --- 50 ---
    ("Turbine wraps Flow assertions in the coroutine tests; the older runBlockingTest with manual timeouts missed a subtle StateFlow duplicate-emission bug that Turbine caught via awaitItem expectations.", "problem", "technical", False,
     [("Turbine", "library"), ("Flow", "api"), ("runBlockingTest", "api"), ("StateFlow", "api"), ("awaitItem", "method")],
     [("Turbine", "runBlockingTest", "REPLACES")],
     "which Flow test library caught the StateFlow duplicate-emission bug that runBlockingTest missed",
     "turbine flow state flow run blocking test await item duplicate emit"),
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
