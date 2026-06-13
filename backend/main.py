import os
import json
import uuid
from log.logger import logger
from dotenv import load_dotenv
from agents.main_agent import build_image_url
from llms.vision_llm import invoke_llm_with_image
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBaseModel
from agents.langgraph_agent.main_langgraph_agent import stream_agent
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from config.supabase_client import get_supabase

load_dotenv(override=True)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractImageRequest(PydanticBaseModel):
    base64: str
    mime_type: str = "image/jpeg"


@app.post("/extract-image")
async def extract_image_endpoint(req: ExtractImageRequest):
    image_url = build_image_url(req.base64, req.mime_type)
    if not image_url:
        raise HTTPException(status_code=400, detail="Invalid image data")
    for _ in range(3):
        try:
            result = await invoke_llm_with_image(image_url)
            if "error" not in result:
                return {"fields": result}
        except Exception as e:
            logger.error(f"extract_image error: {e}")
    raise HTTPException(status_code=422, detail="Failed to extract image information")


@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: str,
    token: str = Query(default=""),
):
    if not thread_id:
        await websocket.close(code=1008, reason="Missing thread ID")
        return

    # Validate the Supabase JWT before accepting the connection.
    try:
        user_response = get_supabase().auth.get_user(token)
        if not user_response.user:
            await websocket.close(code=1008, reason="Unauthorized")
            return
    except Exception as e:
        logger.warning(f"[WS] Auth failed: {e}")
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "prompt":
                try:
                    message = data.get("message", "").strip()
                    if not message:
                        continue
                    logger.info(f"[WS] Prompt: {message}")
                    async for chunk in stream_agent(message, config):
                        await websocket.send_text(json.dumps(chunk))
                except Exception as e:
                    logger.error(f"[WS] response generation error: {e}")
                    result = {"response": "An error occurred. Please try again.", "documents": []}
                    await websocket.send_text(json.dumps({
                        "type": "results",
                        "response": result["response"],
                        "documents": result["documents"],
                    }))
                continue

            elif data.get("type") == "image":
                try:
                    base64_data = data.get("base64", "").strip()
                    mime_type = data.get("mime_type", "image/jpeg").strip() or "image/jpeg"
                    if not base64_data:
                        continue
                    user_prompt = data.get("message", "").strip()
                    image_url = build_image_url(base64_data, mime_type)
                    if not image_url:
                        logger.info("No image found.")
                        await websocket.send_text(json.dumps({
                            "type": "results",
                            "response": "Try uploading another image",
                            "documents": [],
                        })) 
                        continue
                    response = {}
                    success = False
                    # add retry logic here
                    for i in range(3):
                        try:
                            response = await invoke_llm_with_image(image_url)
                            error = response.get("error")
                            if error:
                                if i==2:
                                    await websocket.send_text(json.dumps({
                                        "type": "results",
                                        "response": response["error"],
                                        "documents": [],
                                    }))
                                    success = False
                                    break
                                continue
                            else:
                                success = True
                                break
                        except Exception as e:
                            logger.error(f"Some error occured while extracting data from image: {e}")
                            if i==2:
                                await websocket.send_text(json.dumps({
                                    "type": "results",
                                    "response": "Error occured while parsing image details, try again.",
                                    "documents": [],
                                })) 
                                success = False
                                break
                            continue
                    if not success:
                        continue
                    parts = []
                    # v can only be string or an array of strings
                    for k, v in response.items():
                        if isinstance(v, list):
                            if v:
                                parts.append(f"{k}: {', '.join(str(i) for i in v)}")
                        elif v:
                            parts.append(f"{k}: {v}")
                    product_info_string = "\n".join(parts)
                    
                    if user_prompt and product_info_string:
                        final_prompt = f"{user_prompt} \n Product Info: \n {product_info_string}"

                    elif product_info_string:
                        final_prompt = f"Is the product with the following details halal? \n {product_info_string}"
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "results",
                            "response": "No product information found from the image, please try again.",
                            "documents": [],
                        }))
                        continue

                    async for chunk in stream_agent(final_prompt, config):
                        await websocket.send_text(json.dumps(chunk))
                except Exception as e:
                    print(f"[WS] response generation error: {e}")
                    result = {"response": "An error occurred. Please try again.", "documents": []}
                    await websocket.send_text(json.dumps({
                        "type": "results",
                        "response": result["response"],
                        "documents": result["documents"],
                    }))
                continue

            elif data.get("type") == "run_with_fields":
                try:
                    fields = data.get("fields", {})
                    user_prompt = data.get("message", "").strip()

                    parts = []
                    # v can only be string or an array of strings
                    for k, v in fields.items():
                        if isinstance(v, list):
                            if v:
                                parts.append(f"{k}: {', '.join(str(i) for i in v)}")
                        elif v:
                            parts.append(f"{k}: {v}")
                    product_info_string = "\n".join(parts)

                    if user_prompt and product_info_string:
                        final_prompt = f"{user_prompt} \n Product Info: \n {product_info_string}"
                    elif product_info_string:
                        final_prompt = f"Is the product with the following details halal? \n {product_info_string}"
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "results",
                            "response": "No product information found from the image, please try again.",
                            "documents": [],
                        }))
                        continue
                    
                    async for chunk in stream_agent(final_prompt, config):
                        await websocket.send_text(json.dumps(chunk))
                except Exception as e:
                    logger.error(f"[WS] response generation error: {e}")
                    result = {"response": "An error occurred. Please try again.", "documents": []}
                    await websocket.send_text(json.dumps({
                        "type": "results",
                        "response": result["response"],
                        "documents": [result["documents"]],
                    }))
                continue

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
