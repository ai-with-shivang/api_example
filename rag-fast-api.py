pip install fastapi uvicorn[standard] PyPDF2 requests

from fastapi import FastAPI, UploadFile, Form
import requests
import PyPDF2
import io

app = FastAPI()

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def ask_ollama(prompt, context, model="mistral:latest"):
    """
    Send prompt + context to Ollama model.
    """
    response = requests.post(
        OLLAMA_API_URL,
        json={
            "model": model,
            "prompt": f"Context:\n{context}\n\nQuestion:\n{prompt}\nAnswer:",
            "options": {
                "num_predict": 200,
                "temperature": 0.5
            }
        },
        stream=True
    )

    output = ""
    for line in response.iter_lines():
        if line:
            data = line.decode("utf-8")
            try:
                obj = json.loads(data)
                if "response" in obj:
                    output += obj["response"]
            except Exception:
                pass
    return output.strip()


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using PyPDF2.
    """
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile, question: str = Form(...)):
    """
    Upload a PDF and ask a question about its content.
    """
    file_bytes = await file.read()
    pdf_text = extract_text_from_pdf(file_bytes)

    # Ask Ollama using PDF text as context
    answer = ask_ollama(question, pdf_text)
    return {"question": question, "answer": answer}
	

