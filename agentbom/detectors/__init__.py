"""Agent detection framework."""

from .base import BaseDetector, DetectorResult
from .langchain_py import LangChainPythonDetector
from .langchain_ts import LangChainTypeScriptDetector
from .autogen import AutoGenDetector
from .crewai import CrewAIDetector

__all__ = [
    'BaseDetector',
    'DetectorResult',
    'LangChainPythonDetector',
    'LangChainTypeScriptDetector',
    'AutoGenDetector',
    'CrewAIDetector',
]