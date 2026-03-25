from ingestion import scrape_article_text
url = "https://economictimes.indiatimes.com/news/india/corporate-laws-amendment-bill-2026-introduced-in-lok-sabha-sent-to-jpc/articleshow/129746043.cms"
text, img, synopsis = scrape_article_text(url)
print(f"Synopsis: {synopsis}")
