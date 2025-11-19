# discovery/management/commands/import_fda_data.py

import json
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from discovery.models import Product, ProductMetadata


class Command(BaseCommand):
    help = "Loads product data from a JSON file downloaded from the FDA Ghana portal."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file", type=str, help="The path to the JSON file to import."
        )

    def handle(self, *args, **kwargs):
        json_file_path = kwargs["json_file"]

        try:
            with open(json_file_path, "r") as f:
                all_products_data = json.load(f)["data"]
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found at: {json_file_path}"))
            return
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Could not decode JSON from the file."))
            return

        # A set to keep track of product IDs we've already processed
        processed_product_ids = set()

        # Counters for the final report
        created_count = 0
        skipped_count = 0

        # Use a transaction to make the whole import process atomic
        # If any record fails, the entire import is rolled back.
        with transaction.atomic():
            for item in all_products_data:
                product_id = item.get("product_id")

                # Skip if we don't have a unique ID or if we've already seen it
                if not product_id or product_id in processed_product_ids:
                    skipped_count += 1
                    continue

                # --- Data Extraction and Cleaning ---

                # Use a helper function to extract volume/weight from the product name
                name = item.get("product_name", "Unnamed Product")
                volume_or_weight = self.extract_volume_or_weight(name)

                # Prepare data for the Product model
                product_data = {
                    "name": name,
                    "description": f"Registered as '{item.get('registration_number', 'N/A')}' with the FDA Ghana.",
                    "category": item.get("product_category", "Uncategorized"),
                    "manufacturer": item.get("manufacturer"),
                    "production_date": None,  # Not available in the source data
                    "expiry_date": None, #item.get("expiry_date"),
                    "distributor": item.get(
                        "representative_company_local_agent_applicant"
                    ),
                    "barcode": None,  # Not available in the source data
                }
                if not product_data.get("name"):
                    continue

                # Prepare data for the ProductMetadata model
                metadata_data = {
                    "net_weight": volume_or_weight.get("weight"),
                    "volume": volume_or_weight.get("volume"),
                    "country_of_origin": item.get("country_origin"),
                    # We can store extra, unmapped fields in additional_info
                    "additional_info": {
                        "fda_product_id": product_id,
                        "registration_number": item.get("registration_number"),
                        # "registration_date": item.get("registration_date"),
                        "status": item.get("status"),
                        "product_sub_category": item.get("product_sub_category"),
                        "client_name": item.get("client_name"),
                    },
                }

                # --- Database Insertion ---
                # Use update_or_create to avoid duplicates. It will update an existing
                # product if one with the same name is found, or create a new one.
                # A more robust check might use 'manufacturer' as well.
                product_obj, created = Product.objects.update_or_create(
                    name=product_data["name"], defaults=product_data
                )
                print(f"Product ID: {product_obj.id} FDA ID: {product_id} Created: {created}")

                # Create or update the associated metadata
                ProductMetadata.objects.update_or_create(
                    product=product_obj, defaults=metadata_data
                )

                if created:
                    created_count += 1

                processed_product_ids.add(product_id)

        # Final report
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {len(all_products_data)} items from the file."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count} new products."))
        self.stdout.write(
            self.style.WARNING(f"Skipped: {skipped_count} duplicate or invalid items.")
        )

    def extract_volume_or_weight(self, product_name):
        """
        A helper function to parse volume or weight from a product name string
        using regular expressions.
        Example: "Zuzu Juice ... -PET Bottle(500ml)" -> {'volume': '500ml'}
        """
        if not product_name:
            return {}

        # Volume units: milliliters, liters, fluid ounces
        volume_regex = re.compile(r"(\d+\s*(?:ml|l|fl\s*oz))", re.IGNORECASE)
        # Weight units: grams, kilograms, ounces, pounds
        weight_regex = re.compile(r"(\d+\s*(?:g|kg|oz|lb|lbs))", re.IGNORECASE)

        volume_match = volume_regex.search(product_name)
        if volume_match:
            return {"volume": volume_match.group(1)}

        weight_match = weight_regex.search(product_name)
        if weight_match:
            return {"weight": weight_match.group(1)}

        return {}
