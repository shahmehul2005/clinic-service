import { ArrowRight, MessageSquare, Play, CheckCircle2, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useRef, useState } from 'react';

const Hero = () => {
  const { t } = useTranslation();
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setPlaying(!playing);
  };

  return (
    <>
      {/* ── HERO ── */}
      <div style={{ padding: '5rem 1.5rem 3rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', background: 'var(--bg-card)' }}>

        <div style={{ background: '#eff6ff', color: 'var(--primary)', padding: '0.4rem 1rem', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 600, marginBottom: '1.25rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <MessageSquare size={14} /> WhatsApp AI Receptionist
        </div>

        {/* Brand name */}
        <div style={{ fontSize: '1rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: '0.5rem' }}>
          Clinic Buddy
        </div>

        <h1 style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-1px', maxWidth: '800px', lineHeight: 1.1, marginBottom: '1.25rem' }}>
          {t('hero.title1')} <span style={{ color: 'var(--v0-green)' }}>{t('hero.title2')}</span>
        </h1>

        <p style={{ fontSize: 'clamp(1rem, 2vw, 1.2rem)', color: 'var(--text-secondary)', maxWidth: '580px', marginBottom: '2.5rem', lineHeight: 1.7 }}>
          {t('hero.subtitle')}
        </p>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          <Link to="/contact" className="btn btn-primary" style={{ padding: '0.875rem 1.75rem', fontSize: '1rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
            Start Free Trial <ArrowRight size={18} style={{ marginLeft: '0.5rem' }} />
          </Link>
          <button onClick={togglePlay} className="btn btn-outline" style={{ padding: '0.875rem 1.75rem', fontSize: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', border: 'none', cursor: 'pointer' }}>
            <Play size={18} /> {playing ? 'Pause Demo' : 'Watch Demo'}
          </button>
        </div>

        {/* Demo Video */}
        <div style={{ marginTop: '3.5rem', width: '100%', maxWidth: '900px', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 20px 60px rgba(0,0,0,0.15)', border: '1px solid var(--border-color)', position: 'relative', cursor: 'pointer' }} onClick={togglePlay}>
          <video
            ref={videoRef}
            src="/demo.mp4"
            style={{ width: '100%', display: 'block', maxHeight: '520px', objectFit: 'cover' }}
            playsInline
            onEnded={() => setPlaying(false)}
          />
          {!playing && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.3)', borderRadius: '16px' }}>
              <div style={{ width: '72px', height: '72px', background: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 20px rgba(0,0,0,0.3)' }}>
                <Play size={28} style={{ color: 'var(--primary)', marginLeft: '4px' }} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── PRICING ── */}
      <div style={{ padding: '5rem 1.5rem', background: 'var(--bg-page)', borderTop: '1px solid var(--border-color)' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: '#eff6ff', color: 'var(--primary)', padding: '0.4rem 1rem', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 600, marginBottom: '1.5rem' }}>
            <Zap size={14} /> Simple, Transparent Pricing
          </div>
          <h2 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.5rem)', fontWeight: 800, color: 'var(--text-main)', marginBottom: '0.75rem' }}>
            Start with a free 1-month trial
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginBottom: '3rem' }}>
            No hidden charges. Simple flat pricing after your trial.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
            {/* Setup */}
            <div className="card" style={{ padding: '2.5rem', textAlign: 'left', border: '2px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: '1rem' }}>One-Time Setup</div>
              <div style={{ fontSize: '2.75rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1 }}>₹10,000</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>paid once</div>
              {['WhatsApp AI integration', 'Clinic dashboard setup', 'Token & timed booking config', 'Team onboarding & training'].map(f => (
                <div key={f} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem', fontSize: '0.9rem', color: 'var(--text-main)' }}>
                  <CheckCircle2 size={16} style={{ color: 'var(--v0-green)', flexShrink: 0 }} /> {f}
                </div>
              ))}
            </div>

            {/* Monthly */}
            <div className="card" style={{ padding: '2.5rem', textAlign: 'left', border: '2px solid var(--primary)', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'var(--primary)', color: 'white', padding: '0.25rem 0.75rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 700 }}>RECOMMENDED</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Monthly Maintenance</div>
              <div style={{ fontSize: '2.75rem', fontWeight: 800, color: 'var(--primary)', lineHeight: 1 }}>₹1,000</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>per month</div>
              {['AI bot hosting & uptime', 'WhatsApp message processing', 'Dashboard access for all staff', 'Updates & support'].map(f => (
                <div key={f} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.6rem', fontSize: '0.9rem', color: 'var(--text-main)' }}>
                  <CheckCircle2 size={16} style={{ color: 'var(--v0-green)', flexShrink: 0 }} /> {f}
                </div>
              ))}
            </div>
          </div>

          <p style={{ marginTop: '2rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Start with a <strong>free 1-month trial</strong> — no payment required upfront.{' '}
            <Link to="/contact" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}>Contact us to get started →</Link>
          </p>
        </div>
      </div>
    </>
  );
};

export default Hero;

