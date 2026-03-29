# 🌐 ET News-Sphere: The AI-Native News Experience

> **ET Gen AI Hackathon 2026**  
> **Team Name:** Bit by Bit  
> **Project Title:** ET News-Sphere  
> **Team Members:** Aryan Silswal, Ranjan Singh
>
> **Deployed website:** https://et-news-sphere.vercel.app

---

## 🚩 The Problem Statement: 8-AI-Native News Experience
Business news in 2026 is still delivered like it's 2005 — static text articles, one-size-fits-all homepage,
same format for everyone. Build something that makes people say "I can't go back to reading news the
old way."

---

## ✔️ Our Solution: Transforming Consumption into Conversation
Business news in 2026 is a paradox: more information, less clarity. Professional users (Investors, Students, Founders) spend over **45 minutes daily** manually filtering through 100+ articles to find the "signal" in the "noise." 

**ET News-Sphere** solves this by moving from **Passive Reading** to **Active Intelligence**.

We have successfully combined three major challenge pillars into a single, unified platform that leverages the power of **Google Gemini 3.1 Flash Lite**.

### 1. 🧬 My ET — The Persona Feed
We don't just "filter" your news; we fundamentally reshape it based on your **Persona**.
- **Context-Aware Feeds**: A mutual fund investor receives deep dives into portfolio-relevant sectors, while a student gets "explainer-first" like how to start business content that defines financial jargon in real-time and a tech-enthusiast gets latest tech news.There Are total 7 categories - Student,Startup Founder,
Retail Investor,Tech Enthusiast,Working Professional/Corporate Excecutive,Policy Maker,Financial Advisor 
- **AI Recommendation Engine**: Our custom engine fetches the **Top 15** latest and most relevant articles from the Qdrant vector database using high-precision semantic search.
- **Interrogation Chat**: Each article includes a dedicated follow-up agent powered by Gemini 3.1 Flash Lite, allowing users to deep-dive into the context.

### 2. 🧭 News Navigator — Intelligence Agent Briefings
Say goodbye to "tab-fatigue." Instead of reading 8 separate articles about a major event, users interact with a single **Intelligence Agent Briefing**.
- **Internal Orchestration**: The agent manages 4 specialized sub-roles: **Researcher** (3-article retrieval), **Synthesis** (Drafting), **Auditor** (Citations), and **Vernacular** (Localization).
- **Factual Citations**: Every claim is anchored with citations back to original Economic Times coverage.
- **Interactive Synthesis**: Users can chat directly with the briefing to explore themes that span multiple articles.

### 3. 🌏 Vernacular Business News Engine
True Business inclusion requires language-native understanding, not just raw translation.
- **Persistent UI Localization**: The entire dashboard experience—from navigation to feed labels—is translated and persisted based on the user's language in Supabase.
- **Contextual Translation**: High-fidelity, real-time localization of every individual article and Intelligence Briefing into **English, Hindi, Tamil, Telugu, and Bengali**.
- **Native Interrogation**: Our follow-up Chat Agents (Gemini 3.1 Flash Lite) detect and respond natively in your selected language for a seamless experience.
- **Cultural Adaptation**: Explains complex Business concepts with relevant local context, bridging the professional literacy gap for non-English speakers.

---

## 🛠️ Tech Stack & Architecture

### **The Intelligence Core**
-   **Intelligence Agent**: A multi-functional logical orchestrator for briefings.
-   **AI Core**: Google **Gemini 3.1 Flash Lite** (High-Performance Inference) & **Google GenAI SDK**.
-   **Memory Layer**: **3072-dim Google Embeddings** (`google-embedding-2`) and **Qdrant Vector DB**.

### **The Systems Layer**
-   **Backend**: Python (FastAPI) for high-speed agentic logic.
-   **Frontend**: React (Vite) + Tailwind CSS. A premium **"Glassmorphism"** Dark Mode UI designed for 2026.
-   **Auth & Data**: **Supabase** for secure user authentication and profile (Persona DNA) persistence.
-   **Data Ingestion**: **ET Live RSS Feed** across 6 categories (Top Stories, Tech, Markets, Industry, Economy/Policy, Banking/Finance) can load upto 80 unique new articles on every Refresh Live News Click

---

## 💻 Local Setup & Installation

Follow these steps to experience the future of news on your local machine.

### **1. Prerequisites**
- Python 3.10+
- Node.js 18+
- Git

### **2. Backend Setup**
```bash
cd backend
python -m venv venv
# git-bash source venv/Scripts/activate  # Windows: venv\Scripts\activate (CMD/Powershell)
pip install -r requirements.txt 

# Create .env with:
# GEMINI_API_KEY=your_key
# SUPABASE_URL=your_url
# SUPABASE_ANON_KEY=your_anon_key
# Optional: QDRANT_URL & QDRANT_API_KEY for Cloud Qdrant

python -m uvicorn main:app --reload
```

### **3. Frontend Setup**
```bash
cd frontend
npm install

# Create .env with:
# VITE_SUPABASE_URL=your_url
# VITE_SUPABASE_ANON_KEY=your_anon_key
# VITE_API_URL=http://localhost:8000

npm run dev
```

---

## 🤝 Team Bit by Bit
- **Aryan Silswal**
- **Ranjan Singh**

---
*Built with ❤️ for the ET Gen AI Hackathon 2026*
