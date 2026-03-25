import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabaseClient';
import { getTranslation } from '../lib/translations';
import ReactMarkdown from 'react-markdown';
import {
  RefreshCw, Search, User, Globe, LogOut, Loader2, Settings,
  LayoutGrid, BookOpen, ChevronRight, ArrowLeft, Zap, Star
} from 'lucide-react';

const DashboardPage = () => {
  const { user, signOut } = useAuth();

  // State Management
  const [isOnboarded, setIsOnboarded] = useState(false);
  const [persona, setPersona] = useState('Student');
  const [language, setLanguage] = useState('English');
  const [briefingTopic, setBriefingTopic] = useState('Technology Startups');
  const [activeTopic, setActiveTopic] = useState('');
  const [briefingImage, setBriefingImage] = useState(null);
  const [briefingContent, setBriefingContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [ingestionStatus, setIngestionStatus] = useState({ status: 'idle', scanned_count: 0, processed_count: 0 });
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const [isEditingPreferences, setIsEditingPreferences] = useState(false);

  // Follow Up Chat State
  const [followUpQuery, setFollowUpQuery] = useState('');
  const [followUpChat, setFollowUpChat] = useState([]);
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);

  // New State for UI Redesign
  const [activeTab, setActiveTab] = useState('feed'); // 'feed' or 'briefing'
  const [recommendedArticles, setRecommendedArticles] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [isFeedLoading, setIsFeedLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (message, isError = false) => {
    setToastMessage({ text: message, isError });
    setTimeout(() => setToastMessage(null), 3500);
  };

  const t = (key) => getTranslation(language, key);

  // Helper for determining API URL securely
  const getApiUrl = () => import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    let isMounted = true;
    
    const checkUserStatus = async () => {
      try {
        if (!user) {
          if (isMounted) setInitialCheckDone(true);
          return;
        }

        // Add extreme fallback timeout to prevent infinite spinner
        const timeoutFallback = setTimeout(() => {
          if (isMounted && !initialCheckDone) {
             console.warn("Supabase fetch took too long. Forcing app to initialize.");
             setInitialCheckDone(true);
          }
        }, 4000);

        const { data, error } = await supabase
          .from('users')
          .select('persona, preferred_language')
          .eq('id', user.id)
          .single();

        clearTimeout(timeoutFallback);

        if (data && isMounted) {
          setPersona(data.persona || 'Student');
          setLanguage(data.preferred_language || 'English');
          setIsOnboarded(true);
        }
      } catch (err) {
        console.error("User status check failed:", err);
      } finally {
        if (isMounted) setInitialCheckDone(true);
      }
    };

    checkUserStatus();
    
    return () => { isMounted = false; };
  }, [user]);

  useEffect(() => {
    if (isOnboarded && activeTab === 'feed') {
      fetchRecommendations();
    }
  }, [isOnboarded, activeTab, persona, language]);

  const fetchRecommendations = async () => {
    setIsFeedLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setIsFeedLoading(false);
        return;
      }

      const response = await fetch(`${getApiUrl()}/api/recommendations?persona=${persona}&limit=15&target_language=${language}`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      });
      const data = await response.json();
      if (response.ok) {
        // Backend returns a direct list of articles
        setRecommendedArticles(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error("Error fetching recommendations:", error);
    } finally {
      setIsFeedLoading(false);
    }
  };

  const handleOnboardingSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        showToast("Your session has expired. Please sign in again.", true);
        await signOut();
        return;
      }

      const response = await fetch(`${getApiUrl()}/api/onboarding`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          persona,
          preferred_language: language
        })
      });

      if (response.ok) {
        if (isOnboarded) {
          // Force logout on settings change to ensure deep caches and feeds reset perfectly
          showToast(t('Your settings have been updated. You will now be logged out to apply changes.'));
          setTimeout(async () => {
            await signOut();
          }, 2500);
          return;
        }
        setIsOnboarded(true);
        setIsEditingPreferences(false);
      } else {
        console.error("Failed onboarding");
      }
    } catch (error) {
      console.error("Error during onboarding:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const generateBriefing = async () => {
    if (!briefingTopic) return;
    setIsLoading(true);
    setBriefingContent('');
    setFollowUpChat([]);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 130000); // 130s overall timeout

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        showToast("Your session has expired. Please sign in again.", true);
        await signOut();
        return;
      }

      const response = await fetch(`${getApiUrl()}/api/briefing`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ topic: briefingTopic }),
        signal: controller.signal
      });

      const data = await response.json();
      if (response.ok) {
        setBriefingContent(data.briefing);
        setActiveTopic(data.topic || briefingTopic);
        setBriefingImage(data.image_url);
      } else {
        const errorMsg = data.detail || 'Failed to generate briefing';
        if (errorMsg.includes('429')) {
             setBriefingContent(`*The AI Oracle is currently at peak capacity (Rate Limit Hit). Please wait 10 seconds and try again.*`);
        } else {
             setBriefingContent(`*Error: ${errorMsg}*`);
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        showToast("Request timed out. The agent is still working in the background, please try again in a minute.", true);
        setBriefingContent('*Error: Briefing generation timed out. Please try again soon.*');
      } else {
        console.error("Error generating briefing:", error);
        setBriefingContent('*Error: Could not connect to the server.*');
      }
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
    }
  };

  const handleRefreshNews = async () => {
    setIsRefreshing(true);
    setIngestionStatus({ status: 'running', processed_count: 0, scanned_count: 0 });
    
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        showToast("Your session has expired. Please sign in again.", true);
        await signOut();
        return;
      }

      const response = await fetch(`${getApiUrl()}/api/trigger_ingestion`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${session.access_token}` },
      });

      if (response.ok) {
        showToast("Live News Extraction Started in Background!");
        
        // Start Polling for Status
        let lastCount = 0;
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch(`${getApiUrl()}/api/ingestion_status`, {
              headers: { "Authorization": `Bearer ${session.access_token}` },
            });
            const statusData = await statusRes.json();
            
            setIngestionStatus(statusData);
            
            if (statusData.processed_count > lastCount) {
               fetchRecommendations();
               lastCount = statusData.processed_count;
            }
            
            if (statusData.status === 'completed' || statusData.status === 'failed' || statusData.status === 'idle') {
              clearInterval(pollInterval);
              setIsRefreshing(false);
              if (statusData.status === 'completed') {
                  showToast(`Ingestion Complete! Added ${statusData.processed_count} articles.`);
              } else if (statusData.status === 'idle') {
                  showToast("Ingestion was interrupted by a server restart. Please try again.", true);
              }
            }
          } catch (err) {
            console.error("Polling error:", err);
            clearInterval(pollInterval);
            setIsRefreshing(false);
          }
        }, 3000);
      } else {
        setIsRefreshing(false);
        showToast("Failed to start ingestion", true);
      }
    } catch (error) {
      setIsRefreshing(false);
      console.error("Refresh error:", error);
      showToast("An error occurred during refresh.", true);
    }
  };

  const handleFollowUpSubmit = async (e) => {
    e.preventDefault();
    if (!followUpQuery.trim()) return;

    const userMsg = { role: 'user', text: followUpQuery };
    const newChat = [...followUpChat, userMsg];
    setFollowUpChat(newChat);
    setFollowUpQuery('');
    setIsFollowUpLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 70000); // 70s overall timeout

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { alert("Session expired."); return; }

      const contextType = selectedArticle ? 'article' : 'briefing';
      // ALWAYS prioritize full_text for the AI context, even if hidden from UI
      const contextText = selectedArticle
        ? `${selectedArticle.title}\n\n${selectedArticle.full_text || selectedArticle.summary}`
        : briefingContent;

      const response = await fetch(`${getApiUrl()}/api/followup`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          context_type: contextType,
          context_text: contextText,
          query: userMsg.text,
          history: newChat
        }),
        signal: controller.signal
      });

      const data = await response.json();
      if (response.ok) {
        setFollowUpChat([...newChat, { role: 'agent', text: data.response }]);
      } else {
        setFollowUpChat([...newChat, { role: 'agent', text: `*Error: ${data.detail || 'Failed'}*` }]);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        setFollowUpChat([...newChat, { role: 'agent', text: '*Error: Intelligence analysis timed out. The agent is busy, please try again in a moment.*' }]);
      } else {
        console.error(error);
        setFollowUpChat([...newChat, { role: 'agent', text: '*Error connecting to server.*' }]);
      }
    } finally {
      clearTimeout(timeoutId);
      setIsFollowUpLoading(false);
    }
  };

  const renderFollowUpChat = () => (
    <div className="mt-12 pt-8 border-t border-gray-800/50">
      <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-6">{t('Intelligence Interrogation')}</h3>

      {followUpChat.length > 0 && (
        <div className="space-y-6 mb-8 max-h-[400px] overflow-y-auto no-scrollbar pr-2">
          {followUpChat.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[90%] rounded-2xl p-5 ${msg.role === 'user' ? 'bg-red-900/40 border border-red-800/30 text-white rounded-tr-sm' : 'bg-gray-800/30 border border-gray-700/50 text-gray-300 rounded-tl-sm prose prose-sm prose-invert prose-red'}`}>
                {msg.role === 'agent' ? (
                  <ReactMarkdown 
                    components={{
                      a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-red-400 hover:underline" />
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                ) : (
                  <p className="text-sm font-medium">{msg.text}</p>
                )}
              </div>
            </div>
          ))}
          {isFollowUpLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-800/30 border border-gray-700/50 rounded-2xl p-5 flex items-center space-x-3 rounded-tl-sm">
                <Loader2 className="w-5 h-5 text-red-500 animate-spin" />
                <span className="text-xs font-bold text-gray-400 uppercase tracking-widest animate-pulse">{t('Synthesizing Response...')}</span>
              </div>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleFollowUpSubmit} className="relative group flex items-center">
        <input
          type="text"
          value={followUpQuery}
          onChange={(e) => setFollowUpQuery(e.target.value)}
          placeholder={t('Ask a specific question about this document...')}
          disabled={isFollowUpLoading}
          className="w-full bg-[#0f1115] border border-gray-800 rounded-2xl py-4 pl-6 pr-14 text-white placeholder-gray-600 focus:outline-none focus:border-red-500/50 focus:ring-4 focus:ring-red-500/10 transition-all text-sm font-medium disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isFollowUpLoading || !followUpQuery.trim()}
          className="absolute right-3 p-2 text-gray-500 hover:text-red-400 disabled:opacity-30 transition-colors bg-gray-900 rounded-xl"
        >
          <Search className="w-5 h-5" />
        </button>
      </form>
    </div>
  );

  if (!initialCheckDone) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // --- Onboarding Flow ---
  if (!isOnboarded) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8 bg-gray-800 p-8 rounded-xl border border-gray-700 shadow-2xl">
          <div>
            <h2 className="mt-2 text-center text-3xl font-extrabold text-white">{t('setupProfile')}</h2>
            <p className="mt-2 text-center text-sm text-gray-400">
              {t('customizeDna')}
            </p>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleOnboardingSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">{t('iAmA')}</label>
                <select
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Student">{t('student')}</option>
                  <option value="Startup Founder">{t('startupFounder')}</option>
                  <option value="Retail Investor">{t('retailInvestor')}</option>
                  <option value="Tech Enthusiast">{t('techEnthusiast')}</option>
                  <option value="Corporate Executive">{t('corporateExecutive')}</option>
                  <option value="Policy Maker">{t('policyMaker')}</option>
                  <option value="Financial Advisor">{t('financialAdvisor')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">{t('prefLang')}</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-md py-2 px-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Tamil">Tamil</option>
                  <option value="Telugu">Telugu</option>
                  <option value="Bengali">Bengali</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-gray-900 disabled:opacity-50 transition-colors"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : t('completeSetup')}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // --- Main Dashboard Flow ---
  return (
    <div className="min-h-screen bg-[#0f1115] text-gray-200 flex flex-col font-sans border-0 outline-none ring-0">
      {/* Premium Header */}
      <header className="sticky top-0 z-40 bg-[#161920]/80 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-6 md:space-x-10 lg:space-x-24">
            <div className="flex items-center space-x-3 group cursor-pointer shrink-0" onClick={() => { setActiveTab('feed'); setSelectedArticle(null); }}>
              <img src="/logo.png" alt="ET News-Sphere Logo" className="h-12 md:h-14 lg:h-20 w-auto scale-[1.75] md:scale-[2.15] origin-left object-contain group-hover:scale-[1.85] md:group-hover:scale-[2.4] transition-transform duration-300 filter drop-shadow-xl" />
            </div>

            <nav className="hidden md:flex items-center space-x-1 bg-gray-900/50 p-1 rounded-xl border border-gray-800">
              <button
                onClick={() => { setActiveTab('feed'); setSelectedArticle(null); }}
                className={`flex items-center space-x-2 px-5 py-2.5 rounded-2xl transition-all duration-300 focus:outline-none focus:ring-0 select-none ${activeTab === 'feed' ? 'bg-red-900/40 text-red-400 border border-red-800/30 shadow-[0_8px_20px_rgba(0,0,0,0.3)]' : 'text-gray-500 hover:text-gray-300 border-0 border-transparent shadow-none bg-transparent'}`}
              >
                <LayoutGrid className="w-5 h-5" />
                <span className="text-sm font-black uppercase tracking-widest leading-none">{t('myFeed')}</span>
              </button>
              <button
                onClick={() => { setActiveTab('briefing'); setSelectedArticle(null); }}
                className={`flex items-center space-x-2 px-5 py-2.5 rounded-2xl transition-all duration-300 focus:outline-none focus:ring-0 select-none ${activeTab === 'briefing' ? 'bg-red-900/40 text-red-400 border border-red-800/30 shadow-[0_8px_20px_rgba(0,0,0,0.3)]' : 'text-gray-500 hover:text-gray-300 border-0 border-transparent shadow-none bg-transparent'}`}
              >
                <Zap className="w-5 h-5" />
                <span className="text-sm font-black uppercase tracking-widest">{t('deepDiveBriefings')}</span>
              </button>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden lg:flex items-center space-x-3">
              <div className="flex flex-col items-end">
                <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">{t('iAmA')}</span>
                <span className="text-sm font-bold text-gray-200">
                  {t(persona.charAt(0).toLowerCase() + persona.slice(1).replace(/\s+/g, ''))}
                </span>
              </div>
              <div className="h-8 w-px bg-gray-800 mx-2"></div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleRefreshNews}
                disabled={isRefreshing}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-all shadow-lg hover:shadow-blue-500/20"
              >
                <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
                {isRefreshing ? `${t('ingesting')} (${ingestionStatus.scanned_count}/104)...` : t('refreshNews')}
              </button>

              <div className="flex items-center bg-gray-900/80 border border-gray-800 rounded-xl p-1">
                <button
                  onClick={() => setIsEditingPreferences(true)}
                  className="p-2.5 text-gray-400 hover:text-white transition-colors hover:bg-gray-800 rounded-lg"
                  title="Settings"
                >
                  <Settings className="w-6 h-6" />
                </button>
                <button
                  onClick={signOut}
                  className="p-2.5 text-gray-400 hover:text-red-400 transition-colors hover:bg-red-400/10 rounded-lg"
                  title="Sign Out"
                >
                  <LogOut className="w-6 h-6" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-6 py-8 border-0 outline-none ring-0 focus:outline-none focus:ring-0">
        {selectedArticle ? (
          /* Full Article View */
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl mx-auto bg-[#161920] rounded-3xl border border-gray-800/50 shadow-2xl overflow-hidden flex flex-col">
            <div className="relative h-[300px] md:h-[450px]">
              <img
                src={selectedArticle.image_url || '/api/placeholder/800/400'}
                alt={selectedArticle.title}
                className="w-full h-full object-cover"
                onError={(e) => e.target.src = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=2070&auto=format&fit=crop'}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#161920] via-transparent to-black/20"></div>
              <button
                onClick={() => setSelectedArticle(null)}
                className="absolute top-6 left-6 flex items-center space-x-2 bg-black/50 backdrop-blur-md hover:bg-black/70 text-white px-5 py-2.5 rounded-xl transition-all border border-gray-800 focus:outline-none shadow-xl"
              >
                <ArrowLeft className="w-4 h-4" strokeWidth={3} />
                <span className="font-bold text-xs uppercase tracking-widest">{t('backToFeed')}</span>
              </button>
            </div>

            <div className="px-8 py-10 md:px-16">
              <div className="flex items-center space-x-3 mb-6">
                <span className="px-3 py-1 bg-red-600/10 text-red-500 text-[10px] font-black uppercase tracking-[0.2em] rounded-md border border-red-500/20">
                  {t(persona.charAt(0).toLowerCase() + persona.slice(1).replace(/\s+/g, ''))}
                </span>
                <span className="text-gray-500 text-xs font-bold">{selectedArticle.published_date}</span>
              </div>

              <h1 className="text-3xl md:text-5xl font-black text-white mb-8 leading-[1.15] tracking-tight">
                {selectedArticle.title}
              </h1>

              <div className="bg-[#161920] rounded-2xl p-2 mb-8 border-0">
                <div className="text-gray-300 font-medium leading-relaxed whitespace-pre-wrap md:text-lg italic border-l-4 border-red-900/40 pl-6 py-4 bg-red-900/5">
                  {(selectedArticle.summary && !selectedArticle.summary.includes("Please provide the article text")) 
                    ? selectedArticle.summary 
                    : "Summary not provided by ET"}
                </div>
                <div className="mt-8 pt-8 border-t border-gray-800/30">
                   <p className="text-gray-500 text-xs font-bold uppercase tracking-widest text-center opacity-50">
                     {t('sourceTextHidden')}
                   </p>
                </div>
              </div>

              {renderFollowUpChat()}

              {selectedArticle.link && (
                <div className="pt-8 border-t border-gray-800/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">{t('originalSource')}</span>
                    <a
                      href={selectedArticle.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 font-bold flex items-center group/link text-sm"
                    >
                      {t('etOfficial')}
                      <ChevronRight className="w-4 h-4 ml-1 group-hover/link:translate-x-1 transition-transform" />
                    </a>
                  </div>
                  <button
                    onClick={() => setSelectedArticle(null)}
                    className="flex items-center space-x-3 bg-gray-800/50 hover:bg-gray-800 text-gray-300 px-6 py-3 rounded-2xl transition-all border border-gray-800/50 font-bold text-xs uppercase tracking-widest"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>{t('backToFeed')}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : activeTab === 'feed' ? (
          /* Recommendation Feed View */
          <div className="space-y-8 animate-in fade-in duration-700 focus:outline-none focus:ring-0">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <h2 className="text-4xl font-black text-white tracking-tight mb-2">
                  {t('myFeed')}
                </h2>
                <p className="text-gray-500 font-medium">
                  {t('curatedFor')} <span className="text-red-500/80 font-bold">{t(persona.charAt(0).toLowerCase() + persona.slice(1).replace(/\s+/g, ''))}</span>
                </p>
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] font-black text-gray-500 uppercase tracking-[0.2em] mb-1">{t('intelligenceStatus')}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full bg-red-800 animate-pulse"></div>
                  <span className="text-xs font-bold text-gray-300 uppercase tracking-widest">{t('aiRankingActive')}</span>
                </div>
              </div>
            </div>

            {isFeedLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 focus:outline-none focus:ring-0" tabIndex="-1">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="bg-gray-800/20 rounded-3xl h-[400px] animate-pulse border border-gray-800/50"></div>
                ))}
              </div>
            ) : recommendedArticles.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 focus:outline-none focus:ring-0" tabIndex="-1">
                {recommendedArticles.map((article, idx) => (
                  <div
                    key={idx}
                    onClick={() => { setSelectedArticle(article); setFollowUpChat([]); }}
                    className="group relative bg-[#161920] rounded-[2.5rem] border border-gray-800/30 overflow-hidden cursor-pointer hover:border-red-900/40 hover:shadow-[0_20px_40px_rgba(0,0,0,0.5)] transition-all duration-500 flex flex-col h-full focus:outline-none focus:ring-0 active:outline-none"
                  >
                    <div className="relative h-56 overflow-hidden">
                      <img
                        src={article.image_url || 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&q=80&w=800'}
                        alt={article.title}
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&q=80&w=800';
                        }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-[#161920] via-transparent to-transparent opacity-60"></div>
                      <div className="absolute bottom-4 left-6">
                        <span className="bg-gray-900/80 backdrop-blur-md text-[9px] font-black text-gray-300 px-3 py-1 rounded-full border border-gray-800/30 uppercase tracking-widest">
                          {article.published_date?.split(' ')[0] || 'Today'}
                        </span>
                      </div>
                    </div>
                    <div className="p-8 flex-1 flex flex-col">
                      <h3 className="text-xl font-bold text-white mb-4 leading-snug group-hover:text-red-400 transition-colors line-clamp-3">
                        {article.title}
                      </h3>
                      <p className="text-gray-400 text-sm leading-relaxed mb-6 line-clamp-3 flex-1">
                        {(article.summary && !article.summary.includes("Please provide the article text")) 
                          ? article.summary 
                          : "Summary not provided by ET"}
                      </p>
                      <div className="flex items-center justify-between pt-4 border-t border-gray-800/50">
                        <span className="flex items-center text-xs font-bold text-gray-500 group-hover:text-gray-300 transition-colors">
                          <BookOpen className="w-3 h-3 mr-2" />
                          3 {t('minRead')}
                        </span>
                        <ChevronRight className="w-5 h-5 text-gray-700 group-hover:text-red-500 group-hover:translate-x-1 transition-all" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-20 flex flex-col items-center justify-center bg-gray-800/20 rounded-[3rem] border border-dashed border-gray-700/50 max-w-2xl mx-auto">
                <LayoutGrid className="w-16 h-16 text-gray-700 mb-6" />
                <p className="text-gray-400 font-bold mb-8 text-center px-10 leading-relaxed uppercase tracking-widest text-[10px]">
                  {t('emptyFeedText')}
                </p>
                <button
                  onClick={handleRefreshNews}
                  disabled={isRefreshing}
                  className="flex items-center space-x-3 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-xl active:scale-95"
                >
                  <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  <span>{isRefreshing ? `${t('ingesting')} (${ingestionStatus.scanned_count}/104)...` : t('refreshNews')}</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Conventional Briefing Tool View (Redesigned) */
          <div className="flex flex-col lg:flex-row gap-10 animate-in fade-in duration-700 h-full">
            {/* Sidebar Controls */}
            <div className="w-full lg:w-[380px] space-y-8">
              <div className="bg-[#161920] rounded-3xl p-8 border border-gray-800/50 shadow-xl relative overflow-hidden">
                <div className="absolute top-[-10%] right-[-10%] p-4 opacity-[0.03] pointer-events-none rotate-12">
                  <Search className="w-64 h-64" />
                </div>

                <h2 className="text-2xl font-black text-white mb-3 relative z-10 tracking-tight">{t('intelligenceBriefing')}</h2>
                <p className="text-sm text-gray-500 font-medium mb-8 relative z-10 leading-relaxed">
                  {t('enterTopicDesc')}
                </p>

                <div className="space-y-6 relative z-10">
                  <div className="space-y-3">
                    <label className="block text-[10px] font-black text-gray-500 uppercase tracking-widest pl-1">
                      {t('whatTopic')}
                    </label>
                    <div className="relative group">
                      <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-600 group-focus-within:text-red-500 transition-colors" />
                      <input
                        type="text"
                        value={briefingTopic}
                        onChange={(e) => setBriefingTopic(e.target.value)}
                        placeholder={t('placeholder')}
                        className="w-full bg-[#0f1115] border border-gray-800 rounded-2xl py-4 pl-12 pr-6 text-white placeholder-gray-700 focus:outline-none focus:border-red-500/50 focus:ring-4 focus:ring-red-500/10 transition-all font-medium"
                      />
                    </div>
                  </div>

                  <button
                    onClick={generateBriefing}
                    disabled={isLoading || !briefingTopic}
                    className="w-full flex items-center justify-center space-x-3 bg-red-900/80 hover:bg-red-800 text-white font-black py-5 px-6 rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.3)] transition-all active:scale-[0.98] disabled:opacity-50 disabled:shadow-none uppercase tracking-widest text-sm focus:outline-none focus:ring-2 focus:ring-red-900/20"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>{t('agentWorking')}</span>
                      </>
                    ) : (
                      <>
                        <span>{t('generateBriefing')}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Process Visualization */}
              <div className="bg-[#161920]/40 rounded-3xl p-8 border border-gray-800/30">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mb-6">{t('underTheHood')}</h3>
                <div className="space-y-6 relative">
                  <div className="absolute left-[13px] top-2 bottom-2 w-0.5 bg-gray-800/50"></div>

                  {[
                    { name: 'Intelligence Agent', color: 'red', desc: 'Synthesizes context and tailors the final report to your persona', icon: 'bg-red-500' }
                  ].map((agent, i) => (
                    <div key={i} className="flex items-start space-x-4 relative z-10 transition-all duration-300">
                      <div className={`mt-1.5 w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isLoading ? `${agent.icon}/20 border border-${agent.color}-500/30 animate-pulse` : 'bg-gray-800 border border-gray-700'}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${isLoading ? agent.icon : 'bg-gray-600'}`}></div>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs font-black text-gray-100 uppercase tracking-wider">{agent.name}</span>
                        <span className="text-[11px] text-gray-500 font-medium leading-relaxed mt-0.5">{agent.desc.length > 50 ? agent.desc.substring(0, 50) + '...' : agent.desc}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Output Display */}
            <div className="flex-1 min-h-[600px] flex flex-col">
              <div className="flex-1 bg-[#161920] rounded-[2.5rem] border border-gray-800/50 shadow-2xl overflow-hidden flex flex-col">
                <div className="border-b border-gray-800/50 px-10 h-20 bg-[#161920]/50 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
                  <h2 className="text-xl font-black text-white tracking-tight">
                    {briefingContent ? t('reportTitle') : t('awaitingInput')}
                  </h2>
                  {briefingContent && !isLoading && (
                    <div className="flex flex-col">
                      <span className="text-[11px] font-black text-gray-500 uppercase tracking-[0.2em] mb-1">Intelligence Status</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 rounded-full bg-red-800 animate-pulse"></div>
                        <span className="text-xs font-bold text-gray-300 uppercase tracking-widest">AI Ranking Active</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex-1 p-10 overflow-y-auto no-scrollbar">
                  {isLoading ? (
                    <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-6">
                      <div className="relative">
                        <div className="absolute inset-0 bg-red-500/20 blur-2xl animate-pulse rounded-full"></div>
                        <Loader2 className="w-12 h-12 animate-spin text-red-600 relative z-10" />
                      </div>
                      <p className="font-bold tracking-widest uppercase text-xs animate-pulse opacity-70">{t('agentsAnalyzing')}</p>
                    </div>
                  ) : briefingContent ? (
                    <div className="animate-in fade-in duration-1000">
                      {briefingImage && (
                        <div className="mb-10 rounded-[2rem] overflow-hidden border border-gray-800/50 shadow-2xl">
                          <img
                            src={briefingImage}
                            alt="Cover"
                            className="w-full h-56 md:h-80 object-cover"
                          />
                        </div>
                      )}
                      <div className="prose prose-invert prose-red max-w-none prose-headings:font-black prose-headings:tracking-tighter prose-p:text-gray-300 prose-p:leading-relaxed">
                        <ReactMarkdown
                          components={{
                            a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-red-400 hover:underline" />
                          }}
                        >
                          {briefingContent}
                        </ReactMarkdown>
                      </div>

                      {renderFollowUpChat()}
                    </div>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center space-y-8 opacity-30">
                      <Globe className="w-32 h-32 text-gray-200" strokeWidth={1} />
                      <p className="text-center max-w-sm font-bold text-gray-400 leading-relaxed uppercase tracking-widest text-xs">
                        {t('emptyStateText')}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Settings Modal Layer (Upgraded) */}
      {isEditingPreferences && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <div className="max-w-md w-full bg-[#161920] p-10 rounded-[2.5rem] border border-gray-800 shadow-2xl relative animate-in zoom-in-95 duration-300">
            <button
              onClick={() => setIsEditingPreferences(false)}
              className="absolute top-6 right-6 w-8 h-8 flex items-center justify-center bg-gray-800 rounded-full text-gray-400 hover:text-white transition-colors"
            >
              ✕
            </button>
            <h2 className="text-4xl font-black text-gray-100 mb-3 tracking-tight">{t('updatePrefs')}</h2>
            <p className="text-gray-500 text-base font-medium mb-10">{t('refineIdentity')}</p>

            <form className="space-y-10" onSubmit={handleOnboardingSubmit}>
              <div className="space-y-8">
                <div className="space-y-4">
                  <label className="block text-xs font-black text-gray-500 uppercase tracking-[0.2em] pl-1">{t('iAmA')}</label>
                  <select
                    value={persona}
                    onChange={(e) => setPersona(e.target.value)}
                    className="w-full bg-[#0f1115] border border-gray-800 rounded-2xl py-5 px-6 text-gray-200 text-base focus:outline-none focus:border-red-900/50 focus:ring-4 focus:ring-red-900/10 transition-all font-bold"
                  >
                    <option value="Student">{t('student')}</option>
                    <option value="Startup Founder">{t('startupFounder')}</option>
                    <option value="Retail Investor">{t('retailInvestor')}</option>
                    <option value="Tech Enthusiast">{t('techEnthusiast')}</option>
                    <option value="Corporate Executive">{t('corporateExecutive')}</option>
                    <option value="Policy Maker">{t('policyMaker')}</option>
                    <option value="Financial Advisor">{t('financialAdvisor')}</option>
                  </select>
                </div>
                <div className="space-y-4">
                  <label className="block text-xs font-black text-gray-500 uppercase tracking-[0.2em] pl-1">{t('prefLang')}</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full bg-[#0f1115] border border-gray-800 rounded-2xl py-5 px-6 text-gray-200 text-base focus:outline-none focus:border-red-900/50 focus:ring-4 focus:ring-red-900/10 transition-all font-bold"
                  >
                    <option value="English">English</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Telugu">Telugu</option>
                    <option value="Bengali">Bengali</option>
                  </select>
                </div>
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-5 px-8 border border-transparent rounded-2xl shadow-xl text-sm font-black text-white bg-red-900/80 hover:bg-red-800 transition-all disabled:opacity-50 uppercase tracking-widest mb-4"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : t('saveChanges')}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div className={`fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 rounded-full shadow-2xl flex items-center space-x-3 transition-opacity duration-300 animate-in slide-in-from-bottom-5 ${toastMessage.isError ? 'bg-red-900 border border-red-500 text-white' : 'bg-green-900 border border-green-500 text-white'}`}>
          <span className="font-bold text-sm tracking-wide">{toastMessage.text}</span>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
