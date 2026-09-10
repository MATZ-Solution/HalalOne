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
            "norm_name": "cake bar with strawberry filling",
            "companies": ["7DAYS"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 2. Aero Choco Caramel
        "inputs": {
            "image_filename": "aero_choco_caramel.jpg",
            "image_path": "evaluations/data/images/aero_choco_caramel.jpg",
        },
        "outputs": {
            "norm_name": "aero choco caramel",
            "companies": ["Nestlé", "Aero"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 3. Alyoum Chicken Drumsticks
        "inputs": {
            "image_filename": "alyoum_chicken_drumsticks.jpg",
            "image_path": "evaluations/data/images/alyoum_chicken_drumsticks.jpg",
        },
        "outputs": {
            "norm_name": "alyoum premium fresh chicken drumsticks",
            "companies": ["Alyoum", "Almarai"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": "Halal",
            "sold_in": ["Saudi Arabia"],
            "cert_numbers": None,
            "fda_numbers": None,
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
            "norm_name": "bahlsen waffeletten dark",
            "companies": ["Bahlsen"],
            "cert_bodies": ["UTZ Certified"],
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
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
            "norm_name": None,
            "companies": ["Ben & Jerry's", "Unilever"],
            "cert_bodies": ["Fairtrade", "KOF-K"],
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
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
            "norm_name": "drumstick king size triple chocolate",
            "companies": ["Nestlé", "Drumstick"],
            "cert_bodies": ["Orthodox Union Kosher", "OU-D"],
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
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
            "norm_name": "haribo jelly beans",
            "companies": ["Haribo"],
            "cert_bodies": ["European Vegetarian Union", "V-Label"],
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 8. Hot Pockets Jalapeno Popper
        "inputs": {
            "image_filename": "hot_pockets_jalapeno_popper.jpg",
            "image_path": "evaluations/data/images/hot_pockets_jalapeno_popper.jpg",
        },
        "outputs": {
            "norm_name": "hot pockets snack breaks spicy jalapeno popper",
            "companies": ["Hot Pockets"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 9. Katjes Alpaka Cola
        "inputs": {
            "image_filename": "katjes_alpaka_cola.jpg",
            "image_path": "evaluations/data/images/katjes_alpaka_cola.jpg",
        },
        "outputs": {
            "norm_name": "alpaka cola",
            "companies": ["Katjes", "Katjes Fassin GmbH + Co. KG"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
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
            "norm_name": "kinder happy hippo haselnuss",
            "companies": ["Kinder"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 11. KitKat Chunky Bar
        "inputs": {
            "image_filename": "kitkat_chunky_bar.jpg",
            "image_path": "evaluations/data/images/kitkat_chunky_bar.jpg",
        },
        "outputs": {
            "norm_name": "kitkat chunky crunchy double choc",
            "companies": ["Nestlé", "KitKat"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 12. Knorr Beef Stock Cubes
        "inputs": {
            "image_filename": "knorr_beef_stock_cubes.jpg",
            "image_path": "evaluations/data/images/knorr_beef_stock_cubes.jpg",
        },
        "outputs": {
            "norm_name": "beef stock cubes",
            "companies": ["Knorr"],
            "cert_bodies": ["Health Promotion Board"],
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": "Halal",
            "sold_in": None,
            "cert_numbers": ["MS 1500:2009", "1008-03/2004"],
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 13. Skittles Chewy Candy Tube
        "inputs": {
            "image_filename": "skittles_chewy_candy_tube.jpg",
            "image_path": "evaluations/data/images/skittles_chewy_candy_tube.jpg",
        },
        "outputs": {
            "norm_name": "skittles littles",
            "companies": ["Skittles"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 14. Snickers Pumpkin Candy Bars
        "inputs": {
            "image_filename": "snickers_pumpkin_candy_bars.jpg",
            "image_path": "evaluations/data/images/snickers_pumpkin_candy_bars.jpg",
        },
        "outputs": {
            "norm_name": "snickers pumpkins fun size",
            "companies": ["Snickers"],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": None,
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": None,
        },
    },
    {
        # 15. Twix Salted Caramel
        "inputs": {
            "image_filename": "twix_salted_caramel.jpg",
            "image_path": "evaluations/data/images/twix_salted_caramel.jpg",
        },
        "outputs": {
            "norm_name": "twix salted caramel",
            "companies": ["Twix", "Mars", "Mars Egypt for Manufacturing L.L.C."],
            "cert_bodies": None,
            "marketplace": None,
            "category_l1": None,
            "category_l2": None,
            "halal_status": None,
            "sold_in": ["Egypt", "Morocco", "Syria", "Palestine", "Tunisia"],
            "cert_numbers": None,
            "fda_numbers": None,
            "barcodes": ["6221134010312"],
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

    if client.has_dataset(dataset_name=dataset_name):
        dataset = client.read_dataset(dataset_name=dataset_name)
        client.delete_dataset(dataset_id=dataset.id)
        print(f"Deleted old dataset: {dataset_name}")

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Evaluates vision multimodal extraction against 15 ground-truth product packaging images.",
    )
    client.create_examples(dataset_id=dataset.id, examples=enriched_examples)
    print(f"Successfully generated and uploaded dataset: {dataset_name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(generate_dataset())
