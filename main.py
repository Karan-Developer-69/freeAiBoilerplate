import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import SystemMessage, HumanMessage

app = FastAPI()

# --- CONFIGURATION ---
# "qwen2.5:3b" best balance hai speed aur dimaag ka free tier ke liye.
# Agar server pe 'ollama pull qwen2.5:3b' nahi kiya hai toh kar lena.
DEFAULT_MODEL = "qwen2.5:3b" 

# --- TOOLS ---
search_tool = DuckDuckGoSearchRun()
tools = [search_tool]

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = DEFAULT_MODEL
    enable_web_search: bool = False # Yahan se tum agent on/off karoge
    temperature: float = 0.5

@app.get("/")
def home():
    return {"status": "Online", "mode": "LangChain Agentic AI"}

@app.post("/generate")
async def generate_response(request: QueryRequest):
    
    # LLM Initialize karo
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        streaming=True # LangChain streaming enable
    )

    async def response_generator():
        try:
            # CASE 1: AGENTIC MODE (SEARCH ON)
            if request.enable_web_search:
                # Agent ko batana padta hai ki wo kya hai
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", "You are a helpful AI assistant with web search capabilities. "
                               "If you need current information, use the search tool. "
                               "If the user asks for code, just write the code. "
                               "Always provide the final answer clearly."),
                    ("placeholder", "{chat_history}"),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])
                
                # Agent create karo
                agent = create_tool_calling_agent(llm, tools, prompt_template)
                agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

                # Agent ko run karo aur stream karo
                # Note: Agent streaming thoda complex hota hai, hum chunks filter karenge
                async for event in agent_executor.astream_events(
                    {"input": request.prompt}, version="v1"
                ):
                    kind = event["event"]
                    
                    # Sirf final answer (on_chat_model_stream) user ko bhejo
                    # Taki user ko "Thinking..." wale steps na dikhein (clean output)
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            yield content
                    
            # CASE 2: FAST MODE (DIRECT LLM)
            else:
                # Simple LLM Call - Super Fast
                messages = [
                    SystemMessage(content="You are an expert coding assistant."),
                    HumanMessage(content=request.prompt)
                ]
                async for chunk in llm.astream(messages):
                    yield chunk.content

        except Exception as e:
            yield f"\n[System Error: {str(e)}]"

    return StreamingResponse(response_generator(), media_type="text/plain")