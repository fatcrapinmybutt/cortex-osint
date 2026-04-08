"""SENTINEL — Self-Organizing File Daemon.

Watches drives for new files, classifies them by litigation lane,
copies to canonical locations, and registers in the database.
"""
__version__ = "1.0.0"

from .watcher import SentinelWatcher
from .classifier import FileClassifier
