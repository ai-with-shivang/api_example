import os
import json
import glob
from typing import List

import pdfplumber
from nicegui import ui
import ollama

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer

# =====================================================
# PATHS
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)

vectorstore = None
rag_ready = False

# =====================================================
# EMBEDDINGS
# =====================================================
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# =====================================================
# PDF PROCESSING
# =====================================================
def extract_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text


def build_index(pdf_files: List[str]) -> FAISS:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    texts, metas = [], []

    for pdf in pdf_files:
        name = os.path.basename(pdf)
        text = extract_text(pdf)
        if not text.strip():
            continue

        for c in splitter.split_text(text):
            texts.append(c)
            metas.append({"source": name})

    return FAISS.from_texts(
        texts,
        embedding=lambda x: embedder.encode(x, show_progress_bar=False),
        metadatas=metas,
    )


def retrieve_context(vs: FAISS, query: str, k: int = 4) -> str:
    docs = vs.similarity_search(query, k=k)
    return "\n\n".join(d.page_content for d in docs)

# =====================================================
# CHAT HISTORY
# =====================================================
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2, ensure_ascii=False)


chat_history = load_history()

# =====================================================
# UI MESSAGE
# =====================================================
def add_message(box, sender, text, persist=True):
    css_user = "bg-blue-600 text-white p-2 rounded max-w-[70%]"
    css_bot = "bg-gray-300 text-black p-2 rounded max-w-[70%]"
    align = "justify-end" if sender == "user" else "justify-start"

    with box:
        with ui.row().classes(align):
            ui.label(text).classes(css_user if sender == "user" else css_bot)

    if persist:
        chat_history.append({"sender": sender, "text": text})
        save_history(chat_history)

# =====================================================
# OLLAMA (llama3)
# =====================================================
def ask_llama3(context: str, question: str) -> str:
    prompt = f"""
Answer the question ONLY using the context.
If the answer is not in the context, say:
"Information not found in the documents."

Context:
{context}

Question:
{question}

Answer:
"""
    res = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
    )
    return res["message"]["content"].strip()

# =====================================================
# GUI
# =====================================================
ui.dark_mode().enable()

with ui.header().classes("bg-gray-900 text-white"):
    ui.label("ShivangChatBot — Ask Questions Across Your PDFs").classes("text-xl")

with ui.row().classes("w-full"):

    # ---------- UPLOAD ----------
    with ui.card().classes("w-1/3 p-4"):
        ui.label("Upload PDFs").classes("text-lg")
        status = ui.label("Upload PDFs and build index").classes("text-sm text-yellow-400")
        files_box = ui.column()

        def refresh_files():
            files_box.clear()
            pdfs = glob.glob(os.path.join(UPLOAD_DIR, "*.pdf"))
            with files_box:
                if not pdfs:
                    ui.label("No PDFs uploaded").classes("text-gray-400 text-sm")
                for p in pdfs:
                    ui.label(f"• {os.path.basename(p)}").classes("text-gray-300 text-sm")

        # ✅ CORRECT FOR YOUR NICEGUI
        def upload_handler(e):
            filename = e.args["name"]
            data = e.args["content"]

            with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                f.write(data)

            status.set_text(f"✅ Uploaded: {filename}")
            status.classes(replace="text-sm text-green-500")
            refresh_files()

        ui.upload(on_upload=upload_handler, multiple=True).props("accept=.pdf")

        def build():
            global vectorstore, rag_ready
            pdfs = glob.glob(os.path.join(UPLOAD_DIR, "*.pdf"))
            if not pdfs:
                status.set_text("❌ No PDFs found")
                status.classes(replace="text-sm text-red-500")
                return

            status.set_text("⏳ Building index...")
            status.classes(replace="text-sm text-yellow-400")

            vectorstore = build_index(pdfs)
            rag_ready = True

            status.set_text("✅ Ready to chat")
            status.classes(replace="text-sm text-green-500")

        ui.button("Build Index", on_click=build).classes("mt-2 bg-blue-600")
        refresh_files()

    # ---------- CHAT ----------
    with ui.card().classes("w-2/3 p-4"):
        ui.label("Chat").classes("text-lg")
        chat_box = ui.column().classes("h-[520px] overflow-y-auto bg-gray-800 p-3 rounded")

        for m in chat_history:
            add_message(chat_box, m["sender"], m["text"], persist=False)

        user_input = ui.input(placeholder="Ask a question...").classes("w-full mt-2")

        def ask():
            q = (user_input.value or "").strip()
            if not q:
                return

            add_message(chat_box, "user", q)

            if not rag_ready:
                add_message(chat_box, "bot", "Please upload PDFs and build index first.")
                user_input.value = ""
                return

            context = retrieve_context(vectorstore, q)
            answer = ask_llama3(context, q)

            add_message(chat_box, "bot", answer)
            user_input.value = ""

        ui.button("Ask", on_click=ask).classes("mt-2 bg-green-600")

ui.run(host="127.0.0.1", port=8080, reload=False)
