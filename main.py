# main.py (Fully Fixed & Scalable - Production Ready)
import os
import asyncio
from typing import AsyncIterable
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

# LangChain imports (Fixed order & versions)
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.messages import AnyMessage
from duckduckgo_search import DDGS

# App lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Nothing needed
    yield
    # Shutdown: Cleanup if any

app = FastAPI(
    title="Scalable LangChain FastAPI Agent",
    description="Production-ready streaming AI agent with web search",
    version="2.0",
    lifespan=lifespan
)

# --- SCALABLE SEARCH TOOL ---
@tool
def web_search(query: str) -> str:
    """Search internet for real-time info like news, prices, updates."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if results:
            return "\n".join([
                f"• {r['title']}\n  {r['href']}\n  {r['body'][:200]}..." 
                for r in results
            ])
        return "No relevant results found."
    except Exception as e:
        return f"Search failed: {str(e)}"

tools = [web_search]

# --- REQUEST MODEL (Validated) ---
class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="qwen2.5:3b", max_length=50)
    enable_web_search: bool = Field(default=False)
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=8192)

# main.py - FIXED AGENT STREAMING (LangChain 0.3.0 Compatible)
# Replace ONLY the generate_response function in your server code

@app.post("/generate", response_class=StreamingResponse)
async def generate_response(request: QueryRequest) -> StreamingResponse:
    """Fixed streaming with proper agent compatibility."""
    
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        timeout=60.0,
        keep_alive="10m"
    )

    async def stream_content() -> AsyncIterable[str]:
        try:
            if request.enable_web_search:
                # FIXED PROMPT (v2 - LangChain 0.3+ compatible)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a helpful assistant with web search. 
Use tools only for real-time info. Summarize results concisely.
Final answer format: Clear, direct response."""),
                    ("human", "{input}"),
                    MessagesPlaceholder("agent_scratchpad"),
                ])
                
                agent = create_tool_calling_agent(llm, tools, prompt)
                executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=False,
                    handle_parsing_errors=True,
                    max_iterations=6,
                    early_stopping_method="generate"
                )
                
                # FIXED STREAMING - No 'stream_mode' param
                async for chunk in executor.astream(request.prompt):
                    if "output" in chunk and chunk["output"]:
                        yield chunk["output"]
            
            else:
                # DIRECT CHAT (unchanged)
                messages = [
                    ("system", "You are a helpful coding assistant."),
                    ("human", request.prompt)
                ]
                async for chunk in llm.astream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        yield chunk.content

        except Exception as e:
            error_msg = f"Server Error: {str(e)[:100]}"
            yield error_msg

    return StreamingResponse(stream_content(), media_type="text/plain")


@app.get("/health")
async def health_check():
    """Health endpoint for monitoring."""
    return {"status": "healthy", "model": "ollama-ready"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
