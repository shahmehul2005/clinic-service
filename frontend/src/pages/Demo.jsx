import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Send, Play, MessageSquare, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';

const Demo = () => {
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
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ flexGrow: 1 }}>

        {/* ── Hero ── */}
        <div style={{ padding: '4rem 1.5rem 2rem', textAlign: 'center', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: '#eff6ff', color: 'var(--primary)', padding: '0.35rem 1rem', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 600, marginBottom: '1.25rem' }}>
            <Play size={13} /> Live Demo
          </div>
          <h1 style={{ fontSize: 'clamp(1.75rem, 4vw, 3rem)', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-1px', marginBottom: '1rem' }}>
            See Clinic Buddy in Action
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', maxWidth: '560px', margin: '0 auto 2rem' }}>
            Watch how your clinic runs on WhatsApp AI — tokens, appointments, reports and reviews, all automated.
          </p>
        </div>

        {/* ── Video ── */}
        <div style={{ padding: '3rem 1.5rem', background: 'var(--bg-page)' }}>
          <div style={{ maxWidth: '900px', margin: '0 auto', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 20px 60px rgba(0,0,0,0.15)', border: '1px solid var(--border-color)', position: 'relative', cursor: 'pointer', background: 'black' }} onClick={togglePlay}>
            <video
              ref={videoRef}
              src="/demo.mp4"
              style={{ width: '100%', display: 'block', maxHeight: '520px', objectFit: 'contain' }}
              playsInline
              onEnded={() => setPlaying(false)}
            />
            {!playing && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.35)' }}>
                <div style={{ width: '80px', height: '80px', background: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.3)', transition: 'transform 0.2s' }}>
                  <Play size={30} style={{ color: 'var(--primary)', marginLeft: '5px' }} />
                </div>
              </div>
            )}
          </div>
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '1rem' }}>
            Click to play · Clinic Buddy demo walkthrough
          </p>
        </div>

        {/* ── CTA Cards ── */}
        <div style={{ padding: '3rem 1.5rem 5rem', background: 'var(--bg-card)', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ maxWidth: '900px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>

            {/* Start Trial */}
            <div className="card" style={{ padding: '2.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ width: '48px', height: '48px', background: '#eff6ff', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                <ArrowRight size={24} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>Start Free Trial</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                  Get 1 month free. We set everything up for you — no tech knowledge needed.
                </p>
              </div>
              <Link
                to="/contact"
                style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', background: 'var(--primary)', color: 'white', padding: '0.875rem 1.25rem', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none' }}
              >
                Get Started <ArrowRight size={18} />
              </Link>
            </div>

            {/* Email Sales */}
            <div className="card" style={{ padding: '2.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ width: '48px', height: '48px', background: '#f0fdf4', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16a34a' }}>
                <Send size={24} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>Email Sales Team</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                  Have questions about pricing or setup? Write directly to our sales team.
                </p>
              </div>
              <a
                href="mailto:support@sanwariyatech.dev?subject=Clinic Buddy Demo Inquiry&body=Hi, I watched the demo and I'd like to learn more about Clinic Buddy."
                style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', background: '#16a34a', color: 'white', padding: '0.875rem 1.25rem', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none' }}
              >
                <Send size={18} /> Email Sales Team
              </a>
            </div>

            {/* WhatsApp */}
            <div className="card" style={{ padding: '2.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ width: '48px', height: '48px', background: '#f0fdf4', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16a34a' }}>
                <MessageSquare size={24} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>Chat on WhatsApp</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>
                  Prefer WhatsApp? Message us directly — we usually reply within minutes.
                </p>
              </div>
              <a
                href="https://wa.me/919256653646?text=Hi, I'd like to know more about Clinic Buddy"
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', background: '#25d366', color: 'white', padding: '0.875rem 1.25rem', borderRadius: '8px', fontWeight: 600, fontSize: '0.95rem', textDecoration: 'none' }}
              >
                <MessageSquare size={18} /> Open WhatsApp
              </a>
            </div>

          </div>
        </div>

      </main>

      <Footer />
    </div>
  );
};

export default Demo;
