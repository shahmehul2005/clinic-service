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
              By accessing and using Sanwariya Tech's software, platforms, or services, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.
            </p>
            
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. Description of Service</h2>
            <p>
              Sanwariya Tech develops AI-powered business software including appointment management systems, communication automation bots, and cloud services (collectively, the "Service"). We may update, modify, or discontinue features of the Service at our sole discretion.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. User Responsibilities & Acceptable Use</h2>
            <p>
              You are responsible for maintaining the confidentiality of your account credentials. You agree that you will not:
            </p>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li>Misuse the platform or attempt unauthorized access to our systems.</li>
              <li>Reverse engineer, decompile, or extract the source code of the software.</li>
              <li>Use the platform for any illegal, harmful, or abusive purposes.</li>
              <li>Violate any third-party terms, including WhatsApp's Business and Commerce Policies if utilizing our WhatsApp API integrations.</li>
            </ul>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. Intellectual Property</h2>
            <p>
              All software, source code, logos, branding, designs, and intellectual property associated with the Service remain the exclusive property of Sanwariya Tech. You are granted a limited, non-exclusive license to use the Service in accordance with these Terms.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>5. Service Availability & Limitation of Liability</h2>
            <p>
              We strive to maintain high availability but do not guarantee uninterrupted operation. Sanwariya Tech is provided "as is" without warranties of any kind, express or implied. We shall not be liable for any indirect damages, loss of profits, missed appointments, or operational downtime due to network failures or third-party API outages (e.g., Meta API outages).
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>6. Termination</h2>
            <p>
              We reserve the right to suspend or terminate your access to the Service at any time, with or without notice, for violations of these Terms of Service or for any other reason deemed necessary to protect our platform and users.
            </p>
            
            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>7. Contact Information</h2>
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

export default Terms;
