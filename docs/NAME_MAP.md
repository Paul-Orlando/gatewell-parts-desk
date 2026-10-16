# Name map

> Internal reference for maintainers; not shown in the app.

This is the one place outside `data_generator/` where the real names may appear. The map itself lives in `data_generator/name_map.py` and is applied once, at the end of `generate_dataset.py`, so every number stays the same. See `docs/FICTIONAL_NAMES_PLAN.md`.

## Makes

| Real | Fictional |
|---|---|
| Ford | Halvard |
| Chevrolet | Castellan |
| GMC | Castellan Pro |
| Ram | Ironhorn |
| Jeep | Tralon |
| Dodge | Vexley |
| Chrysler | Ambrel |
| Toyota | Kenzai |
| Honda | Ferra Motors |
| Nissan | Sorano |
| Hyundai | Daeyon |
| Kia | Hanvel |
| Subaru | Aokiri |
| Tesla | Voltrane |

## Family codes and OEM brands

| Old code | New code | Part-number prefix |
|---|---|---|
| FORD | HAL | HL- |
| GM | CAS | CS- |
| STLA | IRN | IH- |
| CUM | IRN | IH- |
| TOY | KEN | KZ- |
| HON | FER | FM- |
| NIS | SOR | SR- |
| HK | DAE | DY- |
| SUB | AOK | AK- |
| TES | VOL | VT- |

| Old OEM brand | New OEM brand |
|---|---|
| Ford OEM | Halvard OEM |
| GM OEM | Castellan OEM |
| Mopar OEM | Ironhorn OEM |
| Toyota OEM | Kenzai OEM |
| Honda OEM | Ferra Motors OEM |
| Nissan OEM | Sorano OEM |
| Hyundai/Kia OEM | Daeyon/Hanvel OEM |
| Subaru OEM | Aokiri OEM |
| Tesla OEM | Voltrane OEM |

## Models

| Real make | Real model | Fictional make | Fictional model |
|---|---|---|---|
| Ford | F-150 | Halvard | Torvik |
| Ford | Escape | Halvard | Rovel |
| Ford | Explorer | Halvard | Tramont |
| Ford | Mustang | Halvard | Vantor |
| Ford | Ranger | Halvard | Grison |
| Ford | Edge | Halvard | Wendal |
| Ford | Fusion | Halvard | Lumeo |
| Ford | Focus | Halvard | Lirra |
| Ford | Expedition | Halvard | Marshfield |
| Chevrolet | Silverado 1500 | Castellan | Bracken 1500 |
| Chevrolet | Equinox | Castellan | Corvin |
| Chevrolet | Malibu | Castellan | Merivale |
| Chevrolet | Tahoe | Castellan | Granmoor |
| Chevrolet | Traverse | Castellan | Westvale |
| Chevrolet | Colorado | Castellan | Durrow |
| Chevrolet | Cruze | Castellan | Pellin |
| GMC | Sierra 1500 | Castellan Pro | Granthor 1500 |
| GMC | Terrain | Castellan Pro | Tarrow |
| GMC | Acadia | Castellan Pro | Brennick |
| GMC | Yukon | Castellan Pro | Ostmark |
| Ram | 1500 | Ironhorn | 1500 |
| Ram | 2500 | Ironhorn | 2500 |
| Jeep | Grand Cherokee | Tralon | Grand Sabrel |
| Jeep | Wrangler | Tralon | Rockhart |
| Jeep | Cherokee | Tralon | Sabrel |
| Jeep | Compass | Tralon | Wayfen |
| Dodge | Charger | Vexley | Razorn |
| Dodge | Grand Caravan | Vexley | Grand Hearthway |
| Chrysler | Pacifica | Ambrel | Kinsley |
| Toyota | Camry | Kenzai | Aravel |
| Toyota | Corolla | Kenzai | Mirelo |
| Toyota | RAV4 | Kenzai | Tavio |
| Toyota | Tacoma | Kenzai | Kodan |
| Toyota | Highlander | Kenzai | Sennridge |
| Toyota | Tundra | Kenzai | Torrack |
| Toyota | 4Runner | Kenzai | Cragmont |
| Toyota | Prius | Kenzai | Ecliva |
| Honda | Civic | Ferra Motors | Nivo |
| Honda | Accord | Ferra Motors | Valena |
| Honda | CR-V | Ferra Motors | Torisa |
| Honda | Pilot | Ferra Motors | Montrel |
| Honda | Odyssey | Ferra Motors | Nestara |
| Honda | HR-V | Ferra Motors | Zenna |
| Nissan | Altima | Sorano | Celvane |
| Nissan | Rogue | Sorano | Tavrin |
| Nissan | Sentra | Sorano | Ressa |
| Nissan | Frontier | Sorano | Gravik |
| Nissan | Pathfinder | Sorano | Wildmere |
| Hyundai | Elantra | Daeyon | Sonnel |
| Hyundai | Tucson | Daeyon | Varenta |
| Hyundai | Santa Fe | Daeyon | Delmora |
| Hyundai | Sonata | Daeyon | Aurelle |
| Kia | Sorento | Hanvel | Morvale |
| Kia | Sportage | Hanvel | Juvo |
| Kia | Forte | Hanvel | Pelto |
| Kia | Telluride | Hanvel | Highwold |
| Subaru | Outback | Aokiri | Fernway |
| Subaru | Forester | Aokiri | Timbrel |
| Subaru | Crosstrek | Aokiri | Kestran |
| Tesla | Model 3 | Voltrane | Ampra |
| Tesla | Model Y | Voltrane | Joulen |

## Engines

| Old description | New description |
|---|---|
| 2.7L V6 EcoBoost | 2.7L V6 Twin-Turbo |
| 3.5L V6 EcoBoost | 3.5L V6 Twin-Turbo |
| 3.0L V6 EcoBoost | 3.0L V6 Twin-Turbo |
| 1.5L I3 EcoBoost | 1.5L I3 Turbo |
| 2.0L I4 EcoBoost | 2.0L I4 Turbo |
| 2.3L I4 EcoBoost | 2.3L I4 Turbo |
| 3.6L V6 Pentastar | 3.6L V6 |
| 5.7L V8 HEMI | 5.7L V8 |
| 6.4L V8 HEMI | 6.4L V8 |

Engine codes take the new family prefix: FORD-2.7TT becomes HAL-2.7TT, CUM-6.7D becomes IRN-6.7D.

## Carriers and services

| Real | Fictional |
|---|---|
| UPS | Parcelora |
| FedEx | Velocair |
| USPS | Postara |
| DHL | Globexa Express |

| Old code | New code | New name |
|---|---|---|
| UPS_GND | PCL_GND | Parcelora Ground |
| UPS_2DA | PCL_2D | Parcelora 2-Day |
| UPS_NDA | PCL_ND | Parcelora Next Day |
| FDX_GND | VLC_GND | Velocair Ground |
| FDX_2D | VLC_2D | Velocair 2Day |
| FDX_SO | VLC_ON | Velocair Overnight |
| USPS_GA | PST_GND | Postara Ground Saver |
| USPS_PM | PST_PRI | Postara Priority |
| USPS_PME | PST_PON | Postara Priority Overnight |
| UPS_STD_CAMX | PCL_STD_CAMX | Parcelora Standard (Canada & Mexico) |
| FDX_IG | VLC_IG | Velocair International Ground (Canada) |
| UPS_WWX | PCL_WWX | Parcelora Worldwide Expedited |
| UPS_WWS | PCL_WWE | Parcelora Worldwide Express |
| FDX_IE | VLC_IE | Velocair International Economy |
| FDX_IP | VLC_IX | Velocair International Express |
| DHL_EXW | GBX_EXW | Globexa Express Worldwide |
| USPS_PMI | PST_INTL | Postara Priority International |

Tracking numbers keep their random body with a new prefix: UPS `1Z…` → `PC…`; USPS `9400…` → `PS00…`; FedEx (digits) → `VC…`; DHL (digits) → `GX…`.

## OEM part numbers cited in tests and docs

All 4,465 OEM part numbers were renumbered in `part_id` order within each family prefix. These are the ones the tests, eval set and docs referred to before the change:

| Old | New |
|---|---|
| 82737772 | CS-100215 |
| 02938-T5C77 | DY-100025 |
| 01223-E8S11 | DY-100512 |
| 20031-M0X44 | DY-100549 |
| 00093-N0V80 | DY-100550 |
| 38080-TGH-Y22 | FM-100003 |
| 50712-XAV-D58 | FM-100192 |
| 08294-PAK-H95 | FM-100194 |
| BN9Z-6149-E | HL-100008 |
| FF8Z-5955-Y | HL-100182 |
| XW5Z-5643-V | HL-100183 |
| DB7Z-9495-M | HL-100184 |
| FW9Z-4457-X | HL-100189 |
| KV8Z-9402-Y | HL-100214 |
| FM8Z-2687-P | HL-100396 |
| 68253600AW | IH-100009 |
| 68439188AR | IH-100149 |
| 68882706AA | IH-100185 |
| 68735551KU | IH-100188 |
| 17102-0G289 | KZ-100190 |
| 97667-5F001 | KZ-100214 |
| 44506-3K857 | KZ-100619 |
