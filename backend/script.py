import json
from collections import defaultdict

# Read JSON file
with open(r'C:\Users\anas_\Downloads\canonical_products.json', 'r', encoding="utf-8") as f:
    data = json.load(f)  # if array of objects
    # or data = [json.loads(line) for line in f]  # if JSONL

# Get unique values
unique = defaultdict(set)

for record in data:
    # String fields
    for field in ['category_l1', 'category_l2', 'halal_status']:
        if record.get(field):
            unique[field].add(record[field])
    
    # List fields
    for field in ['sold_in', 'cert_bodies', 'marketplace']:
        if record.get(field):
            unique[field].update(record[field])  # assumes list

# Convert sets to lists
result = {k: list(v) for k, v in unique.items()}

# Save to file
with open('unique_values.json', 'w') as f:
    json.dump(result, f, indent=2)