# src/schemas.py

from pydantic import BaseModel
from typing import List, Dict

class PermissionsResponse(BaseModel):
    permissions: List[str]