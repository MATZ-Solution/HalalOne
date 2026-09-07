from config.langsmith_client import get_langsmith_client

# ==============================================================================
# DATASET: Company + Product Detection & Retrieval
# PURPOSE: Tests whether the agent brings up the specific product and recognizes
#          the parent/child company requested by the user.
# NOTE: Includes a mix of queries with weights/pack sizes and queries without.
# ==============================================================================

examples = [
    # --------------------------------------------------------------------------
    # 1. HARIBO (Gummy / Confectionery)
    # --------------------------------------------------------------------------
    {
        # Query with weight specified
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Goliath Licorice Sticks 125g by Haribo halal?",
                }
            ],
            "product_name": "Goliath Licorice Sticks 125g",
            "company_name": "Haribo GmbH & Co. KG",
        },
        "outputs": {
            "expected_product": "Goliath Licorice Sticks",
            "expected_company": "Haribo",
        },
    },
    {
        # Query without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Can you check if Haribo Goldbears Halal is certified halal?",
                }
            ],
            "product_name": "Goldbears Halal 100g",
            "company_name": "Haribo GmbH & Co. KG",
        },
        "outputs": {"expected_product": "Goldbears", "expected_company": "Haribo"},
    },
    {
        # Query without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Haribo Tropifrutti Halal suitable for Muslims?",
                }
            ],
            "product_name": "Tropifrutti Halal 100g",
            "company_name": "Haribo GmbH & Co. KG",
        },
        "outputs": {"expected_product": "Tropifrutti", "expected_company": "Haribo"},
    },
    # --------------------------------------------------------------------------
    # 2. MARS / TWIX / SNICKERS / SKITTLES / HUBBA BUBBA (Parent + Child Brands)
    # --------------------------------------------------------------------------
    {
        # Parent: Mars, Child: TWIX, with weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Mars TWIX Caramel Vanilla Ice Cream Bar 3 Oz halal?",
                }
            ],
            "product_name": "TWIX Caramel Vanilla Milk Chocolatey Ice Cream Bar, 3 Oz Bar",
            "company_name": "Mars, Incorporated",
        },
        "outputs": {
            "expected_product": "TWIX Caramel Vanilla",
            "expected_company": "Mars",
        },
    },
    {
        # Child Brand: TWIX, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is TWIX Cookies & Creme Sharing Size Candy Bar halal?",
                }
            ],
            "product_name": "TWIX Cookies & Creme Sharing Size Candy Bar, 2.72oz",
            "company_name": "TWIX",
        },
        "outputs": {
            "expected_product": "TWIX Cookies & Creme",
            "expected_company": "TWIX",
        },
    },
    {
        # Child Brand: SNICKERS, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Tell me if SNICKERS Singles Size Chocolate Candy Bar from Mars is halal",
                }
            ],
            "product_name": "SNICKERS Singles Size Chocolate Candy Bars, 1.86 oz",
            "company_name": "Mars, Incorporated",
        },
        "outputs": {
            "expected_product": "SNICKERS Singles",
            "expected_company": "SNICKERS",
        },
    },
    {
        # Child Brand: SKITTLES, with pack size
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SKITTLES Original Gummies Candy 5.8 oz bag halal?",
                }
            ],
            "product_name": "SKITTLES Original Gummies Candy, 5.8 oz Bag",
            "company_name": "Mars, Incorporated",
        },
        "outputs": {
            "expected_product": "SKITTLES Original Gummies",
            "expected_company": "SKITTLES",
        },
    },
    {
        # Child Brand: HUBBA BUBBA, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Hubba Bubba Original Bubble Gum Tape halal?",
                }
            ],
            "product_name": "HUBBA BUBBA Original Bubble Gum Tape, 2 Oz Pack",
            "company_name": "Mars, Incorporated",
        },
        "outputs": {
            "expected_product": "HUBBA BUBBA Original Bubble Gum Tape",
            "expected_company": "HUBBA BUBBA",
        },
    },
    # --------------------------------------------------------------------------
    # 3. FERRERO / NUTELLA / KINDER
    # --------------------------------------------------------------------------
    {
        # Parent: Ferrero, Child: Nutella
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Nutella B-ready by Ferrero halal?"}
            ],
            "product_name": "Nutella B-ready",
            "company_name": "Ferrero International S.A.",
        },
        "outputs": {
            "expected_product": "Nutella B-ready",
            "expected_company": "Ferrero",
        },
    },
    {
        # Child Brand: Kinder, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Can I eat Ferrero Kinder Surprise chocolate?",
                }
            ],
            "product_name": "Kinder Surprise",
            "company_name": "Ferrero International S.A.",
        },
        "outputs": {
            "expected_product": "Kinder Surprise",
            "expected_company": "Kinder",
        },
    },
    {
        # Child Brand: Kinder, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Kinder Bueno White chocolate bar halal?",
                }
            ],
            "product_name": "Kinder Bueno White",
            "company_name": "Ferrero International S.A.",
        },
        "outputs": {
            "expected_product": "Kinder Bueno White",
            "expected_company": "Kinder",
        },
    },
    # --------------------------------------------------------------------------
    # 4. BARILLA (Pasta & Sauces)
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Barilla Rustic Basil Pesto Sauce halal certified?",
                }
            ],
            "product_name": "Barilla Rustic Basil Pesto Sauce",
            "company_name": "Barilla G. e R. F.lli S.p.A.",
        },
        "outputs": {
            "expected_product": "Rustic Basil Pesto Sauce",
            "expected_company": "Barilla",
        },
    },
    {
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Barilla Al Bronzo Organic Pasta halal?"}
            ],
            "product_name": "Al Bronzo® Organic Pasta",
            "company_name": "Barilla G. e R. F.lli S.p.A.",
        },
        "outputs": {"expected_product": "Al Bronzo", "expected_company": "Barilla"},
    },
    # --------------------------------------------------------------------------
    # 5. NESTLÉ / AERO / DAMAK / KITKAT
    # --------------------------------------------------------------------------
    {
        # Child Brand: Aero, with weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nestle Aero Milkybar White Chocolate Sharing Bar 145g halal?",
                }
            ],
            "product_name": "Aero® Milkybar® White Chocolate Sharing Bar (145g)",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {"expected_product": "Aero Milkybar", "expected_company": "Nestlé"},
    },
    {
        # Child Brand: KitKat, without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is KitKat 4 Finger Milk Chocolate Bar by Nestle halal?",
                }
            ],
            "product_name": "KitKat 4 Finger Milk Chocolate Bar 41.5g",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {
            "expected_product": "KitKat 4 Finger",
            "expected_company": "KitKat",
        },
    },
    {
        # Child Brand: Damak, with weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nestle Damak Baklava with Pistachio 60g halal?",
                }
            ],
            "product_name": "Nestle Damak Baklava with Pistachio 60g",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {"expected_product": "Damak Baklava", "expected_company": "Nestle"},
    },
    # --------------------------------------------------------------------------
    # 6. FRONERI / DRUMSTICK
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Froneri Drumstick Banana Split Sundae Cones halal?",
                }
            ],
            "product_name": "Banana Split Sundae Cones Variety Pack",
            "company_name": "Froneri International Limited",
        },
        "outputs": {
            "expected_product": "Banana Split Sundae Cones",
            "expected_company": "Drumstick",
        },
    },
    # --------------------------------------------------------------------------
    # 7. BAHLSEN
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Bahlsen Choco Leibniz Milk biscuit halal?",
                }
            ],
            "product_name": "Choco Leibniz Milk",
            "company_name": "Bahlsen GmbH & Co. KG",
        },
        "outputs": {
            "expected_product": "Choco Leibniz Milk",
            "expected_company": "Bahlsen",
        },
    },
    # --------------------------------------------------------------------------
    # 8. UNILEVER / KNORR / MAGNUM / WALL'S / CORNETTO
    # --------------------------------------------------------------------------
    {
        # Child Brand: Knorr
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Unilever Knorr Chicken Stock Cubes halal?",
                }
            ],
            "product_name": "Chicken Stock Cubes",
            "company_name": "Unilever PLC",
        },
        "outputs": {
            "expected_product": "Chicken Stock Cubes",
            "expected_company": "Knorr",
        },
    },
    {
        # Child Brand: Magnum
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Magnum Double Chocolate ice cream halal?",
                }
            ],
            "product_name": "Double Chocolate",
            "company_name": "The Magnum Ice Cream Company N.V.",
        },
        "outputs": {
            "expected_product": "Double Chocolate",
            "expected_company": "Magnum",
        },
    },
    {
        # Child Brand: Cornetto
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Wall's Cornetto Classico ice cream halal?",
                }
            ],
            "product_name": "Cornetto Classico",
            "company_name": "Unilever PLC",
        },
        "outputs": {
            "expected_product": "Cornetto Classico",
            "expected_company": "Cornetto",
        },
    },
    # --------------------------------------------------------------------------
    # 9. KATJES
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Katjes Halal Box gummy candy halal?"}
            ],
            "product_name": "Halal Box",
            "company_name": "Katjes Fassin GmbH + Co. KG",
        },
        "outputs": {"expected_product": "Halal Box", "expected_company": "Katjes"},
    },
    # --------------------------------------------------------------------------
    # 10. ALMARAI / 7DAYS / ALYOUM
    # --------------------------------------------------------------------------
    {
        # Child Brand: 7DAYS
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Almarai 7DAYS Jumbo Hazelnut & Cocoa Croissant halal?",
                }
            ],
            "product_name": "Jumbo Hazelnut & Cocoa Croissant",
            "company_name": "Almarai Company",
        },
        "outputs": {
            "expected_product": "Jumbo Hazelnut & Cocoa Croissant",
            "expected_company": "7DAYS",
        },
    },
    {
        # Child Brand: Alyoum
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Alyoum Fresh Chicken Breast Fillet by Almarai halal?",
                }
            ],
            "product_name": "Fresh Chicken Breast Fillet",
            "company_name": "Almarai Company",
        },
        "outputs": {
            "expected_product": "Fresh Chicken Breast Fillet",
            "expected_company": "Alyoum",
        },
    },
    # --------------------------------------------------------------------------
    # 11. AMERICANA GROUP / AMERICANA FOODS
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Americana Foods Chicken Strips halal?"}
            ],
            "product_name": "Chicken Strips",
            "company_name": "Americana Group",
        },
        "outputs": {
            "expected_product": "Chicken Strips",
            "expected_company": "Americana",
        },
    },
]

# LangSmith dataset name
dataset_name = "Halal One Agent: Company and Product Detection Dataset 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluates product detection when both company and product are provided.",
        )
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset: {dataset_name}")


import asyncio

asyncio.run(generate_dataset())
