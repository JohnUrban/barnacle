echo "#1. IEM keeps the long-term NWS product archive"
curl -sS -m 15 "https://mesonet.agron.iastate.edu/api/1/nwstext_search.json?pil=CFWPHI&limit=10" \
  | python3 -m json.tool | head -40

echo

echo "#2. # Example - replace PRODUCT_ID with what the search returned"
curl -sS -m 15 "https://mesonet.agron.iastate.edu/api/1/nwstext/PRODUCT_ID.txt"

echo
echo

echo "#3. python3 nws_surge_parser.py"
python3 nws_surge_parser.py
