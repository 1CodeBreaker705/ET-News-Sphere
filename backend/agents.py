from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from vector_store import search_articles
import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv(override=True)
# Ensure at least one key is present and prioritized
_raw_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_api_key = _raw_key.strip('"').strip("'").strip() if _raw_key else None

if _api_key:
    os.environ["GOOGLE_API_KEY"] = _api_key
    os.environ["GEMINI_API_KEY"] = _api_key



# 1. State Definition
class AgentState(TypedDict):
    query: str
    user_persona: str
    target_language: str
    retrieved_articles: List[dict]
    draft_briefing: str
    final_output: str
    image_url: str

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview", 
    api_key=_api_key,
    temperature=0.2
)

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join([c.get("text", "") for c in content if isinstance(c, dict) and "text" in c])
    return str(content)

# 2. Single-Shot Briefing Generation
async def generate_user_briefing(query: str, persona: str, target_language: str = "English") -> str:
    """
    Generates a hyper-personalized news briefing asynchronousy.
    """
    print(f"--- GENERATING ASYNC BRIEFING FOR: {persona} ---")
    
    # 1. Retrieve Context (Async)
    retrieved_articles = await search_articles(query, limit=3)
    
    image_url = ""
    for article in retrieved_articles:
        if article.get("image_url"):
            image_url = article["image_url"]
            break
            
    if not retrieved_articles:
        print(f"--- NO DIRECT MATCHES FOR {query}. TRIGGERING FALLBACK SEARCH ---")
        retrieved_articles = await search_articles("latest trending financial and business news in India", limit=3)
        if not retrieved_articles:
            from vector_store import get_latest_articles_fallback
            retrieved_articles = await get_latest_articles_fallback(limit=3)
            
    if not retrieved_articles:
        return "The briefing engine is currently building its intelligence base. Please try a more general topic like 'Markets' or 'Technology'.", ""

    # 2. Prepare Context & Sources
    context_parts = []
    sources_parts = []
    for idx, a in enumerate(retrieved_articles, 1):
        content = a.get('full_text') or a.get('summary') or ""
        context_parts.append(f"Source {idx}: {a.get('title')}\n{a.get('summary')}\n{content[:1500]}\nURL: {a.get('link')}")
        sources_parts.append(f"Source {idx}: {a.get('link')}")
    
    context = "\n\n".join(context_parts)
    sources_info = "\n".join(sources_parts)

    # 3. Comprehensive Single-Shot Prompt
    prompt = f"""
    You are a Senior Financial Editor. 
    A user with the persona '{persona}' has requested a briefing for: '{query}'
    
    Your Task:
    1. Write a comprehensive, engaging news briefing in Markdown.
    2. Tailor the content and tone specifically for the '{persona}' persona.
    3. Include inline markdown hyperlinks for every factual claim (e.g., [[Source 1]](url)).
    4. If the target language is NOT English, translate the entire briefing into {target_language}.
    5. Maintain all Markdown formatting and link structures.
    6. End with a "### Sources:" section listing all links as: 1. [Source 1](url)
    
    Context Articles:
    {context}
    
    Sources for Citations:
    {sources_info}
    
    Final Personalized Briefing:
    """
    
    try:
        # One single call without mandatory sleeps = Fast
        print("--- SENDING ASYNC LLM REQUEST ---")
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=120.0)
        return extract_text(response.content), image_url
    except asyncio.TimeoutError:
        print("Briefing error: 120s Timeout limit reached.")
        return "The AI Oracle is currently at peak capacity (Rate Limit Hit). Please wait 10 seconds and try again.", image_url
    except Exception as e:
        print(f"Briefing error: {e}")
        return "The briefing engine is currently under high load.", image_url

import json

# Persona-specific interest profiles to enrich semantic search
PERSONA_PROFILES = {
    "Student": "business basics, education policy, career guidance, internships, campus placements, simplified financial news for students, entry-level jobs, higher education trends, competitive exams, skill development, student loans, CAT exam, IIM placements, IIT MBA, study abroad, UPSC news, educational scholarships, college admissions, startup internships for students",
    "Startup Founder": "funding news, venture capital, startup ecosystem, entrepreneurship, scaling businesses, innovation, tech layoffs, unicorns, market disruption, pitch deck tips, bootstrapping, fintech, saas",
    "Retail Investor": "stock market trends, personal finance, mutual funds, wealth management, investment strategy, market analysis, dividends, sebi regulations, ipo alerts, trading psychology, gold price, real estate investment",
    "Tech Enthusiast": "latest gadgets, semiconductor industry, software development, artificial intelligence, cybersecurity, blockchain, cloud computing, apple news, google updates, future tech, gaming tech, 5g, robotics",
    "Working Professional / Corporate Executive": "corporate governance, leadership, industry mergers, executive moves, business strategy, workplace trends, remote work, macroeconomics, earnings reports, boardroom discussions, management consulting, fortune 500, blue chip companies, career growth, leadership skills, work-life balance, corporate culture, industry analysis",
    "Policy Maker": "economic policy, government regulations, fiscal deficit, trade agreements, infrastructure development, urban planning, environment news, budget 2026, legislative changes, public sector, diplomatic relations",
    "Financial Advisor": "tax planning, asset allocation, global markets, interest rates, rbi guidelines, retirement planning, insurance news, private banking, fixed income, crypto regulation, estate planning, wealth preservation"
}

async def translate_feed_articles(articles: List[dict], target_language: str) -> List[dict]:
    print(f"--- BATCH TRANSLATING FEED TO {target_language} ---")
    if not articles:
        return []
        
    payload = [{"id": i, "title": a.get("title", ""), "summary": a.get("summary", "")[:500]} for i, a in enumerate(articles)]
        
    prompt = f"""
    You are an expert news translator.
    Translate the 'title' and 'summary' of the following JSON array of news articles into {target_language}.
    Return ONLY a strictly valid JSON array of objects with the exact same 'id' keys.
    Do not wrap the response in markdown blocks, just return raw JSON text.
    
    Articles:
    {json.dumps(payload, ensure_ascii=False)}
    """
    
    try:
        print("--- SENDING ASYNC TRANSLATION REQUEST ---")
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=180.0)
        text_resp = extract_text(response.content).strip()
        
        if text_resp.startswith("```json"):
            text_resp = text_resp.split("```json")[1].split("```")[0].strip()
        elif text_resp.startswith("```"):
            text_resp = text_resp.split("```")[1].split("```")[0].strip()
            
        translated_items = json.loads(text_resp)
        
        for item in translated_items:
            idx = item.get("id")
            if idx is not None and idx < len(articles):
                articles[idx] = articles[idx].copy()
                articles[idx]["title"] = item.get("title", articles[idx].get("title"))
                articles[idx]["summary"] = item.get("summary", articles[idx].get("summary"))
                
    except Exception as e:
        print(f"Batch feed translation failed: {e}")
        
    return articles

async def get_recommended_articles(persona: str, target_language: str = "English", limit: int = 15) -> List[dict]:
    """
    Retrieves the most relevant articles for the user's persona by expanding the persona name 
    into a rich interest profile before searching, mapping them to target languages.
    """
    print(f"--- FETCHING RECOMMENDATIONS FOR: {persona} IN {target_language} ---")
    
    search_query = PERSONA_PROFILES.get(persona, persona)

    # CHANGE 1: Fetch more candidates (better selection, same cost)
    results = await search_articles(search_query, limit=30)
    
    # Fallback 1: AI-powered general news
    if not results:
        try:
            print(f"--- Persona search for '{persona}' yielded 0 results, falling back to AI latest news ---")
            results = await search_articles(
                "latest financial and business news from Economic Times",
                limit=30
            )
        except Exception:
            results = []

    # Fallback 2: Direct database scroll (already optimized)
    if not results:
        from vector_store import get_latest_articles_fallback
        print(f"--- AI Search failed (likely rate limit), using zero-API database scroll fallback ---")
        results = await get_latest_articles_fallback(limit=limit)

    # CHANGE 2: Deduplicate results
    unique = {}
    for a in results:
        link = a.get("link")
        if link and link not in unique:
            unique[link] = a

    results = list(unique.values())

    # 3. Translation Hub with Persistence
    lang_key = target_language.lower()
    if lang_key not in ["english", "en"] and results:
        needs_translation = []
        final_articles = []
        
        for a in results:
            cached = a.get("translations", {}).get(lang_key)
            if cached:
                a["title"] = cached.get("title", a["title"])
                a["summary"] = cached.get("summary", a["summary"])
                final_articles.append(a)
            else:
                needs_translation.append(a)
        
        if needs_translation:
            print(f"--- TRANSLATING {len(needs_translation)} NEW ARTICLES TO {target_language} ---")
            translated = await translate_feed_articles(needs_translation, target_language)
            
            # FIX: Ensure translations are saved properly
            from vector_store import update_article_translations
            await asyncio.gather(*[
                update_article_translations(
                    a['link'], lang_key,
                    {"title": a['title'], "summary": a['summary']}
                )
                for a in translated
            ])
            
            final_articles.extend(translated)
        
        # CHANGE 3: Sort + return best 15
        return sorted(
            final_articles,
            key=lambda x: x.get('created_at', 0),
            reverse=True
        )[:limit]

    # CHANGE 3: Sort + return best 15 (normal case)
    return sorted(
        results,
        key=lambda x: x.get('created_at', 0),
        reverse=True
    )[:limit]

async def answer_followup_question(context_text: str, query: str, history: List[dict] = None) -> str:
    print("--- FOLLOW-UP AGENT ---")
    if not history:
        history = []
        
    history_str = ""
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_str += f"{role}: {msg.get('text', '')}\n"
        
    prompt = f"""
    You are an expert analytical assistant responding to follow-up questions about a specific document.
    
    Provided Document Context:
    ---
    {context_text}
    ---
    
    Conversation History:
    {history_str}
    
    User's New Question: {query}
    
    Respond directly to the user's new question based ONLY on the Provided Document Context and the Conversation History.
    If the answer cannot be confidently deduced from the Provided Document Context, explicitly state that the information is not available in the source material.
    Do not hallucinate external facts. Keep your answer concise, engaging, and formatted in clean Markdown.
    """
    
    try:
        print("--- SENDING ASYNC FOLLOW-UP REQUEST ---")
        import asyncio
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=60.0)
        return extract_text(response.content)
    except asyncio.TimeoutError:
        print("Follow-up error: 60s Timeout limit reached.")
        return "The AI is currently busy (Rate Limit Hit). Please wait a moment and try again."
    except Exception as e:
        print(f"Follow-up error: {e}")
        return "The AI is currently busy (Rate Limit Hit). Please wait a moment and try again."

async def generate_ai_summary(text: str) -> str:
    """
    Generates a concise 2-sentence summary for a news article.
    """
    print("--- SUMMARIZER AGENT ---")
    if not text or len(text) < 100:
        return ""
        
    prompt = f"""
    You are an expert news editor. Summarize the following news article into exactly TWO concise, highly engaging sentences.
    Focus on the most impactful financial or business insight.
    
    Article Text:
    {text[:2500]}
    
    Two-Sentence Summary:
    """
    
    try:
        print("--- SENDING ASYNC SUMMARY REQUEST ---")
        import asyncio
        response = await llm.ainvoke(prompt)
        summary = extract_text(response.content).strip()
        # Clean up any potential markdown formatting if LLM adds it
        summary = summary.replace('**', '').replace('"', '').strip()
        return summary
    except Exception as e:
        print(f"Summarization error: {e}")
        return ""

if __name__ == "__main__":
    # Test example block
    # Note: Qdrant vector store must be populated beforehand via ingestion.py
    pass
