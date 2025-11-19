"""This is intended to increase the accuracy of the results from the gen AI API.
I am under no illusion that it will produce the best result, however, it will
provide valuable context that the user can build upon instead of having to type it
all. In its current state, the system works in 3 steps;
1. OCR from images
2. Reconstructing the text layout from the images
3. Gen AI inference from the text layout"""

import cv2
import json
from paddleocr import PaddleOCR
import numpy as np


# A helper class to handle NumPy arrays when creating JSON
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
    # Initialize OCR - use the recommended `use_textline_orientation` parameter
    ocr = PaddleOCR(use_textline_orientation=True, lang="en")

    # This list will hold the distilled data for all processed images
    all_images_data = []
    rec_texts_and_score_data = {"rec_texts": [], "rec_scores": []}
    structured_data = []
    raw_ocr_output = []

    for image_path in images:
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Warning: Could not read image at {image_path}. Skipping.")
            continue

        # Run OCR using the recommended 'predict' method
        results = ocr.predict(img)

        # A list to store structured data for the current image

        # Check if results were returned
        if results and results[0]:
            raw_ocr_output.append(results)
            # print(len(results))
            # for i in results:
            #     print(i)
            # The main data is in the first element of the results list
            ocr_output = results[0]

            # Extract the parallel lists of data
            texts = ocr_output.get("rec_texts", [])
            scores = ocr_output.get("rec_scores", [])
            polygons = ocr_output.get("rec_polys", [])
            rec_texts_and_score_data["rec_texts"].extend(texts)
            rec_texts_and_score_data["rec_scores"].extend(scores)

            # Iterate through the recognized texts and their associated data
            for i in range(len(texts)):
                text = texts[i]
                confidence = scores[i]
                bounding_box = polygons[i]

                # Estimate font size from the height of the bounding box
                # This is an approximation. Bounding box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                box_height = max(bounding_box[2][1], bounding_box[3][1]) - min(
                    bounding_box[0][1], bounding_box[1][1]
                )

                # You could sample the color here using the bounding_box and the original `img`
                # For simplicity, we'll leave it out, but this is where you'd do it.

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
