from fastapi import FastAPI, File, UploadFile
from uvicorn import run

app = FastAPI()


@app.post("/")
async def create_file(file: bytes = File()):
    with open("import.csv","wb+") as fd:
        fd.write(file) 
    return "ok"


if __name__ == "__main__":
    run("api:app",host="0.0.0.0",port=5000,reload=True)