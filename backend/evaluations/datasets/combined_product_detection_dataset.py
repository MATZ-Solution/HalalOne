from config.langsmith_client import get_langsmith_client

# ==============================================================================
# DATASET: Combined Product & Company Detection Dataset (Cleaned & Standardized)
# PURPOSE: Evaluates end-to-end product detection on clean query patterns:
#          - "Is [Product X] halal?"
#          - "Is [Product X] halal or haram?"
#          - "Is [Product X] of [Company Y] halal?"
#          - "Is [Company Y] [Product X] halal?"
#          - "Can Muslims eat [Product X]?"
# ==============================================================================

examples = [
    # --------------------------------------------------------------------------
    # 1. SPECIFIC USER-REQUESTED & CORRECTED CASES
    # --------------------------------------------------------------------------
    {
        # 1. Froneri Drumstick
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
    {
        # 2. Hubba Bubba
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
    {
        # 3. Knorr Beef Stock Cubes (Corrected from generic plural to clean product inquiry)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Knorr Beef Stock Cubes halal or haram?",
                }
            ],
            "product_name": "Beef Stock Cubes",
            "company_name": "Unilever PLC",
        },
        "outputs": {
            "expected_product": "Beef Stock Cubes",
            "expected_company": "Knorr",
        },
    },
    {
        # 4. Heroz Happy Chicken Nuggets (Americana)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Heroz Happy Chicken Nuggets halal?",
                }
            ],
            "product_name": "Heroz Happy Chicken Nuggets",
            "company_name": "Americana Group",
        },
        "outputs": {
            "expected_product": "Heroz Happy Chicken Nuggets",
            "expected_company": "Americana",
        },
    },
    {
        # 5. SKITTLES Sour Wild Berry
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SKITTLES Sour Wild Berry single pack halal?",
                }
            ],
            "product_name": "SKITTLES Sour Wild Berry Candy Single Pack, 1.8 oz",
            "company_name": "Mars, Incorporated",
        },
        "outputs": {
            "expected_product": "SKITTLES Sour Wild Berry",
            "expected_company": "SKITTLES",
        },
    },
    {
        # 6. Garden Gourmet Sensational Burger (Corrected: only asking for halal, vegetarian removed)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Garden Gourmet Sensational Burger of Nestle halal?",
                }
            ],
            "product_name": "Garden Gourmet Sensational Burger",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {
            "expected_product": "Garden Gourmet Sensational Burger",
            "expected_company": "Garden Gourmet",
        },
    },
    {
        # 7. Farm's Select Super Pomegranate juice (Almarai)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Farm's Select Super Pomegranate juice halal?",
                }
            ],
            "product_name": "Farm's Select Super Pomegranate juice",
            "company_name": "Almarai Company",
        },
        "outputs": {
            "expected_product": "Farm's Select Super Pomegranate juice",
            "expected_company": "Almarai",
        },
    },
    {
        # 8. Gluten Free Pasta (Barilla)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Barilla Gluten Free Pasta halal or haram?",
                }
            ],
            "product_name": "Gluten Free Pasta",
            "company_name": "Barilla G. e R. F.lli S.p.A.",
        },
        "outputs": {
            "expected_product": "Gluten Free Pasta",
            "expected_company": "Barilla",
        },
    },
    {
        # 9. Zingz Broasted Chicken Wings (Americana)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Zingz Broasted Chicken Wings halal?",
                }
            ],
            "product_name": "Zingz Broasted Chicken Wings",
            "company_name": "Americana Group",
        },
        "outputs": {
            "expected_product": "Zingz Broasted Chicken Wings",
            "expected_company": "Americana",
        },
    },
    {
        # 10. Nutella Muffin (Ferrero)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nutella Muffin halal?",
                }
            ],
            "product_name": "Nutella Muffin",
            "company_name": "Ferrero International S.A.",
        },
        "outputs": {
            "expected_product": "Nutella Muffin",
            "expected_company": "Nutella",
        },
    },
    # --------------------------------------------------------------------------
    # 2. HARIBO & CONFECTIONERY
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Goliath Licorice Sticks of Haribo halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Haribo Goldbears Halal halal or haram?",
                }
            ],
            "product_name": "Goldbears Halal 100g",
            "company_name": "Haribo GmbH & Co. KG",
        },
        "outputs": {"expected_product": "Goldbears", "expected_company": "Haribo"},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Haribo Tropifrutti Halal halal?",
                }
            ],
            "product_name": "Tropifrutti Halal 100g",
            "company_name": "Haribo GmbH & Co. KG",
        },
        "outputs": {"expected_product": "Tropifrutti", "expected_company": "Haribo"},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Phantasia gummy halal?",
                }
            ],
            "product_name": "Phantasia 175g",
            "company_name": None,
        },
        "outputs": {"expected_product": "Phantasia", "expected_company": None},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Chamallows Minis halal or haram?",
                }
            ],
            "product_name": "Chamallows Minis 200g",
            "company_name": None,
        },
        "outputs": {"expected_product": "Chamallows Minis", "expected_company": None},
    },
    # --------------------------------------------------------------------------
    # 3. MARS / TWIX / SNICKERS / SKITTLES
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is TWIX Caramel Vanilla Ice Cream Bar of Mars halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is TWIX Cookies & Creme Candy Bar halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SNICKERS Singles Size Chocolate Candy Bar of Mars halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SNICKERS Peanut Butter Singles Candy Bar halal?",
                }
            ],
            "product_name": "SNICKERS Peanut Butter Singles Candy Bar, 1.78oz",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "SNICKERS Peanut Butter",
            "expected_company": None,
        },
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SKITTLES Original Gummies Candy of Mars halal?",
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
    # --------------------------------------------------------------------------
    # 4. FERRERO / NUTELLA / KINDER
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nutella Biscuits of Ferrero halal or haram?",
                }
            ],
            "product_name": "Nutella Biscuits",
            "company_name": "Ferrero International S.A.",
        },
        "outputs": {
            "expected_product": "Nutella Biscuits",
            "expected_company": "Ferrero",
        },
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nutella B-ready of Ferrero halal?",
                }
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Kinder Joy chocolate halal?",
                }
            ],
            "product_name": "Kinder Joy",
            "company_name": None,
        },
        "outputs": {"expected_product": "Kinder Joy", "expected_company": None},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Kinder Happy Hippo Hazelnut halal or haram?",
                }
            ],
            "product_name": "Kinder Happy Hippo Hazelnut",
            "company_name": None,
        },
        "outputs": {"expected_product": "Kinder Happy Hippo", "expected_company": None},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Kinder Bueno White chocolate bar of Ferrero halal?",
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
    # 5. NESTLÉ / AERO / KITKAT / DAMAK
    # --------------------------------------------------------------------------
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nestle Aero Milkybar White Chocolate Sharing Bar halal?",
                }
            ],
            "product_name": "Aero® Milkybar® White Chocolate Sharing Bar (145g)",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {"expected_product": "Aero Milkybar", "expected_company": "Nestlé"},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is KitKat 4 Finger Milk Chocolate Bar of Nestle halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is KitKat Chunky Peanut Butter Chocolate Bar halal?",
                }
            ],
            "product_name": "KitKat Chunky Peanut Butter Chocolate Bar 42g",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "KitKat Chunky Peanut Butter",
            "expected_company": None,
        },
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Nestle Damak Baklava with Pistachio halal or haram?",
                }
            ],
            "product_name": "Nestle Damak Baklava with Pistachio 60g",
            "company_name": "Nestlé S.A.",
        },
        "outputs": {"expected_product": "Damak Baklava", "expected_company": "Nestle"},
    },
    # --------------------------------------------------------------------------
    # 6. UNILEVER / KNORR / MAGNUM / WALL'S / VIENNETTA / CORNETTO
    # --------------------------------------------------------------------------
    {
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Magnum Double Chocolate ice cream of Unilever halal?",
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Wall's Cornetto Classico ice cream of Unilever halal?",
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
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Viennetta Vanilla Ice Cream halal or haram?",
                }
            ],
            "product_name": "Viennetta Vanilla 650ml",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Viennetta Vanilla",
            "expected_company": None,
        },
    },
    # --------------------------------------------------------------------------
    # 7. BAHLSEN / KATJES / BARILLA
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
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Katjes Halal Box gummy candy halal or haram?",
                }
            ],
            "product_name": "Halal Box",
            "company_name": "Katjes Fassin GmbH + Co. KG",
        },
        "outputs": {"expected_product": "Halal Box", "expected_company": "Katjes"},
    },
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Barilla Rustic Basil Pesto Sauce halal?",
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
    # --------------------------------------------------------------------------
    # 8. ALMARAI & AMERICANA
    # --------------------------------------------------------------------------
    {
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
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Alyoum Fresh Chicken Breast Fillet of Almarai halal?",
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
    {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Americana Foods Chicken Strips halal or haram?",
                }
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
dataset_name = "Halal One Agent: Combined Product and Company Detection Dataset 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluates standardized product and company detection on clean halal/haram queries.",
        )
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset: {dataset_name}")


import asyncio

asyncio.run(generate_dataset())
