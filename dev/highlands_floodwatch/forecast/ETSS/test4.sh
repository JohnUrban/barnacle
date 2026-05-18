echo "# Try a specific file URL (no listing - direct GET)"
curl -sS -m 10 -o /tmp/etss_file.txt -w "HTTP %{http_code} | %{size_download} bytes | %{time_total}s\n" \
  "https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/etss.20260517/etss.t18z.stormtide.est.txt"

echo

echo "# If you get HTTP 200, take a peek:"
head -50 /tmp/etss_file.txt
wc -l /tmp/etss_file.txt
