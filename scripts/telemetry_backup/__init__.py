"""System Telemetry Engine — real-time health metrics for LitigationOS."""
__version__ = "1.0.0"
from .engine import TelemetryEngine
from .dashboard import generate_dashboard
from .history import TelemetryHistory
