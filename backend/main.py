from nt import error
import os
import json
import uuid
from log.logger import logger
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from llms.vision_llm import invoke_llm_with_image
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agents.main_agent import build_image_url, run_agent


load_dotenv(override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "prompt":
                message = data.get("message", "").strip()
                if not message:
                    continue
                print(f"[WS] Prompt: {message}")
                try:
                    result = await run_agent(message, config)
                except Exception as e:
                    print(f"[WS] run_agent error: {e}")
                    result = {"response": "An error occurred. Please try again.", "documents": []}
                print(f"[WS] Retrieved {len(result['documents'])} document(s)")
                await websocket.send_text(json.dumps({
                    "type": "results",
                    "response": result["response"],
                    "documents": result["documents"],
                }))

            elif data.get("type") == "image":
                base64_data = data.get("base64", "").strip()
                mime_type = data.get("mime_type", "image/jpeg").strip() or "image/jpeg"
                if not base64_data:
                    continue
                user_prompt = data.get("message", "").strip()
                try:
                    image_url = build_image_url(base64_data, mime_type)
                    if not image_url:
                        await websocket.send_text(json.dumps({
                            "type": "results",
                            "response": "Try uploading another image",
                            "documents": [],
                        })) 
                        continue

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
                                continue
                            else:
                                break
                        except Exception as e:
                            logger.error(f"Some error occured while extracting data from image: {e}")
                            if i==2:
                                await websocket.send_text(json.dumps({
                                    "type": "results",
                                    "response": "Error occured while parsing image, try again.",
                                    "documents": [],
                                })) 
                                continue
                    product_info_string += "\n".join(f"{pos}. {k}:{v}" for pos, (k, v) in enumerate(response.items(), 1))
                    if user_prompt:
                        user_prompt+=f"\n Product Info: \n {product_info_string}"
                    else: 
                        user_prompt = f"Is the product with the following details halal? \n {product_info_string}"
                        
                    result = await run_agent(user_prompt, config)
                except Exception as e:
                    print(f"[WS] run_agent error: {e}")
                    result = {"response": "An error occurred. Please try again.", "documents": []}
                print(f"[WS] Retrieved {len(result['documents'])} document(s)")
                await websocket.send_text(json.dumps({
                    "type": "results",
                    "response": result["response"],
                    "documents": result["documents"],
                }))

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
