import os
import requests
from typing import TypedDict, List, Dict, Any
import boto3
from botocore.exceptions import ClientError
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# ─── Setup ───────────────────────────────────────────────────────────────────

import boto3
from botocore.exceptions import ClientError


def get_secret():

    secret_name = "LLM_SECRETS"
    region_name = "ap-south-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    secret=json.loads(secret)
    return secret

secrets=get_secret()
OPENAI_API_KEY = secrets['OPENAI_API_KEY']
SERPER_API_KEY = secrets['SERPER_API_KEY']


llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

class State(TypedDict):
    stocks: List[Dict[str, str]]
    news: Dict[str, List[Dict[str, Any]]]
    summaries: Dict[str, str]

# ─── Node 1: get_news ────────────────────────────────────────────────────────

def get_news(state: State) -> Dict[str, Any]:
    SERPER_ENDPOINT = "https://google.serper.dev/news"
    news_results: Dict[str, List[Dict[str, Any]]] = {}

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    for stock in state["stocks"]:
        name, symbol = next(iter(stock.items()))
        payload = {
            "q": name,
            "gl": "in",
            "hl": "en"
        }

        try:
            resp = requests.post(SERPER_ENDPOINT, headers=headers, json=payload)
            articles = resp.json().get("news", [])[:5]
        except Exception as e:
            articles = [{"title": "Error", "description": str(e)}]

        cleaned = [
            {"title": a.get("title", ""), "description": a.get("snippet", "")}
            for a in articles
        ]

        news_results[name] = cleaned
    return {"news": news_results}

# ─── Node 2: generate_response ────────────────────────────────────────────────

prompt = """
You are a financial market analyst focused on stock price dynamics. Analyze {stock_name}'s performance using the news below. Your task is two-fold:

1. **Explain the Past**: fetch stock price fluctuations of last trading session and describe potential causes of recent share price movement of last trading session.Base reasoning on:

   - Macroeconomic trends (e.g., inflation, interest rates)
   - Industry or sector events (e.g., regulations, commodity prices, innovation)
   - Company-specific fundamentals (e.g., earnings, balance sheet, management)
   - Market sentiment (e.g., investor mood, news headlines)
   - Technical indicators (e.g., volume spikes, price patterns)
   - Geopolitical or external events (e.g., wars, disasters, elections)
   - Analyst and institutional activity (e.g., upgrades, fund flows)
   - ESG developments (e.g., climate policy, corporate responsibility)

2. **Forecast the Impact**: Based on available news or developments, identify how these factors could influence the stock’s price **in the next trading session or near term**—either positively or negatively.

Relevant News and Events:
{news_summary}

Instructions:
- Write a single paragraph, under 90 words.
- Use plain, precise financial language. No opinions.
- Prioritize clarity, conciseness, and factual reasoning.
- Attribute movements or forecasts to specific causes from the list above when possible.
"""

def generate_response(state: State) -> Dict[str, Any]:
    summaries: Dict[str, str] = {}
    for stock in state["stocks"]:
        name = next(iter(stock))
        nw = state["news"].get(name, [])
        bullets = "\n".join(f"- {a['title']}: {a['description']}" for a in nw[:3]) or "No news."
        filled = prompt.format(
            stock_name=name,
            news_summary=bullets
        )
        msg = llm.invoke([
            SystemMessage(content="You are a financial assistant."),
            HumanMessage(content=filled)
        ])
        summaries[name] = msg.content
    return {"summaries": summaries}

# ─── Build & Wire Graph (Linear) ──────────────────────────────────────────────

builder = StateGraph(State)

builder.add_node("get_news", get_news)
builder.add_node("generate_response", generate_response)

builder.set_entry_point("get_news")
builder.add_edge("get_news", "generate_response")
builder.add_edge("generate_response", END)

graph = builder.compile()

# ─── Run ─────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     initial_state = {
#         "stocks": [
#             {"Emerald Finance": "538882.BO"},
#             {"Geojit Financial Services": "GEOJIT.BO"}
#         ]
#     }

#     final_state = graph.invoke(initial_state)
#     for company, summary in final_state["summaries"].items():
#         print(f"\n=== {company} ===\n{summary}")

def generate_news_summary(stock_dict: Dict[str, str]) -> Dict[str, str]:
    initial_state = {
        "stocks": [{name: symbol} for name, symbol in stock_dict.items()]
    }

    final_state = graph.invoke(initial_state)
    return final_state["summaries"]

    # stock_list = [{"NAME": name, "SYMBOL": symbol} for name, symbol in stock_dict.items()]
    # final_state = graph.invoke({"stocks": stock_list})
    # return final_state["summaries"]
