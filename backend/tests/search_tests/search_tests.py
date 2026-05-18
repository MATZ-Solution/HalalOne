"""
Comprehensive search test suite for the Halalify Typesense collection.
Tests norm_name, companies, cert_bodies, fda_numbers, barcodes, cert_numbers,
halal_status, category_l1, typical_uses, and health_info — with both correct
spellings and deliberate typos/misspellings to evaluate fuzzy-match accuracy.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from collection.search.search_collection import search_collection

COLLECTION = "halal_products"

_results = []   # (title, hit_count, expected_hits)


def run(title, query, query_by, expect_hits=True, note=""):
    tag = "[TYPO]" if "[TYPO]" in title else "      "
    sep = "-" * 70
    print(f"\n{sep}")
    print(f"{tag} {title}")
    print(f"  query='{query}'  query_by='{query_by}'")
    if note:
        print(f"  expect: {note}")
    print(sep)
    count = search_collection(query=query, query_by=query_by, collection_name=COLLECTION)
    status = "PASS" if (count > 0) == expect_hits else "FAIL"
    _results.append((title, count, expect_hits, status))
    print(f"  -> hits={count}  [{status}]")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1 — norm_name  (correct spelling)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 1 — norm_name: CORRECT SPELLING")
print("=" * 70)

run("turmeric",
    "turmeric", "norm_name",
    note="e100 curcumin/turmeric entries")

run("riboflavin",
    "riboflavin", "norm_name",
    note="e101 riboflavin (lactoflavin, vitamin b2)")

run("tartrazine",
    "tartrazine", "norm_name",
    note="e102 tartrazine (fd&c yellow 5)")

run("sunset yellow",
    "sunset yellow", "norm_name",
    note="e110 sunset yellow fcf")

run("cochineal",
    "cochineal", "norm_name",
    note="e120 cochineal / carminic acid")

run("butterscotch",
    "butterscotch", "norm_name",
    note="butterscotch syrup (halal_000659)")

run("collagen peptide",
    "collagen peptide", "norm_name",
    note="collagen peptide and vitamin c capsule (halal_000880)")

run("osmolite",
    "osmolite", "norm_name",
    note="multiple osmolite products (halal_000118, halal_000120...)")

run("cream cheese",
    "cream cheese", "norm_name",
    note="cream cheese entries (halal_000967, halal_000968)")

run("dried mangoes",
    "dried mangoes", "norm_name",
    note="dried mangoes (halal_001066)")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2 — norm_name  (typos / misspellings)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 2 — norm_name: TYPOS & MISSPELLINGS")
print("=" * 70)

run("[TYPO] riboflabin  (v->b)",
    "riboflabin", "norm_name",
    note="should still find e101 riboflavin via 1-char fuzzy")

run("[TYPO] tartrazne  (missing i)",
    "tartrazne", "norm_name",
    note="should still find e102 tartrazine")

run("[TYPO] cohineal  (missing c)",
    "cohineal", "norm_name",
    note="should find e120 cochineal")

run("[TYPO] sunst yellow  (missing e in sunset)",
    "sunst yellow", "norm_name",
    note="should find e110 sunset yellow fcf")

run("[TYPO] buttrscotch  (missing e)",
    "buttrscotch", "norm_name",
    note="should find butterscotch syrup")

run("[TYPO] curcumin  (data itself has 'curcurmin')",
    "curcumin", "norm_name",
    note="correct spelling vs typo in data — fuzzy should bridge the gap")

run("[TYPO] vitmin b2  (missing a in vitamin)",
    "vitmin b2", "norm_name",
    note="should find vitamin b2 / riboflavin entries")

run("[TYPO] collagen peptid  (missing final e)",
    "collagen peptid", "norm_name",
    note="should find collagen peptide product")

run("[TYPO] osmolit  (missing final e)",
    "osmolit", "norm_name",
    note="should find osmolite entries")

run("[TYPO] dryed mangos  (wrong spelling of both words)",
    "dryed mangos", "norm_name",
    note="should find dried mangoes")

run("[TYPO] turemric  (scrambled — 3+ edits)",
    "turemric", "norm_name", expect_hits=False,
    note="unlikely — too many character edits for default num_typos=2")

run("[TYPO] crem chese  (2 typos)",
    "crem chese", "norm_name",
    note="2-char errors across 2 words — borderline fuzzy territory")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3 — companies  (correct spelling)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 3 — companies: CORRECT SPELLING")
print("=" * 70)

run("abbott",
    "abbott", "companies",
    note="many products: base powders, osmolite, jevity, etc.")

run("tillamook",
    "tillamook", "companies",
    note="tillamook county creamery association")

run("camino",
    "camino", "companies",
    note="camino branded products")

run("cool whip",
    "cool whip", "companies",
    note="cool whip product")

run("dollarama",
    "dollarama", "companies",
    note="dollarama branded products")

run("dare candy",
    "dare candy", "companies",
    note="dare candy co products")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4 — companies  (typos)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 4 — companies: TYPOS & MISSPELLINGS")
print("=" * 70)

run("[TYPO] abbottt  (extra t)",
    "abbottt", "companies",
    note="should still find abbott via 1-char fuzzy")

run("[TYPO] tillamoook  (extra o)",
    "tillamoook", "companies",
    note="should find tillamook")

run("[TYPO] cammino  (extra m)",
    "cammino", "companies",
    note="should find camino")

run("[TYPO] cool wip  (missing h)",
    "cool wip", "companies",
    note="should find cool whip")

run("[TYPO] dolarama  (missing l)",
    "dolarama", "companies",
    note="should find dollarama")

run("[TYPO] dare cady  (missing n)",
    "dare cady", "companies",
    note="should find dare candy co")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5 — cert_bodies  (correct spelling)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 5 — cert_bodies: CORRECT SPELLING")
print("=" * 70)

run("HFCI India",
    "HFCI India", "cert_bodies",
    note="largest cert body — should return many hits")

run("SANHA South Africa",
    "SANHA South Africa", "cert_bodies",
    note="common cert body — many results expected")

run("IFANCA",
    "IFANCA", "cert_bodies",
    note="US-based halal certifier")

run("HMA",
    "HMA", "cert_bodies",
    note="Halal Monitoring Authority")

run("HFSAA",
    "HFSAA", "cert_bodies",
    note="Halal Food Standards Alliance of America")

run("HQC Croatia",
    "HQC Croatia", "cert_bodies",
    note="Croatian halal certifier")

run("THIDAA Taiwan",
    "THIDAA Taiwan", "cert_bodies",
    note="Taiwan halal certifier")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6 — cert_bodies  (typos)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 6 — cert_bodies: TYPOS & MISSPELLINGS")
print("=" * 70)

run("[TYPO] HFCI Indai  (transposition in India)",
    "HFCI Indai", "cert_bodies",
    note="should find HFCI India")

run("[TYPO] SANHA Soth Africa  (missing u)",
    "SANHA Soth Africa", "cert_bodies",
    note="should find SANHA South Africa")

run("[TYPO] IFACA  (missing N)",
    "IFACA", "cert_bodies",
    note="should find IFANCA")

run("[TYPO] SANAH South Africa  (S↔A transposition)",
    "SANAH South Africa", "cert_bodies",
    note="should find SANHA South Africa")

run("[TYPO] THIDAA Tiwan  (missing a in Taiwan)",
    "THIDAA Tiwan", "cert_bodies",
    note="should find THIDAA Taiwan")

run("[TYPO] HFCE Indai  (wrong acronym + transposition)",
    "HFCE Indai", "cert_bodies",
    note="two errors — fuzzy may or may not bridge this")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7 — fda_numbers  (correct)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 7 — fda_numbers: CORRECT")
print("=" * 70)

run("butterscotch FDA number",
    "1010335050326", "fda_numbers",
    note="halal_000659 butterscotch syrup")

run("collagen peptide FDA number",
    "74-2-05557-5-0010", "fda_numbers",
    note="halal_000880 collagen peptide")

run("double x FDA number",
    "4320145560005", "fda_numbers",
    note="halal_001044 double x")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8 — fda_numbers  (typos — numbers are exact identifiers)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 8 — fda_numbers: TYPOS (expect no match)")
print("=" * 70)

run("[TYPO] 1010335050325  (last digit off by 1)",
    "1010335050325", "fda_numbers", expect_hits=False,
    note="numeric IDs rarely match with 1 digit wrong")

run("[TYPO] 74-2-05557-5-001  (truncated)",
    "74-2-05557-5-001", "fda_numbers", expect_hits=False,
    note="partial number — Typesense won't partial-match numbers")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9 — barcodes  (correct)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 9 — barcodes: CORRECT")
print("=" * 70)

run("coconut milk barcode",
    "8850649200079", "barcodes",
    note="halal_000873 coconut milk drink")

run("double x barcode",
    "8859077800080", "barcodes",
    note="halal_001044 double x")

run("ginger puree barcode",
    "8852646272004", "barcodes",
    note="halal_001526 ginger puree")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 10 — barcodes  (typos)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 10 — barcodes: TYPOS (expect no match)")
print("=" * 70)

run("[TYPO] 8850649200070  (last digit off)",
    "8850649200070", "barcodes", expect_hits=False,
    note="barcode 1 digit wrong — no match expected")

run("[TYPO] 885064920007  (truncated by 1 digit)",
    "885064920007", "barcodes", expect_hits=False,
    note="truncated barcode — no match expected")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 11 — cert_numbers  (correct)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 11 — cert_numbers: CORRECT")
print("=" * 70)

run("banana chips cert number",
    "91A1290880358", "cert_numbers",
    note="halal_000522 banana chips")

run("bone formula cert number",
    "90P8610010965", "cert_numbers",
    note="halal_000642 bone formula")

run("butter scotch cert number",
    "97B6670510363", "cert_numbers",
    note="halal_000657 butter scotch 248gm")

run("children's chewable cert number",
    "99I42710800664", "cert_numbers",
    note="halal_000795 children's chewable tablets")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 12 — cert_numbers  (typos)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 12 — cert_numbers: TYPOS (expect no match)")
print("=" * 70)

run("[TYPO] 91A1290880359  (last digit off)",
    "91A1290880359", "cert_numbers", expect_hits=False,
    note="cert numbers are exact alphanumeric identifiers")

run("[TYPO] 90P8610010966  (last digit off)",
    "90P8610010966", "cert_numbers", expect_hits=False,
    note="cert numbers are exact alphanumeric identifiers")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 13 — halal_status
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 13 — halal_status")
print("=" * 70)

run("Halal",
    "Halal", "halal_status",
    note="large number of halal products")

run("Haraam",
    "Haraam", "halal_status",
    note="haraam (forbidden) products")

run("Mushbooh",
    "Mushbooh", "halal_status",
    note="mushbooh (questionable/doubtful) products")

run("[TYPO] Haram  (missing a — common alternate spelling)",
    "Haram", "halal_status",
    note="should fuzzy-match to Haraam")

run("[TYPO] Musbooh  (missing h)",
    "Musbooh", "halal_status",
    note="should fuzzy-match to Mushbooh")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 14 — category_l1
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 14 — category_l1")
print("=" * 70)

run("Additive",
    "Additive", "category_l1",
    note="e-number food additives")

run("Food",
    "Food", "category_l1",
    note="general food products")

run("Cosmetic",
    "Cosmetic", "category_l1",
    note="cosmetic products")

run("Pharma",
    "Pharma", "category_l1",
    note="pharmaceutical products")

run("Beverage",
    "Beverage", "category_l1",
    note="beverage products")

run("[TYPO] Additiv  (missing e)",
    "Additiv", "category_l1",
    note="should fuzzy-match to Additive")

run("[TYPO] Cosmetc  (missing i)",
    "Cosmetc", "category_l1",
    note="should fuzzy-match to Cosmetic")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 15 — typical_uses
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 15 — typical_uses")
print("=" * 70)

run("curry powder",
    "curry powder", "typical_uses",
    note="products used in curry powder")

run("confectionery",
    "confectionery", "typical_uses",
    note="confectionery products — many e-number entries")

run("peanut butter",
    "peanut butter", "typical_uses",
    note="products used in peanut butter")

run("soft drinks",
    "soft drinks", "typical_uses",
    note="products used in soft drinks")

run("breakfast cereals",
    "breakfast cereals", "typical_uses",
    note="products used in breakfast cereals")

run("[TYPO] confectionary  (common misspelling)",
    "confectionary", "typical_uses",
    note="should fuzzy-match to confectionery")

run("[TYPO] peanut butr  (missing te)",
    "peanut butr", "typical_uses",
    note="borderline — 2-char edit on 'butter'")

run("[TYPO] bred  (missing a in bread)",
    "bred", "typical_uses", expect_hits=False,
    note="too short + 1 missing char — fuzzy unlikely")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 16 — health_info
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 16 — health_info")
print("=" * 70)

run("carcinogenic",
    "carcinogenic", "health_info",
    note="products with carcinogenic warnings")

run("hyperactivity",
    "hyperactivity", "health_info",
    note="products linked to hyperactivity")

run("asthma",
    "asthma", "health_info",
    note="products with asthma warnings")

run("anaphylaxis",
    "anaphylaxis", "health_info",
    note="severe allergic reaction warnings")

run("[TYPO] hyperactivty  (missing i)",
    "hyperactivty", "health_info",
    note="should fuzzy-match hyperactivity")

run("[TYPO] carsinogenic  (c->s swap)",
    "carsinogenic", "health_info",
    note="should fuzzy-match carcinogenic")

run("[TYPO] asthama  (extra a)",
    "asthama", "health_info",
    note="should fuzzy-match asthma")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 17 — Multi-field searches
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 17 — MULTI-FIELD searches")
print("=" * 70)

run("norm_name + companies: 'butterscotch'",
    "butterscotch", "norm_name,companies",
    note="should return butterscotch syrup via norm_name match")

run("norm_name + cert_bodies: 'IFANCA'",
    "IFANCA", "norm_name,cert_bodies",
    note="should return products certified by IFANCA")

run("norm_name + typical_uses: 'chocolate'",
    "chocolate", "norm_name,typical_uses",
    note="broad match across product names and uses")

run("norm_name + companies: 'abbott osmolite'",
    "abbott osmolite", "norm_name,companies",
    note="cross-field: name matches norm_name, company matches companies")

run("[TYPO] norm_name + companies: 'abbottt osmolit'",
    "abbottt osmolit", "norm_name,companies",
    note="two typos across two fields — tests combined fuzzy tolerance")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

passed   = [r for r in _results if r[3] == "PASS"]
failed   = [r for r in _results if r[3] == "FAIL"]
typo_res = [r for r in _results if "[TYPO]" in r[0]]
typo_ok  = [r for r in typo_res if r[3] == "PASS"]

print(f"\nTotal tests  : {len(_results)}")
print(f"PASS         : {len(passed)}")
print(f"FAIL         : {len(failed)}")
print(f"\nTypo/misspelling tests : {len(typo_res)}")
print(f"Typo tests PASS        : {len(typo_ok)}")
typo_rate = (len(typo_ok) / len(typo_res) * 100) if typo_res else 0
print(f"Fuzzy-match accuracy   : {typo_rate:.0f}%")

if failed:
    print("\nFailed tests:")
    for t, count, expected, _ in failed:
        print(f"  - {t}  (hits={count}, expected_hits={expected})")

print("\n" + "=" * 70)
print("""
ACCURACY NOTES
--------------
Typesense uses BM25 ranking with configurable num_typos (default=2 per token).

- norm_name:    Good fuzzy coverage for 1-2 char edits per word. Longer words
                tolerate more typos. Very short words (<4 chars) get 0 tolerance.
                NOTE: 'curcumin' vs 'curcurmin' tests whether Typesense bridges
                a typo that exists IN the indexed data itself.

- companies:    Works well because company names are usually long enough to
                absorb 1-2 char edits (e.g. 'abbottt', 'tillamoook').

- cert_bodies:  Short acronyms like 'HMA', 'HFSAA' have low fuzzy tolerance
                due to their length. Longer forms like 'HFCI India' handle
                transpositions better.

- fda_numbers / barcodes / cert_numbers:
                Numeric/alphanumeric IDs behave poorly under typos — a single
                digit change produces a completely different valid-looking ID,
                so Typesense (correctly) returns no match. Always search these
                with exact values.

- halal_status: Only 3 values (Halal, Haraam, Mushbooh). 'Haram' (1 char short)
                may or may not fuzzy-match depending on word length threshold.

- typical_uses / health_info:
                Long descriptive text — excellent fuzzy-match territory. Even
                'confectionary' (extra a) reliably finds 'confectionery'.
""")
