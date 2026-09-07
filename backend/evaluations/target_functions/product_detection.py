import json

from agents.langgraph_agent.main_langgraph_agent import search_agent


# Target function: runs the full HalalOne search agent on the user prompt
# and returns the message trajectory along with parsed product results.
async def run_product_detection(inputs: dict) -> dict:
    # 1. Extract messages or query string from inputs
    messages = inputs.get("messages", [])
    if not messages:
        question = inputs.get("question", "")
        if question and question.strip():
            messages = [{"role": "user", "content": question}]
        else:
            return {
                "messages": [],
                "matched": [],
                "relevant": [],
                "retrieved_products": [],
                "response_text": "",
            }

    # 2. Invoke the compiled LangGraph search agent
    results = await search_agent.ainvoke({"messages": messages})

    res_messages = results.get("messages", [])
    if not res_messages:
        return {
            "messages": [],
            "matched": [],
            "relevant": [],
            "retrieved_products": [],
            "response_text": "",
        }

    # 3. Parse final assistant message JSON payload (contains response, matched, relevant)
    matched_products = []
    relevant_products = []
    response_text = ""

    last_message = res_messages[-1]
    final_content = getattr(last_message, "content", "")

    if isinstance(final_content, str):
        try:
            data = json.loads(final_content)
            matched_products = data.get("matched") or []
            relevant_products = data.get("relevant") or []
            response_text = data.get("response") or ""
        except (json.JSONDecodeError, TypeError, AttributeError):
            response_text = final_content
    elif isinstance(final_content, dict):
        matched_products = final_content.get("matched") or []
        relevant_products = final_content.get("relevant") or []
        response_text = final_content.get("response") or ""

    # All products returned (both exact matched and relevant)
    retrieved_products = matched_products + relevant_products

    return {
        "messages": res_messages,
        "matched": matched_products,
        "relevant": relevant_products,
        "retrieved_products": retrieved_products,
        "response_text": response_text,
    }
