# Weather ETL Pipeline

A small data engineering project that collects live temperatures for six Indian cities (Pune, Bangalore, Kolkata, Ahmedabad, Chennai, Delhi) and tracks them over time.

**Extract** from the free [Open-Meteo API](https://open-meteo.com/) (no API key needed) -> **Transform** with pandas -> **Load** into SQLite -> **Analyze** with SQL and a matplotlib chart.

## How to run

1. Install Python 3.9 or newer.
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the pipeline:
   ```
   python weather_pipeline.py
   ```

Each run adds one reading per city to the `weather` table in `weather.db` and saves an average-temperature chart as `avg_temp.png`.

## Check the data

`weather.db` is a binary SQLite file, so do not open it in a text editor. Query it instead:

```python
import sqlite3, pandas as pd
conn = sqlite3.connect("weather.db")
print(pd.read_sql("SELECT * FROM weather", conn))
```

## Files

- `weather_pipeline.py` - the full pipeline
- `requirements.txt` - Python dependencies
- `.github/workflows/weather.yml` - runs the pipeline every 6 hours on GitHub Actions

## Tools

Python, pandas, SQLite, matplotlib, GitHub Actions. All free.
