"""One-off emitter for shared-base batch-192 — self-hosted services domain (Nextcloud, Immich, Jellyfin, Authelia, Authentik, Traefik, Caddy, NPM, Portainer, Gitea, Forgejo, Gitlab, Woodpecker, Harbor, Mastodon, Matrix, Kopia, Restic, etc.).

Writes 50 rows to data/v2/shared/batch_192.tmp.jsonl with ids shared-09551..09600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_192.tmp.jsonl"
ID_OFFSET = 9550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 decision ---
    ("Picked Immich over PhotoPrism for the family photo stack; the mobile auto-upload clients and shared-album UX made the pitch, and PhotoPrism's indexer was too heavy on the N100 mini-PC.", "decision", "technical", False,
     [("Immich", "service"), ("PhotoPrism", "service"), ("N100", "platform")],
     [("Immich", "PhotoPrism", "PREFERS")],
     "which photo platform won the family stack decision and which hardware constraint sealed it",
     "immich photoprism family photo n100 mini pc mobile auto upload"),
    # --- 2 architecture ---
    ("Nextcloud runs behind Caddy with the office container split out; Collabora handles the document preview and is wired in via a dedicated subdomain so the WOPI handshake stays clean.", "architecture", "technical", False,
     [("Nextcloud", "service"), ("Caddy", "service"), ("Collabora", "service"), ("WOPI", "protocol")],
     [("Nextcloud", "Caddy", "USES"), ("Nextcloud", "Collabora", "USES")],
     "how is Nextcloud wired to Caddy and Collabora so that document previews work over WOPI",
     "nextcloud caddy collabora wopi subdomain document preview"),
    # --- 3 decision ---
    ("Swapped Nginx Proxy Manager for Traefik on the homelab reverse proxy layer; label-driven routing from the Docker Compose files killed the click-ops maintenance overhead.", "decision", "technical", False,
     [("Nginx Proxy Manager", "service"), ("Traefik", "service"), ("Docker Compose", "tool")],
     [("Traefik", "Nginx Proxy Manager", "REPLACES")],
     "which reverse proxy replaced NPM at home and what workflow benefit made the swap worthwhile",
     "traefik nginx proxy manager label docker compose homelab click ops"),
    # --- 4 architecture ---
    ("Authelia sits in front of Jellyfin and Paperless-ngx as a forward-auth middleware behind Traefik; the TOTP second factor is cached per-session and refresh happens on a ten-minute window.", "architecture", "technical", False,
     [("Authelia", "service"), ("Jellyfin", "service"), ("Paperless-ngx", "service"), ("Traefik", "service"), ("TOTP", "protocol")],
     [("Authelia", "Jellyfin", "APPLIES_TO"), ("Authelia", "Paperless-ngx", "APPLIES_TO"), ("Authelia", "Traefik", "USES")],
     "how does Authelia gate Jellyfin and Paperless behind Traefik and what TOTP refresh window applies",
     "authelia jellyfin paperless traefik forward auth totp session"),
    # --- 5 decision ---
    ("Moved the single-sign-on layer from Authelia to Authentik; the richer LDAP outpost and first-class OIDC provider config for Gitea and Grafana justified the extra memory footprint.", "decision", "technical", False,
     [("Authelia", "service"), ("Authentik", "service"), ("Gitea", "service"), ("Grafana", "service"), ("LDAP", "protocol"), ("OIDC", "protocol")],
     [("Authentik", "Authelia", "REPLACES"), ("Authentik", "Gitea", "APPLIES_TO")],
     "which SSO stack replaced Authelia and what LDAP and OIDC features drove the migration",
     "authentik authelia ldap oidc outpost gitea grafana sso"),
    # --- 6 milestone ---
    ("Finished the Forgejo migration off self-hosted Gitlab CE last weekend; runner count went from four flaky Gitlab Runners to two Woodpecker workers with the same throughput.", "milestone", "technical", False,
     [("Forgejo", "service"), ("Gitlab CE", "service"), ("Gitlab Runner", "service"), ("Woodpecker", "service")],
     [("Forgejo", "Gitlab CE", "REPLACES"), ("Woodpecker", "Gitlab Runner", "REPLACES")],
     "which git forge and CI stack replaced Gitlab CE and how did the runner count shift",
     "forgejo gitlab ce migration woodpecker runner ci weekend"),
    # --- 7 fact ---
    ("Kopia handles the nightly laptop backups into Backblaze B2 with content-addressed chunks; the repository password lives in the KeePass vault and nowhere else.", "fact", "technical", False,
     [("Kopia", "service"), ("Backblaze B2", "service"), ("KeePass", "tool")],
     [("Kopia", "Backblaze B2", "USES")],
     "which backup tool pushes nightly laptop snapshots to Backblaze and where is its repository password",
     "kopia backblaze b2 laptop backup content addressed keepass password"),
    # --- 8 preference ---
    ("I prefer Restic over Duplicati for server-side backups; the single static binary and the pruning semantics are easier to reason about on a hands-off schedule.", "preference", "technical", False,
     [("Restic", "service"), ("Duplicati", "service")],
     [("Restic", "Duplicati", "PREFERS")],
     "which server backup tool do I prefer and what operational properties drive the preference",
     "restic duplicati server backup static binary prune schedule"),
    # --- 9 architecture ---
    ("Gitea runs with a dedicated Postgres sidecar and a Harbor registry next door; CI pushes from Woodpecker authenticate against Harbor with a per-project robot account scoped to push-only.", "architecture", "technical", False,
     [("Gitea", "service"), ("Postgres", "database"), ("Harbor", "service"), ("Woodpecker", "service")],
     [("Gitea", "Postgres", "USES"), ("Woodpecker", "Harbor", "USES")],
     "how is Gitea wired to Postgres and Harbor and how does Woodpecker CI authenticate to the registry",
     "gitea postgres harbor woodpecker robot account push scope"),
    # --- 10 noise ---
    ("The cat knocked over my coffee onto the keyboard drawer and the spacebar still sticks a week later.", "fact", "noise", True, [], [], None, None),
    # --- 11 decision ---
    ("Chose Ollama over LocalAI for the homelab inference layer; the model pull workflow is friction-free and OpenWebUI pairs with it natively over the OpenAI-compatible endpoint.", "decision", "technical", False,
     [("Ollama", "service"), ("LocalAI", "service"), ("OpenWebUI", "service")],
     [("Ollama", "LocalAI", "PREFERS"), ("OpenWebUI", "Ollama", "USES")],
     "which local LLM server won the homelab choice and how does OpenWebUI connect to it",
     "ollama localai openwebui homelab model pull openai compatible"),
    # --- 12 architecture ---
    ("Paperless-ngx consumes from a Syncthing-shared inbox folder; the scanner dumps PDFs into the shared directory, Syncthing replicates them, and the consumer runs OCR through Tesseract.", "architecture", "technical", False,
     [("Paperless-ngx", "service"), ("Syncthing", "service"), ("Tesseract", "tool"), ("PDF", "file")],
     [("Paperless-ngx", "Syncthing", "USES"), ("Paperless-ngx", "Tesseract", "USES")],
     "how does Paperless ingest scanned PDFs from the scanner and where does OCR happen",
     "paperless syncthing tesseract pdf scanner ocr inbox consume"),
    # --- 13 fact ---
    ("Jellyfin transcodes hardware-accelerated on the Intel N100 through Quick Sync; HEVC 10-bit plays without fan spin-up and the CPU stays under twenty percent during simultaneous 4K streams.", "fact", "technical", False,
     [("Jellyfin", "service"), ("N100", "platform"), ("Quick Sync", "tool"), ("HEVC", "technology")],
     [("Jellyfin", "Quick Sync", "USES")],
     "how does Jellyfin transcode 4K HEVC on the N100 without the fans ramping up",
     "jellyfin n100 quick sync hevc 10 bit transcode 4k fan"),
    # --- 14 decision ---
    ("Dropped Plex in favour of Jellyfin for the media stack; the Plex cloud-dependency after the sign-in changes and the looming pass costs weren't defensible for a local-first library.", "decision", "technical", False,
     [("Plex", "service"), ("Jellyfin", "service")],
     [("Jellyfin", "Plex", "REPLACES")],
     "which media server replaced Plex for the local library and what issues pushed the move",
     "jellyfin plex media server local first cloud sign in pass"),
    # --- 15 problem ---
    ("Matrix Synapse was eating 3 GB of resident memory on a small homeserver; migrated to Conduit and watched it settle under 180 MB with the same federation load.", "problem", "technical", False,
     [("Matrix", "protocol"), ("Synapse", "service"), ("Conduit", "service")],
     [("Conduit", "Synapse", "REPLACES")],
     "which Matrix server replaced Synapse to shrink the memory footprint and how far did it drop",
     "matrix synapse conduit memory 3gb federation small homeserver"),
    # --- 16 architecture ---
    ("Mastodon runs split across web, streaming, and sidekiq services in Docker Compose; Redis backs both the cache and the sidekiq queue while Postgres holds the timeline store.", "architecture", "technical", False,
     [("Mastodon", "service"), ("sidekiq", "service"), ("Redis", "database"), ("Postgres", "database"), ("Docker Compose", "tool")],
     [("Mastodon", "Redis", "USES"), ("Mastodon", "Postgres", "USES")],
     "how is Mastodon decomposed in Compose and which data services back cache queue and timelines",
     "mastodon docker compose sidekiq redis postgres streaming web"),
    # --- 17 fact ---
    ("Lemmy instance sits behind Caddy with a cap of fifty registered users; the federation fan-out keeps the feed alive even though the local community is tiny.", "fact", "technical", False,
     [("Lemmy", "service"), ("Caddy", "service")],
     [("Lemmy", "Caddy", "USES")],
     "how does the small Lemmy instance stay useful despite only fifty registered local users",
     "lemmy caddy fifty user federation fan out local community"),
    # --- 18 reference ---
    ("Portainer runs on the primary Docker host with an agent on each secondary node; the environment endpoints are documented in the homelab wiki under Infra > Container Fleet.", "reference", "technical", False,
     [("Portainer", "service"), ("Docker", "tool")],
     [("Portainer", "Docker", "USES")],
     "where is the Portainer fleet topology documented and which endpoints does the primary host manage",
     "portainer docker agent secondary node homelab wiki container fleet"),
    # --- 19 decision ---
    ("Adopted Komodo alongside Portainer for GitOps-style deploys; Portainer kept the dashboard role while Komodo drives the compose stack syncs from the Gitea repo.", "decision", "technical", False,
     [("Komodo", "service"), ("Portainer", "service"), ("Gitea", "service")],
     [("Komodo", "Gitea", "USES")],
     "how is Komodo paired with Portainer for GitOps deploys and which repo drives the compose sync",
     "komodo portainer gitops gitea compose stack sync dashboard"),
    # --- 20 architecture ---
    ("Keycloak runs as the identity provider for work-adjacent services with a Postgres backend; realms are split between staff and public federations and token lifetime is twelve hours for SSO.", "architecture", "technical", False,
     [("Keycloak", "service"), ("Postgres", "database"), ("SSO", "concept")],
     [("Keycloak", "Postgres", "USES")],
     "how are Keycloak realms split and what token lifetime governs SSO for work-adjacent services",
     "keycloak postgres realm staff public token lifetime twelve hours"),
    # --- 21 milestone ---
    ("Firefly III import of five years of bank CSVs finished on Sunday; the rules engine categorised about ninety-four percent of the two thousand imported transactions automatically.", "milestone", "personal", False,
     [("Firefly III", "service")],
     [],
     "when did the multi-year bank import into Firefly finish and how much auto-categorised",
     "firefly iii bank csv import rules engine categorise sunday"),
    # --- 22 preference ---
    ("I prefer Actual Budget's envelope model over Firefly III for monthly planning; Firefly stays the system of record for historical reporting but day-to-day budgeting lives in Actual.", "preference", "personal", False,
     [("Actual Budget", "service"), ("Firefly III", "service")],
     [("Actual Budget", "Firefly III", "PREFERS")],
     "which budgeting tool do I prefer day to day and which one holds historical reporting",
     "actual budget firefly iii envelope monthly plan historical"),
    # --- 23 architecture ---
    ("Seafile replaced the previous Nextcloud Files folder for large binary syncs; the chunked block store handles VM images and Blender project folders that Nextcloud struggled with above 20 GB.", "architecture", "technical", False,
     [("Seafile", "service"), ("Nextcloud", "service"), ("VM", "concept"), ("Blender", "tool")],
     [("Seafile", "Nextcloud", "REPLACES")],
     "which file sync tool took over from Nextcloud Files for large binaries and what payloads drove the switch",
     "seafile nextcloud chunk block vm blender 20gb large binary"),
    # --- 24 fact ---
    ("Syncthing keeps the Obsidian vault mirrored across three devices with send-receive folders on each; versioning is staggered trash so accidental deletes are recoverable for thirty days.", "fact", "personal", False,
     [("Syncthing", "service"), ("Obsidian", "tool")],
     [("Syncthing", "Obsidian", "APPLIES_TO")],
     "how does Syncthing mirror the Obsidian vault across devices and what recovery window covers accidental deletes",
     "syncthing obsidian vault three device send receive staggered trash"),
    # --- 25 decision ---
    ("Bookstack is the team knowledge base instead of Wiki.js or Outline; the book-chapter-page hierarchy maps onto existing mental models and the markdown editor handles technical write-ups fine.", "decision", "technical", False,
     [("Bookstack", "service"), ("Wiki.js", "service"), ("Outline", "service")],
     [("Bookstack", "Wiki.js", "PREFERS"), ("Bookstack", "Outline", "PREFERS")],
     "which knowledge base won over Wiki.js and Outline and which structural model made the call",
     "bookstack wiki js outline book chapter page markdown team kb"),
    # --- 26 preference ---
    ("I prefer Joplin Server over Standard Notes for the encrypted note sync; Joplin Server runs behind Traefik and the clients do the E2EE locally so the server only sees ciphertext.", "preference", "technical", False,
     [("Joplin Server", "service"), ("Standard Notes", "service"), ("Traefik", "service"), ("E2EE", "concept")],
     [("Joplin Server", "Standard Notes", "PREFERS"), ("Joplin Server", "Traefik", "USES")],
     "which encrypted note sync do I prefer over Standard Notes and where does the end-to-end encryption happen",
     "joplin server standard notes traefik e2ee ciphertext prefer"),
    # --- 27 fact ---
    ("Vikunja is the self-hosted task tracker for the household; recurring chores live in shared lists and reminders fire into the Matrix room rather than via SMTP to avoid email noise.", "fact", "personal", False,
     [("Vikunja", "service"), ("Matrix", "protocol"), ("SMTP", "protocol")],
     [("Vikunja", "Matrix", "USES")],
     "which task tracker runs the household chores and where do reminders surface to avoid email noise",
     "vikunja matrix smtp chore household task shared list reminder"),
    # --- 28 problem ---
    ("Verdaccio storage ballooned past 30 GB because of an unchecked max-age on tarballs; tuned the storage config to expire old prereleases after ninety days and the repo size fell by sixty percent.", "problem", "technical", False,
     [("Verdaccio", "service"), ("tarball", "file"), ("prerelease", "concept")],
     [],
     "which Verdaccio setting let storage balloon to 30 GB and what tuning cut the repo size back down",
     "verdaccio tarball max age prerelease expire ninety days size"),
    # --- 29 decision ---
    ("Chose Caddy over Traefik for the public-facing sidecar; automatic HTTPS and file-based config won over label-driven routing for the two services the household actually exposes to the internet.", "decision", "technical", False,
     [("Caddy", "service"), ("Traefik", "service"), ("HTTPS", "protocol")],
     [("Caddy", "Traefik", "PREFERS")],
     "which reverse proxy got picked for the public sidecar and what simplicity argument drove it",
     "caddy traefik public sidecar automatic https file config label"),
    # --- 30 decision ---
    ("Enabled Trivy scanning on every Harbor push for the homelab registry; images that fail the critical-severity gate get quarantined rather than promoted to the stable repository, and the policy won over a sidecar Clair deployment.", "decision", "technical", False,
     [("Harbor", "service"), ("Trivy", "tool"), ("Clair", "tool"), ("stable repository", "concept")],
     [("Harbor", "Trivy", "USES"), ("Trivy", "Clair", "PREFERS")],
     "which Harbor scanner policy got picked over Clair and how does it gate promotion to stable",
     "harbor trivy clair scan critical severity quarantine stable"),
    # --- 31 reference ---
    ("The Ollama model catalogue and their pinned tags live in the ansible-homelab repo under roles/ollama/defaults/main.yml; bump the tag there and a re-run does the pull.", "reference", "technical", False,
     [("Ollama", "service"), ("ansible-homelab", "project"), ("main.yml", "file")],
     [],
     "where is the Ollama model catalogue with pinned tags and how does a re-run update the running container",
     "ollama ansible homelab role defaults main yml tag pull pin"),
    # --- 32 milestone ---
    ("Mastodon timeline backfill from the old Pleroma instance wrapped on Tuesday; followers reconciled over eighteen hours and the old instance went into tombstone mode after migration.", "milestone", "technical", False,
     [("Mastodon", "service"), ("Pleroma", "service")],
     [("Mastodon", "Pleroma", "REPLACES")],
     "when did the Mastodon migration off Pleroma complete and how long did the follower reconcile take",
     "mastodon pleroma migration tuesday follower reconcile tombstone"),
    # --- 33 problem ---
    ("Immich ML container was OOM-killed under two concurrent smart-search scans; pinned the Transformers model cache to a host volume and lowered the worker concurrency to fix it.", "problem", "technical", False,
     [("Immich", "service"), ("Transformers", "library"), ("worker concurrency", "config")],
     [],
     "which Immich container kept OOM-killing and what configuration change stabilised smart search",
     "immich ml oom transformers model cache worker concurrency smart"),
    # --- 34 architecture ---
    ("Nightly Restic snapshots push to both Backblaze B2 and a local NAS; the dual-destination policy guards against a single-target outage and Restic's deduplication makes the local copy cheap.", "architecture", "technical", False,
     [("Restic", "service"), ("Backblaze B2", "service"), ("NAS", "platform")],
     [("Restic", "Backblaze B2", "USES"), ("Restic", "NAS", "USES")],
     "which dual-destination strategy does Restic use and why is the local NAS copy cheap to maintain",
     "restic backblaze b2 nas dual destination dedupe nightly outage"),
    # --- 35 decision ---
    ("Woodpecker CI stays on SQLite for the homelab; the Postgres swap offered no throughput win at the current three-runner scale and SQLite's backup is just a file copy.", "decision", "technical", False,
     [("Woodpecker", "service"), ("SQLite", "database"), ("Postgres", "database")],
     [("SQLite", "Postgres", "PREFERS")],
     "which Woodpecker backend survived at homelab scale and why was the Postgres swap rejected",
     "woodpecker sqlite postgres homelab three runner backup file copy"),
    # --- 36 fact ---
    ("OpenWebUI is configured with three personas mapped to different Ollama models: a coder on qwen2.5-coder, a writer on llama3.1, and a quick-answer default on phi3.", "fact", "technical", False,
     [("OpenWebUI", "service"), ("Ollama", "service"), ("qwen2.5-coder", "technology"), ("llama3.1", "technology"), ("phi3", "technology")],
     [("OpenWebUI", "Ollama", "USES")],
     "which three persona models are wired into OpenWebUI against Ollama and what is each used for",
     "openwebui ollama persona qwen coder llama writer phi3 default"),
    # --- 37 milestone ---
    ("Wiki.js 3 beta got pulled out after the markdown renderer ate an hour of notes; rolled back to Wiki.js 2.5 stable and froze upgrades until the stable 3.x cut.", "milestone", "technical", False,
     [("Wiki.js", "service")],
     [],
     "why was the Wiki.js 3 beta rolled back and what upgrade policy followed",
     "wiki js three beta markdown renderer rollback 2 5 stable"),
    # --- 38 architecture ---
    ("Photo library ingestion in Immich uses an external library mount rather than copy-on-upload; the source tree on the NAS is the single canonical location and Immich only indexes pointers.", "architecture", "technical", False,
     [("Immich", "service"), ("NAS", "platform"), ("external library", "pattern")],
     [("Immich", "NAS", "USES")],
     "how does Immich ingest the photo library without duplicating files off the NAS",
     "immich external library nas canonical location index pointer"),
    # --- 39 decision ---
    ("Dropped Duplicati after a corrupted-database recovery took six hours; switched all laptop endpoints to Kopia and the same dataset restored in under forty minutes on the test run.", "decision", "technical", False,
     [("Duplicati", "service"), ("Kopia", "service")],
     [("Kopia", "Duplicati", "REPLACES")],
     "which backup tool replaced Duplicati after a painful recovery and what restore speedup did the test show",
     "duplicati kopia corrupt database recovery laptop restore forty"),
    # --- 40 preference ---
    ("I prefer Forgejo over stock Gitea now that the governance split is settled; the release cadence and community patches land faster and the migration was a drop-in on the same data directory.", "preference", "technical", False,
     [("Forgejo", "service"), ("Gitea", "service")],
     [("Forgejo", "Gitea", "PREFERS")],
     "which self-hosted forge do I prefer after the governance split and how smooth was the migration",
     "forgejo gitea governance split release cadence drop in migration"),
    # --- 41 milestone ---
    ("Finished wiring the Authentik OpenLDAP outpost into both Jellyfin and Paperless-ngx last Thursday; the outpost runs in a separate container and the group mapping now controls access at the application level.", "milestone", "technical", False,
     [("Authentik", "service"), ("OpenLDAP", "service"), ("Jellyfin", "service"), ("Paperless-ngx", "service")],
     [("Authentik", "OpenLDAP", "USES"), ("Authentik", "Jellyfin", "APPLIES_TO"), ("Authentik", "Paperless-ngx", "APPLIES_TO")],
     "when did the Authentik LDAP outpost integration with Jellyfin and Paperless finish and what does group mapping control",
     "authentik openldap outpost jellyfin paperless group map thursday"),
    # --- 42 reference ---
    ("The homelab backup matrix — which services map to Kopia, which map to Restic, and which are snapshot-only on ZFS — lives in docs/homelab/backup-matrix.md in the infra repo.", "reference", "technical", False,
     [("Kopia", "service"), ("Restic", "service"), ("ZFS", "technology"), ("backup-matrix.md", "file")],
     [],
     "where is the service-to-backup-tool matrix documented for the homelab and what three paths does it cover",
     "homelab backup matrix kopia restic zfs snapshot docs infra"),
    # --- 43 noise ---
    ("The neighbour's chicken coop renovation took three weekends and the rooster still crows at 04:30 every morning.", "fact", "noise", True, [], [], None, None),
    # --- 44 decision ---
    ("LocalAI got retired from the homelab; Ollama covered the same workloads with less memory pressure and the OpenAI-compatible endpoint was identical for the downstream apps.", "decision", "technical", False,
     [("LocalAI", "service"), ("Ollama", "service")],
     [("Ollama", "LocalAI", "REPLACES")],
     "why was LocalAI retired from the homelab and what drop-in replaced it for the downstream apps",
     "localai ollama retire memory openai compatible downstream app"),
    # --- 45 fact ---
    ("Gitlab CE on the homelab consumed about 4 GB of RAM at idle with only two active projects; the workload never justified the footprint compared to the Forgejo alternative.", "fact", "technical", False,
     [("Gitlab CE", "service"), ("Forgejo", "service")],
     [],
     "how much RAM did idle Gitlab CE take at homelab scale and what alternative made more sense",
     "gitlab ce 4gb idle ram two project homelab forgejo footprint"),
    # --- 46 reference ---
    ("Matrix bridges run as separate containers per protocol: mautrix-whatsapp, mautrix-telegram, and heisenbridge for IRC all talk to the Conduit homeserver over the appservice API, and the compose file lives in infra/matrix/docker-compose.yml.", "reference", "technical", False,
     [("Matrix", "protocol"), ("mautrix-whatsapp", "service"), ("mautrix-telegram", "service"), ("heisenbridge", "service"), ("Conduit", "service"), ("IRC", "protocol")],
     [("mautrix-whatsapp", "Conduit", "USES"), ("mautrix-telegram", "Conduit", "USES"), ("heisenbridge", "Conduit", "USES")],
     "which Matrix bridges run alongside Conduit and how do they attach to the homeserver",
     "matrix mautrix whatsapp telegram heisenbridge irc conduit appservice"),
    # --- 47 milestone ---
    ("Cutover from Gitlab Runner to Woodpecker agents finished without a broken pipeline; the three production pipelines ported in a single evening and the runner fleet shrank from four to two.", "milestone", "technical", False,
     [("Gitlab Runner", "service"), ("Woodpecker", "service")],
     [("Woodpecker", "Gitlab Runner", "REPLACES")],
     "how did the Gitlab Runner to Woodpecker cutover land and how much did the runner fleet shrink",
     "gitlab runner woodpecker agent cutover pipeline three production"),
    # --- 48 reference ---
    ("The Authentik flow configuration for MFA enrollment and recovery is exported into config/authentik/flows/ in the infra repo; re-apply via the blueprint mechanism on each deploy.", "reference", "technical", False,
     [("Authentik", "service"), ("MFA", "concept"), ("blueprint", "pattern")],
     [],
     "where do the Authentik MFA enrollment and recovery flows live and how are they reapplied on deploy",
     "authentik flow mfa enrollment recovery config blueprint infra"),
    # --- 49 milestone ---
    ("Nextcloud 28 upgrade finally landed without blocking on an app compatibility issue; the Collabora integration stayed working and the Files client did not need a resync on any device.", "milestone", "technical", False,
     [("Nextcloud", "service"), ("Collabora", "service")],
     [("Nextcloud", "Collabora", "USES")],
     "which Nextcloud major upgrade landed cleanly and what usually fragile integration kept working",
     "nextcloud 28 upgrade collabora app compatibility files client"),
    # --- 50 reference ---
    ("Traefik dynamic config lives under /etc/traefik/dynamic/ and is mounted read-only into the container; label-driven rules on Docker services take precedence when both paths define the same router.", "reference", "technical", False,
     [("Traefik", "service"), ("Docker", "tool")],
     [("Traefik", "Docker", "USES")],
     "where does Traefik read its dynamic file config and which rules win when labels and files overlap",
     "traefik dynamic config etc label docker precedence router"),
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
