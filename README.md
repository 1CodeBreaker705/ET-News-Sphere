# 🌐 ET News-Sphere: The AI-Native News Experience

> **ET Gen AI Hackathon 2026**  
> **Team Name:** Bit by Bit  
> **Project Title:** ET News-Sphere  
> **Team Members:** Aryan Silswal, Ranjan Singh

---

## 🚩 The Problem Statement

> "Business news in 2026 is still delivered like it's 2005 — static text articles, one-size-fits-all homepage, same format for everyone. Build something that makes people say 'I can't go back to reading news the old way.'"

---

## 🚀 Our Solution: Transforming Consumption into Conversation

We have successfully combined three major challenge pillars into a single, unified platform that moves beyond static reading into **Active Intelligence**.

### 1. 🧬 My ET — The Personalized Newsroom

We don't just "filter" your news; we fundamentally reshape it based on your **Persona**.

- **Context-Aware Feeds**: A mutual fund investor receives deep dives into portfolio-relevant sectors, while a student gets "explainer-first" content that defines jargon in real-time.
- **Dynamic Prioritization**: The interface adapts to what matters most to your financial journey, ensuring no signal is lost in the noise.

### 2. 🧭 News Navigator — Interactive Intelligence Briefings

Say goodbye to tab-fatigue. Instead of reading 8 separate articles about a major event (like a Union Budget), users interact with a single **LangGraph-powered Deep Briefing**.

- **Synthesis-First**: Merges coverage from across the Economic Times ecosystem into one cohesive, explorable document.
- **Factual Citations**: Every claim is anchored with citations back to the original ET coverage.

### 3. 🌏 Vernacular Business News Engine

True financial inclusion requires language-native understanding, not just translation.

- **Contextual localization**: Real-time translation into **Hindi, Tamil, Telugu, and Bengali**.
- **Cultural Adaptation**: Our LLM agents explain Western financial concepts with local context and analogies, bridging the literacy gap.

---

### 4. 🔍 Deep-Context Intelligence Interrogation

Instead of a long, cluttered page of text, users interact with a **Summary-Only Reader Mode**.

- **Clean UI**: We hide the multi-thousand-word body text to prevent information overload.
- **Full-Context Chat**: Our "Intelligence Interrogation" bot remains powered by the entire article body in the background, allowing you to ask hyper-specific questions even if it's not in the summary.
- **Seamless Sourcing**: All citations and original ET source links open automatically in new tabs, keeping your research flow uninterrupted.

---

## 🛠️ Tech Stack & Architecture

### **The Intelligence Layer (Multi-Agent Orchestration)**

Powered by **LangGraph**, our system uses a sophisticated multi-agent workflow:

- **Researcher Agent**: Scours 14+ Economic Times RSS feeds and pulls full-text content using BeautifulSoup.
- **Synthesis Agent**: Merges fragmented data into a cohesive narrative.
- **Vernacular Agent**: Localizes content with cultural context.
- **Auditor Agent**: Ensures factual integrity and citation accuracy.

### **The "How It Works" (Technical Specs)**

- **Frontend**: React (Vite) + Tailwind CSS. A premium "Glassmorphism" Dark Mode UI designed for 2026.
- **Backend**: Python (FastAPI) & LangGraph for logic.
- **AI Core**: Google Gemini 3.1 Flash Lite & Gemini Embeddings (`embedding-001`).
- **Database**:
  - **Qdrant**: High-performance Vector Database for Semantic Search and RAG.
  - **Supabase**: PostgreSQL for user profiles, JWT Authentication, and "Profile" storage.
- **Data Pipeline**: Real-time BeautifulSoup scraping of 140+ daily articles. We prioritize professional **OG (Open Graph) Descriptions** and **Synopsis** boxes to ensure a perfect summary experience even when RSS counts are low.

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
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
# Create a .env file with your GEMINI_API_KEY and SUPABASE constants
python -m uvicorn main:app --reload
```

### **3. Frontend Setup**

```bash
cd frontend
npm install
# Create a .env file with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm run dev
```

---

## 🤝 Team Bit by Bit

- **Aryan Silswal** 
- **Ranjan Singh** 
---

_Built with ❤️ for the ET Gen AI Hackathon 2026_
