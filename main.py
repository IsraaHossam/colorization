from fastapi import FastAPI, UploadFile, File, HTTPException
from contextlib import asynccontextmanager
from PIL import Image
from io import BytesIO
import base64
import torch
import os
import sys
import subprocess
import numpy as np

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clone the repo if it doesn't exist
    repo_url = "https://github.com/lehbchau/palette-extraction-and-colorization.git"
    clone_dir = "palette_repo"

    if not os.path.exists(clone_dir):
        subprocess.run(["git", "clone", repo_url, clone_dir])

    # Add src to sys.path
    repo_src = os.path.join(clone_dir, "src")
    sys.path.extend([os.path.abspath(clone_dir), os.path.abspath(repo_src)])

    # Import and initialize model globally
    global GrayscaleColorizer, colorizer
    from src.colorize import GrayscaleColorizer
    colorizer = GrayscaleColorizer()

    yield  # Run the app

app = FastAPI(lifespan=lifespan)

@app.post("/colorize")
async def colorize(uploaded_file: UploadFile = File(...)):
    try:
        img_bytes = await uploaded_file.read()
        image = Image.open(BytesIO(img_bytes)).convert("RGB")
         
        # Preprocess and colorize
        image_np = np.array(image)
        tens_l_orig, tens_l_rs = colorizer.preprocess_img(image_np, HW=(256, 256))
        out_ab = colorizer.model(tens_l_rs).cpu()
        colorized = colorizer.postprocess_tens(tens_l_orig, out_ab)

        # Convert tensor to image and encode to base64
        image_array = (colorized * 255).astype("uint8")
        output_img = Image.fromarray(image_array)
        buffer = BytesIO()
        output_img.save(buffer, format="JPEG")
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {"image_base64": img_str}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
