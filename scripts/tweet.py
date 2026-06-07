#!/usr/bin/env python3
"""Monthly image tweet poster: picks a random episode folder and posts all images as a thread."""

import json
import os
import random
import sys
from pathlib import Path

import tweepy

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGES_PER_TWEET = 4


def load_default_texts(config_path: Path) -> list[str]:
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    return [t["text"] for t in config["tweets"]]


def pick_random_episode(images_dir: Path) -> Path | None:
    episodes = [p for p in images_dir.iterdir() if p.is_dir()]
    if not episodes:
        return None
    return random.choice(episodes)


def get_episode_images(episode_dir: Path) -> list[Path]:
    return sorted(
        p for p in episode_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def get_tweet_text(episode_dir: Path, default_texts: list[str]) -> str:
    # エピソードフォルダ内に tweet.txt があればそれを使う、なければ共通テキストからランダム選択
    tweet_txt = episode_dir / "tweet.txt"
    if tweet_txt.exists():
        return tweet_txt.read_text(encoding="utf-8").strip()
    return random.choice(default_texts)


def get_twitter_client() -> tuple[tweepy.Client, tweepy.API]:
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    return client_v2, api_v1


def upload_images(api_v1: tweepy.API, image_paths: list[Path]) -> list[int]:
    media_ids = []
    for path in image_paths:
        media = api_v1.media_upload(filename=str(path))
        media_ids.append(media.media_id)
        print(f"  Uploaded: {path.name} -> media_id={media.media_id}")
    return media_ids


def post_thread(
    client_v2: tweepy.Client,
    api_v1: tweepy.API,
    first_tweet_text: str,
    images: list[Path],
) -> None:
    chunks = [images[i:i + IMAGES_PER_TWEET] for i in range(0, len(images), IMAGES_PER_TWEET)]
    total = len(chunks)
    previous_tweet_id = None

    for i, chunk in enumerate(chunks):
        print(f"Posting tweet {i + 1}/{total} ({len(chunk)} images)...")
        media_ids = upload_images(api_v1, chunk)

        # 1ツイート目だけ本文テキストを付ける、以降はスレッド番号のみ
        text = first_tweet_text if i == 0 else f"({i + 1}/{total})"

        kwargs: dict = {"text": text, "media_ids": media_ids}
        if previous_tweet_id is not None:
            kwargs["in_reply_to_tweet_id"] = previous_tweet_id

        response = client_v2.create_tweet(**kwargs)
        previous_tweet_id = response.data["id"]
        print(f"  Posted tweet id={previous_tweet_id}")

    print(f"Done: {total} tweets, {len(images)} images.")


def main() -> None:
    repo_root = Path(__file__).parent.parent
    images_dir = repo_root / "images"
    config_path = repo_root / "tweet_config.json"

    default_texts = load_default_texts(config_path)

    episode = pick_random_episode(images_dir)
    if episode is None:
        print("ERROR: No episode folders found in images/", file=sys.stderr)
        sys.exit(1)

    images = get_episode_images(episode)
    if not images:
        print(f"ERROR: No images found in images/{episode.name}/", file=sys.stderr)
        sys.exit(1)

    tweet_text = get_tweet_text(episode, default_texts)

    print(f"Selected episode: {episode.name} ({len(images)} images)")
    print(f"First tweet text: {tweet_text}")

    client_v2, api_v1 = get_twitter_client()
    post_thread(client_v2, api_v1, tweet_text, images)


if __name__ == "__main__":
    main()
