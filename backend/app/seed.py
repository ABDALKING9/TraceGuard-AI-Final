"""Synthetic demonstration dataset for TraceGuard AI.

Every account, record, case, relationship and note in this module is fictional.
No real platform account, real person, real message or real suspected-criminal
profile is represented.  The seed is deterministic and idempotent: running it
twice does not duplicate accounts, records, cases, relationships or notes, and it
never overwrites analyst decisions (review status, notes) that already exist.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, select

from .db.database import Base, engine, SessionLocal
from .models import (Platform, Account, ContentRecord, Case, CaseRecord,
                     RelationshipEdge, AnalystNote, Analysis)
from .services.analysis import analyze_text, encode_analysis, ENGINE_VERSION

PLATFORM_NAMES = ["Telegram", "WhatsApp", "Instagram"]

REVIEW_STATUSES = {
    "P": "Pending Review",
    "R": "Reviewed — No Action",
    "F": "Further Review Required",
}

# Deterministic clock for the demonstration corpus (naive UTC, matching SQLite storage).
SEED_EPOCH = datetime(2026, 9, 22, 6, 0, 0)

# --------------------------------------------------------------------------------------
# Legacy demonstration records - preserved verbatim so existing demo rows are reused.
# --------------------------------------------------------------------------------------
LEGACY_RECORDS = [
    ("tg_amber", "post", "Community update: our fictional anti-drug awareness event is this weekend.", "R"),
    ("tg_birch", "post", "For the classroom simulation, a price list and delivery schedule are shown in the example.", "F"),
    ("tg_cedar", "message", "Public health researchers discuss prescription safety and recovery support.", "R"),
    ("tg_dune", "post", "New catalogue available; message for details about the fictional demonstration.", "P"),
    ("tg_elm", "message", "Orders and payment steps are described in this fictional test scenario.", "P"),
    ("wa_finch", "message", "The school group is organizing a drug prevention campaign.", "R"),
    ("wa_grove", "message", "Fictional exercise: supply and delivery terminology used for analyst training.", "P"),
    ("wa_hazel", "message", "Please share the public health report about rehabilitation resources.", "R"),
    ("wa_iris", "message", "Our classroom example lists 20 packs and a dispatch note.", "P"),
    ("wa_juniper", "message", "Not selling anything; this is a discussion of a news report.", "R"),
    ("ig_kite", "post", "A fictional photo caption for a community clean-up event.", "P"),
    ("ig_linden", "post", "Catalogue update and DM for details, used only in this synthetic demo.", "P"),
    ("ig_maple", "post", "Prescription safety awareness: ask a licensed pharmacist for advice.", "R"),
    ("ig_north", "post", "Example text mentions 50 grams in a fictional contextual exercise.", "P"),
    ("ig_oak", "post", "Orders, price list, and delivery language in a synthetic analyst training example.", "F"),
    ("tg_pine", "message", "Research seminar about public health and medical research.", "R"),
    ("wa_quartz", "message", "A benign message about weekend plans and a family dinner.", "P"),
    ("ig_river", "post", "A fictional promotional caption with a catalogue and payment mention.", "P"),
    ("tg_slate", "post", "This is a fictional example, not selling anything.", "R"),
    ("wa_thyme", "message", "Community support and recovery services are available locally.", "P"),
    ("ig_umber", "post", "Classroom exercise: orders, supply, and 10 packs mentioned in one example.", "F"),
    ("tg_vale", "message", "A news report discusses illegal trafficking and enforcement policy.", "R"),
    ("wa_willow", "message", "The fictional exercise includes dispatch, price list, and payment wording.", "F"),
    ("ig_xenia", "post", "A photo of a park with a short caption about nature.", "P"),
    ("tg_yarrow", "post", "Menu and catalogue wording appears in a synthetic record.", "P"),
    ("wa_zephyr", "message", "Anti-drug campaign volunteers meet at noon.", "R"),
    ("ig_ash", "post", "Fictional post about 2 kg of donated food for a community kitchen.", "P"),
    ("tg_bluff", "message", "Public health and rehabilitation resources are discussed.", "R"),
    ("wa_cloud", "message", "For this fictional test, available for sale appears as an example phrase.", "P"),
    ("ig_dawn", "post", "A school assignment describes a fictional order and delivery scenario.", "F"),
    ("tg_echo", "message", "An analyst-training sample contains a price list and 30 units.", "F"),
    ("wa_field", "message", "Weekend football practice at the campus ground.", "R"),
    ("ig_glade", "post", "DM for details about the fictional photography club catalogue.", "P"),
    ("tg_harbor", "post", "Medical research summary about treatment and recovery.", "R"),
    ("wa_indigo", "message", "The simulation includes supply, payment, and dispatch terms.", "F"),
    ("ig_jade", "post", "A benign caption about a sunset and friends.", "P"),
    ("tg_knoll", "message", "The fictional classroom example references 100 grams and delivery.", "P"),
    ("wa_lake", "message", "This anti-drug poster encourages students to seek support.", "R"),
    ("ig_moss", "post", "A synthetic catalogue example with order and price list phrases.", "F"),
    ("tg_nook", "post", "A community channel announces a public health talk.", "R"),
    ("wa_opal", "message", "Fictional scenario: 5 packs, delivery, and payment.", "F"),
]

# --------------------------------------------------------------------------------------
# Expanded demonstration corpus.
#
# The 109 records below are grouped by the risk band the rule engine is expected to
# produce.  The groups are:
#   A  no configured indicator matched
#   B  exactly one indicator matched
#   C  two low-weight indicators matched
#   D  benign-context wording reduced an indicator match
#   E  two or three indicators matched (Moderate band)
#   F  three indicators matched (Moderate band)
#   G  three indicators matched (Elevated band)
#   H  four indicators matched (Elevated band)
#   I  four or five indicators matched (Elevated band)
#   J  four or more indicators matched including a payment-method indicator (High band)
# --------------------------------------------------------------------------------------
NEW_RECORD_TEXTS = [
    # A - no indicator matched
    ("Community garden volunteers met on Saturday to replant the shared herb beds.", "P"),
    ("A quiet photograph of rain running down a library window.", "P"),
    ("The neighbourhood book club meets on the first Thursday of every month.", "P"),
    ("Sharing a photo of my sourdough starter and its first successful loaf.", "R"),
    ("Sunrise over the harbour with the fishing boats still returning.", "P"),
    ("Reminder that the choir rehearsal has moved to the community hall.", "R"),
    ("My cat has claimed the warmest cushion in the house again.", "P"),
    ("Trail notes from a weekend walk through the pine reserve.", "R"),
    ("The repair cafe at the library is open on Sunday afternoons.", "P"),
    ("A short thank-you note to the volunteers who ran the blood donation drive.", "R"),
    ("Evening light on the old stone bridge.", "P"),
    ("The local school announces its summer reading challenge.", "R"),
    # B - exactly one indicator matched
    ("In this fictional training sample the phrase available for sale appears once.", "P"),
    ("A synthetic caption that mentions a catalogue of community artwork.", "R"),
    ("Sample message quoting a single quantity phrase: 40 packs.", "P"),
    ("Fictional notice about a wholesale cooperative of local growers.", "R"),
    ("In the demo transcript the word payment is used once.", "P"),
    ("A synthetic caption with a single mention of dispatch times.", "R"),
    ("Training example that mentions reach me once.", "P"),
    ("Demo text using the phrase call me exactly once.", "R"),
    ("Synthetic example containing the single phrase text me.", "P"),
    ("Sample line that contains drop off once.", "R"),
    # C - two low-weight indicators matched
    ("Fictional line combining a menu reference with 12 units for the workshop.", "P"),
    ("Demo caption: a catalogue listing of 6 packs for the food bank.", "R"),
    ("Training line with a catalog entry and 15 packs of paper.", "P"),
    ("Synthetic example with a menu plan and 3 units per session.", "R"),
    ("Fictional note pairing a catalogue reference with 25 units.", "P"),
    ("Demo text with a menu mention and 8 grams of pigment.", "R"),
    # D - benign context reduced the contribution
    ("Fictional example, not selling: a price list and delivery schedule for a charity sale.", "P"),
    ("Public health notice about a fictional example with orders and 5 packs listed.", "R"),
    ("Medical research update that includes supply and payment wording in a fictional example.", "P"),
    # E - two or three indicators matched (Moderate band)
    ("Fictional promo: a price list with delivery options for the pop-up.", "P"),
    ("Training example combining orders with a drop off schedule.", "R"),
    ("Synthetic caption quoting a menu and a payment step.", "P"),
    ("Demo line with 40 packs and a dispatch note.", "R"),
    ("Fictional listing: available for sale and delivery across the district.", "P"),
    ("Synthetic sample pairing a catalogue with orders for 30 units.", "R"),
    ("Demo caption: 12 packs, orders open, dispatch tomorrow.", "P"),
    ("Fictional line with wholesale supply and a payment reference.", "R"),
    ("Synthetic caption: catalogue of orders for 25 packs for the school drive.", "P"),
    ("Training line mentioning 60 grams and a price list.", "R"),
    ("Fictional poster: wholesale orders and a dispatch window.", "P"),
    ("Demo message: 5 packs, a menu, and payment details.", "R"),
    ("Fictional caption about 100 grams, orders, and a catalogue.", "P"),
    ("Training sample: drop off times plus payment instructions.", "R"),
    ("Synthetic caption: a menu plus orders for the weekend.", "P"),
    ("Fictional transcript with 15 packs and wholesale wording.", "R"),
    ("Fictional notice: a price list and a wholesale rate card.", "P"),
    ("Demo caption: 20 units, a menu, and orders.", "R"),
    # F - three indicators matched (Moderate band)
    ("Demo caption: a catalogue, orders, and 10 packs for the drive.", "P"),
    ("Training sample: supply, a menu, and 25 units.", "R"),
    ("Fictional line: wholesale supply, orders, and 20 units.", "P"),
    ("Demo message with a catalogue, payment, and 5 packs.", "R"),
    ("Synthetic caption: a menu, orders, and 30 units.", "P"),
    ("Training text with a catalogue, dispatch, and 12 packs.", "R"),
    ("Fictional advert: orders, a menu, and a drop off point.", "P"),
    ("Demo sample: payment, supply, and 15 packs listed.", "R"),
    ("Training caption with a menu, orders, and dispatch.", "P"),
    ("Fictional line: a catalogue, payment, and a drop off.", "R"),
    ("Synthetic caption with a menu, 20 packs, and orders.", "P"),
    ("Demo transcript: a catalogue, dispatch, and payment.", "R"),
    ("Fictional listing: a menu, supply, and 8 units.", "P"),
    ("Training line with a menu, a drop off, and 10 packs.", "R"),
    ("Synthetic caption: a catalogue, 15 packs, and payment.", "P"),
    # G - three indicators matched (Elevated band)
    ("Fictional promo: orders, delivery, and text me to reserve.", "F"),
    ("Training line: a price list, dispatch, and call me details.", "F"),
    ("Synthetic caption: wholesale, crypto, and payment wording.", "F"),
    ("Demo transcript: orders, delivery, and a gift card option.", "F"),
    ("Fictional advert: a price list, dispatch, and a bitcoin note.", "F"),
    ("Synthetic caption: orders, delivery, and text me.", "F"),
    ("Training sample: a menu, orders, and a gift card.", "F"),
    ("Fictional line: a catalogue, crypto, and text me.", "F"),
    ("Demo text: wholesale supply, 20 packs, and a gift card.", "F"),
    ("Training caption: dispatch, a price list, and a crypto mention.", "F"),
    # H - four indicators matched (Elevated band)
    ("Fictional promo: a catalogue, orders, 10 packs, and delivery.", "P"),
    ("Training line: a menu, orders, dispatch, and 5 packs.", "P"),
    ("Synthetic caption: orders, 15 packs, delivery, and text me.", "F"),
    ("Demo text: a catalogue, supply, 20 packs, and payment.", "P"),
    ("Fictional advert: a menu, orders, dispatch, and a gift card.", "F"),
    ("Training sample: a catalogue, 10 packs, delivery, and call me.", "P"),
    ("Synthetic caption: a menu, orders, 25 units, and crypto.", "F"),
    ("Fictional line: wholesale, 30 units, delivery, and a gift card.", "F"),
    ("Demo transcript: a catalogue, orders, 12 packs, and bitcoin.", "F"),
    ("Training caption: a menu, supply, 8 packs, and text me.", "P"),
    ("Synthetic sample: orders, wholesale, 40 packs, and a catalogue.", "P"),
    ("Fictional advert: a catalogue, delivery, 15 units, and reach me.", "P"),
    # I - four or five indicators matched (Elevated band)
    ("Fictional ad: orders, a menu, 10 packs, and text me.", "P"),
    ("Training line: a catalogue, 15 packs, text me, and shipping to the studio.", "P"),
    ("Synthetic caption: payment, a gift card, orders, and 20 packs.", "F"),
    ("Demo transcript: supply, dispatch, 25 units, and a gift card.", "F"),
    ("Training caption: a menu, orders, 10 packs, and bitcoin.", "F"),
    ("Synthetic line: wholesale, 30 units, text me, and shipping to the studio.", "P"),
    ("Fictional offer: orders, payment, a gift card, and call me.", "F"),
    ("Training line: a catalogue, 40 packs, reach me, and crypto.", "F"),
    # J - payment-method indicator present (High band)
    ("Fictional ad: orders, delivery, text me, and a gift card.", "F"),
    ("Training line: a price list, dispatch, reach me, and bitcoin.", "F"),
    ("Synthetic caption: orders, 10 packs, crypto, delivery, and text me.", "F"),
    ("Demo transcript: a menu, payment, dispatch, 20 packs, and a gift card.", "F"),
    ("Fictional offer: wholesale supply, orders, a gift card, and call me.", "F"),
    ("Synthetic caption: orders, 25 units, crypto, shipping to the depot, and delivery.", "F"),
    ("Training sample: a price list, delivery, 15 packs, bitcoin, and reach me.", "F"),
    ("Fictional ad: a menu, orders, dispatch, a gift card, and text me.", "F"),
    ("Synthetic line: wholesale, orders, 30 units, crypto, and call me.", "F"),
    ("Training caption: a catalogue, orders, 10 packs, a gift card, and shipping to the hub.", "F"),
    ("Fictional offer: price list, dispatch, crypto, reach me, and 20 packs.", "F"),
    ("Synthetic caption: payment, supply, 12 packs, a gift card, and ship to the office.", "F"),
    ("Demo transcript: a menu, orders, 40 units, crypto, and text me.", "F"),
    ("Training line: wholesale, orders, 25 units, bitcoin, and shipping to the unit.", "F"),
    ("Synthetic offer: a catalogue, payment, dispatch, a gift card, text me, and 8 packs.", "F"),
]

# Groups of the expanded corpus, used to attach records to demonstration cases.
GROUP_RANGES = {
    "A": (0, 12), "B": (12, 22), "C": (22, 28), "D": (28, 31),
    "E": (31, 49), "F": (49, 64), "G": (64, 74), "H": (74, 86),
    "I": (86, 94), "J": (94, 109),
}

# Additional synthetic accounts. 34 handles, each carrying two demonstration records.
NEW_ACCOUNT_HANDLES = [
    "tg_amberwood", "tg_bramblewood", "tg_cobblestone", "tg_dogwood",
    "tg_elderwood", "tg_flintwood", "tg_gravelwood", "tg_heatherwood",
    "tg_ironwood", "tg_juniperwood", "tg_kestrelwood", "tg_larchwood",
    "wa_maplewood", "wa_nutmegwood", "wa_olivewood", "wa_pinewood",
    "wa_quincewood", "wa_rowanwood", "wa_sycamorewood", "wa_thistlewood",
    "wa_umberwood", "wa_vertexwood", "wa_willowwood",
    "ig_acaciawood", "ig_bramblewood", "ig_cornflowerwood", "ig_dahliawood",
    "ig_foxglovewood", "ig_gorsewood", "ig_hazelwood", "ig_indigowood",
    "ig_juniperwood", "ig_kalmiawood", "ig_lilacwood",
]

LEGACY_CASES = [
    ("Synthetic review — transactional language",
     "Academic demo case for reviewing contextual indicators.", "Open"),
    ("Synthetic review — benign context",
     "Academic demo case demonstrating benign-context handling.", "Under Review"),
    ("Synthetic review — mixed indicators",
     "Academic demo case with multiple configured indicators.", "Open"),
]

# (title, description, status, group, start, count)
NEW_CASES = [
    ("Synthetic review — catalogue and quantity wording",
     "Academic demo case covering catalogue plus quantity indicator matches.", "Open", "C", 0, 3),
    ("Synthetic review — dispatch and contact handoff",
     "Academic demo case covering dispatch and direct contact-handoff wording.", "Under Review", "G", 0, 4),
    ("Synthetic review — payment method indicators",
     "Academic demo case covering payment-method indicator matches.", "Open", "G", 4, 4),
    ("Synthetic review — shipping destination indicators",
     "Academic demo case covering shipping and delivery-destination wording.", "Open", "I", 1, 4),
    ("Synthetic review — multi-indicator cluster",
     "Academic demo case with several configured indicators inside single records.", "Under Review", "H", 0, 4),
    ("Synthetic review — benign public health context",
     "Academic demo case demonstrating benign-context score reduction.", "Open", "D", 0, 3),
    ("Synthetic review — classroom simulation set",
     "Academic demo case built from classroom-style synthetic wording.", "Open", "A", 0, 4),
    ("Synthetic review — community announcement set",
     "Academic demo case built from neutral community announcement wording.", "Closed", "A", 4, 4),
    ("Synthetic review — warehouse vocabulary set",
     "Academic demo case covering wholesale and dispatch vocabulary.", "Open", "E", 0, 4),
    ("Synthetic review — encrypted payment set",
     "Academic demo case covering crypto and gift-card wording.", "Under Review", "J", 0, 4),
    ("Synthetic review — high-priority review queue",
     "Academic demo case prioritising records scored in the High band.", "Under Review", "J", 4, 4),
    ("Synthetic review — moderate review queue",
     "Academic demo case prioritising records scored in the Moderate band.", "Open", "F", 0, 4),
    ("Synthetic review — low priority sweep",
     "Academic demo case covering Low-band records with a single indicator.", "Closed", "B", 0, 4),
    ("Synthetic review — cross-platform wording set",
     "Academic demo case spanning all three simulated platforms.", "Open", "E", 8, 4),
    ("Synthetic review — Instagram caption indicators",
     "Academic demo case drawn from simulated Instagram captions.", "Open", "C", 3, 3),
    ("Synthetic review — Telegram channel indicators",
     "Academic demo case drawn from simulated Telegram channel posts.", "Open", "B", 4, 4),
    ("Synthetic review — WhatsApp group indicators",
     "Academic demo case drawn from simulated WhatsApp group messages.", "Under Review", "E", 4, 4),
    ("Synthetic review — single-indicator sweep",
     "Academic demo case covering records with exactly one matched indicator.", "Open", "B", 6, 4),
    ("Synthetic review — no-indicator benign set",
     "Academic demo case covering records with no matched indicators.", "Closed", "A", 8, 4),
    ("Synthetic review — quantity and weight set",
     "Academic demo case covering quantity and weight expressions.", "Open", "F", 8, 4),
    ("Synthetic review — contact handoff escalation",
     "Academic demo case escalated for direct contact-handoff wording.", "Under Review", "H", 4, 4),
    ("Synthetic review — promotional catalogue set",
     "Academic demo case covering promotional catalogue wording.", "Open", "G", 8, 2),
    ("Synthetic review — mixed context set",
     "Academic demo case mixing benign and indicator-bearing records.", "Open", "D", 0, 2),
    ("Synthetic review — training corpus subset A",
     "Academic demo case for analyst training exercises.", "Open", "E", 12, 4),
    ("Synthetic review — training corpus subset B",
     "Academic demo case for analyst training exercises.", "Open", "F", 4, 4),
    ("Synthetic review — scheduled sweep",
     "Academic demo case used for a recurring analyst review sweep.", "Closed", "H", 8, 4),
    ("Synthetic review — follow-up after escalation",
     "Academic demo case reopened for analyst follow-up.", "Open", "I", 4, 4),
]

NOTE_TEMPLATES = [
    ("Pattern match reviewed against the demonstration corpus; no real-world source exists for this record.",
     "Reviewed — No Action"),
    ("Indicator wording appears in a synthetic training record; retained for analyst review only.",
     "Pending Review"),
    ("Escalated for context because the synthetic text combines several configured indicators.",
     "Further Review Required"),
    ("Context checked against benign public-health language; the score reduction behaved as expected.",
     "Reviewed — No Action"),
]

# The two relationships created by the original seed are preserved exactly.
LEGACY_RELATIONSHIPS = [
    ("tg_amber", "tg_birch", "shared_synthetic_feature", "demo-tag-alpha",
     "Synthetic seed explicitly assigns this shared demo feature."),
    ("tg_dune", "tg_elm", "synthetic_interaction", "training-link-01",
     "Synthetic seed explicitly defines this fictional interaction."),
]

# Clusters of demonstration accounts. Consecutive members of a cluster are linked.
RELATIONSHIP_CLUSTERS = [
    ["wa_finch", "wa_grove", "wa_hazel", "wa_iris", "wa_juniper"],
    ["ig_kite", "ig_linden", "ig_maple", "ig_north", "ig_oak"],
    ["tg_pine", "tg_slate", "tg_vale", "tg_yarrow", "tg_bluff"],
    ["wa_thyme", "wa_zephyr", "wa_cloud", "wa_field", "wa_indigo"],
    ["ig_umber", "ig_xenia", "ig_ash", "ig_dawn", "ig_glade"],
    ["tg_echo", "tg_harbor", "tg_knoll", "tg_nook", "tg_amberwood"],
    ["wa_lake", "wa_opal", "wa_maplewood", "wa_nutmegwood", "wa_olivewood"],
    ["ig_jade", "ig_moss", "ig_acaciawood", "ig_bramblewood", "ig_cornflowerwood"],
    ["tg_bramblewood", "tg_cobblestone", "tg_dogwood", "tg_elderwood", "tg_flintwood"],
    ["wa_pinewood", "wa_quincewood", "wa_rowanwood", "wa_sycamorewood", "wa_thistlewood"],
    ["ig_dahliawood", "ig_foxglovewood", "ig_gorsewood", "ig_hazelwood", "ig_indigowood"],
    ["tg_gravelwood", "tg_heatherwood", "tg_ironwood", "tg_juniperwood", "tg_kestrelwood"],
    ["wa_umberwood", "wa_vertexwood", "wa_willowwood", "tg_larchwood"],
    ["ig_juniperwood", "ig_kalmiawood", "ig_lilacwood", "tg_amberwood"],
]

RELATIONSHIP_TYPES = [
    "shared_synthetic_feature", "synthetic_interaction", "shared_indicator_profile",
    "cross_posting_link", "shared_contact_channel", "shared_catalogue_reference",
]
SHARED_FEATURES = [
    "tag-bravo", "tag-charlie", "tag-delta", "tag-echo", "link-02", "link-03",
    "link-04", "profile-echo", "profile-foxtrot", "channel-04", "channel-05",
    "catalogue-06", "catalogue-07", "indicator-profile-a", "indicator-profile-b",
]
EVIDENCE_TEMPLATES = [
    "Synthetic seed explicitly records a shared {feature} between the two demonstration accounts.",
    "The demonstration corpus pairs these accounts through the {feature} indicator grouping.",
    "Fictional training data links these accounts under {feature}; no real-world contact exists.",
    "Synthetic relationship created for the demonstration graph using {feature}.",
]


def platform_for_handle(handle: str) -> str:
    if handle.startswith("tg_"):
        return "Telegram"
    if handle.startswith("wa_"):
        return "WhatsApp"
    return "Instagram"


def build_sample_records() -> list[tuple[str, str, str, str]]:
    """Return the ordered (handle, record_type, content_text, review_status_code) list."""
    records = [(h, t, c, s) for h, t, c, s in LEGACY_RECORDS]
    legacy_handles = [h for h, _, _, _ in LEGACY_RECORDS]
    for index, (text, status_code) in enumerate(NEW_RECORD_TEXTS):
        if index < len(legacy_handles):
            handle = legacy_handles[index]
        else:
            handle = NEW_ACCOUNT_HANDLES[(index - len(legacy_handles)) // 2]
        record_type = "message" if index % 3 == 0 else "post"
        records.append((handle, record_type, text, status_code))
    return records


def build_relationships() -> list[tuple[str, str, str, str, str]]:
    """Return the ordered relationship tuples used to seed the demonstration graph."""
    relationships = list(LEGACY_RELATIONSHIPS)
    index = 0
    for cluster in RELATIONSHIP_CLUSTERS:
        for position in range(len(cluster) - 1):
            relationship_type = RELATIONSHIP_TYPES[index % len(RELATIONSHIP_TYPES)]
            feature = SHARED_FEATURES[index % len(SHARED_FEATURES)]
            evidence = EVIDENCE_TEMPLATES[index % len(EVIDENCE_TEMPLATES)].format(feature=feature)
            relationships.append((cluster[position], cluster[position + 1], relationship_type, feature, evidence))
            index += 1
    return relationships


def seed():
    Base.metadata.create_all(bind=engine)
    sample_records = build_sample_records()
    with SessionLocal() as db:
        platforms = {}
        for name in PLATFORM_NAMES:
            platform = db.scalar(select(Platform).where(Platform.name == name))
            if platform is None:
                platform = Platform(name=name, description=f"Simulated {name} source", is_simulated=True)
                db.add(platform)
                db.flush()
            platforms[name] = platform

        accounts: dict[str, Account] = {}
        for handle, _, _, _ in sample_records:
            if handle in accounts:
                continue
            platform = platforms[platform_for_handle(handle)]
            account = db.scalar(select(Account).where(Account.platform_id == platform.id,
                                                      Account.username == handle))
            if account is None:
                account = Account(platform_id=platform.id, username=handle,
                                  display_name=f"Fictional {handle.title()}",
                                  account_type="user", is_synthetic=True)
                db.add(account)
                db.flush()
            accounts[handle] = account
        db.flush()

        records: list[ContentRecord] = []
        for index, (handle, record_type, content, status_code) in enumerate(sample_records):
            account = accounts[handle]
            record = db.scalar(select(ContentRecord).where(ContentRecord.account_id == account.id,
                                                           ContentRecord.content_text == content))
            if record is None:
                record = ContentRecord(
                    account_id=account.id, record_type=record_type, content_text=content,
                    conversation_key=f"synthetic-room-{(account.id % 5) + 1}" if record_type == "message" else None,
                    created_at=SEED_EPOCH + timedelta(hours=6 * index),
                    is_synthetic=True, review_status=REVIEW_STATUSES[status_code])
                db.add(record)
                db.flush()
            records.append(record)

            latest = db.scalar(select(Analysis).where(Analysis.record_id == record.id)
                                .order_by(Analysis.id.desc()))
            if latest is None or latest.engine_version != ENGINE_VERSION:
                result = analyze_text(content)
                matched, explanations = encode_analysis(result)
                db.add(Analysis(record_id=record.id, score=result["score"],
                                risk_category=result["risk_category"], engine_version=ENGINE_VERSION,
                                matched_indicators_json=matched, explanation_json=explanations))
        db.flush()

        # ---- cases -------------------------------------------------------------------
        cases: list[Case] = []
        for title, description, status in LEGACY_CASES:
            case = db.scalar(select(Case).where(Case.title == title))
            if case is None:
                case = Case(title=title, description=description, status=status,
                            created_at=SEED_EPOCH, updated_at=SEED_EPOCH)
                db.add(case)
                db.flush()
            cases.append(case)
        legacy_links = [(cases[0], records[4]), (cases[1], records[2]), (cases[2], records[20])]
        for case, record in legacy_links:
            if db.scalar(select(CaseRecord).where(CaseRecord.case_id == case.id,
                                                  CaseRecord.record_id == record.id)) is None:
                db.add(CaseRecord(case_id=case.id, record_id=record.id))
        db.flush()

        new_cases: list[Case] = []
        for offset, (title, description, status, group, start, count) in enumerate(NEW_CASES):
            case = db.scalar(select(Case).where(Case.title == title))
            if case is None:
                case = Case(title=title, description=description, status=status,
                            created_at=SEED_EPOCH + timedelta(hours=6 * offset + 1),
                            updated_at=SEED_EPOCH + timedelta(hours=6 * offset + 1))
                db.add(case)
                db.flush()
            new_cases.append(case)
            low, high = GROUP_RANGES[group]
            for group_index in range(start, min(start + count, high)):
                text_index = low + group_index
                record = records[len(LEGACY_RECORDS) + text_index]
                if db.scalar(select(CaseRecord).where(CaseRecord.case_id == case.id,
                                                      CaseRecord.record_id == record.id)) is None:
                    db.add(CaseRecord(case_id=case.id, record_id=record.id))
        db.flush()

        # ---- analyst notes -----------------------------------------------------------
        for index, case in enumerate(cases + new_cases):
            templates = [NOTE_TEMPLATES[index % len(NOTE_TEMPLATES)]]
            if index % 3 == 0:
                templates.append(NOTE_TEMPLATES[(index + 2) % len(NOTE_TEMPLATES)])
            for note_text, disposition in templates:
                exists = db.scalar(select(AnalystNote).where(AnalystNote.case_id == case.id,
                                                             AnalystNote.note_text == note_text))
                if exists is None:
                    db.add(AnalystNote(case_id=case.id, record_id=None, note_text=note_text,
                                       disposition=disposition,
                                       created_at=SEED_EPOCH + timedelta(hours=6 * index + 2)))

        # ---- relationships -----------------------------------------------------------
        for source_handle, target_handle, relationship_type, feature, evidence in build_relationships():
            source, target = accounts[source_handle], accounts[target_handle]
            exists = db.scalar(select(RelationshipEdge).where(
                RelationshipEdge.source_account_id == source.id,
                RelationshipEdge.target_account_id == target.id,
                RelationshipEdge.relationship_type == relationship_type,
                RelationshipEdge.shared_feature == feature))
            if exists is None:
                db.add(RelationshipEdge(source_account_id=source.id, target_account_id=target.id,
                                        relationship_type=relationship_type, shared_feature=feature,
                                        evidence_description=evidence, is_synthetic=True))

        db.commit()
        return {
            "platforms": db.scalar(select(func.count()).select_from(Platform)),
            "accounts": db.scalar(select(func.count()).select_from(Account)),
            "records": db.scalar(select(func.count()).select_from(ContentRecord)),
            "cases": db.scalar(select(func.count()).select_from(Case)),
            "relationships": db.scalar(select(func.count()).select_from(RelationshipEdge)),
            "notes": db.scalar(select(func.count()).select_from(AnalystNote)),
            "seeded": True,
            "engine_version": ENGINE_VERSION,
        }


if __name__ == "__main__":
    print(seed())
