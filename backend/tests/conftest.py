import sys
from pathlib import Path

# Make the backend packages (agent, rag, config, ...) importable the same way the app runs them.
# Settings are loaded on first import, so each suite's own conftest sets its environment before importing the app.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
