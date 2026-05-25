import asyncio
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agents.main_agent import run_agent, build_image_user_content
from dotenv import load_dotenv
import uuid
import os
import json

from backend.llms.vision_llm import invoke_llm_with_image

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
                text = data.get("message", "").strip() or "Is this halal?"
                try:
                    image_url = build_image_user_url(base64_data, mime_type)
                    result = await invoke_llm_with_image()
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
