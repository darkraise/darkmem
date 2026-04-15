"""One-off emitter for retrieval top-up batch-017 — paraphrase kind, shared rows at line offsets 1600..1699.

Writes 100 rows to data/v2/retrieval/batch_017.tmp.jsonl with ids ret-01601..01700.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_017.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 1600
SHARED_OFFSET = 1600
QUERY_KIND = "paraphrase"

# One query per source row, in the same order as the source rows.
QUERIES: list[str] = [
    # 1601: Bauhaus founded by Walter Gropius in 1919
    "which early twentieth century school fused craft with functional design pedagogy",
    # 1602: Stravinsky Rite of Spring Paris 1913 riot
    "ballet debut that provoked a famous Parisian audience uproar",
    # 1603: Tadao Ando prefers board-formed concrete over ornament
    "material the Japanese architect chooses to highlight light and texture",
    # 1604: Dieter Rams ten principles at Braun
    "German industrial designer's ten heuristics still guiding studios",
    # 1605: Armory Show 1913 New York brought European modernism
    "which exhibit startled American audiences with European avant garde works",
    # 1606: Schenkerian analysis reduces to Ursatz
    "analytical technique reducing tonal pieces to a background structural skeleton",
    # 1607: Sol LeWitt wall drawings via written instructions
    "conceptual artist whose works are executed from written directives",
    # 1608: Brutalism from beton brut, raw concrete
    "postwar architectural movement named after a French phrase for rough concrete",
    # 1609: Clement Greenberg formalism and flatness
    "mid century critic who argued modernist painting should pursue flatness",
    # 1610: noise
    "a brief pause before verifying exhibition dates",
    # 1611: Bridget Riley op-art geometric rules
    "painter whose rule based geometric canvases produce optical vibration",
    # 1612: Memphis Group Milan 1981 Sottsass
    "when and where did the Italian postmodern design collective form",
    # 1613: Steve Reich Music for 18 Musicians 1976
    "landmark piece that codified phase pulse minimalism through chord cycles",
    # 1614: Critical regionalism, Frampton
    "architectural stance grounding buildings in climate topography and local material",
    # 1615: Mono-ha 1960s Japan raw materials
    "late sixties Japanese tendency staging stone steel and wood minimally",
    # 1616: Bach Well-Tempered Clavier 1722 1742
    "keyboard cycle traversing every major and minor key in pairs",
    # 1617: Relational aesthetics Bourriaud 1998
    "French theory recasting art as locus of social encounter",
    # 1618: Eva Hesse latex fibreglass cheesecloth
    "sculptor who embraced fugitive industrial materials to invite decay",
    # 1619: Lina Bo Bardi SESC Pompeia 1986 Sao Paulo
    "Brazilian civic conversion of a factory with board marked concrete towers",
    # 1620: Schoenberg twelve-tone replaces tonal hierarchy
    "serial method that displaced functional tonality using an ordered row",
    # 1621: Arte Povera Celant 1967
    "poor materials movement and its naming manifesto in late sixties Italy",
    # 1622: Kant Critique of Judgment, disinterested pleasure
    "third critique grounding taste on detached pleasure and cognitive free play",
    # 1623: Ligeti Atmospheres 1961 micropolyphony
    "orchestral piece introducing dense cloud like polyphonic textures to audiences",
    # 1624: International Style 1932 MoMA
    "MoMA show that named and codified a pan European modern architecture",
    # 1625: Glenn Murcutt verandahs vs glass facades
    "Australian designer favouring shaded verandahs over sealed glass envelopes",
    # 1626: Pictures Generation New York 1977
    "late seventies cohort appropriating mass media imagery to probe authorship",
    # 1627: Constructivism Rodchenko Tatlin post-1917 Russia
    "Russian avant garde pairing geometric abstraction with socially useful production",
    # 1628: Spectralism Grisey Murail 1970s France
    "French compositional school deriving harmony from analysed sound spectra",
    # 1629: Ulm 1953-1968 extends Bauhaus
    "postwar German school continuing Bauhaus ideals via systems and science",
    # 1630: Metabolism Tokyo 1960
    "when and where the Japanese architectural group treating cities as organisms launched",
    # 1631: Walter Benjamin Work of Art 1935 aura
    "essay linking mechanical reproduction to the loss of artistic aura",
    # 1632: Sonata form exposition development recapitulation
    "classical movement plan hinging on tonal departure and resolving return",
    # 1633: Barcelona Pavilion Mies 1929 travertine onyx
    "year the travertine and onyx modernist pavilion in Catalonia opened",
    # 1634: noise
    "a quick note about verifying attribution records",
    # 1635: This Is Tomorrow Whitechapel 1956
    "London exhibition often cited as the debut of British Pop",
    # 1636: Species counterpoint Fux Gradus 1725
    "eighteenth century treatise formalising graded counterpoint exercises",
    # 1637: Ansel Adams Zone System
    "photographic method dividing tone into numbered zones for exposure planning",
    # 1638: Wolfflin Principles of Art History 1915
    "art history book contrasting Renaissance and Baroque via polar formal pairs",
    # 1639: Crystal Palace Paxton 1851 Great Exhibition
    "London pavilion showcasing modular iron and glass prefabrication at scale",
    # 1640: Documenta Kassel 1955
    "German quinquennial anchoring the contemporary art calendar",
    # 1641: Kahn Salk Institute La Jolla 1965
    "Californian research compound framing a travertine plaza toward the Pacific",
    # 1642: Monteverdi L'Orfeo 1607
    "work commonly treated as the earliest mature opera in modern sense",
    # 1643: Venturi Complexity and Contradiction 1966
    "book that pushed architecture past austere modernism into historical quotation",
    # 1644: Cindy Sherman Untitled Film Stills 1977-1980
    "late seventies series casting its maker as generic cinematic heroines",
    # 1645: Picturesque Uvedale Price 1794 Burke
    "aesthetic category mediating between sublime and beautiful via roughness",
    # 1646: Le Corbusier Villa Savoye 1931 Five Points
    "villa near Paris demonstrating the Swiss architect's five modernist points",
    # 1647: Zaha Hadid parametric curves
    "architect's practice that swapped right angled geometry for algorithmic curves",
    # 1648: Formalism film theory framing editing
    "film theoretic stance weighing technique over story content",
    # 1649: Boulez Le marteau 1955 total serialism
    "fifties chamber showcase of postwar total serialism across parameters",
    # 1650: Aalto Paimio Sanatorium 1933
    "Finnish sanatorium unifying furniture and architecture as a healing environment",
    # 1651: Steam Deck -> Proton-GE for Yakuza
    "compatibility fork that took over the handheld for weekend RPG runs",
    # 1652: SteamOS corrupts exFAT; ROMs on btrfs via CryoUtilities
    "why the retro drive was reformatted for the handheld console",
    # 1653: Steam Family Library shared with Priya in Manchester
    "how the household shares the farming sim across two cities",
    # 1654: PaperMC on Raspberry Pi 5
    "where the household block building server actually runs at home",
    # 1655: Factorio Hetzner dedicated for Diego in Buenos Aires
    "why the automation game moved off peer hosting to a datacenter",
    # 1656: Lichess Stockfish depth 22 on laptop
    "how the Sunday chess review routine flows on the home laptop",
    # 1657: Tabletop Sim + Foundry VTT Thursday, Marco in Milan
    "how the weekly role playing group keeps going when a player is abroad",
    # 1658: Backloggd over Notion CSV 412 titles
    "which service won for tracking completed games after the bulk import",
    # 1659: Project Zomboid Rin Seattle mod curation
    "how the zombie survival install stopped crashing on the big rig",
    # 1660: noise
    "a short aside about fetching a coffee first",
    # 1661: OpenRA via Bottles on Linux with Omar
    "how the classic RTS evenings run on the Linux workstation with a friend",
    # 1662: RetroArch SNES PS1 cores + 8BitDo Kenji player two
    "how Saturday couch co op assigns controllers to the right friend",
    # 1663: EmulationStation + ScreenScraper HTPC
    "which tool made retro library metadata legible on the living room box",
    # 1664: Mumble on VPS replaces Steam Voice Discord Hana
    "why the game night voice chat left mainstream platforms",
    # 1665: Twitch Celeste launch 2026-02-08 from den PC
    "date the weekly platformer broadcast went live from home",
    # 1666: OBS profiles sync via Syncthing to Claire's
    "how streaming scenes travel with me when broadcasting from a friend's house",
    # 1667: Elgato HD60 X for Switch speedrun with Leo
    "reason the capture card was bought and what it records",
    # 1668: Family calendar -> Zapier -> Discord event
    "how the household gaming night gets announced in chat automatically",
    # 1669: Sleeper custom scoring Raj Delhi vs Pacific
    "how the family fantasy league stays fair across time zones",
    # 1670: ROG Ally over Steam Deck for Helldivers 2
    "which handheld won for the co op shooter and the reason",
    # 1671: Playnite green tag + Python SteamDB scrape
    "how the launcher flags handheld compatibility at a glance",
    # 1672: Switch 2 preorder 2026-03-12 Mia Mario Kart
    "when the next generation console launch day racing session locked in",
    # 1673: MO2 replaces Vortex on Steam Deck with Flatseal
    "which mod organiser became reliable for the portable open world title",
    # 1674: Jellyfin hosts Game Grumps with Lina in Lyon
    "where the gaming variety show we watch before tabletop night is stored",
    # 1675: Xbox Cloud Gaming iPad Osaka commute Forza
    "how the racing game continues through quarterly trips to Japan",
    # 1676: noise
    "a brief acknowledgement that the plan makes sense",
    # 1677: Sunshine + Moonlight stream Baldur's Gate to couch tablet for Noa
    "how the party based RPG reaches the couch tablet for a partner to join",
    # 1678: Improved Initiative + Roll20, Freya laptop
    "digital tool replacing paper initiative tracking at the tabletop session",
    # 1679: Pokemon ROM hacks separate collection for Hiro
    "how the retro frontend shields the nine year old from unsafe builds",
    # 1680: Hollow Knight 100% 2026-04-03 HowLongToBeat Go
    "date the metroidvania completion run finished and its logging path",
    # 1681: Tekken 8 tournament fixed by PowerLine Ethernet
    "what cured the competitive fighting game lag in the living room",
    # 1682: Elden Ring Nightreign preorder, Mateo Porto April
    "when the brothers meet up for the souls like co op weekend",
    # 1683: reWASD replaces Steam Input for DualSense Rocket League
    "which utility took over the controller profile after the gyro kept dropping",
    # 1684: Obsidian vault for DnD with Priya Marco Sasha NPC sheet
    "how the campaign crew shares live notes during the weekly session",
    # 1685: Razer Kishi V2 over Backbone for Pixel
    "which mobile controller won for the daily backpack commute",
    # 1686: LAN party Utrecht 2026-10-11 Airbnb Joren
    "when the annual LAN meetup happens and who books the venue",
    # 1687: Flycast replaces Reicast for Dreamcast on Steam Deck
    "which emulator core made the retro console reliable on the handheld",
    # 1688: Sery_Bot Python + Discord webhook for Celeste Friday
    "how the weekly platformer stream handles moderation plus clip sharing",
    # 1689: JKSV on Switch for Animal Crossing backups
    "what utility rescued the family island save from cloud limits",
    # 1690: Stream Deck dedicated page for Amelie intros OBS
    "how co host intros are triggered during the weekly broadcast",
    # 1691: Mumble over Discord for Counter-Strike Opus
    "which voice platform wins for competitive shooter callouts and why",
    # 1692: Yuzu -> Ryujinx on Arch for Zelda shader cache
    "which emulator picked up the adventure replay after the project shut down",
    # 1693: Sleeper NFL league 2026-08-30 cousins Priya Raj Mateo
    "when the family fantasy bracket locks in for the football season",
    # 1694: Shadow of the Colossus PS5 Plex Tdarr h265
    "how console highlight reels get archived into the media library in h265",
    # 1695: DayZ London pod DZSA replaces launcher with Rin mods
    "what combination fixed the survival game desync for the remote pod",
    # 1696: OBS Studio replaces Streamlabs for Apex Legends
    "which broadcaster survived on the rig after the plugin crashes",
    # 1697: GameCube adapter via Delfinovin for Dolphin macOS, Aarav Mumbai
    "how the console adapter finally got recognised on the Apple laptop",
    # 1698: Rocksmith+ next to Focusrite with Noa
    "why the guitar game sits beside the audio interface on the practice desk",
    # 1699: Logitech G Pro X Superlight replaces Zowie for Valorant
    "what hardware swap helped recover rank in the tactical shooter",
    # 1700: Foundry VTT calendar replaces Doodle 2026-01-18 Sasha
    "date the tabletop group retired scheduling polls for weekly sessions",
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    sources = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, (query, src) in enumerate(zip(QUERIES, sources), start=1):
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": src["id"],
                "query": query,
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
