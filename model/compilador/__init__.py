"""Compilador package: SPL parser and pipeline"""

from .flex_pipeline import pipeline_from_text
from .parser_spl import compile_high_level

__all__ = ["pipeline_from_text", "compile_high_level"]
