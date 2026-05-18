echo "# 1. Try the alternate mirror (nomads) - same data, different host"
curl -sS -m 15 -o /dev/null -w "nomads: HTTP %{http_code} in %{time_total}s\n" \
  "https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/"
echo


echo "# 2. Force IPv4 (sometimes IPv6 fails silently)"
curl -4 -sS -m 15 -o /dev/null -w "ftp-v4: HTTP %{http_code} in %{time_total}s\n" \
  "https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/"
echo

echo "# 3. DNS sanity check"
nslookup ftp.ncep.noaa.gov
nslookup nomads.ncep.noaa.gov
