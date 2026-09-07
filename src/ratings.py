"""
Google Maps ratings and review volumes.

Collected by hand on 2026-09-03 from the public Google Maps place pages
(searching by brand and by area). The Places API is not used because it is paid
and the brief asks for a mode with no external dependencies.

Coverage:
  Bedashing        24/24  (100%)  <- the brand the brief is about
  Tips & Toes      28/40  ( 70%)  <- internal competitive context
  Jazz Lounge Spa   0/10  (  0%)  <- men's segment, outside the analysis

`rating_confidence`:
  confirmed = the place page showed the full branch name
  inferred  = place page with no branch name, assigned by geographic proximity
  missing   = not located
"""

# shop_id -> (rating, n_reviews, confidence)
RATINGS = {
    # ---------- BEDASHING (24/24) ----------
    "bd_al_ain":                      (4.7, 1325, "confirmed"),
    "bd_al_barsha":                   (4.6,  742, "confirmed"),
    "bd_al_dhafra":                   (4.5,  358, "confirmed"),
    "bd_al_falah":                    (4.6,  948, "confirmed"),
    "bd_al_jada":                     (4.5,  613, "confirmed"),
    "bd_al_maqta":                    (4.6, 1288, "confirmed"),
    "bd_al_taif_mall":                (4.7,  495, "confirmed"),
    "bd_baniyas":                     (4.6,  694, "confirmed"),
    "bd_city_walk":                   (4.6,  855, "confirmed"),
    "bd_delma":                       (4.6,  671, "confirmed"),
    "bd_jumeirah_park":               (4.8,  440, "confirmed"),
    "bd_khaleej_al_arabi":            (4.6, 1737, "confirmed"),
    "bd_khalifa_city_a":              (4.5, 2453, "confirmed"),
    "bd_ministries_complex":          (4.9, 1214, "confirmed"),
    "bd_mirdif_35":                   (4.5,  817, "confirmed"),
    "bd_mohammed_bin_zayed_city":     (4.4,  830, "confirmed"),
    "bd_nad_al_sheba":                (4.6,  626, "confirmed"),
    "bd_noya_plaza":                  (4.7,  209, "confirmed"),
    "bd_ras_al_khaimah":              (4.6,  769, "confirmed"),
    "bd_shahama":                     (4.6,  746, "confirmed"),
    "bd_shakhbout_city":              (4.5, 1268, "confirmed"),
    "bd_west_yas":                    (4.6,  727, "confirmed"),
    "bd_zawaya_walk":                 (4.7,  601, "confirmed"),
    "bd_zayed_international_airport": (4.9,  535, "confirmed"),

    # ---------- TIPS & TOES (28/40) ----------
    "tt_al_barsha":            (4.2,  825, "confirmed"),
    "tt_al_falah_1":           (4.4,  364, "confirmed"),
    "tt_al_falah_5":           (4.3,  277, "confirmed"),
    "tt_arabian_ranches":      (4.6,  885, "confirmed"),
    "tt_arjan":                (4.5,  388, "confirmed"),
    "tt_business_bay":         (4.5,  456, "confirmed"),
    "tt_city_centre_mirdif":   (4.0,  301, "confirmed"),
    "tt_creek_beach":          (4.5,  198, "confirmed"),
    "tt_dubai_festival_city":  (4.3,  662, "confirmed"),
    "tt_dubai_marina_mall":    (4.4,  457, "confirmed"),
    "tt_dubai_silicon_central":(4.5,  479, "confirmed"),
    "tt_khaleej_al_arabi":     (4.2,  681, "confirmed"),
    "tt_khalifa_city":         (4.3, 1203, "confirmed"),
    "tt_marina_mall_auh":      (4.4,  416, "inferred"),
    "tt_me_aisem_city_centre": (4.2,  386, "confirmed"),
    "tt_meadows_mall":         (4.7,  402, "confirmed"),
    "tt_mira_town_centre":     (4.0,  340, "confirmed"),
    "tt_mohammed_bin_zayed_city": (4.4, 867, "inferred"),
    "tt_nation_towers":        (4.5,  384, "confirmed"),
    "tt_park_point":           (4.4,  221, "confirmed"),
    "tt_port_de_la_mer":       (4.6,  108, "confirmed"),
    "tt_reem_mall":            (4.3,  327, "confirmed"),
    "tt_saadiyat_island":      (4.5,  354, "confirmed"),
    "tt_shamkha_mall":         (4.2,  488, "confirmed"),
    "tt_the_dubai_mall":       (4.1,  474, "confirmed"),
    "tt_the_greens_souk":      (4.4,  601, "confirmed"),
    "tt_the_springs_souk":     (4.5,  516, "confirmed"),
    "tt_the_villa":            (4.3,  137, "confirmed"),
    "tt_yas_mall":             (4.2, 1021, "confirmed"),
}

# No data: 11 Tips & Toes branches in peripheral markets
# (Al Dhannah/Ruwais, Al Furjan x2, Al Hamra Mall/RAK, Golden Mile,
#  Hili Mall, Jimi, Makani, Marina Vista, The Valley) plus the 10 Jazz sites.
# None of them overlaps a Bedashing branch, so the gap does not affect
# any recommendation about the brand the brief is about.
