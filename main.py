from typing import AsyncIterable
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from duckduckgo_search import DDGS

app = FastAPI()

@tool
def web_search(query: str) -> str:
    """Search internet for real-time info like news, prices, events."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No relevant results found."
        lines = []
        for r in results:
            title = r.get("title", "")
            href = r.get("href", "")
            body = r.get("body", "")[:200]
            lines.append(f"Title: {title}\nURL: {href}\nSnippet: {body}...")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {str(e)}"

class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="qwen2.5:3b", max_length=50)
    enable_web_search: bool = Field(default=False)
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)

@app.post("/generate")
async def generate_response(request: QueryRequest):
    llm = ChatOllama(
        model=request.model,
        temperature=request.temperature,
        keep_alive="10m",
        timeout=60.0,
    )

    async def streamer() -> AsyncIterable[str]:
        try:
            # ---- MODE 1: DIRECT CHAT (already working) ----
            if not request.enable_web_search:
                messages = [
                    ("system", "You are a helpful, concise assistant."),
                    ("human", request.prompt),
                ]
                async for chunk in llm.astream(messages):
                    if getattr(chunk, "content", None):
                        yield chunk.content
                return

            # ---- MODE 2: SIMPLE WEB-SEARCH CHAIN (NO AGENT) ----
            search_result = web_search.invoke(request.prompt)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. "
                           "You have been given some web search results. "
                           "Read them and answer the user's question accurately and concisely."),
                ("human", "User question: {question}\n\nWeb search results:\n{results}"),
            ])
            chain = prompt | llm

            input_data = {
                "question": request.prompt,
                "results": search_result,
            }

            async for chunk in chain.astream(input_data):
                if getattr(chunk, "content", None):
                    yield chunk.content

        except Exception as e:
            yield f"Server Error: {str(e)}"

    return StreamingResponse(streamer(), media_type="text/plain")
