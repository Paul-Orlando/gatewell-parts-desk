#!/usr/bin/env python3
"""
Synthetic U.S. auto parts inventory dataset generator.

Everything here is randomly generated from a fixed seed, so it is royalty-free and
reproducible. Vehicle make/model/year/engine combinations approximate common U.S.
vehicles; part numbers, prices, brands, suppliers, carriers, customers and employees
are fictional. Do not use the part numbers for real-world ordering.

Run:  python3 generate_dataset.py
Out:  car_parts_inventory.db (SQLite) and csv/*.csv
"""
import csv, math, os, random, re, sqlite3, zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SEED = 20261011
rng = random.Random(SEED)
UTC = timezone.utc
NOW = datetime(2026, 10, 11, 21, 0, tzinfo=UTC)       # dataset "as of" time
START = datetime(2024, 10, 1, tzinfo=UTC)             # two years of history
DB_PATH = "car_parts_inventory.db"
CSV_DIR = "csv"
N_ORDERS = 32000

def iso(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None

def local_iso(dt, tz):
    return dt.astimezone(ZoneInfo(tz)).isoformat(timespec="minutes") if dt else None

def slug(s):
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

# ----------------------------------------------------------------------------- engines
ENGINES = {
    "FORD-2.7TT": ("2.7L V6 EcoBoost", "Gasoline", 6), "FORD-3.5TT": ("3.5L V6 EcoBoost", "Gasoline", 6),
    "FORD-3.5": ("3.5L V6", "Gasoline", 6), "FORD-5.0": ("5.0L V8", "Gasoline", 8),
    "FORD-1.5T3": ("1.5L I3 EcoBoost", "Gasoline", 3), "FORD-2.0T": ("2.0L I4 EcoBoost", "Gasoline", 4),
    "FORD-2.3T": ("2.3L I4 EcoBoost", "Gasoline", 4), "FORD-3.0TT": ("3.0L V6 EcoBoost", "Gasoline", 6),
    "FORD-2.5": ("2.5L I4", "Gasoline", 4), "FORD-2.0": ("2.0L I4", "Gasoline", 4),
    "GM-5.3": ("5.3L V8", "Gasoline", 8), "GM-4.3": ("4.3L V6", "Gasoline", 6),
    "GM-2.7T": ("2.7L I4 Turbo", "Gasoline", 4), "GM-1.5T": ("1.5L I4 Turbo", "Gasoline", 4),
    "GM-2.4": ("2.4L I4", "Gasoline", 4), "GM-3.6": ("3.6L V6", "Gasoline", 6),
    "GM-1.4T": ("1.4L I4 Turbo", "Gasoline", 4), "GM-2.5": ("2.5L I4", "Gasoline", 4),
    "GM-2.5T": ("2.5L I4 Turbo", "Gasoline", 4),
    "STLA-3.6": ("3.6L V6 Pentastar", "Gasoline", 6), "STLA-5.7": ("5.7L V8 HEMI", "Gasoline", 8),
    "STLA-6.4": ("6.4L V8 HEMI", "Gasoline", 8), "CUM-6.7D": ("6.7L I6 Turbo Diesel", "Diesel", 6),
    "STLA-2.0T": ("2.0L I4 Turbo", "Gasoline", 4), "STLA-2.4": ("2.4L I4", "Gasoline", 4),
    "TOY-2.5": ("2.5L I4", "Gasoline", 4), "TOY-3.5": ("3.5L V6", "Gasoline", 6),
    "TOY-1.8": ("1.8L I4", "Gasoline", 4), "TOY-2.0": ("2.0L I4", "Gasoline", 4),
    "TOY-2.5H": ("2.5L I4 Hybrid", "Hybrid", 4), "TOY-1.8H": ("1.8L I4 Hybrid", "Hybrid", 4),
    "TOY-2.0H": ("2.0L I4 Hybrid", "Hybrid", 4), "TOY-2.7": ("2.7L I4", "Gasoline", 4),
    "TOY-2.4T": ("2.4L I4 Turbo", "Gasoline", 4), "TOY-5.7": ("5.7L V8", "Gasoline", 8),
    "TOY-3.4TT": ("3.4L V6 Twin-Turbo", "Gasoline", 6), "TOY-4.0": ("4.0L V6", "Gasoline", 6),
    "HON-2.0": ("2.0L I4", "Gasoline", 4), "HON-1.5T": ("1.5L I4 Turbo", "Gasoline", 4),
    "HON-2.0T": ("2.0L I4 Turbo", "Gasoline", 4), "HON-2.4": ("2.4L I4", "Gasoline", 4),
    "HON-3.5": ("3.5L V6", "Gasoline", 6), "HON-1.8": ("1.8L I4", "Gasoline", 4),
    "NIS-2.5": ("2.5L I4", "Gasoline", 4), "NIS-1.5T3": ("1.5L I3 Turbo", "Gasoline", 3),
    "NIS-1.8": ("1.8L I4", "Gasoline", 4), "NIS-2.0": ("2.0L I4", "Gasoline", 4),
    "NIS-3.8": ("3.8L V6", "Gasoline", 6), "NIS-4.0": ("4.0L V6", "Gasoline", 6),
    "NIS-3.5": ("3.5L V6", "Gasoline", 6),
    "HK-2.0": ("2.0L I4", "Gasoline", 4), "HK-2.5": ("2.5L I4", "Gasoline", 4),
    "HK-1.6T": ("1.6L I4 Turbo", "Gasoline", 4), "HK-2.4": ("2.4L I4", "Gasoline", 4),
    "HK-3.8": ("3.8L V6", "Gasoline", 6), "HK-3.3": ("3.3L V6", "Gasoline", 6),
    "SUB-2.5": ("2.5L H4 Boxer", "Gasoline", 4), "SUB-2.0": ("2.0L H4 Boxer", "Gasoline", 4),
    "TES-EV": ("Electric drive unit", "Electric", 0),
}

FAMILY = {"Ford": "FORD", "Chevrolet": "GM", "GMC": "GM", "Ram": "STLA", "Jeep": "STLA", "Dodge": "STLA",
          "Chrysler": "STLA", "Toyota": "TOY", "Honda": "HON", "Nissan": "NIS", "Hyundai": "HK", "Kia": "HK",
          "Subaru": "SUB", "Tesla": "TES"}
ENGINE_FAMILY = lambda code: "STLA" if code.startswith("CUM") else code.split("-")[0]
OEM_BRAND = {"FORD": "Ford OEM", "GM": "GM OEM", "STLA": "Mopar OEM", "TOY": "Toyota OEM", "HON": "Honda OEM",
             "NIS": "Nissan OEM", "HK": "Hyundai/Kia OEM", "SUB": "Subaru OEM", "TES": "Tesla OEM"}

# make, model, body, first year, last year, [(engine, from, to)], popularity
VEHICLE_DEFS = [
    ("Ford", "F-150", "Pickup", 2011, 2026, [("FORD-5.0", 2011, 2026), ("FORD-3.5TT", 2011, 2026), ("FORD-2.7TT", 2015, 2026)], 10),
    ("Ford", "Escape", "Compact SUV", 2013, 2026, [("FORD-2.0T", 2013, 2026), ("FORD-1.5T3", 2020, 2026), ("FORD-2.5", 2013, 2019)], 6),
    ("Ford", "Explorer", "Midsize SUV", 2011, 2026, [("FORD-2.3T", 2016, 2026), ("FORD-3.0TT", 2020, 2026), ("FORD-3.5", 2011, 2019)], 6),
    ("Ford", "Mustang", "Car", 2015, 2026, [("FORD-2.3T", 2015, 2026), ("FORD-5.0", 2015, 2026)], 3),
    ("Ford", "Ranger", "Pickup", 2019, 2026, [("FORD-2.3T", 2019, 2026)], 3),
    ("Ford", "Edge", "Midsize SUV", 2011, 2024, [("FORD-2.0T", 2015, 2024), ("FORD-3.5", 2011, 2018)], 3),
    ("Ford", "Fusion", "Car", 2010, 2020, [("FORD-2.5", 2010, 2020), ("FORD-2.0T", 2013, 2020)], 4),
    ("Ford", "Focus", "Car", 2012, 2018, [("FORD-2.0", 2012, 2018)], 3),
    ("Ford", "Expedition", "Full-size SUV", 2018, 2026, [("FORD-3.5TT", 2018, 2026)], 2.5),
    ("Chevrolet", "Silverado 1500", "Pickup", 2014, 2026, [("GM-5.3", 2014, 2026), ("GM-4.3", 2014, 2021), ("GM-2.7T", 2019, 2026)], 9),
    ("Chevrolet", "Equinox", "Compact SUV", 2010, 2026, [("GM-2.4", 2010, 2017), ("GM-1.5T", 2018, 2026)], 6),
    ("Chevrolet", "Malibu", "Car", 2013, 2025, [("GM-2.5", 2013, 2015), ("GM-1.5T", 2016, 2025)], 4),
    ("Chevrolet", "Tahoe", "Full-size SUV", 2015, 2026, [("GM-5.3", 2015, 2026)], 3.5),
    ("Chevrolet", "Traverse", "Midsize SUV", 2018, 2026, [("GM-3.6", 2018, 2023), ("GM-2.5T", 2024, 2026)], 3),
    ("Chevrolet", "Colorado", "Pickup", 2015, 2026, [("GM-3.6", 2015, 2022), ("GM-2.5", 2015, 2022), ("GM-2.7T", 2023, 2026)], 2.5),
    ("Chevrolet", "Cruze", "Car", 2011, 2019, [("GM-1.4T", 2011, 2019)], 3),
    ("GMC", "Sierra 1500", "Pickup", 2014, 2026, [("GM-5.3", 2014, 2026), ("GM-2.7T", 2019, 2026)], 5),
    ("GMC", "Terrain", "Compact SUV", 2018, 2026, [("GM-1.5T", 2018, 2026)], 2.5),
    ("GMC", "Acadia", "Midsize SUV", 2017, 2026, [("GM-3.6", 2017, 2023), ("GM-2.5", 2017, 2022), ("GM-2.5T", 2024, 2026)], 2.5),
    ("GMC", "Yukon", "Full-size SUV", 2015, 2026, [("GM-5.3", 2015, 2026)], 2),
    ("Ram", "1500", "Pickup", 2013, 2026, [("STLA-5.7", 2013, 2025), ("STLA-3.6", 2013, 2026)], 8),
    ("Ram", "2500", "Heavy-duty Pickup", 2013, 2026, [("STLA-6.4", 2014, 2026), ("CUM-6.7D", 2013, 2026)], 3),
    ("Jeep", "Grand Cherokee", "Midsize SUV", 2011, 2026, [("STLA-3.6", 2011, 2026), ("STLA-5.7", 2011, 2024)], 6),
    ("Jeep", "Wrangler", "SUV", 2012, 2026, [("STLA-3.6", 2012, 2026), ("STLA-2.0T", 2018, 2026)], 5),
    ("Jeep", "Cherokee", "Compact SUV", 2014, 2023, [("STLA-2.4", 2014, 2023), ("STLA-3.6", 2014, 2023)], 3.5),
    ("Jeep", "Compass", "Compact SUV", 2017, 2026, [("STLA-2.4", 2017, 2022), ("STLA-2.0T", 2023, 2026)], 3),
    ("Dodge", "Charger", "Car", 2011, 2023, [("STLA-3.6", 2011, 2023), ("STLA-5.7", 2011, 2023)], 3),
    ("Dodge", "Grand Caravan", "Minivan", 2011, 2020, [("STLA-3.6", 2011, 2020)], 3),
    ("Chrysler", "Pacifica", "Minivan", 2017, 2026, [("STLA-3.6", 2017, 2026)], 2),
    ("Toyota", "Camry", "Car", 2012, 2026, [("TOY-2.5", 2012, 2024), ("TOY-3.5", 2012, 2024), ("TOY-2.5H", 2025, 2026)], 8),
    ("Toyota", "Corolla", "Car", 2014, 2026, [("TOY-1.8", 2014, 2026), ("TOY-2.0", 2019, 2026)], 7),
    ("Toyota", "RAV4", "Compact SUV", 2013, 2026, [("TOY-2.5", 2013, 2026), ("TOY-2.5H", 2016, 2026)], 9),
    ("Toyota", "Tacoma", "Pickup", 2016, 2026, [("TOY-3.5", 2016, 2023), ("TOY-2.7", 2016, 2023), ("TOY-2.4T", 2024, 2026)], 5),
    ("Toyota", "Highlander", "Midsize SUV", 2014, 2026, [("TOY-3.5", 2014, 2022), ("TOY-2.4T", 2023, 2026)], 5),
    ("Toyota", "Tundra", "Pickup", 2014, 2026, [("TOY-5.7", 2014, 2021), ("TOY-3.4TT", 2022, 2026)], 3),
    ("Toyota", "4Runner", "SUV", 2010, 2024, [("TOY-4.0", 2010, 2024)], 3),
    ("Toyota", "Prius", "Car", 2010, 2026, [("TOY-1.8H", 2010, 2022), ("TOY-2.0H", 2023, 2026)], 2.5),
    ("Honda", "Civic", "Car", 2012, 2026, [("HON-1.8", 2012, 2015), ("HON-2.0", 2016, 2026), ("HON-1.5T", 2016, 2026)], 8),
    ("Honda", "Accord", "Car", 2013, 2026, [("HON-2.4", 2013, 2017), ("HON-1.5T", 2018, 2026), ("HON-2.0T", 2018, 2022)], 7),
    ("Honda", "CR-V", "Compact SUV", 2012, 2026, [("HON-2.4", 2012, 2016), ("HON-1.5T", 2017, 2026)], 8),
    ("Honda", "Pilot", "Midsize SUV", 2016, 2026, [("HON-3.5", 2016, 2026)], 4),
    ("Honda", "Odyssey", "Minivan", 2011, 2026, [("HON-3.5", 2011, 2026)], 3),
    ("Honda", "HR-V", "Compact SUV", 2016, 2026, [("HON-1.8", 2016, 2022), ("HON-2.0", 2023, 2026)], 3),
    ("Nissan", "Altima", "Car", 2013, 2026, [("NIS-2.5", 2013, 2026)], 6),
    ("Nissan", "Rogue", "Compact SUV", 2014, 2026, [("NIS-2.5", 2014, 2021), ("NIS-1.5T3", 2022, 2026)], 7),
    ("Nissan", "Sentra", "Car", 2013, 2026, [("NIS-1.8", 2013, 2019), ("NIS-2.0", 2020, 2026)], 5),
    ("Nissan", "Frontier", "Pickup", 2010, 2026, [("NIS-4.0", 2010, 2021), ("NIS-3.8", 2022, 2026)], 2.5),
    ("Nissan", "Pathfinder", "Midsize SUV", 2013, 2026, [("NIS-3.5", 2013, 2026)], 2.5),
    ("Hyundai", "Elantra", "Car", 2011, 2026, [("HK-2.0", 2011, 2026)], 5),
    ("Hyundai", "Tucson", "Compact SUV", 2016, 2026, [("HK-2.0", 2016, 2021), ("HK-2.5", 2022, 2026), ("HK-1.6T", 2016, 2026)], 5),
    ("Hyundai", "Santa Fe", "Midsize SUV", 2013, 2026, [("HK-2.4", 2013, 2018), ("HK-3.3", 2013, 2018), ("HK-2.5", 2019, 2026)], 4),
    ("Hyundai", "Sonata", "Car", 2011, 2023, [("HK-2.4", 2011, 2019), ("HK-2.5", 2020, 2023), ("HK-1.6T", 2015, 2023)], 4),
    ("Kia", "Sorento", "Midsize SUV", 2011, 2026, [("HK-2.4", 2011, 2020), ("HK-3.3", 2014, 2020), ("HK-2.5", 2021, 2026)], 4),
    ("Kia", "Sportage", "Compact SUV", 2011, 2026, [("HK-2.4", 2011, 2022), ("HK-2.5", 2023, 2026)], 4),
    ("Kia", "Forte", "Car", 2014, 2026, [("HK-2.0", 2014, 2026)], 4),
    ("Kia", "Telluride", "Midsize SUV", 2020, 2026, [("HK-3.8", 2020, 2026)], 3),
    ("Subaru", "Outback", "Wagon", 2010, 2026, [("SUB-2.5", 2010, 2026)], 5),
    ("Subaru", "Forester", "Compact SUV", 2014, 2026, [("SUB-2.5", 2014, 2026)], 4.5),
    ("Subaru", "Crosstrek", "Compact SUV", 2013, 2026, [("SUB-2.0", 2013, 2026), ("SUB-2.5", 2021, 2026)], 4),
    ("Tesla", "Model 3", "Car (EV)", 2018, 2026, [("TES-EV", 2018, 2026)], 3),
    ("Tesla", "Model Y", "Compact SUV (EV)", 2020, 2026, [("TES-EV", 2020, 2026)], 4),
]

def body_factor(body):
    if any(k in body for k in ("Pickup", "Full-size", "Heavy")): return 1.25
    if "EV" in body: return 1.2
    if "SUV" in body or body in ("Minivan", "Wagon"): return 1.1
    return 1.0

# ----------------------------------------------------------------------------- part categories
# needs: any = every vehicle, ice = not electric, gas = spark-ignition only (not diesel/EV)
CATS = [
    # name, group, scope, positions, price, weight kg, dims cm, hazmat, core, ship, popularity, needs
    ("Brake Pads", "Brakes", "platform", ["Front", "Rear"], (35, 95), (1.2, 2.8), (18, 12, 8), False, 0, "Standard", 10, "any"),
    ("Brake Rotor", "Brakes", "platform", ["Front", "Rear"], (45, 160), (5, 13), (34, 34, 10), False, 0, "Heavy", 7, "any"),
    ("Brake Caliper", "Brakes", "platform", ["Front Left", "Front Right"], (60, 190), (3, 5.5), (25, 20, 15), False, 30, "Standard", 3, "any"),
    ("Oil Filter", "Filters", "engine", [None], (6, 16), (0.25, 0.5), (10, 10, 12), False, 0, "Small Parcel", 14, "ice"),
    ("Engine Air Filter", "Filters", "engine", [None], (14, 38), (0.3, 0.7), (30, 25, 6), False, 0, "Small Parcel", 9, "ice"),
    ("Cabin Air Filter", "Filters", "platform", [None], (14, 32), (0.15, 0.3), (25, 22, 4), False, 0, "Small Parcel", 8, "any"),
    ("Spark Plug Set", "Ignition", "engine", [None], (24, 95), (0.2, 0.6), (15, 10, 5), False, 0, "Small Parcel", 6, "gas"),
    ("Ignition Coil", "Ignition", "engine", [None], (35, 90), (0.3, 0.6), (15, 8, 8), False, 0, "Small Parcel", 2.5, "gas"),
    ("Serpentine Belt", "Engine", "engine", [None], (22, 65), (0.3, 0.6), (25, 20, 4), False, 0, "Small Parcel", 4, "ice"),
    ("12V Battery", "Electrical", "platform", [None], (140, 260), (13, 19), (28, 18, 19), True, 20, "Hazmat", 6, "any"),
    ("Alternator", "Electrical", "engine", [None], (160, 380), (5, 8), (22, 18, 18), False, 45, "Standard", 2.5, "ice"),
    ("Starter Motor", "Electrical", "engine", [None], (120, 290), (3.5, 6), (25, 15, 15), False, 35, "Standard", 2, "ice"),
    ("Oxygen Sensor", "Sensors", "engine", ["Upstream", "Downstream"], (38, 115), (0.2, 0.4), (20, 8, 6), False, 0, "Small Parcel", 3.5, "ice"),
    ("ABS Wheel Speed Sensor", "Sensors", "platform", ["Front", "Rear"], (24, 75), (0.15, 0.35), (25, 10, 5), False, 0, "Small Parcel", 3, "any"),
    ("Wiper Blade Set", "Wipers", "platform", [None], (18, 42), (0.4, 0.8), (70, 8, 5), False, 0, "Standard", 7, "any"),
    ("Headlight Assembly", "Lighting", "platform", ["Left", "Right"], (130, 480), (3, 6), (70, 45, 35), False, 0, "Oversize", 1.5, "any"),
    ("Strut Assembly", "Suspension & Steering", "platform", ["Front", "Rear"], (85, 260), (4, 9), (60, 20, 20), False, 0, "Heavy", 2.5, "any"),
    ("Control Arm", "Suspension & Steering", "platform", ["Front Lower Left", "Front Lower Right"], (55, 170), (2.5, 5), (50, 20, 10), False, 0, "Standard", 2.5, "any"),
    ("Wheel Hub Bearing", "Suspension & Steering", "platform", ["Front", "Rear"], (75, 210), (3, 5), (22, 22, 15), False, 0, "Standard", 3, "any"),
    ("AC Compressor", "Heating & Cooling", "engine", [None], (240, 620), (6, 10), (35, 25, 25), False, 0, "Heavy", 1.5, "ice"),
    ("Radiator", "Heating & Cooling", "engine", [None], (130, 420), (5, 9), (75, 55, 10), False, 0, "Oversize", 1.5, "ice"),
    ("Water Pump", "Heating & Cooling", "engine", [None], (45, 190), (1.5, 3.5), (20, 18, 15), False, 0, "Standard", 2, "ice"),
    ("Front Bumper Cover", "Body", "platform", [None], (160, 420), (4, 8), (175, 45, 25), False, 0, "Oversize", 0.8, "any"),
    ("Side Mirror", "Body", "platform", ["Left", "Right"], (65, 280), (1.2, 2.5), (35, 25, 20), False, 0, "Standard", 1.2, "any"),
]
CAT = {c[0]: dict(name=c[0], group=c[1], scope=c[2], positions=c[3], price=c[4], weight=c[5], dims=c[6],
                  hazmat=c[7], core=c[8], ship=c[9], pop=c[10], needs=c[11]) for c in CATS}
REMAN_CATS = {"Alternator", "Starter Motor", "Brake Caliper"}
HS = {"Brake Pads": "8708.30", "Brake Rotor": "8708.30", "Brake Caliper": "8708.30", "Oil Filter": "8421.23",
      "Engine Air Filter": "8421.31", "Cabin Air Filter": "8421.39", "Spark Plug Set": "8511.10", "Ignition Coil": "8511.30",
      "Serpentine Belt": "4010.31", "12V Battery": "8507.10", "Alternator": "8511.50", "Starter Motor": "8511.40",
      "Oxygen Sensor": "9027.10", "ABS Wheel Speed Sensor": "9031.80", "Wiper Blade Set": "8512.90",
      "Headlight Assembly": "8512.20", "Strut Assembly": "8708.80", "Control Arm": "8708.80", "Wheel Hub Bearing": "8708.99",
      "AC Compressor": "8414.30", "Radiator": "8708.91", "Water Pump": "8413.30", "Front Bumper Cover": "8708.10",
      "Side Mirror": "7009.10"}

# ----------------------------------------------------------------------------- places
WAREHOUSES = [
    ("ATL", "Atlanta Distribution Center", "Atlanta", "GA", "Southeast", "America/New_York", 1.0),
    ("NWK", "Newark Distribution Center", "Newark", "NJ", "Northeast", "America/New_York", 1.0),
    ("CMH", "Columbus Distribution Center", "Columbus", "OH", "Midwest", "America/New_York", 0.9),
    ("ORD", "Chicago Distribution Center", "Chicago", "IL", "Midwest", "America/Chicago", 1.0),
    ("DFW", "Dallas Distribution Center", "Dallas", "TX", "Southwest", "America/Chicago", 1.0),
    ("PHX", "Phoenix Distribution Center", "Phoenix", "AZ", "Southwest", "America/Phoenix", 0.7),
    ("DEN", "Denver Distribution Center", "Denver", "CO", "West", "America/Denver", 0.7),
    ("LAX", "Inland Empire Distribution Center", "Ontario", "CA", "West", "America/Los_Angeles", 1.1),
    ("SEA", "Seattle Distribution Center", "Kent", "WA", "West", "America/Los_Angeles", 0.7),
    ("ANC", "Anchorage Depot", "Anchorage", "AK", "West", "America/Anchorage", 0.25),
    ("HNL", "Honolulu Depot", "Honolulu", "HI", "West", "Pacific/Honolulu", 0.25),
]
WH = {w[0]: dict(code=w[0], name=w[1], city=w[2], state=w[3], region=w[4], tz=w[5], size=w[6]) for w in WAREHOUSES}
WEST = {"LAX", "SEA", "PHX", "DEN"}
EAST = {"ATL", "NWK", "CMH"}
COLD_WH = {"ORD", "CMH", "NWK", "DEN", "ANC"}

STATES = [
    ("CT", "Connecticut", "Northeast", "America/New_York", "NWK", 3.6), ("ME", "Maine", "Northeast", "America/New_York", "NWK", 1.4),
    ("MA", "Massachusetts", "Northeast", "America/New_York", "NWK", 7.0), ("NH", "New Hampshire", "Northeast", "America/New_York", "NWK", 1.4),
    ("RI", "Rhode Island", "Northeast", "America/New_York", "NWK", 1.1), ("VT", "Vermont", "Northeast", "America/New_York", "NWK", 0.6),
    ("NJ", "New Jersey", "Northeast", "America/New_York", "NWK", 9.3), ("NY", "New York", "Northeast", "America/New_York", "NWK", 19.6),
    ("PA", "Pennsylvania", "Northeast", "America/New_York", "NWK", 13.0), ("DE", "Delaware", "Northeast", "America/New_York", "NWK", 1.0),
    ("MD", "Maryland", "Northeast", "America/New_York", "NWK", 6.2), ("DC", "District of Columbia", "Northeast", "America/New_York", "NWK", 0.7),
    ("VA", "Virginia", "Southeast", "America/New_York", "ATL", 8.7), ("WV", "West Virginia", "Southeast", "America/New_York", "CMH", 1.8),
    ("NC", "North Carolina", "Southeast", "America/New_York", "ATL", 10.8), ("SC", "South Carolina", "Southeast", "America/New_York", "ATL", 5.4),
    ("GA", "Georgia", "Southeast", "America/New_York", "ATL", 11.0), ("FL", "Florida", "Southeast", "America/New_York", "ATL", 22.6),
    ("AL", "Alabama", "Southeast", "America/Chicago", "ATL", 5.1), ("MS", "Mississippi", "Southeast", "America/Chicago", "ATL", 2.9),
    ("TN", "Tennessee", "Southeast", "America/Chicago", "ATL", 7.1), ("KY", "Kentucky", "Southeast", "America/New_York", "CMH", 4.5),
    ("AR", "Arkansas", "Southeast", "America/Chicago", "DFW", 3.1), ("LA", "Louisiana", "Southeast", "America/Chicago", "DFW", 4.6),
    ("OH", "Ohio", "Midwest", "America/New_York", "CMH", 11.8), ("MI", "Michigan", "Midwest", "America/Detroit", "CMH", 10.0),
    ("IN", "Indiana", "Midwest", "America/Indiana/Indianapolis", "CMH", 6.9), ("IL", "Illinois", "Midwest", "America/Chicago", "ORD", 12.5),
    ("WI", "Wisconsin", "Midwest", "America/Chicago", "ORD", 5.9), ("MN", "Minnesota", "Midwest", "America/Chicago", "ORD", 5.7),
    ("IA", "Iowa", "Midwest", "America/Chicago", "ORD", 3.2), ("MO", "Missouri", "Midwest", "America/Chicago", "ORD", 6.2),
    ("ND", "North Dakota", "Midwest", "America/Chicago", "ORD", 0.8), ("SD", "South Dakota", "Midwest", "America/Chicago", "ORD", 0.9),
    ("NE", "Nebraska", "Midwest", "America/Chicago", "DEN", 2.0), ("KS", "Kansas", "Midwest", "America/Chicago", "DFW", 2.9),
    ("TX", "Texas", "Southwest", "America/Chicago", "DFW", 30.5), ("OK", "Oklahoma", "Southwest", "America/Chicago", "DFW", 4.0),
    ("AZ", "Arizona", "Southwest", "America/Phoenix", "PHX", 7.4), ("NM", "New Mexico", "Southwest", "America/Denver", "PHX", 2.1),
    ("CO", "Colorado", "West", "America/Denver", "DEN", 5.9), ("UT", "Utah", "West", "America/Denver", "DEN", 3.4),
    ("WY", "Wyoming", "West", "America/Denver", "DEN", 0.6), ("MT", "Montana", "West", "America/Denver", "DEN", 1.1),
    ("ID", "Idaho", "West", "America/Boise", "DEN", 2.0), ("NV", "Nevada", "West", "America/Los_Angeles", "LAX", 3.2),
    ("CA", "California", "West", "America/Los_Angeles", "LAX", 39.0), ("OR", "Oregon", "West", "America/Los_Angeles", "SEA", 4.2),
    ("WA", "Washington", "West", "America/Los_Angeles", "SEA", 7.8), ("AK", "Alaska", "West", "America/Anchorage", "ANC", 0.7),
    ("HI", "Hawaii", "West", "Pacific/Honolulu", "HNL", 1.4),
]
ST = {s[0]: dict(code=s[0], name=s[1], region=s[2], tz=s[3], wh=s[4], pop=s[5]) for s in STATES}
WAREHOUSES_BY_CODE = {w[0]: w for w in WAREHOUSES}
STATES_BY_CODE = {s_[0]: s_ for s_ in STATES}
COLD = set("ME NH VT MA RI CT NY PA OH MI IN IL WI MN IA ND SD NE CO UT WY MT ID AK".split())
HOT = set("FL GA AL MS LA TX AZ NM NV SC OK AR HI".split())
SALT = set("ME NH VT MA RI CT NY NJ PA OH MI IN IL WI MN IA MO MD DE DC WV".split())
DUSTY = set("AZ NM NV TX UT".split())

SUPPLIERS = [
    ("SUP-NGY", "Chubu Components Co.", "Nagoya", "Aichi", "Japan", "JP", "Asia/Tokyo"),
    ("SUP-BSN", "Hanbit Motor Parts", "Busan", "Busan", "South Korea", "KR", "Asia/Seoul"),
    ("SUP-NGB", "Ningbo Precision Auto Parts", "Ningbo", "Zhejiang", "China", "CN", "Asia/Shanghai"),
    ("SUP-STR", "Rheinwerk Fahrzeugteile GmbH", "Stuttgart", "Baden-Wurttemberg", "Germany", "DE", "Europe/Berlin"),
    ("SUP-MTY", "Monterrey Autopartes S.A.", "Monterrey", "Nuevo Leon", "Mexico", "MX", "America/Monterrey"),
    ("SUP-QRO", "Bajio Componentes Automotrices", "Queretaro", "Queretaro", "Mexico", "MX", "America/Mexico_City"),
    ("SUP-WND", "Great Lakes Parts Co.", "Windsor", "Ontario", "Canada", "CA", "America/Toronto"),
    ("SUP-DET", "Motor City Supply LLC", "Detroit", "Michigan", "United States", "US", "America/Detroit"),
]
SUP = {s[0]: dict(id=s[0], name=s[1], city=s[2], province=s[3], country=s[4], cc=s[5], tz=s[6]) for s in SUPPLIERS}
SUP_CCY = {"SUP-NGY": "JPY", "SUP-BSN": "KRW", "SUP-NGB": "CNY", "SUP-STR": "EUR", "SUP-MTY": "MXN",
           "SUP-QRO": "MXN", "SUP-WND": "CAD", "SUP-DET": "USD"}
OEM_SUPPLIERS = {
    "FORD": [("SUP-DET", 5), ("SUP-MTY", 3), ("SUP-WND", 2)], "GM": [("SUP-DET", 5), ("SUP-QRO", 3), ("SUP-WND", 2)],
    "STLA": [("SUP-DET", 4), ("SUP-WND", 3), ("SUP-MTY", 3)], "TOY": [("SUP-NGY", 6), ("SUP-DET", 4)],
    "HON": [("SUP-NGY", 5), ("SUP-DET", 3), ("SUP-WND", 2)], "NIS": [("SUP-NGY", 5), ("SUP-QRO", 5)],
    "HK": [("SUP-BSN", 8), ("SUP-DET", 2)], "SUB": [("SUP-NGY", 9), ("SUP-DET", 1)], "TES": [("SUP-DET", 8), ("SUP-NGB", 2)],
}
AFTER_BRANDS = [  # name, tier, supplier, pn prefix, weight
    ("Corvane", "Value", "SUP-NGB", "CV", 4), ("Brightway", "Value", "SUP-NGB", "BW", 3),
    ("Ostrander", "Value", "SUP-MTY", "OST", 3), ("Taeyang Parts", "Value", "SUP-BSN", "TY", 2),
    ("Halbrook", "Premium", "SUP-DET", "HB", 3), ("Kessler Teknik", "Premium", "SUP-STR", "KT", 2),
]
CARRIERS = {"Ocean": ["Pacific Crest Lines", "Meridian Ocean Freight", "Orient Gate Shipping"],
            "Ocean-Atlantic": ["Atlantic Meridian Shipping", "Hanse Bridge Lines"],
            "Truck": ["Lone Star Haulers", "Blue Corridor Freight", "Northway Logistics"],
            "Air": ["SkyBridge Air Cargo"], "Truck + Barge": ["Northern Barge Co."]}

def route(sup_cc, wh, rng=rng):
    """Return (mode, carrier, port_of_entry, transit_days)."""
    far = wh in ("ANC", "HNL")
    if rng.random() < 0.04:
        return "Air", CARRIERS["Air"][0], "Anchorage ANC" if wh == "ANC" else ("Honolulu HNL" if wh == "HNL" else "Chicago ORD"), rng.uniform(3, 6)
    if sup_cc in ("JP", "KR", "CN"):
        port = {"LAX": "Long Beach, CA", "PHX": "Long Beach, CA", "DEN": "Long Beach, CA", "SEA": "Seattle-Tacoma, WA",
                "ANC": "Anchorage, AK", "HNL": "Honolulu, HI", "ORD": "Seattle-Tacoma, WA", "ATL": "Savannah, GA",
                "NWK": "Newark, NJ", "CMH": "Newark, NJ", "DFW": "Houston, TX"}[wh]
        days = rng.uniform(16, 24) if wh in ("LAX", "SEA") else rng.uniform(13, 20) if wh == "HNL" else \
            rng.uniform(20, 28) if wh in WEST | {"ANC"} else rng.uniform(28, 38)
        return "Ocean", rng.choice(CARRIERS["Ocean"]), port, days
    if sup_cc == "DE":
        port = {"ATL": "Savannah, GA", "DFW": "Houston, TX"}.get(wh, "Newark, NJ" if wh in ("NWK", "CMH", "ORD") else "Long Beach, CA")
        days = rng.uniform(16, 24) if wh in EAST else rng.uniform(20, 28) if wh in ("ORD", "DFW") else \
            rng.uniform(35, 45) if far else rng.uniform(28, 36)
        return "Ocean", rng.choice(CARRIERS["Ocean-Atlantic"]), port, days
    if far:
        return "Truck + Barge", CARRIERS["Truck + Barge"][0], "Tacoma, WA (barge)", rng.uniform(12, 20)
    if sup_cc == "MX":
        port = "Nogales, AZ" if wh == "PHX" else "Otay Mesa, CA" if wh in ("LAX", "SEA") else "Laredo, TX"
        days = rng.uniform(3, 5) if wh in ("DFW", "PHX") else rng.uniform(4, 6) if wh == "LAX" else rng.uniform(5, 9)
        return "Truck", rng.choice(CARRIERS["Truck"]), port, days
    if sup_cc == "CA":
        days = rng.uniform(2, 4) if wh in ("CMH", "ORD", "NWK") else rng.uniform(4, 7)
        return "Truck", rng.choice(CARRIERS["Truck"]), "Detroit, MI (Ambassador Bridge)", days
    days = rng.uniform(2, 4) if wh in ("CMH", "ORD", "NWK", "ATL") else rng.uniform(3, 7)
    return "Truck", rng.choice(CARRIERS["Truck"]), None, days

def seasonal(cat, st, month):
    m = 1.0
    if cat == "12V Battery":
        if st in COLD: m *= 2.2 if month in (12, 1, 2) else 1.5 if month in (11, 3) else 1.0
        if st in HOT and month in (6, 7, 8): m *= 1.4
    elif cat in ("AC Compressor", "Radiator", "Water Pump"):
        if st in HOT: m *= 2.4 if month in (5, 6, 7, 8, 9) else 0.8
        else: m *= 1.4 if month in (6, 7, 8) else 0.6 if month in (12, 1, 2) else 1.0
    elif cat in ("Strut Assembly", "Control Arm", "Wheel Hub Bearing", "ABS Wheel Speed Sensor"):
        if st in SALT: m *= 1.6 * (1.4 if month in (3, 4, 5) else 1.0)
    elif cat == "Brake Rotor" and st in SALT: m *= 1.3
    elif cat == "Wiper Blade Set" and month in (10, 11, 3, 4): m *= 1.6
    elif cat == "Engine Air Filter" and st in DUSTY: m *= 1.5
    elif cat == "Cabin Air Filter" and month in (3, 4, 5): m *= 1.4
    return m

# ----------------------------------------------------------------------------- company & customer service (fictional)
# 555-0100..0199 numbers are reserved for fictional use; the .example domain is reserved and can never be a real site.
COMPANY = dict(company_name="Gatewell Auto Parts Co.", street="1400 Confluence Way, Suite 200", city="St. Louis",
               state="MO", postal_code="63102", country="United States", hq_timezone="America/Chicago",
               toll_free_phone="(800) 555-0142", international_phone="+1 (314) 555-0142",
               main_email="support@gatewellautoparts.example", website="www.gatewellautoparts.example",
               note="Fictional company for prototyping. Phone numbers use the reserved 555-01xx fictional range.")
# dept_id, name, phone, email, handles, weekday hours (Central), saturday hours (Central) or None, languages
SUPPORT_DEPTS = [
    ("CS", "Customer Service", "(800) 555-0142, option 1", "support@gatewellautoparts.example",
     "Part lookup, fitment questions, order status, backorder ETAs", (7, 19), (8, 14), "English, Spanish"),
    ("DLR", "Dealer Accounts", "(800) 555-0143", "dealers@gatewellautoparts.example",
     "Dealer pricing tiers, bulk and repeat orders, account terms", (7, 18), None, "English, Spanish"),
    ("EXP", "International & Export Desk", "+1 (314) 555-0144", "export@gatewellautoparts.example",
     "International orders, customs, import tax and duties, export documents", (7, 17), None, "English, Spanish, French, Arabic"),
    ("RET", "Returns & Cores", "(800) 555-0145", "returns@gatewellautoparts.example",
     "Returns, damaged-on-arrival claims, core charges and core refunds", (8, 17), (8, 12), "English, Spanish"),
    ("BIL", "Billing & Currency", "(800) 555-0146", "billing@gatewellautoparts.example",
     "Invoices, payments, refunds, currency conversion questions", (8, 17), None, "English, Spanish, French"),
]
DEPT = {d[0]: dict(id=d[0], name=d[1], phone=d[2], email=d[3], handles=d[4], wk=d[5], sat=d[6], langs=d[7]) for d in SUPPORT_DEPTS}
HQ_TZ = ZoneInfo("America/Chicago")
def dept_open(dept, dt):
    loc = dt.astimezone(HQ_TZ)
    hrs = DEPT[dept]["wk"] if loc.weekday() < 5 else DEPT[dept]["sat"] if loc.weekday() == 5 else None
    return bool(hrs) and hrs[0] <= loc.hour < hrs[1]
def next_open(dept, dt):
    t = dt
    while not dept_open(dept, t): t += timedelta(minutes=15)
    return t

# ----------------------------------------------------------------------------- outbound carriers & rate cards
# Carrier names are real; every rate, surcharge and transit time below is a SYNTHETIC ESTIMATE for prototyping.
# For live pricing, call each carrier's rating API with your account.
SERVICES = [
    # code, carrier, service name, scope, speed, first-lb factor, add'l-lb factor, max lb, max length+girth in,
    # dim divisor, hazmat (lead-acid) allowed, fixed transit (lo, hi) or None = by zone, offered to customers
    ("UPS_GND", "UPS", "UPS Ground", "Domestic", "Ground", 1.00, 1.00, 150, 165, 139, 1, None, 1),
    ("UPS_2DA", "UPS", "UPS 2nd Day Air", "Domestic", "2-Day", 2.45, 2.30, 150, 165, 139, 0, (2, 2), 1),
    ("UPS_NDA", "UPS", "UPS Next Day Air", "Domestic", "Overnight", 3.90, 3.40, 150, 165, 139, 0, (1, 1), 1),
    ("FDX_GND", "FedEx", "FedEx Ground / Home Delivery", "Domestic", "Ground", 0.98, 1.02, 150, 165, 139, 1, None, 1),
    ("FDX_2D", "FedEx", "FedEx 2Day", "Domestic", "2-Day", 2.40, 2.32, 150, 165, 139, 0, (2, 2), 1),
    ("FDX_SO", "FedEx", "FedEx Standard Overnight", "Domestic", "Overnight", 3.80, 3.45, 150, 165, 139, 0, (1, 1), 1),
    ("USPS_GA", "USPS", "USPS Ground Advantage", "Domestic", "Ground", 0.75, 1.15, 70, 130, 166, 0, None, 1),
    ("USPS_PM", "USPS", "USPS Priority Mail", "Domestic", "Priority", 1.30, 1.30, 70, 108, 166, 0, (1, 3), 1),
    ("USPS_PME", "USPS", "USPS Priority Mail Express", "Domestic", "Overnight", 3.00, 2.90, 70, 108, 166, 0, (1, 2), 1),
    ("UPS_STD_CAMX", "UPS", "UPS Standard (Canada & Mexico)", "International", "Ground", 0.55, 0.50, 150, 165, 139, 1, (3, 7), 1),
    ("FDX_IG", "FedEx", "FedEx International Ground (Canada)", "International", "Ground", 0.52, 0.48, 150, 165, 139, 1, (3, 6), 1),
    ("UPS_WWX", "UPS", "UPS Worldwide Expedited", "International", "Expedited", 1.00, 1.00, 150, 165, 139, 0, (3, 5), 1),
    ("UPS_WWS", "UPS", "UPS Worldwide Saver", "International", "Express", 1.25, 1.22, 150, 165, 139, 0, (1, 3), 1),
    ("FDX_IE", "FedEx", "FedEx International Economy", "International", "Expedited", 0.95, 0.97, 150, 165, 139, 0, (4, 6), 1),
    ("FDX_IP", "FedEx", "FedEx International Priority", "International", "Express", 1.22, 1.20, 150, 165, 139, 0, (1, 3), 1),
    ("DHL_EXW", "DHL", "DHL Express Worldwide", "International", "Express", 1.18, 1.15, 154, 165, 139, 0, (1, 3), 1),
    ("USPS_PMI", "USPS", "USPS Priority Mail International", "International", "Economy", 0.80, 0.85, 66, 108, 166, 0, (6, 10), 1),
    ("OCEAN_LCL", "Freight forwarder", "Ocean LCL consolidation (dealer freight)", "International", "Ocean", 0, 0, None, None, None, 1, (20, 35), 0),
    ("AIR_FWD", "Freight forwarder", "Air freight consolidation (dealer freight)", "International", "Air freight", 0, 0, None, None, None, 0, (4, 7), 0),
    ("GW_ROUTE", "Gatewell Delivery", "Gatewell local delivery route (dealers)", "Domestic", "Route", 0, 0, None, None, None, 1, (1, 1), 0),
]
SVC = {x[0]: dict(code=x[0], carrier=x[1], name=x[2], scope=x[3], speed=x[4], f1=x[5], fa=x[6], maxlb=x[7], maxlg=x[8],
                  dim=x[9], haz=x[10], transit=x[11], quote=x[12]) for x in SERVICES}
INTL_ZONE = {"CA": "A", "MX": "A", "DO": "B", "CR": "B", "CO": "B", "CL": "B", "GB": "C", "DE": "C", "SA": "D", "AE": "D",
             "AU": "E", "PH": "E"}
INTL_BASE = {"A": (32.0, 3.5, 0), "B": (48.0, 6.0, 1), "C": (55.0, 7.0, 1), "D": (62.0, 8.0, 2), "E": (65.0, 8.5, 2)}
GROUND_DAYS = {2: 1, 3: 2, 4: 3, 5: 3, 6: 4, 7: 5, 8: 5}
def DOM_TRANSIT(x, z):
    if x["code"] == "USPS_PM": return (1, 2) if z <= 4 else (2, 3)
    if x["code"] == "USPS_PME": return (1, 1) if z <= 4 else (1, 2)
    if x["transit"]: return x["transit"]
    return GROUND_DAYS[z], GROUND_DAYS[z] + (1 if z >= 6 else 0)
ADJ = {"Northeast": {"Southeast", "Midwest"}, "Southeast": {"Northeast", "Midwest", "Southwest"},
       "Midwest": {"Northeast", "Southeast", "Southwest", "West"}, "Southwest": {"Southeast", "Midwest", "West"},
       "West": {"Midwest", "Southwest"}}
def dom_zone(whc, st):
    w = WAREHOUSES_BY_CODE[whc]; s_ = STATES_BY_CODE[st]
    if st in ("AK", "HI"): return 2 if (st, whc) in (("AK", "ANC"), ("HI", "HNL")) else 8
    if whc in ("ANC", "HNL"): return 8
    if w[3] == st: return 2
    if s_[4] == whc: return 3 if s_[2] == w[4] else 4
    if s_[2] == w[4]: return 5
    return 6 if s_[2] in ADJ[w[4]] else 8 if {s_[2], w[4]} & {"Northeast", "Southeast"} and "West" in {s_[2], w[4]} else 7
SURCHARGES = [  # code, carrier, name, applies to, amount USD, percent, rule
    ("FUEL_GND", "UPS", "Fuel surcharge (ground)", "Ground", None, 17.5, "Percent of transportation charge"),
    ("FUEL_AIR", "UPS", "Fuel surcharge (air)", "Air", None, 21.0, "Percent of transportation charge"),
    ("FUEL_INTL", "UPS", "Fuel surcharge (international)", "International", None, 24.0, "Percent of transportation charge"),
    ("RESI_GND", "UPS", "Residential delivery (ground)", "Ground", 5.95, None, "Delivery to a home address"),
    ("RESI_AIR", "UPS", "Residential delivery (air/international)", "Air", 6.45, None, "Delivery to a home address"),
    ("ADD_HANDLING", "UPS", "Additional handling", "All", 29.50, None, "Longest side > 48 in, 2nd-longest > 30 in, or actual weight > 50 lb"),
    ("LARGE_PKG", "UPS", "Large package", "All", 125.00, None, "Length + girth > 130 in or longest side > 96 in"),
    ("HAZMAT_GND", "UPS", "Hazardous materials (ground)", "Ground", 32.00, None, "Lead-acid battery by ground"),
    ("FUEL_GND", "FedEx", "Fuel surcharge (ground)", "Ground", None, 17.0, "Percent of transportation charge"),
    ("FUEL_AIR", "FedEx", "Fuel surcharge (air)", "Air", None, 21.5, "Percent of transportation charge"),
    ("FUEL_INTL", "FedEx", "Fuel surcharge (international)", "International", None, 24.5, "Percent of transportation charge"),
    ("RESI_GND", "FedEx", "Residential delivery (ground)", "Ground", 5.85, None, "Delivery to a home address"),
    ("RESI_AIR", "FedEx", "Residential delivery (air/international)", "Air", 6.40, None, "Delivery to a home address"),
    ("ADD_HANDLING", "FedEx", "Additional handling", "All", 29.00, None, "Longest side > 48 in, 2nd-longest > 30 in, or actual weight > 50 lb"),
    ("LARGE_PKG", "FedEx", "Oversize charge", "All", 120.00, None, "Length + girth > 130 in or longest side > 96 in"),
    ("HAZMAT_GND", "FedEx", "Hazardous materials (ground)", "Ground", 31.00, None, "Lead-acid battery by ground"),
    ("FUEL_INTL", "DHL", "Fuel surcharge (international)", "International", None, 25.0, "Percent of transportation charge"),
    ("RESI_AIR", "DHL", "Residential delivery", "Air", 5.50, None, "Delivery to a home address"),
    ("ADD_HANDLING", "DHL", "Non-stackable / heavy piece", "All", 27.00, None, "Longest side > 48 in or actual weight > 50 lb"),
    ("LARGE_PKG", "DHL", "Oversize piece", "All", 95.00, None, "Longest side > 47 in and length + girth > 130 in"),
    ("NONSTD_22", "USPS", "Nonstandard length (over 22 in)", "All", 4.50, None, "Longest side > 22 in and <= 30 in"),
    ("NONSTD_30", "USPS", "Nonstandard length (over 30 in)", "All", 18.00, None, "Longest side > 30 in"),
]
def _svc_row(x):
    return dict(service_code=x["code"], carrier=x["carrier"], service_name=x["name"], scope=x["scope"], speed=x["speed"],
                max_weight_lb=x["maxlb"], max_length_plus_girth_in=x["maxlg"], dim_divisor=x["dim"],
                hazmat_lead_acid_allowed=x["haz"], transit_days_min=x["transit"][0] if x["transit"] else None,
                transit_days_max=x["transit"][1] if x["transit"] else None, transit_by_zone=int(x["transit"] is None),
                offered_to_customers=x["quote"])
SVC_ROWS = {code: _svc_row(x) for code, x in SVC.items()}
RATE_ROWS = {}
for x in SVC.values():
    if not x["quote"]: continue          # internal freight services are priced by formula, not rate cards
    if x["scope"] == "Domestic":
        for z in range(2, 9):
            RATE_ROWS[(x["code"], str(z))] = dict(service_code=x["code"], zone=str(z),
                first_lb_usd=round((9.80 + 0.95 * (z - 2)) * x["f1"], 2), additional_lb_usd=round((0.40 + 0.09 * (z - 2)) * x["fa"], 2),
                transit_days_min=DOM_TRANSIT(x, z)[0], transit_days_max=DOM_TRANSIT(x, z)[1], source="Synthetic estimate")
    elif x["quote"]:
        for zc in (["A"] if x["code"] in ("UPS_STD_CAMX", "FDX_IG") else "ABCDE"):
            RATE_ROWS[(x["code"], zc)] = dict(service_code=x["code"], zone=zc,
                first_lb_usd=round(INTL_BASE[zc][0] * x["f1"], 2), additional_lb_usd=round(INTL_BASE[zc][1] * x["fa"], 2),
                transit_days_min=x["transit"][0] + INTL_BASE[zc][2], transit_days_max=x["transit"][1] + INTL_BASE[zc][2],
                source="Synthetic estimate")
SUR_BY_CARRIER = defaultdict(dict)
for x in SURCHARGES:
    SUR_BY_CARRIER[x[1]][x[0]] = dict(surcharge_code=x[0], surcharge_name=x[2], amount_usd=x[4], percent=x[5])

def est_carrier_cost(svc_code, zone, items, residential, value_usd):
    """Our estimated carrier cost for an order (same engine as the agent's shipping quotes)."""
    import agent_tools as AT
    if svc_code == "OCEAN_LCL": return round(150 + 0.02 * value_usd, 2)
    if svc_code == "AIR_FWD": return round(85 + 2.2 * sum(p["weight_lb"] * q for p, q in items), 2)
    if svc_code == "GW_ROUTE": return round(15 + 0.01 * value_usd, 2)
    pk = AT._packages(items)
    for code in (svc_code, "UPS_GND" if SVC[svc_code]["scope"] == "Domestic" else "UPS_WWX"):
        r_ = RATE_ROWS.get((code, zone))
        if not r_: continue
        cost, _ = AT._service_cost(None, SVC_ROWS[code], r_, pk, residential, SVC[code]["scope"], sur=SUR_BY_CARRIER[SVC[code]["carrier"]])
        if cost is not None: return cost
    return 0.0

SHIP_CUTOFF_HOUR = 15   # orders placed before 3:00 PM warehouse local time ship the same business day
FREE_SHIP_THRESHOLD_USD = 99.0

FAQ = [  # category, question, answer, keywords, department
    ("Finding the right part", "How do I know a part fits my vehicle?",
     "Search by year, make, model and engine, or enter your 17-character VIN. Every part page lists the exact vehicles it fits. If two parts look alike, the position (front/rear, left/right) and engine size are usually the difference. Still unsure? Chat with us or call Customer Service and we'll confirm fitment before you order.",
     "fit fitment vin year make model engine compatible", "CS"),
    ("Finding the right part", "What's the difference between OEM, Premium and Value parts?",
     "OEM parts are made for the vehicle manufacturer and match the original. Premium aftermarket parts meet or exceed OEM specs at a lower price. Value parts are budget-friendly replacements that meet basic fit and function. All three are new unless a part is listed as Remanufactured.",
     "oem aftermarket premium value quality brand difference", "CS"),
    ("Finding the right part", "My part number changed. Is it the same part?",
     "Manufacturers sometimes replace an old part number with a new one (a supersession). If you search an old number, we show the current replacement. The replacement fits the same vehicles.",
     "superseded supersession old part number replaced changed", "CS"),
    ("Finding the right part", "Can I search by an aftermarket or competitor part number?",
     "Yes. Enter any OEM or aftermarket number and we'll show the matching parts we carry (cross-reference).",
     "cross reference interchange competitor number equivalent", "CS"),
    ("Ordering & pricing", "Why is the price different for dealers?",
     "Dealership accounts get wholesale pricing based on their account tier. Individual customers see our retail price. Prices shown in the chat already reflect your account.",
     "price dealer wholesale tier discount retail cost", "DLR"),
    ("Ordering & pricing", "What is a core charge?",
     "Some parts, like alternators, starters, brake calipers and batteries, include a refundable core charge. Send your old part back within 30 days and we refund the core charge to your original payment method.",
     "core charge deposit refund old part alternator starter battery caliper", "RET"),
    ("Ordering & pricing", "A part is backordered. When will it ship?",
     "Backordered parts ship as soon as stock arrives. The chat can show the expected arrival date at the warehouse. If you'd rather not wait, we can suggest an equivalent part that's in stock.",
     "backorder backordered out of stock when eta available", "CS"),
    ("Shipping & delivery", "Which carriers do you ship with?",
     "In the U.S. we ship with UPS, FedEx and USPS. Internationally we ship with UPS, FedEx, DHL Express and USPS. You'll see each available service, its cost and its estimated delivery date before you check out.",
     "carrier ups fedex usps dhl shipping options", "CS"),
    ("Shipping & delivery", "How much is shipping?",
     "Shipping depends on the carrier, speed, package size and weight, and distance from our warehouse. Ground shipping is free for U.S. individual orders of $99 or more and for dealer accounts. Oversize parts like bumper covers, radiators and headlights carry oversize charges and aren't eligible for free shipping for individual orders.",
     "shipping cost price how much free shipping rate", "CS"),
    ("Shipping & delivery", "When will my order ship?",
     "Orders placed before 3:00 PM (local time at the shipping warehouse) on a business day ship the same day. Later orders ship the next business day.",
     "ship today same day cutoff when processing", "CS"),
    ("Shipping & delivery", "Why can't I choose air shipping for a battery?",
     "Lead-acid batteries are classed as hazardous materials. We ship them by UPS or FedEx Ground only, within the U.S. and to Canada and Mexico. We don't ship batteries overseas.",
     "battery batteries hazmat hazardous air shipping restricted overseas international export", "CS"),
    ("Shipping & delivery", "How do I track my order?",
     "You'll get a tracking number by email when your order ships. You can also ask the chat for your order status with your order number.",
     "track tracking where is my order status", "CS"),
    ("International orders", "Do you ship outside the United States?",
     "Yes. We ship to Canada, Mexico, the Dominican Republic, Costa Rica, Colombia, Chile, the United Kingdom, Germany, Saudi Arabia, the United Arab Emirates, Australia and the Philippines.",
     "international ship outside country countries abroad export", "EXP"),
    ("International orders", "Will I pay import tax or duties?",
     "For individual customers we collect the destination's import tax (VAT/GST) at checkout, so there's nothing to pay on delivery (DDP). Dealer accounts pay import charges when goods arrive (DAP). Orders to Canada and Mexico may qualify for USMCA duty-free treatment.",
     "import tax duty duties vat gst customs ddp dap usmca", "EXP"),
    ("International orders", "My international order is stuck in customs. What do I do?",
     "Customs sometimes needs extra documents. Contact our International & Export Desk and we'll send the paperwork to the carrier or your broker right away.",
     "customs held stuck clearance documents", "EXP"),
    ("Currency & payment", "Can I pay in my own currency?",
     "Yes. International customers see prices and pay in their local currency. We convert from U.S. dollars at that day's exchange rate. A 2% conversion margin is included in local-currency prices. Some dealer accounts are invoiced in U.S. dollars instead.",
     "currency exchange rate local pay convert dollars pesos euros", "BIL"),
    ("Currency & payment", "Why is my total different from yesterday?",
     "Local-currency prices follow the daily exchange rate, so totals can change slightly from day to day. Your order is locked at the rate on the day you place it.",
     "exchange rate changed price different currency fluctuation", "BIL"),
    ("Currency & payment", "What payment methods and terms do you offer?",
     "Individuals pay by card at checkout. Dealer accounts can be set up with Net 15 or Net 30 terms after a credit review, or pay in advance.",
     "payment card terms net 30 net 15 invoice credit", "BIL"),
    ("Returns & cores", "What is your return policy?",
     "New, uninstalled parts in original packaging can be returned within 30 days of delivery for a full refund. Electrical parts that have been installed can't be returned unless they're defective.",
     "return refund policy exchange send back", "RET"),
    ("Returns & cores", "My part arrived damaged. What do I do?",
     "Sorry about that. Contact Returns & Cores within 7 days with your order number and a photo. We'll send a replacement or refund, plus a prepaid return label.",
     "damaged broken arrived defective wrong", "RET"),
    ("Returns & cores", "I received the wrong part.",
     "Contact us with your order number. If it was our mistake, we ship the correct part at no charge and send a prepaid label for the wrong one.",
     "wrong part incorrect mistake not fit", "CS"),
    ("Warranty", "Do your parts have a warranty?",
     "Yes. OEM and Value parts carry a 12-month warranty. Premium aftermarket parts carry a limited lifetime warranty to the original purchaser. Keep your order number for warranty claims.",
     "warranty guarantee defective lifetime", "RET"),
    ("Dealer accounts", "How do I open a dealer account?",
     "Contact Dealer Accounts. We'll set up wholesale pricing, delivery routes and payment terms for your dealership.",
     "dealer account open wholesale business apply", "DLR"),
    ("Contact us", "How do I reach a live person?",
     "Ask the chat for a person at any time and it will connect you to the right team, or call (800) 555-0142 (U.S. & Canada) or +1 (314) 555-0142 (international). Email support@gatewellautoparts.example. We're open Monday-Friday 7:00 AM-7:00 PM and Saturday 8:00 AM-2:00 PM Central Time.",
     "live person human agent representative talk call phone email contact help", "CS"),
    ("Contact us", "Where are you located?",
     "Gatewell Auto Parts Co., 1400 Confluence Way, Suite 200, St. Louis, MO 63102. Orders ship from our 11 U.S. warehouses.",
     "address location headquarters where located st louis", "CS"),
]

# ----------------------------------------------------------------------------- currencies & FX
CURRENCIES = [  # code, name, symbol, decimals, starting units per USD, daily volatility, pegged to USD
    ("USD", "US Dollar", "$", 2, 1.0, 0, 1), ("CAD", "Canadian Dollar", "C$", 2, 1.38, 0.0035, 0),
    ("MXN", "Mexican Peso", "MX$", 2, 18.6, 0.0065, 0), ("DOP", "Dominican Peso", "RD$", 2, 61.5, 0.0025, 0),
    ("CRC", "Costa Rican Colon", "CRC", 2, 505.0, 0.003, 0), ("COP", "Colombian Peso", "COL$", 2, 4000.0, 0.007, 0),
    ("CLP", "Chilean Peso", "CLP$", 0, 950.0, 0.006, 0), ("GBP", "Pound Sterling", "GBP", 2, 0.75, 0.004, 0),
    ("EUR", "Euro", "EUR", 2, 0.87, 0.004, 0), ("SAR", "Saudi Riyal", "SAR", 2, 3.75, 0, 1),
    ("AED", "UAE Dirham", "AED", 2, 3.6725, 0, 1), ("AUD", "Australian Dollar", "A$", 2, 1.53, 0.005, 0),
    ("PHP", "Philippine Peso", "PHP", 2, 57.5, 0.003, 0), ("JPY", "Japanese Yen", "JPY", 0, 148.0, 0.005, 0),
    ("KRW", "South Korean Won", "KRW", 0, 1390.0, 0.0045, 0), ("CNY", "Chinese Yuan", "CNY", 2, 7.15, 0.002, 0),
]
CCY = {c[0]: dict(code=c[0], name=c[1], symbol=c[2], dec=c[3], base=c[4], vol=c[5], peg=c[6]) for c in CURRENCIES}
FX, fx_rows = {}, []
for code, c in CCY.items():
    x, d = c["base"], (START - timedelta(days=60)).date()
    while d <= NOW.date():
        if not c["peg"]:
            lx = math.log(x) + rng.gauss(0, c["vol"]) + 0.01 * (math.log(c["base"]) - math.log(x))
            if code == "MXN" and (NOW.date() - d).days < 30: lx += 0.002   # planted: peso weakening this month
            x = math.exp(lx)
        x = round(x, 6)
        FX[(code, d.isoformat())] = x
        fx_rows.append(dict(rate_date=d.isoformat(), currency_code=code, units_per_usd=x, usd_per_unit=round(1 / x, 8),
                            source="Synthetic daily mid-rate"))
        d += timedelta(days=1)
def fx(code, dt):
    return FX[(code, dt.astimezone(UTC).date().isoformat())]
def money(v, code):
    return round(v, CCY[code]["dec"])

# International markets: cc, name, currency, market region, [(city, tz, serving warehouse)], share of intl demand,
# proxy U.S. state for climate, season shift in months (southern hemisphere), VAT/GST %, tax name,
# delivery days (lo, hi), overseas, truck/SUV preference, share of dealers invoiced in local currency
INTL = [
    ("CA", "Canada", "CAD", "North America", [("Toronto", "America/Toronto", "CMH"), ("Montreal", "America/Toronto", "NWK"),
        ("Vancouver", "America/Vancouver", "SEA"), ("Calgary", "America/Edmonton", "SEA"), ("Winnipeg", "America/Winnipeg", "ORD"),
        ("Halifax", "America/Halifax", "NWK")], 40, "MN", 0, 5, "GST (federal; provincial tax extra)", (2, 6), False, 1.0, 0.8),
    ("MX", "Mexico", "MXN", "North America", [("Monterrey", "America/Monterrey", "DFW"), ("Mexico City", "America/Mexico_City", "DFW"),
        ("Guadalajara", "America/Mexico_City", "DFW"), ("Tijuana", "America/Tijuana", "LAX")], 25, "TX", 0, 16, "IVA", (3, 8), False, 1.2, 0.6),
    ("DO", "Dominican Republic", "DOP", "Latin America & Caribbean", [("Santo Domingo", "America/Santo_Domingo", "ATL")], 4, "FL", 0, 18, "ITBIS", (5, 12), True, 1.2, 0.3),
    ("CR", "Costa Rica", "CRC", "Latin America & Caribbean", [("San Jose", "America/Costa_Rica", "ATL")], 3, "FL", 0, 13, "IVA", (5, 12), True, 1.0, 0.3),
    ("CO", "Colombia", "COP", "Latin America & Caribbean", [("Bogota", "America/Bogota", "ATL"), ("Medellin", "America/Bogota", "ATL")], 4, "GA", 0, 19, "IVA", (6, 14), True, 1.0, 0.4),
    ("CL", "Chile", "CLP", "Latin America & Caribbean", [("Santiago", "America/Santiago", "ATL")], 3, "CA", 6, 19, "IVA", (7, 15), True, 1.0, 0.4),
    ("GB", "United Kingdom", "GBP", "Europe", [("London", "Europe/London", "NWK"), ("Manchester", "Europe/London", "NWK")], 5, "NY", 0, 20, "VAT", (5, 10), True, 0.8, 0.8),
    ("DE", "Germany", "EUR", "Europe", [("Frankfurt", "Europe/Berlin", "NWK"), ("Hamburg", "Europe/Berlin", "NWK")], 4, "NY", 0, 19, "VAT (MwSt)", (5, 10), True, 0.8, 0.8),
    ("SA", "Saudi Arabia", "SAR", "Middle East", [("Riyadh", "Asia/Riyadh", "NWK"), ("Jeddah", "Asia/Riyadh", "NWK")], 6, "AZ", 0, 15, "VAT", (6, 12), True, 2.0, 0.5),
    ("AE", "United Arab Emirates", "AED", "Middle East", [("Dubai", "Asia/Dubai", "NWK")], 5, "AZ", 0, 5, "VAT", (5, 10), True, 2.0, 0.5),
    ("AU", "Australia", "AUD", "Asia-Pacific", [("Sydney", "Australia/Sydney", "LAX"), ("Brisbane", "Australia/Brisbane", "LAX"),
        ("Perth", "Australia/Perth", "LAX")], 5, "CA", 6, 10, "GST", (6, 12), True, 1.5, 0.8),
    ("PH", "Philippines", "PHP", "Asia-Pacific", [("Manila", "Asia/Manila", "LAX")], 3, "FL", 0, 12, "VAT", (6, 14), True, 1.0, 0.4),
]
CTRY = {c[0]: dict(cc=c[0], name=c[1], ccy=c[2], market=c[3], cities=c[4], share=c[5], season=c[6], shift=c[7], vat=c[8],
                   tax=c[9], transit=c[10], overseas=c[11], truck=c[12], local_bill=c[13]) for c in INTL}
USMCA = {"US", "CA", "MX"}
TRUCKY = ("Pickup", "Full-size", "Heavy")

# ----------------------------------------------------------------------------- build vehicles & platforms
vehicles, platforms = [], {}
vid = 0
for make, model, body, y0, y1, engs, pop in VEHICLE_DEFS:
    for year in range(y0, y1 + 1):
        g = (year - y0) // 6
        gy0, gy1 = y0 + g * 6, min(y1, y0 + g * 6 + 5)
        pid = f"PLT-{slug(make)[:4]}-{slug(model)}-G{g + 1}"
        platforms.setdefault(pid, dict(platform_id=pid, make=make, model=model, generation=g + 1, year_from=gy0,
                                       year_to=gy1, body_style=body, family=FAMILY[make]))
        valid = [e for e, a, b in engs if a <= year <= b]
        assert valid, (make, model, year)
        age = 2026 - year
        af = min(1.0, (age + 1) / 6) * (1.0 if age <= 12 else max(0.3, 1 - (age - 12) * 0.15))
        for e in valid:
            vid += 1
            vehicles.append(dict(vehicle_id=f"V{vid:05d}", year=year, make=make, model=model, body_style=body,
                                 engine_code=e, engine=ENGINES[e][0], fuel_type=ENGINES[e][1], cylinders=ENGINES[e][2],
                                 platform_id=pid, popularity_weight=round(pop * af / len(valid), 4)))
V = {v["vehicle_id"]: v for v in vehicles}
veh_by_platform, veh_by_engine = defaultdict(list), defaultdict(list)
for v in vehicles:
    veh_by_platform[v["platform_id"]].append(v["vehicle_id"])
    veh_by_engine[v["engine_code"]].append(v["vehicle_id"])
engine_body = {}
for v in vehicles:
    engine_body.setdefault(v["engine_code"], v["body_style"])

def applies(cat, fuel):
    n = CAT[cat]["needs"]
    return n == "any" or (n == "ice" and fuel != "Electric") or (n == "gas" and fuel in ("Gasoline", "Hybrid"))

# ----------------------------------------------------------------------------- build parts
LET, DIG = "ABCDEFGHJKLMNPRSTUVWXYZ", "0123456789"
r = lambda chars, n: "".join(rng.choice(chars) for _ in range(n))
used_pn = set()
def pn_oem(fam):
    f = {"FORD": lambda: f"{r(LET, 2)}{r(DIG, 1)}Z-{r(DIG, 4)}-{r(LET, 1)}", "GM": lambda: rng.choice("28") + r(DIG, 7),
         "STLA": lambda: "68" + r(DIG, 6) + r(LET, 2), "TOY": lambda: f"{r(DIG, 5)}-{r(DIG, 1)}{r(LET, 1)}{r(DIG, 3)}",
         "HON": lambda: f"{r(DIG, 5)}-{r(LET, 3)}-{r(LET, 1)}{r(DIG, 2)}",
         "NIS": lambda: f"{r(LET + DIG, 5)}-{r(DIG, 1)}{r(LET, 2)}{r(DIG, 1)}{r(LET, 1)}",
         "HK": lambda: f"{r(DIG, 5)}-{r(LET, 1)}{r(DIG, 1)}{r(LET, 1)}{r(DIG, 2)}", "SUB": lambda: f"{r(DIG, 5)}{r(LET, 2)}{r(DIG, 3)}",
         "TES": lambda: f"{r(DIG, 7)}-00-{r(LET, 1)}"}[fam]
    while True:
        x = f()
        if x not in used_pn:
            used_pn.add(x); return x
def pn_after(prefix):
    while True:
        x = f"{prefix}-{r(DIG, 5)}" + (r(LET, 1) if rng.random() < 0.3 else "")
        if x not in used_pn:
            used_pn.add(x); return x

parts, interchange, fitment = [], [], []
pid_n = 0
def new_part(**kw):
    global pid_n
    pid_n += 1
    kw["part_id"] = f"P{pid_n:06d}"
    parts.append(kw)
    return kw

def size_class(w, dims, ship):
    if ship == "Oversize": return "Oversize"
    m = max(dims)
    if w < 1.5 and m <= 35: return "Small"
    if w < 8 and m <= 60: return "Medium"
    return "Large"

for cname, c in CAT.items():
    if c["scope"] == "platform":
        keys = [(p["platform_id"], p["family"], body_factor(p["body_style"]),
                 f'{p["make"]} {p["model"]} {p["year_from"]}-{p["year_to"]}')
                for p in platforms.values() if c["needs"] == "any" or p["family"] != "TES"]
    else:
        keys = [(e, ENGINE_FAMILY(e), body_factor(engine_body[e]), f"{ENGINES[e][0]} engine ({e})")
                for e in veh_by_engine if applies(cname, ENGINES[e][1])]
    for key, fam, bf, fits_summary in keys:
        for pos in c["positions"]:
            base = rng.uniform(*c["price"]) * bf
            w = rng.uniform(*c["weight"]) * (bf ** 0.8)
            dims = [round(d * rng.uniform(0.85, 1.15) * bf ** 0.3, 1) for d in c["dims"]]
            ship = "Heavy" if (w >= 10 and c["ship"] not in ("Hazmat", "Oversize")) else c["ship"]
            pname = f"{cname} - {pos}" if pos else cname
            common = dict(category=cname, category_group=c["group"], position=pos, fits_scope=c["scope"], fits_key=key,
                          fits_summary=fits_summary, weight_kg=round(w, 2), weight_lb=round(w * 2.20462, 2),
                          length_cm=dims[0], width_cm=dims[1], height_cm=dims[2],
                          size_class=size_class(w, dims, ship), shipping_class=ship, hazmat=int(c["hazmat"]),
                          hazmat_note="Class 8 corrosive - lead-acid battery" if c["hazmat"] else None)
            reman_oem = cname in REMAN_CATS and rng.random() < 0.4
            core = c["core"] if (cname == "12V Battery" or reman_oem) else 0
            sup = rng.choices([s for s, _ in OEM_SUPPLIERS[fam]], [w_ for _, w_ in OEM_SUPPLIERS[fam]])[0]
            oem = new_part(part_number=pn_oem(fam), part_name=pname, brand=OEM_BRAND[fam], brand_type="OEM",
                           quality_tier="OEM", condition="Remanufactured" if reman_oem else "New",
                           list_price_usd=round(base, 2), unit_cost_usd=round(base * rng.uniform(0.55, 0.68), 2),
                           core_charge_usd=core, primary_supplier_id=sup, status="Active", superseded_by_part_id=None,
                           supersession_date=None, oem_family=fam, **common)
            group = [oem]
            # aftermarket equivalents
            n_after = 1 + (rng.random() < 0.35)
            tiers = ["Value", "Premium"][:n_after] if n_after == 2 else [rng.choices(["Value", "Premium"], [3, 1])[0]]
            for tier in tiers:
                opts = [b for b in AFTER_BRANDS if b[1] == tier]
                b = rng.choices(opts, [o[4] for o in opts])[0]
                f = rng.uniform(0.55, 0.75) if tier == "Value" else rng.uniform(0.8, 0.95)
                reman = cname in REMAN_CATS and tier == "Value"
                ap = new_part(part_number=pn_after(b[3]), part_name=pname, brand=b[0], brand_type="Aftermarket",
                              quality_tier=tier, condition="Remanufactured" if reman else "New",
                              list_price_usd=round(base * f, 2), unit_cost_usd=round(base * f * rng.uniform(0.42, 0.58), 2),
                              core_charge_usd=(c["core"] if (cname == "12V Battery" or reman) else 0),
                              primary_supplier_id=b[2], status="Active", superseded_by_part_id=None,
                              supersession_date=None, oem_family=fam, **common)
                interchange.append(dict(part_id=ap["part_id"], part_number=ap["part_number"], brand=ap["brand"],
                                        interchanges_with_part_id=oem["part_id"], interchanges_with_part_number=oem["part_number"],
                                        interchange_type="Aftermarket equivalent of OEM"))
                group.append(ap)
            # supersession: an older OEM number replaced by the current one
            if rng.random() < 0.06:
                sdate = (START + timedelta(days=rng.randint(-400, 500))).date().isoformat()
                old = new_part(**{**{k: v for k, v in oem.items() if k != "part_id"}, "part_number": pn_oem(fam),
                                  "status": "Superseded", "superseded_by_part_id": oem["part_id"], "supersession_date": sdate})
                interchange.append(dict(part_id=oem["part_id"], part_number=oem["part_number"], brand=oem["brand"],
                                        interchanges_with_part_id=old["part_id"], interchanges_with_part_number=old["part_number"],
                                        interchange_type="Supersedes older OEM number"))
                group.append(old)
            vids = veh_by_platform[key] if c["scope"] == "platform" else veh_by_engine[key]
            for p in group:
                for v_ in vids:
                    fitment.append(dict(part_id=p["part_id"], vehicle_id=v_))
P = {p["part_id"]: p for p in parts}
part_index = defaultdict(list)
for p in parts:
    if p["status"] == "Active":
        part_index[(p["category"], p["fits_key"])].append(p)

# ----------------------------------------------------------------------------- people
FIRST = "James Maria Robert Linda Michael Patricia David Jennifer William Elizabeth Carlos Ana Kevin Aisha Daniel Mei Brian Priya Jose Grace Tyrell Hannah Luis Fatima Marcus Olivia Andre Sofia Ethan Keiko".split()
LAST = "Smith Johnson Garcia Brown Davis Martinez Lopez Wilson Anderson Thomas Taylor Moore Jackson Lee Harris Clark Lewis Walker Young Allen King Wright Nguyen Patel Kim Rivera Campbell Mitchell Roberts Turner".split()
employees, eid = [], 0
def add_emp(role, wh, region, dept=None, langs="English", location=None):
    global eid
    eid += 1
    e = dict(employee_id=f"EMP-{eid:04d}", first_name=rng.choice(FIRST), last_name=rng.choice(LAST), role=role,
             warehouse_code=wh, region=region, work_location=location or (WH[wh]["name"] if wh else "St. Louis HQ"),
             support_department=dept, languages=langs,
             chat_access_scope="Company" if role in ("Purchasing Analyst", "Operations Director", "Customer Service Rep",
                                                     "Customer Service Supervisor") else
             "Region" if role == "Regional Manager" else "Warehouse")
    employees.append(e)
    return e
for w in WH.values():
    add_emp("Warehouse Manager", w["code"], w["region"])
    for _ in range(max(1, round(2 * w["size"]))): add_emp("Inventory Control Specialist", w["code"], w["region"])
    for _ in range(max(1, round(4 * w["size"]))): add_emp("Warehouse Associate", w["code"], w["region"])
for reg in ("Northeast", "Southeast", "Midwest", "Southwest", "West"):
    add_emp("Regional Manager", None, reg, location=f"Remote - {reg}")
for _ in range(3): add_emp("Purchasing Analyst", None, None)
add_emp("Operations Director", None, None, location="St. Louis HQ")   # company-wide view
add_emp("Customer Service Supervisor", None, None, dept="CS", langs="English, Spanish")
for dept, langs in [("CS", "English"), ("CS", "English, Spanish"), ("CS", "English, Spanish"), ("CS", "English"),
                    ("CS", "English"), ("DLR", "English"), ("DLR", "English, Spanish"), ("EXP", "English, Spanish"),
                    ("EXP", "English, French"), ("EXP", "English, Arabic"), ("RET", "English, Spanish"),
                    ("RET", "English"), ("BIL", "English, Spanish"), ("BIL", "English, French")]:
    add_emp("Customer Service Rep", None, None, dept=dept, langs=langs)
counters_by_wh = defaultdict(list)
for e in employees:
    if e["role"] in ("Inventory Control Specialist", "Warehouse Associate"):
        counters_by_wh[e["warehouse_code"]].append(e["employee_id"])

# ----------------------------------------------------------------------------- customers
st_codes, st_w = list(ST), [ST[s]["pop"] for s in ST]
make_w = defaultdict(float)
for v in vehicles: make_w[v["make"]] += v["popularity_weight"]
makes = [m for m in make_w if m != "Tesla"]
veh_ids, veh_w = [v["vehicle_id"] for v in vehicles], [v["popularity_weight"] for v in vehicles]
veh_by_make = defaultdict(list)
for v in vehicles: veh_by_make[v["make"]].append(v)
PLACES = "Summit Riverside Heritage Lakeview Pinecrest Gateway Valley Northside Harbor Crossroads Meadowbrook Ironwood Prairie Bayshore Canyon Granite Liberty Frontier Westgate Sunrise Oakmont Redstone Clearwater Brookfield".split()
TIER = {"A": (0.32, "Net 30"), "B": (0.25, "Net 30"), "C": (0.18, "Net 15")}
customers, dealers, individuals, names = [], [], [], set()
for i in range(200):
    st = rng.choices(st_codes, st_w)[0]
    mk = rng.choices(makes, [make_w[m] for m in makes])[0]
    while True:
        nm = f"{rng.choice(PLACES)} {mk} of {ST[st]['name']}"
        if nm not in names: names.add(nm); break
        nm = None
        if rng.random() < 0.1: break
    if not nm: continue
    tier = rng.choices("ABC", [2, 4.5, 3.5])[0]
    c = dict(customer_id=f"D{len(dealers) + 1:04d}", customer_type="Dealership", customer_name=nm, state=st,
             region=ST[st]["region"], timezone=ST[st]["tz"], home_warehouse=ST[st]["wh"], franchise_make=mk,
             price_tier=tier, discount_pct=TIER[tier][0], payment_terms=TIER[tier][1], primary_vehicle_id=None,
             customer_since=(START - timedelta(days=rng.randint(30, 3000))).date().isoformat())
    dealers.append(c); customers.append(c)
for i in range(5000):
    st = rng.choices(st_codes, st_w)[0]
    c = dict(customer_id=f"R{i + 1:05d}", customer_type="Individual", customer_name=f"Retail Customer {i + 1:05d}",
             state=st, region=ST[st]["region"], timezone=ST[st]["tz"], home_warehouse=ST[st]["wh"], franchise_make=None,
             price_tier="Retail", discount_pct=0.0, payment_terms="Card", primary_vehicle_id=rng.choices(veh_ids, veh_w)[0],
             customer_since=(START + timedelta(days=rng.randint(-900, 700))).date().isoformat())
    individuals.append(c); customers.append(c)
for c in customers:
    c.update(city=None, country="United States", country_code="US", billing_currency="USD", market="Domestic",
             _season=c["state"], _shift=0, _overseas=False)
dealer_w = [{"A": 3, "B": 2, "C": 1}[d["price_tier"]] for d in dealers]
intl_dealers, intl_individuals = [], []
ctry_codes, ctry_w = list(CTRY), [CTRY[c]["share"] for c in CTRY]
for i in range(60):
    cc = rng.choices(ctry_codes, ctry_w)[0]; ci = CTRY[cc]
    city, tz, whc = rng.choice(ci["cities"])
    mk = rng.choices(makes, [make_w[m] * (ci["truck"] if m in ("Ford", "Chevrolet", "GMC", "Ram", "Toyota") else 1) for m in makes])[0]
    nm = f"{rng.choice(PLACES)} {mk} {city}"
    if nm in names: nm = f"{nm} {i + 2}"
    names.add(nm)
    tier = rng.choices("ABC", [1, 4, 5])[0]
    terms = "Prepaid" if ci["overseas"] and rng.random() < 0.4 else TIER[tier][1]
    c = dict(customer_id=f"D{len(dealers) + i + 1:04d}", customer_type="Dealership", customer_name=nm, state=None,
             region=ci["market"], timezone=tz, home_warehouse=whc, franchise_make=mk, price_tier=tier,
             discount_pct=TIER[tier][0], payment_terms=terms, primary_vehicle_id=None,
             customer_since=(START - timedelta(days=rng.randint(30, 2000))).date().isoformat(),
             city=city, country=ci["name"], country_code=cc,
             billing_currency=ci["ccy"] if rng.random() < ci["local_bill"] else "USD", market="International",
             _season=ci["season"], _shift=ci["shift"], _overseas=ci["overseas"])
    intl_dealers.append(c); customers.append(c)
veh_w_by_ctry = {cc: [v["popularity_weight"] * (CTRY[cc]["truck"] if any(t in v["body_style"] for t in TRUCKY) else 1)
                      for v in vehicles] for cc in CTRY}
for i in range(700):
    cc = rng.choices(ctry_codes, ctry_w)[0]; ci = CTRY[cc]
    city, tz, whc = rng.choice(ci["cities"])
    c = dict(customer_id=f"R{5000 + i + 1:05d}", customer_type="Individual", customer_name=f"Retail Customer {5000 + i + 1:05d}",
             state=None, region=ci["market"], timezone=tz, home_warehouse=whc, franchise_make=None, price_tier="Retail",
             discount_pct=0.0, payment_terms="Card", primary_vehicle_id=rng.choices(veh_ids, veh_w_by_ctry[cc])[0],
             customer_since=(START + timedelta(days=rng.randint(-900, 700))).date().isoformat(),
             city=city, country=ci["name"], country_code=cc, billing_currency=ci["ccy"], market="International",
             _season=ci["season"], _shift=ci["shift"], _overseas=ci["overseas"])
    intl_individuals.append(c); customers.append(c)
intl_dealer_w = [{"A": 3, "B": 2, "C": 1}[d["price_tier"]] for d in intl_dealers]

# ----------------------------------------------------------------------------- orders
days, day_w = [], []
d = START
while d < NOW:
    days.append(d)
    day_w.append({5: 0.55, 6: 0.2}.get(d.weekday(), 1.0) * (1 + 0.12 * (d - START).days / 365))
    d += timedelta(days=1)
cat_names = list(CAT)
FILTER_CATS = {"Oil Filter", "Engine Air Filter", "Cabin Air Filter"}

def pick_line(cust, v, month):
    st = cust["_season"]
    month = (month - 1 + cust["_shift"]) % 12 + 1
    # business rule: lead-acid batteries (hazmat) are not exported overseas
    cands = [cn for cn in cat_names if applies(cn, v["fuel_type"]) and not (cn == "12V Battery" and cust["_overseas"])]
    ws = [CAT[cn]["pop"] * seasonal(cn, st, month) for cn in cands]
    for _ in range(6):
        cn = rng.choices(cands, ws)[0]
        key = v["platform_id"] if CAT[cn]["scope"] == "platform" else v["engine_code"]
        pool = part_index.get((cn, key))
        if not pool: continue
        want_oem = rng.random() < (0.8 if cust["customer_type"] == "Dealership" else 0.3)
        sub = [p for p in pool if (p["brand_type"] == "OEM") == want_oem] or pool
        return rng.choice(sub)
    return None

orders, lines = [], []
oid = lid = 0
while len(orders) < N_ORDERS:
    day = rng.choices(days, day_w)[0]
    intl = rng.random() < 0.13
    is_dealer = rng.random() < 0.4
    if intl: cust = rng.choices(intl_dealers, intl_dealer_w)[0] if is_dealer else rng.choice(intl_individuals)
    else: cust = rng.choices(dealers, dealer_w)[0] if is_dealer else rng.choice(individuals)
    tz = ZoneInfo(cust["timezone"])
    hour = rng.randint(7, 17) if is_dealer else rng.choices(range(7, 22), [1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 1])[0]
    local = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), tzinfo=tz)
    created = local.astimezone(UTC)
    if created > NOW: continue
    oid += 1
    ccy = cust["billing_currency"]
    rate = fx(ccy, created)
    mk = 0.02 if ccy != "USD" else 0.0          # FX conversion margin on local-currency invoices
    cinfo = CTRY.get(cust["country_code"])
    wh = cust["home_warehouse"]
    age = (NOW - created).total_seconds() / 86400
    if age < 1: status = "Processing" if rng.random() < 0.9 else "Shipped"
    elif age < 4: status = rng.choices(["Shipped", "Processing", "Delivered"], [7, 1, 2])[0]
    else: status = rng.choices(["Delivered", "Cancelled", "Returned"], [94, 2.5, 3.5 if age > 7 else 0])[0]
    shipped = created + timedelta(hours=rng.uniform(4, 30)) if status in ("Shipped", "Delivered", "Returned") else None
    if shipped and shipped > NOW: shipped, status = None, "Processing"
    far = wh in ("ANC", "HNL")
    if intl:
        if not cinfo["overseas"]: ship_mode, tdays = ("Truck (cross-border)" if is_dealer else "Parcel (cross-border)"), rng.uniform(*cinfo["transit"])
        elif is_dealer and rng.random() < 0.3: ship_mode, tdays = "Ocean (consolidated)", rng.uniform(20, 35)
        else: ship_mode, tdays = ("Air freight" if is_dealer else "Air parcel"), rng.uniform(*cinfo["transit"])
    else:
        ship_mode, tdays = "Ground", (rng.uniform(4, 9) if far else rng.uniform(1, 5))
    delivered = shipped + timedelta(days=tdays) if shipped and status in ("Delivered", "Returned") else None
    if delivered and delivered > NOW: delivered, status = None, "Shipped"
    n_lines = rng.randint(1, 6) if is_dealer else rng.choices([1, 2, 3], [6, 3, 1])[0]
    total, total_local, any_bo, origins = 0.0, 0.0, False, set()
    cur_items = []
    has_haz = has_over = False
    for ln in range(n_lines):
        if is_dealer:
            v = rng.choice(veh_by_make[cust["franchise_make"]]) if rng.random() < 0.85 else V[rng.choices(veh_ids, veh_w)[0]]
        else:
            v = V[cust["primary_vehicle_id"]] if rng.random() < 0.8 else V[rng.choices(veh_ids, veh_w)[0]]
        p = pick_line(cust, v, local.month)
        if not p: continue
        if is_dealer:
            qty = rng.randint(4, 24) if p["category"] in FILTER_CATS else rng.randint(2, 8) if p["category"] in (
                "Brake Pads", "Wiper Blade Set", "Spark Plug Set", "Brake Rotor") else rng.randint(1, 3)
            disc = cust["discount_pct"]
        else:
            qty = 2 if p["category"] in ("Brake Rotor", "Ignition Coil") and rng.random() < 0.5 else 1
            disc = 0.10 if rng.random() < 0.08 else 0.0
        unit = round(p["list_price_usd"] * (1 - disc), 2)
        lstat = status
        if status in ("Processing", "Shipped") and age < 21 and rng.random() < 0.03: lstat = "Backordered"
        elif status == "Delivered" and age < 21 and rng.random() < 0.012: lstat = "Backordered"
        any_bo |= lstat == "Backordered"
        core = p["core_charge_usd"]
        if not core or lstat in ("Cancelled", "Backordered"): core_status = None
        elif lstat == "Returned": core_status = "Returned"
        elif delivered and (NOW - delivered).days > 30: core_status = rng.choices(["Returned", "Not Returned"], [82, 18])[0]
        else: core_status = "Pending"
        lid += 1
        unit_local = money(unit * rate * (1 + mk), ccy)
        line_local = money(unit_local * qty, ccy)
        line_total = round(line_local / rate, 2)          # USD equivalent at the order-date rate
        total += line_total; total_local += line_local
        origin = SUP[p["primary_supplier_id"]]["cc"]; origins.add(origin)
        has_haz |= bool(p["hazmat"]); has_over |= p["shipping_class"] == "Oversize"
        if lstat != "Cancelled": cur_items.append((p, qty))
        lines.append(dict(order_line_id=f"SOL-{lid:07d}", order_id=f"SO-{oid:06d}", line_no=ln + 1, part_id=p["part_id"],
                          vehicle_id=v["vehicle_id"], quantity=qty, currency=ccy, unit_price_local=unit_local,
                          line_total_local=line_local, unit_price_usd=round(unit_local / rate, 2), discount_pct=disc,
                          line_total_usd=line_total, core_charge_usd=core * qty if core else 0, core_status=core_status,
                          line_status=lstat, fulfillment_warehouse=wh, country_of_origin=origin, hs_code=HS[p["category"]],
                          usmca_eligible=(int(origin in USMCA) if intl and cust["country_code"] in USMCA else None)))
    zone = (str(dom_zone(wh, cust["state"])) if not intl else INTL_ZONE[cust["country_code"]])
    if not intl and is_dealer and int(zone) <= 3 and rng.random() < 0.85: svc = "GW_ROUTE"
    elif not intl:
        if is_dealer or has_haz or has_over or far: svc = rng.choices(["UPS_GND", "FDX_GND"], [55, 45])[0]
        else: svc = rng.choices(["UPS_GND", "FDX_GND", "USPS_GA", "USPS_PM"], [35, 30, 25, 10])[0]
        if far and not (is_dealer or has_haz or has_over): svc = "USPS_PM"
    elif ship_mode in ("Truck (cross-border)", "Parcel (cross-border)"):
        svc = "FDX_IG" if cust["country_code"] == "CA" and rng.random() < 0.4 else "UPS_STD_CAMX"
    elif ship_mode == "Air parcel": svc = rng.choices(["UPS_WWX", "FDX_IE", "DHL_EXW", "USPS_PMI"], [4, 3, 1, 3])[0]
    elif ship_mode == "Air freight": svc = "AIR_FWD" if rng.random() < 0.75 else rng.choice(["UPS_WWS", "FDX_IP", "DHL_EXW"])
    else: svc = "OCEAN_LCL"
    car = SVC[svc]["carrier"]
    trk = None
    if shipped:
        trk = ("1Z" + r(LET + DIG, 16) if car == "UPS" else r(DIG, 12) if car == "FedEx" else
               "9400" + r(DIG, 18) if car == "USPS" else r(DIG, 10) if car == "DHL" else
               "GW-RT-" + r(DIG, 7) if car == "Gatewell Delivery" else ("AWB-" if svc == "AIR_FWD" else "BL-") + r(DIG, 9))
    carrier_cost = est_carrier_cost(svc, zone, cur_items, not is_dealer, total) if cur_items and status != "Cancelled" else 0.0
    final_status = "Partially Backordered" if any_bo and status != "Delivered" else status
    goods_local = money(total_local, ccy)
    if intl:
        ship_usd = round(carrier_cost * 1.05, 2)      # international shipping is passed through at cost + 5% handling
    else:
        ship_usd = 0.0 if is_dealer or total >= 99 else 9.99
    ship_local = money(ship_usd * rate * (1 + mk), ccy)
    if intl:
        incoterm = "DAP" if is_dealer else "DDP"
        tax_pct = cinfo["vat"]; tax_name = cinfo["tax"]
        tax_local = money((goods_local + ship_local) * tax_pct / 100, ccy)
        tax_by = "Buyer at import (DAP)" if is_dealer else "Seller at checkout (DDP)"
        customs = ("Cleared" if delivered else ("Held - missing documents" if rng.random() < 0.05 else
                   rng.choice(["In transit to border/port", "Awaiting clearance"])) if shipped else "Not shipped")
        docs = ["Commercial invoice"]
        if cust["country_code"] in USMCA and origins <= USMCA: docs.append("USMCA certification of origin")
        if total > 2500: docs.append("EEI filed in AES")
        docs = "; ".join(docs)
    else:
        incoterm = tax_pct = tax_name = tax_by = customs = docs = None
        tax_local = 0.0
    total_due = money(goods_local + ship_local + (tax_local if incoterm == "DDP" else 0), ccy)
    terms = cust["payment_terms"]
    if final_status == "Cancelled": pay_status, paid_at = "Void", None
    elif terms in ("Card", "Prepaid"):
        paid_at = created; pay_status = "Refunded" if final_status == "Returned" else "Paid"
    else:
        due = (shipped or created) + timedelta(days=30 if terms == "Net 30" else 15)
        pay_at = due + timedelta(days=rng.uniform(-6, 12))
        if pay_at <= NOW: paid_at, pay_status = pay_at, ("Credited" if final_status == "Returned" else "Paid")
        else: paid_at, pay_status = None, ("Overdue" if NOW > due else "Open")
    pay_rate = fx(ccy, paid_at) if paid_at else None
    fx_gl = round(total_due / pay_rate - total_due / rate, 2) if (pay_status == "Paid" and ccy != "USD") else 0.0
    orders.append(dict(order_id=f"SO-{oid:06d}", customer_id=cust["customer_id"], customer_type=cust["customer_type"],
                       order_type="International" if intl else "Domestic",
                       channel=rng.choice(["Dealer Portal", "Dealer Portal", "Phone"]) if is_dealer else
                       rng.choices(["Web", "Phone", "Counter Pickup"], [6, 2, 2])[0],
                       ship_to_city=cust["city"], ship_to_state=cust["state"], ship_to_region=cust["region"],
                       ship_to_country=cust["country"], ship_to_country_code=cust["country_code"],
                       fulfillment_warehouse=wh, customer_timezone=cust["timezone"],
                       ordered_at_utc=iso(created), ordered_at_local=local.isoformat(timespec="minutes"),
                       shipped_at_utc=iso(shipped), delivered_at_utc=iso(delivered),
                       delivered_at_local=local_iso(delivered, cust["timezone"]),
                       status=final_status, ship_mode=ship_mode, billing_currency=ccy,
                       fx_rate_units_per_usd=rate, fx_rate_date=created.date().isoformat(), fx_margin_pct=mk,
                       goods_total_local=goods_local, shipping_local=ship_local, import_tax_name=tax_name,
                       import_tax_pct=tax_pct, import_tax_local=tax_local, incoterm=incoterm, import_tax_paid_by=tax_by,
                       total_due_local=total_due, order_total_usd=round(total, 2), shipping_usd=ship_usd,
                       customs_status=customs, export_documents=docs, payment_terms=terms, payment_status=pay_status,
                       paid_at_utc=iso(paid_at), payment_fx_rate=pay_rate, fx_gain_loss_usd=fx_gl,
                       carrier=car, carrier_service_code=svc, carrier_service=SVC[svc]["name"], tracking_number=trk,
                       carrier_cost_usd=carrier_cost, shipping_margin_usd=round(ship_usd - carrier_cost, 2)))

# Planted scenario: a top-selling brake pad is stocked out at ATL with dealer backorders
recent_cut = NOW - timedelta(days=120)
order_by_id = {o["order_id"]: o for o in orders}
demand, last_sold = defaultdict(float), {}
for l in lines:
    o = order_by_id[l["order_id"]]
    if l["line_status"] == "Cancelled": continue
    t = o["ordered_at_utc"]
    if t >= iso(recent_cut): demand[(l["part_id"], l["fulfillment_warehouse"])] += l["quantity"]
    if o["shipped_at_utc"]:
        k = (l["part_id"], l["fulfillment_warehouse"])
        if k not in last_sold or o["shipped_at_utc"] > last_sold[k]: last_sold[k] = o["shipped_at_utc"]
recent_pad = defaultdict(int)
for l in lines:
    if (l["fulfillment_warehouse"] == "ATL" and P[l["part_id"]]["category"] == "Brake Pads"
            and order_by_id[l["order_id"]]["ordered_at_utc"] >= iso(NOW - timedelta(days=30))
            and l["line_status"] in ("Processing", "Shipped", "Delivered")):
        recent_pad[l["part_id"]] += 1
STOCKOUT_PART = max(recent_pad, key=recent_pad.get)
recent_atl = [l for l in lines if l["part_id"] == STOCKOUT_PART and l["fulfillment_warehouse"] == "ATL"
              and order_by_id[l["order_id"]]["ordered_at_utc"] >= iso(NOW - timedelta(days=12))
              and l["line_status"] in ("Processing", "Shipped", "Delivered")]
recent_atl = [l for l in lines if l["part_id"] == STOCKOUT_PART and l["fulfillment_warehouse"] == "ATL"
              and order_by_id[l["order_id"]]["ordered_at_utc"] >= iso(NOW - timedelta(days=30))
              and l["line_status"] in ("Processing", "Shipped", "Delivered")]
recent_atl.sort(key=lambda l: order_by_id[l["order_id"]]["ordered_at_utc"], reverse=True)
for l in recent_atl[:5]:
    l["line_status"] = "Backordered"; l["core_status"] = None
    o = order_by_id[l["order_id"]]
    o["status"] = "Partially Backordered"; o["shipped_at_utc"] = o["delivered_at_utc"] = o["delivered_at_local"] = None

# ----------------------------------------------------------------------------- inventory
reserved, backordered = defaultdict(int), defaultdict(int)
for l in lines:
    k = (l["part_id"], l["fulfillment_warehouse"])
    if l["line_status"] == "Processing": reserved[k] += l["quantity"]
    if l["line_status"] == "Backordered": backordered[k] += l["quantity"]
ZONE = {"Brakes": "B", "Filters": "F", "Ignition": "I", "Engine": "E", "Electrical": "L", "Sensors": "S", "Wipers": "W",
        "Lighting": "H", "Suspension & Steering": "U", "Heating & Cooling": "C", "Body": "Y"}
inventory = {}
for p in parts:
    for w in WH.values():
        k = (p["part_id"], w["code"])
        dq = demand.get(k, 0.0)
        aged = False
        if p["status"] == "Superseded":
            if rng.random() < 0.12 * w["size"]: on_hand, aged = rng.randint(1, 8), True
            else: continue
        elif dq > 0:
            dd = dq / 120
            lead_ = 30 if SUP[p["primary_supplier_id"]]["cc"] in ("JP", "KR", "CN", "DE") else 8
            rop_ = math.ceil(dd * lead_ * 1.2) + 1
            r_ = rng.random()
            if r_ < 0.04: on_hand = 0                                      # stocked out
            elif r_ < 0.16: on_hand = rng.randint(0, rop_)                 # at or below reorder point
            else: on_hand = rop_ + round(dd * rng.uniform(5, 45)) + rng.randint(0, 2)
        else:
            if rng.random() < (0.06 * w["size"] if w["size"] >= 0.5 else 0.02): on_hand, aged = rng.randint(1, 4), True
            else: continue
        if backordered[k]: on_hand = reserved[k]
        on_hand = max(on_hand, reserved[k])
        if w["code"] in COLD_WH and p["category"] == "12V Battery": on_hand = round(on_hand * 0.5)
        dd = dq / 120
        lead = 30 if SUP[p["primary_supplier_id"]]["cc"] in ("JP", "KR", "CN", "DE") else 8
        inventory[k] = dict(part_id=p["part_id"], warehouse_code=w["code"],
                            bin_location=f"{ZONE[p['category_group']]}-{rng.randint(1, 40):02d}-{rng.randint(1, 8):02d}",
                            qty_on_hand=on_hand, qty_reserved=reserved[k], qty_in_transit=0, qty_backordered=backordered[k],
                            qty_damaged=(rng.randint(1, 2) if on_hand >= 2 and rng.random() < 0.03 else 0), qty_missing=0,
                            reorder_point=(math.ceil(dd * lead * 1.2) + 1) if dd > 0 else 0,
                            reorder_qty=max(2, math.ceil(dd * 30)) if dd > 0 else 0, avg_daily_demand=round(dd, 3),
                            unit_cost_usd=p["unit_cost_usd"], last_received_utc=None, last_sold_utc=last_sold.get(k),
                            last_counted_utc=None, _aged=aged)

# ----------------------------------------------------------------------------- shipments
shipments, ship_lines = [], []
sid = slid = 0
def add_shipment(stype, origin, dest, ship_utc, mode, carrier, port, days, items, status_override=None, note=None):
    global sid, slid
    sid += 1
    eta = ship_utc + timedelta(days=days)
    r_ = rng.random()
    delay = rng.uniform(0, 1) if r_ < 0.75 else rng.uniform(2, 4) if r_ < 0.95 else rng.uniform(6, 12)
    delivered = eta + timedelta(days=delay)
    if status_override: status, delivered = status_override, None
    elif delivered <= NOW: status = "Delivered"
    elif NOW > eta: status, delivered = "Delayed", None
    else: status, delivered = "In Transit", None
    otz = origin["tz"]
    dtz = WH[dest]["tz"]
    ccy = SUP_CCY.get(origin["id"], "USD")
    rate = fx(ccy, ship_utc)
    sh = dict(shipment_id=f"SHP-{sid:06d}", shipment_type=stype,
              po_number=f"PO-{sid + 40000:06d}" if stype == "Supplier PO" else None,
              transfer_number=f"TR-{sid + 7000:06d}" if stype == "Warehouse Transfer" else None,
              origin_id=origin["id"], origin_name=origin["name"], origin_city=origin["city"],
              origin_country=origin["country"], origin_country_code=origin["cc"], origin_timezone=otz,
              destination_warehouse=dest, destination_timezone=dtz, mode=mode, carrier=carrier,
              tracking_number=f"{slug(carrier)[:3]}{rng.randint(10 ** 9, 10 ** 10 - 1)}", port_of_entry=port,
              ship_date_utc=iso(ship_utc), ship_date_origin_local=local_iso(ship_utc, otz),
              eta_utc=iso(eta), eta_destination_local=local_iso(eta, dtz),
              delivered_at_utc=iso(delivered), delivered_at_destination_local=local_iso(delivered, dtz),
              status=status, exception_note=note, currency=ccy, fx_rate_units_per_usd=rate,
              po_value_local=0.0, po_value_usd=0.0)
    shipments.append(sh)
    for part_id, q in items:
        slid += 1
        cost_local = money(P[part_id]["unit_cost_usd"] * rate, ccy)
        ship_lines.append(dict(shipment_line_id=f"SHL-{slid:07d}", shipment_id=sh["shipment_id"], part_id=part_id,
                               quantity=q, currency=ccy, unit_cost_local=cost_local,
                               unit_cost_usd=round(cost_local / rate, 2)))
        sh["po_value_local"] = money(sh["po_value_local"] + cost_local * q, ccy)
        sh["po_value_usd"] = round(sh["po_value_usd"] + cost_local * q / rate, 2)
    return sh

def origin_hours(start_date, tz):
    loc = datetime(start_date.year, start_date.month, start_date.day, rng.randint(8, 17), rng.randint(0, 59), tzinfo=ZoneInfo(tz))
    return loc.astimezone(UTC)

stock_by = defaultdict(list)
for (pid, whc), inv in inventory.items():
    if P[pid]["status"] == "Active":
        stock_by[(whc, P[pid]["primary_supplier_id"])].append(pid)
for (whc, sup), plist in stock_by.items():
    s = SUP[sup]
    ocean = s["cc"] in ("JP", "KR", "CN", "DE")
    interval = (28 if ocean else 12) / WH[whc]["size"]
    t = START - timedelta(days=45) + timedelta(days=rng.uniform(0, interval))
    weights = [inventory[(p_, whc)]["avg_daily_demand"] + 0.01 for p_ in plist]
    while t <= NOW:
        ship_utc = origin_hours(t, s["tz"])
        if ship_utc > NOW: break
        k = min(len(plist), max(3, int(rng.randint(10, 35) * WH[whc]["size"])))
        chosen = sorted(set(rng.choices(plist, weights, k=k)))     # sorted: set order varies between runs
        items = []
        for p_ in chosen:
            dd = inventory[(p_, whc)]["avg_daily_demand"]
            items.append((p_, max(1, round(dd * interval * rng.uniform(0.8, 1.3))) if dd > 0 else rng.randint(1, 4)))
        mode, carrier, port, days_ = route(s["cc"], whc)
        add_shipment("Supplier PO", dict(id=sup, name=s["name"], city=s["city"], country=s["country"], cc=s["cc"], tz=s["tz"]),
                     whc, ship_utc, mode, carrier, port, days_, items)
        t += timedelta(days=interval * rng.uniform(0.8, 1.2))

def wh_origin(code):
    w = WH[code]
    return dict(id=code, name=w["name"], city=w["city"], country="United States", cc="US", tz=w["tz"])

# Historical transfers between warehouses
big = [c for c in WH if WH[c]["size"] >= 0.7]
for _ in range(260):
    o, dst = rng.sample(big + ["ANC", "HNL"], 2)
    if o in ("ANC", "HNL"): continue
    pool = [pid for (pid, whc) in inventory if whc == o and P[pid]["status"] == "Active"]
    items = [(p_, rng.randint(1, 10)) for p_ in sorted(set(rng.sample(pool, min(len(pool), rng.randint(3, 12)))))]
    t = START + timedelta(days=rng.uniform(0, (NOW - START).days - 3))
    far = dst in ("ANC", "HNL")
    add_shipment("Warehouse Transfer", wh_origin(o), dst, origin_hours(t, WH[o]["tz"]),
                 "Truck + Barge" if far else "Truck", CARRIERS["Truck + Barge"][0] if far else rng.choice(CARRIERS["Truck"]),
                 None, rng.uniform(12, 18) if far else rng.uniform(2, 6), items)

# Planted scenario: winter battery transfers in transit to cold-climate warehouses
for dst in sorted(COLD_WH):
    for _ in range(2 if dst != "ANC" else 1):
        o = rng.choice(["DFW", "PHX", "LAX", "ATL"])
        bats = [pid for (pid, whc) in inventory if whc == dst and P[pid]["category"] == "12V Battery" and P[pid]["status"] == "Active"]
        items = [(p_, rng.randint(4, 20)) for p_ in sorted(set(rng.sample(bats, min(len(bats), rng.randint(15, 30)))))]
        t = NOW - timedelta(days=rng.uniform(0.5, 3))
        far = dst == "ANC"
        add_shipment("Warehouse Transfer", wh_origin(o), dst, t, "Truck + Barge" if far else "Truck",
                     CARRIERS["Truck + Barge"][0] if far else rng.choice(CARRIERS["Truck"]), None,
                     rng.uniform(14, 18) if far else rng.uniform(3, 6), items,
                     note="Seasonal pre-positioning of batteries ahead of winter")

# Planted scenario: Ningbo shipments held by U.S. Customs, past ETA
s = SUP["SUP-NGB"]
for dst in ("LAX", "LAX", "DFW", "DFW", "SEA"):
    pool = stock_by[(dst, "SUP-NGB")]
    items = [(p_, rng.randint(5, 30)) for p_ in sorted(set(rng.sample(pool, min(len(pool), rng.randint(12, 25)))))]
    mode, carrier, port, days_ = "Ocean", rng.choice(CARRIERS["Ocean"]), \
        {"LAX": "Long Beach, CA", "DFW": "Houston, TX", "SEA": "Seattle-Tacoma, WA"}[dst], rng.uniform(20, 30)
    ship_utc = origin_hours(NOW - timedelta(days=days_ + rng.uniform(3, 9)), s["tz"])
    add_shipment("Supplier PO", dict(id="SUP-NGB", name=s["name"], city=s["city"], country=s["country"], cc=s["cc"], tz=s["tz"]),
                 dst, ship_utc, mode, carrier, port, days_, items, status_override="Customs Hold",
                 note=f"Held by U.S. Customs at {port} - documentation review")

# Relief shipment for the ATL stockout
add_shipment("Supplier PO", dict(id=P[STOCKOUT_PART]["primary_supplier_id"], **{k: SUP[P[STOCKOUT_PART]["primary_supplier_id"]][k] for k in ("name", "city", "country", "cc", "tz")}),
             "ATL", NOW - timedelta(days=1.5), "Air", "SkyBridge Air Cargo", "Atlanta ATL", 4.0,
             [(STOCKOUT_PART, 120)], note="Expedited to clear dealer backorders")

sh_by_id = {sh["shipment_id"]: sh for sh in shipments}
for sl in ship_lines:
    sh = sh_by_id[sl["shipment_id"]]
    k = (sl["part_id"], sh["destination_warehouse"])
    if k not in inventory: continue
    if sh["status"] in ("In Transit", "Delayed", "Customs Hold"):
        inventory[k]["qty_in_transit"] += sl["quantity"]
    elif sh["status"] == "Delivered" and not inventory[k]["_aged"]:
        if not inventory[k]["last_received_utc"] or sh["delivered_at_utc"] > inventory[k]["last_received_utc"]:
            inventory[k]["last_received_utc"] = sh["delivered_at_utc"]
for inv in inventory.values():
    if inv["_aged"]:
        inv["last_received_utc"] = iso(NOW - timedelta(days=rng.randint(200, 640)))
        if inv["last_sold_utc"] and inv["last_sold_utc"] > iso(NOW - timedelta(days=150)): inv["last_sold_utc"] = None
    elif not inv["last_received_utc"]:
        inv["last_received_utc"] = iso(NOW - timedelta(days=rng.randint(20, 120)))

# ----------------------------------------------------------------------------- cycle counts
SHRINK_CATS = {"Oxygen Sensor", "Ignition Coil", "Spark Plug Set", "ABS Wheel Speed Sensor"}
counts, cid = [], 0
inv_by_wh = defaultdict(list)
for k, inv in inventory.items(): inv_by_wh[k[1]].append(inv)
for whc, invs in inv_by_wh.items():
    tz = WH[whc]["tz"]
    for week in range(52):
        wk_start = NOW - timedelta(days=7 * (week + 1))
        picks = rng.sample(invs, max(1, int(len(invs) * 0.012)))
        if whc == "NWK":  # suspected theft: small high-value parts recounted more often
            hot = [i for i in invs if P[i["part_id"]]["category"] in SHRINK_CATS]
            picks += rng.sample(hot, min(len(hot), max(1, len(hot) // 10)))
        for inv in picks:
            d_ = wk_start + timedelta(days=rng.randint(0, 4))
            when = origin_hours(d_, tz)
            if when > NOW: continue
            recent = (NOW - when).days <= 30
            sys_q = inv["qty_on_hand"] if recent else max(0, round(inv["qty_on_hand"] * rng.uniform(0.6, 1.4)))
            shrink = whc == "NWK" and P[inv["part_id"]]["category"] in SHRINK_CATS
            if shrink and sys_q > 0 and rng.random() < 0.55: var = -rng.randint(1, min(6, sys_q))
            elif rng.random() < 0.08:
                var = rng.choice([-3, -2, -1, -1, -1, 1, 1, 2])
                if sys_q + var < 0: var = 0
            else: var = 0
            if var == 0: cstat, reason = "Matched", None
            elif recent: cstat, reason = "Under Review", "Investigating"
            else:
                cstat = "Adjusted"
                reason = rng.choice(["Unknown / shrinkage", "Mis-pick", "Receiving error", "Damaged in handling",
                                     "Found in wrong bin"] if var < 0 else ["Receiving error", "Found in wrong bin", "Return not logged"])
            cid += 1
            counts.append(dict(count_id=f"CC-{cid:06d}", part_id=inv["part_id"], warehouse_code=whc,
                               counted_at_utc=iso(when), counted_at_local=local_iso(when, tz),
                               counted_by=rng.choice(counters_by_wh[whc]), system_qty=sys_q, counted_qty=sys_q + var,
                               variance=var, variance_value_usd=round(var * inv["unit_cost_usd"], 2),
                               status=cstat, reason=reason))
latest = {}
for c in counts:
    k = (c["part_id"], c["warehouse_code"])
    if k not in latest or c["counted_at_utc"] > latest[k]["counted_at_utc"]: latest[k] = c
for k, c in latest.items():
    inventory[k]["last_counted_utc"] = c["counted_at_utc"]
    if c["status"] == "Under Review" and c["variance"] < 0:
        inventory[k]["qty_missing"] = -c["variance"]

# ----------------------------------------------------------------------------- support cases (live-person contacts)
reps = [e for e in employees if e["role"] == "Customer Service Rep"]
cust_by_id = {c["customer_id"]: c for c in customers}
lines_by_order = defaultdict(list)
for l in lines: lines_by_order[l["order_id"]].append(l)
SPANISH = {"MX", "CO", "CR", "CL", "DO"}
HANDOFF = ["Customer asked for a person", "Agent not confident in fitment answer", "Refund or credit above agent limit",
           "Complaint or escalation", "Account change requested"]
cases, csid = [], 0
def lang_for(cu):
    cc = cu["country_code"]
    if cc in SPANISH: return "Spanish" if rng.random() < 0.85 else "English"
    if cc in ("SA", "AE"): return "Arabic" if rng.random() < 0.5 else "English"
    if cc == "CA" and cu["city"] == "Montreal": return "French" if rng.random() < 0.7 else "English"
    return "Spanish" if rng.random() < 0.12 else "English"
def add_case(cu, opened, dept, reason, order=None, force_open=False, note=None):
    global csid
    if opened > NOW: return
    lang = lang_for(cu)
    channel = rng.choices(["AI chat handoff", "Phone", "Email"], [45, 35, 20])[0]
    if channel == "Phone" and next_open(dept, opened) > NOW: channel = "AI chat handoff"  # line closed right now
    if channel != "Phone":  # chats and emails happen during the customer's waking hours (their own time zone)
        loc = opened.astimezone(ZoneInfo(cu["timezone"]))
        opened = loc.replace(hour=rng.choices(range(7, 23), [1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 1])[0]).astimezone(UTC)
        if opened > NOW: return
    if channel == "Phone":  # calls only connect while the line is open
        opened = next_open(dept, opened) + timedelta(minutes=rng.uniform(0, 90))
        if opened > NOW: return
    pool = [r_ for r_ in reps if r_["support_department"] == dept and lang in r_["languages"]]
    if not pool:
        pool = [r_ for r_ in reps if r_["support_department"] == dept]
        note = ((note + "; ") if note else "") + f"{lang} interpreter line used"
    start = next_open(dept, opened) if channel != "Email" else opened
    first = start + timedelta(minutes=rng.uniform(1, 8) if channel == "Phone" else rng.uniform(2, 15)
                              if channel == "AI chat handoff" else rng.uniform(30, 600))
    if channel == "Email" and not dept_open(dept, first): first = next_open(dept, first) + timedelta(minutes=rng.uniform(5, 60))
    recent = (NOW - opened).days < 3
    if force_open or (recent and rng.random() < 0.7):
        status = rng.choice(["Open", "In Progress", "Waiting on Customer"]); resolved = None
        if first > NOW: first, status = None, "Queued (after hours)"
    else:
        status = "Resolved"; resolved = first + timedelta(hours=rng.uniform(0.2, 72))
        if resolved > NOW: status, resolved = "In Progress", None
    csid += 1
    cases.append(dict(case_id=f"CS-{csid:06d}", customer_id=cu["customer_id"], order_id=order["order_id"] if order else None,
                      opened_at_utc=iso(opened), opened_at_customer_local=local_iso(opened, cu["timezone"]),
                      opened_at_hq_local=local_iso(opened, "America/Chicago"), channel=channel,
                      ai_handoff_reason=rng.choice(HANDOFF) if channel == "AI chat handoff" else None,
                      opened_after_hours=int(not dept_open(dept, opened)), department_id=dept,
                      contact_reason=reason, language=lang,
                      priority="High" if (force_open or cu["customer_type"] == "Dealership") else rng.choice(["Normal", "Normal", "Low"]),
                      assigned_to=rng.choice(pool)["employee_id"] if first else None,
                      first_response_at_utc=iso(first), first_response_minutes=round((first - opened).total_seconds() / 60) if first else None,
                      status=status, resolved_at_utc=iso(resolved), notes=note))
for o in orders:
    cu = cust_by_id[o["customer_id"]]
    t0 = datetime.strptime(o["ordered_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    if o["status"] == "Partially Backordered" and t0 > NOW - timedelta(days=21) and rng.random() < 0.6:
        add_case(cu, min(t0 + timedelta(days=rng.uniform(1, 4)), NOW - timedelta(hours=rng.uniform(2, 30))),
                 "DLR" if cu["customer_type"] == "Dealership" else "CS",
                 "Backorder ETA", o, force_open=True)
    elif o["customs_status"] == "Held - missing documents":
        add_case(cu, min(t0 + timedelta(days=rng.uniform(3, 6)), NOW - timedelta(hours=rng.uniform(2, 30))), "EXP",
                 "Customs hold on international order", o,
                 force_open=True, note="Shipment held at destination customs; commercial invoice re-requested")
    elif o["payment_status"] == "Overdue" and rng.random() < 0.3:
        add_case(cu, NOW - timedelta(days=rng.uniform(0.5, 5)), "BIL", "Overdue invoice follow-up", o)
    elif rng.random() < 0.02:
        if o["order_type"] == "International":
            reason, dept = rng.choice([("Import tax or duties question", "EXP"), ("Currency conversion or billing question", "BIL"),
                                       ("Where is my order", "EXP"), ("Wrong part / fitment issue", "CS")])
        elif o["status"] in ("Delivered", "Returned"):
            reason, dept = rng.choice([("Wrong part / fitment issue", "CS"), ("Damaged on arrival", "RET"),
                                       ("Return or core refund", "RET"), ("Invoice question", "BIL")])
        else:
            reason, dept = "Where is my order", "CS"
        add_case(cu, t0 + timedelta(days=rng.uniform(0.2, 10)), dept, reason, o)
for _ in range(500):  # pre-sale questions not tied to an order
    cu = rng.choice(customers)
    reason, dept = rng.choice([("Fitment question before ordering", "CS"), ("Part availability / pricing", "CS"),
                               ("Dealer account or pricing tier", "DLR"), ("International shipping quote", "EXP")])
    if dept == "DLR" and cu["customer_type"] != "Dealership": reason, dept = "Part availability / pricing", "CS"
    if dept == "EXP" and cu["market"] == "Domestic": reason, dept = "Fitment question before ordering", "CS"
    add_case(cu, START + timedelta(seconds=rng.uniform(0, (NOW - START).total_seconds())), dept, reason)

# ----------------------------------------------------------------------------- write SQLite + CSV
for inv in inventory.values(): inv.pop("_aged")
tables = {
    "warehouses": [dict(warehouse_code=w["code"], warehouse_name=w["name"], city=w["city"], state=w["state"],
                        region=w["region"], country="United States", country_code="US", timezone=w["tz"],
                        relative_size=w["size"]) for w in WH.values()],
    "states": [dict(state_code=s["code"], state_name=s["name"], region=s["region"], timezone=s["tz"],
                    serving_warehouse=s["wh"], climate=("Cold" if s["code"] in COLD else "Hot" if s["code"] in HOT else "Mild"),
                    road_salt_state=int(s["code"] in SALT)) for s in ST.values()],
    "suppliers": [dict(supplier_id=s["id"], supplier_name=s["name"], city=s["city"], province_or_state=s["province"],
                       country=s["country"], country_code=s["cc"], timezone=s["tz"]) for s in SUP.values()],
    "vehicles": vehicles,
    "platforms": [{k: v for k, v in p.items() if k != "family"} for p in platforms.values()],
    "parts": parts,
    "part_fitment": fitment,
    "part_interchange": interchange,
    "employees": employees,
    "customers": [{k: v for k, v in c.items() if not k.startswith("_")} for c in customers],
    "company": [COMPANY],
    "support_departments": [dict(department_id=d["id"], department_name=d["name"], phone=d["phone"], email=d["email"],
                                 handles=d["handles"], hours_timezone="America/Chicago",
                                 weekday_hours=f'{d["wk"][0]:02d}:00-{d["wk"][1]:02d}:00',
                                 saturday_hours=f'{d["sat"][0]:02d}:00-{d["sat"][1]:02d}:00' if d["sat"] else "Closed",
                                 sunday_hours="Closed", languages=d["langs"]) for d in DEPT.values()],
    "support_cases": cases,
    "faq": [dict(faq_id=f"FAQ-{i + 1:02d}", category=f[0], question=f[1], answer=f[2], keywords=f[3],
                 related_department_id=f[4],
                 page_url="https://www.gatewellautoparts.example/faq#" + re.sub(r"[^a-z0-9]+", "-", f[1].lower()).strip("-"))
            for i, f in enumerate(FAQ)],
    "shipping_services": list(SVC_ROWS.values()),
    "shipping_rates": list(RATE_ROWS.values()),
    "shipping_surcharges": [dict(carrier=x[1], surcharge_code=x[0], surcharge_name=x[2], applies_to=x[3],
                                 amount_usd=x[4], percent=x[5], rule=x[6], source="Synthetic estimate") for x in SURCHARGES],
    "shipping_zones_domestic": [dict(warehouse_code=w, state_code=st_, zone=dom_zone(w, st_)) for w in WH for st_ in ST],
    "currencies": [dict(currency_code=c["code"], currency_name=c["name"], symbol=c["symbol"], decimals=c["dec"],
                        pegged_to_usd=c["peg"]) for c in CCY.values()],
    "exchange_rates": fx_rows,
    "countries": [dict(country_code="US", country_name="United States", currency_code="USD", market_region="Domestic",
                       serving_warehouses="All", overseas=0, usmca_member=1, import_tax_name=None, import_tax_pct=None,
                       typical_delivery_days="1-5 (AK/HI 4-9)", climate_proxy_state=None, southern_hemisphere=0,
                       shipping_zone="Domestic")] +
                 [dict(country_code=c["cc"], country_name=c["name"], currency_code=c["ccy"], market_region=c["market"],
                       serving_warehouses=", ".join(sorted({w for _, _, w in c["cities"]})), overseas=int(c["overseas"]),
                       usmca_member=int(c["cc"] in USMCA), import_tax_name=c["tax"], import_tax_pct=c["vat"],
                       typical_delivery_days=f'{c["transit"][0]}-{c["transit"][1]} (ocean 20-35)' if c["overseas"] else f'{c["transit"][0]}-{c["transit"][1]}',
                       climate_proxy_state=c["season"], southern_hemisphere=int(c["shift"] == 6),
                       shipping_zone=INTL_ZONE[c["cc"]]) for c in CTRY.values()],
    "orders": orders,
    "order_lines": lines,
    "shipments": shipments,
    "shipment_lines": ship_lines,
    "inventory": list(inventory.values()),
    "cycle_counts": counts,
}
PKS = {"warehouses": "warehouse_code", "states": "state_code", "suppliers": "supplier_id", "vehicles": "vehicle_id",
       "platforms": "platform_id", "parts": "part_id", "employees": "employee_id", "customers": "customer_id",
       "orders": "order_id", "currencies": "currency_code", "support_departments": "department_id", "support_cases": "case_id", "faq": "faq_id", "shipping_services": "service_code", "countries": "country_code", "order_lines": "order_line_id", "shipments": "shipment_id",
       "shipment_lines": "shipment_line_id", "cycle_counts": "count_id"}

def sqltype(vals):
    vs = [v for v in vals if v is not None]
    if vs and all(isinstance(v, int) and not isinstance(v, bool) for v in vs): return "INTEGER"
    if vs and all(isinstance(v, (int, float)) for v in vs): return "REAL"
    return "TEXT"

# Storage settings that keep the file small without changing any data:
#  - narrow tables keyed by text IDs are stored in key order (WITHOUT ROWID), so each key is stored once
#  - 8 KB pages
SLIM_TABLES = {"part_fitment", "order_lines", "shipment_lines", "exchange_rates", "inventory"}
# The demo keeps history from this date on (closed orders and delivered shipments before it are dropped),
# which keeps the database file around 43 MB. Recent data and every demo scenario are unaffected.
HISTORY_START = "2025-01-01T00:00:00Z"

# Fictional names: every real make, model, engine trade name, carrier and OEM part number is
# replaced here, after generation, so the random draws and every number stay the same.
import name_map
name_map.translate(tables)

if os.path.exists(DB_PATH): os.remove(DB_PATH)
con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA page_size = 8192")
os.makedirs(CSV_DIR, exist_ok=True)
for name, rows in tables.items():
    cols = list(rows[0].keys())
    pk = PKS.get(name)
    if pk in cols: cols = [pk] + [c for c in cols if c != pk]
    defs = [f'"{c}" {sqltype([r_[c] for r_ in rows])}{" PRIMARY KEY" if PKS.get(name) == c else ""}' for c in cols]
    if name == "inventory": defs.append("PRIMARY KEY (part_id, warehouse_code)")
    if name == "part_fitment": defs.append("PRIMARY KEY (part_id, vehicle_id)")
    if name == "exchange_rates": defs.append("PRIMARY KEY (rate_date, currency_code)")
    if name == "shipping_rates": defs.append("PRIMARY KEY (service_code, zone)")
    if name == "shipping_zones_domestic": defs.append("PRIMARY KEY (warehouse_code, state_code)")
    con.execute(f'CREATE TABLE "{name}" ({", ".join(defs)})' + (" WITHOUT ROWID" if name in SLIM_TABLES else ""))
    con.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" * len(cols))})', [tuple(r_[c] for c in cols) for r_ in rows])

con.executescript("""
CREATE INDEX ix_fit_vehicle ON part_fitment(vehicle_id);
CREATE INDEX ix_parts_number ON parts(part_number);
CREATE INDEX ix_parts_cat ON parts(category);
CREATE INDEX ix_inv_wh ON inventory(warehouse_code);
CREATE INDEX ix_ol_order ON order_lines(order_id);
CREATE INDEX ix_ol_part ON order_lines(part_id);
CREATE INDEX ix_orders_cust ON orders(customer_id);
CREATE INDEX ix_orders_date ON orders(ordered_at_utc);
CREATE INDEX ix_shl_ship ON shipment_lines(shipment_id);
CREATE INDEX ix_shl_part ON shipment_lines(part_id);
CREATE INDEX ix_cc_part ON cycle_counts(part_id, warehouse_code);
CREATE INDEX ix_veh_ymm ON vehicles(make, model, year);

-- One row per part per warehouse with every quantity bucket and a reorder flag
CREATE VIEW v_stock_position AS
SELECT i.part_id, p.part_number, p.part_name, p.brand, p.brand_type, p.quality_tier, p.category, p.category_group,
       p.condition, p.size_class, p.weight_kg, p.weight_lb, p.hazmat, p.fits_summary, p.status AS part_status,
       i.warehouse_code, w.city AS warehouse_city, w.state AS warehouse_state, w.region, w.country, w.timezone,
       i.bin_location, i.qty_on_hand, i.qty_reserved, i.qty_damaged, i.qty_missing,
       MAX(i.qty_on_hand - i.qty_reserved - i.qty_damaged - i.qty_missing, 0) AS qty_available,
       i.qty_in_transit, i.qty_backordered, i.reorder_point, i.reorder_qty, i.avg_daily_demand,
       CASE WHEN i.reorder_point > 0 AND MAX(i.qty_on_hand - i.qty_reserved - i.qty_damaged - i.qty_missing, 0)
                 + i.qty_in_transit <= i.reorder_point THEN 1 ELSE 0 END AS needs_reorder,
       ROUND(i.qty_on_hand * i.unit_cost_usd, 2) AS stock_value_usd,
       i.last_received_utc, i.last_sold_utc, i.last_counted_utc,
       CAST(julianday('2026-10-11T21:00:00') - julianday(MAX(COALESCE(i.last_sold_utc, ''), COALESCE(i.last_received_utc, ''))) AS INTEGER) AS days_since_last_activity
FROM inventory i JOIN parts p USING (part_id) JOIN warehouses w USING (warehouse_code);

-- Units sold (shipped, delivered or returned lines) by month, region, warehouse, category
CREATE VIEW v_sales AS
SELECT o.order_id, substr(o.ordered_at_utc, 1, 7) AS order_month, o.ordered_at_utc, o.ordered_at_local,
       o.order_type, o.customer_type, o.channel, o.ship_to_city, o.ship_to_state, o.ship_to_region, o.ship_to_country,
       o.ship_to_country_code, o.fulfillment_warehouse, o.ship_mode,
       ol.part_id, p.part_number, p.part_name, p.category, p.category_group, p.brand, p.brand_type,
       v.year AS vehicle_year, v.make AS vehicle_make, v.model AS vehicle_model,
       ol.quantity, ol.currency, ol.line_total_local, o.fx_rate_units_per_usd, ol.line_total_usd, ol.line_status
FROM order_lines ol JOIN orders o USING (order_id) JOIN parts p USING (part_id) JOIN vehicles v USING (vehicle_id)
WHERE ol.line_status IN ('Shipped', 'Delivered', 'Returned');

-- Most recent exchange rate for every currency
CREATE VIEW v_fx_latest AS
SELECT e.currency_code, c.currency_name, c.symbol, e.rate_date, e.units_per_usd, e.usd_per_unit, c.pegged_to_usd
FROM exchange_rates e JOIN currencies c USING (currency_code)
WHERE e.rate_date = (SELECT MAX(rate_date) FROM exchange_rates);

-- Money owed to us, valued at today's rate, with unrealized FX gain/loss vs. the invoice rate
CREATE VIEW v_receivables AS
SELECT o.order_id, o.customer_id, cu.customer_name, o.ship_to_country, o.billing_currency, o.total_due_local,
       o.fx_rate_units_per_usd AS invoice_rate, f.units_per_usd AS current_rate,
       ROUND(o.total_due_local / o.fx_rate_units_per_usd, 2) AS booked_usd,
       ROUND(o.total_due_local / f.units_per_usd, 2) AS current_usd,
       ROUND(o.total_due_local / f.units_per_usd - o.total_due_local / o.fx_rate_units_per_usd, 2) AS unrealized_fx_usd,
       o.payment_terms, o.payment_status, o.ordered_at_utc, o.shipped_at_utc
FROM orders o JOIN customers cu USING (customer_id) JOIN v_fx_latest f ON f.currency_code = o.billing_currency
WHERE o.payment_status IN ('Open', 'Overdue');

-- Everything currently moving toward a warehouse
CREATE VIEW v_in_transit AS
SELECT s.shipment_id, s.shipment_type, s.po_number, s.transfer_number, s.origin_name, s.origin_city,
       s.origin_country, s.origin_timezone, s.destination_warehouse, s.destination_timezone, s.mode, s.carrier,
       s.port_of_entry, s.ship_date_utc, s.ship_date_origin_local, s.eta_utc, s.eta_destination_local, s.status,
       s.exception_note, s.currency, sl.part_id, p.part_number, p.part_name, p.category, sl.quantity,
       sl.unit_cost_local, sl.unit_cost_usd
FROM shipments s JOIN shipment_lines sl USING (shipment_id) JOIN parts p USING (part_id)
WHERE s.status IN ('In Transit', 'Delayed', 'Customs Hold');

-- Movement log assembled from receipts, sales, returns and count adjustments
CREATE VIEW v_movements AS
SELECT s.delivered_at_utc AS moved_at_utc, s.destination_warehouse AS warehouse_code, sl.part_id,
       'Receipt' AS movement_type, sl.quantity AS qty_change, s.shipment_id AS reference
FROM shipments s JOIN shipment_lines sl USING (shipment_id) WHERE s.status = 'Delivered'
UNION ALL
SELECT o.shipped_at_utc, ol.fulfillment_warehouse, ol.part_id, 'Sale', -ol.quantity, o.order_id
FROM order_lines ol JOIN orders o USING (order_id) WHERE o.shipped_at_utc IS NOT NULL AND ol.line_status IN ('Shipped','Delivered','Returned')
UNION ALL
SELECT o.delivered_at_utc, ol.fulfillment_warehouse, ol.part_id, 'Customer Return', ol.quantity, o.order_id
FROM order_lines ol JOIN orders o USING (order_id) WHERE ol.line_status = 'Returned'
UNION ALL
SELECT counted_at_utc, warehouse_code, part_id, 'Count Adjustment', variance, count_id
FROM cycle_counts WHERE status = 'Adjusted';
""")
con.commit()

# Trim history older than HISTORY_START (open and overdue invoices are always kept)
old_orders = f"SELECT order_id FROM orders WHERE ordered_at_utc < '{HISTORY_START}' AND payment_status NOT IN ('Open','Overdue')"
con.execute(f"DELETE FROM support_cases WHERE order_id IN ({old_orders})")
con.execute(f"DELETE FROM support_cases WHERE order_id IS NULL AND opened_at_utc < '{HISTORY_START}'")
con.execute(f"DELETE FROM order_lines WHERE order_id IN ({old_orders})")
con.execute(f"DELETE FROM orders WHERE order_id IN ({old_orders})")
old_ship = f"SELECT shipment_id FROM shipments WHERE status = 'Delivered' AND delivered_at_utc < '{HISTORY_START}'"
con.execute(f"DELETE FROM shipment_lines WHERE shipment_id IN ({old_ship})")
con.execute(f"DELETE FROM shipments WHERE shipment_id IN ({old_ship})")
con.execute(f"DELETE FROM exchange_rates WHERE rate_date < '{HISTORY_START[:10]}' AND rate_date < (SELECT MIN(fx_rate_date) FROM orders)")
con.commit()

# CSV copies of the final tables
for name in tables:
    cur = con.execute(f'SELECT * FROM "{name}"')
    with open(os.path.join(CSV_DIR, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f); wr.writerow([d[0] for d in cur.description]); wr.writerows(cur)
final_counts = {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for name in tables}
con.execute("VACUUM")
con.close()

with zipfile.ZipFile("car_parts_dataset_csv.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for name in tables:
        z.write(os.path.join(CSV_DIR, f"{name}.csv"), f"car_parts_dataset/{name}.csv")
    if os.path.exists("README.md"): z.write("README.md", "car_parts_dataset/README.md")

print("Stockout part (ATL):", STOCKOUT_PART, P[STOCKOUT_PART]["part_number"], P[STOCKOUT_PART]["part_name"], P[STOCKOUT_PART]["fits_summary"])
for name, n in final_counts.items():
    print(f"{name:18s} {n:>8,}")
print(f"database size: {os.path.getsize(DB_PATH) / 1e6:.1f} MB")
