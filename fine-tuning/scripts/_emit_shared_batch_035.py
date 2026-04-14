"""One-off emitter for shared-base batch-035 — cross domain.

Slice: music / audio / podcasting at the intersection of tech and personal life.
Writes 50 rows to data/v2/shared/batch_035.tmp.jsonl with ids shared-01701..01750.
The main session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_035.tmp.jsonl"
ID_OFFSET = 1700

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Bitwig Studio replaced Cubase for the Tuesday writing sessions with Mateo because the modulation grid finally made the synth patches sing.", "decision", "cross", False,
     [("Bitwig Studio", "tool"), ("Cubase", "tool"), ("Mateo", "person"), ("synth patches", "concept")],
     [("Bitwig Studio", "Cubase", "REPLACES")],
     "which DAW took over the weekly co-writing sessions and why",
     "music workstation swap modulation routing collaborator studio"),
    # --- 2 ---
    ("The Universal Audio Apollo Twin X handles tracking for the home demos because the Unison preamp emulations flatter my SM7B better than the old Scarlett did.", "preference", "cross", False,
     [("Universal Audio Apollo Twin X", "tool"), ("Unison", "technology"), ("SM7B", "tool"), ("Scarlett", "tool")],
     [("Universal Audio Apollo Twin X", "Scarlett", "PREFERS")],
     "why did the home recording rig move to the Apollo interface",
     "audio interface preamp modelling dynamic microphone home demo"),
    # --- 3 ---
    ("Plexamp on the bedroom iPad streams the FLAC library off a Synology NAS so Priya can pick albums without waking the desktop.", "architecture", "cross", False,
     [("Plexamp", "service"), ("iPad", "infrastructure"), ("FLAC", "protocol"), ("Synology", "organization"), ("Priya", "person")],
     [("Plexamp", "Synology", "DEPENDS_ON")],
     "how does the household hi-res library reach the bedroom tablet",
     "lossless library network storage tablet remote listening partner"),
    # --- 4 ---
    ("Riverside.fm replaced Zencastr for the Slow Circuit podcast after the local-recording upload glitch ate Neha's episode 14 take.", "decision", "cross", False,
     [("Riverside.fm", "service"), ("Zencastr", "service"), ("Slow Circuit", "project"), ("Neha", "person"), ("episode 14", "event")],
     [("Riverside.fm", "Zencastr", "REPLACES")],
     "why did the podcast swap its remote recording platform after guest episode fourteen",
     "remote podcast tool switch upload failure guest retake"),
    # --- 5 ---
    ("My commute playlist gets regenerated every Monday by a Python script that reads last week's Last.fm scrobbles and pushes a Tidal mix to the Pixel.", "architecture", "cross", False,
     [("Python", "language"), ("Last.fm", "service"), ("Tidal", "service"), ("Pixel", "infrastructure")],
     [("Tidal", "Last.fm", "DEPENDS_ON")],
     "how does the weekly drive playlist get built from my listening history",
     "scrobble analytics streaming export phone Monday automation"),
    # --- 6 ---
    ("Genelec 8030C pair beat the KRK Rokit 5 in the A/B test in the treated office once the sub-60 Hz ringing showed up in REW.", "decision", "cross", False,
     [("Genelec 8030C", "tool"), ("KRK Rokit 5", "tool"), ("REW", "service")],
     [("Genelec 8030C", "KRK Rokit 5", "PREFERS")],
     "which nearfield monitors won the treated-room shootout",
     "studio monitor comparison low frequency measurement acoustic"),
    # --- 7 ---
    ("Ripped the inherited vinyl crate with a Project Debut Carbon feeding a Scarlett 2i2 into Audacity, then ran RX Elements for click removal.", "architecture", "cross", False,
     [("Project Debut Carbon", "tool"), ("Scarlett 2i2", "tool"), ("Audacity", "tool"), ("RX Elements", "tool")],
     [("RX Elements", "Audacity", "BUILDS_ON")],
     "how does the inherited record collection become clean digital files",
     "vinyl rip turntable interface denoise pipeline archival"),
    # --- 8 ---
    ("Descript's Overdub tricked Lena into thinking I had re-recorded the intro, which is why the show-notes disclaimer now mentions AI voice patches.", "problem", "cross", False,
     [("Descript", "service"), ("Overdub", "technology"), ("Lena", "person")],
     [("Descript", "Overdub", "USES")],
     "what forced the podcast to add a disclaimer about synthetic voice edits",
     "editor speech synthesis listener deception transparency note"),
    # --- 9 ---
    ("Hindenburg Pro kept its slot over Adobe Audition for the oral-history project because the auto-leveller handles my grandmother's soft voice better.", "preference", "cross", False,
     [("Hindenburg Pro", "tool"), ("Adobe Audition", "tool"), ("oral-history", "project"), ("grandmother", "person")],
     [("Hindenburg Pro", "Adobe Audition", "PREFERS")],
     "which editor stayed in charge of the family oral history recordings",
     "podcast editor auto leveller quiet speaker family archive"),
    # --- 10. noise ---
    ("One moment, let me grab my headphones.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("The Sonos Era 300 in the kitchen now plays Dolby Atmos Music from Amazon Music while the older Play:1 in the hallway handles announcements from Home Assistant.", "architecture", "cross", False,
     [("Sonos Era 300", "tool"), ("Dolby Atmos Music", "technology"), ("Amazon Music", "service"), ("Play:1", "tool"), ("Home Assistant", "service")],
     [("Sonos Era 300", "Amazon Music", "USES"), ("Play:1", "Home Assistant", "COMMUNICATES_WITH")],
     "how are the kitchen and hallway speakers split across music and announcements",
     "spatial audio streaming household zone smart home split role"),
    # --- 12 ---
    ("Logged the 2026-03-08 basement session for the Ghost Ledger EP through Reason 12 running on the M2 Mac mini with Robbie on drums.", "milestone", "cross", False,
     [("2026-03-08", "date"), ("Ghost Ledger", "project"), ("Reason 12", "tool"), ("M2 Mac mini", "infrastructure"), ("Robbie", "person")],
     [("Reason 12", "M2 Mac mini", "DEPLOYED_ON")],
     "when did the band track the new EP session and on which rig",
     "recording date EP project DAW host computer drummer friend"),
    # --- 13 ---
    ("Set the Intellijel Metropolix as the heart of the bedroom modular patch so the Elektron Digitakt handles the samples and the rack stays melodic.", "architecture", "cross", False,
     [("Intellijel Metropolix", "tool"), ("Elektron Digitakt", "tool")],
     [],
     "how did the modular synth and the sampler divide roles on the bedroom rig",
     "eurorack sequencer groovebox roles melody rhythm allocation"),
    # --- 14 ---
    ("Overcast finally replaced Apple Podcasts on my phone because Marco's Smart Speed saves about forty minutes across the Thursday commute.", "decision", "cross", False,
     [("Overcast", "tool"), ("Apple Podcasts", "service"), ("Marco", "person"), ("Smart Speed", "technology")],
     [("Overcast", "Apple Podcasts", "REPLACES")],
     "which podcast app took over after the time-saving playback feature won me over",
     "listener app switch silence trimming feature daily commute"),
    # --- 15 ---
    ("Traktor Pro 3 still loses sync with the Kontrol S4 MK3 whenever the USB hub is shared with the webcam, so DJ nights run on a dedicated port.", "problem", "cross", False,
     [("Traktor Pro 3", "tool"), ("Kontrol S4 MK3", "tool"), ("USB", "protocol"), ("webcam", "tool")],
     [("Traktor Pro 3", "Kontrol S4 MK3", "DEPENDS_ON")],
     "why does the DJ controller need its own USB port during sets",
     "DJ software controller sync jitter shared bus dedicated port"),
    # --- 16 ---
    ("Hauled a Neumann KM184 pair plus a Zoom F3 recorder to the cabin so Ana could capture the creek for the ambient EP she owes her label.", "architecture", "cross", False,
     [("Neumann KM184", "tool"), ("Zoom F3", "tool"), ("Ana", "person"), ("ambient EP", "project")],
     [],
     "what field-recording kit backed the creekside ambient project",
     "small diaphragm microphone portable recorder nature capture ambient release"),
    # --- 17 ---
    ("The Pro Tools HDX rig at Dad's studio stayed on macOS Ventura because the Avid drivers never stabilised on Sonoma.", "decision", "cross", False,
     [("Pro Tools", "tool"), ("HDX", "technology"), ("Dad", "person"), ("macOS Ventura", "platform"), ("Avid", "organization"), ("Sonoma", "platform")],
     [("Pro Tools", "HDX", "DEPENDS_ON")],
     "why did the family studio freeze its operating system version",
     "digital audio workstation hardware card OS compatibility hold"),
    # --- 18 ---
    ("FabFilter Pro-Q 4 replaced iZotope Neutron on the mastering bus after the dynamic bands sat more naturally on the mix of Sam's indie single.", "decision", "cross", False,
     [("FabFilter Pro-Q 4", "library"), ("iZotope Neutron", "library"), ("Sam", "person"), ("indie single", "project")],
     [("FabFilter Pro-Q 4", "iZotope Neutron", "REPLACES")],
     "which EQ plugin owns the mastering bus now and why it changed",
     "dynamic equaliser mastering chain swap indie release mix"),
    # --- 19 ---
    ("Subscribed to Nebula Genes and the Lo-Fi Girl radio so my focus sessions lean toward beats rather than the Apple Classical I use for journalling.", "preference", "cross", False,
     [("Nebula Genes", "service"), ("Lo-Fi Girl", "service"), ("Apple Classical", "service"), ("journalling", "activity")],
     [("Nebula Genes", "Apple Classical", "PREFERS")],
     "which listening channels match my focus blocks versus my journalling time",
     "streaming station context listening focus beats classical journal"),
    # --- 20 ---
    ("A Whisper large-v3 run on the RTX 4070 transcribed seventeen hours of Grandpa's interview tapes into Markdown for the family archive.", "architecture", "cross", False,
     [("Whisper large-v3", "library"), ("RTX 4070", "infrastructure"), ("Grandpa", "person"), ("Markdown", "language")],
     [("Whisper large-v3", "RTX 4070", "DEPLOYED_ON")],
     "how were the old family interview tapes turned into searchable notes",
     "speech to text local GPU family oral history transcription"),
    # --- 21 ---
    ("The Rekordbox library now rebuilds automatically from the Tidal playlist Priya shares every Friday so the wedding-warmup USB stays in sync.", "architecture", "cross", False,
     [("Rekordbox", "tool"), ("Tidal", "service"), ("Priya", "person"), ("USB", "protocol")],
     [("Rekordbox", "Tidal", "DEPENDS_ON")],
     "how does the DJ library keep pace with the weekly shared playlist",
     "DJ software export streaming friend playlist wedding set warm-up"),
    # --- 22 ---
    ("Sennheiser HD 660S2 took over mixing duties from the old HD 600 because the low end finally matched what the Genelecs showed me.", "decision", "cross", False,
     [("Sennheiser HD 660S2", "tool"), ("HD 600", "tool"), ("Genelecs", "tool")],
     [("Sennheiser HD 660S2", "HD 600", "REPLACES")],
     "which headphones moved into the main mixing role on the desk",
     "open back headphone swap low end reference translation monitors"),
    # --- 23 ---
    ("AntennaPod on the GrapheneOS phone keeps the feed OPML in Nextcloud so the work laptop and the travel phone stay on the same episode number.", "architecture", "cross", False,
     [("AntennaPod", "tool"), ("GrapheneOS", "platform"), ("OPML", "protocol"), ("Nextcloud", "service")],
     [("AntennaPod", "Nextcloud", "USES")],
     "how does the open-source podcast app sync progress across my two devices",
     "android privacy ROM feed export self hosted cloud resume state"),
    # --- 24 ---
    ("Frustration hit when the Moog Matriarch sent midi clock that confused the Ableton Link session and dropped the Friday jam with Theo.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Moog Matriarch", "tool"), ("Ableton Link", "technology"), ("Theo", "person")],
     [],
     "what broke the Friday jam between the analog synth and the DAW session",
     "midi clock sync analog synth wireless clock friend session drop"),
    # --- 25 ---
    ("Plexamp SuperSonic picks commute albums by blending my Last.fm history with the ratings Leila left on the shared family playlist.", "architecture", "cross", False,
     [("Plexamp SuperSonic", "service"), ("Last.fm", "service"), ("Leila", "person"), ("shared family playlist", "pattern")],
     [("Plexamp SuperSonic", "Last.fm", "USES")],
     "how does the commute album picker weigh my history against family ratings",
     "smart playlist history weighting household rating blend selector"),
    # --- 26. noise ---
    ("Sure, will circle back after this.", "fact", "noise", True, [], [], None, None),
    # --- 27 ---
    ("Hauled the Rode NT1 5th Gen into the walk-in closet vocal booth because the 32-bit float output meant Yuki could yell the bridge without clipping.", "architecture", "cross", False,
     [("Rode NT1 5th Gen", "tool"), ("32-bit float", "technology"), ("Yuki", "person")],
     [],
     "how did the vocal booth setup avoid clipping on the loud bridge take",
     "condenser microphone dynamic range dry closet vocal booth loud take"),
    # --- 28 ---
    ("Amped up the Neural DSP Quad Cortex over the Kemper on the road because the capture library shares directly into the band's Dropbox folder.", "decision", "cross", False,
     [("Neural DSP Quad Cortex", "tool"), ("Kemper", "tool"), ("Dropbox", "service")],
     [("Neural DSP Quad Cortex", "Kemper", "PREFERS")],
     "why did the touring amp modeller win over the older profiler",
     "guitar modeller profiler swap capture sharing band cloud folder"),
    # --- 29 ---
    ("Riverside.fm replaced the Zoom H6 local backup habit after the automatic double-ender saved the 2026-02-12 episode when the internet dropped halfway.", "milestone", "cross", False,
     [("Riverside.fm", "service"), ("Zoom H6", "tool"), ("2026-02-12", "date")],
     [("Riverside.fm", "Zoom H6", "REPLACES")],
     "when did the remote podcast tool prove itself over the local recorder habit",
     "internet dropout double ender recovery podcast workflow confidence"),
    # --- 30 ---
    ("Documented the eurorack patch that turned the Make Noise Morphagene loops into the beds for Aisha's meditation app demo on the kitchen whiteboard.", "reference", "cross", False,
     [("Make Noise Morphagene", "tool"), ("Aisha", "person"), ("meditation app", "project")],
     [],
     "where is the patch that generated the beds for the meditation app prototype",
     "modular patch notebook sample mangler ambient bed app prototype"),
    # --- 31 ---
    ("Chose the Focal Clear MG for the late-night mixing chair over the Audeze LCD-X because the planar weight gave my neck trouble after hour three.", "preference", "cross", False,
     [("Focal Clear MG", "tool"), ("Audeze LCD-X", "tool")],
     [("Focal Clear MG", "Audeze LCD-X", "PREFERS")],
     "which late-night mixing headphones won on long-session comfort",
     "dynamic headphone planar comfort long session ergonomics neck"),
    # --- 32 ---
    ("Splice Sounds subscription auto-tags the downloads into Ableton Live 12's browser via a Hazel rule so the Friday beat-making sprint never stalls.", "architecture", "cross", False,
     [("Splice Sounds", "service"), ("Ableton Live 12", "tool"), ("Hazel", "tool")],
     [("Hazel", "Splice Sounds", "USES")],
     "how do downloaded samples land tagged inside the DAW without manual dragging",
     "sample marketplace folder action rule DAW library ingestion"),
    # --- 33 ---
    ("Pocket Casts Plus finally justified its fee on the 2026-01-19 flight when offline downloads kept Rosa's kids from melting down over Planet Money.", "fact", "cross", False,
     [("Pocket Casts Plus", "service"), ("2026-01-19", "date"), ("Rosa", "person"), ("Planet Money", "publication")],
     [],
     "when did the paid podcast client actually earn its keep on a family trip",
     "offline download airplane family kids podcast subscription value"),
    # --- 34 ---
    ("The Acapella iOS app multitracks David's barbershop quartet into the shared iCloud folder so the weekend mixdown in Logic Pro takes ten minutes.", "architecture", "cross", False,
     [("Acapella", "tool"), ("David", "person"), ("iCloud", "service"), ("Logic Pro", "tool")],
     [("Acapella", "iCloud", "USES")],
     "how does the quartet's phone recording pipeline feed the weekend DAW mix",
     "phone multitrack capture cloud folder DAW import quick mix"),
    # --- 35 ---
    ("Hi-res downloads from Qobuz replace the Bandcamp fallback only on nights the wife plugs the DAC directly into the living-room amplifier.", "preference", "cross", False,
     [("Qobuz", "service"), ("Bandcamp", "service"), ("DAC", "tool"), ("amplifier", "tool")],
     [("Qobuz", "Bandcamp", "PREFERS")],
     "when does the hi-res store beat the independent store in the living room",
     "audiophile store lossless independent store living room chain listening"),
    # --- 36 ---
    ("Released the Thin Blue Tape cassette run on 2026-02-28 after the National Audio Company dub masters were cut on an Otari MX-5050 I rented in Denver.", "milestone", "cross", False,
     [("Thin Blue Tape", "project"), ("2026-02-28", "date"), ("National Audio Company", "organization"), ("Otari MX-5050", "tool"), ("Denver", "place")],
     [],
     "when did the cassette EP ship and which tape machine cut the dub masters",
     "cassette release duplication plant vintage tape machine rental city"),
    # --- 37 ---
    ("Switched the rehearsal room from a Mackie ProFX12v3 to the Behringer X32 Compact because recording the band stems for Javier got simpler over USB.", "decision", "cross", False,
     [("Mackie ProFX12v3", "tool"), ("Behringer X32 Compact", "tool"), ("Javier", "person"), ("USB", "protocol")],
     [("Behringer X32 Compact", "Mackie ProFX12v3", "REPLACES")],
     "why did the band upgrade the rehearsal mixer this year",
     "analog digital mixer swap multitrack USB recording band room"),
    # --- 38 ---
    ("Confirmed that Roon ARC streams the Nucleus library over Tailscale to the rental flat in Lisbon without touching any router port-forwarding.", "fact", "cross", False,
     [("Roon ARC", "service"), ("Nucleus", "tool"), ("Tailscale", "service"), ("Lisbon", "place")],
     [("Roon ARC", "Tailscale", "USES")],
     "how does the home library reach the Lisbon rental without router tweaks",
     "mesh VPN music server remote access travel flat streaming"),
    # --- 39 ---
    ("The Boulder Recording Club switched the club podcast feed to Transistor because Libsyn's analytics never matched what Chartable was showing.", "decision", "cross", False,
     [("Boulder Recording Club", "organization"), ("Transistor", "service"), ("Libsyn", "service"), ("Chartable", "service")],
     [("Transistor", "Libsyn", "REPLACES")],
     "why did the local club podcast move hosts after an analytics disagreement",
     "podcast host swap analytics mismatch third party platform trust"),
    # --- 40 ---
    ("Tamed the TR-8S clock drift against the MPC Live II by treating the MPC as master and running a Korg SQ-1 on the side for Jess's generative patterns.", "problem", "cross", False,
     [("TR-8S", "tool"), ("MPC Live II", "tool"), ("Korg SQ-1", "tool"), ("Jess", "person")],
     [("TR-8S", "MPC Live II", "DEPENDS_ON")],
     "how did the beat studio settle the clock drift between the drum box and the sampler",
     "clock master slave drum machine sampler secondary sequencer generative"),
    # --- 41 ---
    ("Built a tiny Flask dashboard on the home server that shows each family member's weekly Plex listening minutes and flags when Mateo resumes the same Radiohead album three times.", "architecture", "cross", False,
     [("Flask", "framework"), ("Plex", "service"), ("Mateo", "person"), ("Radiohead", "organization")],
     [("Flask", "Plex", "USES")],
     "how does the house track weekly listening and catch repeat-album binges",
     "self hosted dashboard household listening metric repeat album flag"),
    # --- 42 ---
    ("Kept the SoundID Reference calibration file on the Focal Solo6 Be pair because the living-room nulls shifted after Eva moved the couch two feet.", "problem", "cross", False,
     [("SoundID Reference", "service"), ("Focal Solo6 Be", "tool"), ("Eva", "person")],
     [("SoundID Reference", "Focal Solo6 Be", "CONFIGURES")],
     "why did the speaker room correction profile need rebuilding this spring",
     "room correction monitor calibration furniture move null shift"),
    # --- 43 ---
    ("Finally shipped the Whisper-powered Substack newsletter on 2026-03-22 that summarises each Decoder episode into bullet points for Tomas's reading habit.", "milestone", "cross", False,
     [("Whisper", "library"), ("Substack", "service"), ("2026-03-22", "date"), ("Decoder", "publication"), ("Tomas", "person")],
     [("Substack", "Whisper", "DEPENDS_ON")],
     "when did the AI podcast-summary newsletter go live and who is the target reader",
     "podcast summary newsletter launch transcription feed friend readership"),
    # --- 44 ---
    ("Hauled the Boss RC-600 out of storage because its MIDI footswitch bank lets me loop the acoustic with Clara over Zoom without a laptop.", "decision", "cross", False,
     [("Boss RC-600", "tool"), ("MIDI", "protocol"), ("Clara", "person"), ("Zoom", "service")],
     [],
     "what pedal resurfaced for remote acoustic looping sessions",
     "looper pedal midi footswitch remote jam acoustic video call"),
    # --- 45 ---
    ("Audirvana Studio on the Mac Studio beat Foobar2000 on the Windows NUC because gapless playback handled the Dark Side of the Moon transitions properly for Chen's listening parties.", "preference", "cross", False,
     [("Audirvana Studio", "service"), ("Mac Studio", "infrastructure"), ("Foobar2000", "tool"), ("NUC", "infrastructure"), ("Dark Side of the Moon", "publication"), ("Chen", "person")],
     [("Audirvana Studio", "Foobar2000", "PREFERS")],
     "which player handles album side transitions better for the hi-fi gatherings",
     "audiophile player gapless playback album listening party host"),
    # --- 46 ---
    ("GoldenEar BRX bookshelves replaced the Wharfedale Linton because the living-room rack between the Cambridge CXA81 and the vinyl shelf needed smaller footprint.", "decision", "cross", False,
     [("GoldenEar BRX", "tool"), ("Wharfedale Linton", "tool"), ("Cambridge CXA81", "tool")],
     [("GoldenEar BRX", "Wharfedale Linton", "REPLACES")],
     "which bookshelf speakers took over the living-room hi-fi rack",
     "speaker swap integrated amplifier furniture footprint vinyl shelf"),
    # --- 47 ---
    ("The Ardour session for the Thursday choir rehearsal lives on a Debian mini PC in the church basement so Father Liam can start the recording without an engineer.", "architecture", "cross", False,
     [("Ardour", "tool"), ("Debian", "platform"), ("mini PC", "infrastructure"), ("Father Liam", "person"), ("choir rehearsal", "event")],
     [("Ardour", "Debian", "DEPLOYED_ON")],
     "how does the choir start its rehearsal recording without a technician present",
     "open source DAW Linux church basement unattended recording"),
    # --- 48 ---
    ("MainStage finally replaced the Yamaha MODX rig for Uncle Dev's church services because the iPad-driven patch changes skipped the startup time that pushed the 9 AM call back.", "decision", "cross", False,
     [("MainStage", "tool"), ("Yamaha MODX", "tool"), ("Uncle Dev", "person"), ("iPad", "infrastructure")],
     [("MainStage", "Yamaha MODX", "REPLACES")],
     "why did the Sunday-service keys rig move from hardware to software",
     "live keys rig software replacement startup time patch changes"),
    # --- 49 ---
    ("The Waveform Pro project with Nora still crashes on export whenever the Melda plugin chain on the vocal bus exceeds eight instances, so we bounce in stages.", "problem", "cross", False,
     [("Waveform Pro", "tool"), ("Nora", "person"), ("Melda", "organization")],
     [("Waveform Pro", "Melda", "USES")],
     "what forces the duo to bounce vocal stems in stages instead of one export",
     "DAW export crash plugin chain count workaround stem bounce"),
    # --- 50 ---
    ("A Home Assistant automation dims the Philips Hue strip behind the turntable whenever the Denon DP-300F starts spinning, which marks the Friday ritual with Amaya.", "architecture", "cross", False,
     [("Home Assistant", "service"), ("Philips Hue", "tool"), ("Denon DP-300F", "tool"), ("Amaya", "person")],
     [("Home Assistant", "Philips Hue", "CONFIGURES")],
     "how does the smart home react when the turntable starts on Friday evenings",
     "smart lighting turntable trigger automation ritual partner evening"),
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
