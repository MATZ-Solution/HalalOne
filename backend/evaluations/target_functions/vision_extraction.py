import base64
import mimetypes
import os
from typing import Any

from llms.vision_llm import invoke_llm_with_image


def get_image_data_url(image_path: str) -> str:
    """Encodes a local image file into a base64 Data URL (data:image/jpeg;base64,...)."""
    if not os.path.isabs(image_path):
        # Resolve path relative to backend root
        backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        full_path = os.path.join(backend_root, image_path)
    else:
        full_path = image_path

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Image file not found: {full_path}")

    mime_type, _ = mimetypes.guess_type(full_path)
    mime_type = mime_type or "image/jpeg"

    with open(full_path, "rb") as img_file:
        b64_str = base64.b64encode(img_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64_str}"


async def run_vision_extraction(inputs: dict[str, Any]) -> dict[str, Any]:
    """Target function for evaluating the vision extraction pipeline.

    Accepts:
        inputs: {
            "image_url": str (optional base64 or remote URL),
            "image_path": str (local path to image),
            "image_filename": str
        }
    Returns:
        Extracted product schema dict from vision_llm
    """
    image_url = inputs.get("image_url")
    if not image_url and inputs.get("image_path"):
        image_url = get_image_data_url(inputs["image_path"])

    if not image_url:
        return {"error": "No image_url or valid image_path found in inputs"}

    extracted_result = await invoke_llm_with_image(image_url)
    return extracted_result
