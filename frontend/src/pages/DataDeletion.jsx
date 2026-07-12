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
              If you have interacted with our WhatsApp Business agent to book clinic appointments, you have the right to request the complete deletion of your data from our systems.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>1. What Data Can Be Deleted?</h2>
            <p>
              When you request data deletion, we will permanently erase the following from our secure PostgreSQL database:
            </p>
            <ul style={{ listStyleType: 'disc', paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li>Your phone number.</li>
              <li>Your WhatsApp Meta IDs associated with your messages.</li>
              <li>Your past and upcoming clinic appointment history.</li>
            </ul>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>2. How to Request Data Deletion</h2>
            <p>
              To initiate a data deletion request, you must email our support team. Please follow these steps:
            </p>
            <ol style={{ paddingLeft: '1.5rem', marginBottom: '1rem' }}>
              <li>Send an email to <strong>support@sanwariyatech.dev</strong>.</li>
              <li>Use the subject line: <strong>"Data Deletion Request"</strong>.</li>
              <li>In the body of the email, clearly state the phone number you used to interact with our WhatsApp service so we can locate your records.</li>
            </ol>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>3. Processing Time</h2>
            <p>
              Once we receive your request, our team will process the deletion of your data within <strong>7 business days</strong>. You will receive a confirmation email once your data has been completely erased from our servers.
            </p>

            <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '2rem', marginBottom: '1rem', color: 'var(--v0-blue)' }}>4. Important Note Regarding WhatsApp</h2>
            <p>
              While we delete your data from the Sanwariya Tech database, your chat history on your personal device remains in your WhatsApp application. To remove the chat entirely, you must delete the conversation directly within your WhatsApp app.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default DataDeletion;
