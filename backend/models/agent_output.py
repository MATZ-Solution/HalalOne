from pydantic import BaseModel
from typing import Optional, List

class OutputSchema(BaseModel):
    # response: Optional[str] = None
    norm_name: Optional[str] = None
    companies: Optional[List[str]] = None
    cert_bodies: Optional[List[str]] = None
    typical_uses: Optional[List[str]] = None
    marketplace: Optional[List[str]] = None
    category_l1: Optional[str] = None
    category_l2: Optional[str] = None
    halal_status: Optional[str] = None
    sold_in: Optional[List[str]] = None
    cert_numbers: Optional[List[str]] = None
    health_info: Optional[List[str]] = None
    source_ids: Optional[List[str]] = None
    source_files: Optional[List[str]] = None
    fda_numbers: Optional[List[str]] = None
    barcodes: Optional[List[str]] = None