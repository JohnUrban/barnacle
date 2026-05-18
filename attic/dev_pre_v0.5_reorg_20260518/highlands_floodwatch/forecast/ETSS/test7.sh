echo "#1. Single command to get the most recent one and see its text:"
curl -sS -m 10 "https://api.weather.gov/products/types/CFW/locations/PHI" | python3 -c "
import json, sys, urllib.request
data = json.load(sys.stdin)
products = data.get('@graph', [])
print(f'Found {len(products)} CFW products at PHI')
if not products:
    print('No recent CFW issued (calm period - no coastal flooding forecast)')
    sys.exit()
for p in products[:5]:
    print(f'  {p.get(\"issuanceTime\")}')
print()
print('--- Fetching most recent ---')
req = urllib.request.Request(products[0]['@id'], headers={'User-Agent':'barnacle'})
detail = json.loads(urllib.request.urlopen(req, timeout=10).read())
print(detail.get('productText', '(no productText)'))
"

echo

echo "#2. Archive query - all CFW from PHI in late Oct 2025"
curl -sS -m 10 "https://api.weather.gov/products/types/CFW/locations/PHI?start=2025-10-28T00:00:00Z&end=2025-10-31T00:00:00Z" | python3 -m json.tool | head -40

