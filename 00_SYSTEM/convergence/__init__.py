"""OMEGA Convergence Certification System — scores unified LitigationOS readiness."""
__version__ = "1.0.0"
from .certifier import ConvergenceCertifier
from .wiring import WiringValidator
from .report import generate_report

__all__ = ["ConvergenceCertifier", "WiringValidator", "generate_report"]
