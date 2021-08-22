import os
import asyncio

import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser
import feedparser
from flask import Flask, render_template

app = Flask(__name__)


def read_feeds():
    return (
        open("feeds.txt")
        .read()
        .splitlines()
    )


async def get_feed(session, url):
    async with session.get(url) as resp:
        feed = await resp.text()
        return feed


async def gather_feeds():
    feeds = read_feeds()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for feed in feeds:
            if not feed:
                continue
            tasks.append(asyncio.ensure_future(get_feed(session, feed)))
        feed_content = await asyncio.gather(*tasks)
        return feed_content


def feed_site(rss):
    feed_info = rss.get("feed", {}) or {}

    site_title = f"{feed_info.get('title', '')}"
    # subtitle = feed_info.get("subtitle", "")
    # if subtitle:
    #     site_title += f": {subtitle}"

    site = {}

    site["title"] = site_title
    site["link"] = feed_info.get("link", "")
    site["lang"] = feed_info.get("language", "")
    site["img_link"] = feed_info.get("image", {}).get("href", "")
    return site


def feed_entries(rss, site):
    entries_raw = rss.get("entries", []) or []
    entries = []
    for i in range(0, int(os.getenv("MAX_ENTRIES", 5))):
        if i >= len(entries_raw) - 1:
            break
        entry_info = entries_raw[i]

        entry = {"site": site}

        entry["published"] = parser.parse(entry_info.get("published", ""))
        entry["published_str"] = str(entry["published"])[:-6]
        entry["link"] = entry_info.get("link", "")
        entry["title"] = entry_info.get("title", "")
        entry["summary"] = entry_info.get("summary", "")
        if entry_info.get("summary_detail", {}).get("type", "") == "text/html":
            soup = BeautifulSoup(entry["summary"])
            text = soup.get_text()
            entry["summary"] = text
        entry["author"] = entry_info.get("author", "")
        entry["content"] = ""
        content = entry_info.get("content", [])
        if content:
            content = content[0]
            # if content.get("type", "") == "text/html":
            #     soup = BeautifulSoup(content.get("value", ""))
            #     text = soup.get_text()
            #     entry["content"] = text
            # else:
            entry["content"] = content.get("value", "")
        entries.append(entry)
    return entries


def extract_feed_content(feed):
    rss = feedparser.parse(feed)
    site_details = feed_site(rss)
    content = feed_entries(rss, site_details)
    return content


def parse_feeds(feeds_content):
    all_feeds = []
    for feed in feeds_content:
        feed_content = extract_feed_content(feed)
        all_feeds.extend(feed_content)
    order_in_place(all_feeds)
    return all_feeds


def order_in_place(feeds):
    feeds.sort(key=lambda d: d["published"], reverse=True)


@app.route("/")
def home():
    return render_template("index.html", feeds=main())

def main():
    feeds_content = asyncio.run(gather_feeds())
    rss_feeds = parse_feeds(feeds_content)
    return rss_feeds


if __name__ == "__main__":
    main()

