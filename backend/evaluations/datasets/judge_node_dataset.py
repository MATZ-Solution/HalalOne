import asyncio
from config.langsmith_client import get_langsmith_client

examples = [
    {
        "inputs": {
            "keyword_args": {"norm_name": "biryani masala", "companies": ["Shan"]},
            "candidates": [
                {"canonical_id": "halal_000001", "norm_name": "Shan Biryani Masala", "companies": ["Shan Foods"]},
                {"canonical_id": "halal_000002", "norm_name": "National Biryani Masala", "companies": ["National Foods"]},
                {"canonical_id": "halal_000003", "norm_name": "Shan Nihari Masala", "companies": ["Shan Foods"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000001"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "olive oil"},
            "candidates": [
                {"canonical_id": "halal_000010", "norm_name": "Extra Virgin Olive Oil", "companies": ["Borges"]},
                {"canonical_id": "halal_000011", "norm_name": "Pure Olive Oil", "companies": ["Figaro"]},
                {"canonical_id": "halal_000012", "norm_name": "Sunflower Oil", "companies": ["Dalda"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000010", "halal_000011"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "creme brulee"},
            "candidates": [
                {"canonical_id": "halal_000020", "norm_name": "Crema Catalana", "companies": ["Hacendado"]},
                {"canonical_id": "halal_000021", "norm_name": "Vanilla Ice Cream", "companies": ["Walls"]},
            ],
        },
        "outputs": {"canonical_ids": []},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "dried fruits white mullberries", "companies": ["basse"]},
            "candidates": [
                {"canonical_id": "halal_000030", "norm_name": "basse, dried fruits, white mulberries", "companies": ["basse"]},
                {"canonical_id": "halal_000031", "norm_name": "dried mixed nuts", "companies": ["basse"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000030"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "chocholate chip cookies", "companies": ["mcvities"]},
            "candidates": [
                {"canonical_id": "halal_000040", "norm_name": "Chocolate Chip Cookies", "companies": ["McVitie's"]},
                {"canonical_id": "halal_000041", "norm_name": "Digestive Biscuits", "companies": ["McVitie's"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000040"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "coconut mixed nuts", "companies": ["heritage snacks"]},
            "candidates": [
                {
                    "canonical_id": "halal_031898",
                    "norm_name": "coconut mixed nuts (cashews, almonds, walnuts)",
                    "companies": ["heritage snacks & food co., ltd. (krathum lom, sam phran, nakhon pathom, thailand)"],
                },
                {"canonical_id": "halal_031899", "norm_name": "coconut mixed nuts", "companies": ["tong garden"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_031898"]},
    },
    {
        "inputs": {
            "keyword_args": {"companies": ["Nestle"]},
            "candidates": [
                {"canonical_id": "halal_000050", "norm_name": "KitKat", "companies": ["Nestlé"]},
                {"canonical_id": "halal_000051", "norm_name": "Nescafé Classic", "companies": ["Nestlé"]},
                {"canonical_id": "halal_000052", "norm_name": "Dairy Milk", "companies": ["Cadbury"]},
                {"canonical_id": "halal_000053", "norm_name": "Maggi Noodles", "companies": ["Nestlé"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000050", "halal_000051", "halal_000053"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "orange juice"},
            "candidates": [
                {"canonical_id": "halal_000060", "norm_name": "Orange Juice", "companies": ["Tropicana"]},
                {"canonical_id": "halal_000061", "norm_name": "Fresh Orange Juice", "companies": ["Del Monte"]},
                {"canonical_id": "halal_000062", "norm_name": "Orange & Mango Juice", "companies": ["Rani"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000060", "halal_000061"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "cafe latte", "companies": ["lavazza"]},
            "candidates": [
                {"canonical_id": "halal_000070", "norm_name": "Café Latté", "companies": ["Lavazza S.p.A."]},
                {"canonical_id": "halal_000071", "norm_name": "Cappuccino", "companies": ["Lavazza S.p.A."]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000070"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "greek yogurt", "companies": ["Chobani"]},
            "candidates": [
                {"canonical_id": "halal_000080", "norm_name": "Greek Yogurt", "companies": ["Chobani"]},
                {"canonical_id": "halal_000081", "norm_name": "Greek Yogurt", "companies": ["Fage"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000080"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "nutella", "companies": ["ferrero"]},
            "candidates": [
                {"canonical_id": "halal_000090", "norm_name": "Ferrero Nutella Hazelnut Spread", "companies": ["Ferrero"]},
                {"canonical_id": "halal_000091", "norm_name": "Hazelnut Spread", "companies": ["Hershey"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000090"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "corn flakes", "companies": ["kelogs"]},
            "candidates": [
                {"canonical_id": "halal_000100", "norm_name": "Corn Flakes", "companies": ["Kellogg's"]},
                {"canonical_id": "halal_000101", "norm_name": "Corn Flakes", "companies": ["Nestlé"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000100"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "sparkling water", "companies": ["Perrier"]},
            "candidates": [],
        },
        "outputs": {"canonical_ids": []},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "basmati rice"},
            "candidates": [
                {"canonical_id": "halal_000110", "norm_name": "Basmati Rice", "companies": ["Falak"]},
                {"canonical_id": "halal_000111", "norm_name": "Premium Basmati Rice", "companies": ["Guard"]},
                {"canonical_id": "halal_000112", "norm_name": "Long Grain Basmati Rice", "companies": ["India Gate"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000110", "halal_000111", "halal_000112"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "tomato ketchup"},
            "candidates": [
                {"canonical_id": "halal_000120", "norm_name": "Tomato Ketchup", "companies": ["Heinz"]},
                {"canonical_id": "halal_000121", "norm_name": "Tomato Paste", "companies": ["Kissan"]},
                {"canonical_id": "halal_000122", "norm_name": "Tomato Puree", "companies": ["Mitchell's"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000120"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "noodles", "companies": ["Maggi"]},
            "candidates": [
                {"canonical_id": "halal_000130", "norm_name": "Maggi 2-Minute Noodles", "companies": ["Nestlé"]},
                {"canonical_id": "halal_000131", "norm_name": "Instant Noodles", "companies": ["Nestlé"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000130"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "chaat masala", "companies": ["Shan", "National"]},
            "candidates": [
                {"canonical_id": "halal_000140", "norm_name": "Chaat Masala", "companies": ["Shan Foods"]},
                {"canonical_id": "halal_000141", "norm_name": "Chaat Masala", "companies": ["National Foods"]},
                {"canonical_id": "halal_000142", "norm_name": "Chaat Masala", "companies": ["Mehran"]},
            ],
        },
        "outputs": {"canonical_ids": []},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "dark chocolate", "companies": ["Lindt"]},
            "candidates": [
                {"canonical_id": "halal_000150", "norm_name": "Lindt Excellence Dark Chocolate", "companies": ["Lindt"]},
                {"canonical_id": "halal_000151", "norm_name": "Lindt Dark Chocolate 70%", "companies": ["Lindt"]},
                {"canonical_id": "halal_000152", "norm_name": "Lindt Milk Chocolate", "companies": ["Lindt"]},
                {"canonical_id": "halal_000153", "norm_name": "Dark Chocolate", "companies": ["Cadbury"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000150", "halal_000151"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "green tea", "companies": ["Lipton"]},
            "candidates": [
                {"canonical_id": "halal_000160", "norm_name": "Green Tea", "companies": ["Lipton"]},
                {"canonical_id": "halal_000161", "norm_name": "Green Tea", "companies": []},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000160"]},
    },
    {
        "inputs": {
            "keyword_args": {"norm_name": "chickpeas"},
            "candidates": [
                {"canonical_id": "halal_000170", "norm_name": "Garbanzo Beans", "companies": ["Sunny"]},
                {"canonical_id": "halal_000171", "norm_name": "Kidney Beans", "companies": ["Sunny"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_000170"]},
    },
]

dataset_name = "Halal One Agent: Judge Node (Field Match) 1.1"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
        )
    print(f"Successfully generated dataset:{dataset_name}")


# import asyncio
# asyncio.run(generate_dataset())


# ---------------------------------------------------------------------------
# Variant dataset — post rubric change: DIFFERENT VARIANTS OF THE SAME PRODUCT
# (sizes, grades, flavours, pack forms) should ALL match, not be rejected.
# Every candidate here is a genuine variant of the user's product, so every id is
# expected to match.
# ---------------------------------------------------------------------------
variant_examples = [
    # olive oil — grade variants match; other cooking oils do not.
    {
        "inputs": {
            "keyword_args": {"norm_name": "olive oil"},
            "candidates": [
                {"canonical_id": "halal_100010", "norm_name": "Extra Virgin Olive Oil", "companies": ["Borges"]},
                {"canonical_id": "halal_100011", "norm_name": "Pure Olive Oil", "companies": ["Figaro"]},
                {"canonical_id": "halal_100012", "norm_name": "Light Olive Oil", "companies": ["Bertolli"]},
                # distractors: different oils entirely
                {"canonical_id": "halal_100013", "norm_name": "Sunflower Oil", "companies": ["Dalda"]},
                {"canonical_id": "halal_100014", "norm_name": "Avocado Oil", "companies": ["Chosen Foods"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100010", "halal_100011", "halal_100012"]},
    },
    # nutella — jar-size variants match; same-brand-different-product and wrong-brand fail.
    {
        "inputs": {
            "keyword_args": {"norm_name": "nutella", "companies": ["ferrero"]},
            "candidates": [
                {"canonical_id": "halal_100020", "norm_name": "Nutella Hazelnut Spread 350g", "companies": ["Ferrero"]},
                {"canonical_id": "halal_100021", "norm_name": "Nutella 750g", "companies": ["Ferrero"]},
                {"canonical_id": "halal_100022", "norm_name": "Nutella & Go", "companies": ["Ferrero"]},
                # distractor: same brand, different product (chocolates, not the spread)
                {"canonical_id": "halal_100023", "norm_name": "Ferrero Rocher", "companies": ["Ferrero"]},
                # distractor: a hazelnut spread but a different brand
                {"canonical_id": "halal_100024", "norm_name": "Hazelnut Cocoa Spread", "companies": ["Hershey's"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100020", "halal_100021", "halal_100022"]},
    },
    # lay's — chip flavour variants match; same-brand-different-form and other-brand fail.
    {
        "inputs": {
            "keyword_args": {"norm_name": "lays chips", "companies": ["lays"]},
            "candidates": [
                {"canonical_id": "halal_100030", "norm_name": "Lay's Classic Salted", "companies": ["Lay's"]},
                {"canonical_id": "halal_100031", "norm_name": "Lay's Salt & Vinegar", "companies": ["Lay's"]},
                {"canonical_id": "halal_100032", "norm_name": "Lay's Masala", "companies": ["Lay's"]},
                # distractor: same brand, but a dip — not chips
                {"canonical_id": "halal_100033", "norm_name": "Lay's French Onion Dip", "companies": ["Lay's"]},
                # distractor: chips, but a different brand
                {"canonical_id": "halal_100034", "norm_name": "Pringles Original", "companies": ["Pringles"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100030", "halal_100031", "halal_100032"]},
    },
    # greek yogurt — fat/pack variants match; same-brand-different-product and wrong-brand fail.
    {
        "inputs": {
            "keyword_args": {"norm_name": "greek yogurt", "companies": ["Chobani"]},
            "candidates": [
                {"canonical_id": "halal_100040", "norm_name": "Greek Yogurt", "companies": ["Chobani"]},
                {"canonical_id": "halal_100041", "norm_name": "Low-Fat Greek Yogurt", "companies": ["Chobani"]},
                {"canonical_id": "halal_100042", "norm_name": "Non-Fat Greek Yogurt 500g", "companies": ["Chobani"]},
                # distractor: same brand, different product
                {"canonical_id": "halal_100043", "norm_name": "Chobani Oat Milk", "companies": ["Chobani"]},
                # distractor: greek yogurt, but a different brand
                {"canonical_id": "halal_100044", "norm_name": "Greek Yogurt", "companies": ["Fage"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100040", "halal_100041", "halal_100042"]},
    },
    # coca-cola — line variants match; other sodas (incl. same-company Sprite) fail.
    {
        "inputs": {
            "keyword_args": {"norm_name": "coca cola"},
            "candidates": [
                {"canonical_id": "halal_100050", "norm_name": "Coca-Cola Classic", "companies": ["Coca-Cola"]},
                {"canonical_id": "halal_100051", "norm_name": "Coca-Cola Zero Sugar", "companies": ["Coca-Cola"]},
                {"canonical_id": "halal_100052", "norm_name": "Diet Coke", "companies": ["Coca-Cola"]},
                # distractor: same company, different drink
                {"canonical_id": "halal_100053", "norm_name": "Sprite", "companies": ["Coca-Cola"]},
                # distractor: a cola, but a different brand
                {"canonical_id": "halal_100054", "norm_name": "Pepsi Cola", "companies": ["PepsiCo"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100050", "halal_100051", "halal_100052"]},
    },
    # peanut butter — texture variants match; same-brand-different-product and
    # a different nut butter fail.
    {
        "inputs": {
            "keyword_args": {"norm_name": "peanut butter", "companies": ["Skippy"]},
            "candidates": [
                {"canonical_id": "halal_100060", "norm_name": "Skippy Creamy Peanut Butter", "companies": ["Skippy"]},
                {"canonical_id": "halal_100061", "norm_name": "Skippy Super Chunk Peanut Butter", "companies": ["Skippy"]},
                {"canonical_id": "halal_100062", "norm_name": "Skippy Natural Peanut Butter 500g", "companies": ["Skippy"]},
                # distractor: same brand, different product
                {"canonical_id": "halal_100063", "norm_name": "Skippy Chocolate Hazelnut Spread", "companies": ["Skippy"]},
                # distractor: a nut butter, but not peanut (and a different brand)
                {"canonical_id": "halal_100064", "norm_name": "Almond Butter", "companies": ["Jif"]},
            ],
        },
        "outputs": {"canonical_ids": ["halal_100060", "halal_100061", "halal_100062"]},
    },
]

variant_dataset_name = "Halal One Agent: Judge Node (Same-Product Variants) 1.0"


async def generate_variant_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=variant_dataset_name):
        dataset = client.create_dataset(dataset_name=variant_dataset_name)
        client.create_examples(
            dataset_id=dataset.id,
            examples=variant_examples,
        )
    print(f"Successfully generated dataset:{variant_dataset_name}")


asyncio.run(generate_variant_dataset())
