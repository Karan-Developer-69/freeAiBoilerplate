import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Imports
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from duckduckgo_search import DDGS

app = FastAPI()

# --- SEARCH TOOL (Fixed) ---
@tool
def web_search(query: str) -> str:
    """Search the internet for current prices, news, and real-time info."""
    try:
        # 3 Results fetch karenge
        results = DDGS().text(query, max_results=3)
        if results:
            return "\n".join([f"Title: {r['title']}\nSnippet: {r['body']}" for r in results])
        return "No results found."
    except Exception as e:
        return f"Search Error: {str(e)}"

tools = [web_search]

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "qwen2.5:3b"
    enable_web_search: bool = False
    temperature: float = 0.5

@app.post("/generate")
async def generate_response(request: QueryRequest):
    
    # 1. LLM Setup
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        keep_alive="5m"
    )

    async def response_generator():
        try:
            # === SCENARIO A: AGENT MODE (INTERNET) ===
            if request.enable_web_search:
                
                # Prompt ko simple banaya taaki 'NoneType' error na aaye
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant with access to the internet. "
                               "Use the 'web_search' tool ONLY if the user asks for real-time information (like prices, news). "
                               "If the user asks a general question, answer directly. "
                               "After searching, provide a summary of the results."),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"), # Zaroori hai tool calling ke liye
                ])
                
                # Agent Construction
                agent = create_tool_calling_agent(llm, tools, prompt_template)
                
                # Agent Executor with Error Handling
                agent_executor = AgentExecutor(
                    agent=agent, 
                    tools=tools, 
                    verbose=True, # Logs on rakho debugging ke liye
                    handle_parsing_errors=True # <-- YE CRASH ROKEGA
                )

                # Streaming
                async for event in agent_executor.astream_events(
                    {"input": request.prompt}, version="v1"
                ):
                    kind = event["event"]
                    # Sirf final text user ko bhejo
                    if kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield chunk.content

            # === SCENARIO B: FAST MODE (DIRECT) ===
            else:
                messages = [
                    SystemMessage(content="You are a coding and logic assistant."),
                    HumanMessage(content=request.prompt)
                ]
                async for chunk in llm.astream(messages):
                    yield chunk.content

        except Exception as e:
            yield f"\n[Critical Error: {str(e)}]"

    return StreamingResponse(response_generator(), media_type="text/plain")