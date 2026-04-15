"""One-off emitter for retrieval top-up batch-018 — acronym-kind queries slice.

Writes 100 rows to data/v2/retrieval/batch_018.tmp.jsonl with ids ret-01701..01800.
Each row references a source row in shared.jsonl at lines SHARED_OFFSET+1..SHARED_OFFSET+100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_018.tmp.jsonl"
ID_OFFSET = 1700
SHARED_OFFSET = 1700
QUERY_KIND = "acronym"

QUERIES: list[str] = [
    # 1701 Bitwig Studio over Cubase for Tuesday writing w/ Mateo
    "which DAW took over Tue co-writing sesh w/ Mateo and why",
    # 1702 UA Apollo Twin X handles home demos; Unison preamp + SM7B over Scarlett
    "UA Apollo Twin X over Scarlett for home demos; Unison pre flatters SM7B",
    # 1703 Plexamp iPad streams FLAC off Synology NAS for Priya
    "Plexamp iPad streams FLAC off NAS for Priya's album picks",
    # 1704 Riverside.fm replaced Zencastr on Slow Circuit pod after ep 14 Neha
    "Riverside.fm over Zencastr for SC pod after Neha's ep 14 upload glitch",
    # 1705 commute playlist Python script Last.fm scrobbles -> Tidal mix on Pixel
    "Mon Py script pulls Last.fm scrobbles and pushes Tidal mix to the Pixel",
    # 1706 Genelec 8030C beat KRK Rokit 5 A/B test, sub-60Hz REW
    "Genelec 8030C won A/B vs KRK in treated office once REW flagged sub-60 Hz ring",
    # 1707 Project Debut Carbon + Scarlett 2i2 into Audacity, RX Elements declick
    "vinyl rip via Debut Carbon into 2i2 + Audacity; iZotope RX declick pass",
    # 1708 Descript Overdub tricked Lena; show-notes disclaimer re AI voice
    "Descript Overdub fooled Lena; show-notes now flag AI VO patches",
    # 1709 Hindenburg Pro over Adobe Audition for oral-history; auto-leveller
    "Hindenburg Pro over AA for oral-history proj because auto-level handles grandma's voice",
    # 1710 noise — grabbing headphones
    "1 sec lemme grab my cans real quick",
    # 1711 Sonos Era 300 Dolby Atmos Music from Amazon Music; Play:1 + HA
    "kitchen Era 300 plays Atmos via AM while Play:1 handles HA announcements",
    # 1712 2026-03-08 Ghost Ledger EP basement via Reason 12 on M2 Mac mini w/ Robbie
    "2026-03-08 Ghost Ledger EP tracked in Reason 12 on M2 mini w/ Robbie on drums",
    # 1713 Intellijel Metropolix heart of modular; Elektron Digitakt for samples
    "Intellijel Metropolix runs the bedroom modular; Digitakt owns the DT sample duties",
    # 1714 Overcast over Apple Podcasts; Smart Speed saves 40 min Thu commute
    "Overcast over AP on the phone; Smart Speed claws back ~40 min on Thu commute",
    # 1715 Traktor Pro 3 loses sync w/ Kontrol S4 MK3 when USB hub shared w/ webcam
    "Traktor Pro 3 loses sync w/ S4 MK3 on a shared USB hub",
    # 1716 Neumann KM184 pair + Zoom F3 to cabin for Ana's ambient EP
    "Neumann KM184 pair + Zoom F3 hauled to cabin for Ana's ambient EP creek recs",
    # 1717 Pro Tools HDX at Dad's studio stayed on macOS Ventura; Avid drivers
    "PT HDX at Dad's studio pinned to macOS Ventura; Avid drivers never stable on Sonoma",
    # 1718 FabFilter Pro-Q 4 replaced iZotope Neutron on mastering bus; Sam's single
    "FF Pro-Q 4 over Neutron on master bus for Sam's indie single",
    # 1719 Nebula Genes + Lo-Fi Girl radio for focus; Apple Classical for journalling
    "Nebula Genes + LFG radio for focus sessions vs Apple Classical for journalling",
    # 1720 Whisper large-v3 on RTX 4070 transcribed 17h Grandpa tapes to Markdown
    "Whisper large-v3 on RTX 4070 turned 17 hr of Grandpa's tapes into MD archive",
    # 1721 Rekordbox library rebuilds from Tidal playlist Priya shares Fri; wedding USB
    "Rekordbox lib auto-rebuilds from Priya's Fri Tidal PL for wedding warmup USB",
    # 1722 Sennheiser HD 660S2 over HD 600 for mixing; low end matches Genelecs
    "HD 660S2 over HD 600 for mixing; LF finally matches the Genelecs",
    # 1723 AntennaPod on GrapheneOS; OPML feed in Nextcloud across devices
    "AntennaPod on GOS phone keeps feed OPML in NC so devices share ep state",
    # 1724 Moog Matriarch midi clock confused Ableton Link; Fri jam w/ Theo
    "Moog Matriarch MIDI clock broke Ableton Link at Fri jam w/ Theo",
    # 1725 Plexamp SuperSonic blends Last.fm history w/ Leila's family ratings
    "Plexamp SuperSonic blends L.fm history w/ Leila's fam PL ratings for commute",
    # 1726 noise — will circle back
    "sure, will CB after this call",
    # 1727 Rode NT1 5th Gen in closet booth; 32-bit float so Yuki could yell
    "Rode NT1 5G in closet booth; 32-bit float let Yuki belt the bridge clip-free",
    # 1728 Neural DSP Quad Cortex over Kemper on road; captures share to Dropbox
    "NDSP Quad Cortex over Kemper on tour because the capture lib shares via DB",
    # 1729 Riverside.fm over Zoom H6 local backup; 2026-02-12 dbl-ender save
    "Riverside.fm over Zoom H6 local BU after the 2026-02-12 double-ender save",
    # 1730 Make Noise Morphagene loops for Aisha's meditation app; kitchen whiteboard
    "MN Morphagene loops feed Aisha's meditation app demo; patch on kitchen WB",
    # 1731 Focal Clear MG over Audeze LCD-X for late-night mixing; neck strain
    "Focal Clear MG over LCD-X for late-night mixing chair; LCD planar weight killed neck",
    # 1732 Splice Sounds auto-tags into Ableton Live 12 via Hazel rule; Fri beat sprint
    "Splice subs auto-tag into Ableton L12 browser via a Hazel rule for Fri BM sprint",
    # 1733 Pocket Casts Plus on 2026-01-19 flight; Rosa kids & Planet Money
    "PC Plus paid off on the 2026-01-19 flight: Planet Money offline saved Rosa's kids",
    # 1734 Acapella iOS app multitracks David's barbershop quartet to iCloud
    "Acapella iOS multitracks David's BS quartet to iCloud so LP mixdown takes 10 min",
    # 1735 Qobuz hi-res replaces Bandcamp fallback when wife plugs DAC to living-room amp
    "Qobuz hi-res over BC fallback only when the DAC is direct into LR amp",
    # 1736 Thin Blue Tape cassette run on 2026-02-28 via NAC on Otari MX-5050 in Denver
    "Thin Blue Tape cassette run 2026-02-28 via NAC dubs cut on Otari MX-5050 in Denver",
    # 1737 Mackie ProFX12v3 -> Behringer X32 Compact; USB recording stems for Javier
    "rehearsal desk: ProFX12v3 swapped for X32 Compact so band stems hit USB for Javier",
    # 1738 Roon ARC streams Nucleus over Tailscale to Lisbon rental; no port-fwd
    "Roon ARC streams Nucleus lib over TS to Lisbon flat w/o touching router port-fwd",
    # 1739 Boulder Recording Club podcast moved from Libsyn to Transistor; Chartable
    "BRC pod feed left Libsyn for Transistor after Chartable analytics mismatch",
    # 1740 TR-8S clock drift vs MPC Live II; MPC as master, Korg SQ-1 for Jess patterns
    "TR-8S clock tamed vs MPC Live II; SQ-1 for Jess's gen patterns",
    # 1741 Flask dashboard on home server tracking Plex minutes; Mateo Radiohead flag
    "tiny Flask dash on HS tracks fam Plex min and flags Mateo's Radiohead replays",
    # 1742 SoundID Reference cal file on Focal Solo6 Be; Eva moved couch
    "SoundID Ref cal file re-saved for Solo6 Be after Eva shifted LR couch 2 ft",
    # 1743 Whisper Substack on 2026-03-22 summarises Decoder eps for Tomas
    "Whisper-powered SS newsletter shipped 2026-03-22 summarising Decoder eps for Tomas",
    # 1744 Boss RC-600 looper; MIDI footswitch bank for acoustic loop w/ Clara on Zoom
    "Boss RC-600 pulled for Zoom loop sessions w/ Clara; MIDI FS bank beats a laptop",
    # 1745 Audirvana Studio on Mac Studio beat Foobar2000 on Win NUC for Chen listening
    "Audirvana on Mac Studio > Foobar2000 on Win NUC for DSOTM gapless",
    # 1746 GoldenEar BRX bookshelves over Wharfedale Linton; Cambridge CXA81 rack
    "GE BRX bookshelves replaced the Wharfedale Lintons next to the Cambridge CXA81",
    # 1747 Ardour rehearsal session on Debian mini PC in church basement for Father Liam
    "Ardour choir session on Debian mini PC so Father Liam records w/o an eng",
    # 1748 MainStage replaced Yamaha MODX rig for Uncle Dev's church services; iPad patches
    "MainStage over MODX for Uncle Dev's 9 AM services; iPad patches beat MODX boot time",
    # 1749 Waveform Pro export crash w/ Melda plugin chain >8 on vocal bus; Nora
    "WF Pro crashes on export when Melda chain on vox bus > 8",
    # 1750 HA automation dims Hue strip when Denon DP-300F starts spinning; Fri w/ Amaya
    "HA automation dims Hue behind TT when Denon DP-300F spins w/ Amaya",
    # 1751 Jekyll -> Astro for personal blog; MDX component story for longform
    "blog migration from Jekyll to Astro once MDX story made DS essays easier",
    # 1752 Ghost over Substack on Tue newsletter; Ghost on Hetzner VPS
    "Ghost over SS for Tue newsletter; self-hosted Ghost on Hetzner VPS owns the list",
    # 1753 novel manuscript in private Git; MD per chapter; Pandoc -> ePub for beta
    "novel MS in private Git, one MD per chapter; Pandoc spits ePub for beta readers",
    # 1754 Scrivener -> iA Writer on MacBook Air past 80 scenes
    "iA Writer over Scrivener on the MBA once outline passed 80 scenes",
    # 1755 Substack archive -> Hugo site via tiny Python exporter for climate essays
    "SS archive feeds a Hugo site via a Py exporter for non-SS readers",
    # 1756 noise — pull that up
    "1 sec lemme pull that up real quick",
    # 1757 Giscus on Astro blog; comments in same GH Discussions thread as repo issues
    "Giscus wired to Astro blog so comments live in the same GH Discussions as issues",
    # 1758 Plausible replaced GA on writing site; cookie banner
    "Plausible over GA on writing site; cookie banner scared off target readers",
    # 1759 dictation: Whisper on MacBook -> LanguageTool -> Obsidian drafts
    "dictation: Whisper on MB -> LT -> MD drop into Obsidian drafts",
    # 1760 Cold Turkey Blocker locks socials weekends for Patreon short-story arc
    "CTB blocks social all wknd so the current Patreon SS arc ships on time",
    # 1761 Eleventy + Decap CMS on Netlify; Git repo source
    "11ty + Decap CMS gave spouse a Netlify admin while site still builds from Git",
    # 1762 2026-03-22 KDP launch failed preflight; embedded TTF in ePub
    "2026-03-22 KDP launch failed preflight — embedded TTF in ePub broke Amazon's validator",
    # 1763 Zola poetry site swapped for hand-rolled theme; Katex for concrete poetry
    "Zola theme on poetry site swapped for hand-rolled after author notes needed KaTeX",
    # 1764 BookFunnel ARC delivery for next thriller; Mailchimp list never sees ePub
    "BookFunnel handles ARC delivery so MC list never sees the raw ePub for next thriller",
    # 1765 Hemingway Editor over LanguageTool for final polish; subordinate clauses
    "Hemingway Editor over LT for final polish; para readability flags my worst sub-clauses",
    # 1766 self-hosted WordPress on DO droplet powers food blog; ACF custom fields
    "self-hosted WP on DO droplet stays for food blog; ACF beats any SSG",
    # 1767 Registrar moved from GoDaddy to Porkbun on 2026-01-18; whois privacy + DNS API
    "registrar moved GoDaddy -> Porkbun 2026-01-18; whois priv free + DNS API scriptable",
    # 1768 FocusWriter full-screen + Yeti mic in spare room for podcast scripts
    "FW full-screen + Yeti mic turned spare rm into a podcast-script studio",
    # 1769 GH Action builds Beehiiv digest Thu from RSS; MJML formatting
    "GHA builds the Beehiiv digest every Thu from RSS and formats as MJML",
    # 1770 TinaCMS upgrade silently dropped draft entries for interview series
    "TinaCMS upgrade silently dropped draft entries before Mon publish for the IS series",
    # 1771 Patreon restructure 2026-02-09; novella to 10-USD patrons; world-building to 5-USD
    "2026-02-09 Patreon tier restructure: monthly novella -> 10-USD tier, WB notes -> 5-USD",
    # 1772 Simple Analytics over Plausible on author site; GDPR referrer breakdown
    "Simple Analytics over Plausible on author site because the GDPR referrer bd pleased the LA",
    # 1773 shared novella project w/ Malia on HackMD for co-edit; not VS Code Live Share
    "novella co-writing w/ Malia on HackMD for live MD edit instead of VS Code LS",
    # 1774 Cusdis beat Disqus for minimalist tech blog; tracking scripts
    "Cusdis over Disqus on the minimalist tech blog because the privacy promise mattered",
    # 1775 Notion accountability template w/ Cron webhooks auto-posts missed sessions
    "Notion accountability template w/ cron webhooks auto-posts misses to the small DS",
    # 1776 Freedom app blocks Twitter weekday AMs for book-two revisions
    "Freedom schedule blocks TW weekday AMs so book-two revisions stop losing 2 hr/day",
    # 1777 Ulysses on iPad Pro travel drafting; Scrivener on Windows desktop; iCloud
    "Ulysses on iPad Pro for travel drafts; Scrivener on desktop Win; iCloud sync holds",
    # 1778 Aeon Timeline hooked to trilogy Scrivener project; 100-year backstory
    "Aeon Timeline hooked to trilogy Scriv proj so the 100-yr family BS stops drifting",
    # 1779 2026-04-05 indie novella via Draft2Digital over KDP Select; Kobo + Apple Books
    "2026-04-05 novella via D2D over KDP Select because Kobo + AB reach > KU royalties",
    # 1780 beta reader feedback in Google Docs suggestion mode; PDF annotations unreconciled
    "beta reader fb moved to GDoc suggestion mode after PDF annot chaos across 12 readers",
    # 1781 Kafka Castle essay 50k readers after HN front page 2026-03-11; Plausible graph
    "Plausible spike on Kafka Castle essay after HN FP'd the Astro post on 2026-03-11",
    # 1782 Drafts app on iPhone over FocusWriter for first drafts; Siri dictation
    "Drafts on iPhone over FW on desktop for 1st drafts; Siri V2T fastest",
    # 1783 reader Sofia Buenos Aires flagged Astro theme footnote dialog VoiceOver iOS
    "Sofia in BA flagged a11y bug: Astro theme hid FN dialog from VO iOS",
    # 1784 2026-04-12 webserial 100th chapter on Royal Road; Ghost mirror site
    "2026-04-12 serial milestone: 100th ch on RR while the personal Ghost mirror stayed current",
    # 1785 Amazon KDP monthly CSV into DuckDB queried via Quarto notebook for royalties
    "KDP monthly CSV dumped into a DuckDB file + Quarto nb cleared up royalty confusion",
    # 1786 Obsidian Publish replaced custom Docusaurus for world-building wiki; rename breakage
    "Obs Publish replaced custom Docusaurus WB wiki because internal links broke on rename",
    # 1787 ConvertKit + Zapier + LanguageTool auto-welcome letter to essay subscribers
    "CK wired through a Zap to a LT-checked welcome letter for every new essay sub",
    # 1788 Hugo site deploy moved Netlify -> Cloudflare Pages 2026-02-28; build minutes
    "Hugo site deploy moved Netlify -> CF Pages on 2026-02-28 after build-min ceiling kept tripping",
    # 1789 Editor Priya Mumbai wants romance MS as Docx track changes; Scrivener compile notes
    "editor Priya in Mum wants romance MS as Docx w/ TC; Scriv notes died",
    # 1790 Calibre library + Python script keeps ARC metadata consistent across 3 distributors
    "Calibre lib + a little Py script keeps ARC meta consistent across 3 distribution uploads",
    # 1791 Shiki at build time on eng blog; Monokai theme matches headshot
    "eng blog code snippets run through Shiki at build; Monokai theme matches author HS",
    # 1792 Patreon tiers map to GitHub Sponsors tiers via Go webhook; OSS vs fiction overlap
    "Patreon tiers mapped to GH Sponsors via Go webhook; OSS vs fic readers",
    # 1793 Plottr -> Markdown board in Obsidian for epic fantasy trilogy outline
    "epic fantasy outline moved Plottr -> MD board in Obs; beats export manual",
    # 1794 2026-03-02 MC newsletter landed in Gmail Promotions spam
    "2026-03-02 MC newsletter send skipped Gmail Promo-safe preview; 40% hit spam",
    # 1795 R Markdown reading-diary PDF zine emailed to mother-in-law Haruko
    "R Markdown pipeline turns reading diary into PDF zine for MIL Haruko",
    # 1796 Grammarly stayed on corp-comms but pulled off fiction laptop; tone homogenising
    "Grammarly kept on corp-comms acct; pulled off fiction laptop; tone homogenised VO",
    # 1797 Backblaze B2 bucket nightly via Restic; 2024 SSD corruption
    "novel repo backed to B2 bucket nightly via Restic after 2024 SSD corrupt Scriv loss",
    # 1798 poetry chapbook launch 2026-04-02 Nix-built Pandoc; Mixam PDF + Gumroad ePub
    "2026-04-02 poetry chapbook via Nix-built Pandoc: print-ready PDF for Mixam + reflow ePub for GR",
    # 1799 Typora over Obsidian for plain-prose op-eds w/o PKM cross-links
    "Typora over Obs for plain-prose op-ed when the piece has no PKM cross-links",
    # 1800 2026-04-10 SS note about hardcover tipped Kaito Osaka into second pre-order
    "2026-04-10 SS note on upcoming HC got Kaito in OSK to pre-order 2nd copy",
]


def emit() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with SHARED_PATH.open("r", encoding="utf-8") as f:
        source_lines = f.readlines()

    rows = []
    for i, query in enumerate(QUERIES):
        shared_line_idx = SHARED_OFFSET + i
        source_row = json.loads(source_lines[shared_line_idx])
        source_id = source_row["id"]
        positive = source_row["text"]

        row_id = f"ret-{ID_OFFSET + i + 1:05d}"
        rows.append({
            "id": row_id,
            "source_id": source_id,
            "query": query,
            "positive": positive,
            "query_kind": QUERY_KIND,
        })

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
