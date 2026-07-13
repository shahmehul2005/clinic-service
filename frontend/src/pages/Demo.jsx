import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { PlayCircle, Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const Demo = () => {
  const { t } = useTranslation();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      
      <main style={{ flexGrow: 1, padding: '4rem 2rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          
          <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
            <h1 style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-1px', marginBottom: '1rem' }}>
              {t('demo.title')}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem', maxWidth: '600px', margin: '0 auto' }}>
              {t('demo.subtitle')}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '3rem' }}>
            
            {/* Video Placeholder */}
            <div style={{ background: 'black', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.2)', position: 'relative', aspectRatio: '16/9', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
               <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'linear-gradient(45deg, rgba(37,99,235,0.2), rgba(16,185,129,0.2))' }}></div>
               <div style={{ zIndex: 10, textAlign: 'center', color: 'white' }}>
                 <PlayCircle size={64} style={{ marginBottom: '1rem', opacity: 0.8 }} />
                 <h3 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Demo Video (Coming Soon)</h3>
                 <p style={{ opacity: 0.8 }}>Embed your YouTube or Loom link here</p>
               </div>
            </div>

            {/* Contact Sales Card */}
            <div style={{ background: 'white', padding: '3rem', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>
                Start Your 7-Day Trial
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: '2.5rem', lineHeight: 1.6 }}>
                We provide a white-glove onboarding experience. Contact our sales team directly to provision your secure sandbox account today.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <a href="mailto:support@sanwariyatech.dev" className="btn-primary" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.75rem', padding: '1.25rem', textDecoration: 'none', background: 'var(--v0-blue)' }}>
                  Email Sales Team <Send size={20} />
                </a>
                
                <a href="https://wa.me/919876543210" target="_blank" rel="noopener noreferrer" className="btn-outline" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.75rem', padding: '1.25rem', textDecoration: 'none', border: '2px solid var(--v0-green)', color: 'var(--v0-green)', fontWeight: 600, borderRadius: '8px' }}>
                  Chat on WhatsApp
                </a>
              </div>
            </div>

          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Demo;
