from fastapi import FastAPI

app = FastAPI(title="Mind Recovery MVP")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
