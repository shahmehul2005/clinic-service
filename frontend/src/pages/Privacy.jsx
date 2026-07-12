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
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>1. Information We Collect</h2>
            <p>
              When you interact with Sanwariya Tech via our website, WhatsApp Business integration, or our cloud platform, we may collect the following information:
              personal identification information (Name, Phone Number, WhatsApp Meta IDs) and appointment booking history.
            </p>
            
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. How We Use Your Data</h2>
            <p>
              The data collected is strictly used for facilitating medical appointments, sending automated WhatsApp reminders, providing real-time dashboard updates for clinic receptionists, and improving our software services. We do not sell your personal data to third parties.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. WhatsApp Messaging Data</h2>
            <p>
              By initiating a conversation with our WhatsApp Business Number, you consent to receive automated and manual replies regarding your clinic appointments. Meta (WhatsApp's parent company) also processes the delivery of these messages according to their own Privacy Policy. We store a log of appointment statuses exclusively on our secure PostgreSQL database.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. Security</h2>
            <p>
              We implement a variety of security measures to maintain the safety of your personal information, including HMAC SHA-256 signature validation for all incoming WhatsApp webhooks and Row Level Security on our databases.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>5. Contact Information</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at: <strong>support@sanwariyatech.dev</strong>.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Privacy;
