import json
import os

from discovery.llm_response_models import ProductInfo

prompt = {
    "role": "system",
    "content": """
    You are an expert data extractor specializing in analyzing product package information. Your task is to meticulously analyze the provided structured data from a product image and populate a `ProductInfo` schema with high accuracy.

    ---
    ### 1. Your Input Data Structure

    You will be provided with a JSON object containing two primary sources of information:

    *   **`layout_metadata`**: A JSON object containing a list of all `text_blocks`. Each block includes:
        *   `text`: The raw text content.
        *   `font_size`: An estimated numerical size of the text, indicating its visual prominence.
        *   `bounding_box`: The precise x/y coordinates and dimensions of the text on the package.

    *   **`reconstructed_text`**: A single string of pre-processed text that groups words into lines and uses tabs (`\t`) to represent columns. This provides the semantic reading order.

    ---
    ### 2. Your Analysis Strategy

    You must use both data sources together to achieve the most accurate extraction.

    1.  **Read for Context First**: Start by reading the `reconstructed_text` to understand the overall layout, the flow of information, and how words are grouped into sentences and tables.

    2.  **Cross-Reference for Importance**: As you analyze the `reconstructed_text`, you must cross-reference key phrases with the `layout_metadata`. Use the `font_size` as a definitive indicator of importance.
        *   **Large `font_size`**: Almost always indicates the Brand Name, Product Name, or a key feature like Quantity.
        *   **Small `font_size`**: Typically indicates ingredients, warnings, distributor information, or other fine print.

    3.  **Use Proximity for Grouping**: Use the `bounding_box` data to confirm relationships. Text blocks that are physically close to each other are related (e.g., a header like "Ingredients:" and the list that follows).

    ---
    ### 3. Key Fields to Extract

    Your primary goal is to populate the `ProductInfo` schema. Pay special attention to extracting the following critical attributes:

    *   **`name`**: Construct the full product name from the most prominent text, as identified by the largest `font_size`.
    *   **`production_date`**: Construct the production date from lot numbers, mfg, etc.
    *   **`expiry_date`**: Construct the expiry date from exp, bb, bbe etc.
    *   **`manufacturer`**: Construct the manufacturer information from associated text like fabricated by, LTD, industries etc.
    *   **`distributor`**: Construct the distributor information from associated text like fabricated by, LTD, industries etc.
    *   **`net_weight`**: The weight of the product (e.g., "500g", "2 lbs").
    *   **`volume`**: The liquid volume of the product (e.g., "250ml", "12 fl oz").
    *   **`quantity_in_package`**: The number of items in the pack (e.g., 56, 12).
    *   **`dimensions`**: Physical size of the product or package.
    *   **`country_of_origin`**: The country where the product was made.
    *   **`materials` / `ingredients`**: The composition of the product.
    *   **`warnings`**: Any safety or allergy warnings.
    *   **`usage_directions`**: Instructions on how to use the product.
    *   **`barcode` / `part_number`**: Any unique identifiers.

    ---
    ### 4. Output Formatting Rules

    *   Be brief, factual, and precise.
    *   Do not use hedging language or modal expressions (e.g., "it appears to be", "this might be").
    *   Where possible, standardize keys in any final metadata dictionary (e.g., use `net_weight` not `wt.`).
    """,
}

from openai import OpenAI
import instructor
import re


def infer_product_details(_ocr_data):
    if _orc_data.get("reconstructed_text", "") == "":
        return None
    client = instructor.patch(OpenAI(api_key=os.environ.get("LLM_API_KEY")))

    cleaned = re.sub(r"\s+", " ", str(_ocr_data)).strip()
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[prompt, {"role": "user", "content": str(cleaned)}],
        response_model=ProductInfo,
        # max_completion_tokens=2048
    )

    product = response
    token_usage = response._raw_response.usage

    # --- Print the results ---
    print(f"Prompt Tokens:     {token_usage.prompt_tokens}")
    print(f"Completion Tokens: {token_usage.completion_tokens}")
    print(f"Total Tokens:      {token_usage.total_tokens}")
    print(product.model_dump_json(indent=2))
    return json.loads(product.model_dump_json(indent=2))
