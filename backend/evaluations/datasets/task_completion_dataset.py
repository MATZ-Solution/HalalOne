import asyncio

from config.langsmith_client import get_langsmith_client

examples = [
    {
        "inputs": {
            "turns": ["Is Lay's Classic Salted halal?"],
        },
    },
    {
        "inputs": {
            "turns": [
                "Is Nutella halal?",
                "Which company makes it?",
                "Is it sold worldwide?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Hi, how are you?",
                "what do you help with?",
                "Can you check if Oreo biscuits are halal?",
                "Oreo in Canada are halal too, right?",
                "Thank you!",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Show me halal chicken nuggets",
                "Actually, I meant beef nuggets, not chicken",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Show me halal certified products from Boston",
                "Just the dairy ones",
                "Which of those are sold worldwide?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "are Hershey products halal?",
                "there Kit kat too?",
                "which of their products are sold in the US?",
                "are they halal in the US too?",
                "Got it, thanks for checking",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "I'm so confused about what's halal or not these days",
                "Can you just tell me if Cadbury Dairy Milk is halal?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Is the product with barcode 235726 halal?",
                "Which certification body approved it?",
            ],
        },
    },

    # agent generated examples

    {
        "inputs": {
            "turns": ["Is McDonald's French fries halal?"],
        },
    },
    {
        "inputs": {
            "turns": [
                "Does Jell-O contain gelatin?",
                "Is that gelatin beef or pork based?",
                "So is it halal or not?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Show me halal marshmallows",
                "Wait, I actually need vegan ones too",
                "Okay show me just the vegan halal ones then",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "List halal snacks from Nestle",
                "Remove the chocolate ones from that list",
                "What's left after that?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "hey there",
                "who made you?",
                "cool, is Doritos Nacho Cheese halal?",
                "thanks a lot!",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Is Lay's halal?",
                "What about Pringles?",
                "Which one is safer for a halal diet?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Is vanilla extract halal if it contains alcohol?",
                "Are there non-alcoholic versions available?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Is KitKat halal in Canada?",
                "What about in the UK?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Which halal certification does Nestle use?",
                "Is that certification recognized internationally?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "What's the weather like today?",
                "Never mind, is Skittles halal?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "Are Oreo, KitKat, and Snickers all halal?",
                "Which of those is the safest bet?",
            ],
        },
    },
    {
        "inputs": {
            "turns": [
                "I'm not sure this is even the right place to ask, but is whey protein halal?",
                "Does it matter if it's derived from cheese-making?",
            ],
        },
    },
]

dataset_name = "Halal One Agent: Task Completion (Multi-Turn) 1.0"


async def generate_dataset():
    client = get_langsmith_client()
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(dataset_name=dataset_name)
        client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
        )
    print(f"Successfully generated dataset:{dataset_name}")

asyncio.run(generate_dataset())
