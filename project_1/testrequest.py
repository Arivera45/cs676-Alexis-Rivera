"""
Additional Project Tests

These tests were created beyond the provided test_credibility.py
suite to validate page-level metadata extraction, preprint
detection, and Cloudflare handling.
"""

import requests
from credibility import _extract_page_metadata
from credibility import score_url


print("=" * 60)
print("TEST 1: Nature Metadata Extraction")
print("=" * 60)

nature_url = "https://www.nature.com/articles/s41586-021-03819-2"

print("URL:", nature_url)
print(_extract_page_metadata(nature_url))

print("\n")


print("=" * 60)
print("TEST 2: bioRxiv Cloudflare Handling")
print("=" * 60)

biorxiv_url = "https://www.biorxiv.org/content/10.1101/2020.01.01.0000"

print("URL:", biorxiv_url)

try:
    response = requests.get(biorxiv_url, timeout=5)
    print(response.text[:1000])
except Exception as e:
    print("Error:", e)

print("\n")


print("=" * 60)
print("TEST 3: arXiv Metadata Extraction")
print("=" * 60)

arxiv_url = "https://arxiv.org/abs/1706.03762"

print("URL:", arxiv_url)
print(_extract_page_metadata(arxiv_url))

print("\n")


print("=" * 60)
print("TEST 4: Basic Page Retrieval")
print("=" * 60)

try:
    response = requests.get(nature_url, timeout=5)
    print("Successfully fetched page.")
    print(response.text[:500])
except Exception as e:
    print("Error:", e)

print("\n")


print("=" * 60)
print("TEST 5: Credibility Score + Explanation")
print("=" * 60)

result = score_url(nature_url)

print("Score:", result["score"])
print("Explanation:", result["explanation"])

print("\nDone.")