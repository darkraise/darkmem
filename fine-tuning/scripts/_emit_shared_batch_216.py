"""One-off emitter for shared-base batch-216 — personal domain (video editing and podcast production: NLEs, color, cameras, codecs, mics, interfaces, DAWs, podcast tools, transcription, hosting).

Writes 50 rows to data/v2/shared/batch_216.tmp.jsonl with ids shared-10751..10800.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_216.tmp.jsonl"
ID_OFFSET = 10750

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Moved the weekly podcast edit from Adobe Premiere Pro to DaVinci Resolve Studio 19; the Fairlight page consolidates the audio pass and the node-based grading saves a round-trip for the talking-head B-roll.", "decision", "personal", False,
     [("Adobe Premiere Pro", "tool"), ("DaVinci Resolve Studio 19", "tool"), ("Fairlight", "method")],
     [("DaVinci Resolve Studio 19", "Adobe Premiere Pro", "REPLACES")],
     "which editor replaced Premiere for the weekly podcast and what on-page workflow did it consolidate",
     "davinci resolve premiere fairlight node grade podcast switch"),
    # --- 2 architecture ---
    ("The colour pipeline sits in ACES with DWG working space and a Rec. 2020 output transform; LUTs now live only as creative looks on a dedicated node rather than as technical conversions.", "architecture", "personal", False,
     [("ACES", "protocol"), ("DWG", "protocol"), ("Rec. 2020", "protocol"), ("LUTs", "concept")],
     [("ACES", "LUTs", "REPLACES")],
     "which colour-managed working space replaced bare LUTs for technical conversion in the pipeline",
     "aces dwg rec 2020 lut color pipeline creative look node"),
    # --- 3 milestone ---
    ("Shipped episode 100 of the interview show on Transistor with a full DaVinci Resolve Studio 19 grade and a Hindenburg master for the audio; the workflow has been stable for a year.", "milestone", "personal", False,
     [("Transistor", "service"), ("DaVinci Resolve Studio 19", "tool"), ("Hindenburg", "tool")],
     [("Hindenburg", "Transistor", "APPLIES_TO")],
     "which milestone episode number did the interview show hit on Transistor and which tools cut the master",
     "episode 100 transistor resolve hindenburg interview milestone"),
    # --- 4 fact ---
    ("The A-camera on the studio set is a Blackmagic Pocket 6K Pro shooting Blackmagic RAW at 12:1; the BRAW file sizes are about a third of ProRes 4444 for the same visual quality.", "fact", "personal", False,
     [("Blackmagic Pocket 6K Pro", "technology"), ("Blackmagic RAW", "technology"), ("ProRes 4444", "technology")],
     [("Blackmagic RAW", "ProRes 4444", "REPLACES")],
     "which camera and codec drive the studio A-cam and how do file sizes compare to ProRes 4444",
     "blackmagic pocket 6k pro braw prores 4444 12 1 studio a cam"),
    # --- 5 reference ---
    ("The Sony FX3 and Sony FX6 share the same S-Cinetone and S-Log3 profiles; matching them on set means we can cut between them without a dedicated grade node per camera.", "reference", "personal", False,
     [("Sony FX3", "technology"), ("Sony FX6", "technology"), ("S-Log3", "technology"), ("S-Cinetone", "technology")],
     [("Sony FX3", "Sony FX6", "APPLIES_TO")],
     "which shared picture profiles let the FX3 and FX6 cut together without separate grade nodes",
     "sony fx3 fx6 slog3 s cinetone match grade cut profile"),
    # --- 6 preference ---
    ("Prefer recording podcast voice on a Shure SM7B over a Rode Procaster for the main host chair; the SM7B handles plosives and room noise with less work even before the Cloudlifter.", "preference", "personal", False,
     [("Shure SM7B", "technology"), ("Rode Procaster", "technology"), ("Cloudlifter", "technology")],
     [("Shure SM7B", "Rode Procaster", "PREFERS")],
     "which microphone do I prefer for the host chair and how does it handle plosives before the preamp",
     "shure sm7b rode procaster cloudlifter podcast host plosive"),
    # --- 7 decision ---
    ("Picked a RME Babyface over a Focusrite Scarlett for the mobile rig; the Babyface's drivers survive macOS updates without the USB dropouts the Scarlett showed in long interviews.", "decision", "personal", False,
     [("RME Babyface", "technology"), ("Focusrite Scarlett", "technology"), ("macOS", "platform")],
     [("RME Babyface", "Focusrite Scarlett", "PREFERS")],
     "which audio interface replaced the Focusrite Scarlett on the mobile rig and why",
     "rme babyface focusrite scarlett macos driver dropout mobile rig"),
    # --- 8 problem ---
    ("The H.265/HEVC exports from Final Cut Pro ghosted on a Shotcut-rendered intro; transcoding the intro to ProRes before the concat fixed the GOP boundary artefacts at the cut.", "problem", "personal", False,
     [("H.265/HEVC", "technology"), ("Final Cut Pro", "tool"), ("Shotcut", "tool"), ("ProRes", "technology")],
     [("ProRes", "H.265/HEVC", "REPLACES")],
     "which transcode step fixed the GOP-boundary ghosting when concatenating Shotcut renders into Final Cut Pro",
     "hevc h265 final cut shotcut prores gop ghost concat intro"),
    # --- 9 architecture ---
    ("The podcast ingest pipeline records locally via Riverside.fm, then the lossless WAV backups feed into Descript for transcript-first editing before Hindenburg handles the master and chapter markers.", "architecture", "personal", False,
     [("Riverside.fm", "service"), ("Descript", "tool"), ("Hindenburg", "tool"), ("WAV", "technology")],
     [("Riverside.fm", "Descript", "APPLIES_TO"), ("Descript", "Hindenburg", "APPLIES_TO")],
     "which three-stage pipeline handles remote podcast recording through transcript edit to master",
     "riverside descript hindenburg wav podcast ingest transcript master"),
    # --- 10. noise ---
    ("The office snake plant drooped for a week and perked up the day after someone finally repotted it into a terracotta pot.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Swapped Zencastr for SquadCast for remote interviews; SquadCast's progressive upload survived a guest's flaky hotel Wi-Fi during the last three recordings without losing the end of any take.", "decision", "personal", False,
     [("Zencastr", "service"), ("SquadCast", "service")],
     [("SquadCast", "Zencastr", "REPLACES")],
     "which remote-recording service replaced Zencastr for interviews and which failure mode did it survive",
     "squadcast zencastr progressive upload hotel wifi guest remote"),
    # --- 12 fact ---
    ("Whisper large-v3 runs locally on the M2 Mac Studio for transcript drafts; the hallucination rate on clean studio audio is low enough that Descript's correction pass is short.", "fact", "personal", False,
     [("Whisper", "framework"), ("M2 Mac Studio", "technology"), ("Descript", "tool")],
     [("Whisper", "Descript", "APPLIES_TO")],
     "which local transcription model feeds Descript and what hardware runs it for clean studio audio",
     "whisper large v3 m2 mac studio descript transcript local draft"),
    # --- 13 architecture ---
    ("Session files live in a project-per-episode tree with a transcripts/ folder, a masters/ folder for WAV and MP3, and an assets/ folder for LUTs and chapter art; nothing episode-specific leaks into the shared library.", "architecture", "personal", False,
     [("project-per-episode", "pattern"), ("transcripts/", "file"), ("masters/", "file"), ("assets/", "file"), ("LUTs", "concept")],
     [],
     "how is each podcast episode's project tree laid out to keep shared-library contamination out",
     "project per episode transcripts masters assets lut tree layout"),
    # --- 14 preference ---
    ("Prefer Reaper over Pro Tools for the podcast audio pass; the per-project installable Reaper copy and SWS extensions make batch render presets faster than Pro Tools session templates.", "preference", "personal", False,
     [("Reaper", "tool"), ("Pro Tools", "tool"), ("SWS", "library")],
     [("Reaper", "Pro Tools", "PREFERS")],
     "which DAW do I prefer for podcast audio and which extension stack seals the choice over Pro Tools",
     "reaper pro tools sws portable podcast audio render preset"),
    # --- 15 decision ---
    ("Chose the Sennheiser MKH416 over a Schoeps CMIT 5U for outdoor interview boom; the price-per-minute of rental and the proven reject on urban background noise won out over the CMIT's smoother off-axis.", "decision", "personal", False,
     [("Sennheiser MKH416", "technology"), ("Schoeps CMIT 5U", "technology")],
     [("Sennheiser MKH416", "Schoeps CMIT 5U", "PREFERS")],
     "which shotgun mic beat the Schoeps for outdoor interview boom and what drove the choice",
     "sennheiser mkh416 schoeps cmit 5u shotgun outdoor boom urban"),
    # --- 16 fact ---
    ("The DaVinci Resolve Studio 19 colour page uses a waveform and vectorscope side-by-side; the vectorscope's 75% colour bars target is what keeps skin-tone vectors pinned to the flesh line across episodes.", "fact", "personal", False,
     [("DaVinci Resolve Studio 19", "tool"), ("waveform", "tool"), ("vectorscope", "tool")],
     [],
     "which two scopes stay open on the colour page and how do they pin skin tone across episodes",
     "waveform vectorscope resolve colour page skin tone 75 percent"),
    # --- 17 milestone ---
    ("Crossed one million lifetime downloads on Buzzsprout last month; the jump over Libsyn came from moving the back catalogue over during the rebrand and pointing old RSS at the Buzzsprout redirect.", "milestone", "personal", False,
     [("Buzzsprout", "service"), ("Libsyn", "service"), ("RSS", "protocol")],
     [("Buzzsprout", "Libsyn", "REPLACES")],
     "which hosting milestone did the show hit on Buzzsprout and how did the catalogue move from Libsyn",
     "buzzsprout libsyn million downloads rss redirect back catalogue"),
    # --- 18 architecture ---
    ("Master-bus chain in Reaper is ReaEQ into a gentle ReaComp with a 2:1 ratio, then a hard-limiter for peaks, and finally a LUFS meter targeting -16 LUFS integrated for the podcast deliverable.", "architecture", "personal", False,
     [("Reaper", "tool"), ("ReaEQ", "tool"), ("ReaComp", "tool"), ("LUFS", "concept")],
     [],
     "which Reaper master-bus chain sits under the podcast LUFS target and what is the integrated loudness goal",
     "reaper reaeq reacomp limiter lufs 16 podcast master bus"),
    # --- 19 reference ---
    ("Avid Media Composer still owns the scripted-documentary project; the bin-based media management and ScriptSync on the interview rushes are the features nothing else in the toolbox fully replicates.", "reference", "personal", False,
     [("Avid Media Composer", "tool"), ("ScriptSync", "method")],
     [],
     "which NLE retains the scripted-documentary project and which unique features keep it in the toolbox",
     "avid media composer scriptsync bin documentary scripted rushes"),
    # --- 20 decision ---
    ("Picked Kdenlive over Shotcut for the Linux travel laptop; the proxy workflow in Kdenlive is closer to what the main DaVinci Resolve Studio 19 rig does, so round-tripping rushes to the studio doesn't require a re-ingest.", "decision", "personal", False,
     [("Kdenlive", "tool"), ("Shotcut", "tool"), ("DaVinci Resolve Studio 19", "tool")],
     [("Kdenlive", "Shotcut", "PREFERS")],
     "which Linux NLE won the travel-laptop slot over Shotcut and what workflow compatibility sealed it",
     "kdenlive shotcut linux travel proxy resolve round trip"),
    # --- 21 fact ---
    ("The Canon C70 on the B-cam records Canon Log 3 to CFexpress; the 4K intra-frame recording option cuts faster in DaVinci Resolve Studio 19 than the Long GOP profile even after optimised media.", "fact", "personal", False,
     [("Canon C70", "technology"), ("Canon Log 3", "technology"), ("CFexpress", "technology"), ("DaVinci Resolve Studio 19", "tool")],
     [("Canon Log 3", "Canon C70", "APPLIES_TO")],
     "which codec mode on the Canon C70 cuts faster in Resolve and what log profile does it use",
     "canon c70 log 3 cfexpress intra long gop resolve b cam"),
    # --- 22 problem ---
    ("AV1 exports from CapCut refused to stream cleanly on an older Smart TV during a client preview; fell back to H.265/HEVC HEVC Main10 at the same bitrate and the playback was immediately stable.", "problem", "personal", False,
     [("AV1", "technology"), ("CapCut", "tool"), ("H.265/HEVC", "technology")],
     [("H.265/HEVC", "AV1", "REPLACES")],
     "which codec fallback fixed an AV1 playback issue on an older Smart TV during a client preview",
     "av1 capcut hevc h265 smart tv client preview fallback bitrate"),
    # --- 23 architecture ---
    ("Chapter markers are authored in Hindenburg, exported as a podcast:chapters XML, and merged with the Transistor feed on publish; the RSS namespace entry is the single source of truth for chapter timing.", "architecture", "personal", False,
     [("Hindenburg", "tool"), ("Transistor", "service"), ("podcast:chapters", "protocol"), ("RSS", "protocol")],
     [("Hindenburg", "Transistor", "APPLIES_TO")],
     "how do Hindenburg chapter markers end up as the source of truth on the Transistor feed",
     "hindenburg chapter marker transistor rss podcast chapters xml"),
    # --- 24 preference ---
    ("Prefer the Electro-Voice RE20 for a second host chair even though the Shure SM7B is on the primary; the RE20's brighter presence range cuts through when two hosts overlap without a sidechain duck.", "preference", "personal", False,
     [("Electro-Voice RE20", "technology"), ("Shure SM7B", "technology")],
     [("Electro-Voice RE20", "Shure SM7B", "PREFERS")],
     "which mic do I prefer on the second host chair to cut through overlaps with the SM7B primary",
     "electro voice re20 shure sm7b second host overlap sidechain"),
    # --- 25 decision ---
    ("Moved the studio-recording monitor path through a Universal Audio OX reamp box for guitar pickups; the UA Apollo keeps the tracking chain dry while the OX handles the cabinet sim.", "decision", "personal", False,
     [("Universal Audio OX", "technology"), ("UA Apollo", "technology")],
     [("Universal Audio OX", "UA Apollo", "APPLIES_TO")],
     "which reamp path handles guitar cabinet sim off the Apollo and why is the tracking chain kept dry",
     "universal audio ox apollo reamp guitar cabinet sim dry track"),
    # --- 26 architecture ---
    ("Proxy media for 6K footage is generated as DNxHR LB at quarter resolution during ingest; the Blackmagic Pocket 6K Pro Blackmagic RAW originals stay on the archive drive and only link back for the final conform.", "architecture", "personal", False,
     [("DNxHR LB", "technology"), ("Blackmagic Pocket 6K Pro", "technology"), ("Blackmagic RAW", "technology")],
     [("DNxHR LB", "Blackmagic RAW", "APPLIES_TO")],
     "which proxy workflow sits under the Pocket 6K Pro BRAW and when do the originals come back online",
     "dnxhr lb proxy braw pocket 6k pro conform archive ingest"),
    # --- 27 milestone ---
    ("Finished the RED V-Raptor test shoot for the sponsored short; the 8K VV footage cut natively in DaVinci Resolve Studio 19 on the M2 Mac Studio without transcoding and that alone justifies the rental budget.", "milestone", "personal", False,
     [("RED V-Raptor", "technology"), ("DaVinci Resolve Studio 19", "tool"), ("M2 Mac Studio", "technology")],
     [("RED V-Raptor", "DaVinci Resolve Studio 19", "APPLIES_TO")],
     "which RED body did the sponsored-short test shoot clear and how did 8K VV cut on the Mac Studio",
     "red v raptor 8k vv m2 mac studio resolve native sponsored"),
    # --- 28 fact ---
    ("A DPA 4018 lavaliered on the host covers the handheld b-roll segments; the supercardioid pattern rejects the floor-wedge monitor at the tech-talk shoots without touching room treatment.", "fact", "personal", False,
     [("DPA 4018", "technology"), ("supercardioid", "concept")],
     [],
     "which lavalier pickup rejects the floor wedge at tech-talk shoots without room treatment tweaks",
     "dpa 4018 supercardioid lav b roll floor wedge tech talk"),
    # --- 29 decision ---
    ("Rev is the transcription vendor for the court-reporting segment; Otter.ai kept missing the legal-register terms in the sample batch and the Rev human-reviewed tier passed the same batch clean.", "decision", "personal", False,
     [("Rev", "service"), ("Otter.ai", "service")],
     [("Rev", "Otter.ai", "REPLACES")],
     "which transcription vendor replaced Otter.ai for the court-reporting segment and what drove the swap",
     "rev otter court reporting legal register human reviewed sample"),
    # --- 30 architecture ---
    ("The colour-grade handoff to the colourist uses CDL values in a sidecar per shot plus a baked Rec. 2020 reference render; the colourist relights in ACES and the sidecar drives the primary starting point.", "architecture", "personal", False,
     [("CDL", "protocol"), ("Rec. 2020", "protocol"), ("ACES", "protocol")],
     [("CDL", "ACES", "APPLIES_TO")],
     "how does the colour-grade handoff carry primary values across to the colourist's ACES session",
     "cdl sidecar aces rec 2020 reference render colourist primary"),
    # --- 31 reference ---
    ("Logic Pro stays the DAW for the music-bed composition; the stock amp models and the flex-pitch editor are enough for intro-stinger work and nothing about it blocks export to the podcast project.", "reference", "personal", False,
     [("Logic Pro", "tool"), ("flex-pitch", "method")],
     [],
     "which DAW stays reserved for music-bed work and why is it kept out of the podcast master path",
     "logic pro music bed flex pitch amp model intro stinger"),
    # --- 32 milestone ---
    ("Completed the Adobe Premiere Pro storage migration last month after the network-share auto-save corruption; every active project now auto-saves to the local drive and syncs nightly over rsync, and no corruption has reappeared since.", "milestone", "personal", False,
     [("Adobe Premiere Pro", "tool"), ("rsync", "tool"), ("auto-save", "method")],
     [("rsync", "auto-save", "APPLIES_TO")],
     "which storage-migration milestone retired the Premiere Pro network-share autosave corruption",
     "premiere pro autosave network share rsync corruption migration"),
    # --- 33 fact ---
    ("The ARRI Alexa 35 rental used on the music-video shoot recorded ARRIRAW to Codex; the delivery transcode to ProRes 4444 XQ was done in-camera-manufacturer software to keep metadata intact on the way into Resolve.", "fact", "personal", False,
     [("ARRI Alexa 35", "technology"), ("ARRIRAW", "technology"), ("Codex", "technology"), ("ProRes 4444", "technology")],
     [("ARRIRAW", "ARRI Alexa 35", "APPLIES_TO")],
     "which delivery transcode path preserved ARRIRAW metadata into Resolve for the music-video shoot",
     "arri alexa 35 arriraw codex prores 4444 xq metadata transcode"),
    # --- 34 decision ---
    ("Picked the Fujifilm X-H2S as the second-body B-roll camera over staying all-Sony; the 240 fps ProRes recording was the lever for the cooking-show slow-motion inserts without renting a cinema body per shoot.", "decision", "personal", False,
     [("Fujifilm X-H2S", "technology"), ("ProRes", "technology")],
     [("Fujifilm X-H2S", "ProRes", "APPLIES_TO")],
     "which hybrid body won the second B-roll slot and which slow-motion capability sealed the choice",
     "fujifilm x h2s 240 fps prores cooking slow motion b roll"),
    # --- 35 architecture ---
    ("The podcast deliverable is an MP3 at 128 kbps joint-stereo for Transistor and a lossless WAV master in the archive; the MP3 is always re-encoded from WAV rather than from a previous MP3 generation.", "architecture", "personal", False,
     [("MP3", "technology"), ("WAV", "technology"), ("Transistor", "service")],
     [("WAV", "MP3", "APPLIES_TO")],
     "which two-format deliverable strategy keeps the podcast free of generational MP3 re-encoding",
     "mp3 wav transistor 128 kbps joint stereo lossless master"),
    # --- 36 reference ---
    ("The SSL 2+ sits at the guest desk for drop-in recording sessions; its single-knob Legacy 4K analogue mode adds enough air to a guest's cheaper mic that the audio editor reliably needs fewer corrective EQ bands.", "reference", "personal", False,
     [("SSL 2+", "technology"), ("Legacy 4K", "method")],
     [],
     "which interface sits at the guest desk and which analogue-mode feature reduces corrective EQ work",
     "ssl 2 plus legacy 4k guest desk drop in analogue mode"),
    # --- 37 fact ---
    ("The SSD array for the edit bay is three 8 TB NVMe drives in RAID 0; the Blackmagic RAW from the Blackmagic Pocket 6K Pro sustains its ingest rate comfortably and the nightly backup goes to spinning disks off-rack.", "fact", "personal", False,
     [("NVMe", "technology"), ("RAID 0", "pattern"), ("Blackmagic RAW", "technology"), ("Blackmagic Pocket 6K Pro", "technology")],
     [("RAID 0", "NVMe", "APPLIES_TO")],
     "which storage layout in the edit bay sustains BRAW ingest from the Pocket 6K Pro",
     "nvme raid 0 8 tb braw pocket 6k pro edit bay backup"),
    # --- 38 decision ---
    ("Chose Descript for the ad-insertion workflow over a manual Reaper cut; the text-level edit of dynamic midroll slots saved roughly two hours per episode at the cost of one subscription seat.", "decision", "personal", False,
     [("Descript", "tool"), ("Reaper", "tool")],
     [("Descript", "Reaper", "PREFERS")],
     "which editor owns the midroll ad-insertion workflow and what per-episode time saving did it win",
     "descript reaper ad insertion midroll text edit subscription"),
    # --- 39 architecture ---
    ("Multicam sync on the interview shoots uses a Tentacle Sync timecode jam across the Sony FX6 and the Blackmagic Pocket 6K Pro; DaVinci Resolve Studio 19's auto sync clip lines them up without relying on clap or scratch audio.", "architecture", "personal", False,
     [("Tentacle Sync", "technology"), ("Sony FX6", "technology"), ("Blackmagic Pocket 6K Pro", "technology"), ("DaVinci Resolve Studio 19", "tool")],
     [("Tentacle Sync", "DaVinci Resolve Studio 19", "APPLIES_TO")],
     "how do the interview multicams stay in sync across FX6 and Pocket 6K Pro without clap or scratch audio",
     "tentacle sync timecode fx6 pocket 6k resolve auto sync clip"),
    # --- 40 milestone ---
    ("The documentary cut locked picture yesterday on DaVinci Resolve Studio 19; ACES timeline, Rec. 2020 output, and the sound mix moves to Pro Tools for the final stereo and Atmos deliverables this week.", "milestone", "personal", False,
     [("DaVinci Resolve Studio 19", "tool"), ("ACES", "protocol"), ("Rec. 2020", "protocol"), ("Pro Tools", "tool"), ("Atmos", "technology")],
     [("DaVinci Resolve Studio 19", "Pro Tools", "APPLIES_TO")],
     "which milestone did the documentary hit on Resolve and which tool owns the final stereo and Atmos mix",
     "documentary picture lock resolve aces rec 2020 pro tools atmos"),
    # --- 41 problem ---
    ("A gamma shift between Final Cut Pro output and the DaVinci Resolve Studio 19 reference render traced to QuickTime's legacy gamma tag; stamping the file with a Rec. 709 tag on export fixed the mismatch in the client deliverable.", "problem", "personal", False,
     [("Final Cut Pro", "tool"), ("DaVinci Resolve Studio 19", "tool"), ("QuickTime", "tool"), ("Rec. 709", "protocol")],
     [("Rec. 709", "QuickTime", "APPLIES_TO")],
     "which gamma-tag fix resolved the Final Cut Pro vs Resolve shift in the client deliverable",
     "gamma shift final cut resolve quicktime rec 709 tag deliverable"),
    # --- 42 reference ---
    ("Reference LUTs for the documentary series live on the ACES node graph as creative looks; the Rec. 2020 output transform happens after the look so a Rec. 709 deliverable regrades the same project in one switch.", "reference", "personal", False,
     [("LUTs", "concept"), ("ACES", "protocol"), ("Rec. 2020", "protocol"), ("Rec. 709", "protocol")],
     [],
     "where do reference LUTs sit on the documentary node graph and how does a Rec. 709 deliverable regrade cheaply",
     "lut aces rec 2020 rec 709 node graph deliverable regrade"),
    # --- 43. noise ---
    ("The edit-bay coffee grinder started making a metallic whine last Thursday and nobody has volunteered to open it up yet.", "fact", "noise", True, [], [], None, None),
    # --- 44 milestone ---
    ("Fine-tuned the Descript overdub voice on twenty hours of host audio last month; pronunciation of proper nouns and guest names is now reliable enough for pickups without a re-record session.", "milestone", "personal", False,
     [("Descript", "tool"), ("overdub", "method")],
     [],
     "which Descript voice milestone let pickups happen without re-recording and on how much host audio",
     "descript overdub fine tune voice pickup proper noun twenty"),
    # --- 45 decision ---
    ("Picked Final Cut Pro over Adobe Premiere Pro for the travel-vlog cut; the magnetic timeline and Apple silicon H.265/HEVC encoder together finished the 25-minute vlog export in under eight minutes on a MacBook Pro.", "decision", "personal", False,
     [("Final Cut Pro", "tool"), ("Adobe Premiere Pro", "tool"), ("H.265/HEVC", "technology"), ("MacBook Pro", "technology")],
     [("Final Cut Pro", "Adobe Premiere Pro", "PREFERS")],
     "which editor won the travel-vlog slot over Premiere and which export metric clinched it",
     "final cut pro premiere magnetic timeline h265 macbook pro"),
    # --- 46 decision ---
    ("Picked a two-pass ffmpeg AV1 encode driven from the DaVinci Resolve Studio 19 render queue via a bash post-hook over sticking with H.265/HEVC for YouTube masters; the visual hit is invisible at the 1440p viewer sizes that dominate analytics.", "decision", "personal", False,
     [("AV1", "technology"), ("H.265/HEVC", "technology"), ("ffmpeg", "tool"), ("DaVinci Resolve Studio 19", "tool")],
     [("AV1", "H.265/HEVC", "REPLACES")],
     "how is the YouTube AV1 master produced after the Resolve render queue and when does it beat H.265",
     "av1 h265 ffmpeg two pass youtube resolve render queue 1440p"),
    # --- 47 preference ---
    ("Prefer to cut the rough assembly on CapCut on the iPad while travelling and pull the XML back into DaVinci Resolve Studio 19 for the finishing pass; the round-trip preserves in and out points without re-logging.", "preference", "personal", False,
     [("CapCut", "tool"), ("DaVinci Resolve Studio 19", "tool"), ("XML", "technology")],
     [("CapCut", "DaVinci Resolve Studio 19", "APPLIES_TO")],
     "which travel-assembly tool pairs with Resolve for finishing and how does the round-trip preserve edits",
     "capcut ipad xml resolve round trip assembly rough travel"),
    # --- 48 milestone ---
    ("Finished the podcast publish-pipeline rollout last week: a single Python script triggered on the Hindenburg export now uploads the MP3 to Transistor via API, posts the transcript to the site's CMS, and schedules the YouTube audiogram.", "milestone", "personal", False,
     [("Python", "language"), ("Hindenburg", "tool"), ("Transistor", "service"), ("YouTube", "service")],
     [("Python", "Transistor", "APPLIES_TO")],
     "which publish pipeline runs after a Hindenburg export and which three outputs does it drive",
     "python hindenburg transistor youtube audiogram cms publish pipeline"),
    # --- 49 decision ---
    ("Chose ProRes over DNxHR LB as the intermediate across the whole facility; every machine here is on Apple silicon and ProRes decode is hardware-accelerated while DNxHR LB stays CPU-bound on that hardware.", "decision", "personal", False,
     [("ProRes", "technology"), ("DNxHR LB", "technology"), ("Apple silicon", "technology")],
     [("ProRes", "DNxHR LB", "PREFERS")],
     "which intermediate codec replaced DNxHR across the facility and what hardware-decode argument won",
     "prores dnxhr apple silicon intermediate hardware decode facility"),
    # --- 50 reference ---
    ("The rack room keeps a printed reference of monitor calibration targets: D65 white point, 2.4 gamma for dim-surround, and 100 nits for the SDR master grade; anything higher only applies to HDR-flagged timelines.", "reference", "personal", False,
     [("D65", "concept"), ("SDR", "technology"), ("HDR", "technology")],
     [],
     "which monitor calibration targets sit on the rack-room reference and when do higher nit values apply",
     "d65 2 4 gamma 100 nits sdr hdr monitor calibration rack"),
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
