from fastapi import APIRouter, Depends, HTTPException, status
from security import get_current_user, supabase
from schemas import ProfileUpdateRequest, BriefingRequest, FollowUpRequest
from agents import generate_user_briefing, get_recommended_articles, answer_followup_question

router = APIRouter()

@router.post("/api/onboarding")
def update_profile(request: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    """
    Updates user persona and preferred language in Supabase PostgreSQL.
    If the user doesn't exist, it inserts a new row.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    email = user.get("email", "")
    display_name = user.get("user_metadata", {}).get("full_name", "")
    
    # Check if user exists
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
            # Update existing user
            supabase.table("users").update(user_data).eq("id", user_id).execute()
        else:
            # Insert new user
            supabase.table("users").insert(user_data).execute()
            
        return {"status": "success", "message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/briefing")
def get_briefing(request: BriefingRequest, user: dict = Depends(get_current_user)):
    """
    Generates a personalized briefing based on the user's persona and preferred language.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    
    # Fetch user preferences
    try:
        response = supabase.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
        
        if len(response.data) == 0:
             raise HTTPException(status_code=400, detail="User profile not found. Complete onboarding first.")
             
        user_pref = response.data[0]
        persona = user_pref.get("persona", "General User")
        preferred_language = user_pref.get("preferred_language", "English")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    # Generate briefing via Multi-Agent System
    try:
        briefing_markdown, image_url = generate_user_briefing(
             query=request.topic,
             persona=persona,
             target_language=preferred_language
        )
        return {"topic": request.topic, "briefing": briefing_markdown, "image_url": image_url}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@router.post("/api/followup")
def followup_chat(req: FollowUpRequest, user: dict = Depends(get_current_user)):
    try:
        if not req.context_text:
            raise HTTPException(status_code=400, detail="Missing context text.")
            
        answer = answer_followup_question(req.context_text, req.query, req.history)
        return {"response": answer}
    except Exception as e:
        print(f"Followup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/recommendations")
def get_recommendations(limit: int = 12, user: dict = Depends(get_current_user)):
    """
    Fetches persona-targeted recommended articles for the user feed.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    user_id = user.get("sub")
    
    # Fetch user preferences
    try:
        response = supabase.table("users").select("persona", "preferred_language").eq("id", user_id).execute()
        
        if len(response.data) == 0:
             raise HTTPException(status_code=400, detail="User profile not found. Complete onboarding first.")
             
        user_pref = response.data[0]
        persona = user_pref.get("persona", "General User")
        preferred_language = user_pref.get("preferred_language", "English")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    try:
        articles = get_recommended_articles(persona=persona, target_language=preferred_language, limit=limit)
        return {"persona": persona, "language": preferred_language, "articles": articles}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

@router.post("/api/trigger_ingestion")
def trigger_ingestion(user: dict = Depends(get_current_user)):
    """
    Manually triggers the ingestion process to fetch and store new articles in vector db.
    """
    try:
        from ingestion import RSS_FEEDS, fetch_et_rss_feed, scrape_article_text
        from vector_store import store_articles_in_qdrant, is_article_ingested
        from agents import generate_ai_summary
        from concurrent.futures import ThreadPoolExecutor
        
        all_processed = []
        
        def process_entry(a: dict):
            # Skip if already in database
            if is_article_ingested(a['link']):
                return None
            
            # Scrape if new
            full_text, image_url, synopsis = scrape_article_text(a['link'])
            if full_text:
                a['full_text'] = full_text
                a['image_url'] = image_url
                
                # Use scraped synopsis if RSS summary is missing or empty
                if not a.get('summary') or len(a.get('summary', '').strip()) < 10:
                    if synopsis:
                        print(f"Using scraped synopsis for: {a['title']}")
                        a['summary'] = synopsis
                    
                return a
            return None

        for category in RSS_FEEDS.keys():
            print(f"Ingesting category: {category}")
            articles = fetch_et_rss_feed(category)
            top_articles = articles[:35] 
            
            # Parallelize scraping for this category
            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(process_entry, top_articles))
                # Add only newly processed articles
                all_processed.extend([r for r in results if r is not None])
             
        if all_processed:
            store_articles_in_qdrant(all_processed)
            
        return {"status": "success", "message": f"Successfully processed {len(all_processed)} new articles."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
