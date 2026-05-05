"""Reset bola.db and create demo users, orgs, event types, bookings."""
import os
from datetime import datetime, timedelta, timezone

from app.auth.passwords import hash_password
from app.database import Base, SessionLocal, engine, init_db
from app.models import Booking, EventType, Membership, Org, ShareLink, User

DB_PATH = "bola.db"

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

Base.metadata.drop_all(bind=engine)
init_db()

db = SessionLocal()
try:
    pw = hash_password("demo1234")
    alice = User(email="alice@acme.test", password_hash=pw, full_name="Alice Acme")
    bob = User(email="bob@acme.test", password_hash=pw, full_name="Bob Acme")
    eve = User(email="eve@acme.test", password_hash=pw, full_name="Eve Acme")
    carol = User(email="carol@initech.test", password_hash=pw, full_name="Carol Initech")
    dave = User(email="dave@initech.test", password_hash=pw, full_name="Dave Initech")
    db.add_all([alice, bob, eve, carol, dave])
    db.flush()

    acme = Org(name="Acme", slug="acme")
    initech = Org(name="Initech", slug="initech")
    db.add_all([acme, initech])
    db.flush()

    db.add_all([
        Membership(user_id=alice.id, org_id=acme.id, role="owner"),
        Membership(user_id=bob.id, org_id=acme.id, role="member"),
        Membership(user_id=eve.id, org_id=acme.id, role="member"),
        Membership(user_id=carol.id, org_id=initech.id, role="owner"),
        Membership(user_id=dave.id, org_id=initech.id, role="admin"),
    ])

    alice_personal = EventType(
        owner_id=alice.id, org_id=None, slug="30min-intro",
        title="30-min intro", duration_min=30, description="Quick chat",
    )
    carol_personal = EventType(
        owner_id=carol.id, org_id=None, slug="60min-consult",
        title="60-min consult", duration_min=60, description="Deep dive",
    )
    acme_team = EventType(
        owner_id=alice.id, org_id=acme.id, slug="team-demo",
        title="Acme team demo", duration_min=45, description="Team product walk-through",
    )
    initech_team = EventType(
        owner_id=carol.id, org_id=initech.id, slug="support-call",
        title="Initech support call", duration_min=30, description="Customer support",
    )
    db.add_all([alice_personal, carol_personal, acme_team, initech_team])
    db.flush()

    soon = datetime.now(timezone.utc) + timedelta(days=2)

    # Eve hosts a confidential booking on Acme's team event type (used by branch 2 PoC)
    eve_team_booking = Booking(
        event_type_id=acme_team.id,
        host_id=eve.id,
        invitee_email="bigclient@example.com",
        invitee_name="Big Client",
        scheduled_at=soon,
        notes="Confidential pricing discussion",
    )
    # Alice's own booking (general scenery)
    alice_booking = Booking(
        event_type_id=alice_personal.id,
        host_id=alice.id,
        invitee_email="someone@example.com",
        invitee_name="Someone",
        scheduled_at=soon + timedelta(hours=3),
        notes="",
    )
    # Carol's booking (used by branch 1 + share-token branches)
    carol_booking = Booking(
        event_type_id=carol_personal.id,
        host_id=carol.id,
        invitee_email="vip@example.com",
        invitee_name="VIP Customer",
        scheduled_at=soon + timedelta(days=1),
        notes="VIP customer renewal — DO NOT LEAK",
    )
    db.add_all([eve_team_booking, alice_booking, carol_booking])
    db.flush()

    # Issue auto-reschedule share link for carol's booking (used by branch 5 PoC)
    db.add(ShareLink(
        booking_id=carol_booking.id,
        purpose="reschedule",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=carol.id,
    ))

    db.commit()
    print("Seed complete.")
    print("Demo users (password: demo1234):")
    for u in [alice, bob, eve, carol, dave]:
        print(f"  {u.email}")
finally:
    db.close()
