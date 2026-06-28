import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, Lock, Mail } from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(email, password);
    if (success) {
      navigate('/dashboard');
    } else {
      alert("Login failed. Please check your credentials or Supabase configuration.");
    }
  };

  return (
    <div style={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {/* Background decorations */}
      <div style={{ position: 'absolute', top: '10%', right: '10%', width: '40%', height: '40%', background: 'radial-gradient(circle, hsla(var(--accent), 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: -1 }} />
      <div style={{ position: 'absolute', bottom: '10%', left: '10%', width: '30%', height: '30%', background: 'radial-gradient(circle, hsla(38, 100%, 50%, 0.1) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: -1 }} />

      <Link to="/" style={{ position: 'absolute', top: '2rem', left: '2rem', fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.5px' }}>
        Platform<span className="text-gradient">X</span>
      </Link>

      <div className="glass animate-fade-in" style={{ width: '100%', maxWidth: '400px', padding: '3rem 2rem', borderRadius: '1.5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Welcome Back</h1>
          <p style={{ color: 'hsl(var(--text-secondary))' }}>Sign in to continue to your dashboard.</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'hsl(var(--text-secondary))' }}>Email Address</label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-secondary))' }} />
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.75rem', borderRadius: '0.75rem', border: '1px solid var(--glass-border)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }} 
                placeholder="you@example.com" 
              />
            </div>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'hsl(var(--text-secondary))' }}>Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-secondary))' }} />
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.75rem', borderRadius: '0.75rem', border: '1px solid var(--glass-border)', background: 'rgba(0,0,0,0.2)', color: 'white', outline: 'none' }} 
                placeholder="••••••••" 
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary hover-lift" style={{ width: '100%', marginTop: '0.5rem' }}>
            Sign In <ArrowRight size={18} style={{ marginLeft: '0.5rem' }} />
          </button>
        </form>
        
        <p style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.9rem', color: 'hsl(var(--text-secondary))' }}>
          Don't have an account? <a href="#" style={{ color: 'hsl(var(--accent))' }}>Contact Sales</a>
        </p>
      </div>
    </div>
  );
};

export default Login;
