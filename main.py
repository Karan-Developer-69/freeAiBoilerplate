import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# LangChain Imports
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

# DuckDuckGo New Library Import
from duckduckgo_search import DDGS

app = FastAPI()

# --- CONFIGURATION ---
DEFAULT_MODEL = "qwen2.5:3b"

# --- CUSTOM ROBUST SEARCH TOOL ---
# Hum khud ka tool banayenge jo error aane par crash na ho
@tool
def web_search(query: str) -> str:
    """Useful for searching the internet for current events, prices, and real-time information."""
    try:
        results = DDGS().text(query, max_results=3)
        if results:
            # Sirf relevant text wapas bhejo
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        return "No results found on the internet."
    except Exception as e:
        return f"Search failed due to error: {str(e)}"

tools = [web_search]

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = DEFAULT_MODEL
    enable_web_search: bool = False
    temperature: float = 0.5

@app.get("/")
def home():
    return {"status": "Online", "mode": "Fixed Agentic API"}

@app.post("/generate")
async def generate_response(request: QueryRequest):
    
    # LLM Setup
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        keep_alive="5m"
    )

    async def response_generator():
        try:
            # === MODE A: AGENTIC SEARCH (INTERNET ON) ===
            if request.enable_web_search:
                
                # Agent Prompt
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant. You have access to a web_search tool. "
                               "Use it ONLY if the user asks for current prices, news, or real-time info. "
                               "After searching, summarize the answer properly."),
                    ("placeholder", "{chat_history}"),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])
                
                # Agent Create
                agent = create_tool_calling_agent(llm, tools, prompt_template)
                
                # IMPORTANT: verbose=False rakha hai taki wo 'Serialization Error' na aaye
                agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

                # Streaming Response
                # Hum astream_events use karenge aur sirf 'final answer' filter karenge
                async for event in agent_executor.astream_events(
                    {"input": request.prompt}, version="v1"
                ):
                    kind = event["event"]
                    
                    # Jab Model Final Answer likh raha ho, tabhi user ko dikhao
                    if kind == "on_chat_model_stream":
                        # Check karte hain ki ye Tool Call ka data toh nahi hai?
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield chunk.content
            
            # === MODE B: FAST CODING (DIRECT LLM) ===
            else:
                messages = [
                    SystemMessage(content="You are an expert coding assistant. Write clean code."),
                    HumanMessage(content=request.prompt)
                ]
                async for chunk in llm.astream(messages):
                    yield chunk.content

        except Exception as e:
            # Error user ko dikhe taki debugging ho sake
            yield f"\n[System Error: {str(e)}]"

    return StreamingResponse(response_generator(), media_type="text/plain")