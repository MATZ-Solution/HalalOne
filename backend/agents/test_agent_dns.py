# from agents.main_agent import llm
# from langchain.agents import create_agent

# agent = create_agent(name= "Halalify Agent", model = llm)


# async def run_agent(query):
#     response = await agent.ainvoke(
#         {"messages": [
#             {"role": "user", "content": query}
#             ]}
#     )
    
#     return response['messages'][-1].content


# response = await run_agent("Hello how are you?")
# print("response", response)