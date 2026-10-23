"""Configuration commune des tests : rend le dossier du projet importable (import pipeline....)."""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
