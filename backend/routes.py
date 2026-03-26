from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from security import get_current_user, supabase
from schemas import ProfileUpdateRequest, BriefingRequest, FollowUpRequest
from agents import get_recommended_articles, generate_user_briefing, answer_followup_question, generate_ai_summary
from vector_store import search_articles
import time
import asyncio

# Global variable to track background ingestion status for the UI
ingestion_status = {
    "status": "idle", # idle, running, completed, failed
    "scanned_count": 0,
    "processed_count": 0,
    "current_category": "",
    "last_run": None,
    "error": None
}

router = APIRouter()

@router.post("/api/onboarding")
def update_profile(request: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """
    Updates user persona and preferred language in Supabase PostgreSQL.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    email = user.get("email", "")
    display_name = user.get("user_metadata", {}).get("full_name", "")
    
    try:
        # Use user's token for RLS
        client = supabase.postgrest.auth(user.get("access_token"))
        response = client.table("users").select("*").eq("id", user_id).execute()
        
        user_data = {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "persona": request.persona,
            "preferred_language": request.preferred_language
        }
        
        if len(response.data) > 0:
            client.table("users").update(user_data).eq("id", user_id).execute()
        else:
            client.table("users").insert(user_data).execute()
            
        return {"status": "success", "message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/briefing")
async def get_briefing(request: BriefingRequest, user: dict = Depends(get_current_user)):
    """Generates a personalized briefing asynchronously."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    try:
        # Use user's token for RLS
        client = supabase.postgrest.auth(user.get("access_token"))
        response = client.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
        if len(response.data) == 0:
             raise HTTPException(status_code=400, detail="User profile not found.")
             
        user_pref = response.data[0]
        persona = user_pref.get("persona", "General User")
        preferred_language = user_pref.get("preferred_language", "English")
        
        briefing_markdown, image_url = await generate_user_briefing(
             query=request.topic,
             persona=persona,
             target_language=preferred_language
        )
        return {"topic": request.topic, "briefing": briefing_markdown, "image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Briefing error: {str(e)}")

@router.post("/api/followup")
async def followup_chat(req: FollowUpRequest, user: dict = Depends(get_current_user)):
    try:
        answer = await answer_followup_question(req.context_text, req.query, req.history)
        return {"response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/recommendations")
async def get_recommendations(persona: str = None, target_language: str = None, limit: int = 15, user: dict = Depends(get_current_user)):
    """Fetches recommendations using the new persona-cache and persistent translation layer."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    try:
        # Use user's token for RLS
        client = supabase.postgrest.auth(user.get("access_token"))
        
        # Prioritize persona from query param (for UI reactivity), fallback to profile
        if not persona:
            response = client.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
            if len(response.data) > 0:
                persona = response.data[0].get("persona", "General User")
            else:
                persona = "General User"
        
        # Pull language from request first (for instant preview), fallback to profile
        preferred_language = target_language
        if not preferred_language:
            profile_res = client.table("users").select("preferred_language").eq("id", user_id).execute()
            if len(profile_res.data) > 0:
                preferred_language = profile_res.data[0].get("preferred_language", "English")
            else:
                preferred_language = "English"
            
        articles = await get_recommended_articles(persona=persona, target_language=preferred_language, limit=limit)
        return articles
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

async def run_ingestion():
    global ingestion_status
    try:
        from ingestion import fetch_et_rss_feed, scrape_article_text
        from vector_store import store_articles_in_qdrant, get_all_existing_links, delete_old_articles
        from datetime import datetime, timedelta
        
        ingestion_status["status"] = "running"
        ingestion_status["scanned_count"] = 0
        ingestion_status["processed_count"] = 0
        ingestion_status["error"] = None
        
        # 1. Bulk Cleanup & Bulk Duplicate Check Optimization
        await delete_old_articles(30)
        existing_links = await get_all_existing_links(limit=2000)

        #  helper: recency filter
        def is_recent(published_date, hours=48):
            try:
                article_time = datetime.strptime(published_date, "%a, %d %b %Y %H:%M:%S %z")
                now = datetime.now(article_time.tzinfo)
                return (now - article_time) <= timedelta(hours=hours)
            except:
                return False
        
        categories = ["top_stories", "tech", "markets", "economy_policy", "banking", "industry"]
        all_articles = []
        
        for category in categories:
            ingestion_status["current_category"] = category
            articles = await fetch_et_rss_feed(category)

            if not articles:
                continue

            # filter recent
            articles = [a for a in articles if is_recent(a.get("published_date", ""))]

            # apply limits
            if category == "top_stories":
                articles = articles[:30]
            else:
                articles = articles[:10]

            all_articles.extend(articles)

        print(f"After fetch + filter: {len(all_articles)}")

        #  Step 2: Dedup BEFORE scraping
        unique_articles = {}
        for a in all_articles:
            link = a.get("link")
            if link and link not in unique_articles:
                unique_articles[link] = a

        articles = list(unique_articles.values())

        #  Step 3: Remove already stored
        new_articles_queue = [
            a for a in articles if a["link"] not in existing_links
        ]

        print(f"After dedup + DB filter: {len(new_articles_queue)}")
        print(f"Final articles to process: {len(new_articles_queue)}")

        # Process in small parallel batches to stay under rate limits
        for i in range(0, len(new_articles_queue), 7):  
             batch = new_articles_queue[i:i+7]
             tasks = [scrape_article_text(a['link']) for a in batch]
             results = await asyncio.gather(*tasks)

             successfully_scraped = []

             for a, (content, img_url, synopsis) in zip(batch, results):
                 ingestion_status["scanned_count"] += 1

                 if not content:
                    continue

                 a['full_text'] = content
                 a['image_url'] = img_url

                 if synopsis and (not a.get('summary') or len(a.get('summary', '').strip()) < 10):
                   a['summary'] = synopsis

                 successfully_scraped.append(a)

             if successfully_scraped:
                  await store_articles_in_qdrant(successfully_scraped)
                  ingestion_status["processed_count"] += len(successfully_scraped)
                  await asyncio.sleep(0.3)
        
        ingestion_status["status"] = "completed"
        ingestion_status["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print("--- ASYNC INGESTION COMPLETED ---")
        
    except Exception as e:
        print(f"Ingestion error: {e}")
        ingestion_status["status"] = "failed"
        ingestion_status["error"] = str(e)

@router.post("/api/trigger_ingestion")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Triggers the async background process."""
    if ingestion_status["status"] == "running":
        return {"status": "already_running", "message": "Background sync is already in progress."}
    
    background_tasks.add_task(run_ingestion)
    return {"status": "started", "message": "Intelligence engine initialized."}

@router.get("/api/ingestion_status")
def get_ingest_status():
    return ingestion_status
