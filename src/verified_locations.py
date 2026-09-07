"""
Verified coordinates for all 24 Bedashing branches, read off each business's
Google Maps place page (the !3d/!4d pair in the canonical URL).

The initial geocoding resolved the postal address to a neighbourhood centroid.
Cannibalisation rests on the distance between sites over a catchment of roughly
2 km, so a 1 km error changes the overlap completely and a 34 km error changes
which emirate is being analysed:

    Al Taif Mall      25.41474,56.23137 -> 25.12026,56.32535   34.4 km
    Khalifa City A    24.42013,54.57495 -> 24.43998,54.59891    2.8 km
    Khaleej Al Arabi  24.45138,54.33797 -> 24.45887,54.35378    1.7 km
    Mirdif 35         25.22184,55.42315 -> 25.23230,55.43296    1.4 km

Six recommendations changed on recomputation. Mirdif 35 is the clearest case:
its 49% cannibalisation against Tips & Toes City Centre Mirdif was a geocoding
artifact, and with the real positions the overlap drops to 19%.

The 40 Tips & Toes and 10 Jazz sites remain geocoded. They are competitive
context, not the object of a recommendation, and verifying them is the next
step.

Collected 2026-09-07.
"""

# shop_id -> (lat, lon)
VERIFIED = {
    "bd_al_ain":                     (24.2266835, 55.6599794),
    "bd_al_barsha":                  (25.1131451, 55.2156092),
    "bd_al_dhafra":                  (23.6280524, 53.7141144),
    "bd_al_falah":                   (24.4428939, 54.7396974),
    "bd_al_jada":                    (25.3192096, 55.4799114),
    "bd_al_maqta":                   (24.4130516, 54.4929556),
    "bd_al_taif_mall":               (25.1202606, 56.3253503),
    "bd_baniyas":                    (24.2973631, 54.6332474),
    "bd_city_walk":                  (25.2019849, 55.2638147),
    "bd_delma":                      (24.4679540, 54.3847796),
    "bd_jumeirah_park":              (25.0391540, 55.1659736),
    "bd_khaleej_al_arabi":           (24.4588702, 54.3537762),
    "bd_khalifa_city_a":             (24.4399805, 54.5989056),
    "bd_ministries_complex":         (24.4321470, 54.4647516),
    "bd_mirdif_35":                  (25.2322986, 55.4329599),
    "bd_mohammed_bin_zayed_city":    (24.3667831, 54.5403404),
    "bd_nad_al_sheba":               (25.1595625, 55.3696875),
    "bd_noya_plaza":                 (24.4995625, 54.6254375),
    "bd_ras_al_khaimah":             (25.7515410, 55.9198717),
    "bd_shahama":                    (24.5243742, 54.6718965),
    "bd_shakhbout_city":             (24.3481854, 54.6238561),
    "bd_west_yas":                   (24.4934924, 54.5868369),
    "bd_zawaya_walk":                (25.3306234, 55.4294728),
    "bd_zayed_international_airport":(24.4527718, 54.6411421),
}

PENDING = []   # no Bedashing branch left to verify
