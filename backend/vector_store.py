import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt

load_dotenv()

COLLECTION_NAME = "et_news_v2"

_client = None

def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        try:
            qdrant_url = os.getenv("QDRANT_URL")
            qdrant_api_key = os.getenv("QDRANT_API_KEY")

            if qdrant_url and qdrant_api_key:
                # Connect to Qdrant Cloud
                print(f"Connecting to Qdrant Cloud at {qdrant_url}...")
                _client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            else:
                # Persistent local storage
                print("Using local Qdrant database (./qdrant_db)...")
                _client = QdrantClient(path="./qdrant_db")
            
            # Setup collection if missing
            if not _client.collection_exists(COLLECTION_NAME):
                _client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
                )
        except Exception as e:
            print(f"CRITICAL: Qdrant setup failed: {e}")
            # Fallback to in-memory if disk is locked, to prevent total crash
            _client = QdrantClient(":memory:")
            if not _client.collection_exists(COLLECTION_NAME):
                _client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
                )
    return _client

def close_qdrant():
    global _client
    if _client:
        try:
            _client.close()
            _client = None
        except:
            pass

@retry(wait=wait_exponential(multiplier=1.5, min=4, max=65), stop=stop_after_attempt(6))
def _embed_with_retry(model, text):
    return model.embed_query(text)

def store_articles_in_qdrant(articles):
    """
    Takes a list of dictionaries (containing title, summary, link, full_text).
    Generates embeddings for the text and upserts into Qdrant.
    """
    if not articles:
         return
         
    client = get_qdrant_client()
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    points = []
    
    for article in articles:
        # Combine title and text for a richer embedding representation
        text_to_embed = f"{article.get('title', '')}\n{article.get('summary', '')}\n{article.get('full_text', '')}"
        
        # Generate embedding with exponential backoff
        try:
             vector = _embed_with_retry(embeddings_model, text_to_embed)
        except Exception as e:
             print(f"Failed to embed article {article.get('title')}: {e}")
             continue
             
        # Create a unique, deterministic ID based on the link to prevent duplicates
        namespace = uuid.NAMESPACE_URL
        point_id = str(uuid.uuid5(namespace, article.get('link', '')))
        
        # Store metadata
        payload = {
            "title": article.get("title", ""),
            "link": article.get("link", ""),
            "summary": article.get("summary", ""),
            "published_date": article.get("published_date", ""),
            "full_text": article.get("full_text", ""),
            "image_url": article.get("image_url", "")
        }
        
        points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        
    # Upsert into Qdrant
    if points:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"Successfully stored {len(points)} articles in Qdrant.")
        
def search_articles(query, limit=5):
    """Searches Qdrant for the top relevant articles."""
    client = get_qdrant_client()
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    query_vector = embeddings_model.embed_query(query)
    
    search_result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit
    )
    
    results = []
    for hit in search_result.points:
        # Return a copy of the payload to prevent accidental mutations of the underlying in-memory DB objects
        results.append(dict(hit.payload))
        
    return results

def is_article_ingested(link: str) -> bool:
    """Checks if an article link already exists in the vector store."""
    client = get_qdrant_client()
    namespace = uuid.NAMESPACE_URL
    point_id = str(uuid.uuid5(namespace, link))
    try:
        # Check if the point exists by ID
        res = client.retrieve(collection_name=COLLECTION_NAME, ids=[point_id])
        return len(res) > 0
    except:
        return False
