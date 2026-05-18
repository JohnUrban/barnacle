echo "Note: I am running all 3 commands regardless of what 1st or 2nd returns"
echo

echo "#1. Hit the alerts archive (this one supports event filtering)"
curl -sS -m 15 "https://api.weather.gov/alerts?point=40.4015,-73.991&event=Coastal+Flood+Warning&limit=3" \
  | python3 -c "
import json, sys, urllib.request
data = json.load(sys.stdin)
features = data.get('features', [])
print(f'Found {len(features)} past Coastal Flood Warnings near 342 Bay Ave')
for f in features:
    p = f['properties']
    print(f'  effective: {p.get(\"effective\")}')
    print(f'  headline:  {p.get(\"headline\")}')
    print()
if features:
    print('--- Most recent text follows ---')
    print(features[0]['properties']['description'])
    print()
    print('--- Instruction text ---')
    print(features[0]['properties']['instruction'] or '(none)')
"

echo

echo "#2. If that returns nothing, also try: <-- Note: I am running all 3 commands regardless of what 1st or 2nd returns"
curl -sS -m 15 "https://api.weather.gov/alerts?point=40.4015,-73.991&event=Coastal+Flood+Advisory&limit=3" \
  | python3 -m json.tool | head -120

echo "#3. And one more fallback — search by NWS zone instead of point (Eastern Monmouth NJ is zone NJZ014):"
curl -sS -m 15 "https://api.weather.gov/alerts?zone=NJZ014&event=Coastal+Flood+Warning&limit=5" \
  | python3 -m json.tool | head -60
