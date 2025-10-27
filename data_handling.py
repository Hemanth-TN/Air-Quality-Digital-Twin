import pandas as pd
from pathlib import Path

CITIES = ['Chicago', 'Sacramento','Bangalore','New Delhi']

# Initialize empty dictionaries - load data lazily
DATA = {}
FILTERED_DATA = {}
LIMITS_DATA = {}

def get_data(city_name):
    """Load city data lazily when requested"""
    if city_name not in DATA:
        DATA[city_name] = pd.read_parquet(f"AQ_data_avg_parq/{city_name}.parquet.gz")
    
    if city_name in ['Bangalore','New Delhi']:
        df_temp = DATA[city_name]
        M = {'so2': 64.066, 'no2': 46.0055, 'co': 28.01, 'o3': 48.00}
        mask_ppb = (df_temp['unit'] == 'ppb') & (df_temp['pollutant'].isin(M))
        factor = df_temp.loc[mask_ppb, 'pollutant'].map(M)
        df_temp.loc[mask_ppb, 'avg'] = df_temp.loc[mask_ppb, 'avg'] * factor / 24.45
        df_temp.loc[mask_ppb, 'unit'] = 'µg/m³'

        mask_ppm = (df_temp['unit'] == 'ppm') & (df_temp['pollutant'].isin(M))
        factor2 = df_temp.loc[mask_ppm, 'pollutant'].map(M)
        df_temp.loc[mask_ppm, 'avg'] = df_temp.loc[mask_ppm, 'avg'] * factor2 * 1000 / 24.45
        df_temp.loc[mask_ppm, 'unit'] = 'µg/m³'
        
    return DATA[city_name]

def get_filtered_data(city_name):
    """Load filtered data lazily when requested"""
    if city_name not in FILTERED_DATA:
        FILTERED_DATA[city_name] = pd.read_parquet(f"AQ_data_avg_parq/{city_name}_filtered.parquet.gz").set_index('Timestamp')
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