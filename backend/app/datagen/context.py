"""Shared deterministic context and typed reference fixtures for data generation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from app.engine.calendar import AS_OF_DATE

type Row = dict[str, Any]

COUNTRIES: tuple[str, ...] = ("IN", "US", "GB", "DE", "SG")
COUNTRY_SHARES: dict[str, Decimal] = {
    "IN": Decimal("0.35"),
    "US": Decimal("0.25"),
    "GB": Decimal("0.15"),
    "DE": Decimal("0.15"),
    "SG": Decimal("0.10"),
}
COUNTRY_CURRENCIES: dict[str, str] = {
    "IN": "INR",
    "US": "USD",
    "GB": "GBP",
    "DE": "EUR",
    "SG": "SGD",
}
COUNTRY_COST_FACTORS: dict[str, Decimal] = {
    "IN": Decimal("0.65"),
    "US": Decimal("1.00"),
    "GB": Decimal("0.95"),
    "DE": Decimal("0.90"),
    "SG": Decimal("1.05"),
}
CATEGORIES: tuple[str, ...] = (
    "MEALS",
    "LODGING",
    "AIRFARE",
    "GROUND_TRANSPORT",
    "SOFTWARE",
    "OFFICE_SUPPLIES",
    "TRAINING",
    "CLIENT_ENTERTAINMENT",
    "GIFTS",
    "COMMUNICATION",
)
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "MEALS": "Meals and refreshments",
    "LODGING": "Accommodation and lodging",
    "AIRFARE": "Air travel",
    "GROUND_TRANSPORT": "Local ground transportation",
    "SOFTWARE": "Software and digital services",
    "OFFICE_SUPPLIES": "Office supplies and equipment",
    "TRAINING": "Training and professional development",
    "CLIENT_ENTERTAINMENT": "Client entertainment",
    "GIFTS": "Business gifts",
    "COMMUNICATION": "Communication services",
}
CATEGORY_LIMITS: dict[str, tuple[Decimal, Decimal]] = {
    "MEALS": (Decimal("150.00"), Decimal("25.00")),
    "LODGING": (Decimal("500.00"), Decimal("50.00")),
    "AIRFARE": (Decimal("2000.00"), Decimal("0.00")),
    "GROUND_TRANSPORT": (Decimal("250.00"), Decimal("25.00")),
    "SOFTWARE": (Decimal("3000.00"), Decimal("0.00")),
    "OFFICE_SUPPLIES": (Decimal("500.00"), Decimal("25.00")),
    "TRAINING": (Decimal("2000.00"), Decimal("0.00")),
    "CLIENT_ENTERTAINMENT": (Decimal("1000.00"), Decimal("25.00")),
    "GIFTS": (Decimal("500.00"), Decimal("25.00")),
    "COMMUNICATION": (Decimal("300.00"), Decimal("25.00")),
}
DEPARTMENTS: tuple[str, ...] = (
    "Engineering",
    "Sales",
    "Marketing",
    "Finance",
    "HR",
    "Operations",
    "Legal",
    "Support",
)
COST_CENTER_DEPARTMENTS: tuple[str, ...] = (
    "Engineering",
    "Engineering",
    "Engineering",
    "Engineering",
    "Sales",
    "Sales",
    "Sales",
    "Marketing",
    "Marketing",
    "Finance",
    "Finance",
    "HR",
    "HR",
    "Operations",
    "Operations",
    "Operations",
    "Legal",
    "Legal",
    "Support",
    "Support",
)

FIRST_NAMES: dict[str, tuple[str, ...]] = {
    "IN": (
        "Aarav",
        "Aditi",
        "Arjun",
        "Diya",
        "Ishaan",
        "Kavya",
        "Mira",
        "Neel",
        "Riya",
        "Vivaan",
        "Anaya",
        "Dev",
        "Ira",
        "Kabir",
        "Nisha",
        "Reyansh",
        "Sana",
        "Tara",
        "Vihaan",
        "Zoya",
    ),
    "US": (
        "Alex",
        "Avery",
        "Blake",
        "Casey",
        "Drew",
        "Elliot",
        "Jamie",
        "Jordan",
        "Morgan",
        "Quinn",
        "Reese",
        "Riley",
        "Rowan",
        "Sam",
        "Taylor",
        "Cameron",
        "Dakota",
        "Harper",
        "Logan",
        "Skyler",
    ),
    "GB": (
        "Amelia",
        "Arthur",
        "Charlotte",
        "Ethan",
        "Freya",
        "George",
        "Harriet",
        "Isla",
        "Jack",
        "Luca",
        "Maisie",
        "Noah",
        "Olivia",
        "Oscar",
        "Poppy",
        "Theo",
        "Alice",
        "Evelyn",
        "Henry",
        "Milo",
    ),
    "DE": (
        "Ada",
        "Anton",
        "Clara",
        "Emil",
        "Greta",
        "Hannah",
        "Jonas",
        "Klara",
        "Lena",
        "Lukas",
        "Mila",
        "Nico",
        "Oskar",
        "Paula",
        "Theo",
        "Tilda",
        "Anja",
        "Felix",
        "Mara",
        "Rudi",
    ),
    "SG": (
        "Aisha",
        "Chloe",
        "Darren",
        "Ethan",
        "Hui",
        "Jia",
        "Kai",
        "Leah",
        "Mei",
        "Noah",
        "Priya",
        "Ravi",
        "Siti",
        "Wei",
        "Xavier",
        "Yuna",
        "Amir",
        "Evelyn",
        "Irfan",
        "Zara",
    ),
}
LAST_NAMES: dict[str, tuple[str, ...]] = {
    "IN": (
        "Anand",
        "Basu",
        "Chandra",
        "Das",
        "Iyer",
        "Jain",
        "Kapoor",
        "Mehta",
        "Nair",
        "Rao",
        "Bhat",
        "Desai",
        "Ghosh",
        "Joshi",
        "Khan",
        "Menon",
        "Patel",
        "Reddy",
        "Shah",
        "Verma",
    ),
    "US": (
        "Adams",
        "Baker",
        "Brooks",
        "Carter",
        "Cole",
        "Diaz",
        "Foster",
        "Gray",
        "Hayes",
        "Jordan",
        "Kelly",
        "Morgan",
        "Parker",
        "Reed",
        "Sullivan",
        "Turner",
        "Wells",
        "Young",
        "Rivera",
        "Cruz",
    ),
    "GB": (
        "Abbott",
        "Bennett",
        "Clarke",
        "Davies",
        "Ellis",
        "Fletcher",
        "Grant",
        "Hughes",
        "Irwin",
        "Jones",
        "King",
        "Lewis",
        "Morris",
        "Nash",
        "Owen",
        "Price",
        "Reid",
        "Shaw",
        "Turner",
        "White",
    ),
    "DE": (
        "Becker",
        "Brandt",
        "Fischer",
        "Frank",
        "Graf",
        "Hartmann",
        "Keller",
        "Klein",
        "Koch",
        "Kraus",
        "Lang",
        "Mayer",
        "Neumann",
        "Ott",
        "Schmidt",
        "Schulz",
        "Vogel",
        "Weber",
        "Wolf",
        "Zimmer",
    ),
    "SG": (
        "Chua",
        "Goh",
        "Ho",
        "Lim",
        "Ong",
        "Tan",
        "Teo",
        "Wong",
        "Yeo",
        "Chan",
        "Chen",
        "Koh",
        "Lee",
        "Ng",
        "Sim",
        "Yap",
        "Ang",
        "Chew",
        "Lau",
        "Toh",
    ),
}
MERCHANTS: dict[str, tuple[str, ...]] = {
    "IN": (
        "Monsoon Table",
        "Copper Kite Inn",
        "Blue Banyan Air",
        "City Loop Transit",
        "Nimbus Deskworks",
        "Paper Lantern Supply",
        "Bright Path Learning",
        "Mango Grove Events",
    ),
    "US": (
        "Cedar Street Cafe",
        "Northstar Suites",
        "Cloudline Air",
        "Metro Fern Transit",
        "Juniper Systems",
        "Fieldnote Supply",
        "Open Trail Learning",
        "Harborlight Events",
    ),
    "GB": (
        "Thistle & Teacup",
        "Crownstone Rooms",
        "Silver Finch Air",
        "Civic Way Transit",
        "Moorland Software",
        "Copperleaf Supply",
        "Northbank Learning",
        "Lantern House Events",
    ),
    "DE": (
        "Linden Table",
        "Copper Clock Rooms",
        "Riverglass Air",
        "U-Bahn Loop",
        "Meadowbyte Systems",
        "Foliohaus Supply",
        "Brightwerk Learning",
        "Lindenlicht Events",
    ),
    "SG": (
        "Orchid Current Cafe",
        "Merlion House",
        "Sky Orchard Air",
        "Island Link Transit",
        "Cloud Orchid Systems",
        "Kopi Paper Co",
        "Straits Learning",
        "Rain Tree Events",
    ),
}
MERCHANT_CATEGORY: dict[str, str] = {
    "MEALS": "meal",
    "LODGING": "lodging",
    "AIRFARE": "airfare",
    "GROUND_TRANSPORT": "transport",
    "SOFTWARE": "software",
    "OFFICE_SUPPLIES": "supplies",
    "TRAINING": "training",
    "CLIENT_ENTERTAINMENT": "events",
    "GIFTS": "events",
    "COMMUNICATION": "software",
}
MERCHANT_BY_COUNTRY_CATEGORY: dict[tuple[str, str], str] = {
    (
        country,
        category,
    ): f"{MERCHANTS[country][index % len(MERCHANTS[country])]} {MERCHANT_CATEGORY[category]}"
    for country in COUNTRIES
    for index, category in enumerate(CATEGORIES)
}


@dataclass(frozen=True, slots=True)
class ScalePreset:
    name: str
    employees: int
    leave_requests: int
    expense_claims: int


PRESETS: dict[str, ScalePreset] = {
    "starter": ScalePreset("starter", 40, 80, 100),
    "full": ScalePreset("full", 400, 800, 1000),
}


@dataclass(slots=True)
class GenerationContext:
    seed: int
    as_of_date: date
    preset: ScalePreset
    rng: random.Random
    np_rng: np.random.Generator
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    references: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    def set_rows(self, table: str, rows: list[Row], columns: tuple[str, ...]) -> None:
        self.frames[table] = pd.DataFrame(
            {
                column: pd.Series([row.get(column) for row in rows], dtype="object")
                for column in columns
            }
        )

    def get_rows(self, table: str) -> list[Row]:
        frame = self.frames[table]
        return frame.to_dict(orient="records")


def create_context(seed: int, scale: str) -> GenerationContext:
    """Create both explicitly seeded generators from one Python RNG seed."""

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    try:
        preset = PRESETS[scale]
    except KeyError as exc:
        raise ValueError("scale must be 'starter' or 'full'") from exc
    rng = random.Random(seed)
    numpy_seed = rng.getrandbits(64)
    return GenerationContext(
        seed=seed,
        as_of_date=AS_OF_DATE,
        preset=preset,
        rng=rng,
        np_rng=np.random.default_rng(numpy_seed),
    )
