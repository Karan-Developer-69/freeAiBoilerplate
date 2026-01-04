import os
import logging
import asyncio
from typing import Annotated, TypedDict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# --- Async & Network ---
import httpx
# FIX: Use standard DDGS and asyncio for non-blocking execution
from duckduckgo_search import DDGS 
from bs4 import BeautifulSoup

# --- LangChain / AI Core ---
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# --- LangGraph (The Brain) ---
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# --------------------------------------------------------------------------------------
# 1. Configuration & Global State
# --------------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GenAI-Agent")

# Model: Use a smart model suitable for tool calling (qwen2.5 or llama3.1)
MODEL_NAME = "qwen2.5:3b" 
BASE_URL = "http://localhost:11434"

# Global HTTP Client
http_client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await http_client.aclose()

app = FastAPI(title="GenAI Advanced Agent", version="2.1", lifespan=lifespan)

# --------------------------------------------------------------------------------------
# 2. Advanced Tools (Fixed for Latest DuckDuckGo)
# --------------------------------------------------------------------------------------

@tool
async def web_search(query: str) -> str:
    """
    Search the web for latest information, technical docs, or news.
    Returns top 5 results with snippets and URLs.
    """
    # Helper function to run sync library in async environment
    def run_sync_search(q):
        try:
            with DDGS() as ddgs:
                # Latest version returns a list of dicts directly
                return list(ddgs.text(q, max_results=5))
        except Exception as e:
            return str(e)

    logger.info(f"🔎 Searching for: {query}")
    try:
        # Offload sync task to a separate thread to keep server fast
        results = await asyncio.to_thread(run_sync_search, query)
        
        if isinstance(results, str): # Check if error occurred
            return f"Search Error: {results}"
        
        if not results:
            return "No results found on the web."
        
        # Format cleanly for the LLM
        output = []
        for r in results:
            title = r.get('title', 'No Title')
            link = r.get('href', '#')
            body = r.get('body', '')
            output.append(f"Title: {title}\nLink: {link}\nSnippet: {body}\n---")
        return "\n".join(output)
    except Exception as e:
        return f"Search System Error: {str(e)}"

@tool
async def read_webpage(url: str) -> str:
    """
    Reads the full content of a specific URL. 
    Use this if the search snippet is not enough and you need deep technical details.
    """
    logger.info(f"📖 Reading page: {url}")
    try:
        # User-Agent to avoid blocking
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = await http_client.get(url, headers=headers)
        
        if resp.status_code != 200:
            return f"Failed to load page: Status {resp.status_code}"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Clean up unnecessary tags
        for tag in soup(["script", "style", "nav", "footer", "svg"]):
            tag.decompose()
        
        text = soup.get_text(separator="\n")
        
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit text length to avoid context overflow (approx 4000 chars)
        return clean_text[:4000] + "...(truncated)"
    except Exception as e:
        return f"Scraping Error: {str(e)}"

tools = [web_search, read_webpage]

# --------------------------------------------------------------------------------------
# 3. LangGraph Agent Architecture (Reasoning Engine)
# --------------------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "add_messages"]

# Initialize LLM with Tools
llm = ChatOllama(
    model=MODEL_NAME,
    base_url=BASE_URL,
    temperature=0.3, # Lower temp for more precise code/facts
    keep_alive="1h"
).bind_tools(tools)

# System Prompt - Formatting & Behavior Rules
SYSTEM_PROMPT = """You are an advanced GenAI technical assistant. 

CORE RULES:
1. **Latest Info:** Always use 'web_search' for current events, libraries, or news. Do not guess.
2. **Deep Dive:** If search snippets are too short, use 'read_webpage' to get full documentation/code.
3. **Format:** 
   - Start your response with a brief summary.
   - Use headings (##) for sections.
   - For code, ALWAYS use this XML format: 
     <code lang="python">
     print("code here")
     </code>
   - NEVER use markdown triple backticks (```) for code.
4. **Memory:** If the user asks "continue" or "more", check the previous conversation history.

Think step-by-step before answering.
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
workflow.add_edge("tools", "agent")

# Memory (Checkpointer)
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)

# --------------------------------------------------------------------------------------
# 4. API Handling & Streaming
# --------------------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    thread_id: str = Field(..., description="Unique ID for conversation (e.g., 'session-1')")

async def event_generator(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=query)]}
    
    yield "🤖 **GenAI Agent Initialized...**\n\n"
    
    try:
        async for event in app_graph.astream_events(inputs, config=config, version="v1"):
            event_type = event["event"]
            
            # 1. Agent Thinking (Stream Tokens)
            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    yield chunk

            # 2. Tool Start (Thinking Process)
            elif event_type == "on_tool_start":
                tool_name = event['name']
                yield f"\n\n🤔 **Thinking:** Searching external sources using `{tool_name}`...\n\n"

            # 3. Tool End (Success)
            elif event_type == "on_tool_end":
                output = str(event['data'].get('output'))[:150] # Preview data
                yield f"✅ **Data Found:** {output}...\n\n"

    except Exception as e:
        yield f"\n❌ **System Error:** {str(e)}"

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        event_generator(req.query, req.thread_id),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)