
import uuid
import json
import asyncio
from langchain.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import RetryPolicy, default_retry_on, TimeoutPolicy
from .models.models import SearchAgentState, FinalAnswerInput
from .nodes.node import classify_intent, search_node, tool_node, response_node, default_error_handler
from log.logger import logger

workflow = StateGraph(SearchAgentState)
workflow.set_node_defaults(
    retry_policy=RetryPolicy(max_attempts=3, retry_on=default_retry_on), error_handler=default_error_handler
)

workflow.add_node(
    "classify_intent",
    classify_intent,
)
workflow.add_node("search_node", search_node)
workflow.add_node("tool_node", tool_node)
workflow.add_node("response_node", response_node)

workflow.add_edge(START, "classify_intent")
workflow.add_edge("search_node", "tool_node")
workflow.add_edge("tool_node", "response_node")
workflow.add_edge("response_node", END)


checkpointer = InMemorySaver()
search_agent = workflow.compile(checkpointer = checkpointer)


def format_results(product_list: list) -> str:
    for i, product in enumerate(product_list, 1):
        logger.info(f"{i}. Product name: {product.norm_name} Companies: {' '.join(product.companies)} Certified By: {' '.join(product.cert_bodies)}") 

async def run_agent(query:str, config: dict = None)-> dict:
    if not query:
        return {"response": "Please enter a valid query", "documents": []}
    result = await asyncio.to_thread(
        search_agent.invoke,
        {"user_prompt": query, "messages": [HumanMessage(query)], "search_results": []},
        config=config or {"configurable": {"thread_id": str(uuid.uuid4())}}
    )
    final = FinalAnswerInput.model_validate_json(result["messages"][-1].content)
    response = final.response
    products = final.products
    # print(f"""{'='*25} RESPONSE {'='*25}
    # {final.response}
    # """)
    # format_results(final.products)

    return {"response": response, "documents": products} 



async def stream_agent(query: str, config: dict = None):
    if not query:
        yield {"response": "Please enter a valid query", "documents": []}  # ✅ yield the error
        return  # Stop execution
    final_result = {"response": "", "documents": []}

    async for chunk in search_agent.astream(
        {
            "user_prompt": query, 
            "messages": [HumanMessage(query)], 
            "search_results": []
        },
        stream_mode=["messages", "custom", "updates"],
        version = "v2",
        config=config or {"configurable": {"thread_id": str(uuid.uuid4())}},
    ):

        if chunk["type"] == "updates":
            for node_name, state in chunk["data"].items():
                if node_name == "__default_error_handler__" and state:
                    messages = state.get("messages", [])
                    if messages:
                        last_message = messages[-1]
                        result = json.loads(last_message.content) 
                        response = result.get("response", "Some error occured, please try again.")
                        products = result.get("products", [])
                        yield {"type": "results", "response": response, "documents": products}
                        return
        elif chunk["type"] == "messages":
            message, metadata = chunk["data"]
            node_name = metadata.get("langgraph_node", "")
            if node_name == "response_node" and message.content:
                result = json.loads(message.content)
                if result["response"]:
                    response = result["response"]
                    products = result.get("products", [])
                    yield {"type": "results", "response": response, "documents": products}
                    return
            content_blocks = getattr(message, 'content_blocks', [])
            for block in content_blocks:
                if block.get("type") == "reasoning":
                    reasoning = block.get("reasoning")
                    if reasoning:
                        # logger.info(f"[NODE]: {node_name} [REASONING]: {reasoning}")
                        yield {"type": "reasoning", "node": node_name, "reasoning": reasoning}      
            
            # handler for response_node streaming
            # logger.info(f"[NODE]: {node_name} [CONTENT]: {message.content}")                    
            tool_calls = getattr(message, 'tool_calls', [])
            for tool_call in tool_calls:
                name = tool_call.get("name")
                args = tool_call.get("args")
                if name == "KeywordFilterSearch":
                    has_keywords = bool(args.get("keyword_args"))
                    has_filters = bool(args.get("filter_args"))
                    msg = None
                    if has_keywords and has_filters:
                        msg = "Searching keywords"
                    elif not has_keywords and has_filters:
                        msg = "Applying filters"
                    else:
                        msg = "Searching relevant products"
                    # logger.info(f"[NODE]: {node_name}, [TOOL]: {name}, [ARGS]: {args}, [MESSAGE]: {msg}")
                    yield {"type": "tool_status", "node": node_name, "message": msg, "tool": name, "args": args}
                elif name == "SemanticFilterSearch":
                    # logger.info(f"[NODE]: {node_name}, [TOOL]: {name}, [ARGS]: {args}")
                    yield {"type": "tool_status", "node": node_name, "message": "Performing Semantic Search", "tool": name, "args": args}
        elif chunk["type"] == "custom":
            # writer({"search_results": observation})
            search_results = chunk['data'].get("search_results", [])
            tool = chunk['data'].get('tool',"Tool Result")
            if search_results:
                yield {"type": "search_results", "search_results": search_results, "tool": tool}
        



# async def test_stream():
#     async for chunk in stream_agent("is creme brule halal?"):
#         print(f"\n\n{chunk}\n")  # Now you'll see the output

# # Run the async function
# asyncio.run(test_stream())

# while True:
#     query = input("Enter your halal search query here: ")
#     if query == "exit":
#         break
#     search_halal_products(query)
