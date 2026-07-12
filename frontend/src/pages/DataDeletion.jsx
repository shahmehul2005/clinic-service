import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { Trash2 } from 'lucide-react';

const DataDeletion = () => {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      
      <main style={{ flexGrow: 1, padding: '4rem 2rem' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto', background: 'white', padding: '3rem', borderRadius: '16px', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
            <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '1rem', borderRadius: '12px' }}>
              <Trash2 size={32} />
            </div>
            <div>
              <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px', margin: 0 }}>Data Deletion Policy</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', margin: '0.5rem 0 0' }}>Instructions for managing your data</p>
            </div>
          </div>
          
          <div className="legal-content" style={{ color: 'var(--text-main)', lineHeight: 1.8, fontSize: '1rem' }}>
            <p>
              At Sanwariya Tech, we respect your privacy and give you full control over your personal data. 
              If you have interacted with any of our software solutions, including our WhatsApp Business agents, you have the right to request the complete deletion of your data from our systems.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>1. What Data Can Be Deleted?</h2>
            <p>
              When you request data deletion, we will permanently erase your personal data from our secure databases. Depending on the service you used, this may include:
            </p>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li>Your phone number and contact details.</li>
              <li>Your WhatsApp Meta IDs associated with your messages.</li>
              <li>Your interaction history and service usage logs (such as appointment bookings).</li>
            </ul>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. How to Request Data Deletion</h2>
            <p>
              To initiate a data deletion request, you must email our support team. Please format your email exactly as follows:
            </p>
            
            <div style={{ background: 'var(--bg-page)', padding: '1.5rem', borderRadius: '8px', margin: '1rem 0', borderLeft: '4px solid var(--v0-blue)' }}>
              <p style={{ margin: 0 }}><strong>Contact us at:</strong></p>
              <p style={{ marginBottom: '1rem' }}><a href="mailto:support@sanwariyatech.dev" style={{ color: 'var(--v0-blue)', textDecoration: 'none', fontWeight: 600 }}>support@sanwariyatech.dev</a></p>
              
              <p style={{ margin: 0 }}><strong>Subject:</strong></p>
              <p style={{ marginBottom: '1rem' }}>Data Deletion Request</p>
              
              <p style={{ margin: 0 }}><strong>Body (include your associated identifier):</strong></p>
              <p style={{ margin: 0 }}>Phone Number: +91XXXXXXXXXX (or relevant email/ID)</p>
            </div>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. Processing Time</h2>
            <p>
              Once we receive your request, our team will process the complete deletion of your data within <strong>7 business days</strong>. You will receive a confirmation email once your data has been erased from our servers.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. Important Note Regarding Third-Party Platforms</h2>
            <p>
              While we delete your data from Sanwariya Tech's databases, your chat history on platforms like WhatsApp remains on your personal device and Meta's servers according to their retention policies. To remove the chat entirely from your end, you must delete the conversation directly within your WhatsApp application.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default DataDeletion;
