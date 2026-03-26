import os
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range
import uuid
import time
import functools
import asyncio
from typing import List, Optional, Dict
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

COLLECTION_NAME = "et_news_google_v2" # Upgrade to 3072 dimensions
VECTOR_SIZE = 3072
_async_client = None

# Configure Google GenAI Client
_raw_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
_api_key = _raw_key.strip('"').strip("'").strip() if _raw_key else None
# Use the new SDK's client-based architecture
genai_client = genai.Client(api_key=_api_key)

async def get_async_qdrant_client() -> AsyncQdrantClient:
    global _async_client
    if _async_client is None:
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_url and qdrant_api_key:
            _async_client = AsyncQdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        else:
            _async_client = AsyncQdrantClient(path="./qdrant_db")
            
        try:
            exists = await _async_client.collection_exists(COLLECTION_NAME)
            if not exists:
                print(f"--- CREATING CLOUD-READY COLLECTION: {COLLECTION_NAME} ({VECTOR_SIZE} dims) ---")
                await _async_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
                )
        except Exception as e:
            print(f"Initial setup failed: {e}")
            
    return _async_client

def _embed_with_google(texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
    """
    Calls the modern Google GenAI SDK for embeddings. 
    Efficiently batches requests for multiple texts.
    """
    if not texts: return []
    try:
        # The new SDK's embed_content handles lists of strings natively
        res = genai_client.models.embed_content(
            model="gemini-embedding-2-preview", # Required for high-precision 3072 dims
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=VECTOR_SIZE # Maintain 3072 dimensions
            )
        )
        # Extract individual embedding values from the response
        return [e.values for e in res.embeddings]
    except Exception as e:
        print(f"Google GenAI Embedding Error: {e}")
        # Zero-vector fallback to prevent crash and ensure service continuity
        return [[0.0] * VECTOR_SIZE for _ in texts]

async def store_articles_in_qdrant(articles: List[dict]):
    if not articles: return
    client = await get_async_qdrant_client()
    
    texts = [f"{a.get('title','')}\n{a.get('summary','')}" for a in articles]
    
    try:
        # 1. Batch Embedding (One API call for up to 100 articles)
        vectors = await asyncio.to_thread(_embed_with_google, texts, "retrieval_document")
        
        points = []
        for i, a in enumerate(articles):
            p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, a.get('link', '')))
            payload = {
                "title": a.get("title", ""),
                "link": a.get("link", ""),
                "summary": a.get("summary", ""),
                "full_text": a.get("full_text", ""),
                "published_date": a.get("published_date", ""),
                "image_url": a.get("image_url", ""),
                "created_at": a.get("created_at", int(time.time())),
                "translations": a.get("translations", {})
            }
            points.append(PointStruct(id=p_id, vector=vectors[i], payload=payload))
            
        await client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"--- CLOUD STORE: Persisted {len(points)} articles with {VECTOR_SIZE}-dim embeddings ---")
    except Exception as e:
        print(f"Cloud store failed: {e}")

async def search_articles(query: str, limit: int = 5) -> List[dict]:
    client = await get_async_qdrant_client()
    try:
        # One API call per search (Minimal)
        vector = (await asyncio.to_thread(_embed_with_google, [query], "retrieval_query"))[0]
        res = await client.query_points(collection_name=COLLECTION_NAME, query=vector, limit=limit)
        return [dict(hit.payload) for hit in res.points]
    except Exception as e:
        print(f"Cloud search error: {e}")
        return []

async def is_article_ingested(link: str) -> bool:
    client = await get_async_qdrant_client()
    p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, link))
    try:
        res = await client.retrieve(collection_name=COLLECTION_NAME, ids=[p_id])
        return len(res) > 0
    except: return False

async def get_all_existing_links(limit: int = 2000) -> set:
    client = await get_async_qdrant_client()
    try:
        points, _ = await client.scroll(collection_name=COLLECTION_NAME, limit=limit, with_payload=True)
        return {p.payload.get('link') for p in points if p.payload}
    except: return set()

async def update_article_translations(link: str, lang: str, translated_data: dict):
    client = await get_async_qdrant_client()
    p_id = str(uuid.uuid5(uuid.NAMESPACE_URL, link))
    try:
        res = await client.retrieve(collection_name=COLLECTION_NAME, ids=[p_id])
        if not res: return
        payload = dict(res[0].payload)
        if "translations" not in payload: payload["translations"] = {}
        payload["translations"][lang.lower()] = translated_data
        await client.set_payload(collection_name=COLLECTION_NAME, payload=payload, points=[p_id])
    except: pass

async def delete_old_articles(days: int = 30):
    client = await get_async_qdrant_client()
    cutoff_ts = int(time.time()) - (days * 24 * 60 * 60)
    try:
        await client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(must=[FieldCondition(key="created_at", range=Range(lt=cutoff_ts))])
        )
    except: pass

async def get_latest_articles_fallback(limit: int = 15) -> List[dict]:
    client = await get_async_qdrant_client()
    try:
        points, _ = await client.scroll(collection_name=COLLECTION_NAME, limit=limit, with_payload=True)
        return [dict(p.payload) for p in points]
    except: return []

async def close_qdrant():
    global _async_client
    if _async_client:
        await _async_client.close()
        _async_client = None
