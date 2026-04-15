"""One-off emitter for document stub batch-003 — manual/email/code mix.

Writes 50 rows to data/v2/documents/batch_003.tmp.jsonl with ids doc-00101..00150.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "documents" / "batch_003.tmp.jsonl"
ID_OFFSET = 100

# Each row is: (doc_type, text)
# doc_type ∈ {manual, email, code}. 17 manual, 17 email, 16 code.
ROWS: list[tuple[str, str]] = [
    # --- manual (17) ---
    (
        "manual",
        "WARNING: Disconnect the AC power cord from the wall outlet before opening the lower access panel. Residual voltage may remain on the capacitor bank for up to sixty seconds after shutdown. To replace the intake filter, slide the retention clip at the top of the panel toward the right, then tilt the panel forward until the hinges disengage. Lift out the filter frame and inspect for visible damage. Install the replacement filter with the airflow arrow pointing toward the motor housing. Refit the panel and confirm the clip clicks audibly before restoring power.",
    ),
    (
        "manual",
        "Before first use, charge the battery pack for a minimum of four hours using only the supplied 19-volt adapter. Connecting a non-approved adapter will void the warranty and may damage the charging circuit. The LED indicator on the handle glows amber during charging and green when the pack is full. Do not operate the trimmer in wet conditions or submerge any part of the unit in water. Store the device in a dry location at temperatures between five and thirty-five degrees Celsius. Replace the cutting line only with genuine 2.0 mm round nylon spools.",
    ),
    (
        "manual",
        "To calibrate the pressure transducer, enter the service menu by holding the MODE and SET keys simultaneously for three seconds. Scroll to CAL using the down arrow, then press ENTER. Vent the sensor to atmosphere and confirm the displayed reading is zero plus or minus 0.5 kPa. If the reading is outside tolerance, press ZERO and wait for the confirmation beep. Apply a known reference pressure of 100.0 kPa from the dead-weight tester and press SPAN. The controller will store the new calibration constants in non-volatile memory.",
    ),
    (
        "manual",
        "The Model 4200 espresso machine includes an automatic descaling cycle. Fill the water reservoir to the MAX line with a solution of one part citric acid descaler to four parts cold water. Place an empty container of at least one litre under the group head and steam wand. Press and hold the DESCALE button until the indicator flashes. The cycle takes approximately twenty minutes and cannot be interrupted. When complete, rinse the reservoir thoroughly and run two full tanks of fresh water through the machine before brewing.",
    ),
    (
        "manual",
        "CAUTION: Hot surfaces. The exhaust manifold and turbocharger housing remain hot for at least thirty minutes after engine shutdown. Wear heat-resistant gloves when servicing nearby components. To inspect the wastegate actuator rod, remove the heat shield by loosening the three M6 bolts with an 8 mm socket. Do not reuse the gasket; a replacement is supplied in the service kit. Torque the bolts to 10 N·m in a cross pattern on reassembly. Failure to follow the torque sequence may warp the shield and allow exhaust leakage into the engine bay.",
    ),
    (
        "manual",
        "Installation of the ceiling fan must be performed by a qualified electrician in accordance with local wiring regulations. The outlet box must be rated for fan support, typically marked ACCEPTABLE FOR FAN SUPPORT on the box label. Switch off the circuit breaker feeding the outlet and verify the absence of voltage with a non-contact tester before proceeding. Connect the black fan lead to the black supply conductor, white to white, and the green ground lead to the bare copper ground. Use the supplied wire nuts and wrap each joint with electrical tape.",
    ),
    (
        "manual",
        "The blood pressure monitor uses the oscillometric method and should be used while seated with both feet flat on the floor. Rest quietly for at least five minutes before taking a measurement. Wrap the cuff around the bare upper arm, approximately two centimetres above the elbow, with the tube positioned over the brachial artery. Do not speak or move during inflation. If ERR is displayed, check for a kinked hose or loose cuff and repeat the measurement. Consult a physician if readings consistently exceed 140 over 90 mmHg.",
    ),
    (
        "manual",
        "To remove the ink cartridge, open the top cover and wait for the carriage to move to the centre service position. Press the tab on the rear of the cartridge firmly downward until it releases, then lift the cartridge straight up. Do not tilt the cartridge; ink may leak onto the printhead contacts. Unpack the replacement cartridge, remove the orange protective strip, and insert it at a slight angle with the nozzles facing down. Push the cartridge forward until it clicks into position and close the cover.",
    ),
    (
        "manual",
        "Safety goggles and cut-resistant gloves are required when operating the benchtop mitre saw. Secure the workpiece against the fence using the hold-down clamp before energising the motor. Never place your hands within 15 cm of the blade path. After completing a cut, allow the blade to come to a full stop before raising the saw head. Clean sawdust from the base and dust port daily to prevent build-up. Inspect the blade for cracked teeth each morning and replace it at the first sign of damage.",
    ),
    (
        "manual",
        "The dishwasher features a soft water sensor that automatically adjusts rinse aid dosage. If the rinse aid indicator remains lit after refilling, verify that the cap is fully seated and turned clockwise until it clicks. Use only rinse aid formulated for household dishwashers; hand dishwashing liquid will cause excessive foaming and may damage the pump seal. The recommended rinse aid setting for most regions is level three; increase to level four in areas with very hard water above 300 ppm calcium carbonate.",
    ),
    (
        "manual",
        "Before mounting the telescope on the equatorial wedge, align the latitude scale to match your observing location. For the northern hemisphere, rotate the polar axis until it points toward Polaris and tighten the azimuth locks. Attach the counterweight shaft and slide the counterweight onto the shaft before mounting the optical tube, to prevent the mount from tipping. Balance the telescope in both right ascension and declination by loosening the clutches and adjusting the tube position in the saddle until it remains stationary at any orientation.",
    ),
    (
        "manual",
        "Replace the smoke detector battery at least once per year, or immediately when the unit emits intermittent chirps at 30 to 60 second intervals. Press and hold the TEST button for three seconds after installing the new battery; the horn should sound loudly and the red LED should flash. If the alarm does not sound, remove the unit and verify the battery polarity. The detector should be replaced entirely every ten years. Record the installation date on the label provided on the back of the housing.",
    ),
    (
        "manual",
        "The lithium-ion drill battery must not be charged in ambient temperatures below 0 degrees Celsius or above 40 degrees Celsius. If the charger detects an out-of-range temperature, the status LED will flash red and charging will pause until the pack returns to the allowed range. Never disassemble, puncture, or incinerate the battery pack. Dispose of end-of-life packs through a certified battery recycling programme. Do not store fully discharged packs for more than seven days, as deep discharge may permanently damage the cells.",
    ),
    (
        "manual",
        "NOTICE: This router supports dual-band operation on the 2.4 GHz and 5 GHz bands. For best throughput, connect devices that support 802.11ac or 802.11ax to the 5 GHz SSID. To reset the router to factory defaults, press and hold the recessed RESET button on the rear panel for fifteen seconds using a paper clip or similar tool. All custom configuration, including Wi-Fi passwords and port forwarding rules, will be erased. The default management URL is printed on the label underneath the router.",
    ),
    (
        "manual",
        "The washing machine door cannot be opened while the drum contains water or while a cycle is active. To drain the machine manually in the event of a power failure, locate the access panel at the lower front of the cabinet. Place a shallow tray under the panel to catch residual water. Unscrew the drain plug counter-clockwise by one full turn and allow the drum to empty. Refit the plug hand-tight before restoring power and running a rinse cycle to confirm there are no leaks at the plug threads.",
    ),
    (
        "manual",
        "For optimal sound quality, position the subwoofer within one metre of a wall but not directly in a corner, as corner placement exaggerates low-frequency room modes. Connect the subwoofer to the AV receiver using a shielded RCA cable no longer than five metres. Set the receiver crossover frequency to 80 Hz for bookshelf satellites or 60 Hz for tower speakers. Run the automatic room correction routine with the supplied microphone placed at the primary listening position at ear height.",
    ),
    (
        "manual",
        "To change the oil in the lawn tractor, run the engine for five minutes to warm the oil, then shut it down and remove the key. Park on a level surface and engage the parking brake. Place a drain pan of at least three litres capacity beneath the engine. Remove the drain plug with a 17 mm socket and allow the oil to drain for at least ten minutes. Refit the plug with a new crush washer and torque to 20 N·m. Refill with SAE 10W-30 engine oil to the FULL mark on the dipstick.",
    ),

    # --- email (17) ---
    (
        "email",
        "Hi Priya,\n\nQuick heads up that the staging deploy tonight is going to slip by about an hour. We hit a migration conflict on the reports table and I want to run it by hand rather than risk an automated rollback at 2 AM. I'll ping the on-call channel once it's green so you can run your smoke tests in the morning.\n\nLet me know if that window breaks anything on your side.\n\nThanks,\nMarco",
    ),
    (
        "email",
        "Dear Dr. Lindqvist,\n\nThank you for agreeing to review the revised manuscript. I have attached the updated PDF along with a point-by-point response to the reviewers' comments. The main changes are in sections 3.2 and 4, where we have expanded the ablation study and corrected the reported F1 scores that were affected by the stratification bug you identified.\n\nPlease let me know if you require any additional materials. The editor has requested a decision by 30 April.\n\nKind regards,\nAmelia Hart",
    ),
    (
        "email",
        "Hey team,\n\nJust a reminder that the office will be closed this Friday for the building's fire alarm testing. If you can WFH, great. If you absolutely need to be in the building, security will escort individual contributors in and out between 10 and 11 AM only.\n\nCoffee supplies should last through next week but Ravi is putting in the usual order Monday, so shout if you want anything specific added to the list.\n\nCheers,\nDana",
    ),
    (
        "email",
        "Hi Jordan,\n\nCongratulations on the offer! We are thrilled to welcome you to the product team. I've attached the signed offer letter and the onboarding packet. HR will reach out separately with benefits enrolment instructions.\n\nYour first day will be Monday, 21 April. Please plan to arrive at 9 AM; reception will have your badge ready. Dress code is business casual. If you have any questions before then, feel free to reach me directly at this address.\n\nWelcome aboard,\nElena Vasquez",
    ),
    (
        "email",
        "Hi Mom,\n\nMade it in fine last night, the flight was only an hour late which is basically on time by this airline's standards. Ubered to the hotel and crashed pretty much immediately.\n\nFirst day of the conference is tomorrow. I'll try to call Sunday evening your time once things settle down. Tell Dad the tomato plants are going to survive a week without him fussing over them, I promise.\n\nLove,\nSam",
    ),
    (
        "email",
        "Dear Mr. Okafor,\n\nFollowing our call yesterday, I am writing to confirm the revised scope of work for the Meridian project. The updated statement of work attached as Appendix A reflects the reduced deliverables in Phase 2 and the corresponding fee adjustment of 14,500 USD. All other terms of our master services agreement dated 3 February remain unchanged.\n\nPlease countersign and return at your convenience. Work on Phase 1 will continue on the existing timeline.\n\nSincerely,\nFrances Li",
    ),
    (
        "email",
        "Hey Alex,\n\nWeird one for you. The Prometheus scrape on the billing pods is returning 503s intermittently, but only between 14:00 and 14:30 UTC. I checked the obvious stuff: no scheduled jobs, no autoscaling events in that window, CPU looks flat. Could be a coincidence with the hourly cache flush but the timing is suspicious.\n\nWould you mind taking a peek tomorrow when you're fresh? I've pinned the relevant grafana panel in #obs-alerts.\n\nThanks,\nRobin",
    ),
    (
        "email",
        "Hi Sara,\n\nThe landlord came by this morning about the leak under the kitchen sink. He agrees it's the shut-off valve, not the P-trap like I thought, and he's sending a plumber Wednesday between 10 and 2. I can be home, but if you happen to finish early at the clinic, extra eyes are welcome.\n\nAlso, we're out of dishwasher tablets. Picking some up after work unless you're closer to the store.\n\nLove you,\nTom",
    ),
    (
        "email",
        "Dear Hiring Committee,\n\nI am writing to formally withdraw my application for the Senior Research Scientist position in the Computational Biology group. After extensive consideration, I have decided to accept an offer from another institution that better aligns with my long-term research interests.\n\nI am grateful for the time your team invested in the interview process and for the thoughtful feedback you provided. I hope our paths cross again in the future, perhaps at an upcoming conference.\n\nWith best wishes,\nDr. Kenji Watanabe",
    ),
    (
        "email",
        "Hey Chris,\n\nSending the updated deck for Thursday. Two things I changed based on your feedback: pulled the revenue forecast slide out of the main deck and into the appendix, and rewrote the go-to-market timeline so it fits on a single page. I think it reads much cleaner now.\n\nOne thing I want your take on before we send it to the board: should we include the competitor benchmark table? It's flattering to us, but it might invite questions we don't have great answers to yet.\n\nTalk soon,\nNora",
    ),
    (
        "email",
        "Hi all,\n\nThe Q1 expense reports are due by end of day Friday. Please make sure receipts over 75 dollars are attached as images or PDFs in the expense tool; scanned paper copies are fine as long as line items are legible. If you traveled for a client engagement, remember to tag the project code in the notes field so we can bill back correctly.\n\nReach out to me or Jia if anything in the tool is behaving oddly.\n\nBest,\nHarriet, Finance Ops",
    ),
    (
        "email",
        "Hi Dr. Park,\n\nThank you for fitting me in on short notice last Tuesday. I wanted to follow up on the lab results you mentioned would be back by the end of the week. The portal still shows them as pending, so I'm not sure if that's a delay at the lab or something on the portal side. No rush, just wanted to flag it in case you need to nudge someone.\n\nI've been taking the medication as prescribed and feel noticeably better.\n\nThanks,\nLucia Ferrari",
    ),
    (
        "email",
        "Team,\n\nHeads up that we're freezing deploys to production starting Thursday 17:00 UTC through Monday 09:00 UTC. This is to give the infra team a clean window to finish the Kubernetes upgrade to 1.32 without fighting application rollouts. Staging remains open for normal work.\n\nIf you have an urgent hotfix during the freeze, page the on-call engineer and we'll evaluate case by case. Please do not work around the freeze silently.\n\nThanks for the cooperation,\nBen, Platform Lead",
    ),
    (
        "email",
        "Hi Coach,\n\nMia is not going to make practice tomorrow evening. She picked up whatever bug is going around at school and has been running a low fever all afternoon. I don't want to risk passing it to the rest of the squad before the weekend tournament.\n\nShe'll be back Thursday if she's feeling better by then. She asked me to tell you she's been reviewing the new set plays on her tablet at home, which I can't verify independently.\n\nThanks,\nJared",
    ),
    (
        "email",
        "Dear Customer Service,\n\nI am writing regarding order number A7-44210, placed on 2 April. The package arrived yesterday, but the item inside is the wrong model. I ordered the 24-inch matte black shelf brackets and received a pair of 18-inch polished chrome brackets instead. Photos of the packing slip and the brackets are attached.\n\nPlease advise on the return process and the timeline for shipping the correct product. The brackets are needed for a project on 19 April.\n\nRegards,\nClaire Donnelly",
    ),
    (
        "email",
        "Hey Yusuf,\n\nThat bug you tracked down last week in the session cleanup job is still giving us grief in the EU region. It looks like the fix works on the primary replicas but the read replicas are lagging far enough behind that stale sessions reappear for a minute or two after cleanup. Not a data integrity problem, just spammy in the logs.\n\nI can open a ticket if you want, but wanted to check with you first in case this is expected behaviour given the replication topology.\n\nThanks,\nPatel",
    ),
    (
        "email",
        "Hi neighbours,\n\nJust a quick note that the building's hot water will be off from 09:00 to approximately 14:00 this Saturday while the boiler service is carried out. Cold water will remain available throughout. The contractor has asked that the mechanical room be left clear of bicycles and storage items so they have access to the control panel.\n\nIf you have any questions, Magda in unit 3B is coordinating with the service company and can be reached on the building WhatsApp.\n\nThanks,\nBuilding Committee",
    ),

    # --- code (16) ---
    (
        "code",
        "# Retry with exponential backoff and jitter.\nimport random\nimport time\nfrom typing import Callable, TypeVar\n\nT = TypeVar(\"T\")\n\ndef retry_with_backoff(fn: Callable[[], T], *, max_attempts: int = 5, base_delay: float = 0.5) -> T:\n    for attempt in range(1, max_attempts + 1):\n        try:\n            return fn()\n        except Exception:\n            if attempt == max_attempts:\n                raise\n            sleep_for = base_delay * (2 ** (attempt - 1))\n            sleep_for += random.uniform(0, base_delay)\n            time.sleep(sleep_for)\n    raise RuntimeError(\"unreachable\")",
    ),
    (
        "code",
        "// Debounce a function so it only fires after `wait` ms of silence.\nexport function debounce<F extends (...args: unknown[]) => void>(fn: F, wait: number): F {\n  let timer: ReturnType<typeof setTimeout> | null = null;\n  return ((...args: Parameters<F>) => {\n    if (timer !== null) clearTimeout(timer);\n    timer = setTimeout(() => {\n      timer = null;\n      fn(...args);\n    }, wait);\n  }) as F;\n}",
    ),
    (
        "code",
        "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\t\"time\"\n)\n\n// worker consumes jobs until ctx is cancelled or the channel closes.\nfunc worker(ctx context.Context, id int, jobs <-chan int, results chan<- int) {\n\tfor {\n\t\tselect {\n\t\tcase <-ctx.Done():\n\t\t\treturn\n\t\tcase j, ok := <-jobs:\n\t\t\tif !ok {\n\t\t\t\treturn\n\t\t\t}\n\t\t\ttime.Sleep(50 * time.Millisecond)\n\t\t\tresults <- j * j\n\t\t\tfmt.Printf(\"worker %d finished job %d\\n\", id, j)\n\t\t}\n\t}\n}",
    ),
    (
        "code",
        "-- Top 10 customers by revenue over the trailing 30 days, excluding internal test accounts.\nSELECT c.customer_id,\n       c.display_name,\n       SUM(o.total_cents) / 100.0 AS revenue_usd,\n       COUNT(*)                    AS order_count\nFROM   orders       AS o\nJOIN   customers    AS c ON c.customer_id = o.customer_id\nWHERE  o.placed_at >= NOW() - INTERVAL '30 days'\n  AND  o.status = 'fulfilled'\n  AND  c.is_internal = FALSE\nGROUP  BY c.customer_id, c.display_name\nORDER  BY revenue_usd DESC\nLIMIT  10;",
    ),
    (
        "code",
        "use std::collections::HashMap;\n\n/// Counts how many times each word appears in `text`, case-insensitive.\npub fn word_count(text: &str) -> HashMap<String, u32> {\n    let mut counts = HashMap::new();\n    for raw in text.split_whitespace() {\n        let word: String = raw\n            .chars()\n            .filter(|c| c.is_alphanumeric())\n            .flat_map(|c| c.to_lowercase())\n            .collect();\n        if !word.is_empty() {\n            *counts.entry(word).or_insert(0) += 1;\n        }\n    }\n    counts\n}",
    ),
    (
        "code",
        "#!/usr/bin/env bash\n# Rotate local log files older than 14 days into a dated tarball and remove the originals.\nset -euo pipefail\n\nLOG_DIR=\"${1:-/var/log/myapp}\"\nARCHIVE_DIR=\"${LOG_DIR}/archive\"\nmkdir -p \"$ARCHIVE_DIR\"\n\ncd \"$LOG_DIR\"\nmapfile -t OLD < <(find . -maxdepth 1 -type f -name '*.log' -mtime +14)\nif [[ ${#OLD[@]} -eq 0 ]]; then\n  echo \"nothing to rotate\"\n  exit 0\nfi\n\nSTAMP=$(date -u +%Y%m%dT%H%M%SZ)\ntar -czf \"${ARCHIVE_DIR}/logs-${STAMP}.tar.gz\" \"${OLD[@]}\"\nrm -f \"${OLD[@]}\"",
    ),
    (
        "code",
        "from dataclasses import dataclass\nfrom decimal import Decimal\n\n@dataclass(frozen=True)\nclass LineItem:\n    sku: str\n    quantity: int\n    unit_price: Decimal\n\n    def subtotal(self) -> Decimal:\n        return self.unit_price * self.quantity\n\ndef order_total(items: list[LineItem], tax_rate: Decimal) -> Decimal:\n    subtotal = sum((item.subtotal() for item in items), Decimal(\"0\"))\n    tax = (subtotal * tax_rate).quantize(Decimal(\"0.01\"))\n    return subtotal + tax",
    ),
    (
        "code",
        "import React, { useEffect, useState } from \"react\";\n\nexport function UserBadge({ userId }: { userId: string }) {\n  const [name, setName] = useState<string | null>(null);\n  const [error, setError] = useState<Error | null>(null);\n\n  useEffect(() => {\n    let cancelled = false;\n    fetch(`/api/users/${userId}`)\n      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))\n      .then((u) => { if (!cancelled) setName(u.displayName); })\n      .catch((e) => { if (!cancelled) setError(e); });\n    return () => { cancelled = true; };\n  }, [userId]);\n\n  if (error) return <span className=\"badge err\">offline</span>;\n  return <span className=\"badge\">{name ?? \"…\"}</span>;\n}",
    ),
    (
        "code",
        "# Pytest fixture that spins up a throwaway Postgres via testcontainers and yields a connection URL.\nimport pytest\nfrom testcontainers.postgres import PostgresContainer\n\n@pytest.fixture(scope=\"session\")\ndef pg_url():\n    with PostgresContainer(\"postgres:16-alpine\") as pg:\n        url = pg.get_connection_url().replace(\"postgresql+psycopg2\", \"postgresql\")\n        yield url",
    ),
    (
        "code",
        "// Clamp a value into the inclusive range [min, max].\nfunction clamp(value, min, max) {\n  if (min > max) throw new RangeError(\"min must be <= max\");\n  if (value < min) return min;\n  if (value > max) return max;\n  return value;\n}\n\n// Example: clamp the slider input so it never escapes the document's scroll range.\nwindow.addEventListener(\"scroll\", () => {\n  const y = clamp(window.scrollY, 0, document.body.scrollHeight - window.innerHeight);\n  document.documentElement.style.setProperty(\"--scroll\", String(y));\n});",
    ),
    (
        "code",
        "fn fibonacci(n: u32) -> u64 {\n    let (mut a, mut b): (u64, u64) = (0, 1);\n    for _ in 0..n {\n        let next = a.checked_add(b).expect(\"fibonacci overflowed u64\");\n        a = b;\n        b = next;\n    }\n    a\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n\n    #[test]\n    fn small_values_match_known_sequence() {\n        let expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34];\n        for (i, want) in expected.iter().enumerate() {\n            assert_eq!(fibonacci(i as u32), *want);\n        }\n    }\n}",
    ),
    (
        "code",
        "-- Enforce that every active subscription has a payment method on file.\nALTER TABLE subscriptions\n    ADD CONSTRAINT subscriptions_payment_required\n        CHECK (status <> 'active' OR payment_method_id IS NOT NULL);\n\nCREATE INDEX CONCURRENTLY IF NOT EXISTS subscriptions_active_customer_idx\n    ON subscriptions (customer_id)\n    WHERE status = 'active';",
    ),
    (
        "code",
        "package com.example.cache;\n\nimport java.util.LinkedHashMap;\nimport java.util.Map;\n\npublic final class LruCache<K, V> extends LinkedHashMap<K, V> {\n    private final int capacity;\n\n    public LruCache(int capacity) {\n        super(capacity, 0.75f, true);\n        if (capacity <= 0) throw new IllegalArgumentException(\"capacity must be positive\");\n        this.capacity = capacity;\n    }\n\n    @Override\n    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {\n        return size() > capacity;\n    }\n}",
    ),
    (
        "code",
        "import httpx\nimport asyncio\n\nasync def fetch_all(urls: list[str], concurrency: int = 8) -> list[bytes]:\n    sem = asyncio.Semaphore(concurrency)\n    async with httpx.AsyncClient(timeout=10.0) as client:\n        async def one(url: str) -> bytes:\n            async with sem:\n                resp = await client.get(url)\n                resp.raise_for_status()\n                return resp.content\n        return await asyncio.gather(*(one(u) for u in urls))",
    ),
    (
        "code",
        "// Parse a CSV line that may contain quoted fields with embedded commas.\npub fn parse_csv_line(line: &str) -> Vec<String> {\n    let mut fields = Vec::new();\n    let mut buf = String::new();\n    let mut in_quotes = false;\n    let mut chars = line.chars().peekable();\n    while let Some(c) = chars.next() {\n        match (c, in_quotes) {\n            ('\"', true) if chars.peek() == Some(&'\"') => { buf.push('\"'); chars.next(); }\n            ('\"', _) => in_quotes = !in_quotes,\n            (',', false) => { fields.push(std::mem::take(&mut buf)); }\n            (c, _) => buf.push(c),\n        }\n    }\n    fields.push(buf);\n    fields\n}",
    ),
    (
        "code",
        "# Ansible task: ensure the nginx service is running with the latest config.\n- name: Deploy nginx site config\n  ansible.builtin.template:\n    src: site.conf.j2\n    dest: /etc/nginx/conf.d/{{ site_name }}.conf\n    owner: root\n    group: root\n    mode: '0644'\n  notify: reload nginx\n\n- name: Ensure nginx is enabled and running\n  ansible.builtin.service:\n    name: nginx\n    state: started\n    enabled: true",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (doc_type, text) in enumerate(ROWS, start=1):
            row_id = f"doc-{ID_OFFSET + i:05d}"
            f.write(json.dumps({
                "id": row_id,
                "doc_type": doc_type,
                "text": text,
            }, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
