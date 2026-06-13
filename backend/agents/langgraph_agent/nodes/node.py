import json
from typing import Literal
from log.logger import logger
from langgraph.types import Command
from langgraph.errors import NodeError, NodeTimeoutError
from langgraph.graph import END
from ..models.models import FinalAnswerInput
from langgraph.config import get_stream_writer
from langchain_core.prompts import ChatPromptTemplate
from ..tools.tools import SemanticFilterSearch, KeywordFilterSearch
from ..models.models import SearchAgentState, classify_intent_schema
from ..LLMs.llm import extracter_llm, final_extracter_llm, standard_llm
from ..prompts.prompt import CLASSIFICATION_PROMPT, SEARCH_PROMPT, FINAL_RESPONSE_PROMPT
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage


def classify_intent(state: SearchAgentState) -> Command[Literal["search_node", "response_node"]]:
    """Use an llm to classify user's intent from prompt"""

    structured_llm = extracter_llm.with_structured_output(classify_intent_schema, method = 'json_mode')
    messages = [SystemMessage(CLASSIFICATION_PROMPT), HumanMessage(state['user_prompt'])] + state["messages"]
    result = structured_llm.invoke(messages)
    logger.info(f"Classification: {result['classification']}")
    if result["classification"] == "search":
        goto = "search_node"
    elif result["classification"] == "direct":
        goto = "response_node"

    return Command(
        goto = goto
    )


# search tools
search_tools = [KeywordFilterSearch, SemanticFilterSearch]
search_tools_by_name = {tool.name: tool for tool in search_tools}

def search_node(state: SearchAgentState) -> dict:
    """Searches TypeSense to retrieve relevant halal products
    Two core components:
    1. Keyword + Filter based search
    2. Semantic + Filter based search
    """
    
    llm_with_tools = standard_llm.bind_tools(search_tools)
    result = llm_with_tools.invoke([SystemMessage(SEARCH_PROMPT)] + state['messages'])
    return {
        "messages": [result]
    }

def tool_node(state: SearchAgentState) -> dict:
    """Performs the tool call"""
    # raise RuntimeError("Some Error occured")
    if not state["messages"][-1].tool_calls:
        return {"messages": []}
    
    # initialize the stream writer
    writer = get_stream_writer()
    search_results = []
    tool_messages = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = search_tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call['args'])
        if len(observation) == 0:
            continue
        writer({"search_results": observation, "tool": tool_call["name"]})
        search_results.append(observation)
        tool_messages.append(ToolMessage(content=json.dumps(observation), tool_call_id = tool_call["id"]))
    
    if len(search_results) == 0 or len(tool_messages) == 0:
            return {"messages": []}
    return {"messages": tool_messages, "search_results": search_results}


def response_node(state: SearchAgentState) -> dict:
    """Formats the final user-facing response"""
    
    structured_llm = final_extracter_llm.with_structured_output(FinalAnswerInput, method = "json_schema")
    prompt = ChatPromptTemplate.from_template(FINAL_RESPONSE_PROMPT)
    chain = prompt | structured_llm
    
    result = chain.invoke({"user_prompt": state['user_prompt'], "halal_search_results": state['search_results'], "conversation_history": state['messages']})

    # logger.info(f"""{'=='*25} Final Result {'=='*25}
    # {result}\n\n
    # """)
    # return the result
    return {
        "messages": [AIMessage(content=result.model_dump_json())]
    }


def default_error_handler(state: SearchAgentState):
    response_object = {"response": "Some error occured, please try again.", "products": []}
    print("Error handler triggered!")

    return Command(
        update = {"messages": [AIMessage(content=json.dumps(response_object))]},
        goto = END
    )
