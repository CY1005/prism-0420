"""M08 Pydantic schemas — design/02-modules/M08-module-relation/00-design.md §7."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

RelationType = Literal["depends_on", "related_to", "conflicts_with"]


class RelationCreate(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    relation_type: RelationType
    notes: str | None = None

    @model_validator(mode="after")
    def check_no_self_loop(self) -> RelationCreate:
        if self.source_node_id == self.target_node_id:
            raise ValueError("source_node_id and target_node_id must differ")
        return self


class RelationUpdate(BaseModel):
    notes: str | None = None


class RelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relation_type: str
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class RelationListResponse(BaseModel):
    items: list[RelationResponse]
    total: int
