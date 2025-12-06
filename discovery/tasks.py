from celery import shared_task

from discovery.serializers import ProductSerializer
from discovery.services.ocr import process_image_with_ocr
from discovery.services.reconstruction import reconstruct_llm_input
from discovery.services.gen_ai import infer_product_details
from discovery.models import Product, ProductMetadata


@shared_task
def process_product_images(image_paths: list):
    """
    Celery task to perform the full OCR and AI inference pipeline.
    """
    # 1. OCR from images
    raw_ocr_output = process_image_with_ocr(images=image_paths)
    print("RAW OCR OUTPUT", raw_ocr_output)

    # 2. Reconstruct text layout
    reconstructed_text = reconstruct_llm_input(raw_ocr_output)
    print("RECONSTRUCTED TEXT", reconstructed_text)

    # 3. Gen AI inference
    product_data = infer_product_details(reconstructed_text)
    print("PRODUCT DATA", product_data)
    if not product_data:
        print("Product data is null or empty")
        return None
    # 4. Save to database
    metadata = product_data.pop("metadata", {})
    product = Product.objects.create(**product_data)
    ProductMetadata.objects.create(product=product, **metadata)
    product.refresh_from_db()

    return ProductSerializer(product).data


@shared_task
def process_structured_text(structured_text: str):
    """
    Celery task for when OCR data is already provided.
    """
    # 1. Gen AI inference
    product_data = infer_product_details(structured_text)
    if not product_data:
        print("Product data is null or empty text")
        return None
    # 2. Save to database
    metadata = product_data.pop("metadata", {})
    product = Product.objects.create(**product_data)
    ProductMetadata.objects.create(product=product, **metadata)

    product.refresh_from_db()

    return ProductSerializer(product).data


"""curl 'https://verifypermit.fdaghana.gov.gh/publicsearch?draw=1&columns%5B0%5D%5Bdata%5D=DT_RowIndex&columns%5B0%5D%5Bsearchable%5D=false&columns%5B1%5D%5Bdata%5D=client_name&columns%5B1%5D%5Bname%5D=tbl_client_details.client_name&columns%5B2%5D%5Bdata%5D=product_name&columns%5B3%5D%5Bdata%5D=product_category&columns%5B4%5D%5Bdata%5D=expiry_date&columns%5B5%5D%5Bdata%5D=status&columns%5B5%5D%5Bname%5D=tbl_products_details.status&columns%5B6%5D%5Bdata%5D=action&columns%5B6%5D%5Bsearchable%5D=false&columns%5B6%5D%5Borderable%5D=false&order%5B0%5D%5Bcolumn%5D=1&order%5B0%5D%5Bdir%5D=desc&start=0&length=25&search%5Bvalue%5D=&_=1763133604095' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Accept-Language: en-US,en;q=0.5' \
  -H 'Accept-Encoding: gzip, deflate, br, zstd' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Connection: keep-alive' \
  -H 'Referer: https://verifypermit.fdaghana.gov.gh/publicsearch' \
  -H 'Cookie: XSRF-TOKEN=eyJpdiI6IkltZUFLTnJITmVDMkI4ZllMRzR4dlE9PSIsInZhbHVlIjoiNzVaeExzLzZjcVU2MTlNY2tINzZtMmtyNy8rQUdlWGxRSG9teDE2ajdMOTd3UXA5a3Q2eXBJYjNKVzA1UURXVzlOVkYvUFpRdlNLTDMxcnZKSFc0dEF3UURYbk9pdFhtTnE4VkRPc0g5cnRXcjBqdGhpcWd6VjF0WjA1UnkwODEiLCJtYWMiOiI5Yzk5NzQ4ZGJmN2YzNDY5MmUzMDE3ZmZiMTI1ZmZhMWMzMTg2NTY2NjRkZmM4NjQwNDIwNzAyZTBkZjY3YTg1IiwidGFnIjoiIn0%3D; clientdbs_v3_session=eyJpdiI6IkZTM1JkRlRvRXVPZzBkaGlML0FnclE9PSIsInZhbHVlIjoiZUNPMkJPeW9BOFl2NEFYdDF1aldwYVJKM09KZytDZjRUb3ZQK01oYnNCZTZKYk5iUzhZVDZsVlZ5elhDRVFuMElhZXgxQVQwSzFNWjJqKzVVQ1B2cGIrTVFzU2VRWWpwNDBlZlVBdGpmY3Bkd212b3A1amRCU0FLU1Q2cWRhYXgiLCJtYWMiOiJhYTU5MjM3NzhkOTQxNDZlZGI1YWMzMjYxNDU5M2I4OWIyOWJkYTgwOWU0NGZjZDAzZDkwOTJkMGUyMDZjMDAwIiwidGFnIjoiIn0%3D' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Pragma: no-cache' \
  -H 'Cache-Control: no-cache'"""
