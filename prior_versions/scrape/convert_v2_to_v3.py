"""
Quick converter: Add pageids to V2 data to make it V3-compatible
"""
import json
import wikipedia
from datetime import datetime
import time

# Load V2 data
with open('economists_v2.json', 'r') as f:
    v2_data = json.load(f)

print(f"Loaded {len(v2_data)} entries from V2")

v3_data = []
processed = 0
skipped = 0

for entry in v2_data:
    # Skip entries without names or birth dates
    if not entry.get('name') or not entry.get('born'):
        skipped += 1
        continue

    # Extract pageid from URL (easier than API call)
    url = entry.get('url', '')
    name = entry['name']

    # Convert date string to timestamp
    born_str = entry.get('born')
    born_timestamp = None
    if born_str:
        try:
            dt = datetime.strptime(born_str, '%Y-%m-%d')
            born_timestamp = int(dt.timestamp())
        except:
            try:
                dt = datetime.strptime(born_str[:4], '%Y')
                born_timestamp = int(dt.timestamp())
            except:
                pass

    # Get pageid from URL (Wikipedia URLs end with the page title)
    pageid = None
    if url:
        try:
            page_title = url.split('/')[-1]
            page = wikipedia.page(page_title, auto_suggest=False)
            pageid = str(page.pageid)
            time.sleep(0.1)  # Small delay
        except:
            pass

    if not pageid or not born_timestamp:
        skipped += 1
        continue

    # Create V3 entry
    v3_entry = {
        'pageid': pageid,
        'name': name,
        'url': url,
        'born': born_timestamp,
        'died': None,  # V2 format not compatible
        'influences': entry.get('influences', []),
        'doctoral_advisors': entry.get('doctoral_advisors', []),
        'doctoral_students': entry.get('doctoral_students', []),
        'img': entry.get('image_url', '')
    }

    v3_data.append(v3_entry)
    processed += 1

    if processed % 10 == 0:
        print(f"Processed {processed} entries...")

    if processed >= 50:  # Limit to 50 for demo
        print("Reached 50 entries limit for demo")
        break

print(f"\nConverted {processed} entries, skipped {skipped}")

# Save V3 data
with open('../economists_v3_demo.json', 'w') as f:
    json.dump(v3_data, f, indent=2)

print(f"Saved to economists_v3_demo.json")
