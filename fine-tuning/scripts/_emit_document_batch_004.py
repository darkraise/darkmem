"""One-off emitter for document-stub batch-004.

Produces 50 rows with `doc_type` in {spec, legal, narrative}, writes to
`data/v2/documents/batch_004.tmp.jsonl`. Ids are allocated as
`doc-NNNNN` starting at ID_OFFSET + 1.

This follows the same emitter pattern as shared batch-001: entries are
embedded as Python data and serialised to JSONL in a single pass, so
the audit trail lives in version control alongside the output.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "documents" / "batch_004.tmp.jsonl"
ID_OFFSET = 150

# Each entry: (doc_type, text)
# doc_type in {"spec", "legal", "narrative"}. Text 40-120 words.
ROWS: list[tuple[str, str]] = [
    # ---------------- spec (17) ----------------
    ("spec",
     "1.  Introduction.  This document specifies the wire format for the Darkmem Memory Transport "
     "Protocol, Version 2 (MTP/2).  Implementations MUST accept frames of at most 65,535 octets "
     "and SHALL reject frames whose declared length exceeds the octets actually received.  Frames "
     "MAY be fragmented across TCP segments; receivers SHALL reassemble using the sequence number "
     "in octets 4 through 7.  The keywords MUST, SHOULD, and MAY in this document are to be "
     "interpreted as described in BCP 14."),
    ("spec",
     "2.  Frame Header.  Each MTP/2 frame begins with a fixed eight-octet header.  Octet 0 carries "
     "the version nibble in the high four bits and flags in the low four bits.  Octets 1 and 2 "
     "encode the payload length in network byte order.  Octet 3 is reserved and SHALL be "
     "transmitted as zero and ignored on receipt.  Octets 4 through 7 carry the monotonically "
     "increasing sequence number."),
    ("spec",
     "3.  Handshake.  On connection establishment the initiator SHALL send a HELLO frame whose "
     "payload is the ASCII literal \"MTP/2\" followed by a single space and the decimal capability "
     "bitmap.  The responder MUST reply within two seconds with a HELLO-ACK or else the initiator "
     "SHALL close the connection.  Capability bits undefined in this specification SHALL be set "
     "to zero and MUST be echoed unchanged by the responder."),
    ("spec",
     "4.  Keep-Alive.  A peer that has not transmitted a data frame for thirty seconds SHALL emit "
     "a PING frame carrying an opaque eight-octet token.  The remote peer MUST answer with a "
     "PONG frame echoing the same token within five seconds.  After two consecutive missed PONGs "
     "the local peer SHALL consider the session dead and MUST tear the connection down without "
     "transmitting further data frames."),
    ("spec",
     "5.  Error Codes.  Error frames carry a two-octet code in network byte order.  Codes 0x0001 "
     "through 0x00FF are reserved for transport errors and MUST be emitted only by the transport "
     "layer.  Codes 0x0100 through 0x0FFF are reserved for application errors.  Codes 0x1000 and "
     "above are experimental and SHALL NOT be used on the public Internet without prior IANA "
     "registration."),
    ("spec",
     "6.  Flow Control.  Each direction of an MTP/2 session maintains an independent credit window "
     "initialised to 65,536 octets.  A sender SHALL NOT transmit data frames whose cumulative "
     "payload exceeds the remaining credit.  Receivers MUST replenish credit by emitting WINDOW "
     "frames; a WINDOW frame carrying a zero increment is reserved for future use and SHALL be "
     "treated as a protocol error by current implementations."),
    ("spec",
     "7.  Compression.  Implementations MAY negotiate payload compression during the handshake by "
     "setting bit 3 of the capability bitmap.  When compression is active each data frame payload "
     "SHALL be a single DEFLATE stream terminated by its end-of-block marker.  Receivers MUST "
     "refuse frames larger than the negotiated maximum uncompressed size and SHALL report the "
     "condition with error code 0x0007."),
    ("spec",
     "8.  Authentication.  Mutual authentication SHALL be performed over TLS 1.3 using certificates "
     "issued by a trust anchor configured out of band.  Clients MUST present a certificate whose "
     "Subject Alternative Name matches the configured service identifier.  Servers MUST reject "
     "connections whose client certificate has been revoked according to the Online Certificate "
     "Status Protocol response cached no more than four hours prior."),
    ("spec",
     "9.  Session Resumption.  A peer MAY offer a resumption ticket of at most 128 octets in a "
     "RESUME frame sent immediately after HELLO-ACK.  Resumption tickets SHALL be opaque to the "
     "peer and MUST be bound cryptographically to the issuing session so that replay across "
     "sessions is detectable.  Implementations SHOULD expire tickets after twenty-four hours "
     "regardless of declared validity."),
    ("spec",
     "10.  Graceful Shutdown.  A peer that wishes to close a session cleanly SHALL transmit a "
     "BYE frame and then cease transmitting data frames.  The remote peer MUST drain outstanding "
     "data frames, acknowledge the BYE within one second, and then close the underlying TCP "
     "connection.  Implementations SHALL NOT send a RST-style close before both BYE frames have "
     "been exchanged except in response to a protocol violation."),
    ("spec",
     "11.  Identifier Format.  Memory identifiers exchanged over MTP/2 SHALL be sixteen-octet "
     "RFC 4122 version 7 UUIDs.  Endpoints MUST reject any identifier whose version nibble is "
     "not 0x7 and SHALL emit error code 0x0021.  Textual representations of identifiers outside "
     "the wire format SHOULD use the canonical hyphenated form and MUST preserve lowercase "
     "hexadecimal digits."),
    ("spec",
     "12.  Extensibility.  Future revisions of this specification MAY introduce new frame types "
     "by consuming currently reserved values of the type octet.  Implementations that encounter "
     "an unknown frame type SHALL respond with error code 0x0003 and MUST NOT attempt to process "
     "the payload.  A peer that receives three consecutive unknown-type errors SHOULD treat the "
     "session as incompatible and tear it down."),
    ("spec",
     "13.  Character Encoding.  Textual fields in control frames SHALL be encoded in UTF-8 "
     "without a byte order mark.  Receivers MUST reject frames that contain ill-formed UTF-8 "
     "sequences with error code 0x0009 and SHALL NOT attempt substitution of replacement "
     "characters.  Implementations SHOULD normalise identifiers to Unicode Normalization Form C "
     "prior to comparison but MUST NOT alter stored text."),
    ("spec",
     "14.  Time Values.  Timestamps transmitted in MTP/2 SHALL be 64-bit signed integers "
     "expressing microseconds since the Unix epoch.  Implementations MUST treat negative values "
     "as an error and SHALL report error code 0x0011.  Clock skew tolerance SHOULD be no greater "
     "than sixty seconds; peers that detect larger skew SHOULD emit a warning frame but MUST NOT "
     "terminate the session on that basis alone."),
    ("spec",
     "15.  Security Considerations.  This specification does not itself provide confidentiality; "
     "implementations SHALL run MTP/2 exclusively over TLS 1.3 or a successor mandated by IETF "
     "consensus.  Operators MUST NOT expose MTP/2 endpoints on unencrypted transports even "
     "within trusted networks.  Implementations SHOULD rate-limit handshake attempts from any "
     "single peer to no more than ten per minute."),
    ("spec",
     "16.  IANA Considerations.  This document requests IANA to register the TCP port 4712 as "
     "\"mtp2\" with the service name \"Darkmem Memory Transport\".  IANA SHALL also maintain the "
     "MTP/2 Frame Type registry with an initial allocation policy of \"Specification Required\".  "
     "Requests for values in the experimental range 0xF0 through 0xFF MAY be granted on a "
     "first-come-first-served basis."),
    ("spec",
     "17.  Backward Compatibility.  Implementations of MTP/2 MUST NOT interoperate with MTP/1 on "
     "the same TCP port because their handshake frames are indistinguishable in the first octet.  "
     "Operators who must support both versions SHALL expose MTP/1 on a separate port.  Future "
     "revisions SHALL introduce a version-negotiation octet so that single-port operation becomes "
     "feasible without ambiguity."),

    # ---------------- legal (17) ----------------
    ("legal",
     "1.  Definitions.  \"Agreement\" means this Darkmem Evaluation License Agreement, including "
     "all schedules attached hereto.  \"Licensor\" means Darkmem Labs, a limited liability "
     "company organised under the laws of the State of Delaware.  \"Licensee\" means the person "
     "or entity that accepts this Agreement.  \"Software\" means the Darkmem memory platform in "
     "object and source form, together with any updates, documentation, and sample data provided "
     "by Licensor hereunder."),
    ("legal",
     "2.  Grant of License.  Subject to the terms and conditions of this Agreement, Licensor "
     "hereby grants to Licensee a limited, non-exclusive, non-transferable, revocable licence to "
     "install and operate the Software solely for internal evaluation purposes, for a period of "
     "ninety (90) days following acceptance of this Agreement.  All rights not expressly granted "
     "to Licensee hereunder are reserved by Licensor, including without limitation rights of "
     "distribution, sublicensing, and commercial exploitation."),
    ("legal",
     "3.  Restrictions.  Licensee shall not, and shall not permit any third party to: (a) modify, "
     "translate, or create derivative works of the Software; (b) reverse engineer, decompile, or "
     "disassemble the Software, except to the extent such activity is expressly permitted by "
     "applicable law notwithstanding this limitation; (c) rent, lease, lend, sell, or sublicense "
     "the Software; or (d) remove or obscure any proprietary notices affixed to or contained "
     "within the Software."),
    ("legal",
     "4.  Confidentiality.  Licensee acknowledges that the Software, including but not limited to "
     "its source code, architecture, benchmarks, and performance characteristics, constitutes "
     "the confidential information of Licensor (hereinafter \"Confidential Information\").  "
     "Licensee shall protect such Confidential Information using at least the degree of care it "
     "uses to protect its own information of similar sensitivity, and in no event less than a "
     "reasonable degree of care."),
    ("legal",
     "5.  Ownership.  As between the parties, Licensor is and shall remain the sole and exclusive "
     "owner of all right, title, and interest in and to the Software and all intellectual "
     "property rights therein.  Nothing in this Agreement shall be construed as a transfer or "
     "assignment of ownership.  Licensee hereby assigns to Licensor any feedback, suggestions, or "
     "improvements it may provide concerning the Software, including without limitation all "
     "associated intellectual property rights."),
    ("legal",
     "6.  Term and Termination.  This Agreement shall commence on the date of acceptance and "
     "shall continue for the evaluation period set forth in Section 2 unless earlier terminated "
     "in accordance with this Section.  Either party may terminate this Agreement for any reason "
     "upon seven (7) days' written notice.  Upon termination, Licensee shall immediately cease "
     "all use of the Software and shall destroy all copies in its possession or control."),
    ("legal",
     "7.  Warranty Disclaimer.  THE SOFTWARE IS PROVIDED \"AS IS\" AND \"AS AVAILABLE\" WITHOUT "
     "WARRANTY OF ANY KIND, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE.  LICENSOR HEREBY "
     "DISCLAIMS ALL IMPLIED WARRANTIES, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF "
     "MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT.  LICENSOR "
     "DOES NOT WARRANT THAT THE SOFTWARE WILL BE ERROR-FREE OR THAT ITS OPERATION WILL BE "
     "UNINTERRUPTED."),
    ("legal",
     "8.  Limitation of Liability.  In no event shall Licensor be liable to Licensee for any "
     "indirect, incidental, special, consequential, or punitive damages, including without "
     "limitation damages for lost profits, lost revenue, lost data, or business interruption, "
     "arising out of or related to this Agreement, regardless of the theory of liability and "
     "even if Licensor has been advised of the possibility of such damages.  Licensor's aggregate "
     "liability hereunder shall not exceed one hundred United States dollars."),
    ("legal",
     "9.  Indemnification.  Licensee shall defend, indemnify, and hold harmless Licensor and its "
     "affiliates, officers, directors, employees, and agents from and against any and all "
     "claims, damages, liabilities, costs, and expenses, including reasonable attorneys' fees, "
     "arising out of or related to Licensee's breach of this Agreement, Licensee's use of the "
     "Software in violation of applicable law, or any allegation that data supplied by Licensee "
     "infringes the rights of any third party."),
    ("legal",
     "10.  Governing Law.  This Agreement shall be governed by and construed in accordance with "
     "the laws of the State of Delaware, without regard to its conflict-of-laws principles.  The "
     "parties irrevocably consent to the exclusive jurisdiction of the state and federal courts "
     "located in New Castle County, Delaware, for the resolution of any dispute arising out of "
     "or related to this Agreement.  The United Nations Convention on Contracts for the "
     "International Sale of Goods shall not apply."),
    ("legal",
     "11.  Privacy.  Licensor may collect diagnostic telemetry from the Software during the "
     "evaluation period, including but not limited to version identifiers, feature usage "
     "counters, and anonymised error reports.  Licensee hereby consents to such collection for "
     "the sole purpose of improving the Software.  Licensor shall not transmit Licensee data "
     "containing personal information to any third party except as required by law or as "
     "expressly authorised by Licensee in writing."),
    ("legal",
     "12.  Export Compliance.  Licensee represents and warrants that it is not located in, under "
     "the control of, or a national or resident of any country or region to which the export of "
     "the Software is prohibited under the laws of the United States.  Licensee further "
     "represents that it is not listed on any United States government list of prohibited or "
     "restricted parties, including without limitation the Specially Designated Nationals list "
     "maintained by the Office of Foreign Assets Control."),
    ("legal",
     "13.  Assignment.  Licensee shall not assign this Agreement, whether by operation of law or "
     "otherwise, without the prior written consent of Licensor; any purported assignment in "
     "violation of this Section shall be null and void.  Licensor may assign this Agreement in "
     "its entirety, without consent of Licensee, in connection with a merger, acquisition, "
     "corporate reorganisation, or sale of all or substantially all of Licensor's assets.  "
     "Subject to the foregoing, this Agreement shall bind and inure to the benefit of the "
     "parties and their respective successors."),
    ("legal",
     "14.  Force Majeure.  Neither party shall be liable for any failure or delay in the "
     "performance of its obligations under this Agreement, excepting payment obligations, to the "
     "extent such failure or delay is caused by an event beyond its reasonable control, "
     "including without limitation acts of God, war, terrorism, civil unrest, governmental "
     "action, labour disputes, fire, flood, earthquake, epidemic, or failure of the public "
     "Internet.  The affected party shall promptly notify the other and shall use reasonable "
     "efforts to mitigate."),
    ("legal",
     "15.  Entire Agreement.  This Agreement, together with any schedules attached hereto, "
     "constitutes the entire agreement between the parties with respect to the subject matter "
     "hereof and supersedes all prior or contemporaneous understandings, agreements, "
     "representations, and warranties, whether written or oral.  No modification, amendment, or "
     "waiver of any provision of this Agreement shall be effective unless in writing and signed "
     "by the party against whom the modification, amendment, or waiver is asserted."),
    ("legal",
     "16.  Notices.  All notices, requests, consents, and other communications required or "
     "permitted under this Agreement shall be in writing and shall be delivered by hand, by "
     "certified mail return receipt requested, or by nationally recognised overnight courier to "
     "the addresses set forth beneath the parties' signatures, or to such other address as a "
     "party may designate by written notice.  Notices shall be deemed delivered upon actual "
     "receipt or refusal of delivery."),
    ("legal",
     "17.  Survival.  The provisions of Sections 3 (Restrictions), 4 (Confidentiality), 5 "
     "(Ownership), 7 (Warranty Disclaimer), 8 (Limitation of Liability), 9 (Indemnification), "
     "10 (Governing Law), and this Section 17 shall survive any expiration or termination of "
     "this Agreement for any reason.  Any other provision that by its nature is intended to "
     "survive shall also survive notwithstanding the expiration or termination of this "
     "Agreement."),

    # ---------------- narrative (16) ----------------
    ("narrative",
     "The kitchen tiles still held the heat of the afternoon when Mara pushed the window open. "
     "Outside, the jacaranda was shedding its last purple flowers onto the neighbour's Renault, "
     "and somewhere down the street a child was practising the recorder, the same three notes "
     "over and over.  She set the kettle on the hob and watched the gas flower blue.  For the "
     "first time in weeks the flat felt like hers again, emptied of the small, irritating "
     "presences of other people."),
    ("narrative",
     "Ivan had never trusted the lift in his building, so he took the stairs at a pace that "
     "suggested some internal clock was always three minutes fast.  On the fourth landing he "
     "paused by the window that overlooked the courtyard, breath catching, and noticed that "
     "someone had left a pot of basil on the sill.  The leaves were limp with thirst.  He "
     "filled a paper cup at the communal tap and poured it slowly, feeling oddly tender toward "
     "this anonymous plant."),
    ("narrative",
     "The train pulled out of Bologna in a slow, reluctant way, as if the city itself were "
     "tugging at the couplings.  Lena had a window seat and a thermos of bitter coffee she had "
     "bought at the kiosk.  Somewhere south of Florence the rain began, thin silver lines across "
     "the glass, and the landscape blurred into tunnels and olive groves.  She thought about her "
     "grandmother's house, and the key hidden under a broken terracotta pot by the gate, and "
     "wondered whether anyone else still knew."),
    ("narrative",
     "The fisherman's dog had learned to sit exactly three steps back from the nets, in the "
     "place where the spray could not reach him.  He watched the gulls with the patience of "
     "something that has weighed all the available options and chosen stillness.  When the boat "
     "came in at dusk, riding low under the day's catch, he rose, shook the sleep from his coat, "
     "and padded down the slipway to meet it.  The old man called him by a name nobody else "
     "used."),
    ("narrative",
     "On the last day of term Kofi found a single sheet of paper tucked into his locker, folded "
     "twice, unsigned.  The handwriting was small and careful, the kind that belonged to "
     "someone who had practised being invisible.  He read it in the corridor while the bell "
     "rang and a tide of students surged past him toward the doors.  By the time he looked up, "
     "the corridor was almost empty, and the sun through the stained-glass window lay in "
     "amber-and-green lozenges at his feet."),
    ("narrative",
     "My grandmother kept every letter my grandfather ever sent her, bundled with string in a "
     "shoebox under the wardrobe.  She never read them aloud, not even on their anniversary.  "
     "When I was ten she opened the box in front of me for the first time, took out one "
     "envelope, and touched its corner the way a priest might touch a relic.  Then she put it "
     "back without showing me a single word inside.  Some things, she said, are meant to be "
     "kept, not explained."),
    ("narrative",
     "The old darkroom smelled of stop bath and dust, and the red safelight turned everything "
     "the colour of a memory half-recalled.  Hana hung the negatives to dry on the wire strung "
     "across the ceiling, clipping each one with a wooden peg.  She had taken the photographs "
     "in a month she did not like to think about, and seeing the images emerge in the tray felt "
     "like meeting a version of herself she had been avoiding.  Outside, the city traffic "
     "moaned on, indifferent."),
    ("narrative",
     "By the time we reached the ridge the wind had turned and the clouds were spilling over "
     "the far peaks like foam from a kettle boiling too hard.  Sanjay stopped walking and stood "
     "with his hands on his hips, looking at the weather the way a man might look at a bill he "
     "had been expecting.  He said nothing for a long minute.  Then he turned and started down "
     "the way we had come, and I followed, trying not to feel the altitude in my knees."),
    ("narrative",
     "The bakery opened at four in the morning, and by five the street outside smelled of "
     "sourdough and wet cobblestones.  Camille tied her apron twice because the knot always "
     "came loose by ten, pulled her hair back, and began weighing the rye.  The radio murmured "
     "overnight football results from a country she had never visited.  Somewhere in the back "
     "of the oven a loaf was singing, the way good bread does, a faint crackle as the crust "
     "cooled."),
    ("narrative",
     "Felix had not expected the museum to be empty.  He wandered from one gallery to the next, "
     "hearing only the squeak of his own shoes on the polished floor and the occasional sigh of "
     "the air handlers.  In a small room at the back he found a single painting he did not "
     "recognise: a dark harbour under a greenish sky, a figure on the jetty almost swallowed by "
     "the weather.  He stood in front of it for longer than he meant to, and then he did not "
     "stop thinking about it for weeks."),
    ("narrative",
     "The cat arrived in October, thin and mostly black, with one ear folded as if somebody had "
     "tried to post him through a letterbox.  He would not come inside for three days.  On the "
     "fourth he walked across the kitchen as though he had always lived there, sat on the "
     "newspaper my father was reading, and fell asleep.  My father, who had said many firm "
     "things about cats over the years, put down his coffee and did not move for an hour, in "
     "case he woke him."),
    ("narrative",
     "Anya practised the cello in the laundry room because the concrete walls flattered her "
     "tone.  At ten on a Sunday morning the building was asleep except for a single "
     "tumble-dryer thumping a slow heartbeat through the wall.  She played the opening of the "
     "Elgar badly, and then better, and then badly again.  Her teacher had told her that a "
     "phrase was not finished until she could hear the silence after it.  She was beginning, "
     "at last, to believe him."),
    ("narrative",
     "The lighthouse keeper's name was Inigo and he had not spoken to a mainland person in "
     "eleven weeks.  He kept a journal in tiny, ruled handwriting, less because he feared "
     "forgetting and more because the act of writing was a kind of company.  On the evening the "
     "storm came in he wrote: \"wind NNW, visibility half a mile, a gull the colour of bone on "
     "the lantern gallery.\"  He closed the book, listened to the sea for a while, and then lit "
     "the lamp."),
    ("narrative",
     "In the summer of her twelfth year Priya learned to ride a bicycle on a path of packed red "
     "earth behind her aunt's house.  Her cousin ran alongside, one hand on the saddle, until "
     "one afternoon he simply let go without telling her.  She pedalled for a full minute "
     "before she realised she was alone with her balance, and in the shock of it she almost "
     "forgot how.  Years later she remembered the heat, the dust, and the particular sound of "
     "his laughter behind her."),
    ("narrative",
     "The bus from Tbilisi climbed the pass at a pace that made the goats on the verge look "
     "hurried by comparison.  Nino had given up her window seat to an old woman carrying a "
     "basket of cheese wrapped in a dish towel.  Somewhere near the top the engine made a noise "
     "like a dog clearing its throat, and the driver switched it off and let us coast for a "
     "while.  Nobody seemed alarmed.  The mountains, enormous and indifferent, went on being "
     "mountains."),
    ("narrative",
     "On Thursday evenings my father walked to the river with a folding stool and a book he "
     "never actually read.  He would sit where the willow leaned out over the water, the stool "
     "sinking unevenly into the bank, and watch the swifts cut their low arcs at the insects.  "
     "Once, when I was small, I asked him what he was thinking about.  He considered the "
     "question for a long time, as if it deserved respect, and then he said: nothing I can "
     "usefully tell you yet."),
]


def main() -> None:
    assert len(ROWS) == 50, f"expected 50 rows, got {len(ROWS)}"
    counts = {"spec": 0, "legal": 0, "narrative": 0}
    for dt, _ in ROWS:
        counts[dt] += 1
    assert counts == {"spec": 17, "legal": 17, "narrative": 16}, counts

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for idx, (doc_type, text) in enumerate(ROWS, start=1):
        doc_id = f"doc-{ID_OFFSET + idx:05d}"
        wc = len(text.split())
        assert 40 <= wc <= 120, f"{doc_id} has {wc} words, out of 40-120 range"
        row = {"id": doc_id, "doc_type": doc_type, "text": text}
        lines.append(json.dumps(row, ensure_ascii=False))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} rows to {OUT}")


if __name__ == "__main__":
    main()
