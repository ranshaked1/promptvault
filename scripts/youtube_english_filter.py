"""
YouTube English-Only Video Filter

Uses the YouTube Data API v3 to search for videos filtered by English language.
The `relevanceLanguage=en` parameter prioritizes English-language content.

Usage:
    export YOUTUBE_API_KEY="your-api-key"
    python youtube_english_filter.py "machine learning"

To get an API key:
    1. Go to https://console.cloud.google.com/
    2. Create a project and enable the YouTube Data API v3
    3. Create an API key under Credentials
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_english_videos(query, api_key, max_results=10):
    """Search YouTube for English-language videos on a given topic."""
    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "type": "video",
        "relevanceLanguage": "en",
        "maxResults": max_results,
        "key": api_key,
    })

    url = f"{YOUTUBE_SEARCH_URL}?{params}"
    req = urllib.request.Request(url)

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())

    results = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        results.append({
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "video_id": item["id"]["videoId"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "published": snippet["publishedAt"],
            "description": snippet["description"][:150],
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Search YouTube for English-language videos")
    parser.add_argument("query", help="Search topic (e.g., 'machine learning')")
    parser.add_argument("--max-results", type=int, default=10, help="Number of results (default: 10)")
    args = parser.parse_args()

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: Set YOUTUBE_API_KEY environment variable.", file=sys.stderr)
        print("Get one at https://console.cloud.google.com/", file=sys.stderr)
        sys.exit(1)

    results = search_english_videos(args.query, api_key, args.max_results)

    for i, video in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"{i}. {video['title']}")
        print(f"   Channel: {video['channel']}")
        print(f"   URL: {video['url']}")
        print(f"   Published: {video['published']}")
        print(f"   {video['description']}...")


if __name__ == "__main__":
    main()
