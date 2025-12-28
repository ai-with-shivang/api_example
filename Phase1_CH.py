import re
import json
import requests
from ddgs import DDGS

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"


# -----------------------------
# SAFE OLLAMA CALL
# -----------------------------
def ask_llama(prompt):
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Ollama error: {data['error']}")

        if "response" not in data:
            raise RuntimeError(f"Unexpected Ollama output: {data}")

        return data["response"]

    except Exception as e:
        print("❌ LLM failure:", e)
        return ""


# -----------------------------
# WEB SEARCH (MULTI-SOURCE)
# -----------------------------
def web_search(company):
    queries = [
        f"{company} official website",
        f"{company} address contact",
        f"{company} phone email",
        f"{company} LinkedIn",
        f"{company} management team",
        f"{company} HR email",
        f"{company} Chakan MIDC Pune",
    ]

    results = []
    with DDGS() as ddgs:
        for q in queries:
            for r in ddgs.text(q, max_results=5):
                results.append({
                    "query": q,
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", "")
                })
    return results


# -----------------------------
# INTELLIGENCE EXTRACTION
# -----------------------------
def extract_intelligence(company, search_results):
    if not search_results:
        return {}

    context = "\n\n".join(
        f"URL: {r['url']}\n{r['snippet']}"
        for r in search_results[:25]  # limit context
    )

    prompt = f"""
You are a business OSINT analyst.

Company: {company}
Country: India

Extract ONLY verifiable, publicly available information.

Return STRICT JSON only (no commentary):

{{
  "addresses": [],
  "phones": [],
  "emails": [],
  "people": [
    {{
      "name": "",
      "designation": "",
      "phone": "",
      "email": ""
    }}
  ]
}}

RULES:
- Do not guess or fabricate
- Leave fields empty if unknown
- Use Indian phone formats
- Do not repeat duplicates

DATA:
{context}
"""

    raw = ask_llama(prompt)
    if not raw:
        return {}

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        print("⚠️ LLM returned no JSON")
        return {}

    try:
        return json.loads(match.group())
    except Exception as e:
        print("⚠️ JSON parse error:", e)
        return {}


# -----------------------------
# MAIN ACTIONFLOW
# -----------------------------
def run():
    company = input("Enter company name: ").strip()

    print("\n🔍 Searching public sources...\n")
    results = web_search(company)
    print(f"🔎 Found {len(results)} public references")

    if not results:
        print("⚠️ No public content found")
        return

    print("\n🧠 Extracting intelligence using LLaMA...\n")
    data = extract_intelligence(company, results)

    print("\n================= RESULT =================")
    print(json.dumps(data, indent=2, ensure_ascii=False))


if _name_ == "_main_":
    run()
