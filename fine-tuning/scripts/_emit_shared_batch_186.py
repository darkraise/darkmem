"""One-off emitter for shared-base batch-186 — technical domain (audio processing and DSP: frameworks, plugin formats, host APIs, DSP algorithms, DAWs).

Writes 50 rows to data/v2/shared/batch_186.tmp.jsonl with ids shared-09251..09300.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_186.tmp.jsonl"
ID_OFFSET = 9250

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Picked JUCE over iPlug2 for the new compressor plugin; the cross-format wrapper ships VST3 and AUv3 from one codebase and the dsp module saved us weeks of filter work.", "decision", "technical", False,
     [("JUCE", "framework"), ("iPlug2", "framework"), ("VST3", "protocol"), ("AUv3", "protocol")],
     [("JUCE", "iPlug2", "PREFERS"), ("JUCE", "VST3", "SUPPORTS"), ("JUCE", "AUv3", "SUPPORTS")],
     "which cross-format plugin framework did the compressor team pick and which plugin formats does it target",
     "juce iplug2 vst3 auv3 cross format compressor plugin wrapper"),
    # --- 2 fact ---
    ("The audio engine layers a PortAudio host backend under a RtAudio-style callback abstraction; the low-level device enumeration now lives in a single file instead of one per OS.", "fact", "technical", False,
     [("PortAudio", "library"), ("RtAudio", "library"), ("callback abstraction", "pattern")],
     [("callback abstraction", "PortAudio", "USES")],
     "how does the audio engine abstract device enumeration across operating systems",
     "portaudio rtaudio callback host backend device enumeration os"),
    # --- 3 milestone ---
    ("Shipped the first CMajor-authored reverb: the patch compiles to WASM for the WebAudio preview page and to native for the VST3 binary without touching the graph definition.", "milestone", "technical", False,
     [("CMajor", "language"), ("WASM", "technology"), ("WebAudio", "api"), ("VST3", "protocol")],
     [("CMajor", "WASM", "PRODUCES"), ("CMajor", "VST3", "PRODUCES")],
     "which DSP language shipped our first cross-target reverb and which two build outputs did one graph produce",
     "cmajor reverb wasm webaudio vst3 cross target compile graph"),
    # --- 4 fact ---
    ("Faust generates the biquad cascade for the EQ band; the generated C++ drops straight into the JUCE dsp chain without a glue layer beyond a thin process wrapper.", "fact", "technical", False,
     [("Faust", "language"), ("JUCE", "framework"), ("biquad cascade", "algorithm")],
     [("Faust", "biquad cascade", "PRODUCES"), ("Faust", "JUCE", "APPLIES_TO")],
     "which DSL produces the EQ biquad cascade and how does it integrate with the JUCE dsp chain",
     "faust juce biquad cascade eq generate cpp dsp chain"),
    # --- 5 reference ---
    ("The YIN pitch-detection paper by de Cheveigne and Kawahara is still the reference we lean on for the monophonic vocal tuner; SWIPE comes in for noisier instrument tracks.", "reference", "technical", False,
     [("YIN", "algorithm"), ("SWIPE", "algorithm"), ("de Cheveigne", "person"), ("Kawahara", "person"), ("monophonic vocal tuner", "project")],
     [("YIN", "de Cheveigne", "AUTHORED_BY"), ("monophonic vocal tuner", "YIN", "USES")],
     "which pitch detection papers anchor our tuner design and which algorithm handles noisier instrument tracks",
     "yin swipe pitch detection monophonic vocal tuner noisy instrument"),
    # --- 6 decision ---
    ("Standardised on KissFFT for embedded targets and FFTW for the desktop renderer; the license boundary and SIMD gap both pushed us to a two-library split instead of one everywhere.", "decision", "technical", False,
     [("KissFFT", "library"), ("FFTW", "library"), ("SIMD", "concept")],
     [("KissFFT", "FFTW", "REPLACES")],
     "which two FFT libraries split our stack between embedded and desktop and what drove the split",
     "kissfft fftw simd embedded desktop license fft library split"),
    # --- 7 problem ---
    ("Convolution reverb on mobile was eating the CPU budget; switched from direct FIR convolution to a partitioned-block FFT convolver and the load dropped below fifteen percent.", "problem", "technical", False,
     [("Convolution reverb", "algorithm"), ("direct FIR convolution", "algorithm"), ("partitioned-block FFT convolver", "algorithm")],
     [("partitioned-block FFT convolver", "direct FIR convolution", "REPLACES")],
     "which convolver algorithm replaced direct FIR on mobile to cut the reverb CPU load",
     "convolution reverb partitioned block fft fir convolver mobile cpu"),
    # --- 8 architecture ---
    ("Sample-rate conversion in the mix bus uses a polyphase windowed-sinc filter; the earlier linear interpolation produced audible aliasing above ten kilohertz during pitch shifts.", "architecture", "technical", False,
     [("polyphase", "algorithm"), ("windowed-sinc filter", "algorithm"), ("linear interpolation", "algorithm"), ("aliasing", "concept")],
     [("polyphase", "linear interpolation", "REPLACES")],
     "which sample-rate converter replaced linear interpolation after aliasing showed up during pitch shifts",
     "polyphase windowed sinc linear interpolation sample rate aliasing"),
    # --- 9 decision ---
    ("Rubberband drives time-stretch and pitch-shift in the DAW export path; the phase vocoder we hand-rolled smeared transients on drum stems and we retired it after the v4 release.", "decision", "technical", False,
     [("Rubberband", "library"), ("phase vocoder", "algorithm"), ("time-stretch", "concept"), ("pitch-shift", "concept")],
     [("Rubberband", "phase vocoder", "REPLACES")],
     "which time-stretch library replaced our hand-rolled phase vocoder after it smeared drum transients",
     "rubberband phase vocoder time stretch pitch shift drum transient"),
    # --- 10 noise ---
    ("The studio coffee grinder finally broke and the whole sound team is rationing the last bag of single-origin beans.", "fact", "noise", True, [], [], None, None),
    # --- 11 architecture ---
    ("The plugin ships three binaries from one target: VST3, AUv3, and LV2; the Steinberg VST SDK provides the core host contract and Apple AudioUnits wraps the AUv3 bundle.", "architecture", "technical", False,
     [("VST3", "protocol"), ("AUv3", "protocol"), ("LV2", "protocol"), ("Steinberg VST SDK", "library"), ("Apple AudioUnits", "framework")],
     [("Steinberg VST SDK", "VST3", "IMPLEMENTS"), ("Apple AudioUnits", "AUv3", "IMPLEMENTS")],
     "which three plugin formats ship from the single target and which SDKs back each one",
     "vst3 auv3 lv2 steinberg audiounits plugin formats host contract"),
    # --- 12 decision ---
    ("Replaced PulseAudio with PipeWire as the default Linux backend; session latency dropped by about four milliseconds and JACK clients now coexist with desktop audio on the same graph.", "decision", "technical", False,
     [("PulseAudio", "service"), ("PipeWire", "service"), ("JACK", "service"), ("Linux", "platform")],
     [("PipeWire", "PulseAudio", "REPLACES"), ("PipeWire", "JACK", "SUPPORTS")],
     "which Linux audio server replaced PulseAudio and what latency and coexistence wins did it unlock",
     "pipewire pulseaudio jack linux default backend latency coexist"),
    # --- 13 fact ---
    ("ALSA sits underneath PipeWire on our Linux builds; direct ALSA access is still exposed for the measurement tool where we cannot afford the server's scheduling jitter.", "fact", "technical", False,
     [("ALSA", "service"), ("PipeWire", "service"), ("measurement tool", "project")],
     [("PipeWire", "ALSA", "DEPENDS_ON"), ("measurement tool", "ALSA", "USES")],
     "which low-level Linux audio API do we still hit directly for the measurement tool and why",
     "alsa pipewire linux measurement tool scheduling jitter direct"),
    # --- 14 architecture ---
    ("Core Audio on macOS is accessed through an AVFoundation capture session rather than raw AudioToolbox; the high-level session simplified permissions and device-change handling considerably.", "architecture", "technical", False,
     [("Core Audio", "api"), ("macOS", "platform"), ("AVFoundation", "framework"), ("AudioToolbox", "framework")],
     [("AVFoundation", "Core Audio", "USES"), ("AVFoundation", "AudioToolbox", "REPLACES")],
     "which macOS framework wraps Core Audio for our capture path and which lower-level API did it replace",
     "core audio macos avfoundation audiotoolbox capture session permission"),
    # --- 15 preference ---
    ("The DSP team prefers REAPER for plugin debugging sessions: the ReaJS console, flexible routing, and low overhead beat Ableton and Logic Pro when stepping through a crash loop.", "preference", "technical", False,
     [("REAPER", "tool"), ("Ableton", "tool"), ("Logic Pro", "tool")],
     [("REAPER", "Ableton", "PREFERS"), ("REAPER", "Logic Pro", "PREFERS")],
     "which DAW does the DSP team prefer for plugin debugging and which alternatives did they weigh against it",
     "reaper ableton logic pro dsp debug plugin crash loop routing"),
    # --- 16 milestone ---
    ("First Bitwig Grid patch shipped as a preset pack; the CMajor export path let us mirror the same DSP graph into the plugin build without rewriting the oscillator chain.", "milestone", "technical", False,
     [("Bitwig Grid", "pattern"), ("CMajor", "language")],
     [("Bitwig Grid", "CMajor", "RELATED_TO")],
     "which DAW's modular environment got our first preset pack and which export path kept the DSP graph consistent",
     "bitwig grid cmajor preset pack dsp graph oscillator chain export"),
    # --- 17 fact ---
    ("WebAudio API nodes compose the browser preview; Tone.js sits on top as the musical-time scheduler so track timelines sync to transport beats rather than raw seconds.", "fact", "technical", False,
     [("WebAudio API", "api"), ("Tone.js", "library"), ("transport", "concept")],
     [("Tone.js", "WebAudio API", "BUILDS_ON")],
     "which library layers musical-time scheduling on top of the WebAudio API in the browser preview",
     "webaudio tone js browser preview musical time transport scheduler"),
    # --- 18 decision ---
    ("Room impulse responses for the reverb pack were captured with the swept-sine method rather than MLS; the deconvolution was cleaner and the loudspeaker nonlinearity rejection won it out.", "decision", "technical", False,
     [("Room impulse responses", "concept"), ("swept-sine", "method"), ("MLS", "method"), ("deconvolution", "algorithm")],
     [("swept-sine", "MLS", "PREFERS")],
     "which impulse-response capture method replaced MLS for the reverb pack and which property drove the choice",
     "room impulse response swept sine mls deconvolution loudspeaker nonlinear"),
    # --- 19 fact ---
    ("SoundPipe modules back the physical-modelling voices in the synth; the plain C source inlines cleanly into the JUCE build and keeps the dependency graph flat on embedded targets.", "fact", "technical", False,
     [("SoundPipe", "library"), ("JUCE", "framework")],
     [("JUCE", "SoundPipe", "USES")],
     "which DSP library supplies the synth's physical-modelling voices and how does it integrate with JUCE",
     "soundpipe juce physical modelling synth voice c dependency embedded"),
    # --- 20 preference ---
    ("The patcher UI is prototyped in Max/MSP and mirrored in Pure Data for the free tier; SuperCollider survives as the test-signal generator because its sclang loop scripts are hard to beat.", "preference", "technical", False,
     [("Max/MSP", "tool"), ("Pure Data", "tool"), ("SuperCollider", "tool"), ("sclang", "language")],
     [("Pure Data", "Max/MSP", "RELATED_TO")],
     "which three visual or text patching environments split our prototyping, free-tier, and test-signal roles",
     "max msp pure data supercollider sclang patcher prototype free tier"),
    # --- 21 problem ---
    ("FFTW's threaded plan kept hanging on plugin reload under Ableton because the wisdom file was locked by another plugin instance; switched to per-instance plans with a shared read-only wisdom.", "problem", "technical", False,
     [("FFTW", "library"), ("Ableton", "tool"), ("wisdom file", "config")],
     [("FFTW", "Ableton", "APPLIES_TO")],
     "which FFTW configuration fixed the plugin-reload hang under Ableton caused by a locked wisdom file",
     "fftw ableton wisdom file lock reload hang per instance plan"),
    # --- 22 reference ---
    ("The Julius O Smith CCRMA notes on IIR vs FIR design are our house reference for filter choice; FIR when linear phase matters, IIR when CPU budget is tight and phase drift is acceptable.", "reference", "technical", False,
     [("Julius O Smith", "person"), ("CCRMA", "organization"), ("IIR", "algorithm"), ("FIR", "algorithm"), ("linear phase", "concept")],
     [("IIR", "Julius O Smith", "AUTHORED_BY"), ("FIR", "linear phase", "APPLIES_TO")],
     "which published notes anchor our filter choice and when does each of FIR and IIR win in that framework",
     "julius smith ccrma iir fir linear phase filter design reference"),
    # --- 23 decision ---
    ("Window selection for the spectrogram settled on Blackman over Hann for the analysis view; the lower side-lobes matter more than main-lobe width for the kinds of partials we track.", "decision", "technical", False,
     [("Blackman", "algorithm"), ("Hann", "algorithm"), ("spectrogram", "concept")],
     [("Blackman", "Hann", "PREFERS")],
     "which analysis window replaced Hann for the spectrogram and what spectral property drove the pick",
     "blackman hann spectrogram window side lobe main lobe partial"),
    # --- 24 architecture ---
    ("IPlug2's graphics layer draws the plugin UI and the dsp side reuses our Faust-compiled blocks; no JUCE in this codebase because the team wanted a lighter static binary per plugin.", "architecture", "technical", False,
     [("IPlug2", "framework"), ("Faust", "language"), ("JUCE", "framework")],
     [("IPlug2", "Faust", "USES"), ("IPlug2", "JUCE", "REPLACES")],
     "which plugin framework draws the UI in this codebase and which heavier framework was explicitly avoided",
     "iplug2 faust juce plugin ui static binary lightweight codebase"),
    # --- 25 milestone ---
    ("LV2 port of the reverb landed in the v2.4 release; the turtle manifest and atom event plumbing were the slowest parts, not the audio processing itself.", "milestone", "technical", False,
     [("LV2", "protocol"), ("turtle manifest", "file"), ("atom event", "pattern"), ("v2.4", "date")],
     [("LV2", "turtle manifest", "HAS_PART")],
     "which release introduced the LV2 reverb port and which non-audio plumbing was the slow part",
     "lv2 reverb turtle manifest atom event v2 4 release port"),
    # --- 26 decision ---
    ("JACK stays in the pro build while PipeWire covers the consumer path; pro users tolerate the setup friction for the low-latency graph and PipeWire wasn't quite there on sub-three-millisecond buffers.", "decision", "technical", False,
     [("JACK", "service"), ("PipeWire", "service"), ("pro build", "project"), ("consumer path", "project")],
     [("pro build", "JACK", "USES"), ("consumer path", "PipeWire", "USES")],
     "how do the pro and consumer builds split between JACK and PipeWire and what latency threshold gated the call",
     "jack pipewire pro consumer build latency graph sub three ms"),
    # --- 27 reference ---
    ("Pitch detection on whistled input kept flipping octaves under YIN at low amplitudes; gating the candidate threshold and adding SWIPE as a second opinion cleared the worst of it on our test corpus.", "reference", "technical", False,
     [("YIN", "algorithm"), ("SWIPE", "algorithm"), ("octave", "concept")],
     [("SWIPE", "YIN", "IMPROVES_ON")],
     "which second-opinion pitch algorithm stabilised YIN's octave flips on whistled low-amplitude input",
     "yin swipe pitch octave flip whistle low amplitude threshold"),
    # --- 28 architecture ---
    ("Plugin parameter automation is normalised to a zero-to-one range at the host boundary and mapped into engineering units inside the dsp module; VST3 and AUv3 hosts see the same contract.", "architecture", "technical", False,
     [("VST3", "protocol"), ("AUv3", "protocol"), ("parameter automation", "concept"), ("dsp module", "pattern")],
     [("parameter automation", "VST3", "APPLIES_TO"), ("parameter automation", "AUv3", "APPLIES_TO")],
     "how does the plugin normalise parameter automation at the host boundary across VST3 and AUv3",
     "parameter automation vst3 auv3 host boundary normalise engineering unit"),
    # --- 29 fact ---
    ("Logic Pro stresses the AUv3 validation tool harder than Ableton's VST3 scanner; we gate releases on the auval pass rather than on a clean VST3Validator run.", "fact", "technical", False,
     [("Logic Pro", "tool"), ("Ableton", "tool"), ("AUv3", "protocol"), ("VST3", "protocol"), ("auval", "command"), ("VST3Validator", "command")],
     [("Logic Pro", "auval", "USES")],
     "which host's validation tool gates our plugin releases and how does it compare to VST3Validator",
     "logic pro ableton auv3 vst3 auval validator release gate"),
    # --- 30 decision ---
    ("Chose convolution reverb over algorithmic reverb for the cinema bundle; real rooms sample better on orchestral material than any algorithmic topology we auditioned in the shootout.", "decision", "technical", False,
     [("convolution reverb", "algorithm"), ("algorithmic reverb", "algorithm"), ("cinema bundle", "project")],
     [("convolution reverb", "algorithmic reverb", "PREFERS")],
     "which reverb topology won the cinema-bundle shootout and what kind of material drove the call",
     "convolution reverb algorithmic cinema bundle orchestral shootout"),
    # --- 31 architecture ---
    ("The spectral editor runs an STFT with a Hann window and fifty-percent hop; frame size adapts to transient content by dropping to a shorter window when the flux detector spikes.", "architecture", "technical", False,
     [("STFT", "algorithm"), ("Hann", "algorithm"), ("flux detector", "algorithm"), ("spectral editor", "project")],
     [("STFT", "Hann", "USES"), ("spectral editor", "STFT", "USES")],
     "how does the spectral editor adapt its STFT window size to transient content",
     "stft hann window hop flux detector transient spectral editor"),
    # --- 32 reference ---
    ("Zolzer's DAFX book chapter on phase vocoders is the reference bundled in the onboarding reading list; the transient preservation section saved the time-stretch team a month.", "reference", "technical", False,
     [("Zolzer", "person"), ("DAFX", "publication"), ("phase vocoder", "algorithm"), ("time-stretch", "concept")],
     [("DAFX", "Zolzer", "AUTHORED_BY"), ("phase vocoder", "DAFX", "PUBLISHED_IN")],
     "which DSP book anchors onboarding for the time-stretch team and which chapter saved them most time",
     "zolzer dafx phase vocoder time stretch transient preservation onboarding"),
    # --- 33 problem ---
    ("Rubberband's R3 engine desynced the MIDI clock on long sessions in REAPER; the fix was to anchor the transport query to the host's sample position instead of an internal monotonic clock.", "problem", "technical", False,
     [("Rubberband", "library"), ("REAPER", "tool"), ("MIDI clock", "protocol"), ("sample position", "concept")],
     [("Rubberband", "MIDI clock", "APPLIES_TO")],
     "which transport anchoring change stopped the MIDI-clock drift between Rubberband and REAPER on long sessions",
     "rubberband reaper midi clock desync transport sample position anchor"),
    # --- 34 architecture ---
    ("FFT sizes in the mastering suite are constrained to powers of two between 512 and 8192; KissFFT handles the smaller plans and FFTW takes the large transform the loudness meter needs.", "architecture", "technical", False,
     [("KissFFT", "library"), ("FFTW", "library"), ("mastering suite", "project"), ("loudness meter", "project")],
     [("mastering suite", "KissFFT", "USES"), ("loudness meter", "FFTW", "USES")],
     "how does the mastering suite split FFT work between KissFFT and FFTW across plan sizes",
     "kissfft fftw mastering suite loudness meter fft power two plan"),
    # --- 35 preference ---
    ("The sound designer prefers Pure Data for sketching granular ideas over Max/MSP; the licence and Raspberry Pi target matter more to her than the polished IDE experience.", "preference", "technical", False,
     [("Pure Data", "tool"), ("Max/MSP", "tool"), ("Raspberry Pi", "platform")],
     [("Pure Data", "Max/MSP", "PREFERS"), ("Pure Data", "Raspberry Pi", "DEPLOYED_ON")],
     "which patching environment does the sound designer prefer for granular sketches and what drove it over Max/MSP",
     "pure data max msp raspberry pi granular sketch licence patch"),
    # --- 36 milestone ---
    ("Hit sub-two-millisecond round-trip latency on macOS with Core Audio exclusive mode in the live-performance build; the PipeWire Linux target still sits at four milliseconds end to end.", "milestone", "technical", False,
     [("Core Audio", "api"), ("macOS", "platform"), ("PipeWire", "service"), ("Linux", "platform"), ("live-performance build", "project")],
     [("live-performance build", "Core Audio", "USES")],
     "which round-trip latency did the live-performance build hit on macOS and where does the Linux target sit",
     "core audio macos pipewire linux round trip latency live performance"),
    # --- 37 decision ---
    ("Went with an IIR Linkwitz-Riley crossover instead of a linear-phase FIR for the speaker-management tool; the phase response is acceptable and the latency budget did not have room for an FIR.", "decision", "technical", False,
     [("IIR", "algorithm"), ("Linkwitz-Riley", "algorithm"), ("FIR", "algorithm"), ("speaker-management tool", "project")],
     [("IIR", "FIR", "PREFERS"), ("speaker-management tool", "Linkwitz-Riley", "USES")],
     "which crossover topology beat the FIR option in the speaker-management tool and what constraint drove it",
     "iir linkwitz riley fir crossover speaker management latency phase"),
    # --- 38 fact ---
    ("The host-side MIDI comes in through VST3's note-expression event and AUv3's MIDI-over-property interface; both paths flatten into the same internal event struct before dsp sees it.", "fact", "technical", False,
     [("VST3", "protocol"), ("AUv3", "protocol"), ("MIDI", "protocol"), ("note-expression", "pattern")],
     [("MIDI", "VST3", "APPLIES_TO"), ("MIDI", "AUv3", "APPLIES_TO")],
     "how do VST3 and AUv3 MIDI paths converge inside the plugin before reaching the dsp layer",
     "vst3 auv3 midi note expression property internal event flatten"),
    # --- 39 architecture ---
    ("Impulse-response files are stored as 32-bit float WAV with a sidecar JSON describing capture metadata; the convolution reverb loads the pair atomically or marks the slot unavailable.", "architecture", "technical", False,
     [("convolution reverb", "algorithm"), ("WAV", "file"), ("JSON", "technology"), ("sidecar", "pattern")],
     [("convolution reverb", "WAV", "USES")],
     "how does the convolution reverb pair impulse-response audio with capture metadata on load",
     "impulse response wav float json sidecar metadata atomic load"),
    # --- 40 preference ---
    ("The plugin lead prefers Steinberg VST SDK examples as the starting point for new projects over JUCE tutorials; they map to the real host quirks the SDK documents first-hand.", "preference", "technical", False,
     [("Steinberg VST SDK", "library"), ("JUCE", "framework")],
     [("Steinberg VST SDK", "JUCE", "PREFERS")],
     "which SDK does the plugin lead prefer as a starting reference and what makes it more useful than JUCE tutorials",
     "steinberg vst sdk juce tutorial starting point host quirk"),
    # --- 41 reference ---
    ("The Smith polyphase sample-rate-conversion chapter is bundled with the onboarding doc; reading it explains why we keep a separate set of kernels for integer versus rational ratios.", "reference", "technical", False,
     [("Smith", "person"), ("polyphase", "algorithm"), ("sample-rate-conversion", "concept")],
     [("polyphase", "Smith", "AUTHORED_BY")],
     "which reading anchors onboarding on polyphase sample-rate conversion and which design split does it justify",
     "smith polyphase sample rate conversion integer rational kernel onboarding"),
    # --- 42 milestone ---
    ("The DAW template for REAPER ships with our suite preloaded on the master bus and a dedicated monitor chain; users who install on Logic Pro get an AUv3-flavoured clone generated from the same template.", "milestone", "technical", False,
     [("REAPER", "tool"), ("Logic Pro", "tool"), ("AUv3", "protocol"), ("DAW template", "project")],
     [("DAW template", "REAPER", "APPLIES_TO"), ("DAW template", "Logic Pro", "APPLIES_TO")],
     "how does the DAW template share its structure between REAPER and Logic Pro users",
     "daw template reaper logic pro auv3 master bus monitor chain"),
    # --- 43 decision ---
    ("Stopped shipping the Pure Data patch as a separate product and folded the patch set into the main CMajor library; one build system covers both exports now and the patch authors iterate faster.", "decision", "technical", False,
     [("Pure Data", "tool"), ("CMajor", "language"), ("patch set", "project")],
     [("CMajor", "Pure Data", "REPLACES")],
     "which language absorbed the Pure Data patch set into the main library and what build-system win did it bring",
     "pure data cmajor patch set library build system consolidate"),
    # --- 44 decision ---
    ("VST3 parameter changes arriving off-block caused stair-stepping in the gain smoother; moving to the VST3 parameter-queue model and interpolating within the block removed the artefact.", "decision", "technical", False,
     [("VST3", "protocol"), ("parameter-queue", "pattern"), ("gain smoother", "algorithm")],
     [("parameter-queue", "VST3", "APPLIES_TO")],
     "which VST3 parameter delivery model fixed the stair-stepping artefact in the gain smoother",
     "vst3 parameter queue gain smoother stair step interpolate block"),
    # --- 45 reference ---
    ("The Griffin-Lim paper is still the baseline for magnitude-only resynthesis; our current iteration uses a fast variant but the original is in the onboarding reading list regardless.", "reference", "technical", False,
     [("Griffin-Lim", "algorithm"), ("magnitude-only resynthesis", "concept")],
     [("magnitude-only resynthesis", "Griffin-Lim", "USES")],
     "which algorithm paper remains the baseline for magnitude-only resynthesis in onboarding material",
     "griffin lim magnitude only resynthesis baseline onboarding reading"),
    # --- 46 decision ---
    ("Switched the plugin UI toolkit from a JUCE-native component tree to a skia-based renderer shared with the web preview; design-system parity jumped and one asset pack drives both surfaces.", "decision", "technical", False,
     [("JUCE", "framework"), ("skia", "library"), ("web preview", "project")],
     [("skia", "JUCE", "REPLACES"), ("skia", "web preview", "APPLIES_TO")],
     "which rendering stack replaced JUCE's native component tree in the plugin UI and what parity did it unlock",
     "juce skia web preview plugin ui rendering design system asset"),
    # --- 47 architecture ---
    ("The SuperCollider test rig generates reference sine sweeps into a captive JACK graph; the plugin under test lives on another client and the renderer records both sides for offline analysis.", "architecture", "technical", False,
     [("SuperCollider", "tool"), ("JACK", "service"), ("test rig", "project")],
     [("test rig", "SuperCollider", "USES"), ("test rig", "JACK", "USES")],
     "how does the SuperCollider test rig route reference sweeps into the plugin under test for offline capture",
     "supercollider jack test rig sine sweep plugin under test record"),
    # --- 48 milestone ---
    ("iPlug released the v2 static-binary build on Windows; the plugin dll now weighs under two megabytes and boot time inside a host fell to under fifty milliseconds.", "milestone", "technical", False,
     [("iPlug", "framework"), ("Windows", "platform"), ("dll", "file")],
     [("iPlug", "Windows", "DEPLOYED_ON")],
     "which platform received the iPlug static-binary build and what plugin size and boot time did it hit",
     "iplug v2 static binary windows dll plugin size boot time"),
    # --- 49 milestone ---
    ("First CMajor-to-LV2 export worked end to end on PipeWire; the same patch that ships as VST3 on Windows now loads in Ardour on Linux without any hand-written glue.", "milestone", "technical", False,
     [("CMajor", "language"), ("LV2", "protocol"), ("PipeWire", "service"), ("Ardour", "tool"), ("Linux", "platform")],
     [("CMajor", "LV2", "PRODUCES"), ("Ardour", "LV2", "SUPPORTS")],
     "which end-to-end export proved CMajor's LV2 path on Linux and which host loaded the result",
     "cmajor lv2 pipewire ardour linux export end to end glue free"),
    # --- 50 noise ---
    ("Someone left a post-it on the bathroom mirror quoting a Brian Eno liner note and no one has had the heart to take it down yet.", "fact", "noise", True, [], [], None, None),
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
