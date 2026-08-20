# import json
# from collections import defaultdict

# # Read JSON file
# with open(r'C:\Users\anas_\Downloads\canonical_products.json', 'r', encoding="utf-8") as f:
#     data = json.load(f)  # if array of objects
#     # or data = [json.loads(line) for line in f]  # if JSONL

# # Get unique values
# unique = defaultdict(set)

# for record in data:
#     # String fields
#     for field in ['category_l1', 'category_l2', 'halal_status']:
#         if record.get(field):
#             unique[field].add(record[field])
    
#     # List fields
#     for field in ['sold_in', 'cert_bodies', 'marketplace']:
#         if record.get(field):
#             unique[field].update(record[field])  # assumes list

# # Convert sets to lists
# result = {k: list(v) for k, v in unique.items()}

# # Save to file
# with open('unique_values.json', 'w') as f:
#     json.dump(result, f, indent=2)


# import json
# from pathlib import Path
# input_file = r'C:\Users\anas_\Downloads\canonical_products.json'
# output_file = 'unqiue_values.json'
# # Load existing data from unique_values.json if it exists
# existing_data = {}
# if Path(output_file).exists():
#     with open(output_file, 'r', encoding='utf-8') as f:
#         existing_data = json.load(f)

# # Load canonical products
# with open(input_file, 'r', encoding='utf-8') as f:
#     data = json.load(f)  # array of objects

# # Initialize stats
# stats = {
#     "typical_uses": {
#         "max_length": 0,
#         "min_length": float('inf'),
#         "max_value": None,
#         "min_value": None,
#         "total_length": 0,
#         "count": 0,
#         "max_word_count": 0,
#         "min_word_count": float('inf'),
#         "total_words": 0
#     },
#     "health_info": {
#         "max_length": 0,
#         "min_length": float('inf'),
#         "max_value": None,
#         "min_value": None,
#         "total_length": 0,
#         "count": 0,
#         "max_word_count": 0,
#         "min_word_count": float('inf'),
#         "total_words": 0
#     }
# }

# def analyze_field(field_name, field_stats):
#     """Analyze a field and update stats."""
#     for record in data:
#         field_value = record.get(field_name)
#         if not field_value or not isinstance(field_value, list):
#             continue
        
#         # For each item in the list (if it's a list of strings)
#         for item in field_value:
#             if not isinstance(item, str):
#                 continue
            
#             item_length = len(item)
#             word_count = len(item.split())
            
#             # Update length stats
#             if item_length > field_stats["max_length"]:
#                 field_stats["max_length"] = item_length
#                 field_stats["max_value"] = item
#             if item_length < field_stats["min_length"]:
#                 field_stats["min_length"] = item_length
#                 field_stats["min_value"] = item
            
#             # Update word count stats
#             if word_count > field_stats["max_word_count"]:
#                 field_stats["max_word_count"] = word_count
#             if word_count < field_stats["min_word_count"]:
#                 field_stats["min_word_count"] = word_count
            
#             # Accumulate for averages
#             field_stats["total_length"] += item_length
#             field_stats["total_words"] += word_count
#             field_stats["count"] += 1

# # Analyze both fields
# analyze_field("typical_uses", stats["typical_uses"])
# analyze_field("health_info", stats["health_info"])

# # Calculate averages
# for field_name, field_stats in stats.items():
#     if field_stats["count"] > 0:
#         field_stats["avg_length"] = field_stats["total_length"] / field_stats["count"]
#         field_stats["avg_word_count"] = field_stats["total_words"] / field_stats["count"]
#     else:
#         field_stats["avg_length"] = 0
#         field_stats["avg_word_count"] = 0
#         field_stats["min_length"] = 0
#         field_stats["min_word_count"] = 0

# # Prepare data to append
# new_data = {
#     "analysis_results": stats
# }

# # Merge with existing data
# existing_data.update(new_data)

# # Write back to unique_values.json
# with open(output_file, 'w', encoding='utf-8') as f:
#     json.dump(existing_data, f, indent=2, ensure_ascii=False)

# # Print results
# print("=" * 60)
# print("ANALYSIS RESULTS")
# print("=" * 60)

# for field_name, field_stats in stats.items():
#     print(f"\n📊 {field_name.upper()}:")
#     print(f"  Total items analyzed: {field_stats['count']}")
#     if field_stats['count'] > 0:
#         print(f"  Longest string: {field_stats['max_length']} chars")
#         print(f"    Value: {field_stats['max_value'][:100]}...")
#         print(f"  Shortest string: {field_stats['min_length']} chars")
#         print(f"    Value: {field_stats['min_value'][:100]}...")
#         print(f"  Average length: {field_stats['avg_length']:.2f} chars")
#         print(f"  Max word count: {field_stats['max_word_count']} words")
#         print(f"  Min word count: {field_stats['min_word_count']} words")
#         print(f"  Average word count: {field_stats['avg_word_count']:.2f} words")
#     else:
#         print("  No data found")

# print(f"\n✅ Results appended to: {output_file}")



# import json
# from pathlib import Path

# input_file = r'C:\Users\anas_\Downloads\canonical_products.json'
# output_file = 'average_field_size.json'

# # Load canonical products
# with open(input_file, 'r', encoding='utf-8') as f:
#     data = json.load(f)

# fields = [
#     "canonical_id", "norm_name", "companies", "cert_bodies", "typical_uses",
#     "marketplace", "category_l1", "category_l2", "halal_status", "sold_in",
#     "cert_numbers", "health_info", "fda_numbers", "barcodes"
# ]

# stats = {}
# for field in fields:
#     stats[field] = {
#         "total_bytes": 0,
#         "count": 0,
#         "max_bytes": 0,
#         "min_bytes": float('inf'),
#         "total_items": 0
#     }

# for record in data:
#     for field in fields:
#         value = record.get(field)
#         if value is None:
#             continue
            
#         if isinstance(value, str):
#             byte_size = len(value)
#             stats[field]["total_bytes"] += byte_size
#             stats[field]["count"] += 1
#             stats[field]["total_items"] += 1
#             stats[field]["max_bytes"] = max(stats[field]["max_bytes"], byte_size)
#             stats[field]["min_bytes"] = min(stats[field]["min_bytes"], byte_size)
            
#         elif isinstance(value, list):
#             if not value:
#                 continue
#             stats[field]["count"] += 1
#             for item in value:
#                 if isinstance(item, str):
#                     item_bytes = len(item)
#                     stats[field]["total_bytes"] += item_bytes
#                     stats[field]["total_items"] += 1
#                     stats[field]["max_bytes"] = max(stats[field]["max_bytes"], item_bytes)
#                     stats[field]["min_bytes"] = min(stats[field]["min_bytes"], item_bytes)

# # Calculate averages
# for field in fields:
#     if stats[field]["count"] > 0:
#         stats[field]["avg_bytes"] = stats[field]["total_bytes"] / stats[field]["count"]
#         stats[field]["avg_bytes_per_item"] = stats[field]["total_bytes"] / stats[field]["total_items"]
#     else:
#         stats[field]["avg_bytes"] = 0
#         stats[field]["avg_bytes_per_item"] = 0
#         stats[field]["min_bytes"] = 0

# # Save to file
# with open(output_file, 'w', encoding='utf-8') as f:
#     json.dump(stats, f, indent=2, ensure_ascii=False)