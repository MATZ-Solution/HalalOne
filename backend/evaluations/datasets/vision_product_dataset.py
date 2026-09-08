import os
import sys

# Ensure backend root is in sys.path when running script directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.langsmith_client import get_langsmith_client

# ==============================================================================
# DATASET: Vision Product Image Dataset (15 Products)
# PURPOSE: Evaluates multi-modal / vision product information extraction on 15
#          product packaging images saved under evaluations/data/images.
# SCHEMA:
#   - norm_name: str
#   - companies: List[str]
#   - cert_bodies: List[str]
#   - marketplace: List[str]
#   - category_l1: str
#   - category_l2: str
#   - halal_status: str
#   - sold_in: List[str]
#   - cert_numbers: List[str]
#   - fda_numbers: List[str]
#   - barcodes: List[str]
# ==============================================================================

examples = [
    {
        # 1. 7days Strawberry Cake Bar
        "inputs": {
            "image_filename": "7days_strawberry_cake_bar.jpg",
            "image_path": "evaluations/data/images/7days_strawberry_cake_bar.jpg",
        },
        "outputs": {
            "norm_name": "7days cake bar with strawberry filling",
            "companies": ["7DAYS", "Almarai", "Chipita"],
            "cert_bodies": [],
            "marketplace": ["Supermarkets", "Retail"],
            "category_l1": "Food",
            "category_l2": "Bakery & Cakes",
            "halal_status": "Halal",
            "sold_in": ["Romania", "European Union", "Balkans"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 2. Aero Choco Caramel
        "inputs": {
            "image_filename": "aero_choco_caramel.jpg",
            "image_path": "evaluations/data/images/aero_choco_caramel.jpg",
        },
        "outputs": {
            "norm_name": "nestle aero choco caramel chocolate bar",
            "companies": ["Nestlé", "Aero"],
            "cert_bodies": [],
            "marketplace": ["Retail", "Supermarkets"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal Suitable",
            "sold_in": ["United Kingdom", "Ireland"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 3. Alyoum Chicken Drumsticks
        "inputs": {
            "image_filename": "alyoum_chicken_drumsticks.jpg",
            "image_path": "evaluations/data/images/alyoum_chicken_drumsticks.jpg",
        },
        "outputs": {
            "norm_name": "alyoum premium fresh chicken drumsticks 450g",
            "companies": ["Alyoum", "Almarai", "Hail Agricultural Development Company"],
            "cert_bodies": ["Halal Certified (Saudi Arabia)", "SFDA"],
            "marketplace": ["Supermarkets", "Grocery Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Meat & Poultry",
            "halal_status": "Halal",
            "sold_in": ["Saudi Arabia", "GCC"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["6281007057899"],
        },
    },
    {
        # 4. Bahlsen Waffeletten Dark
        "inputs": {
            "image_filename": "bahlsen_waffeletten_dark.jpg",
            "image_path": "evaluations/data/images/bahlsen_waffeletten_dark.jpg",
        },
        "outputs": {
            "norm_name": "bahlsen waffeletten dark chocolate wafer rolls 100g",
            "companies": ["Bahlsen"],
            "cert_bodies": ["UTZ Certified"],
            "marketplace": ["Retail", "Supermarkets", "Export"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal Suitable",
            "sold_in": ["Germany", "European Union", "Portugal", "Poland", "Saudi Arabia", "Algeria", "Libya", "Tunisia"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["4017100210105"],
        },
    },
    {
        # 5. Ben & Jerry's Peanut Butter Chocolate Chip Cookie Dough
        "inputs": {
            "image_filename": "ben&jerry_peanut_butter_chocolate_chip_cookie_dough.jpg",
            "image_path": "evaluations/data/images/ben&jerry_peanut_butter_chocolate_chip_cookie_dough.jpg",
        },
        "outputs": {
            "norm_name": "ben & jerry's peanut butter chocolate chip cookie dough chunks",
            "companies": ["Ben & Jerry's", "Unilever"],
            "cert_bodies": ["KOF-K Kosher", "Fairtrade"],
            "marketplace": ["Supermarkets", "Retail", "Grocery Stores"],
            "category_l1": "Food",
            "category_l2": "Frozen Desserts & Snacks",
            "halal_status": "Halal Suitable (Kosher Dairy)",
            "sold_in": ["United States", "North America"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["076840002313"],
        },
    },
    {
        # 6. Drumstick Triple Chocolate Sundae Cone
        "inputs": {
            "image_filename": "drumstick_tripl_chocolate_sundae_cone.jpg",
            "image_path": "evaluations/data/images/drumstick_tripl_chocolate_sundae_cone.jpg",
        },
        "outputs": {
            "norm_name": "nestle drumstick king size triple chocolate sundae cone",
            "companies": ["Nestlé", "Drumstick", "Froneri"],
            "cert_bodies": ["Orthodox Union Kosher (OU-D)"],
            "marketplace": ["Convenience Stores", "Supermarkets", "Retail"],
            "category_l1": "Food",
            "category_l2": "Frozen Desserts & Ice Cream",
            "halal_status": "Halal Suitable (Kosher Dairy)",
            "sold_in": ["United States"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["072554218903"],
        },
    },
    {
        # 7. Haribo Jelly Beans
        "inputs": {
            "image_filename": "haribo_jelly_beans.jpg",
            "image_path": "evaluations/data/images/haribo_jelly_beans.jpg",
        },
        "outputs": {
            "norm_name": "haribo jelly beans 8 flavors share size",
            "companies": ["Haribo"],
            "cert_bodies": ["European Vegetarian Union (V-Label)"],
            "marketplace": ["Supermarkets", "Candy Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal (Vegetarian, Gelatin-Free)",
            "sold_in": ["United Kingdom", "European Union", "Germany"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 8. Hot Pockets Jalapeno Popper
        "inputs": {
            "image_filename": "hot_pockets_jalapeno_popper.jpg",
            "image_path": "evaluations/data/images/hot_pockets_jalapeno_popper.jpg",
        },
        "outputs": {
            "norm_name": "hot pockets snack breaks spicy jalapeno popper pretzel crust",
            "companies": ["Hot Pockets", "Nestlé"],
            "cert_bodies": [],
            "marketplace": ["Supermarkets", "Grocery Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Frozen Foods & Snacks",
            "halal_status": "Mushbooh",
            "sold_in": ["United States"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 9. Katjes Alpaka Cola
        "inputs": {
            "image_filename": "katjes_alpaka_cola.jpg",
            "image_path": "evaluations/data/images/katjes_alpaka_cola.jpg",
        },
        "outputs": {
            "norm_name": "katjes al paka cola fruchtgummi 200g",
            "companies": ["Katjes", "Katjes Fassin GmbH + Co. KG"],
            "cert_bodies": ["Vegan Certified"],
            "marketplace": ["Supermarkets", "Retail", "German Grocery Stores"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal (100% Vegan, No Animal Gelatin)",
            "sold_in": ["Germany", "European Union"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["4037400346069"],
        },
    },
    {
        # 10. Kinder Happy Hippo
        "inputs": {
            "image_filename": "kinder_happy_hippo.jpg",
            "image_path": "evaluations/data/images/kinder_happy_hippo.jpg",
        },
        "outputs": {
            "norm_name": "kinder happy hippo hazelnut biscuits",
            "companies": ["Kinder", "Ferrero"],
            "cert_bodies": [],
            "marketplace": ["Supermarkets", "Retail", "Duty Free"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal Suitable",
            "sold_in": ["Germany", "United Kingdom", "European Union", "Worldwide"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 11. KitKat Chunky Bar
        "inputs": {
            "image_filename": "kitkat_chunky_bar.jpg",
            "image_path": "evaluations/data/images/kitkat_chunky_bar.jpg",
        },
        "outputs": {
            "norm_name": "nestle kitkat chunky crunchy double choc chocolate bar",
            "companies": ["Nestlé", "KitKat"],
            "cert_bodies": [],
            "marketplace": ["Supermarkets", "Convenience Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal Suitable",
            "sold_in": ["United Kingdom", "Australia", "European Union"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 12. Knorr Beef Stock Cubes
        "inputs": {
            "image_filename": "knorr_beef_stock_cubes.jpg",
            "image_path": "evaluations/data/images/knorr_beef_stock_cubes.jpg",
        },
        "outputs": {
            "norm_name": "knorr beef stock cubes",
            "companies": ["Knorr", "Unilever"],
            "cert_bodies": ["JAKIM (Malaysia)", "Health Promotion Board (Singapore)"],
            "marketplace": ["Supermarkets", "Asian Grocery Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Pantry & Seasonings",
            "halal_status": "Halal",
            "sold_in": ["Malaysia", "Singapore", "Hong Kong", "Southeast Asia"],
            "cert_numbers": ["MS 1500:2009", "1008-03/2004"],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 13. Skittles Chewy Candy Tube
        "inputs": {
            "image_filename": "skittles_chewy_candy_tube.jpg",
            "image_path": "evaluations/data/images/skittles_chewy_candy_tube.jpg",
        },
        "outputs": {
            "norm_name": "skittles littles original chewy candy tube",
            "companies": ["Skittles", "Mars", "Mars Wrigley"],
            "cert_bodies": [],
            "marketplace": ["Supermarkets", "Convenience Stores", "Retail"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal (Gelatin-Free, Vegan Suitable)",
            "sold_in": ["United States"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 14. Snickers Pumpkin Candy Bars
        "inputs": {
            "image_filename": "snickers_pumpkin_candy_bars.jpg",
            "image_path": "evaluations/data/images/snickers_pumpkin_candy_bars.jpg",
        },
        "outputs": {
            "norm_name": "snickers pumpkins fun size milk chocolate candy bars",
            "companies": ["Snickers", "Mars", "Mars Wrigley"],
            "cert_bodies": ["Orthodox Union Kosher (OU-D)"],
            "marketplace": ["Supermarkets", "Retail", "Seasonal Aisles"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal Suitable (Kosher Dairy, Vegetarian Suitable)",
            "sold_in": ["United States"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": [],
        },
    },
    {
        # 15. Twix Salted Caramel
        "inputs": {
            "image_filename": "twix_salted_caramel.jpg",
            "image_path": "evaluations/data/images/twix_salted_caramel.jpg",
        },
        "outputs": {
            "norm_name": "twix salted caramel chocolate bar",
            "companies": ["Twix", "Mars Wrigley", "Mars"],
            "cert_bodies": ["Halal Certified (Halal Australia / HCAA)"],
            "marketplace": ["Supermarkets", "Retail", "Convenience Stores"],
            "category_l1": "Food",
            "category_l2": "Snacks & Confectionery",
            "halal_status": "Halal",
            "sold_in": ["Australia", "New Zealand"],
            "cert_numbers": [],
            "fda_numbers": [],
            "barcodes": ["6221134031843"],
        },
    },
]

from evaluations.target_functions.vision_extraction import get_image_data_url

# LangSmith Dataset Name
dataset_name = "Halal One Agent: Vision Product Extraction Eval Dataset 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    # Enrich examples with Base64 data URLs for LangSmith upload
    enriched_examples = []
    for ex in examples:
        item = {
            "inputs": {
                "image_filename": ex["inputs"]["image_filename"],
                "image_path": ex["inputs"]["image_path"],
                "image_url": get_image_data_url(ex["inputs"]["image_path"]),
            },
            "outputs": ex["outputs"],
        }
        enriched_examples.append(item)

    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Evaluates vision multimodal extraction against 15 ground-truth product packaging images.",
        )
        client.create_examples(dataset_id=dataset.id, examples=enriched_examples)
    print(f"Successfully generated dataset: {dataset_name}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(generate_dataset())

