import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Shield } from 'lucide-react';

const Terms = () => {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      
      <main style={{ flexGrow: 1, padding: '4rem 2rem' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', background: 'white', padding: '3rem', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '1rem', borderRadius: '12px' }}>
              <Shield size={32} />
            </div>
            <div>
              <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px', margin: 0 }}>Terms of Service</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', margin: '0.5rem 0 0' }}>Last updated: {new Date().toLocaleDateString()}</p>
            </div>
          </div>
          
          <div className="legal-content" style={{ color: 'var(--text-main)', lineHeight: 1.8, fontSize: '1rem' }}>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>1. Agreement to Terms</h2>
            <p>
              By accessing and using Sanwariya Tech, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our service.
            </p>
            
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. Description of Service</h2>
            <p>
              Sanwariya Tech provides a clinic management dashboard and automated WhatsApp appointment booking services via the official Meta Graph API.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. User Responsibilities</h2>
            <p>
              You are responsible for maintaining the confidentiality of your account credentials (dashboard login). Clinic owners must ensure that they have the right to process their patients' medical appointments through our systems and comply with local healthcare privacy regulations.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. WhatsApp Usage Policies</h2>
            <p>
              Usage of the WhatsApp booking feature must comply with WhatsApp's Business and Commerce Policies. We reserve the right to suspend accounts that use the API for spam or unapproved marketing.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>5. Limitation of Liability</h2>
            <p>
              Sanwariya Tech is provided "as is" without warranties of any kind. We shall not be liable for missed appointments due to network downtime, Meta API outages, or misinterpretation by the automated AI agent.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Terms;
