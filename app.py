from fastapi import FastAPI
import uvicorn
app = FastAPI()
@app.get("/add")
def add(x,y):
    return float(x) + float(y)
@app.get("/subtract")
def subtract(x,y):
    return float(x) - float(y)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9321)
