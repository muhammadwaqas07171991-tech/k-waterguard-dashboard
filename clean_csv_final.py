import os
import pandas as pd

p = os.path.expanduser('~') + '/water_quality_data/water_quality_records.csv'
df = pd.read_csv(p)
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df = df.dropna(subset=['timestamp'])

cleaned = []
for _, group in df.groupby(['station_name', 'timestamp'], dropna=False):
    coord_rows = group[group['latitude'].notna() & group['longitude'].notna()]
    if not coord_rows.empty:
        cleaned.append(coord_rows.iloc[-1])
    else:
        cleaned.append(group.iloc[-1])

cleaned_df = pd.DataFrame(cleaned).drop_duplicates(subset=['station_name', 'timestamp'], keep='last')
cleaned_df.to_csv(p, index=False)
print('saved', len(cleaned_df))
print(cleaned_df[['station_name', 'latitude', 'longitude', 'location_name']].head(20).to_string(index=False))
lat_nonnull = int(cleaned_df['latitude'].notna().sum())
lon_nonnull = int(cleaned_df['longitude'].notna().sum())
print('nonnull', lat_nonnull, lon_nonnull)
