import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

security = HTTPBearer()

import jwt

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not SUPABASE_JWT_SECRET:
        # Fallback to network if no secret is provided (slower)
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase not configured")
        try:
            response = supabase.auth.get_user(token)
            user_obj = response.user
            if not user_obj:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"sub": user_obj.id, "email": user_obj.email, "user_metadata": user_obj.user_metadata, "access_token": token}
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

    try:
        # Offline JWT Validation (Zero Network Handshakes = No _ssl.c errors)
        # Dynamically get the algorithm from the token header (Supabase uses HS256, but others might differ)
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=[alg], 
            options={"verify_aud": False}
        )
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "user_metadata": payload.get("user_metadata", {}),
            "access_token": token
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except Exception as local_decode_err:
        # Final fallback: If local decode fails (e.g., malformed token, mismatched algorithm, secret issues),
        # safely fall back to the Supabase SDK network ping.
        if supabase:
            try:
                response = supabase.auth.get_user(token)
                user_obj = response.user
                if user_obj:
                    return {
                        "sub": user_obj.id,
                        "email": user_obj.email,
                        "user_metadata": user_obj.user_metadata,
                        "access_token": token
                    }
            except Exception as network_err:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail=f"Local Auth Failed: {str(local_decode_err)[0:30]} | Network Auth Failed (Possible SSL Timeout): {str(network_err)[0:40]}"
                )
        
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(local_decode_err)}")
