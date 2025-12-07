"""This is intended to increase the accuracy of the results from the gen AI API.
I am under no illusion that it will produce the best result, however, it will
provide valuable context that the user can build upon instead of having to type it
all. In its current state, the system works in 3 steps;
1. OCR from images
2. Reconstructing the text layout from the images
3. Gen AI inference from the text layout"""
import os
import cv2
import json
import numpy as np

# 1. Define the variable as None initially.
# This is safe to import anywhere (API, Beat, Worker) because it consumes no memory yet.
GLOBAL_OCR = None


def get_ocr_engine():
    """
    Singleton accessor for PaddleOCR.
    Initializes the model ONLY if it hasn't been created yet.
    """
    global GLOBAL_OCR

    # 2. Check if it's already loaded
    if GLOBAL_OCR is None:
        print("Initializing PaddleOCR model (First Run)...")

        # Optional: Safety check to prevent accidental loading in API container
        # If you run a script locally, 'SERVICE_TYPE' might be None, so we allow that too.
        service_type = os.environ.get("SERVICE_TYPE", "local")
        if service_type not in ["celery-worker", "local"]:
            raise RuntimeError(f"Attempting to load OCR in unauthorized service: {service_type}")

        # Limit threads to prevent memory explosion
        from paddleocr import PaddleOCR  # Import inside to avoid top-level dependency issues

        # Initialize ONCE
        GLOBAL_OCR = PaddleOCR(
            use_textline_orientation=True,
            lang="en",
            ocr_version='PP-OCRv4',  # Explicitly use v4
            det_model_dir=None,  # Let it download the default (Mobile)
            rec_model_dir=None,
            cls_model_dir=None
        )

    return GLOBAL_OCR


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def process_image_with_ocr(images: list[str]):
    # 3. Get the global instance.
    # If this is the first task, it loads the model.
    # If this is the 100th task, it returns the existing model instantly.
    ocr_engine = get_ocr_engine()

    all_images_data = []
    rec_texts_and_score_data = {"rec_texts": [], "rec_scores": []}
    structured_data = []
    raw_ocr_output = []

    for image_path in images:
        img = cv2.imread(image_path)
        if img is None:
            print(f"Warning: Could not read image at {image_path}. Skipping.")
            continue

        # 4. Use the singleton instance
        results = ocr_engine.predict(img)

        if results and results[0]:
            raw_ocr_output.append(results)
            ocr_output = results[0]

            texts = ocr_output.get("rec_texts", [])
            scores = ocr_output.get("rec_scores", [])
            polygons = ocr_output.get("rec_polys", [])
            rec_texts_and_score_data["rec_texts"].extend(texts)
            rec_texts_and_score_data["rec_scores"].extend(scores)

            for i in range(len(texts)):
                text = texts[i]
                confidence = scores[i]
                bounding_box = polygons[i]

                # Calculate box height safely
                y_coords = [p[1] for p in bounding_box]
                box_height = max(y_coords) - min(y_coords)

                structured_entry = {
                    "text": text,
                    "confidence": float(confidence),
                    "bounding_polygon": bounding_box,
                    "estimated_font_size_px": int(box_height),
                }
                all_images_data.append(
                    [text, float(confidence), bounding_box, int(box_height)]
                )
                structured_data.append(structured_entry)

    return raw_ocr_output
