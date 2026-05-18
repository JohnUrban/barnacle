echo "# Put both files in the same directory (nws_surge_parser.py and flood_forecast_daily.py)"
echo 
echo "python3 nws_surge_parser.py --self-test    # should print PASS"
python3 nws_surge_parser.py --self-test    # should print PASS
echo
echo "python3 flood_forecast_daily.py --dry-run  # should print today's email"
python3 flood_forecast_daily.py --dry-run  # should print today's email
