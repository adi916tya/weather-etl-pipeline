"""Weather ETL pipeline: fetch -> save to SQLite -> chart.

Run: python weather_pipeline.py
Each run appends one reading per city to weather.db and
saves a fresh chart as avg_temp.png.
"""

import sqlite3

import matplotlib
matplotlib.use("Agg")  # no display needed, works on servers and GitHub Actions
import matplotlib.pyplot as plt
import pandas as pd
import requests

DB_FILE = "weather.db"
CHART_FILE = "avg_temp.png"
API_URL = "https://api.open-meteo.com/v1/forecast"

CITIES = {
    "Pune": (18.52, 73.86),
    "Bangalore": (12.97, 77.59),
    "Kolkata": (22.57, 88.36),
    "Ahmedabad": (23.02, 72.57),
    "Chennai": (13.08, 80.27),
    "Delhi": (28.61, 77.21),
}


def fetch_weather():
    """Extract + Transform: call the API for each city, return a DataFrame."""
    rows = []
    for city, (lat, lon) in CITIES.items():
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "timezone": "Asia/Kolkata",
        }
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        current = response.json()["current"]
        rows.append(
            {
                "city": city,
                "temperature_c": current["temperature_2m"],
                "timestamp": current["time"],
            }
        )
    return pd.DataFrame(rows)


MIN_TEMP, MAX_TEMP = -10, 55  # realistic range for India, in °C


def validate(df):
    """Data quality gate: stop with a clear error if anything looks wrong."""
    errors = []

    if len(df) != len(CITIES):
        errors.append(f"Expected {len(CITIES)} rows, got {len(df)}")

    if df[["city", "temperature_c", "timestamp"]].isnull().any().any():
        errors.append("Found missing (null) values")

    if df["city"].duplicated().any():
        errors.append("Found duplicate cities in one run")

    out_of_range = df[(df["temperature_c"] < MIN_TEMP) | (df["temperature_c"] > MAX_TEMP)]
    if not out_of_range.empty:
        errors.append(f"Temperature outside {MIN_TEMP} to {MAX_TEMP} °C:\n{out_of_range}")

    if errors:
        raise ValueError("Data validation failed:\n- " + "\n- ".join(errors))
    print("Validation passed")


def save_to_db(df):
    """Load: append the DataFrame to the weather table in SQLite."""
    with sqlite3.connect(DB_FILE) as conn:
        df.to_sql("weather", conn, if_exists="append", index=False)


def make_chart():
    """Analyze: average temperature per city, saved as a bar chart."""
    with sqlite3.connect(DB_FILE) as conn:
        avg = pd.read_sql(
            "SELECT city, AVG(temperature_c) AS avg_temp_c "
            "FROM weather GROUP BY city ORDER BY avg_temp_c DESC",
            conn,
        )
    plt.figure(figsize=(8, 5))
    plt.bar(avg["city"], avg["avg_temp_c"], color="orange")
    plt.title("Average Temperature per City")
    plt.xlabel("City")
    plt.ylabel("Temperature (°C)")
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()


def main():
    df = fetch_weather()
    print(df)
    validate(df)  # stops here if the data is bad, nothing gets saved
    save_to_db(df)
    make_chart()
    print(f"Saved to {DB_FILE} and chart to {CHART_FILE}")


if __name__ == "__main__":
    main()
