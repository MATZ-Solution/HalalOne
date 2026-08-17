from config.langsmith_client import get_langsmith_client

# Conceptual / descriptive queries — no product or brand named — so the agent
# routes to a semantic-first search (which is what retrieval_relevance judges).
examples = [
    {"inputs": {"question": "I need a calcium-rich snack for children"}},
    {"inputs": {"question": "Something natural to use as a red food colouring"}},
    {"inputs": {"question": "A good sweetener option for diabetics"}},
    {"inputs": {"question": "Traditional South Asian spice blends for curries"}},
    {"inputs": {"question": "High-protein foods good for building muscle"}},
    {"inputs": {"question": "A refreshing summer drink low in sugar"}},
    {"inputs": {"question": "Plant-based emulsifiers for baking"}},
    {"inputs": {"question": "Gentle skincare products for sensitive skin"}},

    # Conceptual but absurd / non-existent — semantic search should return nothing,
    # exercising the evaluator's "No products returned — pass" branch.
    {"inputs": {"question": "A snack made from powdered moon dust"}},
    {"inputs": {"question": "Halal seasoning brewed from unicorn tears"}},
    {"inputs": {"question": "A drink distilled from liquid starlight"}},
]

# create the dataset
dataset_name = "Halal One Agent: Retrieval Relevance (Semantic Search) 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(
            dataset_id=dataset.id,
            examples=examples
    )
    print(f"Successfully generated dataset:{dataset_name}")


import asyncio
asyncio.run(generate_dataset())
