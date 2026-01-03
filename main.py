import os
import datetime
from typing import AsyncIterable

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import requests
from duckduckgo_search import DDGS

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# --------------------------------------------------------------------------------------
# FastAPI app
# --------------------------------------------------------------------------------------
app = FastAPI(
    title="FreeAI Multi-Tool Server",
    description="LLM + Web Search + Weather + Time utilities with streaming",
    version="1.0.0",
)

# --------------------------------------------------------------------------------------
# TOOLS
# --------------------------------------------------------------------------------------

@tool
def web_search(query: str) -> str:
    """Search the internet for latest info and return list-style results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No relevant results found."
        lines = []
        for i, r in enumerate(results, start=1):
            title = (r.get("title") or "").strip()
            href = (r.get("href") or "").strip()
            body = (r.get("body") or "").strip()[:300]
            lines.append(
                f"{i}. Title: {title}\n"
                f"   URL: {href}\n"
                f"   Snippet: {body}..."
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def get_india_time(_: str = "") -> str:
    """Return current date and time in India (IST)."""
    # IST = UTC + 5:30
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_tz = datetime.timezone(ist_offset)
    now_ist = datetime.datetime.now(tz=ist_tz)
    date_str = now_ist.strftime("%Y-%m-%d")
    time_str = now_ist.strftime("%H:%M:%S")
    return f"Date: {date_str}, Time: {time_str} IST"


@tool
def get_weather(city: str) -> str:
    """Get current weather for a city using OpenWeatherMap (metric, °C)."""
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        return "Weather API key not configured on server."

    try:
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",
        }
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            return f"Weather API error: {resp.text}"

        data = resp.json()
        name = data.get("name", city)
        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})

        desc = weather.get("description", "N/A")
        temp = main.get("temp", "N/A")
        feels_like = main.get("feels_like", "N/A")
        humidity = main.get("humidity", "N/A")

        return (
            f"City: {name}\n"
            f"Condition: {desc}\n"
            f"Temperature: {temp}°C (feels like {feels_like}°C)\n"
            f"Humidity: {humidity}%"
        )
    except Exception as e:
        return f"Weather fetch failed: {str(e)}"


TOOLS = [web_search, get_india_time, get_weather]

# --------------------------------------------------------------------------------------
# Request model
# --------------------------------------------------------------------------------------

class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(default="qwen2.5:3b", max_length=50)
    enable_web_search: bool = Field(
        default=False,
        description="If true, use web_search + tools before answering.",
    )
    temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    power_mode: bool = Field(
        default=False,
        description="If true, give deeper multi-level list answers.",
    )


# --------------------------------------------------------------------------------------
# Small helper: detect dev queries
# --------------------------------------------------------------------------------------

DEV_KEYWORDS = [
    "code", "bug", "error", "traceback",
    "fastapi", "nextjs", "next.js", "react",
    "python", "typescript", "stack trace",
]


def is_dev_query(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in DEV_KEYWORDS)


# --------------------------------------------------------------------------------------
# Core endpoint with streaming
# --------------------------------------------------------------------------------------

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
            # --------------------------------------------------
            # MODE 1: No web search → pure chat with dev/normal mode
            # --------------------------------------------------
            if not request.enable_web_search:
                dev_mode = is_dev_query(request.prompt)
                if dev_mode:
                    system_msg = (
                        "You are a senior full-stack engineer. "
                        "Always give clean code blocks, stepwise reasoning, and avoid unnecessary text."
                    )
                else:
                    system_msg = (
                        "You are a helpful assistant. "
                        "Be concise and clear. Prefer bullet lists for multiple points."
                    )

                messages = [
                    ("system", system_msg),
                    ("human", request.prompt),
                ]
                async for chunk in llm.astream(messages):
                    if getattr(chunk, "content", None):
                        yield chunk.content
                return

            # --------------------------------------------------
            # MODE 2: Web / tools powered answer
            #  - Tool calls run server-side (fast)
            #  - LLM then reasons + formats for user
            # --------------------------------------------------
            user_q = request.prompt.lower()

            # Auto tool selection hints for system prompt
            use_time = any(w in user_q for w in ["time", "date", "india time", "ist"])
            use_weather = "weather" in user_q or "temperature" in user_q or "mausam" in user_q

            tool_info = []
            if use_time:
                tool_info.append("get_india_time")
            if use_weather:
                # naive: try to extract city name from end of question if any
                # user can also just say: 'weather in Mumbai'
                city_guess = request.prompt.replace("weather", "").strip()
                if not city_guess:
                    city_guess = "Mumbai"
                weather_text = get_weather.invoke(city_guess)
                tool_info.append(f"get_weather(city='{city_guess}') -> {weather_text}")

            # Always run web_search as a general context provider
            search_results = web_search.invoke(request.prompt)

            if request.power_mode:
                system_text = (
                    "You are an expert research assistant with access to some tools.\n"
                    "- Use the web search results and tool outputs given below as primary facts.\n"
                    "- Always answer in clear bullet or numbered lists when there are multiple items.\n"
                    "- Group related items and keep explanations short but precise.\n"
                )
            else:
                system_text = (
                    "You are a concise assistant.\n"
                    "- Use the web search results and tools outputs below.\n"
                    "- Keep the answer short, focusing on key points.\n"
                )

            tools_context = ""
            if tool_info:
                tools_context = "\n\nTool outputs:\n" + "\n".join(f"- {t}" for t in tool_info)

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_text),
                (
                    "human",
                    "User question: {question}\n\n"
                    "Web search results:\n{results}"
                    "{tools_ctx}"
                ),
            ])

            chain = prompt | llm
            input_data = {
                "question": request.prompt,
                "results": search_results,
                "tools_ctx": tools_context,
            }

            async for chunk in chain.astream(input_data):
                if getattr(chunk, "content", None):
                    yield chunk.content

        except Exception as e:
            yield f"Server Error: {str(e)}"

    return StreamingResponse(streamer(), media_type="text/plain")


# --------------------------------------------------------------------------------------
# Simple health check
# --------------------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "model": "ollama", "tools": ["web_search", "get_india_time", "get_weather"]}


# --------------------------------------------------------------------------------------
# Local run
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
