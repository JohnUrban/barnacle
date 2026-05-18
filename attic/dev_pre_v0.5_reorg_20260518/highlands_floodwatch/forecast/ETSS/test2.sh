echo "#0. Confirm NOA reachable at all"
#curl -sS -m 10 -o /tmp/etss_test.txt -w "HTTP %{http_code} | %{size_download} bytes | %{time_total}s\n" \
#  "https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/" | head -5

echo "# 1. Confirm NOAA reachable at all"
curl -sS -m 10 -o /tmp/etss_test.html -w "HTTP %{http_code} | %{size_download} bytes | %{time_total}s\n" \
  "https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/"
echo

echo "# 2. Find a recent run directory by listing what's there"
curl -sS -m 10 "https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/" | grep -o 'etss\.[0-9]*' | sort -u | tail -5
echo

echo "# 3. Now try the new fetcher"
python3 etss_fetcher.py
echo 

echo "# 4. If that works, save the raw file so we can see the format"
python3 etss_fetcher.py --save etss_sample.txt
echo
