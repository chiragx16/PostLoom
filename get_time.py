from datetime import datetime
import pytz

# Step 1: Parse the UTC string
utc_time_str = "2025-07-22T12:34:24.942877"
utc_time = datetime.fromisoformat(utc_time_str).replace(tzinfo=pytz.UTC)

# Step 2: Convert to IST
india_tz = pytz.timezone("Asia/Kolkata")
ist_time = utc_time.astimezone(india_tz)

print(ist_time.isoformat())  # ISO format
print(ist_time.strftime("%d-%m-%Y %I:%M:%S %p"))  # Custom format
