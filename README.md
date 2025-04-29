# SD1 - Film Production AI System

A comprehensive AI-powered system for film production planning and management.

## Features

- Script parsing and analysis
- Character breakdown and profiling
- Production scheduling and optimization
- Budget estimation and tracking
- Storyboard generation
- One-liner scene summaries

## Installation

Install the package directly from the repository:

```bash
pip install -e .
```

## Usage

```python
# Example: Script ingestion
from sd1.src.script_ingestion.coordinator import ScriptIngestionCoordinator

coordinator = ScriptIngestionCoordinator()
script_data = await coordinator.process_script(script_text)
```

## Dependencies

- fastapi
- uvicorn
- python-dotenv
- numpy
- pandas
- openai
- google-generativeai 