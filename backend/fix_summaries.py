from vector_store import get_qdrant_client, COLLECTION_NAME
from ingestion import scrape_article_text
from qdrant_client.models import PointStruct
import uuid

def fix_missing_summaries():
    print("--- Starting Summary Maintenance ---")
    client = get_qdrant_client()
    
    # Scroll through all articles
    scroll_result = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=100,
        with_payload=True,
        with_vectors=False
    )
    
    points = scroll_result[0]
    total_fixed = 0
    
    for point in points:
        payload = point.payload
        summary = payload.get("summary", "")
        link = payload.get("link", "")
        
        # Identify bad summaries: empty, or the AI refusal message
        is_bad = not summary or "Please provide the article text" in summary or len(summary) < 10
        
        if is_bad and link:
            print(f"Fixing summary for: {payload.get('title')}")
            # Re-scrape specifically for the synopsis
            text, img, synopsis = scrape_article_text(link)
            
            if synopsis:
                print(f"  Found Synopsis: {synopsis[:50]}...")
                # Update payload
                new_payload = dict(payload)
                new_payload["summary"] = synopsis
                
                # Check if we should also update image if missing
                if not new_payload.get("image_url") and img:
                    new_payload["image_url"] = img
                
                client.set_payload(
                    collection_name=COLLECTION_NAME,
                    payload=new_payload,
                    points=[point.id]
                )
                total_fixed += 1
            else:
                print("  No synopsis found on page.")
                
    print(f"--- Maintenance Complete. Fixed {total_fixed} articles. ---")

if __name__ == "__main__":
    fix_missing_summaries()
