import os
import sys
import types
from importlib.machinery import ModuleSpec
import requests
from datetime import datetime, timedelta
import pandas as pd

API_KEY = "1f30615161cf4037b369adb5e4e0efb6"  
DISABLE_JAX_IMPORTS = True  

def _register_stub_module(module_name: str) -> None:
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    module.__spec__ = ModuleSpec(name=module_name, loader=None)
    sys.modules[module_name] = module

if DISABLE_JAX_IMPORTS:
    for name in [
        "jax",
        "jax.numpy",
        "jaxlib",
        "jaxlib.utils",
        "flax",
        "tensorflow",
    ]:
        _register_stub_module(name)

from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax
import torch

STOCKS = [
    "Bitcoin",
    "Ethereum",
    "Solana",
    "Tesla",
    "NVIDIA",
    "Amazon",
    "Microsoft",
]
MAX_TOKENS = 512  
NEWS_DAYS = 7     
ARTICLES_PER_COMPANY = 25  

print("Loading FinBERT sentiment model...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-tone")
model = AutoModelForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone")
model.to(device)
model.eval()
print(f"FinBERT loaded successfully on {device}.\n")

positive_news, negative_news, neutral_news = [], [], []

def get_news(company: str) -> list:
    start_date = (datetime.now() - timedelta(days=NEWS_DAYS)).strftime("%Y-%m-%d")
    endpoint = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": API_KEY,
        "q": company,
        "sortBy": "publishedAt",
        "language": "en",
        "from": start_date,
        "to": datetime.now().strftime("%Y-%m-%d"),
        "pageSize": ARTICLES_PER_COMPANY,
    }

    try:
        r = requests.get(endpoint, params=params, timeout=15)
        if r.status_code == 200:
            articles = r.json().get("articles", [])
            cleaned = []
            seen_titles = set()
            for a in articles:
                title = (a.get("title") or "").strip()
                description = (a.get("description") or "").strip()
                if not title and not description:
                    continue
                # de-dup by title
                key = title.lower()
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                cleaned.append(
                    {
                        "title": title,
                        "description": description,
                        "url": a.get("url") or "",
                        "publishedAt": a.get("publishedAt") or "",
                        "source": (a.get("source") or {}).get("name", ""),
                    }
                )
            return cleaned
        else:
            print(f"[ERROR] NewsAPI {r.status_code}: {r.text}")
            return []
    except Exception as e:
        print(f"[EXCEPTION] while fetching news for {company}: {e}")
        return []

def analyze_sentiment(text: str) -> dict:
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0, "probs": {"negative": 0.0, "neutral": 1.0, "positive": 0.0}}

    encoded = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_TOKENS,
    )
    encoded = {k: v.to(device) for k, v in encoded.items()}
    with torch.no_grad():
        outputs = model(**encoded)

    scores = softmax(outputs.logits[0].detach().cpu().numpy())
    labels = ["negative", "neutral", "positive"]
    best_index = int(scores.argmax())
    best_label = labels[best_index]
    confidence = float(scores[best_index])
    probs = {labels[i]: float(scores[i]) for i in range(3)}

    return {"label": best_label, "score": confidence, "probs": probs}


def aggregate_company_sentiments(items: list) -> dict:
    if not items:
        return {"label": "neutral", "score": 0.0}

    total = {"negative": 0.0, "neutral": 0.0, "positive": 0.0}
    for it in items:
        probs = it.get("probs", {})
        for k in total:
            total[k] += float(probs.get(k, 0.0))

    n = max(len(items), 1)
    avg = {k: v / n for k, v in total.items()}
    label = max(avg, key=avg.get)
    score = avg[label]
    return {"label": label, "score": score, "avg_probs": avg}

def main():
    print("Starting FinBERT Sentiment Analysis...\n")
    if not API_KEY:
        print("[WARNING] NEWSAPI_KEY not set. Using built-in key if present.")

    per_article_rows = []

    for company in STOCKS:
        print(f"Analyzing {company}...")
        articles = get_news(company)
        company_items = []

        for a in articles:
            text = (a.get("title", "") + ". " + a.get("description", "")).strip()
            sentiment = analyze_sentiment(text)
            company_items.append(sentiment)
            per_article_rows.append(
                {
                    "company": company,
                    "title": a.get("title", ""),
                    "description": a.get("description", ""),
                    "url": a.get("url", ""),
                    "publishedAt": a.get("publishedAt", ""),
                    "source": a.get("source", ""),
                    "label": sentiment["label"],
                    "score": sentiment["score"],
                    "prob_negative": sentiment["probs"]["negative"],
                    "prob_neutral": sentiment["probs"]["neutral"],
                    "prob_positive": sentiment["probs"]["positive"],
                }
            )

        agg = aggregate_company_sentiments(company_items)
        label, score = agg.get("label", "neutral"), float(agg.get("score", 0.0))
        print(f"→ Company sentiment: {label.upper()} ({score:.2f})")

        if label == "positive":
            print(f"BUY {company}")
            positive_news.append({"Company": company, "Score": score})
        elif label == "negative":
            print(f"SELL {company}")
            negative_news.append({"Company": company, "Score": score})
        else:
            print(f"HOLD {company}")
            neutral_news.append({"Company": company, "Score": score})

        print("-" * 50)

    if positive_news:
        pd.DataFrame(positive_news).to_csv("buy_signals.csv", index=False)
    if negative_news:
        pd.DataFrame(negative_news).to_csv("sell_signals.csv", index=False)
    if neutral_news:
        pd.DataFrame(neutral_news).to_csv("hold_signals.csv", index=False)

    if per_article_rows:
        pd.DataFrame(per_article_rows).to_csv("news_sentiments_detailed.csv", index=False)

    print("\nSentiment analysis completed!")
    print("CSV files generated: buy_signals.csv, sell_signals.csv, hold_signals.csv, news_sentiments_detailed.csv")

if __name__ == "__main__":
    main()
