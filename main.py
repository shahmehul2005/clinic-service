import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from agent import generate_craft_images, root_agent

app = FastAPI(title="Kalpana AI Muse Agent API")

class ImageRequest(BaseModel):
    image_input: str

@app.post("/generate")
def generate_images(request: ImageRequest):
    """
    Generate 4 modern interpretations of a traditional craft image.
    image_input can be a base64 encoded image, URL, or local file path.
    """
    try:
        result = generate_craft_images(request.image_input)
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error_message"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
