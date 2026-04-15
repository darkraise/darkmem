"""One-off emitter for shared-base batch-137 — cross domain.

Slice: personal writing and blogging meets tech (publishing software, static
site generators, newsletter tooling, RSS rituals, indie-web). Writes 50 rows
to data/v2/shared/batch_137.tmp.jsonl with ids shared-06801..06850. The main
session aggregates the tmp file into shared.jsonl after validation.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_137.tmp.jsonl"
ID_OFFSET = 6800

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the personal blog from WordPress to Ghost self-hosted on a Hetzner box on 2026-02-08 because the newsletter-plus-blog combo meant paying for both WordPress and Mailchimp otherwise.", "milestone", "cross", False,
     [("WordPress", "service"), ("Ghost", "service"), ("Hetzner", "organization"), ("2026-02-08", "date"), ("Mailchimp", "service")],
     [("Ghost", "WordPress", "REPLACES")],
     "when did the personal blog move off WordPress and what pushed it",
     "blog platform migration self hosted newsletter combined tooling cost"),
    # --- 2 ---
    ("Prefers Ghost self-hosted over Ghost Pro because the 9-dollar Hetzner CX22 handles the current 1800 subscribers fine and the Pro plan jumps to 25 dollars a month for the same seat count.", "preference", "cross", False,
     [("Ghost", "service"), ("Hetzner", "organization"), ("CX22", "infrastructure")],
     [("Ghost", "Hetzner", "DEPLOYED_ON")],
     "why is the Ghost install self-hosted instead of on the managed plan",
     "self hosted versus managed ghost pro subscriber count VPS cost"),
    # --- 3 ---
    ("The Astro 5.2 rebuild replaced the Gatsby 4 personal site on 2026-03-14 after the Gatsby build times on Netlify crept past seven minutes and MDX hot-reload broke under Node 20.", "decision", "cross", False,
     [("Astro", "library"), ("Gatsby", "library"), ("2026-03-14", "date"), ("Netlify", "service"), ("MDX", "language"), ("Node", "platform")],
     [("Astro", "Gatsby", "REPLACES")],
     "when did the static site move off Gatsby and what triggered the rewrite",
     "static site generator migration build time hot reload node upgrade"),
    # --- 4 ---
    ("Beehiiv replaced Substack on 2026-01-19 for the weekly letter because Substack's recommendations network stopped working once the politics channel got too noisy and the CSV export wouldn't bring subscriber tags.", "milestone", "cross", False,
     [("Beehiiv", "service"), ("Substack", "service"), ("2026-01-19", "date"), ("CSV", "concept")],
     [("Beehiiv", "Substack", "REPLACES")],
     "when did the newsletter leave Substack and what was the breaking point",
     "newsletter migration platform recommendations network subscriber tags"),
    # --- 5 ---
    ("Utterances replaced Disqus on the Hugo site on 2026-02-22 because the Disqus tracker was adding 340 KB to every post and the Lighthouse privacy audit kept screaming about the ad network.", "decision", "cross", False,
     [("Utterances", "service"), ("Disqus", "service"), ("Hugo", "library"), ("2026-02-22", "date"), ("Lighthouse", "tool")],
     [("Utterances", "Disqus", "REPLACES")],
     "why did the blog comments move off Disqus and onto Utterances",
     "comments system privacy third party tracker page weight lighthouse"),
    # --- 6. noise ---
    ("Let me pull up the relevant material.", "fact", "noise", True, [], [], None, None),
    # --- 7 ---
    ("Cloudflare Pages replaced Netlify for the Hugo deployment on 2026-03-01 once Netlify's egress charges on the 100 GB bandwidth tier pushed the monthly cost past 19 dollars.", "decision", "cross", False,
     [("Cloudflare Pages", "service"), ("Netlify", "service"), ("Hugo", "library"), ("2026-03-01", "date")],
     [("Cloudflare Pages", "Netlify", "REPLACES")],
     "why did the Hugo site's hosting move from Netlify to Cloudflare Pages",
     "static host migration egress bandwidth pricing free tier comparison"),
    # --- 8 ---
    ("The Eleventy starter from Zach Leatherman's v3 template powers the link blog because the filter pipeline for RSS-to-post conversion fits cleanly in the _data layer.", "architecture", "cross", False,
     [("Eleventy", "library"), ("Zach Leatherman", "person"), ("RSS", "protocol")],
     [("Eleventy", "RSS", "USES")],
     "which static generator powers the link blog and why was it chosen",
     "eleventy starter template link blog RSS feed ingestion data pipeline"),
    # --- 9 ---
    ("Buttondown replaced Revue when Twitter killed Revue on 2023-01-18, and the archive CSV imported cleanly into Buttondown's subscriber list without the double-opt-in reset.", "milestone", "cross", False,
     [("Buttondown", "service"), ("Revue", "service"), ("Twitter", "service"), ("2023-01-18", "date"), ("CSV", "concept")],
     [("Buttondown", "Revue", "REPLACES")],
     "when did the newsletter leave Revue and how did the list transfer go",
     "newsletter migration revue shutdown archive import double opt in"),
    # --- 10 ---
    ("Inoreader's rules engine tags every post from Simon Willison's feed with a read-later flag that syncs through the Pocket integration overnight.", "architecture", "cross", False,
     [("Inoreader", "service"), ("Simon Willison", "person"), ("Pocket", "service")],
     [("Inoreader", "Pocket", "COMMUNICATES_WITH")],
     "how do new posts from specific authors reach the read-later queue",
     "rss reader rule tag filter read later integration overnight sync"),
    # --- 11 ---
    ("NetNewsWire replaced Reeder 5 as the daily feed reader on 2026-02-11 because iCloud Drive sync between the M4 Mac mini and the iPad Pro stopped dropping the starred state.", "decision", "cross", False,
     [("NetNewsWire", "tool"), ("Reeder 5", "tool"), ("2026-02-11", "date"), ("iCloud Drive", "service"), ("M4 Mac mini", "infrastructure"), ("iPad Pro", "infrastructure")],
     [("NetNewsWire", "Reeder 5", "REPLACES"), ("NetNewsWire", "iCloud Drive", "USES")],
     "when did the feed reader swap and which sync issue forced it",
     "rss client swap icloud sync starred state devices desktop tablet"),
    # --- 12 ---
    ("Moved the personal domain DNS from Google Domains to Cloudflare on 2024-09-07 after Google sold the registrar to Squarespace and the renewal emails started pitching Squarespace sites.", "milestone", "cross", False,
     [("Google Domains", "service"), ("Cloudflare", "service"), ("2024-09-07", "date"), ("Squarespace", "service"), ("DNS", "protocol")],
     [("Cloudflare", "Google Domains", "REPLACES")],
     "when did the personal domain leave Google and end up at Cloudflare",
     "domain registrar migration acquisition DNS transfer renewal cycle"),
    # --- 13 ---
    ("Micro.blog posts cross-post to the Mastodon account via the built-in ActivityPub bridge, so the short-form writing reaches both readerships without running a separate Mastodon server.", "architecture", "cross", False,
     [("Micro.blog", "service"), ("Mastodon", "service"), ("ActivityPub", "protocol")],
     [("Micro.blog", "ActivityPub", "USES"), ("Micro.blog", "Mastodon", "COMMUNICATES_WITH")],
     "how does the short-form writing reach both Micro.blog readers and Mastodon",
     "short form crosspost activitypub bridge fediverse readership single source"),
    # --- 14 ---
    ("Frustration flared when the Jekyll 4.3 build broke under GitHub Pages' pinned Ruby 2.7 on 2026-02-03, forcing the site to move to GitHub Actions with a custom workflow.", "problem", "cross", False,
     [("Frustration", "emotion"), ("Jekyll", "library"), ("GitHub Pages", "service"), ("Ruby", "language"), ("2026-02-03", "date"), ("GitHub Actions", "service")],
     [("GitHub Actions", "GitHub Pages", "REPLACES")],
     "what forced the Jekyll site off the default GitHub Pages build in February",
     "jekyll pinned ruby version github pages actions workflow migration"),
    # --- 15 ---
    ("Prefers Hugo over Eleventy for the main essay site because the 800-post archive builds in 1.2 seconds on Hugo and the 11ty pipeline was clocking 14 seconds even with incremental mode.", "preference", "cross", False,
     [("Hugo", "library"), ("Eleventy", "library")],
     [("Hugo", "Eleventy", "PREFERS")],
     "which static generator wins for the big essay archive and why",
     "static site generator build speed large archive incremental mode bench"),
    # --- 16 ---
    ("The h-card on the homepage follows the IndieWebCamp 2024 microformats spec so the Webmentions from Brid.gy actually link back to the right author profile.", "architecture", "cross", False,
     [("h-card", "pattern"), ("IndieWebCamp", "organization"), ("Webmentions", "protocol"), ("Brid.gy", "service")],
     [("Brid.gy", "Webmentions", "USES")],
     "how do incoming Webmentions know which author profile to attribute to",
     "indieweb microformats h card webmention attribution author profile"),
    # --- 17 ---
    ("Vercel replaced Cloudflare Pages for the Next.js portfolio on 2026-01-04 because the incremental static regeneration hooks needed the Vercel-specific edge runtime to stay under 200ms.", "decision", "cross", False,
     [("Vercel", "service"), ("Cloudflare Pages", "service"), ("Next.js", "library"), ("2026-01-04", "date")],
     [("Vercel", "Cloudflare Pages", "REPLACES")],
     "why did the Next.js portfolio move from Cloudflare Pages to Vercel",
     "next js hosting swap incremental static regeneration edge runtime latency"),
    # --- 18 ---
    ("The writing-streak on 750words rolled past 180 days on 2026-03-22 and the morning dump is now where the weekly essay ideas surface before they hit the Ghost drafts folder.", "milestone", "cross", False,
     [("750words", "service"), ("2026-03-22", "date"), ("Ghost", "service")],
     [("750words", "Ghost", "COMMUNICATES_WITH")],
     "when did the morning writing streak cross 180 days and how does it feed the blog",
     "morning pages streak idea capture essay pipeline draft handoff"),
    # --- 19 ---
    ("Cactus Comments replaced Utterances on 2026-03-18 because anonymous readers could never log in through the GitHub flow and the Matrix-backed threads actually land anonymous replies.", "decision", "cross", False,
     [("Cactus Comments", "service"), ("Utterances", "service"), ("2026-03-18", "date"), ("GitHub", "service"), ("Matrix", "protocol")],
     [("Cactus Comments", "Utterances", "REPLACES")],
     "which comments system took over for Utterances and why",
     "comments migration anonymous reply matrix backed login friction"),
    # --- 20 ---
    ("Curiosity hit when Robb Knight's post on 2026-02-27 walked through running a personal Micropub endpoint on Val Town and the whole indie-web posting flow suddenly felt approachable.", "reference", "cross", False,
     [("Curiosity", "emotion"), ("Robb Knight", "person"), ("2026-02-27", "date"), ("Micropub", "protocol"), ("Val Town", "service")],
     [("Val Town", "Micropub", "USES")],
     "which blog post demystified running a personal Micropub endpoint",
     "indieweb micropub server serverless val town personal publishing walkthrough"),
    # --- 21 ---
    ("The Buttondown API key lives in the Ghost webhook so a new essay in Ghost pushes a draft issue into Buttondown automatically without copy-pasting the HTML body.", "architecture", "cross", False,
     [("Buttondown", "service"), ("Ghost", "service"), ("HTML", "language")],
     [("Ghost", "Buttondown", "COMMUNICATES_WITH")],
     "how does a new Ghost essay become a Buttondown draft without manual copy",
     "webhook integration newsletter draft automation cross platform handoff"),
    # --- 22 ---
    ("Prefers Feedbin over Inoreader for the paid tier because Feedbin's newsletter-to-RSS mailbox catches the Substacks that refuse to expose a clean RSS feed.", "preference", "cross", False,
     [("Feedbin", "service"), ("Inoreader", "service"), ("Substack", "service"), ("RSS", "protocol")],
     [("Feedbin", "Inoreader", "PREFERS")],
     "which paid RSS reader wins for pulling in locked-down newsletters",
     "rss paid tier newsletter email address trick substack feed gap"),
    # --- 23 ---
    ("The Fathom Analytics instance replaced Plausible on 2026-03-09 because the lifetime pricing deal closed before Plausible's subscription bumped from 9 to 14 dollars a month.", "decision", "cross", False,
     [("Fathom Analytics", "service"), ("Plausible", "service"), ("2026-03-09", "date")],
     [("Fathom Analytics", "Plausible", "REPLACES")],
     "why did the blog analytics swap from Plausible to Fathom in early March",
     "privacy analytics swap lifetime deal subscription price increase"),
    # --- 24 ---
    ("Joy surged when the first Webmention from Kev Quirk's post actually rendered under the essay with the right avatar on 2026-02-19 after a whole weekend of debugging the h-entry markup.", "milestone", "cross", False,
     [("Joy", "emotion"), ("Webmention", "protocol"), ("Kev Quirk", "person"), ("2026-02-19", "date"), ("h-entry", "pattern")],
     [("Webmention", "h-entry", "USES")],
     "when did the Webmentions pipeline finally render correctly under an essay",
     "indieweb webmention debugging weekend h entry markup first success"),
    # --- 25 ---
    ("The essay drafts live in an Obsidian vault with a Templater script that stamps the frontmatter Hugo expects, so the publish step is just a cp into the content directory.", "architecture", "cross", False,
     [("Obsidian", "tool"), ("Templater", "library"), ("Hugo", "library"), ("cp", "command")],
     [("Obsidian", "Hugo", "COMMUNICATES_WITH"), ("Templater", "Hugo", "USES")],
     "how does a draft in Obsidian become a Hugo post with the right frontmatter",
     "draft pipeline templater frontmatter static generator content directory copy"),
    # --- 26 ---
    ("Confusion set in when the Medium cross-post canonical tag stopped passing SEO weight back on 2024-08-14, and the rel-canonical strategy got scrapped for an excerpt-only cross-post.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Medium", "service"), ("2024-08-14", "date"), ("SEO", "concept"), ("rel-canonical", "pattern")],
     [],
     "what went sideways with the Medium canonical cross-post strategy",
     "medium canonical tag SEO weight cross post strategy excerpt rewrite"),
    # --- 27 ---
    ("Prefers a custom domain on Micro.blog over keeping the micro.blog subdomain because the RSS feed URL stays portable if the hosting moves back to self-hosted someday.", "preference", "cross", False,
     [("Micro.blog", "service"), ("RSS", "protocol")],
     [],
     "why does the Micro.blog setup use a custom domain instead of the subdomain",
     "custom domain portability rss feed url hosting migration readiness"),
    # --- 28 ---
    ("The newsletter archive page uses Buttondown's public archive feature through a reverse proxy on Cloudflare Workers so the URL stays under the main domain instead of the buttondown.email host.", "architecture", "cross", False,
     [("Buttondown", "service"), ("Cloudflare Workers", "service")],
     [("Cloudflare Workers", "Buttondown", "USES")],
     "how does the newsletter archive live under the main domain",
     "reverse proxy archive page custom domain worker newsletter public"),
    # --- 29 ---
    ("Hugo's hugo-coder theme handles the essay site, and the fork lives in the content repo as a git submodule pinned to the 1.30.1 tag.", "architecture", "cross", False,
     [("Hugo", "library"), ("hugo-coder", "library")],
     [("hugo-coder", "Hugo", "USES")],
     "which Hugo theme powers the essay site and how is it pinned",
     "hugo theme fork submodule pinned tag version control maintenance"),
    # --- 30 ---
    ("Moved the 15-year Tumblr archive into a Hugo content folder on 2026-02-17 after exporting the backup XML and running a 200-line Python parser that preserved the permalinks.", "milestone", "cross", False,
     [("Tumblr", "service"), ("Hugo", "library"), ("2026-02-17", "date"), ("XML", "language"), ("Python", "language")],
     [("Hugo", "Tumblr", "REPLACES")],
     "when did the old Tumblr archive finally land inside the Hugo site",
     "legacy blog migration archive export xml parser permalink preservation"),
    # --- 31 ---
    ("The Prose app on iPad feeds the morning journal straight into the Obsidian vault over iCloud, and the session either stays private or gets promoted into a blog draft by the end of the week.", "architecture", "cross", False,
     [("Prose", "tool"), ("iPad", "infrastructure"), ("Obsidian", "tool"), ("iCloud", "service")],
     [("Prose", "iCloud", "USES"), ("Prose", "Obsidian", "COMMUNICATES_WITH")],
     "how do mobile journal sessions connect to the essay drafting workflow",
     "journaling app tablet vault sync icloud private to public pipeline"),
    # --- 32 ---
    ("Pelican lost to Astro in the 2026-02 static-generator audit because Astro's content collections schema caught the frontmatter typos that Pelican's loose YAML load ignored.", "decision", "cross", False,
     [("Pelican", "library"), ("Astro", "library"), ("YAML", "language")],
     [("Astro", "Pelican", "REPLACES")],
     "why did the static-generator audit pick Astro over Pelican",
     "static generator audit content collections schema validation frontmatter"),
    # --- 33 ---
    ("Typlog replaced the custom Flask podcasting rig on 2026-01-11 once the episode backlog hit 47 and manual RSS-feed edits got too error-prone before every Apple Podcasts submission.", "decision", "cross", False,
     [("Typlog", "service"), ("Flask", "library"), ("2026-01-11", "date"), ("RSS", "protocol"), ("Apple Podcasts", "service")],
     [("Typlog", "Flask", "REPLACES")],
     "when did the custom podcast feed code get retired and what replaced it",
     "podcast platform migration custom flask rig managed hosting rss feed edit"),
    # --- 34. noise ---
    ("I want to revisit that question in a moment.", "fact", "noise", True, [], [], None, None),
    # --- 35 ---
    ("SEO basics for the essay site came down to the Ahrefs-recommended descriptive slugs plus a single og-image generator in Cloudflare Workers; the Yoast-style checklist overhead never earned its keep.", "decision", "cross", False,
     [("Ahrefs", "service"), ("Cloudflare Workers", "service"), ("Yoast", "service"), ("SEO", "concept")],
     [("Cloudflare Workers", "Yoast", "REPLACES")],
     "which SEO approach stuck for the personal essay site",
     "SEO minimal approach descriptive slug og image generator checklist overhead"),
    # --- 36 ---
    ("Ghost's member paywall on the self-hosted instance uses Stripe test mode first because the 2.9% plus 30 cents felt wrong until the 12 founding subscribers actually clicked through on 2026-03-06.", "milestone", "cross", False,
     [("Ghost", "service"), ("Stripe", "service"), ("2026-03-06", "date")],
     [("Ghost", "Stripe", "USES")],
     "when did the blog's paid-member flow go live and how was it tested",
     "member paywall payment processor test mode founding subscriber launch"),
    # --- 37 ---
    ("The Eleventy-plus-Pagefind setup replaced Algolia DocSearch on 2026-02-05 because Algolia removed the free-tier indexing when the archive hit 1000 posts.", "decision", "cross", False,
     [("Eleventy", "library"), ("Pagefind", "library"), ("Algolia DocSearch", "service"), ("2026-02-05", "date")],
     [("Pagefind", "Algolia DocSearch", "REPLACES")],
     "when did the blog search move off Algolia and onto Pagefind",
     "static site search self hosted pagefind algolia free tier archive size"),
    # --- 38 ---
    ("Prefers the AVIF og-images generated on build over the Satori-based runtime ones because the edge render on the 8-year-old Android Chrome still stalled on missing font fallbacks.", "preference", "cross", False,
     [("AVIF", "concept"), ("Satori", "library"), ("Android", "infrastructure"), ("Chrome", "service")],
     [("AVIF", "Satori", "PREFERS")],
     "which og-image pipeline won and why was the runtime option dropped",
     "open graph image build time versus runtime font fallback older browser"),
    # --- 39 ---
    ("The newsletter-to-blog backfill script turned 94 Buttondown issues into Hugo posts on 2026-02-28 so the essay archive finally reads in one place instead of across two silos.", "milestone", "cross", False,
     [("Buttondown", "service"), ("Hugo", "library"), ("2026-02-28", "date")],
     [("Hugo", "Buttondown", "USES")],
     "when did the newsletter archive finally merge into the blog",
     "archive backfill script newsletter to blog consolidation silo merge"),
    # --- 40 ---
    ("Excitement flickered when Paolo Amoroso's Medium-vs-open-web essay on 2025-11-02 captured exactly why the essay site refuses to cross-post to Medium even for the extra reach.", "reference", "cross", False,
     [("Excitement", "emotion"), ("Paolo Amoroso", "person"), ("Medium", "service"), ("2025-11-02", "date")],
     [],
     "which essay captured the reasoning behind refusing to cross-post to Medium",
     "medium open web debate reach tradeoff essay reference ownership"),
    # --- 41 ---
    ("The RSS reading ritual starts at 6am with Inoreader on the Kindle Scribe over the share-sheet browser, and unread items over an hour old get the mass-mark-read treatment without guilt.", "fact", "cross", False,
     [("Inoreader", "service"), ("Kindle Scribe", "infrastructure")],
     [("Inoreader", "Kindle Scribe", "DEPLOYED_ON")],
     "what does the morning RSS reading ritual actually look like",
     "morning rss routine kindle scribe reader mass mark read triage"),
    # --- 42 ---
    ("Prefers Astro's MDX over Hugo's shortcodes for the tutorial site because React interactive components embed directly in the post body without the shortcode parameter parsing dance.", "preference", "cross", False,
     [("Astro", "library"), ("MDX", "language"), ("Hugo", "library"), ("React", "library")],
     [("Astro", "Hugo", "PREFERS")],
     "which authoring format wins for the tutorial site with interactive components",
     "mdx versus shortcodes react interactive embed static generator tutorial"),
    # --- 43 ---
    ("Subscribed to Manton Reece's Micro.blog newsletter on 2026-03-04 because the weekly roundup surfaces the indie-web pieces that the Inoreader feed misses entirely.", "fact", "cross", False,
     [("Manton Reece", "person"), ("Micro.blog", "service"), ("2026-03-04", "date"), ("Inoreader", "service")],
     [],
     "when did the Manton Reece newsletter get added to the reading rotation",
     "newsletter subscription indie web roundup weekly digest discovery"),
    # --- 44 ---
    ("Confusion spiked when Ghost's 5.80 upgrade flipped the default theme to Source and broke the custom Liebling fork because the card rendering API changed without a deprecation window.", "problem", "cross", False,
     [("Confusion", "emotion"), ("Ghost", "service"), ("Source", "library"), ("Liebling", "library")],
     [("Source", "Liebling", "REPLACES")],
     "what broke when Ghost's upgrade flipped the default theme",
     "ghost upgrade theme default change card api breaking change fork"),
    # --- 45 ---
    ("A CNAME on writings.example.com points to the Ghost droplet's reverse proxy through Cloudflare's orange-cloud on full-strict TLS, and the origin cert renews through Caddy's ACME flow.", "architecture", "cross", False,
     [("CNAME", "protocol"), ("Ghost", "service"), ("Cloudflare", "service"), ("TLS", "protocol"), ("Caddy", "service"), ("ACME", "protocol")],
     [("Caddy", "ACME", "USES"), ("Ghost", "Cloudflare", "COMMUNICATES_WITH")],
     "how does the custom writing subdomain route to the Ghost self-hosted instance",
     "custom domain cname reverse proxy full strict tls origin cert acme"),
    # --- 46 ---
    ("Ali Abdaal's 2024-05-12 YouTube video on Beehiiv's referral program looked compelling but the essay site skipped the referral feature because the social gamification clashed with the slow-writing ethos.", "decision", "cross", False,
     [("Ali Abdaal", "person"), ("2024-05-12", "date"), ("YouTube", "service"), ("Beehiiv", "service")],
     [],
     "why did the newsletter skip the Beehiiv referral program despite the hype",
     "referral program skip gamification newsletter growth ethos mismatch"),
    # --- 47 ---
    ("Regret lingered over picking Gatsby in 2021 because the 2026-03-14 Astro rewrite turned into a three-weekend project to untangle the GraphQL data layer that never added value for a personal blog.", "problem", "cross", False,
     [("Regret", "emotion"), ("Gatsby", "library"), ("Astro", "library"), ("2026-03-14", "date"), ("GraphQL", "language")],
     [],
     "what made the 2021 Gatsby choice look bad in hindsight",
     "gatsby hindsight graphql overkill personal blog rewrite effort regret"),
    # --- 48 ---
    ("The POSSE pattern routes every long post through the Hugo site first, then syndicates to Mastodon via Brid.gy Fed and to LinkedIn through a Zapier rule that watches the RSS feed.", "architecture", "cross", False,
     [("POSSE", "pattern"), ("Hugo", "library"), ("Mastodon", "service"), ("Brid.gy", "service"), ("LinkedIn", "service"), ("Zapier", "service"), ("RSS", "protocol")],
     [("Zapier", "RSS", "USES"), ("Mastodon", "Brid.gy", "USES")],
     "how does a long post reach Mastodon and LinkedIn from the Hugo site",
     "posse syndication pattern mastodon linkedin rss watcher zapier bridge"),
    # --- 49 ---
    ("The Pinboard.in bookmarks feed drops into the Eleventy link-blog through a cron-fetched JSON endpoint, so every starred link shows up in the next nightly build without manual curation.", "architecture", "cross", False,
     [("Pinboard.in", "service"), ("Eleventy", "library"), ("cron", "tool"), ("JSON", "language")],
     [("Eleventy", "Pinboard.in", "USES")],
     "how do starred bookmarks flow into the link blog without manual posting",
     "bookmark feed link blog cron fetch json automation nightly build"),
    # --- 50 ---
    ("Satisfaction settled in when the 2026-04-01 essay on indie publishing hit 12000 readers in a week across Mastodon, Hacker News, and the RSS subscribers without any Substack recommendation boost.", "milestone", "cross", False,
     [("Satisfaction", "emotion"), ("2026-04-01", "date"), ("Mastodon", "service"), ("Hacker News", "service"), ("RSS", "protocol"), ("Substack", "service")],
     [],
     "when did a post prove the open-web distribution strategy actually works",
     "open web reach proof mastodon hacker news rss substack independence"),
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
