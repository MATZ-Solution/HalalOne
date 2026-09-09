from config.langsmith_client import get_langsmith_client
from agents.langgraph_agent.utils.utils import KEYWORD, SEMANTIC

DIRECT = None

examples = [
    {
        "inputs": {"question": "Is KitKat halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "kitkat", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["Nestle", "Nestlé", "chocolate"],
        },
        "metadata": {"category": "distinctive_product", "note": "distinctive product name, no brand stated"},
    },
    {
        "inputs": {"question": "Is Nestle KitKat halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "kitkat", "companies": ["Nestle"]},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["chocolate"],
        },
        "metadata": {"category": "distinctive_product", "note": "distinctive product plus a company"},
    },
    {
        "inputs": {"question": "Is Nutella halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "nutella", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["Ferrero", "hazelnut spread"],
        },
        "metadata": {"category": "distinctive_product", "note": "brand and product are the same word"},
    },
    {
        "inputs": {"question": "Are Skittles halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "skittles", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["Mars", "Wrigley", "candy", "sweets"],
        },
        "metadata": {"category": "distinctive_product", "note": "must not add the manufacturer or a category word"},
    },
    {
        "inputs": {"question": "Is 7up halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "7up", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["barcodes", "cert_numbers", "fda_numbers", "halal_status", "category_l1"],
            "forbidden_terms": ["soda", "soft drink"],
        },
        "metadata": {"category": "distinctive_product", "note": "digits in a product name must not become an identifier"},
    },
    {
        "inputs": {"question": "Is E471 halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "e471", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
            "forbidden_terms": ["diglyceride", "monoglyceride", "fatty acid", "emulsifier"],
        },
        "metadata": {"category": "distinctive_product", "note": "an additive code identifies one substance, so it is a valid norm_name"},
    },
    {
        "inputs": {"question": "Is McDonald's Big Mac sauce halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "big mac sauce", "companies": ["McDonald's"]},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l2"],
        },
        "metadata": {"category": "distinctive_product", "note": "punctuation in the brand is normalized away before comparison, so any spelling of McDonald's passes"},
    },
    {
        "inputs": {"question": "Is Nestle Milo halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "milo", "companies": ["Nestle"]},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
            "forbidden_terms": ["malt", "drink", "beverage"],
        },
        "metadata": {"category": "distinctive_product", "note": "Milo is a named product, unlike the generic word drinks"},
    },
    {
        "inputs": {"question": "kya Rooh Afza halal hai?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "rooh afza", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "sold_in", "category_l2"],
            "forbidden_terms": ["rose syrup", "sharbat", "squash"],
        },
        "metadata": {"category": "distinctive_product", "note": "transliterated named product; must not be translated"},
    },
    {
        "inputs": {"question": "IS COCA-COLA HALAL??"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "coca-cola", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
        },
        "metadata": {"category": "distinctive_product", "note": "all caps input; the name still normalises"},
    },
    {
        "inputs": {"question": "Is Meiji Hello Panda halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "hello panda", "companies": ["Meiji"]},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "sold_in", "category_l2"],
            "forbidden_terms": ["Japan", "biscuit"],
        },
        "metadata": {"category": "distinctive_product", "note": "must not infer sold_in from the brand's origin"},
    },
    {
        "inputs": {"question": "oreo"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "oreo", "companies": None},
            "filter_args": None,
            "forbidden_filter_keys": [
                "category_l1", "category_l2", "halal_status", "sold_in",
                "cert_bodies", "cert_numbers", "fda_numbers", "barcodes", "marketplace",
            ],
        },
        "metadata": {"category": "over_extraction", "note": "bare product name; every filter must stay unset"},
    },

    {
        "inputs": {"question": "Show me halal Nestle products sold in the UK"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": None, "companies": ["Nestle"]},
            "filter_args": {"halal_status": "Halal", "sold_in": ["UK"]},
            "forbidden_filter_keys": ["category_l1", "category_l2", "cert_bodies"],
        },
        "metadata": {"category": "filler_plus_filters", "note": "products is filler, so the company and filters drive a keyword search"},
    },
    {
        "inputs": {"question": "Show me all items from Unilever certified by JAKIM in Malaysia"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": None, "companies": ["Unilever"]},
            "filter_args": {"cert_bodies": ["JAKIM"], "sold_in": ["Malaysia"]},
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
        },
        "metadata": {"category": "filler_plus_filters", "note": "items is filler; norm_name must stay null"},
    },
    {
        "inputs": {"question": "anything from Ferrero that is mushbooh"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": None, "companies": ["Ferrero"]},
            "filter_args": {"halal_status": "Mushbooh"},
            "forbidden_filter_keys": ["category_l1", "category_l2"],
        },
        "metadata": {"category": "filler_plus_filters", "note": "anything is filler; a status filter is enough for keyword"},
    },

    {
        "inputs": {"question": "Show me all halal certified products sold in Pakistan"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {"halal_status": "Halal", "sold_in": ["Pakistan"]},
            "forbidden_filter_keys": ["category_l1", "category_l2", "cert_bodies"],
            "forbidden_terms": ["South Asia", "India"],
        },
        "metadata": {"category": "filter_only", "note": "Pakistan is absent from the canonical list yet the prompt's own example emits it"},
    },
    {
        "inputs": {"question": "Is the product with barcode 8901234567 halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {"barcodes": ["8901234567"]},
            "forbidden_filter_keys": ["halal_status", "category_l1"],
        },
        "metadata": {"category": "filter_only", "note": "an identifier alone is always a keyword search"},
    },
    {
        "inputs": {"question": "certification number 2a22782D70 please"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {"cert_numbers": ["2a22782D70"]},
            "forbidden_filter_keys": ["halal_status"],
            "forbidden_terms": ["2A22782D70", "2a22782d70"],
        },
        "metadata": {"category": "verbatim_ids", "note": "mixed casing must survive exactly"},
    },
    {
        "inputs": {"question": "Find the product with FDA number 12345-678"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {"fda_numbers": ["12345-678"]},
            "forbidden_filter_keys": ["halal_status"],
            "forbidden_terms": ["12345678"],
        },
        "metadata": {"category": "verbatim_ids", "note": "the hyphen must not be removed"},
    },
    {
        "inputs": {"question": "find the mushboh product with barcode 0 89 01234 5678 sold in the uae"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {
                "halal_status": "Mushbooh",
                "barcodes": ["0 89 01234 5678"],
                "sold_in": ["UAE"],
            },
            "forbidden_terms": ["8901234567", "089012345678"],
        },
        "metadata": {"category": "verbatim_ids", "note": "verbatim and normalized fields in one call"},
    },
    {
        "inputs": {"question": "product with barcodes 0089012345678 and 089 0123 4567 8, cert numbers 2a22782D70 and MY-00931b, FDA 12345-678, halal, sold in Malaysia, industry"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {
                "barcodes": ["0089012345678", "089 0123 4567 8"],
                "cert_numbers": ["2a22782D70", "MY-00931b"],
                "fda_numbers": ["12345-678"],
                "halal_status": "Halal",
                "sold_in": ["Malaysia"],
                "marketplace": ["Industry"],
            },
            "forbidden_terms": ["89012345678", "MY-00931B", "2A22782D70"],
        },
        "metadata": {"category": "verbatim_ids", "filter_count": 6, "note": "five identifiers with leading zeros, spaces and mixed casing"},
    },

    {
        "inputs": {"question": "Find KitKat, category Food, subcategory Snacks & Confectionery, halal, sold in UAE and Oman, certified by HMA, certificate number HMA-2291X, FDA number 98765-432, barcode 6291234567890, available through Retail"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "kitkat", "companies": None},
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "halal_status": "Halal",
                "sold_in": ["UAE", "Oman"],
                "cert_bodies": ["HMA"],
                "cert_numbers": ["HMA-2291X"],
                "fda_numbers": ["98765-432"],
                "barcodes": ["6291234567890"],
                "marketplace": ["Retail"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 9, "note": "every filter field at once alongside a named product"},
    },
    {
        "inputs": {"question": "Find Oreo, Fod category, Snacks and Confectionry, halal, sold in Malasia, Indonisia and Bruni, certified by Jakim and Hfce, FDA reg 55512-009, barcode 9556001234567, marketplace industry"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "oreo", "companies": None},
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "halal_status": "Halal",
                "sold_in": ["Malaysia", "Indonesia", "Brunei"],
                "cert_bodies": ["JAKIM", "HFCE"],
                "fda_numbers": ["55512-009"],
                "barcodes": ["9556001234567"],
                "marketplace": ["Industry"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 8, "note": "eight filters, seven needing a different correction"},
    },
    {
        "inputs": {"question": "Find Pringles Original, Food, Snacks & Confectionery, halal, sold in usa and canada, certified by IFANCA, cert number US-77120, FDA number 33344-555, barcode 0016000123456, retail"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "pringles original", "companies": None},
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "halal_status": "Halal",
                "sold_in": ["USA, Canada"],
                "cert_bodies": ["IFANCA"],
                "cert_numbers": ["US-77120"],
                "fda_numbers": ["33344-555"],
                "barcodes": ["0016000123456"],
                "marketplace": ["Retail"],
            },
            "forbidden_terms": ["16000123456"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 9, "note": "usa and canada is one stored value, not two"},
    },
    {
        "inputs": {"question": "Is Nestle Milo, Beverage category, Tea & Coffee, sold in Egypt, Jordan and Lebanon, certified by HMA and IFANCA, cert numbers EG-1120 and US-9931, FDA 77788-999, barcodes 6221031492015 and 6221031492022, foodservice bulk, halal?"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "milo", "companies": ["Nestle"]},
            "filter_args": {
                "category_l1": "Beverage",
                "category_l2": "Tea & Coffee",
                "sold_in": ["Egypt", "Jordan", "Lebanon"],
                "cert_bodies": ["HMA", "IFANCA"],
                "cert_numbers": ["EG-1120", "US-9931"],
                "fda_numbers": ["77788-999"],
                "barcodes": ["6221031492015", "6221031492022"],
                "marketplace": ["FoodService - Bulk"],
            },
            "forbidden_filter_keys": ["halal_status"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 8, "note": "eight filters with multi-values in four of them, and halal is still the question"},
    },
    {
        "inputs": {"question": "FIND TWIX, FOOD, SNACKS & CONFECTIONERY, HALAL, SOLD IN UK AND SOUTH AFRICA, CERTIFIED BY SANHA AND HFCE, CERT NO ZA-4412, BARCODE 6001087001234, RETAIL"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "twix", "companies": None},
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "halal_status": "Halal",
                "sold_in": ["UK", "South Africa"],
                "cert_bodies": ["SANHA South Africa", "HFCE"],
                "cert_numbers": ["ZA-4412"],
                "barcodes": ["6001087001234"],
                "marketplace": ["Retail"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 8, "note": "all caps; canonical casing produced but the cert number stays verbatim"},
    },
    {
        "inputs": {"question": "Show me any products, Non-food, General Cosmetic, halal, sold in Turkey and Egypt, certified by HQC Croatia, barcode 8690123456789, direct marketing"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": None,
            "filter_args": {
                "category_l1": "Non-food",
                "category_l2": "General Cosmetic",
                "halal_status": "Halal",
                "sold_in": ["Turkey", "Egypt"],
                "cert_bodies": ["HQC Croatia"],
                "barcodes": ["8690123456789"],
                "marketplace": ["Direct Marketing"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 7, "note": "seven filters with only filler for a product; keyword_args must stay null"},
    },
    {
        "inputs": {"question": "Find KitKat sold in Nigeria and Bangladesh, certified by MUIS Singapore, Food category, Snacks & Confectionery, barcode 8901234567890, retail"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "kitkat", "companies": None},
            "filter_args": {
                "sold_in": ["Nigeria", "Bangladesh"],
                "cert_bodies": ["MUIS Singapore"],
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "barcodes": ["8901234567890"],
                "marketplace": ["Retail"],
            },
            "forbidden_filter_keys": ["halal_status"],
            "forbidden_terms": ["Algeria", "South Asia", "JAKIM", "IFANCA"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "note": "three values absent from the canonical lists must pass through unchanged"},
    },
    {
        "inputs": {"question": "Nutella under 10 dollars, certified after 2021, Food category, Sauce & Paste, sold in Italy and Spain, certified by HFCE, barcode 8001234567890, retail"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "nutella", "companies": None},
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Sauce & Paste",
                "sold_in": ["Italy", "Spain"],
                "cert_bodies": ["HFCE"],
                "barcodes": ["8001234567890"],
                "marketplace": ["Retail"],
            },
            "forbidden_filter_keys": ["halal_status", "cert_numbers", "fda_numbers"],
            "forbidden_terms": ["10 dollar", "2021", "$10"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "note": "price and date have no field and must be dropped, not forced elsewhere"},
    },
    {
        "inputs": {"question": "sold in Kazakhstan — I'm after Oreo, it should be halal, the full barcode is 8076809529433, Food category, General Food I think, and retail"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "oreo", "companies": None},
            "filter_args": {
                "sold_in": ["Kazakhstan"],
                "halal_status": "Halal",
                "barcodes": ["8076809529433"],
                "category_l1": "Food",
                "category_l2": "General Food",
                "marketplace": ["Retail"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "note": "filters stated out of order and interleaved with the product"},
    },
    {
        "inputs": {"question": "hey so I'm putting a hamper together for my neighbours, nothing fancy, I want some KitKat in there, it needs to be halal obviously, food category, snacks and confectionery, something you can actually buy in the UK, and if possible certified by HMA"},
        "outputs": {
            "expected_tool": KEYWORD,
            "keyword_args": {"norm_name": "kitkat", "companies": None},
            "filter_args": {
                "halal_status": "Halal",
                "category_l1": "Food",
                "category_l2": "Snacks & Confectionery",
                "sold_in": ["UK"],
                "cert_bodies": ["HMA"],
            },
            "forbidden_filter_keys": ["barcodes", "cert_numbers", "fda_numbers", "marketplace"],
            "forbidden_terms": ["hamper", "neighbour"],
        },
        "metadata": {"category": "heavy_filters", "filter_count": 5, "note": "five filters buried in casual prose rather than listed"},
    },
    {
        "inputs": {"question": "show me halal products, actually include mushbooh ones too, category Food, subcategory Dairy, sold in India, certified by HFCI India, barcode 8901234500001, retail"},
        "outputs": {
            "expected_tool": [KEYWORD, DIRECT],
            "keyword_args": None,
            "filter_args": {
                "category_l1": "Food",
                "category_l2": "Dairy",
                "sold_in": ["India"],
                "cert_bodies": ["HFCI India"],
                "barcodes": ["8901234500001"],
                "marketplace": ["Retail"],
            },
        },
        "metadata": {"category": "heavy_filters", "filter_count": 6, "known_ambiguity": True, "note": "two statuses requested but the field holds one; clarifying is also valid"},
    },
    

    {
        "inputs": {"question": "Is Nestle chocolate halal?"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "Nestle chocolate",
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
        },
        "metadata": {"category": "negative_routing", "note": "chocolate is generic, so this is semantic with the brand kept in the text"},
    },
    {
        "inputs": {"question": "Show me halal Nestle drinks sold in the UK"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "Nestle drinks",
            "filter_args": {"halal_status": "Halal", "sold_in": ["UK"]},
            "forbidden_filter_keys": ["category_l1", "category_l2"],
        },
        "metadata": {"category": "negative_routing", "note": "drinks carries meaning, unlike products, so it must be embedded"},
    },
    
    {
        "inputs": {"question": "Find halal chocolate sold in UAE"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "chocolate",
            "filter_args": {"halal_status": "Halal", "sold_in": ["UAE"]},
            "forbidden_filter_keys": ["category_l1", "category_l2"],
        },
        "metadata": {"category": "negative_routing", "note": "a generic word plus filters is still semantic; the word carries meaning"},
    },
    {
        "inputs": {"question": "Show me products from Nestle"},
        "outputs": {
            "expected_tool": [SEMANTIC, KEYWORD],
            "semantic_query": "Nestle products",
            "keyword_args": {"norm_name": None, "companies": ["Nestle"]},
            "filter_args": None,
            "forbidden_filter_keys": ["halal_status", "category_l1", "category_l2"],
        },
        "metadata": {"category": "negative_routing", "known_ambiguity": True, "note": "company alone with no filters and no descriptor"},
    },
    {
        "inputs": {"question": "something rich in iron that helps with low energy"},
        "outputs": {
            "expected_tool": SEMANTIC,
            "semantic_query": "products rich in iron that help with low energy",
            "filter_args": None,
            "forbidden_filter_keys": ["category_l1", "category_l2", "halal_status"],
        },
        "metadata": {"category": "negative_routing", "note": "purely conceptual, no product or brand"},
    },
    {
        "inputs": {"question": "What is halal certification and who issues it?"},
        "outputs": {"expected_tool": DIRECT},
        "metadata": {"category": "negative_routing", "note": "general knowledge; no tool at all"},
    },
    {
        "inputs": {"question": "asdkjh qwe zxcvb"},
        "outputs": {"expected_tool": DIRECT},
        "metadata": {"category": "negative_routing", "note": "no signal; must not fabricate a norm_name"},
    },
]

dataset_name = "Halal One Agent: Keyword Search (Tool Arguments) 3.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(dataset_id=dataset.id, examples=examples)
    print(f"Successfully generated dataset:{dataset_name}")


# import asyncio
# asyncio.run(generate_dataset())
