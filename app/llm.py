from langchain_core.messages import BaseMessage,HumanMessage,AIMessage,ToolMessage
# from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated
from dotenv import load_dotenv
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver # it store data in ram
from langgraph.prebuilt import ToolNode,tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.tools import tool
import sqlite3
import requests
load_dotenv()


class ChatState(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]   # use add_message it add one by one 

model=HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-20b",
    task="text-generation"
)

llm= ChatHuggingFace(llm=model)

# llm=ChatOpenAI()

#  tools----------------------------------------------------
#  in langchain 2 types of tools prebuilt and custom

search_tool=DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=CMJ1YK6C5ODQLHJI"
    r = requests.get(url)
    return r.json()

# make list of tools---

tools = [search_tool, get_stock_price, calculator]

#make llm tool-aware-----------

llm_with_tools = llm.bind_tools(tools)

# ------------------------------------------------

# graph node---

def chat_node(state:ChatState):
    """LLM node that may answer or request a tool call."""
    messages=state["messages"]
    response=llm_with_tools.invoke(messages)
    return {"messages":[response]}

tool_node=ToolNode(tools)  # excute tool calls

# -----
#  Checkpointer---------

conn=sqlite3.connect(database="chatbot_db",check_same_thread=False)

checkpointer=SqliteSaver(conn=conn)


# 6. Graph----------

#  add nodes----
graph=StateGraph(ChatState)

graph.add_node("chat_node",chat_node)
graph.add_node("tools",tool_node)

# add_ edges----

graph.add_edge(START,"chat_node")

graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge("tools","chat_node")
graph.add_edge("chat_node",END)

chatbot=graph.compile(checkpointer=checkpointer)


def stream_process_msg(user_input: str, threadId: str):
    config = {"configurable": {"thread_id": threadId}}

    for chunk, _ in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="messages",
    ):
        # 🧠 When the LLM starts using a tool
        if isinstance(chunk, ToolMessage):
            tool_name = getattr(chunk, "name", "unknown_tool")
            yield {"type": "tool_start", "tool": tool_name}

        # 🧠 When the tool has finished executing and LLM responds
        elif isinstance(chunk, AIMessage):
            yield {"type": "ai_message", "text": chunk.content}


            
# histrory -----------------------------------------------------
def get_conversation_history(threadId: str):
    config = {"configurable": {"thread_id": threadId}}
    snapshot = chatbot.get_state(config)   # StateSnapshot
    state = snapshot.values                # ✅ this is the dict with "messages"
    
    return [
        {"role": msg.type, "content": msg.content}
        for msg in state["messages"]
    ]

# Old threads from database------------------------------------

def retriveAllThreads():
     
   allThreads=set()

   for checkpoint in checkpointer.list(None):
    allThreads.add(checkpoint.config['configurable']['thread_id'])

   return list(allThreads)