import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Loader2, Globe, Mail, Lock, ChevronRight, ShieldCheck } from 'lucide-react';

const LoginPage = () => {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      if (isSignUp) {
        const data = await signUpWithEmail(email, password);
        if (!data?.session) {
          setMessage('Account created! Please verify your email.');
        } else {
          setMessage('Success! Redirecting...');
        }
      } else {
        await signInWithEmail(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f1115] flex flex-col items-center justify-start pt-4 md:pt-12 p-6 relative overflow-hidden font-sans">
      {/* Dynamic Background Accents */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-red-600/10 blur-[120px] rounded-full"></div>

      <div className="max-w-[450px] w-full z-10">
        {/* Logo Section */}
        <div className="flex flex-col items-center mb-4 animate-in fade-in slide-in-from-top-4 duration-700">
          <div className="flex items-center justify-center mb-2 group">
            <img 
              src="/logo.png" 
              alt="ET News-Sphere Logo" 
              className="h-32 md:h-40 w-auto scale-[1.8] origin-center object-contain drop-shadow-2xl" 
            />
          </div>
          <p className="text-gray-500 font-bold uppercase tracking-[0.4em] text-xs">
            Intelligence Reimagined
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[#161920]/40 backdrop-blur-2xl p-10 rounded-[2.5rem] border border-white/5 shadow-2xl animate-in fade-in zoom-in-95 duration-700 delay-100">
          <div className="mb-10">
            <h2 className="text-2xl font-black text-white tracking-tight mb-2">
              {isSignUp ? 'Create Strategic Account' : 'Welcome Back'}
            </h2>
            <p className="text-gray-500 text-sm font-medium">
              {isSignUp ? 'Join the elite news synthesis platform.' : 'Access your personalized intelligence feed.'}
            </p>
          </div>

          {error && (
            <div className="mb-6 bg-red-500/10 border border-red-500/20 text-red-500 px-5 py-3 rounded-2xl text-xs font-bold flex items-center gap-3 animate-in shake-in">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
              {error}
            </div>
          )}
          
          {message && (
            <div className="mb-6 bg-green-500/10 border border-green-500/20 text-green-500 px-5 py-3 rounded-2xl text-xs font-bold flex items-center gap-3 animate-in slide-in-from-top-2">
              <ShieldCheck className="w-4 h-4" />
              {message}
            </div>
          )}

          <form className="space-y-5" onSubmit={handleEmailAuth}>
            <div className="space-y-1 relative group">
              <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-red-500 transition-colors" />
              <input
                type="email"
                required
                className="w-full bg-[#0f1115] border border-white/5 rounded-2xl py-4 pl-12 pr-6 text-white text-sm font-bold placeholder-gray-700 focus:outline-none focus:border-red-500/40 transition-all"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1 relative group">
              <Lock className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within:text-red-500 transition-colors" />
              <input
                type="password"
                required
                className="w-full bg-[#0f1115] border border-white/5 rounded-2xl py-4 pl-12 pr-6 text-white text-sm font-bold placeholder-gray-700 focus:outline-none focus:border-red-500/40 transition-all"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center space-x-4 bg-red-900/80 hover:bg-red-800 text-gray-100 font-black py-5 rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.3)] transition-all active:scale-[0.98] disabled:opacity-50 mt-10 uppercase tracking-widest text-sm"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                <>
                  <span>{isSignUp ? 'Initialize Profile' : 'Gain Access'}</span>
                  <ChevronRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          <div className="flex items-center my-10 px-4">
            <div className="flex-1 h-px bg-white/5"></div>
            <span className="px-5 text-[10px] font-black text-gray-700 uppercase tracking-widest">Or authenticate via</span>
            <div className="flex-1 h-px bg-white/5"></div>
          </div>

          <button
            onClick={signInWithGoogle}
            className="w-full flex items-center justify-center space-x-3 bg-white text-black font-black py-4 rounded-2xl hover:bg-gray-100 transition-all active:scale-[0.98] shadow-xl uppercase tracking-widest text-xs"
          >
            <svg className="h-5 w-5" viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.64 24.55c0-1.65-.15-3.23-.42-4.75H24v9h12.75c-.55 2.87-2.17 5.3-4.61 6.93l7.26 5.64c4.25-3.92 6.71-9.69 6.71-16.82z"/>
              <path fill="#FBBC05" d="M10.54 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.98-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.26-5.64c-2.21 1.49-5.04 2.37-8.63 2.37-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            </svg>
            <span>Google Login</span>
          </button>

          <div className="text-center mt-10">
            <button 
              type="button" 
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-[10px] font-black text-gray-500 hover:text-red-500 transition-colors uppercase tracking-[0.2em]"
            >
              {isSignUp ? 'Already a strategist? Sign In' : "New User? Create Account"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
