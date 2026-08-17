from config.langsmith_client import get_langsmith_client

# Create dataset
examples = [
    # Existing examples
    {
        "inputs": {"messages": [{"role": "user", "content": "Hey there, how are you doing?"}]},
        "outputs": {"classification": "response_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Is E101 halal? Please provide it's halal certificate"}]},
        "outputs": {"classification": "search_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "I live in London and here I have difficulty finding halal options in consumer goods and other things. I am so frustrated and can't find a solution."}]},
        "outputs": {"classification": "response_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Is kitkat halal? Product certificate is 12736712312 and usually sold in middle Eastern countries and has fda number 823782387"}]},
        "outputs": {"classification": "search_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Can you find me some halal gummy bears without gelatin?"}]},
        "outputs": {"classification": "search_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "What does halal mean exactly?"}]},
        "outputs": {"classification": "response_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Find halal cheese brands available in the US"}]},
        "outputs": {"classification": "search_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "I'm so tired of checking every ingredient label, it's exhausting"}]},
        "outputs": {"classification": "response_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Search for halal marshmallows with kosher gelatin"}]},
        "outputs": {"classification": "search_node"},
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "Thank you for your help earlier, I really appreciate it"}]},
        "outputs": {"classification": "response_node"},
    },
]

# create the dataset
dataset_name = "Halal One Agent: Node 1 (Intent Classifier Dataset)"


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
