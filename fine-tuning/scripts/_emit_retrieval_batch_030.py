"""One-off emitter for retrieval top-up batch-030 - hard-negative kind, target shared rows at line offsets 2900..2999.

Writes 100 rows to data/v2/retrieval/batch_030.tmp.jsonl with ids ret-02901..03000.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_030.tmp.jsonl"
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
ID_OFFSET = 2900
SHARED_OFFSET = 2900
QUERY_KIND = "hard-negative"

# One (query, negative_line_offset) per target row, in target-row order.
# `query` is about the TARGET row; `negative_line_offset` points to a different shared row
# whose text is topically close but does not answer the query.
ENTRIES: list[tuple[str, int]] = [
    # 2900 shared-02902 Reconnected with Imogen after eight years, Hampstead Heath walk
    ("Who did I reconnect with after eight years on a Hampstead Heath walk?", 2917),
    # 2901 shared-02903 Hosted Nadia's 35th at the flat, 14 guests, lemon-drizzle
    ("How many guests came to Nadia's 35th birthday at the flat?", 2922),
    # 2902 shared-02904 Prefers small four-player board-game nights over eight-player Catan
    ("Why do I prefer four-player board-game nights over eight-player Catan?", 2919),
    # 2903 shared-02905 Split one huge group chat into three smaller threads
    ("How did splitting the mega group chat into three smaller threads change volume?", 2921),
    # 2904 shared-02906 Sunday brunch booking at Cafe Lila, six at 11:00, Theo holds table
    ("What is the Sunday brunch standing booking at Cafe Lila for six?", 2941),
    # 2905 shared-02907 Friendship with Marcus ended 2026-02-09 over loan and wedding RSVP
    ("Why did I end the friendship with Marcus on 2026-02-09?", 2938),
    # 2906 shared-02908 Board-game shelf rotation by night: heavy euros, party, Wingspan newcomers
    ("How is the board-game shelf rotation set for friend nights?", 2940),
    # 2907 shared-02909 Prefers the Anvil quiet bar over the Crown's main room
    ("Why do I prefer the Anvil quiet bar over the Crown's main room for catch-ups?", 2926),
    # 2908 shared-02910 NOISE filler about leaving coat at the table
    ("What offhand aside mentioned leaving a coat behind at the table?", 2932),
    # 2909 shared-02911 Uni reunion at Magdalen 2026-06-20, 42 RSVPs, jacket if you have one
    ("How many RSVPs are in for the Magdalen uni reunion on 2026-06-20?", 2950),
    # 2910 shared-02912 Neighbour Iris at flat 4B shares parcel-collection
    ("What parcel-collection arrangement do I have with Iris at flat 4B?", 2944),
    # 2911 shared-02913 Dinner-party rota among four households resets each January
    ("How does the four-household dinner-party rota reset each January?", 2923),
    # 2912 shared-02914 Bumped into ex-flatmate Caleb at Whitechapel gallery opening
    ("How did the awkward run-in with ex-flatmate Caleb at Whitechapel go?", 2938),
    # 2913 shared-02915 Switched friend-group calendar from Google Calendar to Notion
    ("Why did the friend-group calendar move from Google Calendar to Notion?", 2930),
    # 2914 shared-02916 Theo's stag weekend in Lisbon 2026-05-09, nine guys, Alfama
    ("What are the plans for Theo's Lisbon stag weekend?", 2942),
    # 2915 shared-02917 Prefers planning friend dinners three weeks out
    ("Why do I plan friend dinners three weeks out instead of day-of?", 2929),
    # 2916 shared-02918 Board-game injury count for 2025 was three
    ("What was the board-game night injury count for 2025?", 2937),
    # 2917 shared-02919 Reconnected with secondary-school WhatsApp of 28, six showed up
    ("How many people from the secondary-school WhatsApp actually showed up to the pub?", 2900),
    # 2918 shared-02920 Dinner party seating rule: never Anya next to Felix, no Karim at head
    ("What dinner-party seating rules did we settle on after the 2025 Christmas disaster?", 2923),
    # 2919 shared-02921 Tuesday board-game night at Draughts Hackney over weekend slots
    ("Why did I pick Tuesday board-game night at Draughts Hackney over weekends?", 2937),
    # 2920 shared-02922 Neighbour Mr Akadiri taught chequer lawn-mowing trick
    ("Who taught me the chequer-pattern lawn-mowing trick over a beer?", 2910),
    # 2921 shared-02923 'Sunday Roasts' chat is the only real-time chat, rest triaged at 19:00
    ("Which chat group do I read in real time rather than triage?", 2903),
    # 2922 shared-02924 Surprise party for Priya's 40th on 2026-04-12 at Lordship Lane wine bar
    ("Where was the surprise party for Priya's 40th birthday held?", 2901),
    # 2923 shared-02925 Dinner-party menu format: shared starter, big roast, three sides
    ("What dinner-party menu format do I keep returning to?", 2936),
    # 2924 shared-02926 Replaced loud Brixton bar with The Pelican for drinks with Yusuf and Iona
    ("Why did I replace the Brixton cocktail bar with The Pelican for monthly drinks?", 2907),
    # 2925 shared-02927 Friendship with Tomas drifted in 2024, back via WhatsApp voice notes
    ("How did the drifted friendship with Tomas come back in March 2026?", 2939),
    # 2926 shared-02928 Board-game dietary cheat-sheet on fridge
    ("What is on the board-game night dietary cheat-sheet pinned to the fridge?", 2906),
    # 2927 shared-02929 Prefers post-mortem walk with Sam to post-mortem text next day
    ("Why do I prefer the post-dinner walk with Sam over a next-day text?", 2947),
    # 2928 shared-02930 Neighbour Marcellus in flat 7 plays trombone Wednesdays, 21:30 cut-off
    ("What cut-off time did I agree with Marcellus for his trombone practice?", 2920),
    # 2929 shared-02931 Switched birthday format to Saturday lunch for ten
    ("Why did I switch my birthday format from a bar takeover to a Saturday lunch?", 2915),
    # 2930 shared-02932 Hiking crew chat uses three reactions: boot, mountain, sleeping bag
    ("What three reactions does the hiking-crew chat thread use?", 2913),
    # 2931 shared-02933 Lordship Lane neighbours' street WhatsApp has 38 members
    ("How many members does the Lordship Lane neighbours' street WhatsApp have?", 2944),
    # 2932 shared-02934 NOISE filler about whether we are still doing nine or Maya bailed
    ("What offhand aside was about whether Maya had bailed on the count of nine?", 2908),
    # 2933 shared-02935 2026 social calendar has 19 pinned events January through June
    ("How many pinned events are on the 2026 social calendar from January through June?", 2909),
    # 2934 shared-02936 Skipped Henderson wedding 2026-05-23 due to Theo stag clash
    ("Why did I skip the Henderson wedding on 2026-05-23?", 2914),
    # 2935 shared-02937 Friend group shift after Eva moved to Berlin, Iona became organiser
    ("How did the friend group dynamic shift after Eva moved to Berlin?", 2927),
    # 2936 shared-02938 Dinner-party welcome drink rotated from Aperol spritz to Beaujolais
    ("What did we rotate the dinner-party welcome drink to on 2026-02-08?", 2923),
    # 2937 shared-02939 Board-game cafe outing 2026-04-08 at Draughts Hackney ended 23:40
    ("What happened at the 2026-04-08 Draughts Hackney board-game outing?", 2919),
    # 2938 shared-02940 Awkward Christmas drinks ran into Marcus, did not speak
    ("How did the 2025-12-19 office Christmas drinks run-in with Marcus play out?", 2905),
    # 2939 shared-02941 Prefers WhatsApp voice notes to keep in touch with Tomas in Sao Paulo
    ("Why do I prefer WhatsApp voice notes for keeping in touch with Tomas?", 2925),
    # 2940 shared-02942 Board-game night at flat tops out at six players
    ("Why does the flat's board-game night top out at six players?", 2906),
    # 2941 shared-02943 Replaced NYE dinner with NY Day brunch on 2026-01-01
    ("Why did we replace the New Year's Eve dinner with a New Year's Day brunch?", 2904),
    # 2942 shared-02944 Hen weekend for Iona in York 2026-07-11, eleven guests
    ("What are the plans for Iona's hen weekend in York?", 2914),
    # 2943 shared-02945 Friend network after 2025 Bristol-to-London move: four close, three drifted
    ("How did the friend network settle after the 2025 Bristol-to-London move?", 2900),
    # 2944 shared-02946 Lordship Lane block party 2026-06-21, council form by 2026-04-30
    ("What deadline does the Lordship Lane block party need for the council form?", 2931),
    # 2945 shared-02947 Prefers Saturday pub trivia at The Junction over Friday at The Anvil
    ("Why do I prefer Saturday trivia at The Junction over Friday at The Anvil?", 2907),
    # 2946 shared-02948 Rebuilt friendship with Hayden over five long calls in early 2026
    ("How did I rebuild the friendship with Hayden in early 2026?", 2925),
    # 2947 shared-02949 Dinner-party post-game ritual is loading dishwasher with Sam
    ("What is the dinner-party post-game ritual with Sam?", 2927),
    # 2948 shared-02950 2014 backpacking crew reunion 2026-09-12 in the Peak District
    ("What reunion plans did the 2014 backpacking crew lock in for 2026-09-12?", 2909),
    # 2949 shared-02951 Morning zafu sit lasts 22 minutes by Insight Timer bell
    ("How long is the morning zafu sit and which timer marks it?", 2966),
    # 2950 shared-02952 Switched journal from bullet-point to morning-pages style
    ("Why did I switch the evening journal to a morning-pages style?", 2965),
    # 2951 shared-02953 Prefers Tara Brach's RAIN talks over Sam Harris guided sessions
    ("Why do I prefer Tara Brach's RAIN talks to the Sam Harris Waking Up sessions?", 2960),
    # 2952 shared-02954 Started weekly therapy with Dr Halpern 2026-01-08, CBT-leaning
    ("When did I start weekly therapy with Dr Halpern and what is the format?", 2991),
    # 2953 shared-02955 Box-breathing on the 06:40 train is four-four-four-four for ten cycles
    ("What box-breathing pattern do I use on the 06:40 train?", 2987),
    # 2954 shared-02956 Replaced Calm with Insight Timer on 2026-03-02
    ("Why did I replace the Calm subscription with Insight Timer?", 2986),
    # 2955 shared-02957 Gratitude practice is three concrete items said aloud at lights-out
    ("How is my gratitude practice structured at lights-out?", 2993),
    # 2956 shared-02958 Daylio mood log shows seven straight low-mood days March 2026
    ("What did the Daylio mood log show for 2026-03-19 through 2026-03-25?", 2996),
    # 2957 shared-02959 Ten-day Vipassana at Dhamma Dipa booked 2026-09-04 through 2026-09-14
    ("When is the ten-day Vipassana retreat at Dhamma Dipa booked for?", 2997),
    # 2958 shared-02960 NOISE filler about grabbing glass of water
    ("What offhand aside was about getting a glass of water before continuing?", 2981),
    # 2959 shared-02961 Grief sessions for Nan use continuing-bonds frame, not five stages
    ("What grief frame does Dr Halpern use for the sessions about Nan?", 2972),
    # 2960 shared-02962 Prefers Headspace sleepcasts to Calm sleep stories
    ("Why do I prefer Headspace sleepcasts to the Calm sleep stories?", 2976),
    # 2961 shared-02963 Anxiety coping kit in desk drawer: 4-7-8 card, peppermint, pen, values list
    ("What is in the anxiety coping kit in my desk drawer?", 2982),
    # 2962 shared-02964 Friday night body-scan length is 32 minutes
    ("How long is the Friday night body-scan for me?", 2949),
    # 2963 shared-02965 Started loving-kindness practice 2026-02-09 for morning Marcus resentment
    ("Why did I start the loving-kindness practice on 2026-02-09?", 2988),
    # 2964 shared-02966 Therapy homework binder lives on second shelf in the bedroom
    ("Where is the therapy homework binder kept?", 2974),
    # 2965 shared-02967 Switched journaling from laptop to Leuchtturm1917 hardback
    ("Why did I switch journaling from the laptop to a paper notebook?", 2950),
    # 2966 shared-02968 Walking meditation loop in Stanpit Park is 1.4 km
    ("How long is the walking meditation loop in Stanpit Park?", 2973),
    # 2967 shared-02969 Panic episode in Tesco queue 2026-02-27, fix was naming five textures
    ("What worked for the panic episode in the Tesco queue on 2026-02-27?", 2979),
    # 2968 shared-02970 Prefers in-person therapy slot over video when diary allows
    ("Why do I prefer the in-person therapy slot over the video slot?", 2991),
    # 2969 shared-02971 Breath-count drill at desk runs twenty inhales between emails
    ("What breath-count drill do I run at the desk between emails?", 2987),
    # 2970 shared-02972 Replaced wine-with-dinner habit with chamomile and a gratitude line
    ("Why did I replace the wine-with-dinner habit with chamomile?", 2955),
    # 2971 shared-02973 Sunday self-care block is 16:00 to 19:00, no invites
    ("What is the Sunday self-care block and what are its rules?", 2985),
    # 2972 shared-02974 Grief letter to Nan written 2026-03-22 stays sealed
    ("What is the status of the grief letter to Nan written on 2026-03-22?", 2959),
    # 2973 shared-02975 Prefers Plum Village app for guided walking sessions
    ("Why do I prefer the Plum Village app for guided walking meditations?", 2966),
    # 2974 shared-02976 Mental-health day cap is one per quarter, taken preemptively
    ("What is my cap on mental-health days and when do I take them?", 2973),
    # 2975 shared-02977 Thought-record template has six columns that stuck after three weeks
    ("What columns are on the thought-record template I kept?", 2964),
    # 2976 shared-02978 Switched from Headspace sleep meds to Nothing Much Happens podcast
    ("Why did I switch from Headspace sleep meditations to the Nothing Much Happens podcast?", 2960),
    # 2977 shared-02979 Joined men's grief circle at Harbourside Centre 2026-04-02
    ("When did I join the men's grief circle at the Harbourside Centre?", 2959),
    # 2978 shared-02980 Stoic evening review is ten minutes: what went well, poorly, tomorrow
    ("What three prompts structure my ten-minute Stoic evening review?", 2955),
    # 2979 shared-02981 Morning anxiety spike at 05:40 treated as data, cold water and write it down
    ("How do I treat the 05:40 morning anxiety spike?", 2967),
    # 2980 shared-02982 Prefers open-monitoring on Saturdays to breath-anchor style
    ("Why do I prefer open-monitoring on Saturday mornings to the breath-anchor style?", 2989),
    # 2981 shared-02983 NOISE filler about where I was before kettle boiled
    ("What offhand aside referenced losing my place because the kettle boiled?", 2958),
    # 2982 shared-02984 DBT distress-tolerance card in wallet lists TIPP
    ("What does the DBT distress-tolerance card in my wallet list?", 2961),
    # 2983 shared-02985 Prefers silent zazen at Hampshire Zen group to chanted opening
    ("Why do I prefer the silent zazen sit at the Hampshire Zen group over the chant?", 2951),
    # 2984 shared-02986 Sleep-hygiene rules from CBT-i: bed only for sleep, fixed wake time
    ("Which CBT-i sleep-hygiene rules have I kept?", 2970),
    # 2985 shared-02987 Journaling streak hit 90 days on 2026-04-09
    ("When did the journaling streak hit 90 days?", 2965),
    # 2986 shared-02988 Finch app stays installed just for streak nudge
    ("Why do I keep the Finch app installed?", 2954),
    # 2987 shared-02989 4-7-8 beats Wim Hof for pre-meeting nerves
    ("Which breath pattern works better for pre-meeting nerves?", 2969),
    # 2988 shared-02990 Values clarification with Dr Halpern surfaced four anchors
    ("What four values anchors did the values clarification session surface?", 2963),
    # 2989 shared-02991 Morning meditation app rotates by weekday, Friday is silence
    ("How does the morning meditation app rotation go across weekdays?", 2953),
    # 2990 shared-02992 Grief wave at kitchen sink 2026-03-30, eleven minutes logged
    ("How did I handle the grief wave at the kitchen sink on 2026-03-30?", 2972),
    # 2991 shared-02993 Therapy fee is 80 pounds a session by standing order on the 1st
    ("How much is the therapy fee and how is it paid?", 2952),
    # 2992 shared-02994 Mindful-eating rule: twenty chews on first bite, fork down between
    ("What is the mindful-eating rule for the first bite?", 2955),
    # 2993 shared-02995 Sunday self-compassion break uses Kristin Neff's three steps
    ("What framework structures the Sunday self-compassion break?", 2955),
    # 2994 shared-02996 Replaced doom-scroll AM habit with Insight Timer kindness bell
    ("What did I replace the morning doom-scroll habit with?", 2950),
    # 2995 shared-02997 MBSR eight-week course at Riverside Hall ran 2026-01-13 through 2026-03-03
    ("When did the MBSR eight-week course at Riverside Hall run?", 2957),
    # 2996 shared-02998 Prefers morning anxiety check on paper to Daylio app
    ("Why do I prefer a paper morning anxiety check to the Daylio app?", 2956),
    # 2997 shared-02999 Retreat packing list is short: layers, sandals, ear plugs, notebook
    ("What is on the retreat packing list?", 2957),
    # 2998 shared-03000 Breath-anchor cue on lock screen reads 'long exhale', replaced by Rumi
    ("What did the breath-anchor lock-screen cue read and what replaced it?", 2961),
    # 2999 shared-03001 Adam Smith's Wealth of Nations, 1776, division of labour and invisible hand
    ("What did Adam Smith's 1776 Wealth of Nations recast political economy around?", 3000),
]


def emit() -> int:
    with SHARED.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    targets = [json.loads(lines[SHARED_OFFSET + i]) for i in range(100)]
    assert len(ENTRIES) == 100
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as out:
        for i, ((query, neg_off), tgt) in enumerate(zip(ENTRIES, targets), start=1):
            neg_row = json.loads(lines[neg_off])
            if neg_row["id"] == tgt["id"]:
                raise ValueError(f"negative row must differ from target at index {i}")
            row = {
                "id": f"ret-{ID_OFFSET + i:05d}",
                "source_id": tgt["id"],
                "query": query,
                "negative": neg_row["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
