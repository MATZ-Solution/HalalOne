from config.langsmith_client import get_langsmith_client

examples = [
    # question 1: Keyword Search Only
    {
        "inputs": {
            "question": "Hello how are you doing?"
        },
    },
    {
        "inputs": {
            "question": "Is Biryani Masala halal?"
        },
    },
    
    #  question 2: Filters Only
    {
        "inputs": {
            "question": "Show me all halal certified products in Pakistan"
        },
    },

]


# create the dataset
dataset_name = "Halal One Agent: Node 2 (Search Node Trajectory Dataset) 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(
            dataset_id=dataset.id,
            examples=examples
    )
    print(f"Successfully generated dataset:{dataset_name}")



# import asyncio
# asyncio.run(generate_dataset())
