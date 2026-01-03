import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# --- IMPORTS FIX ---
try:
    # Naye versions ke liye
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    # Agar structure alag hai (Fallback)
    from langchain.agents import AgentExecutor
    from langchain.agents.tool_calling_agent.base import create_tool_calling_agent

from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

app = FastAPI()

# --- CONFIGURATION ---
DEFAULT_MODEL = "qwen2.5:3b" # Ensure this model is pulled on the server

# --- TOOLS ---
search_tool = DuckDuckGoSearchRun()
tools = [search_tool]

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = DEFAULT_MODEL
    enable_web_search: bool = False
    temperature: float = 0.5

@app.get("/")
def home():
    return {"status": "Online", "mode": "LangChain Fixed Agent"}

@app.post("/generate")
async def generate_response(request: QueryRequest):
    
    # 1. LLM Initialize (Streaming ON)
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        keep_alive="5m"
    )

    async def response_generator():
        try:
            # === MODE A: AGENTIC SEARCH (INTERNET ON) ===
            if request.enable_web_search:
                
                # Prompt Template for Agent
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful assistant. Use the search tool if the user asks for current information. If not needed, answer directly."),
                    ("placeholder", "{chat_history}"),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])
                
                # Agent Construction
                agent = create_tool_calling_agent(llm, tools, prompt_template)
                agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

                # Streaming the Agent's Final Answer
                # 'astream_events' is best for getting tokens in real-time
                async for event in agent_executor.astream_events(
                    {"input": request.prompt}, version="v1"
                ):
                    kind = event["event"]
                    # Hum sirf final LLM generation wala text user ko bhejenge
                    if kind == "on_chat_model_stream":
                        # Check agar ye tool call nahi hai, balki final answer hai
                        content = event["data"]["chunk"].content
                        if content:
                            yield content
            
            # === MODE B: FAST CODING (DIRECT LLM) ===
            else:
                messages = [
                    SystemMessage(content="You are an expert coding assistant."),
                    HumanMessage(content=request.prompt)
                ]
                # Direct streaming from LLM is much faster
                async for chunk in llm.astream(messages):
                    yield chunk.content

        except Exception as e:
            yield f"\n[Server Error: {str(e)}]"

    return StreamingResponse(response_generator(), media_type="text/plain")