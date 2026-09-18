"""
MeetingPoint   --> Pydantic model for an individual topic point with transcript evidence
MeetingSection --> Pydantic model for a topic section grouping points
ActionItem     --> Pydantic model for an explicit action item with owner and deadline
MeetingReport  --> Pydantic model for the top-level immutable meeting report
"""

from skynet_core.models.base import FrozenModel


class MeetingPoint(FrozenModel):
    content: str
    evidence: str


class MeetingSection(FrozenModel):
    title: str
    points: list[MeetingPoint]


class ActionItem(FrozenModel):
    task: str
    owner: str | None = None
    deadline: str | None = None
    evidence: str


class MeetingReport(FrozenModel):
    overview: str
    action_items: list[ActionItem]
    sections: list[MeetingSection]
