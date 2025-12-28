# ==========================================================
# ActionFlow – Excel Based Company Intelligence (CLI)
# Python 3.14 | Ollama | No LangChain
# ==========================================================

import pandas as pd
import requests
import subprocess
import os
import sys
import textwrap

# --------------------------
# CONFIG
# --------------------------
INPUT_EXCEL = r"C:\Users\2shiv\Downloads\AI\Phase2-Excel\company-Name.xlsx"
OUTPUT_DIR = r"C:\Users\2shiv\Downloads\AI\Phase2-Excel"
OUTPUT_EXCEL = os.path.join(OUTPUT_DIR, "Company_details-Output.xlsx")

HINT = "All these companies are located in Chakan MIDC area of Pune, India"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# --------------------------
# OLLAMA CALL (CLI)
# --------------------------
def call_llama(prompt: str) -> str:
    result = subprocess.run(
        ["ollama", "run", "llama3.1"],
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True
    )

    if result.returncode != 0:
        return "LLM execution failed."

    return result.stdout.strip()

# --------------------------
# FETCH PUBLIC INFO (WIKI API)
# --------------------------
def fetch_public_info(company: str) -> str:
    title = company.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("extract", "")
    except Exception:
        pass

    return ""

# --------------------------
# ACTION: ADDRESS DISCOVERY
# --------------------------
def find_company_address(company: str, public_text: str) -> str:
    prompt = f"""
You are a business intelligence assistant.

Company Name: {company}
Hint: {HINT}

Based on the information below and your general knowledge:
1. Identify the company address or location
2. Mention industrial area, city, state if known
3. If exact address is not available, provide best inferred location

Public Information:
{public_text}

Respond clearly in plain text.
"""
    return call_llama(prompt)

# --------------------------
# LOAD INPUT EXCEL
# --------------------------
def load_companies():
    df = pd.read_excel(INPUT_EXCEL)

    if "Company Name" not in df.columns:
        print("❌ Excel must contain column: Company Name")
        sys.exit(1)

    return df["Company Name"].dropna().tolist()

# --------------------------
# INIT OUTPUT EXCEL
# --------------------------
def init_output_excel():
    if not os.path.exists(OUTPUT_EXCEL):
        df = pd.DataFrame(columns=[
            "Company Name",
            "Identified Address / Location",
            "Remarks"
        ])
        df.to_excel(OUTPUT_EXCEL, index=False)

# --------------------------
# APPEND TO OUTPUT EXCEL
# --------------------------
def append_to_excel(company, address, remarks=""):
    df = pd.read_excel(OUTPUT_EXCEL)

    df.loc[len(df)] = [company, address, remarks]
    df.to_excel(OUTPUT_EXCEL, index=False)

# --------------------------
# ACTIONFLOW ENGINE
# --------------------------
def run_actionflow():
    print("\n" + "=" * 55)
    print(" ACTIONFLOW – CHAKAN MIDC COMPANY INTELLIGENCE ")
    print("=" * 55)

    companies = load_companies()
    init_output_excel()

    for idx, company in enumerate(companies, start=1):
        print(f"\n[{idx}] COMPANY: {company}")
        print("-" * 75)

        try:
            public_info = fetch_public_info(company)

            address_info = find_company_address(company, public_info)

            print("\n==FINDINGS:==\n")
            print(textwrap.fill(address_info, width=90))

            choice = input("\n➡ Save this entry to Excel? (y/n): ").strip().lower()

            if choice in ("y", "yes"):
                append_to_excel(company, address_info)
                print("✅ Saved to OutputSheet_1.xlsx")
            else:
                print("⏭ Skipped saving this entry")

        except Exception as e:
            print(f"❌ Error processing {company}: {e}")

        cont = input("\n➡ Continue with next company? (y/n): ").strip().lower()
        if cont not in ("y", "yes"):
            print("\n=== ActionFlow stopped by user ===")
            break

# --------------------------
# ENTRY POINT
# --------------------------
if __name__ == "__main__":
    run_actionflow()
