import pandas as pd
from pathlib import Path

CITIES = ['Chicago', 'Sacremento']

# Initialize empty dictionaries - load data lazily
DATA = {}
FILTERED_DATA = {}
LIMITS_DATA = {}

def get_data(city_name):
    """Load city data lazily when requested"""
    if city_name not in DATA:
        DATA[city_name] = pd.read_parquet(f"AQ_data_avg_parq/{city_name}.parquet.gz")
    return DATA[city_name]

def get_filtered_data(city_name):
    """Load filtered data lazily when requested"""
    if city_name not in FILTERED_DATA:
        FILTERED_DATA[city_name] = pd.read_parquet(f"AQ_data_avg_parq/{city_name}_filtered.parquet.gz")
    return FILTERED_DATA[city_name]

def get_limits_data(city_name):
    """Load limits data lazily when requested"""
    if city_name not in LIMITS_DATA:
        limits_path = Path(f"./AQ_data_avg_parq/{city_name}_limits.parquet.gz")
        LIMITS_DATA[city_name] = pd.read_parquet(limits_path).set_index('pollutant')
    return LIMITS_DATA[city_name] 

def get_location_data(df):
    location_data = df.groupby('location_name').agg(
        latitude=('latitude', 'first'),
        longitude=('longitude', 'first'),
        readings_available=('pollutant', lambda x: x.unique().tolist())
    ).reset_index()
    location_data['size'] = 1
    return location_data