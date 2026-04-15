"""One-off emitter for shared-base batch-102 — ai_coding domain (mobile coding patterns slice: iOS/Android/cross-platform app code).

Writes 50 rows to data/v2/shared/batch_102.tmp.jsonl with ids shared-05051..05100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_102.tmp.jsonl"
ID_OFFSET = 5050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("New screens in the iOS app ship in SwiftUI; UIKit stays only for the legacy camera module that still leans on AVCaptureSession delegates.", "decision", "ai_coding", False,
     [("SwiftUI", "framework"), ("UIKit", "framework"), ("AVCaptureSession", "api"), ("iOS", "platform")],
     [("SwiftUI", "UIKit", "REPLACES")],
     "which UI framework do new iOS screens use and why does UIKit still exist in one module",
     "swiftui replace uikit ios new screen legacy camera avcapturesession"),
    # --- 2 ---
    ("Combine publishers drive the account view model; upstream REST calls expose AnyPublisher<Account, APIError> instead of completion handlers with optional errors.", "architecture", "ai_coding", False,
     [("Combine", "framework"), ("AnyPublisher", "api"), ("APIError", "error")],
     [("Combine", "AnyPublisher", "USES")],
     "how does the account view model consume network calls in the reactive iOS stack",
     "combine publisher anypublisher rest view model swift ios reactive"),
    # --- 3 ---
    ("Objective-C interop lives behind a thin bridging header; the Swift side never imports raw Foundation collection classes, it wraps them in Swift types at the boundary.", "architecture", "ai_coding", False,
     [("Objective-C", "language"), ("Swift", "language"), ("bridging header", "pattern"), ("Foundation", "framework")],
     [],
     "how does the iOS codebase keep Objective-C interop from leaking into Swift call sites",
     "objective c bridging header swift foundation wrap boundary interop"),
    # --- 4 ---
    ("Migrated the shared analytics module to Kotlin Multiplatform; the iOS target consumes it as an XCFramework produced by the Gradle build.", "milestone", "ai_coding", False,
     [("Kotlin Multiplatform", "framework"), ("XCFramework", "pattern"), ("Gradle", "tool"), ("iOS", "platform")],
     [("Kotlin Multiplatform", "XCFramework", "PRODUCES")],
     "how does the cross-platform analytics module reach iOS consumers after the KMP migration",
     "kotlin multiplatform xcframework gradle analytics ios consume share"),
    # --- 5 ---
    ("Dropped the REST-only sharing layer between iOS and Android in favour of KMP shared business logic; duplicate pagination bugs dried up within a release.", "decision", "ai_coding", False,
     [("KMP", "framework"), ("REST", "protocol"), ("Android", "platform"), ("iOS", "platform")],
     [("KMP", "REST", "REPLACES")],
     "which cross-platform approach replaced duplicate REST clients between iOS and Android",
     "kmp replace rest sharing business logic android ios pagination"),
    # --- 6 ---
    ("Jetpack Compose replaced every XML layout in the onboarding flow; the ViewBinding scaffolding went away and the designer handoff now goes through Compose previews.", "decision", "ai_coding", False,
     [("Jetpack Compose", "framework"), ("XML", "pattern"), ("ViewBinding", "library"), ("onboarding", "project")],
     [("Jetpack Compose", "XML", "REPLACES")],
     "which Android UI toolkit replaced XML layouts in the onboarding flow",
     "jetpack compose replace xml layout android viewbinding preview"),
    # --- 7 ---
    ("KSP is the only annotation processor we accept in new modules; KAPT is pinned to the legacy DI module until its last Dagger 2 generator gets ported.", "preference", "ai_coding", False,
     [("KSP", "tool"), ("KAPT", "tool"), ("Dagger 2", "library")],
     [("KSP", "KAPT", "REPLACES")],
     "which Kotlin annotation-processing tool do new modules use and what keeps KAPT around",
     "ksp replace kapt kotlin annotation processor dagger legacy module"),
    # --- 8 ---
    ("Flutter widget tests replaced the old integration_test smoke pack for the merchant app; the WidgetTester pumpAndSettle loop caught a scroll-jank regression the smoke pack missed.", "milestone", "ai_coding", False,
     [("Flutter", "framework"), ("WidgetTester", "api"), ("integration_test", "library"), ("merchant app", "project")],
     [("WidgetTester", "integration_test", "IMPROVES_ON")],
     "which Flutter test harness caught the scroll-jank regression the old smoke pack missed",
     "flutter widget tester pump settle integration test regression scroll"),
    # --- 9 ---
    ("The Flutter engine upgrade to 3.22 broke our custom PlatformView on Android; pinned the engine until the hybrid composition path stabilised one point release later.", "problem", "ai_coding", False,
     [("Flutter", "framework"), ("PlatformView", "api"), ("Android", "platform")],
     [],
     "which Flutter engine upgrade broke the custom PlatformView and how was the bleed stopped",
     "flutter engine platformview android hybrid composition pin release"),
    # --- 10 ---
    ("Picked React Native for the partner SDK because Expo's managed workflow could not ship the custom BLE native module we needed.", "decision", "ai_coding", False,
     [("React Native", "framework"), ("Expo", "framework"), ("BLE", "protocol")],
     [("React Native", "Expo", "PREFERS")],
     "why did the partner SDK pick React Native over Expo for its mobile build",
     "react native expo managed workflow ble native module partner sdk"),
    # --- 11. noise ---
    ("The whiteboard marker on the mobile pod's desk dried out three days before the on-site sprint kickoff.", "fact", "noise", True, [], [], None, None),
    # --- 12 ---
    ("Capacitor replaced the aging Cordova shell on the field-service app; the plugin API is friendlier and the iOS build stopped choking on the legacy WKWebView shim.", "decision", "ai_coding", False,
     [("Capacitor", "framework"), ("Cordova", "framework"), ("WKWebView", "api"), ("field-service app", "project")],
     [("Capacitor", "Cordova", "REPLACES")],
     "which hybrid shell replaced Cordova on the field-service app and what was the win",
     "capacitor replace cordova hybrid wkwebview plugin ios build field"),
    # --- 13 ---
    ("iOS lifecycle handling moved from AppDelegate callbacks to SceneDelegate plus SwiftUI ScenePhase; multi-window on iPad finally behaves when the user drags a second scene.", "architecture", "ai_coding", False,
     [("AppDelegate", "api"), ("SceneDelegate", "api"), ("ScenePhase", "api"), ("SwiftUI", "framework")],
     [("SceneDelegate", "AppDelegate", "REPLACES")],
     "how does the iOS app now handle lifecycle on iPad multi-window after the SceneDelegate move",
     "ios scene delegate app delegate scenephase swiftui multi window ipad"),
    # --- 14 ---
    ("Android lifecycle bugs dropped after moving all background starts behind Lifecycle.State.STARTED checks via repeatOnLifecycle; the old onStart/onStop guards leaked coroutines on config changes.", "problem", "ai_coding", False,
     [("repeatOnLifecycle", "api"), ("Lifecycle.State.STARTED", "api"), ("onStart", "api"), ("onStop", "api")],
     [("repeatOnLifecycle", "onStart", "REPLACES")],
     "which Android lifecycle helper replaced manual onStart/onStop coroutine guards",
     "android repeat on lifecycle started coroutine leak config change"),
    # --- 15 ---
    ("Deep linking on iOS uses Universal Links backed by an apple-app-site-association file at the apex domain; custom URL schemes are reserved for internal QA builds only.", "architecture", "ai_coding", False,
     [("Universal Links", "pattern"), ("apple-app-site-association", "file"), ("iOS", "platform")],
     [],
     "which iOS deep-link mechanism is the default and what stays on custom URL schemes",
     "universal link apple app site association ios deep link url scheme"),
    # --- 16 ---
    ("Android App Links verification relies on an assetlinks.json published at /.well-known; a botched Play Console signing rotation broke verification for a week until we re-uploaded the file.", "problem", "ai_coding", False,
     [("App Links", "pattern"), ("assetlinks.json", "file"), ("Play Console", "service"), ("Android", "platform")],
     [],
     "which Android deep-link verification artefact broke after a signing rotation incident",
     "android app links assetlinks well known play console signing rotation"),
    # --- 17 ---
    ("The APNs payload stays under 4 KB and always carries a mutable-content flag so the Notification Service Extension can decrypt the body in-place before display.", "architecture", "ai_coding", False,
     [("APNs", "service"), ("mutable-content", "config"), ("Notification Service Extension", "api")],
     [],
     "which iOS push payload conventions allow the extension to mutate the body before rendering",
     "apns payload mutable content notification service extension decrypt"),
    # --- 18 ---
    ("FCM topic subscriptions drive the broadcast notifications; per-device tokens are kept for direct messages but topics cut our fan-out traffic by an order of magnitude.", "architecture", "ai_coding", False,
     [("FCM", "service"), ("topic", "pattern"), ("device token", "pattern")],
     [],
     "which FCM delivery mechanism handles broadcast notifications and why",
     "fcm topic subscribe broadcast device token fan out traffic android"),
    # --- 19 ---
    ("StoreKit 2 replaced our StoreKit 1 transaction observer glue; Transaction.currentEntitlements and the async updates stream made the receipt-validation server call optional in normal flows.", "decision", "ai_coding", False,
     [("StoreKit 2", "framework"), ("StoreKit 1", "framework"), ("Transaction.currentEntitlements", "api")],
     [("StoreKit 2", "StoreKit 1", "IMPROVES_ON")],
     "which iOS in-app purchase framework replaced StoreKit 1 and what did it simplify",
     "storekit 2 improve storekit 1 entitlement transaction async stream"),
    # --- 20 ---
    ("Google Play Billing Library 6 pairs with a BillingClient singleton bound to the application process; the acknowledgePurchase call now runs server-side via Real-Time Developer Notifications.", "architecture", "ai_coding", False,
     [("Google Play Billing", "library"), ("BillingClient", "api"), ("Real-Time Developer Notifications", "service")],
     [("BillingClient", "Google Play Billing", "USES")],
     "how does the Android app acknowledge purchases after moving to Play Billing 6",
     "google play billing client acknowledge purchase real time developer"),
    # --- 21 ---
    ("Crash reporting moved from Crashlytics to Sentry because symbolicated async stack traces across Swift concurrency hops were missing frames in Crashlytics for months.", "decision", "ai_coding", False,
     [("Crashlytics", "service"), ("Sentry", "service"), ("Swift", "language")],
     [("Sentry", "Crashlytics", "REPLACES")],
     "which crash reporter replaced Crashlytics on iOS and why did it win",
     "sentry replace crashlytics swift concurrency async stack symbol"),
    # --- 22 ---
    ("Embrace sits alongside Sentry for session timelines; Sentry handles the crash signal while Embrace's network and user-flow breadcrumbs drive the release health dashboard.", "architecture", "ai_coding", False,
     [("Embrace", "service"), ("Sentry", "service")],
     [],
     "how are Embrace and Sentry split between session timelines and crash reporting",
     "embrace sentry session timeline crash network breadcrumb dashboard"),
    # --- 23 ---
    ("Core Data migrations run as lightweight unless the mapping model exists; the app pre-creates NSPersistentStoreDescription with shouldInferMappingModelAutomatically off for the v4-to-v5 custom migration.", "architecture", "ai_coding", False,
     [("Core Data", "framework"), ("NSPersistentStoreDescription", "api"), ("shouldInferMappingModelAutomatically", "config")],
     [],
     "how does the iOS app decide between lightweight and custom Core Data migration",
     "core data lightweight migration mapping model persistent store ios"),
    # --- 24 ---
    ("Room replaced the hand-rolled SQLiteOpenHelper stack on the Android app; TypeConverters killed an entire folder of blob-serialisation boilerplate in the process.", "decision", "ai_coding", False,
     [("Room", "library"), ("SQLiteOpenHelper", "api"), ("TypeConverters", "api"), ("Android", "platform")],
     [("Room", "SQLiteOpenHelper", "REPLACES")],
     "which Android persistence library replaced the raw SQLiteOpenHelper stack",
     "room replace sqlite open helper type converters android persistence"),
    # --- 25 ---
    ("Realm still backs the offline sync queue on the partner tablet app; the live-objects contract is load-bearing for the inventory screen and no replacement matches the ergonomics.", "fact", "ai_coding", False,
     [("Realm", "database"), ("partner tablet app", "project")],
     [],
     "which mobile database keeps the offline sync queue on the partner tablet app",
     "realm live object offline sync queue inventory tablet partner"),
    # --- 26 ---
    ("Asset Catalogs carry every iOS image as an App Icon set plus 1x/2x/3x raster pairs; vector PDFs are enabled with Preserve Vector Data only on symbols that need template tinting.", "architecture", "ai_coding", False,
     [("Asset Catalogs", "pattern"), ("Preserve Vector Data", "config"), ("iOS", "platform")],
     [],
     "how are iOS assets organised across raster and vector artwork in the catalog",
     "asset catalog app icon vector pdf preserve data 1x 2x 3x ios"),
    # --- 27 ---
    ("Vector Drawables cover nearly every Android asset; raster PNGs are reserved for photographic textures that vector paths would bloat rather than compress.", "architecture", "ai_coding", False,
     [("Vector Drawables", "pattern"), ("PNG", "pattern"), ("Android", "platform")],
     [],
     "which Android asset format is the default and where does raster still make sense",
     "vector drawable android png photographic texture compress asset"),
    # --- 28 ---
    ("Lottie animations drive the onboarding hero on both iOS and Android; the JSON is shared across platforms and the designer exports from After Effects with the bodymovin plugin.", "architecture", "ai_coding", False,
     [("Lottie", "library"), ("After Effects", "tool"), ("bodymovin", "tool"), ("iOS", "platform"), ("Android", "platform")],
     [("Lottie", "bodymovin", "USES")],
     "how does the onboarding hero share animations between iOS and Android",
     "lottie animation bodymovin after effects json shared ios android"),
    # --- 29 ---
    ("BGProcessingTask handles overnight database vacuum on iOS; the identifier is registered in Info.plist's BGTaskSchedulerPermittedIdentifiers and the handler has a hard 30-second budget.", "architecture", "ai_coding", False,
     [("BGProcessingTask", "api"), ("Info.plist", "file"), ("BGTaskSchedulerPermittedIdentifiers", "config"), ("iOS", "platform")],
     [],
     "how does the iOS app schedule an overnight database vacuum without getting the process killed",
     "bg processing task info plist identifier scheduler vacuum ios"),
    # --- 30 ---
    ("WorkManager handles every deferrable Android job; the old JobScheduler and GCMNetworkManager code paths got deleted once the minSdk moved to 26 and WorkManager covered legacy devices.", "decision", "ai_coding", False,
     [("WorkManager", "library"), ("JobScheduler", "api"), ("GCMNetworkManager", "api"), ("Android", "platform")],
     [("WorkManager", "JobScheduler", "REPLACES")],
     "which Android background-work API now replaces the JobScheduler and GCMNetworkManager paths",
     "workmanager replace jobscheduler gcm network manager android legacy"),
    # --- 31 ---
    ("App Store Review rejection on guideline 4.3 forced us to split the private-label rebrand into a separate SKU; the shared codebase now gates theming via a compiled-in brand id.", "problem", "ai_coding", False,
     [("App Store", "service"), ("guideline 4.3", "publication"), ("SKU", "concept")],
     [],
     "which App Store guideline forced the rebrand split and how does the code handle multi-SKU now",
     "app store 4.3 rejection private label sku rebrand theming brand id"),
    # --- 32 ---
    ("Play Store Data Safety form is generated from a JSON manifest in the repo; every new analytics SDK PR has to update the manifest or the Play upload step in CI fails.", "architecture", "ai_coding", False,
     [("Play Store", "service"), ("Data Safety", "config")],
     [],
     "how is the Play Store Data Safety form kept in sync with analytics SDK changes",
     "play store data safety manifest json ci analytics sdk declare"),
    # --- 33 ---
    ("Swift concurrency migration replaced DispatchQueue.main.async calls with @MainActor isolation; the UI layer no longer assumes a thread, it declares one.", "decision", "ai_coding", False,
     [("@MainActor", "api"), ("DispatchQueue", "api"), ("Swift", "language")],
     [("@MainActor", "DispatchQueue", "REPLACES")],
     "what now isolates iOS UI work after removing the explicit dispatch-queue hops",
     "main actor replace dispatch queue swift concurrency ui thread"),
    # --- 34 ---
    ("Kotlin coroutines on Android bind structured scopes to viewModelScope and lifecycleScope; GlobalScope is banned by a lint rule to stop orphan jobs surviving navigation.", "preference", "ai_coding", False,
     [("viewModelScope", "api"), ("lifecycleScope", "api"), ("GlobalScope", "api"), ("Kotlin", "language")],
     [],
     "how does Android code keep Kotlin coroutines scoped to avoid orphan jobs",
     "viewmodel scope lifecycle global coroutine kotlin lint ban orphan"),
    # --- 35 ---
    ("Push notification permission now prompts after first meaningful interaction rather than at launch; opt-in rate nearly doubled on iOS after the change went live on 2026-02-14.", "milestone", "ai_coding", False,
     [("Push notification", "pattern"), ("iOS", "platform"), ("2026-02-14", "date")],
     [],
     "when did the iOS notification prompt move off first-launch and what was the opt-in impact",
     "push notification permission first interaction ios opt in rate prompt"),
    # --- 36 ---
    ("The Android 13 POST_NOTIFICATIONS runtime permission landed with a contextual rationale screen; the targetSdk bump that forced it was the 34 upgrade.", "architecture", "ai_coding", False,
     [("POST_NOTIFICATIONS", "config"), ("Android 13", "platform"), ("targetSdk", "config")],
     [],
     "which Android runtime permission was gated behind the targetSdk 34 bump",
     "post notifications android 13 permission target sdk 34 rationale"),
    # --- 37 ---
    ("SwiftData is under evaluation behind a feature flag; the production Core Data stack stays for now because migration tooling and CloudKit mirroring are still maturing.", "fact", "ai_coding", False,
     [("SwiftData", "framework"), ("Core Data", "framework"), ("CloudKit", "service")],
     [],
     "which iOS persistence framework is being evaluated as a potential Core Data successor",
     "swift data core data cloudkit mirror feature flag evaluation ios"),
    # --- 38. noise ---
    ("The office kombucha tap switched to a new flavour that nobody on the Android team seems to tolerate.", "fact", "noise", True, [], [], None, None),
    # --- 39 ---
    ("Android ProGuard gave way to R8 for release builds; the shrinker config got simpler and the dex method count under Play Feature Delivery dropped below the 64K threshold per split.", "decision", "ai_coding", False,
     [("R8", "tool"), ("ProGuard", "tool"), ("Play Feature Delivery", "service"), ("Android", "platform")],
     [("R8", "ProGuard", "REPLACES")],
     "which Android shrinker replaced ProGuard on release builds and what was the dex impact",
     "r8 replace proguard shrinker dex method count play feature delivery"),
    # --- 40 ---
    ("Dynamic Feature modules gate the optional scanning flow on Android; the base APK stays under 15 MB and the scanner download kicks off from a deep-link handler on first use.", "architecture", "ai_coding", False,
     [("Dynamic Feature", "pattern"), ("APK", "pattern"), ("Android", "platform")],
     [],
     "how does the Android app keep the base APK small while still shipping the scanner flow",
     "dynamic feature module apk base size scanner deep link android"),
    # --- 41 ---
    ("Swift Package Manager replaced CocoaPods in the main iOS workspace; a handful of binary-only vendor SDKs still ship as xcframeworks referenced via SPM binary targets.", "milestone", "ai_coding", False,
     [("Swift Package Manager", "tool"), ("CocoaPods", "tool"), ("xcframework", "pattern"), ("iOS", "platform")],
     [("Swift Package Manager", "CocoaPods", "REPLACES")],
     "which iOS dependency manager replaced CocoaPods and how do binary SDKs plug in",
     "swift package manager replace cocoapods xcframework binary target ios"),
    # --- 42 ---
    ("Gradle version catalog centralises every Android dependency version; the libs.versions.toml file is the single editable surface for bumping Compose BOM and AndroidX.", "architecture", "ai_coding", False,
     [("Gradle", "tool"), ("libs.versions.toml", "file"), ("Compose BOM", "library"), ("AndroidX", "library")],
     [],
     "where are Android dependency versions defined so Compose BOM and AndroidX bumps land in one place",
     "gradle version catalog libs versions toml compose bom androidx"),
    # --- 43 ---
    ("Accessibility labels live with the component in SwiftUI via accessibilityLabel modifiers; the review checklist also requires an accessibilityIdentifier for every tappable primitive so UI tests can hook on.", "preference", "ai_coding", False,
     [("accessibilityLabel", "api"), ("accessibilityIdentifier", "api"), ("SwiftUI", "framework")],
     [],
     "how does the iOS review checklist require accessibility metadata on tappable SwiftUI primitives",
     "accessibility label identifier swiftui tappable ui test hook ios"),
    # --- 44 ---
    ("Hilt handles DI on Android, replacing the last of the manual Dagger 2 component wiring; generated code dropped by roughly half after the cutover.", "milestone", "ai_coding", False,
     [("Hilt", "library"), ("Dagger 2", "library"), ("Android", "platform")],
     [("Hilt", "Dagger 2", "REPLACES")],
     "which Android DI framework replaced manual Dagger 2 wiring and what was the generated-code impact",
     "hilt replace dagger android dependency injection generated code"),
    # --- 45 ---
    ("Flutter state management lives in Riverpod 2; the legacy Provider packages stay in one archive screen scheduled for deletion next quarter.", "decision", "ai_coding", False,
     [("Riverpod", "library"), ("Provider", "library"), ("Flutter", "framework")],
     [("Riverpod", "Provider", "REPLACES")],
     "which Flutter state-management library replaced Provider and where does Provider still live",
     "riverpod replace provider flutter state management archive screen"),
    # --- 46 ---
    ("Swift Testing replaced XCTest for new unit suites; expect macros and parameterised tests landed cleanly and XCTest stays only where snapshot-testing libraries have not caught up.", "decision", "ai_coding", False,
     [("Swift Testing", "framework"), ("XCTest", "framework")],
     [("Swift Testing", "XCTest", "REPLACES")],
     "which iOS test framework replaced XCTest for new suites and what held XCTest in place",
     "swift testing replace xctest parameterised expect macro snapshot"),
    # --- 47 ---
    ("Android instrumented tests run on a Gradle Managed Device grid; the old Firebase Test Lab integration stayed for the long-tail OEM matrix covering Samsung One UI quirks.", "architecture", "ai_coding", False,
     [("Gradle Managed Device", "tool"), ("Firebase Test Lab", "service"), ("Samsung One UI", "platform")],
     [],
     "how does Android instrumented testing split between Gradle Managed Devices and Firebase Test Lab",
     "gradle managed device firebase test lab android oem samsung one ui"),
    # --- 48 ---
    ("App Store Connect upload runs through fastlane deliver; the signing metadata pulls from a match repo on a private Git remote and rotating an expired cert is now a 90-second job.", "architecture", "ai_coding", False,
     [("App Store Connect", "service"), ("fastlane", "tool"), ("match", "tool")],
     [("fastlane", "match", "USES")],
     "how does the iOS release flow handle signing rotation via fastlane match",
     "fastlane deliver match app store connect signing rotation ios cert"),
    # --- 49 ---
    ("Play Asset Delivery serves install-time assets for the 3D catalog on Android; the asset pack replaced an OBB expansion file and cut a whole support ticket category about download stalls.", "milestone", "ai_coding", False,
     [("Play Asset Delivery", "service"), ("OBB", "pattern"), ("asset pack", "pattern"), ("Android", "platform")],
     [("Play Asset Delivery", "OBB", "REPLACES")],
     "which Android asset-delivery mechanism replaced OBB expansion files for the 3D catalog",
     "play asset delivery obb expansion pack android 3d catalog install"),
    # --- 50 ---
    ("Foreground service types on Android 14 are declared per use case; the location-tracking service advertises location and the media-playback service advertises mediaPlayback so the system doesn't kill them.", "reference", "ai_coding", False,
     [("Foreground service", "pattern"), ("Android 14", "platform"), ("mediaPlayback", "config")],
     [],
     "how does the Android 14 foreground-service declaration split between location and media use cases",
     "foreground service type android 14 location media playback declare"),
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
