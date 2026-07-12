import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Shield } from 'lucide-react';

const Privacy = () => {
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
              <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px', margin: 0 }}>Privacy Policy</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', margin: '0.5rem 0 0' }}>Last updated: {new Date().toLocaleDateString()}</p>
            </div>
          </div>
          
          <div className="legal-content" style={{ color: 'var(--text-main)', lineHeight: 1.8, fontSize: '1rem' }}>
            
            <p>
              Sanwariya Tech ("we", "our", or "us") develops software solutions for businesses, including AI-powered appointment management, communication automation, and cloud services. We respect your privacy and are committed to protecting it.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>1. Information We Collect</h2>
            <p>
              When you interact with Sanwariya Tech via our websites, WhatsApp Business integrations, or cloud platforms, we may collect: personal identification information (e.g., Name, Phone Number, WhatsApp Meta IDs) and system usage data.
            </p>
            
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. Legal Basis & How We Use Your Data</h2>
            <p>
              We process your information only for providing our services, responding to your requests, fulfilling contractual obligations, complying with legal requirements, or where you have provided consent. The data collected is strictly used for facilitating our AI software solutions, sending automated reminders, and improving our platforms. We do not sell your personal data to third parties.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. Third-Party Services</h2>
            <p>
              We may use trusted third-party service providers to host our application, database, analytics, and communication services. These providers process data only as necessary to provide the requested services. These include, but are not limited to:
            </p>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li><strong>Meta (WhatsApp Business Platform):</strong> For messaging automation and delivery.</li>
              <li><strong>Vercel & Render:</strong> For hosting our web platforms and APIs.</li>
              <li><strong>Supabase:</strong> For secure database management and authentication.</li>
            </ul>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. Cookies</h2>
            <p>
              Our website may use cookies and similar technologies to improve user experience, analyze traffic, and enhance website functionality.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>5. User Rights</h2>
            <p>
              Depending on your location, you may have certain rights regarding your personal information. You may request to <strong>access</strong>, <strong>correct</strong>, <strong>update</strong>, or <strong>delete</strong> your information by contacting us.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>6. Security</h2>
            <p>
              We implement a variety of security measures to maintain the safety of your personal information, including HMAC SHA-256 signature validation for all incoming integrations and strict database security rules.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>7. Contact Information</h2>
            <p>
              If you have any questions about this Privacy Policy or wish to exercise your data rights, please contact us at:
            </p>
            <address style={{ fontStyle: 'normal', marginTop: '0.5rem', padding: '1rem', background: 'var(--bg-page)', borderRadius: '8px' }}>
              <strong>Sanwariya Tech</strong><br/>
              Email: <a href="mailto:support@sanwariyatech.dev" style={{ color: 'var(--v0-blue)', textDecoration: 'none', fontWeight: 600 }}>support@sanwariyatech.dev</a>
            </address>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Privacy;
