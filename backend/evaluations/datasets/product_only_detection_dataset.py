from config.langsmith_client import get_langsmith_client

# ==============================================================================
# DATASET: Product-Only Detection & Retrieval
# PURPOSE: Tests whether the agent brings up the specific product when no
#          company is specified in the user prompt.
# NOTE: Includes a mix of queries with weights/pack sizes and queries without.
# ==============================================================================

examples = [
    # --------------------------------------------------------------------------
    # 1. CONFECTIONERY & GUMMIES
    # --------------------------------------------------------------------------
    {
        # With weight
        "inputs": {
            "messages": [{"role": "user", "content": "Is Phantasia 175g gummy halal?"}],
            "product_name": "Phantasia 175g",
            "company_name": None,
        },
        "outputs": {"expected_product": "Phantasia", "expected_company": None},
    },
    {
        # With weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Chamallows Minis 200g halal?"}
            ],
            "product_name": "Chamallows Minis 200g",
            "company_name": None,
        },
        "outputs": {"expected_product": "Chamallows Minis", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Check halal status of TWIX Salted Caramel Bar",
                }
            ],
            "product_name": "TWIX Salted Caramel Bar",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "TWIX Salted Caramel Bar",
            "expected_company": None,
        },
    },
    {
        # Without weight
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
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is SKITTLES Sour Wild Berry single pack halal?",
                }
            ],
            "product_name": "SKITTLES Sour Wild Berry Candy Single Pack, 1.8 oz",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "SKITTLES Sour Wild Berry",
            "expected_company": None,
        },
    },
    {
        # Without pack size
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is HUBBA BUBBA Max Strawberry Watermelon Bubble Gum halal?",
                }
            ],
            "product_name": "HUBBA BUBBA Max Strawberry Watermelon Bubble Gum, 5 Piece Pack",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "HUBBA BUBBA Max Strawberry Watermelon",
            "expected_company": None,
        },
    },
    # --------------------------------------------------------------------------
    # 2. BAKERY, SPREADS & CHOCOLATES
    # --------------------------------------------------------------------------
    {
        # Without weight
        "inputs": {
            "messages": [{"role": "user", "content": "Is Nutella Biscuits halal?"}],
            "product_name": "Nutella Biscuits",
            "company_name": None,
        },
        "outputs": {"expected_product": "Nutella Biscuits", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Can Muslims eat Nutella Muffin?"}
            ],
            "product_name": "Nutella Muffin",
            "company_name": None,
        },
        "outputs": {"expected_product": "Nutella Muffin", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [{"role": "user", "content": "Is Kinder Joy chocolate halal?"}],
            "product_name": "Kinder Joy",
            "company_name": None,
        },
        "outputs": {"expected_product": "Kinder Joy", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Kinder Happy Hippo Hazelnut halal?"}
            ],
            "product_name": "Kinder Happy Hippo Hazelnut",
            "company_name": None,
        },
        "outputs": {"expected_product": "Kinder Happy Hippo", "expected_company": None},
    },
    {
        # With weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Aero Milk Chocolate Bar 36g halal?"}
            ],
            "product_name": "Aero Milk Chocolate Bar (36g)",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Aero Milk Chocolate Bar",
            "expected_company": None,
        },
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is KitKat Chunky Peanut Chocolate Bar halal?",
                }
            ],
            "product_name": "KitKat Chunky Peanut Chocolate Bar 42g",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "KitKat Chunky Peanut",
            "expected_company": None,
        },
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Waffeletten Milk biscuit halal?"}
            ],
            "product_name": "Waffeletten Milk",
            "company_name": None,
        },
        "outputs": {"expected_product": "Waffeletten Milk", "expected_company": None},
    },
    # --------------------------------------------------------------------------
    # 3. PASTA & PLANT-BASED FOODS
    # --------------------------------------------------------------------------
    {
        # Without weight
        "inputs": {
            "messages": [{"role": "user", "content": "Is Gluten Free Pasta halal?"}],
            "product_name": "Gluten Free Pasta",
            "company_name": None,
        },
        "outputs": {"expected_product": "Gluten Free Pasta", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Garden Gourmet Sensational Burger vegetarian and halal?",
                }
            ],
            "product_name": "Garden Gourmet Sensational Burger",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Garden Gourmet Sensational Burger",
            "expected_company": None,
        },
    },
    # --------------------------------------------------------------------------
    # 4. ICE CREAMS & DESSERTS
    # --------------------------------------------------------------------------
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Crushed It Sundae Cones halal?"}
            ],
            "product_name": "Crushed It! Sundae Cones",
            "company_name": None,
        },
        "outputs": {"expected_product": "Crushed It", "expected_company": None},
    },
    {
        # With volume
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Viennetta Vanilla 650ml ice cream halal?",
                }
            ],
            "product_name": "Viennetta Vanilla 650ml",
            "company_name": None,
        },
        "outputs": {"expected_product": "Viennetta Vanilla", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Ben & Jerry's Cherry Garcia ice cream halal?",
                }
            ],
            "product_name": "Cherry Garcia®",
            "company_name": None,
        },
        "outputs": {"expected_product": "Cherry Garcia", "expected_company": None},
    },
    # --------------------------------------------------------------------------
    # 5. SOUPS & SEASONINGS
    # --------------------------------------------------------------------------
    {
        # Without weight
        "inputs": {
            "messages": [{"role": "user", "content": "Are Beef Stock Cubes halal?"}],
            "product_name": "Beef Stock Cubes",
            "company_name": None,
        },
        "outputs": {"expected_product": "Beef Stock Cubes", "expected_company": None},
    },
    # --------------------------------------------------------------------------
    # 6. VEGAN CANDIES & CROISSANTS
    # --------------------------------------------------------------------------
    {
        # With weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Katjes Al Paka Cola Sour 210g halal?"}
            ],
            "product_name": "Al Paka Cola Sour 210g",
            "company_name": None,
        },
        "outputs": {"expected_product": "Al Paka Cola Sour", "expected_company": None},
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Double Fill Vanilla & Chocolate Croissant halal?",
                }
            ],
            "product_name": "Double Fill Vanilla & Chocolate Croissant",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Double Fill Vanilla & Chocolate Croissant",
            "expected_company": None,
        },
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Farm's Select Super Pomegranate juice halal?",
                }
            ],
            "product_name": "Super Pomegranate",
            "company_name": None,
        },
        "outputs": {"expected_product": "Super Pomegranate", "expected_company": None},
    },
    # --------------------------------------------------------------------------
    # 7. MEAT & POULTRY
    # --------------------------------------------------------------------------
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Heroz Happy Chicken Nuggets halal?"}
            ],
            "product_name": "Heroz Happy Chicken Nuggets",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Heroz Happy Chicken Nuggets",
            "expected_company": None,
        },
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {"role": "user", "content": "Is Zingz Broasted Chicken Wings halal?"}
            ],
            "product_name": "Zingz Broasted Chicken Wings",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Zingz Broasted Chicken Wings",
            "expected_company": None,
        },
    },
    {
        # Without weight
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Air Fryer Zingz Chicken Strips Hot & Crunchy halal?",
                }
            ],
            "product_name": "Air Fryer Zingz Chicken Strips (Hot & Crunchy)",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Zingz Chicken Strips",
            "expected_company": None,
        },
    },
]

# LangSmith dataset name
dataset_name = "Halal One Agent: Product-Only Detection Dataset 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluates product detection when only the product name is provided.",
        )
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset: {dataset_name}")


import asyncio

asyncio.run(generate_dataset())
