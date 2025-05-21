import json
import csv

# Path to the input JSON file
input_file = "/Users/mardoqueo/Downloads/wealth_of_nations_information/scrape/economists.json"

# Path to the output CSV file
output_file = "/Users/mardoqueo/Downloads/wealth_of_nations_information/scrape/economists.csv"

# Load JSON data
with open(input_file, "r", encoding="utf-8") as file:
    economists = json.load(file)

# Extract field names from the first record (keys of the dictionary)
fields = list(economists[0].keys())

# Write to CSV
with open(output_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()  # Write the header row
    writer.writerows(economists)  # Write all records

print(f"Data successfully converted to {output_file}")
