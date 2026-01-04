import os
import re
import logging
import asyncio
from typing import Annotated, Literal, TypedDict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# --- Async & Network ---
import httpx
from duckduckgo_search import AsyncDDGS
from bs4 import BeautifulSoup

# --- LangChain / AI Core ---
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# --- LangGraph (The Brain) ---
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver # In-memory DB for context

# --------------------------------------------------------------------------------------
# 1. Configuration & Global State
# --------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenAI-Agent")

# Model Configuration (Use a smart model like qwen2.5 or llama3.1)
MODEL_NAME = "qwen2.5:7b" 
BASE_URL = "http://localhost:11434"

# HTTP Client for Scraping
http_client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await http_client.aclose()

app = FastAPI(title="Advanced GenAI Agent", version="2.0", lifespan=lifespan)

# --------------------------------------------------------------------------------------
# 2. Advanced Tools (Search + Scrape)
# --------------------------------------------------------------------------------------

@tool
async def web_search(query: str) -> str:
    """
    Search the web for latest information, technical docs, or news.
    Returns top 5 results with snippets and URLs.
    """
    try:
        results = await AsyncDDGS().text(query, max_results=5)
        if not results:
            return "No results found on the web."
        
        # Format cleanly
        output = []
        for r in results:
            output.append(f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}\n---")
        return "\n".join(output)
    except Exception as e:
        return f"Search Error: {str(e)}"

@tool
async def read_webpage(url: str) -> str:
    """
    Reads the full content of a specific URL. 
    Use this if the search snippet is not enough and you need deep technical details.
    """
    try:
        resp = await http_client.get(url)
        if resp.status_code != 200:
            return f"Failed to load page: Status {resp.status_code}"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Remove scripts and styles
        for script in soup(["script", "style", "nav", "footer"]):
            script.extract()
        
        text = soup.get_text(separator="\n")
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text[:4000] + "...(truncated)" # Limit length for LLM context
    except Exception as e:
        return f"Scraping Error: {str(e)}"

tools = [web_search, read_webpage]

# --------------------------------------------------------------------------------------
# 3. LangGraph Agent Architecture (Reasoning Engine)
# --------------------------------------------------------------------------------------

# Define State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "add_messages"]

# Initialize LLM with Tools
llm = ChatOllama(
    model=MODEL_NAME,
    base_url=BASE_URL,
    temperature=0.4, # Balanced for creativity and accuracy
    keep_alive="1h"
).bind_tools(tools)

# System Prompt - The Persona & Formatting Rules
SYSTEM_PROMPT = """You are an advanced GenAI technical assistant. 

CORE RULES:
1. **Latest Info:** Always use 'web_search' for current events or tech libraries. Do not guess.
2. **Thinking:** Before answering, explain your plan briefly.
3. **Deep Dive:** If a search result looks promising but incomplete, use 'read_webpage' to get full code/docs.
4. **Code Formatting:** 
   - NEVER use markdown triple backticks (```). 
   - ALWAYS use this XML format for code:
     <code lang="python">
     print("Hello World")
     </code>
5. **Context:** If the user asks to "continue" or "more", look at the previous conversation history.

If the answer is long, structure it with headers and bullet points.
"""

# Node: Agent (Decides what to do)
async def agent_node(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    lambda state: "tools" if state["messages"][-1].tool_calls else END
)
workflow.add_edge("tools", "agent") # Loop back to agent after tool usage

# Memory (Checkpointer) - Saves state per thread_id
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)

# --------------------------------------------------------------------------------------
# 4. Request Handling & Streaming
# --------------------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    thread_id: str = Field(..., description="Unique ID for conversation history (e.g., 'user-123')")

def format_chunk(content: str) -> str:
    """Helper to ensure live streaming looks good"""
    # Real-time regex replacement could be risky, better to rely on system prompt,
    # but we can do simple cleanups here if needed.
    return content

async def event_generator(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    # User message input
    inputs = {"messages": [HumanMessage(content=query)]}
    
    try:
        # Stream events from the graph
        async for event in app_graph.astream_events(inputs, config=config, version="v1"):
            event_type = event["event"]
            
            # 1. Agent is Thinking (Streaming the token output)
            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield chunk

            # 2. Tool Start (Reasoning visible)
            elif event_type == "on_tool_start":
                tool_name = event['name']
                tool_args = event['data'].get('input')
                yield f"\n\n🤔 **Thinking:** I need to use `{tool_name}` to find info about: `{str(tool_args)}`...\n\n"

            # 3. Tool End (Observation)
            elif event_type == "on_tool_end":
                output = event['data'].get('output')
                snippet = str(output)[:100].replace('\n', ' ')
                yield f"✅ **Found Data:** {snippet}...\n\n"

    except Exception as e:
        yield f"\n❌ **Error:** {str(e)}"

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        event_generator(req.query, req.thread_id),
        media_type="text/plain"
    )

@app.get("/health")
def health():
    return {"status": "GenAI Agent Ready", "model": MODEL_NAME}

# --------------------------------------------------------------------------------------
# Run Server
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Use proper host for network access
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)