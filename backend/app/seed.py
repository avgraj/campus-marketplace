"""Seed data — categories are data, not hardcoded strings (plan §6)."""

from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from .models import Category

CATEGORIES = [
    ("Books & Study Material", "books-study-material"),
    ("Electronics & Gadgets", "electronics-gadgets"),
    ("Cycles & Vehicles", "cycles-vehicles"),
    ("Hostel & Room Essentials", "hostel-room-essentials"),
    ("Stationery", "stationery"),
    ("Sports & Fitness Gear", "sports-fitness-gear"),
    ("Musical Instruments", "musical-instruments"),
    ("Clothing", "clothing"),
    ("Furniture", "furniture"),
    ("Others", "others"),
]


def seed_categories(db: OrmSession) -> None:
    existing = set(db.scalars(select(Category.slug)))
    for name, slug in CATEGORIES:
        if slug not in existing:
            db.add(Category(name=name, slug=slug))
    db.commit()
