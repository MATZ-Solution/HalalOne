import os
import sys

# Ensure backend root is in sys.path when running script directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.langsmith_client import get_langsmith_client

# ==============================================================================
# DATASET: Custom Product & Company Detection Eval Dataset
# PURPOSE: Evaluates product and company detection accuracy across user queries:
#          - 4 User-specified target queries
#          - 6 Product-only queries (company_name = None)
#          - 4 Company + Product queries (company specified)
# ==============================================================================

examples = [
    # --------------------------------------------------------------------------
    # 1. USER SPECIFIED QUERIES (4 items)
    # --------------------------------------------------------------------------
    {
        # 1. Knorr Beef Stock Cubes (Company + Product)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Are Beef Stock Cubes halal?",
                }
            ],
            "product_name": "Beef Stock Cubes",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Beef Stock Cubes",
            "expected_company": None,
        },
    },
    {
        # 2. Garden Gourmet Sensational Burger (Product Only)
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
    {
        # 3. Gluten Free Pasta (Product Only)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Gluten Free Pasta halal?",
                }
            ],
            "product_name": "Gluten Free Pasta",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Gluten Free Pasta",
            "expected_company": None,
        },
    },
    {
        # 4. Nutella Muffin (Product Only)
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Can Muslims eat Nutella Muffin?",
                }
            ],
            "product_name": "Nutella Muffin",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Nutella Muffin",
            "expected_company": None,
        },
    },
    # --------------------------------------------------------------------------
    # 2. ADDITIONAL PRODUCT NAME ONLY QUERIES (6 items)
    # --------------------------------------------------------------------------
    {
        # 5. Phantasia gummy
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Phantasia 175g gummy halal?",
                }
            ],
            "product_name": "Phantasia 175g",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Phantasia",
            "expected_company": None,
        },
    },
    {
        # 6. Chamallows Minis
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Chamallows Minis 200g halal or haram?",
                }
            ],
            "product_name": "Chamallows Minis 200g",
            "company_name": None,
        },
        "outputs": {
            "expected_product": "Chamallows Minis",
            "expected_company": None,
        },
    },
    {
        # 7. TWIX Salted Caramel Bar
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
        # 8. SNICKERS Peanut Butter Singles
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
        # 9. Aero Milk Chocolate Bar
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": "Is Aero Milk Chocolate Bar 36g halal?",
                }
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
        # 10. Viennetta Vanilla Ice Cream
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
        "outputs": {
            "expected_product": "Viennetta Vanilla",
            "expected_company": None,
        },
    },
    # --------------------------------------------------------------------------
    # 3. ADDITIONAL COMPANY + PRODUCT QUERIES (4 items)
    # --------------------------------------------------------------------------
    {
        # 11. Goliath Licorice Sticks (Haribo)
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
        # 12. TWIX Caramel Vanilla Ice Cream Bar (Mars)
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
        # 13. KitKat 4 Finger Milk Chocolate Bar (Nestle)
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
        # 14. Almarai 7DAYS Jumbo Hazelnut & Cocoa Croissant
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
]

# LangSmith dataset name
dataset_name = "Halal One Agent: Custom Product Detection Eval Dataset 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluates product detection on user queries with product-only and company+product inputs.",
        )
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset: {dataset_name}")


import asyncio

asyncio.run(generate_dataset())

