"""Retrieval top-up batch-010: code-switch queries over shared rows 900..999."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_010.tmp.jsonl"
ID_OFFSET = 900
SHARED_OFFSET = 900
QUERY_KIND = "code-switch"

# 100 code-switch queries, rotating across Spanish (es), French (fr), German (de),
# Japanese romaji (ja), Vietnamese (vi), Portuguese (pt), Mandarin pinyin (zh),
# Hindi romanised (hi), Korean romanised (ko). English technical/proper nouns preserved.
QUERIES: list[str] = [
    # 900 es
    "por qué cambiamos del Paprika recipe binder al Mealie con Diego en Linux",
    # 901 fr
    "comment AnyList synchronise la grocery list entre iPhone et Android de Mara",
    # 902 de
    "warum hat Copilot Money das YNAB joint budgeting mit Olivia ersetzt",
    # 903 ja
    "doushite 1Password families ga Bitwarden yori streaming credentials sharing ni ii no",
    # 904 vi
    "chia sẻ Apple Family calendar với Tomas cho pediatrician visits trên Outlook",
    # 905 pt
    "como o Readwise Reader encaminha New Yorker clippings da tia Rita para o Notion",
    # 906 zh pinyin
    "weishenme yong Immich on home server daitì Google Photos gei Grandma",
    # 907 hi
    "hamne Pi-hole kyun lagaya Raspberry Pi 5 par Sunday dinner ke video calls ke liye",
    # 908 ko
    "wae Monarch Money ro Wells Fargo accounts reul Julia daeshboard e tonghabhaesseo",
    # 909 es (noise row)
    "dame un momentito, déjame pensar that for a second",
    # 910 fr
    "comment Bear notes sur iPad et Mac de Kenji restent sync via iCloud Drive",
    # 911 de
    "wie teilt Fastmail calendar den CalDAV link mit Gabrielas Thunderbird für vet visits",
    # 912 ja
    "naze toddler no story archive wo Kobo ni kaeta, Farah no Kindle library no mondai de",
    # 913 vi
    "Photoprism trên attic NAS lưu trữ Christmas photos với face tags như thế nào",
    # 914 pt
    "como o Aqara Smart Lock deixa a faxineira Valentina entrar nos weekdays das 9 ao meio-dia",
    # 915 zh pinyin
    "Eufy doorbell retention weishenme jianshao dao seven days, Sofia shuo le shenme",
    # 916 hi
    "mera buzurg neighbour Henryk ko kaunsa MedMinder Telegram reminder milta hai rozana",
    # 917 ko
    "Lunch Money ga Priyanka ui freelance invoices reul eotteoke categorise hae 2026 tax",
    # 918 es
    "desde cuándo uso Todoist shared projects con mi madre para grocery runs",
    # 919 fr
    "comment le Synology family share a survécu à la power surge grâce à l'UPS de Wojtek",
    # 920 de
    "wie wird die Plex library jeden Sunday zu Backblaze B2 für Julios cinema gesichert",
    # 921 ja
    "Getting Things Done by David Allen ga OmniFocus no household retreat agenda ni dou eikyou",
    # 922 vi
    "Home Assistant thông báo qua Sonos lúc washing machine finishes cho Elena như thế nào",
    # 923 pt
    "por que voltei pro Gmail depois do Superhuman não deixar Raya compartilhar filter set",
    # 924 zh pinyin
    "Proton Drive shang de One Medical vault zenme baoguan kids vaccination records",
    # 925 es (noise)
    "déjame double-check that figure before responding, un segundo",
    # 926 fr
    "pourquoi Cozi Gold calendar préfère coloured tags plus que Google Calendar pour Linas dance",
    # 927 de
    "wie pipet Plan to Eat die week's ingredients jeden Thursday in Instacart für Leo",
    # 928 ja
    "Skylight frame ga Mirabel no boarding school kara no photos wo rotate suru houhou",
    # 929 vi
    "Bitwarden Emergency Access cho em trai Ethan được cấp vào ngày nào cho estate paperwork",
    # 930 pt
    "como o Tailscale Funnel expõe Mylio Photos só pra tia Beatriz sem cloud account",
    # 931 zh pinyin
    "weishenme Marco bu xihuan Goodreads de Amazon data policy, huan cheng Storygraph",
    # 932 hi
    "Alexa routines ne baby Aurora ko 3 AM par kyun jagaya, Home Assistant automation ki galti",
    # 933 ko
    "Karin gwa na neun wae Proton Calendar reul Fastmail boda menstrual tracker ro gollasseo",
    # 934 es
    "cómo el Matter integration del Hatch Rest encajó con la hora de preschool de Sienna",
    # 935 fr
    "pourquoi on a migré le wedding RSVP vers Airtable pour la tia de Mariana sur Dell",
    # 936 de
    "wo liegt das shared financial playbook von Francesca vor purchases über 2000 euros",
    # 937 ja
    "Atomic Habits no implementation intention ga Rafael no Sunday chore ni dou tsukawareru",
    # 938 vi
    "AnyList grocery list tự động generate từ Mealie recipe tags vì Rowan ghét staples",
    # 939 pt
    "por que o Kagi family plan substituiu DuckDuckGo em five household devices da Alina",
    # 940 zh pinyin
    "Signal shang de neighborhood bill-split bot shi shenme shihou qidong, lawn-care fund",
    # 941 hi
    "Matter-over-Thread bulbs nursery mein Zigbee se behtar kyun hain, Bastian ne kya kaha",
    # 942 ko
    "Deep Work ui shutdown complete 5 PM gaenyeom i eotteoke Karolinarel Slack buteo makasseo",
    # 943 es
    "por qué Beeper Desktop junta WhatsApp Telegram y Signal threads con Abuela",
    # 944 fr
    "pourquoi j'ai self-hosted Actual Budget sur Mini PC après Intuit shut Mint down",
    # 945 de
    "wie wird das Pinboard archive von Tomikos knitting patterns jedes Christmas als Zine exportiert",
    # 946 ja
    "Quad9 DNS swap ga Babcia no iPad no phishing popups wo tomeru made no relief",
    # 947 vi
    "mua Yubikey 5C NFC ở Reykjavik ngày nào trong 2026-03-17 trip với Nils",
    # 948 pt
    "como o Immich upload do Pixel da Genoveva alimenta o timeline no Apple TV",
    # 949 zh pinyin
    "2026-04-09 household retro weishenme jueding Beancount bi Monarch geng shihe Alba",
    # 950 hi
    "Polar H10 heart-rate straps cycling workouts ko Golang ingester mein kaise bhejte hain InfluxDB",
    # 951 ko
    "jumal home-brewing Belgian dubbel i ESP32 sensor node ro fermentation gravity reul dashboard e",
    # 952 es
    "por qué cambié Capture One a darktable después del problema de licencia en Linux studio",
    # 953 fr
    "pourquoi OrcaSlicer a remplacé PrusaSlicer pour les Bambu X1C profiles sur le 3D printing",
    # 954 de
    "wie treibt der Arduino Mega im model-train club die zwölf servo turnouts an der benchwork",
    # 955 ja
    "amateur radio no doyoubi wa GQRX to HackRF One de 40-metre band wo tuned suru",
    # 956 vi
    "điểm board-game night được capture trong BGStats rồi sync sang Supabase cho Elo recap như nào",
    # 957 pt
    "como o fantasy football draft prep usa Jupyter notebook pra puxar Sleeper API aos domingos",
    # 958 zh pinyin
    "houyuan weather monitoring yong Ecowitt GW2000 zenme lianjie Weewx zai Raspberry Pi 4",
    # 959 hi (noise)
    "ek second ruko, main woh information abhi pull up karta hoon",
    # 960 ko
    "music production jeonyeok e wae Reaper reul Logic Pro boda seontaekhae ReaScript MIDI routing",
    # 961 es
    "el film scanning workflow subió de Plustek 8200i al Epson V850 por qué el throughput",
    # 962 fr
    "comment la bird-detection camera BirdNET-Pi sur Orange Pi 5 me ping pour le pileated woodpecker",
    # 963 de
    "wann hat die Lattice climbing training app das paper logbook nach dem ersten V6 ersetzt",
    # 964 ja
    "music collecting de Beets library ga NAS no CD rips wo tag shite Navidrome ni watasu",
    # 965 vi
    "chess analysis trên Lichess dùng Stockfish 16 binary pinned depth 22 cho overnight reviews",
    # 966 pt
    "por que o retro gaming mudou do RetroArch no laptop pra MiSTer FPGA na prateleira CRT",
    # 967 zh pinyin
    "huayuan chuanganqi wangluo yong liu ge Zigbee soil probes zai Home Assistant shang zenme zhuizong",
    # 968 hi
    "Strava segment chasing ab Wahoo Elemnt Roam GPX files se kyun pull hoti hai, old Garmin chhoda",
    # 969 ko
    "wedding hobby gig yong euro Lightroom i RawTherapee reul Fuji face tagging ro daechaehaesseo",
    # 970 es
    "por qué el birthday marathon goal se movió al 2026-09-12 según Whoop recovery",
    # 971 fr
    "comment le homelab media stack sur Proxmox VM améliore l'ancien Kodi avec Jellyfin",
    # 972 de
    "wie wurde das ham radio logbook auf SQLite mit Syncthing zwischen den laptops migriert",
    # 973 ja
    "PrusaSlicer profile fix ga 3D printing enclosure no nozzle clog wo 2026-03-29 ni naosu made",
    # 974 vi
    "The Art of Electronics của Horowitz và Hill đọc trước bench session cứu ESP32 như thế nào",
    # 975 es (noise)
    "dame un minuto mientras pull up el documento",
    # 976 fr
    "comment le backyard astrophotography pipeline va d'ASIAIR à PixInsight puis Flickr le dimanche",
    # 977 de
    "wie wurde der Rodecaster Pro 2 für das local history podcasting im Keller eingerichtet",
    # 978 ja
    "hiking trip planning wa Gaia GPS kara CalTopo ni naze kawatta, winter couloir no slope-angle",
    # 979 vi
    "MuseScore 4 render violin arrangement cho recital của cháu gái ngày nào và export MIDI",
    # 980 pt
    "quando o bouldering strength block terminou e o hangboard PR entrou no Crimpd",
    # 981 zh pinyin
    "Dungeons and Dragons campaign notes zenme fang zai Obsidian vaults bing yong Git tongbu",
    # 982 hi
    "custom Strava clone ka FastAPI backend aur SolidJS dashboard Fly.io par kaise deploy hua",
    # 983 ko
    "trail-running jung Suunto Wing bone-conduction headset i AirPods boda wae deo joha situational awareness",
    # 984 es
    "cómo el Bluesound Node mejora sobre el Squeezebox con Roon para el vinyl rip library",
    # 985 fr
    "comment la trail camera dans les bois utilise YOLO-v8 sur Jetson Nano pour taguer les deer",
    # 986 de
    "warum ist mein kayaking log book zu Paddle Logger gewechselt nach Notion route map problemen",
    # 987 ja
    "coffee roasting no Artisan ga Phidget thermocouple curve wo yomi Google Sheet ni export",
    # 988 vi
    "pinball restoration project sửa Williams Funhouse Sound Board vào 2026-01-30 với Pinscore kit",
    # 989 pt
    "por que o SDR++ melhora o SDR# pra garage amateur radio com o upconverter no Linux mini PC",
    # 990 zh pinyin
    "music production rig shang Ableton Live zenme 2026-03-14 bengkui le Focusrite Scarlett USB 3",
    # 991 hi
    "gardening irrigation ko Rachio 3 controllers se kab rebuild karna hai, summer 2026 se pehle",
    # 992 ko
    "Zen Mind Beginners Mind eul ilgeun hu aikido dojo yeonseub i eotteoke bakkwieosseo",
    # 993 es
    "por qué el woodworking shop notebook pasó de index cards a Notion con los router table plans",
    # 994 fr
    "comment mes mountain biking GPX files deviennent un yearly heatmap via Rust CLI sur Tracestrack",
    # 995 de
    "warum verlassen sich meine fly fishing notes mehr auf Troutbitten als Orvis nach zwei seasons tippet",
    # 996 ja
    "fantasy baseball draft spreadsheet ga Google Sheets de FanGraphs projections wo Apps Script de maiban",
    # 997 vi
    "BoardGameGeek tracker build trên Airtable base cũ với Hono API mới và Turso SQLite store",
    # 998 pt
    "quando o birding life list atingiu 300 species e o Merlin confirmou o vesper sparrow",
    # 999 es
    "por qué la frustration del 3D printing con OctoPrint webcam en Ender 3 se arregló con powered USB hub",
]


def load_shared() -> list[dict]:
    with SHARED.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"
    for q in QUERIES:
        wc = len(q.split())
        if not (5 <= wc <= 20):
            raise ValueError(f"query word count {wc} out of 5..20: {q!r}")

    rows = load_shared()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i in range(100):
            src = rows[SHARED_OFFSET + i]
            new_id = f"ret-{ID_OFFSET + i + 1:05d}"
            record = {
                "id": new_id,
                "source_id": src["id"],
                "query": QUERIES[i],
                "positive": src["text"],
                "query_kind": QUERY_KIND,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    print(f"wrote {written} rows to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
