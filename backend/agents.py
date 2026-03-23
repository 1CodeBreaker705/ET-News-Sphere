from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from vector_store import search_articles
import os
from dotenv import load_dotenv

load_dotenv()

# 1. State Definition
class AgentState(TypedDict):
    query: str
    user_persona: str
    target_language: str
    retrieved_articles: List[dict]
    draft_briefing: str
    final_output: str
    image_url: str

llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0.2)

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join([c.get("text", "") for c in content if isinstance(c, dict) and "text" in c])
    return str(content)

# 2. Node 1 - ResearcherAgent
def researcher_agent(state: AgentState) -> AgentState:
    print("--- RESEARCHER AGENT ---")
    query = state["query"]
    print(f"Searching vector DB for query: {query}")
    
    # Retrieve top 5 most relevant ET articles
    results = search_articles(query, limit=5)
    
    # Extract the first available image_url from retrieved results
    image_url = ""
    for article in results:
        if article.get("image_url"):
            image_url = article["image_url"]
            break
            
    return {"retrieved_articles": results, "image_url": image_url}

# 3. Node 2 - SynthesisAgent
def synthesis_agent(state: AgentState) -> AgentState:
    print("--- SYNTHESIS AGENT ---")
    retrieved_articles = state["retrieved_articles"]
    user_persona = state["user_persona"]
    query = state["query"]
    
    context = ""
    for idx, article in enumerate(retrieved_articles, 1):
        context += f"\n[Source {idx}: {article.get('title')} - ({article.get('link')})]\n"
        context += f"{article.get('summary', '')}\n"
        context += f"{article.get('full_text', '')[:800]}...\n" # Truncate to save tokens
        
    prompt = f"""
    You are an expert financial analyst. A user with the persona '{user_persona}' has asked: '{query}'
    
    Based on the following Economic Times articles, write a comprehensive briefing in Markdown.
    Tailor the focus specifically to the '{user_persona}' persona.
    Identify any conflicting viewpoints if they exist in the sources.
    
    Context Articles:
    {context}
    
    Draft Briefing:
    """
    
    response = llm.invoke(prompt)
    draft_briefing = extract_text(response.content)
    
    return {"draft_briefing": draft_briefing}

# 4. Node 3 - AuditAgent
def audit_agent(state: AgentState) -> AgentState:
    print("--- AUDIT AGENT ---")
    draft_briefing = state["draft_briefing"]
    retrieved_articles = state["retrieved_articles"]
    
    sources_info = "\n".join([f"Source {idx}: {a.get('link')}" for idx, a in enumerate(retrieved_articles, 1)])
    
    prompt = f"""
    You are an Audit Editor. Review the drafted briefing below.
    Ensure every factual claim includes an inline markdown hyperlink citation linked to the original URL (e.g., [[Source 1]](url)) based on the provided sources.
    Do not use text-only citations; all citations in the main text must be clickable hyperlinks that go directly to the source.
    At the absolute bottom of the briefing, append a new section exactly named "### Sources:" that lists all the referenced sources as clickable markdown links, formatted exactly like:
    1. [Source 1](url)
    2. [Source 2](url)
    
    Do not change the general factual content of the draft.
    
    Sources available:
    {sources_info}
    
    Draft Briefing:
    {draft_briefing}
    
    Audited Briefing:
    """
    
    response = llm.invoke(prompt)
    audited_briefing = extract_text(response.content)
    
    return {"draft_briefing": audited_briefing, "final_output": audited_briefing}

# 5. Node 4 - VernacularAgent
def vernacular_agent(state: AgentState) -> AgentState:
    print("--- VERNACULAR AGENT ---")
    target_language = state["target_language"]
    audited_briefing = state["draft_briefing"]
    
    # If English is requested, skip translation
    if target_language.lower() in ["english", "en"]:
        return {"final_output": audited_briefing}
        
    print(f"Translating to {target_language}...")
    
    prompt = f"""
    You are an expert context-aware translator for business and financial news.
    Translate the following briefing into {target_language}.
    Do not just transliterate; adapt the explanations culturally and provide local context where applicable for {target_language} speakers.
    Maintain all Markdown formatting and link structures completely intact.
    
    Original Briefing:
    {audited_briefing}
    
    Translated Briefing:
    """
    
    response = llm.invoke(prompt)
    translated_briefing = extract_text(response.content)
    
    return {"final_output": translated_briefing}

# 6. Compile the Graph
workflow = StateGraph(AgentState)

workflow.add_node("researcher", researcher_agent)
workflow.add_node("synthesis", synthesis_agent)
workflow.add_node("audit", audit_agent)
workflow.add_node("vernacular", vernacular_agent)

# Define edges
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "synthesis")
workflow.add_edge("synthesis", "audit")
workflow.add_edge("audit", "vernacular")
workflow.add_edge("vernacular", END)

# Compile the graph into a runnable application
app = workflow.compile()

# Helper execution function
def generate_user_briefing(query: str, persona: str, target_language: str = "English") -> str:
    """
    Invokes the LangGraph execution for generating a hyper-personalized news briefing.
    """
    initial_state = {
        "query": query,
        "user_persona": persona,
        "target_language": target_language,
        "retrieved_articles": [],
        "draft_briefing": "",
        "final_output": "",
        "image_url": ""
    }
    
    result = app.invoke(initial_state)
    return result["final_output"], result.get("image_url", "")

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

def translate_feed_articles(articles: List[dict], target_language: str) -> List[dict]:
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
        response = llm.invoke(prompt)
        text_resp = extract_text(response.content).strip()
        
        if text_resp.startswith("```json"):
            text_resp = text_resp.split("```json")[1].split("```")[0].strip()
        elif text_resp.startswith("```"):
            text_resp = text_resp.split("```")[1].split("```")[0].strip()
            
        translated_items = json.loads(text_resp)
        
        for item in translated_items:
            idx = item.get("id")
            if idx is not None and idx < len(articles):
                # Clone the dict to avoid mutating shared state
                articles[idx] = articles[idx].copy()
                articles[idx]["title"] = item.get("title", articles[idx].get("title"))
                articles[idx]["summary"] = item.get("summary", articles[idx].get("summary"))
                
    except Exception as e:
        print(f"Batch feed translation failed (fallback to English): {e}")
        
    return articles

def get_recommended_articles(persona: str, target_language: str = "English", limit: int = 15) -> List[dict]:
    """
    Retrieves the most relevant articles for the user's persona by expanding the persona name 
    into a rich interest profile before searching, mapping them to target languages.
    """
    print(f"--- FETCHING RECOMMENDATIONS FOR: {persona} IN {target_language} ---")
    
    search_query = PERSONA_PROFILES.get(persona, persona)
    results = search_articles(search_query, limit=limit)
    
    if target_language.lower() not in ["english", "en"]:
        results = translate_feed_articles(results, target_language)
        
    return results

def answer_followup_question(context_text: str, query: str, history: List[dict] = None) -> str:
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
    
    response = llm.invoke(prompt)
    return extract_text(response.content)

def generate_ai_summary(text: str) -> str:
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
        response = llm.invoke(prompt)
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
