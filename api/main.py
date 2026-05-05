from fastapi import FastAPI

app = FastAPI(title="prism-0420", version="0.1.0")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
