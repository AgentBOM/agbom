"""Data models for AgentBOM."""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Model for tool parameter definition."""
    type: str
    required: bool = False
    description: Optional[str] = None


class ToolReturns(BaseModel):
    """Model for tool return value definition."""
    type: str
    description: Optional[str] = None


class ToolDetail(BaseModel):
    """Model for individual tool details."""
    tool_name: str
    description: str = "unknown"
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    returns: Optional[ToolReturns] = None
    integrations: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    category: Optional[str] = None


class Tools(BaseModel):
    """Model for agent tools."""
    count: int = 0
    details: List[ToolDetail] = Field(default_factory=list)


class Agent(BaseModel):
    """Model for an individual agent."""
    name: str
    repository: str
    type: Literal["LLM Agent", "SQL Agent", "Retrieval Agent"] = "LLM Agent"
    language: Literal["Python", "TypeScript"]
    frameworks: List[str]
    architecture: Literal["ReAct", "MAS", "Other"] = "Other"
    description: str = ""
    files: List[str]
    owner: str = "unknown"
    created_at: datetime
    updated_at: datetime
    x_last_changed_by: Optional[str] = None
    x_repo_default_branch: Optional[str] = None
    tools: Tools = Field(default_factory=Tools)


class AgentBOM(BaseModel):
    """Root model for Agent Bill of Materials."""
    agents: List[Agent] = Field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string."""
        # Serialize datetime objects properly
        data = self.model_dump()

        # Convert datetime objects to ISO format strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj

        data = convert_datetime(data)
        return json.dumps(data, indent=indent)

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return self.model_dump()