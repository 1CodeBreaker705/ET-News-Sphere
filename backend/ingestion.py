import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import html

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

def fetch_et_rss_feed(category="top_stories"):
    """
    Fetches the RSS feed from The Economic Times for the given category.
    """
    feed_url = RSS_FEEDS.get(category)
    if not feed_url:
        raise ValueError(f"Unknown category: {category}")
        
    feed = feedparser.parse(feed_url)
    
    articles = []
    for entry in feed.entries:
        articles.append({
            "title": html.unescape(entry.title),
            "link": entry.link,
            "published_date": entry.get("published", ""),
            "summary": html.unescape(entry.get("summary", ""))
        })
        
    return articles
        
def scrape_article_text(url):
    """
    Scrapes the main text content and the main image from an ET article URL.
    Returns: (text_content, image_url)
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract image URL
        image_url = ""
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            image_url = og_img['content']
        else:
            # Fallback: look for likely main article images
            for img in soup.find_all('img'):
                # Heuristic: main images are usually large and not icons
                if img.get('src') and not any(x in img.get('src').lower() for x in ['icon', 'logo', 'ads', 'pixel', 'sprite']):
                    image_url = img.get('src')
                    if not image_url.startswith('http'):
                        from urllib.parse import urljoin
                        image_url = urljoin(url, image_url)
                    break
            
        # Extract synopsis (summary) if present on page
        synopsis = ""
        # 1. Try OG Description (very reliable for ET)
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            synopsis = og_desc['content']
            
        # 2. Try standard Meta Description
        if not synopsis:
            meta_desc = soup.find('meta', attrs={"name": "description"})
            if meta_desc and meta_desc.get('content'):
                synopsis = meta_desc['content']
        
        # 3. Try .synopsis class if meta tags are missing/empty
        if not synopsis:
            synopsis_tag = soup.select_one('.synopsis')
            if synopsis_tag:
                synopsis = synopsis_tag.get_text(strip=True)
                
        # Clean up the synopsis
        if synopsis:
            # Remove "Synopsis" prefix if it exists
            if synopsis.lower().startswith("synopsis"):
                synopsis = synopsis[8:].strip()
            if synopsis.startswith("-") or synopsis.startswith(":"):
                synopsis = synopsis[1:].strip()

        # Decompose common boilerplate elements BEFORE searching for content
        # This prevents headers, footers, and sidebars from leaking into the 'last-ditch' text
        for boilerplate in soup.find_all(['header', 'footer', 'nav', 'aside', 'script', 'style', 'iframe']):
            boilerplate.decompose()
            
        # Specific ET boilerplate classes/ids
        for junk_selector in ['.featured_funds', '.market_stats', '.top_nav', '.et_ad', '#footer', '.common_header', '.tab_container', '.shareBox', '.share_wrap', '.author', '.date', '.time', '.fontResize', '.social_share', '.article_utils', '.shareBar']:
            for junk in soup.select(junk_selector):
                junk.decompose()
            
        # ET stores main article text in various containers depending on the article type
        # We try to find the most specific container first
        article_body = soup.find(['div', 'section'], class_=['artText', 'article_content', 'content', 'story-content', 'article-text', 'section-body', 'article-section', 'story_body'])
        if not article_body:
             article_body = soup.find(id=['artText', 'article_content', 'story_body'])

        if article_body:
            # Filter for actual content-bearing paragraphs
            # We look for <p> tags but also <div> tags that contain significant text
            text_parts = []
            
            # 1. Try finding <p> tags first as they are most reliable for structure
            paragraphs = article_body.find_all('p')
            if len(paragraphs) > 2:
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 40 and "Font Size" not in p_text and "ShareFont" not in p_text: # Ignore short fragments (ads/meta)
                        text_parts.append(p_text)
            
            # 2. If no <p> tags, look for text-heavy <div> elements
            if not text_parts:
                for chunk in article_body.find_all(['div', 'span'], recursive=False):
                    content = chunk.get_text(strip=True)
                    if len(content) > 100 and "Font Size" not in content and "ShareFont" not in content:
                        text_parts.append(content)
            
            if text_parts:
                # Ensure each part starts on a new line for ReactMarkdown
                return "\n\n".join(text_parts), image_url, synopsis
            
            # Final fallback for the container itself
            return article_body.get_text(separator="\n\n", strip=True), image_url, synopsis
            
        # Global last-ditch fallback: seek the largest cluster of text now that boilerplate is gone
        all_text_blobs = [p.get_text(strip=True) for p in soup.find_all(['p', 'div']) if len(p.get_text(strip=True)) > 150 and "ShareFont" not in p.get_text()]
        if all_text_blobs:
             return "\n\n".join(all_text_blobs[:10]), image_url, synopsis # Limit to 10 blobs for sanity
             
        return "", image_url, synopsis
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return "", "", ""

def process_new_articles():
    """
    Loops through top 5 articles, scrapes them, and prints the result.
    """
    try:
        print("Fetching Top Stories RSS feed from Economic Times...\n")
        articles = fetch_et_rss_feed("top_stories")
        top_5 = articles[:5]
        
        for idx, article in enumerate(top_5, 1):
            print(f"--- Article {idx}: {article['title']} ---")
            print(f"URL: {article['link']}")
            print(f"Published: {article['published_date']}")
            
            print("Scraping content...")
            content, img_url = scrape_article_text(article['link'])
            print(f"Image: {img_url}")
            
            print("\nPreview:")
            preview = content[:400] + "..." if len(content) > 400 else content
            print(preview)
            print("-" * 80 + "\n")
            
    except Exception as e:
        print(f"Failed to process articles: {e}")

if __name__ == "__main__":
    process_new_articles()
