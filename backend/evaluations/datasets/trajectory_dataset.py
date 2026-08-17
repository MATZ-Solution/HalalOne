from config.langsmith_client import get_langsmith_client

examples = [
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
    {
        "inputs": {
            "question": "Show me all halal certified products in Pakistan"
        },
        "outputs": {
            "halal_status": "Halal"
        },
    },
    {
        "inputs": {
            "question": "Is the product with barcode 235726 halal?"
        },
        "outputs": {
            "barcodes": ["235726"]
        },
    },
    {
        "inputs": {
            "question": "Is the product with certification number 2A22782D70 halal?"
        },
        "outputs": {
            "cert_numbers": ["2A22782D70"]
        },
    },
    {
        "inputs": {
            "question": "Find the halal product with FDA number 12345-678"
        },
        "outputs": {
            "fda_numbers": ["12345-678"]
        },
    },
    {
        "inputs": {
            "question": "Show me haram products from Nestle"
        },
        "outputs": {
            "halal_status": "Haram"
        },
    },
    {
        "inputs": {
            "question": "Find me the mushbooh product with barcode 8901234567?"
        },
        "outputs": {
            "halal_status": "Mushbooh",
            "barcodes": ["8901234567"]
        },
    },

]

# create the dataset
dataset_name = "Halal One Agent: Node 2 (Search Node Trajectory Dataset) 1.1"

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