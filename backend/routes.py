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
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        user_data = {
            "id": user_id,
            "email": email,
            "display_name": display_name,
            "persona": request.persona,
            "preferred_language": request.preferred_language
        }
        
        if len(response.data) > 0:
            supabase.table("users").update(user_data).eq("id", user_id).execute()
        else:
            supabase.table("users").insert(user_data).execute()
            
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
        response = supabase.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
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
        # Prioritize persona from query param (for UI reactivity), fallback to profile
        if not persona:
            response = supabase.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
            if len(response.data) > 0:
                persona = response.data[0].get("persona", "General User")
            else:
                persona = "General User"
        
        # Pull language from request first (for instant preview), fallback to profile
        preferred_language = target_language
        if not preferred_language:
            profile_res = supabase.table("users").select("preferred_language").eq("id", user_id).execute()
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
        
        ingestion_status["status"] = "running"
        ingestion_status["scanned_count"] = 0
        ingestion_status["processed_count"] = 0
        ingestion_status["error"] = None
        
        # 1. Bulk Cleanup & Bulk Duplicate Check Optimization
        await delete_old_articles(30)
        existing_links = await get_all_existing_links(limit=2000)
        
        categories = ["top_stories", "tech", "markets", "politics", "economy", "international", "banking", "wealth", "industry", "small_biz", "jobs_edu", "software", "panache"]
        
        for category in categories:
            ingestion_status["current_category"] = category
            articles = await fetch_et_rss_feed(category)
            
            # Take up to 8 from each category to ensure a diverse 15-article feed (total 104 targets)
            new_articles_queue = [a for a in articles if a['link'] not in existing_links][:8]
            
            if not new_articles_queue:
                # Still increment scanned count by 10 for UI progress
                ingestion_status["scanned_count"] += 10
                continue

            # Process in small parallel batches to stay under rate limits
            for i in range(0, len(new_articles_queue), 5):
                batch = new_articles_queue[i:i+5]
                tasks = [scrape_article_text(a['link']) for a in batch]
                results = await asyncio.gather(*tasks)
                
                successfully_scraped = []
                for idx, (content, img_url, synopsis) in enumerate(results):
                    ingestion_status["scanned_count"] += 1
                    a = batch[idx]
                    if content:
                        a['full_text'] = content
                        a['image_url'] = img_url
                        if synopsis and (not a.get('summary') or len(a.get('summary','').strip()) < 10):
                             a['summary'] = synopsis
                        successfully_scraped.append(a)
                
                if successfully_scraped:
                    await store_articles_in_qdrant(successfully_scraped)
                    ingestion_status["processed_count"] += len(successfully_scraped)
                    await asyncio.sleep(1)
        
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
