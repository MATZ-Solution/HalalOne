import asyncio

from config.langsmith_client import get_langsmith_client

examples = [
    # type_a — 9 messages, ~257 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": "Hey, I've got a few snacks to check today. Is Skittles halal?"},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Skittles shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Is M&M's halal?"},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for M&M\'s in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "What about Kellogg's Corn Flakes, is that halal?"},
                {"role": 'assistant', "content": '{"response": "Kellogg\'s Corn Flakes does appear as halal certified, with no pork-derived ingredients listed.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Quick one — is Lay's Classic Salted halal?"},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Lay\'s Classic Salted shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Is Pringles Original halal? Also, which company makes it, and is it sold in the US?'},
            ],
        },
    },
    # type_b — 11 messages, ~298 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": 'Hey! Just restocking a few things today, might ask about a couple different snacks.'},
                {"role": 'assistant', "content": '{"response": "I’m glad you’re restocking! Feel free to ask about any snacks you need—happy to help you find halal options.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'By the way, thanks for checking these for me.'},
                {"role": 'assistant', "content": '{"response": "Take your time! I\'m here whenever you want to check another product.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Is Nutella halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Nutella shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'This is really helpful, appreciate it.'},
                {"role": 'assistant', "content": '{"response": "Glad it\'s helpful \\u2014 ready whenever you are.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'What about Twix, is that halal?'},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for Twix in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Before we wrap up can you check if Milka is halal?"},
            ],
        },
    },
    # type_a — 9 messages, ~262 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": 'Okay, running through a short list today. Is Ferrero Rocher halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Ferrero Rocher shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Is Reese's halal?"},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for Reese\'s in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'What about Cadbury Dairy Milk, is that halal?'},
                {"role": 'assistant', "content": '{"response": "Cadbury Dairy Milk does appear as halal certified, with no pork-derived ingredients listed.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Quick one is Skittles halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Skittles shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Is Hershey's Kisses halal?"},
            ],
        },
    },
    # type_b — 11 messages, ~307 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": "Hi there! Planning out a few groceries, so I'll ask about a couple things."},
                {"role": 'assistant', "content": '{"response": "No worries at all, happy to help \\u2014 let me know what\'s next.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Okay, one more thing on my mind before the next one.'},
                {"role": 'assistant', "content": '{"response": "Take your time! I\'m here whenever you want to check another product.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Is Lindt Dark Chocolate halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Lindt Dark Chocolate shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'By the way, thanks for checking these for me.'},
                {"role": 'assistant', "content": '{"response": "Glad it\'s helpful \\u2014 ready whenever you are.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "What about Lay's Classic Salted, is that halal?"},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for Lay\'s Classic Salted in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "One last thing is Reese's Peanut Butter Cups halal?"},
            ],
        },
    },
    # type_a — 9 messages, ~258 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": "Starting a short list today, Is Toblerone halal?"},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Toblerone shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Is Cadbury Dairy Milk halal?'},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for Cadbury Dairy Milk in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'What about Maggi noodles, is that halal?'},
                {"role": 'assistant', "content": '{"response": "Maggi noodles does appear as halal certified, with no pork-derived ingredients listed.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Quick one is Oreo halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Oreo shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Is Skittles halal?"},
            ],
        },
    },
    # type_b — 11 messages, ~290 tokens
    {
        "inputs": {
            "history": [
                {"role": 'user', "content": 'Hey, quick pantry check today, a few questions coming up.'},
                {"role": 'assistant', "content": '{"response": "No worries at all, happy to help \\u2014 let me know what\'s next.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": "Hope you're having a good day so far!"},
                {"role": 'assistant', "content": '{"response": "Take your time! I\'m here whenever you want to check another product.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Is Twix halal?'},
                {"role": 'assistant', "content": '{"response": "Yes \\u2014 Twix shows up as halal certified in our records, so it should be fine.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'By the way, thanks for checking these for me.'},
                {"role": 'assistant', "content": '{"response": "Glad it\'s helpful \\u2014 ready whenever you are.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'What about Maggi noodles, is that halal?'},
                {"role": 'assistant', "content": '{"response": "I couldn\'t find a certified match for Maggi noodles in our database, so I can\'t confirm its status \\u2014 worth checking the packaging directly.", "matched": [], "relevant": []}'},
                {"role": 'user', "content": 'Last question before I go is Ferrero Rocher halal?'},
            ],
        },
    },
]

dataset_name = "Halal One Agent: Task Completion 1.1"


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
