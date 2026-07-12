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

            {/* Trial Request Form */}
            <div style={{ background: 'white', padding: '3rem', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', border: '1px solid var(--border-color)' }}>
              <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '2rem' }}>
                {t('demo.formTitle')}
              </h2>
              
              <form onSubmit={(e) => { e.preventDefault(); alert("Thanks! We will provision your sandbox account shortly."); }} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem' }}>{t('demo.nameLabel')}</label>
                  <input type="text" required placeholder="Dr. John Doe" className="form-input" />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem' }}>{t('demo.emailLabel')}</label>
                  <input type="email" required placeholder="john@clinic.com" className="form-input" />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem' }}>{t('demo.phoneLabel')}</label>
                  <input type="tel" required placeholder="+91 98765 43210" className="form-input" />
                </div>
                
                <button type="submit" className="btn-primary" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', padding: '1rem' }}>
                  {t('demo.submit')} <Send size={18} />
                </button>
              </form>
            </div>

          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Demo;
