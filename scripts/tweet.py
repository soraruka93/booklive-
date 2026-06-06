#!/usr/bin/env python3
"""Monthly image tweet poster: picks a random image from images/ and a random tweet text."""

import json
import os
import random
import sys
from pathlib import Path

import tweepy

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def load_tweet_texts(config_path: Path) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    return [t["text"] for t in config["tweets"]]


def pick_random_image(images_dir: Path) -> Path | None:
    images = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not images:
        return None
    return random.choice(images)


def get_twitter_client() -> tuple[tweepy.Client, tweepy.API]:
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    # v1.1 API for media upload, v2 for tweet posting
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    return client_v2, api_v1


def main() -> None:
    repo_root = Path(__file__).parent.parent
    images_dir = repo_root / "images"
    config_path = repo_root / "tweet_config.json"

    tweet_texts = load_tweet_texts(config_path)
    tweet_text = random.choice(tweet_texts)

    image_path = pick_random_image(images_dir)
    if image_path is None:
        print("ERROR: No images found in images/ directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Selected image: {image_path.name}")
    print(f"Selected text: {tweet_text}")

    client_v2, api_v1 = get_twitter_client()

    # Upload image via v1.1 API (required for media upload)
    media = api_v1.media_upload(filename=str(image_path))
    print(f"Media uploaded: media_id={media.media_id}")

    # Post tweet via v2 API
    response = client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
    print(f"Tweet posted: id={response.data['id']}")


if __name__ == "__main__":
    main()
