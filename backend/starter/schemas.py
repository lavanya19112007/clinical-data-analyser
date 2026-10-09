"""
Starter schemas for ATLAS -> MONITOR -> WATCH clinical trial review system.
These schemas define the core data contracts between stages.
"""

from typing import List, Optional, Any, Dict
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            for k, v in self.__class__.__dict__.items():
                if not k.startswith('_') and k not in kwargs and not callable(v):
                    setattr(self, k, v() if callable(v) else v)
        def dict(self):
            return {k: (v.dict() if hasattr(v, 'dict') else [i.dict() if hasattr(i, 'dict') else i for i in v] if isinstance(v, list) else v)
                    for k, v in self.__dict__.items()}
        def model_dump(self):
            return self.dict()

    def Field(default=None, default_factory=None):
        if default_factory is not None:
            return default_factory
        return default


class Question(BaseModel):
    """Reviewer question to Atlas."""
    text: str
    category: Optional[str] = None  # COUNT, LOOKUP, FINDING, TRAP
    parameters: Optional[Dict[str, Any]] = None


class Evidence(BaseModel):
    """Verifiable source record reference supporting an answer or finding."""
    record_id: str
    subject_id: Optional[str] = None
    domain: Optional[str] = None
    source_file: Optional[str] = None
    reason: Optional[str] = None
    variable: Optional[str] = None
    value: Optional[Any] = None
    unit: Optional[str] = None
    visit: Optional[str] = None
    date: Optional[str] = None


class Calculation(BaseModel):
    """Deterministic clinical rule calculation trace."""
    name: str
    formula: Optional[str] = None
    inputs: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None


class Answer(BaseModel):
    """Evidence-grounded answer to a reviewer question."""
    answer: str
    result: Any
    evidence: List[Evidence] = Field(default_factory=list)
    calculations: List[Calculation] = Field(default_factory=list)
    data_cut: Optional[int] = 1
    category: Optional[str] = None
