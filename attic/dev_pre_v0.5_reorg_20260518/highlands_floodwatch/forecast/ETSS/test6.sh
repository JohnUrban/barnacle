echo "# 1. What product types does Mt Holly NJ office (PHI) issue? Look for CFS, CFW, CFY, CFA"
curl -sS -m 10 "https://api.weather.gov/products/locations/PHI/types" | python3 -m json.tool | grep -E '"(productCode|productName)"' | head -40

echo

echo "# 2. Get the most recent Coastal Flood Statement (if any). Even old ones tell us the format."
curl -sS -m 10 "https://api.weather.gov/products/types/CFS/locations/PHI" | python3 -c "
import json, sys
data = json.load(sys.stdin)
products = data.get('@graph', [])
print(f'Found {len(products)} CFS products at PHI')
if products:
    p = products[0]
    print(f'Most recent: {p.get(\"issuanceTime\")}')
    print(f'Fetch with: curl {p[\"@id\"]}')
"
