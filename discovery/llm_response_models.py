from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    net_weight: Optional[str] = Field(
        default=None,
        description="Net weight of the product, including units (e.g., '500 g', '2 lbs').",
    )
    volume: Optional[str] = Field(
        default=None,
        description="Volume of the product, including units (e.g., '250 ml', '12 fl oz').",
    )
    quantity_in_package: Optional[int] = Field(
        default=None,
        description="The number of individual items in the package (e.g., 60 for a 60-pack of pads).",
    )
    size: Optional[int] = Field(
        default=None,
        description="The size of the product(e.g., Large, Medium, Small, Pro, Pro-Max, Jumbo).",
    )
    part_number: Optional[int] = Field(
        default=None,
        description="Part number of the product, OEM or aftermarket part number.",
    )
    age_rating: Optional[int] = Field(
        default=None,
        description="Age rating of the product, (e.g. 18+ for alcohol, 7+ for toys with risk of choking toys).",
    )
    country_of_origin: Optional[str] = Field(default=None)
    ingredients: Optional[List[str]] = Field(
        default=None, description="List of ingredients."
    )
    materials: Optional[List[str]] = Field(
        default=None, description="List of materials for non-food items."
    )
    warnings: Optional[List[str]] = Field(default=None)
    usage_directions: Optional[str] = Field(default=None)
    additional_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="A dictionary for any other relevant metadata not covered by other fields, such as 'energy_per_serving' or 'BPA-free'.",
    )


class ProductInfo(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    category: str = Field(...)
    manufacturer: Optional[str] = Field(default=None)
    production_date: Optional[str] = Field(
        default=None,
        description="Production date of the product, if date is available but no day, set 01 as day in format yyyy-MM-dd",
    )
    expiry_date: Optional[str] = Field(
        default=None,
        description="Expiry date of the product, if date is available but no day, set 01 as day in format yyyy-MM-dd",
    )
    distributor: Optional[str] = Field(default=None)
    barcode: Optional[str] = Field(default=None)
    metadata: Metadata = Field(...)
