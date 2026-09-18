"""
FrozenModel --> Base Pydantic model dùng chung, dữ liệu immutable và cấm field ngoài schema.
"""

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )
