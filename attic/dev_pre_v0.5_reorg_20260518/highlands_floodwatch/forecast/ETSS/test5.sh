echo "# Last attempt at NOMADS: pretend to be a browser"
curl -sS -m 10 -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -o /tmp/etss_file.txt -w "HTTP %{http_code} | %{size_download} bytes\n" \
  "https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/etss.20260517/etss.t18z.stormtide.est.txt"

echo

echo "# And one more — try a parallel NOAA endpoint that should be open API"
curl -sS -m 10 -o /dev/null -w "NWS alerts: HTTP %{http_code} in %{time_total}s\n" \
  "https://api.weather.gov/alerts/active?point=40.4015,-73.991"
