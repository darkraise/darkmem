"""One-off emitter for shared-base batch-257 — technical domain (iOS development and Swift: Swift 6 concurrency, SwiftUI, SwiftData, CloudKit, WidgetKit, StoreKit 2, Metal, Xcode tooling, SPM, Fastlane, TestFlight).

Writes 50 rows to data/v2/shared/batch_257.tmp.jsonl with ids shared-12801..12850.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_257.tmp.jsonl"
ID_OFFSET = 12800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1. decision ---
    ("Flipped the iOS target to Swift 6 language mode with strict concurrency checking on complete; every module now compiles against data-race safety and the old unchecked @preconcurrency imports were audited down to a short allowlist.", "decision", "technical", False,
     [("Swift 6", "language"), ("strict concurrency", "pattern"), ("@preconcurrency", "api"), ("data-race safety", "concept")],
     [("Swift 6", "@preconcurrency", "REPLACES")],
     "which Swift language mode did the iOS target move to and what concurrency checking level did it enable",
     "swift 6 strict concurrency data race preconcurrency complete allowlist"),
    # --- 2. architecture ---
    ("Shared mutable caches moved behind actors: the image cache, the session metadata store, and the feed prefetcher all became actor types, and any cross-actor call sites are explicitly awaited rather than lock-guarded.", "architecture", "technical", False,
     [("actor", "pattern"), ("image cache", "pattern"), ("session metadata store", "pattern"), ("feed prefetcher", "pattern")],
     [("actor", "image cache", "APPLIES_TO"), ("actor", "feed prefetcher", "APPLIES_TO")],
     "which Swift concurrency primitive now protects the shared mutable caches and how are cross-boundary calls handled",
     "actor image cache session metadata feed prefetcher await cross boundary"),
    # --- 3. milestone ---
    ("Shipped the Observable macro migration across the SwiftUI app: every view model dropped @ObservableObject and @Published in favour of @Observable, and body recomputation narrowed to the exact property reads each view performs.", "milestone", "technical", False,
     [("Observable", "api"), ("@ObservableObject", "api"), ("@Published", "api"), ("SwiftUI", "framework")],
     [("Observable", "@ObservableObject", "REPLACES"), ("Observable", "@Published", "REPLACES")],
     "which SwiftUI observation model replaced ObservableObject and what rendering behaviour did it narrow",
     "observable macro observableobject published swiftui body recompute property"),
    # --- 4. fact ---
    ("The Live Activity for the delivery feature uses ActivityKit with a Dynamic Island compact and expanded layout; push token refresh happens through an APNs push-to-start registration rather than a foreground app round-trip.", "fact", "technical", False,
     [("Live Activity", "concept"), ("ActivityKit", "framework"), ("Dynamic Island", "concept"), ("APNs", "service"), ("push-to-start", "api")],
     [("ActivityKit", "Live Activity", "APPLIES_TO")],
     "which framework drives the delivery Live Activity and how does it refresh its push token on iOS",
     "activitykit live activity dynamic island apns push to start delivery"),
    # --- 5. decision ---
    ("Picked SwiftData over Core Data for the notes feature; the @Model macro plus ModelContainer handles migration-light schemas fast enough and the old NSPersistentContainer stack was overkill for a 3-entity graph.", "decision", "technical", False,
     [("SwiftData", "framework"), ("Core Data", "framework"), ("@Model", "api"), ("ModelContainer", "api"), ("NSPersistentContainer", "api")],
     [("SwiftData", "Core Data", "PREFERS"), ("SwiftData", "NSPersistentContainer", "REPLACES")],
     "which persistence framework won the notes feature bake-off and why was Core Data dropped",
     "swiftdata core data model container nspersistentcontainer notes persistence"),
    # --- 6. architecture ---
    ("The app's long-running work is modelled as structured Tasks with child TaskGroups; cancellation propagates from the NavigationStack push so backing out of a screen cancels its in-flight network fan-out automatically.", "architecture", "technical", False,
     [("Task", "api"), ("TaskGroup", "api"), ("NavigationStack", "api"), ("cancellation", "concept")],
     [("TaskGroup", "Task", "USES")],
     "how do long-running operations tie their cancellation to SwiftUI navigation state on iOS",
     "task taskgroup navigationstack cancellation structured concurrency fan out"),
    # --- 7. problem ---
    ("Fixed a data-race crash where the feed view controller mutated a UIKit UITableView data source from a Task.detached; the fix was to hop to the MainActor via await MainActor.run before touching any UI property.", "problem", "technical", False,
     [("UITableView", "api"), ("Task.detached", "api"), ("MainActor", "api"), ("UIKit", "framework")],
     [("MainActor", "Task.detached", "REPLACES")],
     "which concurrency fix stopped the feed table-view crash caused by mutating UI off the main thread",
     "data race uitableview task detached mainactor swift concurrency hop"),
    # --- 8. reference ---
    ("The Sendable conformance guide lives at docs/ios/sendable-checklist.md: it enumerates which domain model types are marked Sendable, which are @unchecked Sendable with a justification, and which still need migration.", "reference", "technical", False,
     [("Sendable", "api"), ("@unchecked Sendable", "api"), ("sendable-checklist.md", "file")],
     [],
     "where is the Sendable conformance checklist for the iOS domain model types documented",
     "sendable checklist unchecked domain model ios documentation guide"),
    # --- 9. decision ---
    ("Dropped Combine from new code paths in favour of AsyncSequence and AsyncStream; bridging publishers into Tasks via .values is the only sanctioned pattern for the remaining legacy Combine surface.", "decision", "technical", False,
     [("Combine", "framework"), ("AsyncSequence", "api"), ("AsyncStream", "api"), ("Task", "api")],
     [("AsyncSequence", "Combine", "REPLACES")],
     "which async pattern replaced Combine for new iOS code and how is legacy Combine bridged in",
     "combine asyncsequence asyncstream task values bridge publisher legacy"),
    # --- 10. noise ---
    ("The Cupertino-themed neon sign in the mobile team's corner flickers on Fridays and everyone pretends not to notice until the batteries in the remote die.", "fact", "noise", True, [], [], None, None),
    # --- 11. architecture ---
    ("The MainActor pins all view models and view-bound observers; background data crunching runs inside nonisolated actor methods that return Sendable value types, so the boundary between UI and work is explicit.", "architecture", "technical", False,
     [("MainActor", "api"), ("nonisolated", "api"), ("Sendable", "api")],
     [("MainActor", "nonisolated", "APPLIES_TO")],
     "how does the app separate UI-bound state from background work at the Swift actor boundary",
     "mainactor nonisolated sendable view model boundary background work"),
    # --- 12. milestone ---
    ("Landed the NavigationSplitView adoption for iPad and Mac Catalyst; the sidebar-content-detail split replaced the NavigationView hack and column visibility now persists across cold launches via scene storage.", "milestone", "technical", False,
     [("NavigationSplitView", "api"), ("NavigationView", "api"), ("Mac Catalyst", "platform"), ("scene storage", "api")],
     [("NavigationSplitView", "NavigationView", "REPLACES")],
     "which iPad navigation container shipped this cycle and how does it persist column visibility",
     "navigationsplitview navigationview ipad mac catalyst scene storage sidebar"),
    # --- 13. reference ---
    ("The StoreKit 2 integration follows Apple's Meet StoreKit 2 session and stores transaction proof via Transaction.currentEntitlements; the handbook lives at docs/ios/storekit2-playbook.md.", "reference", "technical", False,
     [("StoreKit 2", "framework"), ("Transaction.currentEntitlements", "api"), ("storekit2-playbook.md", "file")],
     [],
     "which handbook describes the StoreKit 2 entitlement verification flow used in the iOS app",
     "storekit 2 transaction current entitlements playbook handbook proof"),
    # --- 14. preference ---
    ("The team prefers Tuist-generated Xcode projects over hand-edited pbxproj files; merge conflicts in the project file dropped to effectively zero after the migration away from the tracked Xcode project.", "preference", "technical", False,
     [("Tuist", "tool"), ("Xcode", "tool"), ("pbxproj", "file")],
     [("Tuist", "pbxproj", "REPLACES")],
     "which project-generation tool does the team prefer over a tracked pbxproj and what conflict pain did it eliminate",
     "tuist xcode pbxproj merge conflict generate project preference"),
    # --- 15. decision ---
    ("Moved from CocoaPods to Swift Package Manager as the primary dependency manager; the lone pod left is a binary-only analytics SDK that hasn't published an SPM manifest, and it lives in a separate Podfile.", "decision", "technical", False,
     [("CocoaPods", "tool"), ("Swift Package Manager", "tool"), ("Podfile", "file")],
     [("Swift Package Manager", "CocoaPods", "REPLACES")],
     "which iOS dependency manager replaced CocoaPods and what kind of dependency still lives in a Podfile",
     "swift package manager cocoapods podfile binary analytics sdk dependency"),
    # --- 16. architecture ---
    ("The widget bundle uses WidgetKit with TimelineProvider per-entry snapshots; reloads are budgeted through WidgetCenter.shared.reloadTimelines rather than a periodic background refresh, which kept the energy impact down.", "architecture", "technical", False,
     [("WidgetKit", "framework"), ("TimelineProvider", "api"), ("WidgetCenter", "api")],
     [("WidgetCenter", "TimelineProvider", "USES")],
     "how does the widget architecture schedule reloads while keeping its energy impact low",
     "widgetkit timeline provider widgetcenter reload timelines energy impact"),
    # --- 17. fact ---
    ("The xcodebuild invocation in CI runs with -destination 'generic/platform=iOS' and -archivePath, then feeds exportArchive with an exportOptionsPlist pinned to app-store-connect; manual Organizer uploads are banned on release branches.", "fact", "technical", False,
     [("xcodebuild", "tool"), ("exportArchive", "api"), ("exportOptionsPlist", "file"), ("Organizer", "tool")],
     [],
     "which xcodebuild invocation does CI use to produce App Store archives and what manual step is banned",
     "xcodebuild archive export options plist organizer ci release branch"),
    # --- 18. decision ---
    ("Xcode Cloud took over CI from the self-hosted Jenkins runners; signed TestFlight builds now flow from a merge to main through a workflow that runs unit tests, UI tests on simulators, and archives into App Store Connect.", "decision", "technical", False,
     [("Xcode Cloud", "service"), ("Jenkins", "tool"), ("TestFlight", "service"), ("App Store Connect", "service")],
     [("Xcode Cloud", "Jenkins", "REPLACES")],
     "which CI service replaced the Jenkins fleet for iOS and what path do signed TestFlight builds take",
     "xcode cloud jenkins testflight app store connect ci signed build"),
    # --- 19. architecture ---
    ("Sign in with Apple is the primary auth surface; the identity-token JWT is verified server-side against Apple's JWKS and the email-relay flag is propagated into the user profile so the contact address stays routable.", "architecture", "technical", False,
     [("Sign in with Apple", "concept"), ("JWT", "protocol"), ("JWKS", "api"), ("identity-token", "concept")],
     [("JWT", "JWKS", "USES")],
     "how is the Sign in with Apple identity token verified and what email-relay information is tracked on the profile",
     "sign in with apple identity token jwt jwks email relay profile"),
    # --- 20. milestone ---
    ("Cut over the cryptographic helpers to CryptoKit; the custom CommonCrypto AES-GCM wrapper that had its own nonce-management bug history got deleted once symmetric-key envelopes all went through ChaChaPoly.seal.", "milestone", "technical", False,
     [("CryptoKit", "framework"), ("CommonCrypto", "framework"), ("AES-GCM", "algorithm"), ("ChaChaPoly.seal", "api")],
     [("CryptoKit", "CommonCrypto", "REPLACES")],
     "which Apple crypto framework replaced the CommonCrypto wrapper and what primitive now seals envelopes",
     "cryptokit commoncrypto aes gcm chachapoly seal nonce management envelope"),
    # --- 21. reference ---
    ("The onboarding TipKit tips are defined in OnboardingTips.swift under features/onboarding; each Tip conforms to Tip with a display rule tied to UserDefaults so the tips respect one-shot and cooldown constraints.", "reference", "technical", False,
     [("TipKit", "framework"), ("OnboardingTips.swift", "file"), ("Tip", "api"), ("UserDefaults", "api")],
     [],
     "where are the onboarding TipKit tips declared and how do their display rules honour cooldowns",
     "tipkit onboarding tips swift userdefaults cooldown one shot display rule"),
    # --- 22. preference ---
    ("The team prefers the Preview macro over PreviewProvider for all new SwiftUI previews; the shorter trailing-closure form and its data-source helpers made the preview files drop roughly a third of their ceremony.", "preference", "technical", False,
     [("Preview", "api"), ("PreviewProvider", "api"), ("SwiftUI", "framework")],
     [("Preview", "PreviewProvider", "PREFERS")],
     "which SwiftUI preview form does the team prefer for new files and what did it trim from the previous approach",
     "preview macro previewprovider swiftui trailing closure ceremony data source"),
    # --- 23. architecture ---
    ("The app intents surface uses AppIntent types registered via AppShortcutsProvider; Shortcuts donation happens on first successful action rather than at launch, so Siri suggestions track actual usage instead of cold promises.", "architecture", "technical", False,
     [("AppIntent", "api"), ("AppShortcutsProvider", "api"), ("Shortcuts", "framework"), ("Siri", "service")],
     [("AppShortcutsProvider", "AppIntent", "USES")],
     "how does the app register App Intents and when does it donate shortcuts so Siri tracks real usage",
     "appintent appshortcutsprovider shortcuts siri donation launch register"),
    # --- 24. decision ---
    ("Chose GlobalActor-annotated namespaces over ad-hoc DispatchQueue serialisation for cross-module coordinators; @DataStoreActor and @AnalyticsActor now guard their respective mutable state and the old queue.sync fences are gone.", "decision", "technical", False,
     [("GlobalActor", "api"), ("DispatchQueue", "api"), ("@DataStoreActor", "pattern"), ("@AnalyticsActor", "pattern")],
     [("GlobalActor", "DispatchQueue", "REPLACES")],
     "which Swift concurrency construct replaced DispatchQueue fences for cross-module coordination",
     "globalactor dispatchqueue datastore analytics actor fence cross module"),
    # --- 25. fact ---
    ("UIViewRepresentable shims wrap the legacy UIKit MKMapView and PencilKit canvas into the SwiftUI hierarchy; updateUIView reconciles bindings and coordinator types hold delegate callbacks without retaining the view tree.", "fact", "technical", False,
     [("UIViewRepresentable", "api"), ("MKMapView", "api"), ("PencilKit", "framework"), ("updateUIView", "method"), ("coordinator", "pattern")],
     [("UIViewRepresentable", "MKMapView", "APPLIES_TO")],
     "which SwiftUI bridge hosts the legacy UIKit MKMapView and PencilKit canvas and how are bindings reconciled",
     "uiviewrepresentable mkmapview pencilkit coordinator updateuiview bridge delegate"),
    # --- 26. architecture ---
    ("CloudKit sync drives cross-device notes: a CKRecord per Note flows through NSPersistentCloudKitContainer, and conflict resolution picks the server-newer record via modifiedTimestamp before merging user-edit metadata.", "architecture", "technical", False,
     [("CloudKit", "framework"), ("CKRecord", "api"), ("NSPersistentCloudKitContainer", "api"), ("modifiedTimestamp", "concept")],
     [("NSPersistentCloudKitContainer", "CKRecord", "USES")],
     "how do notes sync across devices on CloudKit and how are conflicting edits resolved",
     "cloudkit ckrecord nspersistentcloudkitcontainer modified timestamp conflict sync"),
    # --- 27. problem ---
    ("A retain cycle was leaking view controllers through a closure captured by a Combine sink; swapping to a [weak self] capture in .sink fixed it and the Memory Graph debugger now shows a clean unwind on pop.", "problem", "technical", False,
     [("Combine", "framework"), (".sink", "api"), ("Memory Graph debugger", "tool"), ("[weak self]", "pattern")],
     [("[weak self]", ".sink", "APPLIES_TO")],
     "which capture change fixed the Combine-driven view controller retain cycle visible in the Memory Graph",
     "retain cycle combine sink weak self memory graph debugger pop"),
    # --- 28. milestone ---
    ("Wrapped up the Fastlane to xcodebuild migration for release; fastlane pilot still uploads the IPA to TestFlight, but fastlane match for signing retired in favour of Xcode Cloud's managed certificates.", "milestone", "technical", False,
     [("Fastlane", "tool"), ("fastlane pilot", "api"), ("fastlane match", "api"), ("Xcode Cloud", "service"), ("TestFlight", "service")],
     [("Xcode Cloud", "fastlane match", "REPLACES")],
     "which Fastlane steps survived the migration to Xcode Cloud and which one was retired",
     "fastlane pilot match testflight xcode cloud managed certificates migration"),
    # --- 29. reference ---
    ("The Metal shader authoring guide lives at docs/ios/metal-authoring.md; it documents the MTLFunction naming convention, the argument-buffer layout for scene data, and the MetalFX temporal upscaling tuning used on iPhone 15 Pro.", "reference", "technical", False,
     [("Metal", "framework"), ("MTLFunction", "api"), ("MetalFX", "framework"), ("metal-authoring.md", "file")],
     [],
     "where is the Metal shader authoring guide and what MetalFX tuning does it describe",
     "metal mtlfunction metalfx authoring guide argument buffer iphone temporal"),
    # --- 30. architecture ---
    ("Logging routes through Logger with subsystem and category per module; os_log was kept only in a tiny compatibility shim for iOS 13 builds and every new call site constructs a Logger rather than calling the legacy API.", "architecture", "technical", False,
     [("Logger", "api"), ("os_log", "api"), ("subsystem", "concept"), ("category", "concept")],
     [("Logger", "os_log", "REPLACES")],
     "which unified logging type replaced os_log call sites in new code and what stayed behind a shim",
     "logger os_log subsystem category unified logging shim ios 13"),
    # --- 31. decision ---
    ("Dropped Carthage completely; every framework dependency now either ships via Swift Package Manager or is vendored as an XCFramework inside the monorepo, which retired the Cartfile and its Rome cache tooling.", "decision", "technical", False,
     [("Carthage", "tool"), ("Swift Package Manager", "tool"), ("XCFramework", "concept"), ("Cartfile", "file"), ("Rome", "tool")],
     [("Swift Package Manager", "Carthage", "REPLACES")],
     "which dependency tool got retired in favour of SPM and XCFrameworks and what tooling went with it",
     "carthage swift package manager xcframework cartfile rome cache vendored"),
    # --- 32. architecture ---
    ("The VisionOS companion app uses RealityView with entity-component systems; a shared Swift package holds the domain model so iOS and VisionOS targets both import the same Sendable value types without rewiring.", "architecture", "technical", False,
     [("VisionOS", "platform"), ("RealityView", "api"), ("entity-component", "pattern"), ("Swift package", "concept")],
     [("RealityView", "entity-component", "USES")],
     "how does the VisionOS companion share its domain model with the iOS app on Swift",
     "visionos realityview entity component swift package sendable shared model"),
    # --- 33. fact ---
    ("AsyncStream wraps the Core Location CLLocationManager delegate into a back-pressure-aware sequence; consumers cancel by dropping the Task, and the continuation finishes on didFailWithError so downstream callers see termination.", "fact", "technical", False,
     [("AsyncStream", "api"), ("CLLocationManager", "api"), ("Core Location", "framework"), ("didFailWithError", "method")],
     [("AsyncStream", "CLLocationManager", "APPLIES_TO")],
     "how is the Core Location delegate bridged into Swift concurrency and how does error termination propagate",
     "asyncstream cllocationmanager core location back pressure didfailwitherror continuation"),
    # --- 34. preference ---
    ("Engineers prefer Instruments' Swift Concurrency template for diagnosing actor-hop stalls over sprinkling os_signpost by hand; the template surfaces suspension points and actor contention inline with the timeline view.", "preference", "technical", False,
     [("Instruments", "tool"), ("Swift Concurrency", "pattern"), ("os_signpost", "api")],
     [("Instruments", "os_signpost", "PREFERS")],
     "which Instruments template does the team prefer for actor-hop diagnosis on iOS over manual signposts",
     "instruments swift concurrency template os signpost actor hop stall"),
    # --- 35. problem ---
    ("Found a strict-concurrency warning trail rooted in a non-Sendable UIImage being passed across a Task boundary; the fix was to extract the CGImage and pass it along with a @Sendable closure for the post-processing step.", "problem", "technical", False,
     [("UIImage", "api"), ("CGImage", "api"), ("@Sendable", "api"), ("Task", "api")],
     [("@Sendable", "UIImage", "REPLACES")],
     "which Sendable-related fix silenced the strict-concurrency warnings around UIImage crossing Task boundaries",
     "uiimage cgimage sendable task strict concurrency warning closure boundary"),
    # --- 36. reference ---
    ("The App Store Connect API integration lives in tools/asc-client; the handbook at docs/ios/asc-release.md covers the key rotation cadence, the TestFlight group promotion flow, and the reject-and-resubmit workflow.", "reference", "technical", False,
     [("App Store Connect", "service"), ("asc-client", "project"), ("asc-release.md", "file"), ("TestFlight", "service")],
     [],
     "where is the App Store Connect release handbook and which workflows does it document",
     "app store connect asc release testflight reject resubmit key rotation"),
    # --- 37. milestone ---
    ("Shipped the SwiftData migration plan for the v4.2 schema change; the lightweight migration on ModelContainer handled renaming two properties and adding one relationship without a custom MigrationStage.", "milestone", "technical", False,
     [("SwiftData", "framework"), ("v4.2", "date"), ("ModelContainer", "api"), ("MigrationStage", "api")],
     [],
     "which SwiftData migration shipped in v4.2 and what kind of migration plan handled the schema change",
     "swiftdata migration v4 2 modelcontainer migrationstage lightweight schema"),
    # --- 38. decision ---
    ("Chose @State and @Binding over @StateObject for feature-local view state; the Observable macro made @StateObject redundant for value-backed models and the compile-time guarantees on identity lived better with pure structs.", "decision", "technical", False,
     [("@State", "api"), ("@Binding", "api"), ("@StateObject", "api"), ("Observable", "api")],
     [("@State", "@StateObject", "PREFERS")],
     "which SwiftUI state primitives does the team now prefer for feature-local state after adopting Observable",
     "state binding stateobject observable swiftui feature local value struct"),
    # --- 39. architecture ---
    ("The Environment chain carries a HapticsEngine and a FeatureFlags reader into every SwiftUI view that needs them; the app no longer threads these through initialisers, which simplified the root-composition site significantly.", "architecture", "technical", False,
     [("Environment", "api"), ("HapticsEngine", "project"), ("FeatureFlags", "project"), ("SwiftUI", "framework")],
     [("Environment", "HapticsEngine", "APPLIES_TO"), ("Environment", "FeatureFlags", "APPLIES_TO")],
     "which SwiftUI mechanism delivers the haptics engine and feature flags down the view tree without init threading",
     "environment haptics feature flags swiftui view tree init composition"),
    # --- 40. fact ---
    ("The macOS sibling ships with AppKit wrappers using NSViewRepresentable alongside the SwiftUI scene; the menu bar extra reuses the shared feature package but binds to Mac-specific Commands declared in the Scene body.", "fact", "technical", False,
     [("AppKit", "framework"), ("NSViewRepresentable", "api"), ("Commands", "api"), ("Scene", "api")],
     [("NSViewRepresentable", "AppKit", "USES")],
     "how does the macOS sibling reuse SwiftUI features while still hosting AppKit views and Mac-specific Commands",
     "appkit nsviewrepresentable commands scene menu bar macos sibling"),
    # --- 41. reference ---
    ("The XcodeGen fallback config at project.yml still exists for developers who haven't installed Tuist locally; docs/ios/project-generation.md explains which tool is source of truth and how to regenerate after a merge.", "reference", "technical", False,
     [("XcodeGen", "tool"), ("Tuist", "tool"), ("project.yml", "file"), ("project-generation.md", "file")],
     [("Tuist", "XcodeGen", "PREFERS")],
     "where is the project-generation handbook and which tool is the source of truth for the Xcode project",
     "xcodegen tuist project yml generation source of truth regenerate"),
    # --- 42. decision ---
    ("Picked MetalFX temporal upscaling for the particle-heavy shader path on A17 Pro devices; rendering at 2x internal resolution and upscaling to native gave a cleaner frame than native at full resolution with ambient occlusion on.", "decision", "technical", False,
     [("MetalFX", "framework"), ("A17 Pro", "platform"), ("temporal upscaling", "algorithm"), ("ambient occlusion", "concept")],
     [("MetalFX", "ambient occlusion", "APPLIES_TO")],
     "which upscaling technique did the particle-heavy shader path adopt on A17 Pro and what tradeoff did it win",
     "metalfx temporal upscaling a17 pro particle shader ambient occlusion"),
    # --- 43. noise ---
    ("The office espresso machine learned a new trick this week: it silently dumps grounds into the drawer even when the drawer is already overflowing, to the delight of exactly no one.", "fact", "noise", True, [], [], None, None),
    # --- 44. architecture ---
    ("Isolated domain models use the Swift `isolated` parameter keyword for sync boundary crossings; helper functions that want to operate on an actor's state without hopping declare `isolated actor: MyActor` and the compiler proves the invariant.", "architecture", "technical", False,
     [("isolated", "api"), ("actor", "pattern"), ("Swift", "language")],
     [("isolated", "actor", "APPLIES_TO")],
     "which Swift keyword lets helper functions operate on an actor's state without a runtime hop",
     "isolated actor swift helper sync boundary compiler invariant hop"),
    # --- 45. milestone ---
    ("The iOS 17 minimum-deployment bump landed on main after the quarterly review; the Observation framework, TipKit, and SwiftData can now be used unconditionally and the #available fences around them were deleted.", "milestone", "technical", False,
     [("iOS 17", "platform"), ("Observation", "framework"), ("TipKit", "framework"), ("SwiftData", "framework"), ("#available", "api")],
     [],
     "which deployment-target bump unblocked Observation, TipKit, and SwiftData without availability fences",
     "ios 17 deployment target observation tipkit swiftdata available fence"),
    # --- 46. preference ---
    ("Reviewers prefer explicit async throws signatures over Result return types in new API boundaries; the error-propagation path through await is cleaner than threading Result through continuations in hot paths.", "preference", "technical", False,
     [("async throws", "pattern"), ("Result", "api"), ("await", "api")],
     [("async throws", "Result", "PREFERS")],
     "which error-handling style do reviewers prefer in new Swift API boundaries over Result",
     "async throws result await error propagation api boundary swift"),
    # --- 47. fact ---
    ("The release pipeline's TestFlight external-tester group auto-promotes builds tagged release/* after a twelve-hour soak in the internal group; beta feedback attachments flow to the issue tracker via an App Store Connect webhook shim.", "fact", "technical", False,
     [("TestFlight", "service"), ("release/*", "concept"), ("App Store Connect", "service"), ("webhook", "concept")],
     [],
     "how do release tags flow to TestFlight external testers and where does beta feedback land on iOS",
     "testflight external tester release tag soak app store connect webhook"),
    # --- 48. decision ---
    ("Replaced the custom NotificationCenter broadcast bus for cross-module events with an AsyncStream-based event bus per domain; loss-on-slow-consumer is now explicit via BufferingPolicy.bufferingNewest instead of silent drops.", "decision", "technical", False,
     [("NotificationCenter", "api"), ("AsyncStream", "api"), ("BufferingPolicy.bufferingNewest", "api"), ("event bus", "pattern")],
     [("AsyncStream", "NotificationCenter", "REPLACES")],
     "which event-bus design replaced NotificationCenter broadcasts and how is slow-consumer loss now expressed",
     "notificationcenter asyncstream event bus buffering newest slow consumer"),
    # --- 49. reference ---
    ("The on-device Core Data legacy stack that SwiftData hasn't absorbed yet is documented at docs/ios/legacy-core-data.md; it explains which stores survive, the NSPersistentHistoryTransaction pruning cadence, and the planned sunset window.", "reference", "technical", False,
     [("Core Data", "framework"), ("SwiftData", "framework"), ("NSPersistentHistoryTransaction", "api"), ("legacy-core-data.md", "file")],
     [],
     "where is the legacy Core Data stack documented and what is its planned sunset window",
     "core data swiftdata nspersistenthistorytransaction pruning legacy sunset stack"),
    # --- 50. preference ---
    ("Contributors prefer keeping SwiftUI view bodies under thirty lines; when a body grows beyond that, the reviewers push for ViewBuilder helpers rather than stacks of modifiers, which keeps diff readability high.", "preference", "technical", False,
     [("SwiftUI", "framework"), ("ViewBuilder", "api"), ("modifier", "pattern")],
     [("ViewBuilder", "modifier", "PREFERS")],
     "which SwiftUI style rule do contributors prefer for long view bodies and what helper do reviewers push for",
     "swiftui view body viewbuilder modifier thirty line reviewer diff"),
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
