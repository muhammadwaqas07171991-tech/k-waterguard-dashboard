import requests
import xml.etree.ElementTree as ET

url = 'http://apis.data.go.kr/1480523/WaterqualityServices/getIvstgWFS'
params = {
    'serviceKey': 'vZRnIWwOb32xPebHSXJgsUipLGqd5U58xA2H9d0nC+eehLWvEwLzGE4VdVQyAJ8XL+F0pxdEV/Eh16Qej4uUWQ==',
    'srsName': 'EPSG:5179',
    'maxFeatures': 3,
    'resultType': 'results',
}
r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
print('status', r.status_code)
print(r.text[:5000])

root = ET.fromstring(r.content)
for element in root.iter():
    tag = element.tag.split('}', 1)[-1]
    if tag.lower() in {'pos', 'coordinates', 'point', 'poslist', 'x', 'y', 'longitude', 'latitude', 'lon', 'lat'}:
        print(tag, '=>', element.text)
        for k, v in element.attrib.items():
            print(' attr', k, v)
