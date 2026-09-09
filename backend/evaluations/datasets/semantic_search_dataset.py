from config.langsmith_client import get_langsmith_client
from agents.langgraph_agent.utils.utils import SEMANTIC

DIRECT = None

examples = [
    {
        "inputs": {"question": "something rich in iron that helps with low energy"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products rich in iron that help with low energy",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "nutrient need with no product or brand"},
    },
    {
        "inputs": {"question": "I need something suitable for diabetics that won't spike blood sugar"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products suitable for diabetics that do not spike blood sugar",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "health condition framing"},
    },
    {
        "inputs": {"question": "I need snacks with no nuts in them at all for a school lunchbox"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "nut free snacks for a school lunchbox",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "avoidance framing; the exclusion must survive in the query"},
    },
    {
        "inputs": {"question": "what should I give a toddler who is just starting on solids"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "food for a toddler starting on solids",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Baby & Infant"],
        },
        "metadata": {"category": "intent_capture", "note": "life stage must stay in the text, not become a category filter"},
    },
    {
        "inputs": {"question": "looking for something warming and creamy for cold evenings"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "warming creamy products for cold evenings",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "purely sensory description"},
    },
    {
        "inputs": {"question": "what can I get that keeps for months without a fridge, for travelling"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "shelf stable products that keep for months without refrigeration for travel",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Travel"],
        },
        "metadata": {"category": "intent_capture", "note": "functional requirement; Travel is a category value and must not be set"},
    },
    {
        "inputs": {"question": "I want sweets for iftar that aren't too heavy after fasting"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "light sweets suitable for iftar after fasting",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "cultural occasion; halal must not be assumed from the context"},
    },
    {
        "inputs": {"question": "is there anything that helps me sleep better at night"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products that help with sleep",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Wellness", "Herbal Medicine", "Pharma"],
        },
        "metadata": {"category": "intent_capture", "note": "wellness need must not be snapped to a real category value"},
    },
    {
        "inputs": {"question": "something I can cook in under ten minutes after work"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "quick products that cook in under ten minutes",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "intent_capture", "note": "preparation-time need with no product named"},
    },
    {
        "inputs": {"question": "I want a natural red colouring that isn't derived from insects"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "natural red colouring not derived from insects",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Colorant", "Additive"],
        },
        "metadata": {"category": "intent_capture", "note": "ingredient property; Colorant is a category value and must not be inferred"},
    },
    {
        "inputs": {"question": "a moisturiser that won't clog pores and has no alcohol in it"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "non comedogenic alcohol free moisturiser",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Cosmetic", "Skin Care"],
        },
        "metadata": {"category": "intent_capture", "note": "cosmetic need; the category was never stated by the user"},
    },
    {
        "inputs": {"question": "high protein options that aren't meat"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "high protein products that are not meat",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Meat & Poultry"],
        },
        "metadata": {"category": "intent_capture", "note": "a negated category name must not become a positive filter"},
    },

    {
        "inputs": {"question": "Fetch me halal products that are used for baking a cake and gluten free. Should be sold in UK and india."},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "gluten free products used for baking a cake",
            "filter_args": {"halal_status": "Halal", "sold_in": ["UK", "India"]},
            "forbidden_terms": ["UK", "India", "halal"],
        },
        "metadata": {"category": "filter_lifting", "source": "prompt_fewshot", "note": "control row, verbatim from the system prompt"},
    },
    {
        "inputs": {"question": "cosmetics category, something for very dry skin in winter"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products for very dry skin in winter",
            "filter_args": {"category_l1": "Cosmetic"},
            "forbidden_filter_keys": ["halal_status"],
            # "forbidden_terms": ["cosmetics category"],
        },
        "metadata": {"category": "filter_lifting", "note": "the user named the category, so it is a filter and leaves the text"},
    },
    {
        "inputs": {"question": "anything certified by JAKIM that works as a natural sweetener"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "natural sweetener",
            "filter_args": {"cert_bodies": ["JAKIM"]},
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["JAKIM", "Sweetener"],
        },
        "metadata": {"category": "filter_lifting", "note": "certifier is an exact filter; Sweetener is a category value and must not be set"},
    },
    {
        "inputs": {"question": "show me the doubtful ones that people usually assume are fine"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products people usually assume are permissible",
            "filter_args": {"halal_status": "Mushbooh"},
            "forbidden_filter_keys": ["category_l1", "category_l2"],
        },
        "metadata": {"category": "filter_lifting", "note": "doubtful is a status synonym and must map to Mushbooh"},
    },
    {
        "inputs": {"question": "I want something gentle on the stomach for my baby, halal, available in Malaysia"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products that are gentle on the stomach for a baby",
            "filter_args": {"halal_status": "Halal", "sold_in": ["Malaysia"]},
            "forbidden_filter_keys": ["category_l1", "category_l2"],
            "forbidden_terms": ["Malaysia", "halal", "Baby & Infant"],
        },
        "metadata": {"category": "filter_lifting", "note": "two stated filters leave the text; the life stage stays in it"},
    },
    {
        "inputs": {"question": "something for sensitive skin that I can buy through retail"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products for sensitive skin",
            "filter_args": {"marketplace": ["Retail"]},
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["retail"],
        },
        "metadata": {"category": "filter_lifting", "note": "marketplace is the only stated filter"},
    },

    {
        "inputs": {"question": "I need something high in fibre, Food category, Nutritional Supplement subcategory, halal, sold in UAE and Oman, certified by HMA, through retail"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products high in fibre",
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Nutritional Supplement",
                "halal_status": "Halal",
                "sold_in": ["UAE", "Oman"],
                "cert_bodies": ["HMA"],
                "marketplace": ["Retail"],
            },
            "forbidden_terms": ["UAE", "Oman", "HMA", "halal"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "note": "six filters must be extracted while the conceptual need stays in the query"},
    },
    {
        "inputs": {"question": "something gentle for sensitive skin, Cosmetic category, Skin Care, halal, sold in Malaysia and Indonesia, certified by JAKIM and HFCE, retail"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "gentle products for sensitive skin",
            "filter_args": {
                "category_l1": "Cosmetic",
                "category_l2": "Skin Care",
                "halal_status": "Halal",
                "sold_in": ["Malaysia", "Indonesia"],
                "cert_bodies": ["JAKIM", "HFCE"],
                "marketplace": ["Retail"],
            },
            "forbidden_terms": ["Malaysia", "Indonesia", "JAKIM", "halal"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "note": "multi-value lists in two fields alongside a conceptual query"},
    },
    {
        "inputs": {"question": "something rich in protien, Fod category, Nutritional Suplement, halal, sold in Malasia and Indonisia, certified by Jakim"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products rich in protein",
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Nutritional Supplement",
                "halal_status": "Halal",
                "sold_in": ["Malaysia", "Indonesia"],
                "cert_bodies": ["JAKIM"],
            },
            "forbidden_filter_keys": ["marketplace"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 5, "note": "five filters all misspelt, on a conceptual query"},
    },

    {
        "inputs": {"question": "Ahhh I'm so tired and frustrated living in London, I can't find any good halal nutritional products for my baby. He is just a month old. Can you help?"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "nutritional products for a baby",
            "filter_args": {"halal_status": "Halal", "sold_in": ["UK"]},
            "forbidden_terms": ["London", "month old", "frustrated", "tired"],
        },
        "metadata": {"category": "noise_stripping", "source": "prompt_fewshot", "note": "control row, close to a prompt example"},
    },
    {
        "inputs": {"question": "honestly this is the third app I've tried today, I've been at this for hours and I'm about to give up, I just want something that's high in calcium"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products high in calcium",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["app", "give up", "hours", "third"],
        },
        "metadata": {"category": "noise_stripping", "note": "long venting; only the need may reach the query"},
    },
    {
        "inputs": {"question": "Hi there, hope you're well, thank you so much for helping me the other day. When you have a moment, could you possibly suggest something low in sodium? Thanks again!"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "low sodium products",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["thank", "hope you", "moment"],
        },
        "metadata": {"category": "noise_stripping", "note": "politeness padding around a one-clause need"},
    },
    {
        "inputs": {"question": "my mother in law is visiting next week and she is quite particular, she had surgery last year and the doctor was strict about it, anyway what I need is something soft and easy to chew"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "soft products that are easy to chew",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["mother in law", "surgery", "doctor", "week"],
        },
        "metadata": {"category": "noise_stripping", "note": "the need is the last clause of a long story"},
    },

    {
        "inputs": {"question": "something nutritious for elderly parents"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "nutritious products for elderly people",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Nutritional Supplement", "Health Product", "Wellness"],
        },
        "metadata": {"category": "must_not_invent", "note": "a need must not be snapped to a real category value"},
    },
    {
        "inputs": {"question": "kuch aisa chahiye jo bachon ke liye healthy ho"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "healthy products for children",
            "filter_args": None,
            "forbidden_filter_keys": ["sold_in", "category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Pakistan", "India", "South Asia"],
        },
        "metadata": {"category": "must_not_invent", "note": "the language of the question must not become a country filter"},
    },
    {
        "inputs": {"question": "I want something refreshing to drink"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "refreshing drinks",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Beverage", "General Beverage", "Juice"],
        },
        "metadata": {"category": "must_not_invent", "note": "drink must not become category_l1 Beverage; the user set no filter"},
    },
    {
        "inputs": {"question": "vegan options with a long shelf life"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "vegan products with a long shelf life",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["Halal", "Mushbooh"],
        },
        "metadata": {"category": "must_not_invent", "note": "vegan is not a halal status and there is no field for it"},
    },
    {
        "inputs": {"question": "I'm fasting all month, what keeps energy up through the day"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products that sustain energy through the day while fasting",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status", "sold_in"],
        },
        "metadata": {"category": "must_not_invent", "note": "religious context must not be turned into a halal_status filter"},
    },

    {
        "inputs": {"question": "healthy snacks under 100 calories"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "healthy snacks under 100 calories",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "barcodes", "cert_numbers", "halal_status"],
        },
        "metadata": {"category": "unsupported", "note": "no calorie field; the constraint may stay in the text but not in a filter"},
    },
    {
        "inputs": {"question": "cheap filling meals for a student budget"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "affordable filling meals",
            "filter_args": None,
            "forbidden_filter_keys": ["marketplace", "category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "unsupported", "note": "no price field exists"},
    },
    {
        "inputs": {"question": "bulk quantities of dried fruit for a family of eight"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "bulk quantities of dried fruit for a large family",
            "filter_args": None,
            "forbidden_filter_keys": ["marketplace", "category_l1", "category_l2"],
            "forbidden_terms": ["FoodService - Bulk", "Industry"],
        },
        "metadata": {"category": "unsupported", "known_ambiguity": True, "note": "bulk must not be snapped to a marketplace value"},
    },
    {
        "inputs": {"question": "anything that was certified in the last two years and is good for skin"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "certified in the last two years and good for skin",
            "filter_args": None,
            "forbidden_filter_keys": ["cert_bodies", "cert_numbers", "category_l1", "category_l2", "halal_status"],
            # "forbidden_terms": ["two years", "2024", "2025"],
        },
        "metadata": {"category": "unsupported", "note": "no certification date field; the constraint must be dropped, not forced into cert_numbers"},
    },

    {
        "inputs": {"question": "what can I eat that helps with acid reflux?"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products that help with acid reflux",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["?", "what can I"],
        },
        "metadata": {"category": "query_hygiene", "note": "a question must become a search phrase, not be embedded as a question"},
    },
    {
        "inputs": {"question": "my doctor said I need more fibre in my diet"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products high in fibre",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["doctor", "my diet"],
        },
        "metadata": {"category": "query_hygiene", "note": "first-person framing must be generalised into a product need"},
    },
    {
        "inputs": {"question": "something healthier than crisps for an afternoon snack"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "healthier alternatives to crisps for an afternoon snack",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "query_hygiene", "note": "comparative framing; the reference point must survive"},
    },
    {
        "inputs": {"question": "sweets that contain absolutely no gelatin"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "sweets that contain no gelatin",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "query_hygiene", "note": "the negation must survive; dropping it inverts the meaning"},
    },
    {
        "inputs": {"question": "I want something both high in protein and low in sugar"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products high in protein and low in sugar",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "query_hygiene", "note": "both clauses must be kept, not just the first"},
    },

    {
        "inputs": {"question": "healthy"},
        "outputs": {
            "expected_tool": [SEMANTIC, DIRECT],
            "semantic_query": "healthy products",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "degenerate", "known_ambiguity": True, "note": "single word; must not be padded with invented detail"},
    },
    {
        "inputs": {"question": "I want something sweet but with no sugar in it at all"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "sweet tasting products with no sugar",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "degenerate", "note": "apparent contradiction that is actually a real product class"},
    },
    {
        "inputs": {"question": "I need protein for the gym, and also something for my daughter's eczema, and ideally something for my father's blood pressure"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "max_tool_calls": 1,
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "degenerate", "known_ambiguity": True, "note": "three unrelated needs; must not emit parallel tool calls"},
    },
    {
        "inputs": {"question": "something nice"},
        "outputs": {"expected_tool": [SEMANTIC, DIRECT]},
        "metadata": {"category": "degenerate", "known_ambiguity": True, "note": "too vague to embed usefully; asking to clarify is defensible"},
    },
]

dataset_name = "Halal One Agent: Semantic Search (Conceptual Queries) 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset:{dataset_name}")


import asyncio
asyncio.run(generate_dataset())
