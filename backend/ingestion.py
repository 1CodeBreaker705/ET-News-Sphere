import feedparser
import httpx
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
import html
from typing import List, Tuple, Optional

RSS_FEEDS = {
    "top_stories": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "tech": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "politics": "https://economictimes.indiatimes.com/news/politics/and-nation/rssfeeds/2733220.cms",
    "small_biz": "https://economictimes.indiatimes.com/small-biz/rssfeeds/5429640.cms",
    "industry": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
    "jobs_edu": "https://economictimes.indiatimes.com/jobs/rssfeeds/107032.cms",
    "software": "https://economictimes.indiatimes.com/tech/software-services/rssfeeds/13357598.cms",
    "economy_policy": "https://economictimes.indiatimes.com/news/economy/policy/rssfeeds/13358050.cms",
    "economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380685.cms",
    "international": "https://economictimes.indiatimes.com/news/international/world-news/rssfeeds/85847812.cms",
    "banking": "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358319.cms",
    "wealth": "https://economictimes.indiatimes.com/wealth/personal-finance/rssfeeds/81582969.cms",
    "panache": "https://economictimes.indiatimes.com/magazines/panache/rssfeeds/22756855.cms"
}

async def fetch_et_rss_feed(category="top_stories") -> List[dict]:
    """Fetches the RSS feed asynchronously."""
    feed_url = RSS_FEEDS.get(category)
    if not feed_url:
        raise ValueError(f"Unknown category: {category}")
        
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(feed_url)
        feed = feedparser.parse(response.text)
    
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": html.unescape(entry.title),
            "link": entry.link,
            "published_date": entry.get("published", ""),
            "summary": html.unescape(entry.get("summary", ""))
        })
    return articles

async def scrape_article_text(url: str) -> Tuple[str, str, str]:
    """Scrapes content asynchronously."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=10, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Image URL Extraction
        image_url = ""
        og_img = soup.find('meta', property='og:image')
        if og_img: image_url = og_img.get('content', '')
        
        # 2. Synopsis Extraction
        synopsis = ""
        og_desc = soup.find('meta', property='og:description')
        if og_desc: synopsis = og_desc.get('content', '')
        
        # 3. Content Extraction (Optimized ET selectors)
        for junk in soup.select('header, footer, nav, script, style, .social_share, .et_ad, .featured_funds'):
            junk.decompose()
            
        article_body = soup.find(['div', 'section'], class_=['artText', 'article_content', 'story_body'])
        if article_body:
            paragraphs = [p.get_text(strip=True) for p in article_body.find_all('p') if len(p.get_text()) > 40]
            if paragraphs:
                return "\n\n".join(paragraphs), image_url, synopsis
            return article_body.get_text(separator="\n\n", strip=True), image_url, synopsis
            
        return "", image_url, synopsis
    except Exception as e:
        print(f"Async scrape error for {url}: {e}")
        return "", "", ""

async def process_new_articles():
    """
    Loops through top 5 articles, scrapes them, and prints the result.
    """
    try:
        print("Fetching Top Stories RSS feed from Economic Times...\n")
        articles = await fetch_et_rss_feed("top_stories")
        top_5 = articles[:5]
        
        for idx, article in enumerate(top_5, 1):
            print(f"--- Article {idx}: {article['title']} ---")
            print(f"URL: {article['link']}")
            print(f"Published: {article['published_date']}")
            
            print("Scraping content...")
            content, img_url, synopsis = await scrape_article_text(article['link'])
            print(f"Image: {img_url}")
            print(f"Synopsis: {synopsis}")
            
            print("\nPreview:")
            preview = content[:400] + "..." if len(content) > 400 else content
            print(preview)
            print("-" * 80 + "\n")
            
    except Exception as e:
        print(f"Failed to process articles: {e}")

if __name__ == "__main__":
    asyncio.run(process_new_articles())
