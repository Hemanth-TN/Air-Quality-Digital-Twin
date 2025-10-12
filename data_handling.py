import pandas as pd
from pathlib import Path

CITIES = ['Chicago', 'Sacremento']

DATA = {}
for city in CITIES:
    DATA[city] = pd.read_parquet(f"AQ_data_avg_parq/{city}.parquet.gz")

# Read all the filtered data files
FILTERED_DATA = {}
for city in CITIES:
    FILTERED_DATA[city] = pd.read_parquet(f"AQ_data_avg_parq/{city}_filtered.parquet.gz")

LIMITS_DATA = {}
for city in CITIES:
    limits_path = Path(f"./AQ_data_avg_parq/{city}_limits.parquet.gz")
    LIMITS_DATA[city] = pd.read_parquet(limits_path).set_index('pollutant') 

def get_location_data(df):
    location_data = df.groupby('location_name').agg(
        latitude=('latitude', 'first'),
        longitude=('longitude', 'first'),
        readings_available=('pollutant', lambda x: x.unique().tolist())
    ).reset_index()
    location_data['size'] = 1
    return location_data