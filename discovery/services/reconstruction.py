# SLN307 a refined version of SLN304 combined with SLN300_A
# SLN300_A Solution 3, variant of solution 1 in Phase 2
import json
from typing import List, Dict, Any

import numpy as np


# --- Using the same simulated raw OCR output ---
# --- Helper functions ---
def get_box_center_y(polygon: np.ndarray):
    return np.mean(polygon[:, 1])


def get_box_height(polygon: np.ndarray) -> float:
    return np.max(polygon[:, 1]) - np.min(polygon[:, 1])


def get_box_x_start(polygon: np.ndarray) -> float:
    return np.min(polygon[:, 0])


def get_box_x_end(polygon: np.ndarray) -> float:
    return np.max(polygon[:, 0])


def get_avg_char_width(box: Dict[str, Any]) -> float:
    text = box["text"]
    width = get_box_x_end(box["polygon"]) - get_box_x_start(box["polygon"])
    if not text:
        return 0
    return width / len(text)


def reconstruct_text_with_columns(single_image_ocr_result: List[Dict[str, Any]]) -> str:
    """
    Reconstructs a text block by grouping text into lines and then detecting columns within each line.
    """
    if (
        not single_image_ocr_result
        or not isinstance(single_image_ocr_result, list)
        or not single_image_ocr_result[0]
    ):
        return ""

    ocr_data = single_image_ocr_result[0]

    if not ocr_data.get("rec_texts"):
        return ""

    # Step 1: Extract and prepare the data
    boxes_with_info = []
    for i in range(len(ocr_data["rec_texts"])):
        boxes_with_info.append(
            {
                "text": ocr_data["rec_texts"][i],
                "polygon": ocr_data["rec_polys"][i],
                "y_center": get_box_center_y(ocr_data["rec_polys"][i]),
            }
        )

    # Step 2: Sort all boxes from top to bottom
    sorted_boxes = sorted(boxes_with_info, key=lambda b: b["y_center"])

    # Step 3: Group boxes into rough physical lines
    all_lines = []
    if not sorted_boxes:
        return ""
    current_line = [sorted_boxes[0]]
    for i in range(1, len(sorted_boxes)):
        prev_box = current_line[-1]
        current_box = sorted_boxes[i]
        vertical_distance = abs(current_box["y_center"] - prev_box["y_center"])
        tolerance = (
            (
                get_box_height(prev_box["polygon"])
                + get_box_height(current_box["polygon"])
            )
            / 2
            * 0.7
        )
        if vertical_distance <= tolerance:
            current_line.append(current_box)
        else:
            all_lines.append(current_line)
            current_line = [current_box]
    all_lines.append(current_line)

    # Step 4: Detect columns within each line and assemble the final text
    reconstructed_text = ""
    # A tab is used as a machine-readable column separator.
    COLUMN_SEPARATOR = "\t\t"

    for line in all_lines:
        # Sort the boxes within each line from left to right
        line_sorted = sorted(line, key=lambda b: get_box_x_start(b["polygon"]))

        line_text = ""
        if not line_sorted:
            continue

        line_text += line_sorted[0]["text"]
        for i in range(len(line_sorted) - 1):
            current_box = line_sorted[i]
            next_box = line_sorted[i + 1]

            # Calculate the horizontal gap between the boxes
            gap = get_box_x_start(next_box["polygon"]) - get_box_x_end(
                current_box["polygon"]
            )

            # Heuristic for detecting a column break:
            # The gap must be larger than a few average character widths.
            avg_char_w = get_avg_char_width(current_box)
            # This factor is tunable. A lower number means more sensitive column detection.
            GAP_TOLERANCE_FACTOR = 3.0

            if avg_char_w > 0 and gap > avg_char_w * GAP_TOLERANCE_FACTOR:
                line_text += COLUMN_SEPARATOR
            else:
                line_text += " "

            line_text += next_box["text"]

        reconstructed_text += line_text + "\n"

    return reconstructed_text.strip()


def create_text_block_json(
    single_image_ocr_result: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Processes raw OCR results into a structured JSON containing page dimensions
    and a flat list of text blocks with their visual properties.

    Args:
        single_image_ocr_result: The raw OCR output for a single image.

    Returns:
        A dictionary structured for layout-aware LLM analysis.
    """
    # --- 1. Input Validation ---
    if not single_image_ocr_result or not single_image_ocr_result[0]:
        return {"page_dimensions": {"width": 0, "height": 0}, "text_blocks": []}

    ocr_data = single_image_ocr_result[0]
    if not ocr_data.get("rec_texts") or not ocr_data.get("rec_polys"):
        return {"page_dimensions": {"width": 0, "height": 0}, "text_blocks": []}

    text_blocks = []
    max_x, max_y = 0, 0

    # --- 2. Process Each Text Element Individually ---
    for i in range(len(ocr_data["rec_texts"])):
        text = ocr_data["rec_texts"][i]
        polygon = ocr_data["rec_polys"][i]

        # --- 3. Calculate Bounding Box from Polygon ---
        x_coords = polygon[:, 0]
        y_coords = polygon[:, 1]

        x_min = np.min(x_coords)
        y_min = np.min(y_coords)
        x_max = np.max(x_coords)
        y_max = np.max(y_coords)

        width = x_max - x_min
        height = y_max - y_min

        # Update overall page dimensions
        max_x = max(max_x, x_max)
        max_y = max(max_y, y_max)

        # --- 4. Estimate Font Size from Bounding Box Height ---
        # This is a direct and effective heuristic: font size correlates with height.
        font_size = int(height)

        # --- 5. Assemble the Text Block Object ---
        text_block = {
            "text": text,
            "font_size": font_size,
            "bounding_box": {
                "x": int(x_min),
                "y": int(y_min),
                "width": int(width),
                "height": int(height),
            },
        }
        text_blocks.append(text_block)

    # --- 6. Assemble the Final Output JSON ---
    output_json = {
        "page_dimensions": {"width": int(max_x), "height": int(max_y)},
        "text_blocks": text_blocks,
    }

    return output_json


def create_final_llm_input(
    single_image_ocr_result: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Combines the physical JSON layout and the semantic text reconstruction
    into a single, optimized JSON object for the LLM.
    """
    # 1. Get the layout-aware JSON with font sizes and bounding boxes
    layout_json = create_text_block_json(single_image_ocr_result)

    # 2. Get the reconstructed ASCII/text layout with semantic grouping
    reconstructed_text = reconstruct_text_with_columns(single_image_ocr_result)

    # 3. Combine them into one final object
    final_input = {
        "layout_metadata": layout_json,
        "reconstructed_text": reconstructed_text,
    }
    return final_input


def reconstruct_llm_input(raw_ocr_output: list) -> Dict[str, Any]:
    # --- Main execution loop ---
    sln307_result = ""
    for i, result in enumerate(raw_ocr_output):
        layout_json = create_final_llm_input(result)
        sln307_result += f"--- Layout-Aware JSON for Image {i + 1} ---\n"
        sln307_result += json.dumps(layout_json, indent=2)
        sln307_result += "\n"

    return sln307_result
