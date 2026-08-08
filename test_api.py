import requests
import time
import sys

BASE_URL = "http://localhost:8000"

print("Uploading CSV...")
with open("test_products.csv", "rb") as f:
    files = {"file": ("test_products.csv", f, "text/csv")}
    try:
        response = requests.post(f"{BASE_URL}/api/v1/upload", files=files)
    except requests.exceptions.ConnectionError:
        print("Failed to connect to the server. Is it running?")
        sys.exit(1)

if response.status_code != 200:
    print(f"Failed to upload: {response.text}")
    sys.exit(1)

batch = response.json()
batch_id = batch["id"]
print(f"Upload successful. Batch ID: {batch_id}")
print(f"Total rows to process: {batch['total_rows']}")

print("Polling batch status...")
while True:
    res = requests.get(f"{BASE_URL}/api/v1/batches/{batch_id}")
    if res.status_code != 200:
        print(f"Failed to get batch status: {res.text}")
        break
    status_data = res.json()
    print(f"Status: {status_data['status']}, Processed: {status_data['processed_rows']}/{status_data['total_rows']}")
    
    if status_data['status'] in ['COMPLETED', 'FAILED']:
        break
    time.sleep(5)

print("\nFetching enriched products...")
res = requests.get(f"{BASE_URL}/api/v1/products?size=3")
if res.status_code == 200:
    products = res.json()["products"]
    for p in products:
        print(f"\nProduct: {p['raw_name']}")
        print(f"Status: {p['status']}")
        print(f"SEO Desc: {p['seo_description']}")
        print(f"Tags: {p['category_tags']}")
else:
    print("Failed to fetch products.")
