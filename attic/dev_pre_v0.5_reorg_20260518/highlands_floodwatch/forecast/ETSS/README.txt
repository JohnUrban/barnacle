Extra-Tropical Storm Surge (ETSS)

- NOAA's ETSS (Extra-Tropical Storm Surge) model has Sandy Hook on its station list, runs 4x daily, and publishes results as text files in a public NOMADS directory. 
	- That's exactly what we want — forecast total water level (predicted tide + forecast surge + 5-day error correction) for Sandy Hook, refreshed every 6 hours. Let me find the actual file format.
	- Runs 4x daily (00z, 06z, 12z, 18z) on operational government infrastructure
	- Forecasts total water level (= astronomical tide + storm surge + 5-day error correction) for the next ~96 hours
	- Lists Sandy Hook NJ explicitly on its 82-station East Coast list
	- Publishes results as plain text files in a public NOMADS directory: https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/etss.YYYYMMDD/etss.tNNz.stormtide.est.txt
	- The "5-day average anomaly" baked in handles the same job our "current surge persists" heuristic was trying to do, but better — it learns from rolling forecast-vs-observation errors and corrects automatically

- NOAA's ETSS publishes daily forecast directories at https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/etss.YYYYMMDD/.
	- The East coast text file etss.tNNz.stormtide.est.txt should contain Sandy Hook. 
- the files exist at https://ftp.ncep.noaa.gov/data/nccf/com/etss/prod/etss.YYYYMMDD/etss.tNNz.stormtide.est.txt 



