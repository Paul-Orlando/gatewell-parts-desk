"""Real-to-fictional name map, applied once at the end of generate_dataset.py.

Generation keeps its internal names and keys so the random draws (and every
number) stay the same. Right before the tables are written, every name below
is swapped for its fictional equivalent. See docs/FICTIONAL_NAMES_PLAN.md.

This file and docs/NAME_MAP.md are the only places old names may appear.
"""

# Vehicle makes.
MAKE = {
    "Ford": "Halvard",
    "Chevrolet": "Castellan",
    "GMC": "Castellan Pro",
    "Ram": "Ironhorn",
    "Jeep": "Tralon",
    "Dodge": "Vexley",
    "Chrysler": "Ambrel",
    "Toyota": "Kenzai",
    "Honda": "Ferra Motors",
    "Nissan": "Sorano",
    "Hyundai": "Daeyon",
    "Kia": "Hanvel",
    "Subaru": "Aokiri",
    "Tesla": "Voltrane",
}

# Internal family codes (engine codes, OEM brand, suppliers). CUM is folded into IRN.
FAMILY = {
    "FORD": "HAL", "GM": "CAS", "STLA": "IRN", "CUM": "IRN", "TOY": "KEN",
    "HON": "FER", "NIS": "SOR", "HK": "DAE", "SUB": "AOK", "TES": "VOL",
}

# OEM brand label per family.
OEM_BRAND = {
    "Ford OEM": "Halvard OEM",
    "GM OEM": "Castellan OEM",
    "Mopar OEM": "Ironhorn OEM",
    "Toyota OEM": "Kenzai OEM",
    "Honda OEM": "Ferra Motors OEM",
    "Nissan OEM": "Sorano OEM",
    "Hyundai/Kia OEM": "Daeyon/Hanvel OEM",
    "Subaru OEM": "Aokiri OEM",
    "Tesla OEM": "Voltrane OEM",
}

# Two-letter prefix for neutral OEM part numbers (e.g. IH-100123), per family.
PART_PREFIX = {
    "HAL": "HL", "CAS": "CS", "IRN": "IH", "KEN": "KZ", "FER": "FM",
    "SOR": "SR", "DAE": "DY", "AOK": "AK", "VOL": "VT",
}
PART_NUMBER_START = 100001  # numbered in part_id order within each prefix
FICTIONAL_OEM_BRANDS = set(OEM_BRAND.values())

# Family name shown in engine fit text ("Halvard 5.0L V8 engine"), per new family code.
FAMILY_LABEL = {
    "HAL": "Halvard", "CAS": "Castellan", "IRN": "Ironhorn", "KEN": "Kenzai", "FER": "Ferra Motors",
    "SOR": "Sorano", "DAE": "Daeyon/Hanvel", "AOK": "Aokiri", "VOL": "Voltrane",
}
assert {f"{v} OEM" for v in FAMILY_LABEL.values()} == FICTIONAL_OEM_BRANDS

# Models, keyed by (real make, real model). Body type, years, engines and
# popularity are unchanged; names hint at the vehicle type.
MODEL = {
    # Halvard
    ("Ford", "F-150"): "Torvik",              # full-size pickup
    ("Ford", "Escape"): "Rovel",              # compact SUV
    ("Ford", "Explorer"): "Tramont",          # midsize SUV
    ("Ford", "Mustang"): "Vantor",            # sports car
    ("Ford", "Ranger"): "Grison",             # midsize pickup
    ("Ford", "Edge"): "Wendal",               # midsize SUV
    ("Ford", "Fusion"): "Lumeo",              # midsize car
    ("Ford", "Focus"): "Lirra",               # compact car
    ("Ford", "Expedition"): "Marshfield",     # full-size SUV
    # Castellan
    ("Chevrolet", "Silverado 1500"): "Bracken 1500",
    ("Chevrolet", "Equinox"): "Corvin",
    ("Chevrolet", "Malibu"): "Merivale",
    ("Chevrolet", "Tahoe"): "Granmoor",
    ("Chevrolet", "Traverse"): "Westvale",
    ("Chevrolet", "Colorado"): "Durrow",
    ("Chevrolet", "Cruze"): "Pellin",
    # Castellan Pro
    ("GMC", "Sierra 1500"): "Granthor 1500",
    ("GMC", "Terrain"): "Tarrow",
    ("GMC", "Acadia"): "Brennick",
    ("GMC", "Yukon"): "Ostmark",
    # Ironhorn (plain heavy-duty numbers are fine)
    ("Ram", "1500"): "1500",
    ("Ram", "2500"): "2500",
    # Tralon
    ("Jeep", "Grand Cherokee"): "Grand Sabrel",
    ("Jeep", "Wrangler"): "Rockhart",         # off-road SUV
    ("Jeep", "Cherokee"): "Sabrel",
    ("Jeep", "Compass"): "Wayfen",
    # Vexley
    ("Dodge", "Charger"): "Razorn",           # muscle car
    ("Dodge", "Grand Caravan"): "Grand Hearthway",  # minivan
    # Ambrel
    ("Chrysler", "Pacifica"): "Kinsley",      # minivan
    # Kenzai
    ("Toyota", "Camry"): "Aravel",
    ("Toyota", "Corolla"): "Mirelo",
    ("Toyota", "RAV4"): "Tavio",
    ("Toyota", "Tacoma"): "Kodan",
    ("Toyota", "Highlander"): "Sennridge",
    ("Toyota", "Tundra"): "Torrack",
    ("Toyota", "4Runner"): "Cragmont",
    ("Toyota", "Prius"): "Ecliva",            # hybrid car
    # Ferra Motors
    ("Honda", "Civic"): "Nivo",
    ("Honda", "Accord"): "Valena",
    ("Honda", "CR-V"): "Torisa",
    ("Honda", "Pilot"): "Montrel",
    ("Honda", "Odyssey"): "Nestara",          # minivan
    ("Honda", "HR-V"): "Zenna",
    # Sorano
    ("Nissan", "Altima"): "Celvane",
    ("Nissan", "Rogue"): "Tavrin",
    ("Nissan", "Sentra"): "Ressa",
    ("Nissan", "Frontier"): "Gravik",
    ("Nissan", "Pathfinder"): "Wildmere",
    # Daeyon
    ("Hyundai", "Elantra"): "Sonnel",
    ("Hyundai", "Tucson"): "Varenta",
    ("Hyundai", "Santa Fe"): "Delmora",
    ("Hyundai", "Sonata"): "Aurelle",
    # Hanvel
    ("Kia", "Sorento"): "Morvale",
    ("Kia", "Sportage"): "Juvo",
    ("Kia", "Forte"): "Pelto",
    ("Kia", "Telluride"): "Highwold",
    # Aokiri
    ("Subaru", "Outback"): "Fernway",         # wagon
    ("Subaru", "Forester"): "Timbrel",
    ("Subaru", "Crosstrek"): "Kestran",
    # Voltrane (EV)
    ("Tesla", "Model 3"): "Ampra",
    ("Tesla", "Model Y"): "Joulen",
}

# Engine descriptions: trade names dropped, generic descriptions kept.
ENGINE_NAME = {
    "2.7L V6 EcoBoost": "2.7L V6 Twin-Turbo",
    "3.5L V6 EcoBoost": "3.5L V6 Twin-Turbo",
    "3.0L V6 EcoBoost": "3.0L V6 Twin-Turbo",
    "1.5L I3 EcoBoost": "1.5L I3 Turbo",
    "2.0L I4 EcoBoost": "2.0L I4 Turbo",
    "2.3L I4 EcoBoost": "2.3L I4 Turbo",
    "3.6L V6 Pentastar": "3.6L V6",
    "5.7L V8 HEMI": "5.7L V8",
    "6.4L V8 HEMI": "6.4L V8",
}

# Parcel carriers. Freight forwarders, ocean/truck carriers and Gatewell
# Delivery are already fictional and stay.
CARRIER = {
    "UPS": "Parcelora",
    "FedEx": "Velocair",
    "USPS": "Postara",
    "DHL": "Globexa Express",
}

# Service code -> (new code, new name). Rules, limits, rates and transit are unchanged.
SERVICE = {
    "UPS_GND": ("PCL_GND", "Parcelora Ground"),
    "UPS_2DA": ("PCL_2D", "Parcelora 2-Day"),
    "UPS_NDA": ("PCL_ND", "Parcelora Next Day"),
    "FDX_GND": ("VLC_GND", "Velocair Ground"),
    "FDX_2D": ("VLC_2D", "Velocair 2Day"),
    "FDX_SO": ("VLC_ON", "Velocair Overnight"),
    "USPS_GA": ("PST_GND", "Postara Ground Saver"),
    "USPS_PM": ("PST_PRI", "Postara Priority"),
    "USPS_PME": ("PST_PON", "Postara Priority Overnight"),
    "UPS_STD_CAMX": ("PCL_STD_CAMX", "Parcelora Standard (Canada & Mexico)"),
    "FDX_IG": ("VLC_IG", "Velocair International Ground (Canada)"),
    "UPS_WWX": ("PCL_WWX", "Parcelora Worldwide Expedited"),
    "UPS_WWS": ("PCL_WWE", "Parcelora Worldwide Express"),
    "FDX_IE": ("VLC_IE", "Velocair International Economy"),
    "FDX_IP": ("VLC_IX", "Velocair International Express"),
    "DHL_EXW": ("GBX_EXW", "Globexa Express Worldwide"),
    "USPS_PMI": ("PST_INTL", "Postara Priority International"),
}

# Parcel tracking numbers: real carriers' formats get a neutral prefix; the random body is kept.
TRACKING_PREFIX = {
    "UPS": ("1Z", "PC"),      # 1Z + 16 characters  -> PC + same 16
    "USPS": ("9400", "PS00"),  # 9400 + 18 digits   -> PS00 + same 18
    "FedEx": ("", "VC"),      # 12 digits           -> VC + same 12
    "DHL": ("", "GX"),        # 10 digits           -> GX + same 10
}

# Whole-word, case-sensitive denylist for tests/test_no_real_brands.py: real makes,
# carriers and engine trade names. Models are checked structurally instead, because
# several are ordinary words or places that stay real (Colorado, Tacoma, Frontier).
DENYLIST = sorted(
    set(MAKE) | set(CARRIER)
    | {"Mopar", "EcoBoost", "Pentastar", "HEMI", "Cummins", "Ground Advantage",
       "Priority Mail", "Worldwide Saver", "2nd Day Air", "Next Day Air"}
)

# Fictional sets, for the guard test.
FICTIONAL_MAKES = set(MAKE.values())
FICTIONAL_MODELS = set(MODEL.values())
FICTIONAL_CARRIERS = set(CARRIER.values())


# ----------------------------------------------------------------------------- translation
import re


def _slug(s):
    """Same rule as generate_dataset.slug()."""
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def _word(old):
    return re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")


def engine_code(code):
    """FORD-2.7TT -> HAL-2.7TT, CUM-6.7D -> IRN-6.7D."""
    fam, rest = code.split("-", 1)
    return f"{FAMILY[fam]}-{rest}"


def translate(tables):
    """Replace every real name in the generated tables, in place. Numbers, dates and
    row order are untouched. Returns the old -> new OEM part-number map."""
    T = tables
    model = lambda make, m: MODEL[(make, m)]

    # Platforms and vehicles (platform IDs rebuilt with the generator's slug rule).
    plat = {}
    for p in T["platforms"]:
        new_make, new_model = MAKE[p["make"]], model(p["make"], p["model"])
        new_id = f"PLT-{_slug(new_make)[:4]}-{_slug(new_model)}-G{p['generation']}"
        plat[p["platform_id"]] = (new_id, f"{new_make} {new_model} {p['year_from']}-{p['year_to']}",
                                  f"{p['make']} {p['model']} {p['year_from']}-{p['year_to']}")
        p.update(platform_id=new_id, make=new_make, model=new_model)
        if "family" in p: p["family"] = FAMILY[p["family"]]
    assert len({v[0] for v in plat.values()}) == len(plat), "platform ID collision"

    engines = {}
    for v in T["vehicles"]:
        engines[v["engine_code"]] = v["engine"]
        v.update(make=MAKE[v["make"]], model=model(v["make"], v["model"]), engine_code=engine_code(v["engine_code"]),
                 engine=ENGINE_NAME.get(v["engine"], v["engine"]), platform_id=plat[v["platform_id"]][0])

    # OEM part numbers: neutral, numbered in part_id order within each family prefix.
    pn, counters = {}, {}
    for p in sorted(T["parts"], key=lambda p: p["part_id"]):
        if p["brand_type"] == "OEM":
            pre = PART_PREFIX[FAMILY[p["oem_family"]]]
            counters[pre] = counters.get(pre, PART_NUMBER_START - 1) + 1
            assert p["part_number"] not in pn
            pn[p["part_number"]] = f"{pre}-{counters[pre]}"

    # Engine fit text: family + engine, no internal code. Each must read differently.
    engine_text = {code: f"{FAMILY_LABEL[FAMILY[code.split('-')[0]]]} {ENGINE_NAME.get(name, name)} engine"
                   for code, name in engines.items()}
    assert len(set(engine_text.values())) == len(engine_text), "two engines would read alike"

    for p in T["parts"]:
        if p["fits_scope"] == "platform":
            new_key, new_sum, old_sum = plat[p["fits_key"]]
        else:
            name = engines[p["fits_key"]]
            new_key = engine_code(p["fits_key"])
            old_sum = f"{name} engine ({p['fits_key']})"
            new_sum = engine_text[p["fits_key"]]
        assert p["fits_summary"] == old_sum, (p["part_id"], p["fits_summary"])
        p.update(part_number=pn.get(p["part_number"], p["part_number"]), brand=OEM_BRAND.get(p["brand"], p["brand"]),
                 oem_family=FAMILY[p["oem_family"]], fits_key=new_key, fits_summary=new_sum)

    for i in T["part_interchange"]:
        i.update(part_number=pn.get(i["part_number"], i["part_number"]), brand=OEM_BRAND.get(i["brand"], i["brand"]),
                 interchanges_with_part_number=pn.get(i["interchanges_with_part_number"], i["interchanges_with_part_number"]))

    # Dealers: only the make inside the name changes ("Oakmont Ford of Pennsylvania").
    for c in T["customers"]:
        if c["franchise_make"]:
            name, n = _word(c["franchise_make"]).subn(MAKE[c["franchise_make"]], c["customer_name"])
            assert n == 1, c["customer_name"]
            c.update(customer_name=name, franchise_make=MAKE[c["franchise_make"]])

    # Carriers and services.
    def carrier_text(s):
        s = _word("DHL Express").sub(CARRIER["DHL"], s)
        for old, new in CARRIER.items():
            s = _word(old).sub(new, s)
        return s

    for f in T["faq"]:
        for k in ("question", "answer", "keywords"):
            if f.get(k): f[k] = carrier_text(f[k])
    for s in T["shipping_services"]:
        if s["service_code"] in SERVICE:
            s.update(service_code=SERVICE[s["service_code"]][0], service_name=SERVICE[s["service_code"]][1],
                     carrier=CARRIER[s["carrier"]])
    for r in T["shipping_rates"]:
        r["service_code"] = SERVICE.get(r["service_code"], (r["service_code"],))[0]
    for s in T["shipping_surcharges"]:
        s["carrier"] = CARRIER.get(s["carrier"], s["carrier"])
    for o in T["orders"]:
        car = o["carrier"]
        if car in CARRIER:
            code = o["carrier_service_code"]
            trk = o["tracking_number"]
            if trk:
                old_pre, new_pre = TRACKING_PREFIX[car]
                assert trk.startswith(old_pre), trk
                trk = new_pre + trk[len(old_pre):]
            o.update(carrier=CARRIER[car], carrier_service_code=SERVICE[code][0], carrier_service=SERVICE[code][1],
                     tracking_number=trk)
    for s in T["shipments"]:
        s["carrier"] = CARRIER.get(s["carrier"], s["carrier"])

    _self_check(T, pn)
    return pn


def _self_check(tables, pn):
    """Fail loudly if any real name, old family code or old OEM number is left in any text value."""
    deny = re.compile(r"(?<![\w-])(" + "|".join(re.escape(w) for w in sorted(DENYLIST, key=len, reverse=True)) + r")(?![\w-])")
    old_codes = re.compile(r"\b(" + "|".join(k for k in FAMILY) + r")-\d")
    old_svc = re.compile(r"\b(UPS|FDX|USPS|DHL)_[A-Z0-9]")
    old_plat = re.compile(r"PLT-(" + "|".join({_slug(m)[:4] for m in MAKE}) + r")-")
    old_pn = set(pn)
    for name, rows in tables.items():
        for row in rows:
            for k, v in row.items():
                if isinstance(v, str):
                    for rx in (deny, old_codes, old_svc, old_plat):
                        assert not rx.search(v), f"{name}.{k}: {v!r}"
                    assert v not in old_pn, f"{name}.{k}: old part number {v!r}"
    for name in ("parts",):
        for row in tables[name]:
            assert row["oem_family"] in FAMILY.values(), row["oem_family"]
