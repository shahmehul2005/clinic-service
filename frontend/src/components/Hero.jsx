import { ArrowRight, MessageSquare, Calendar } from 'lucide-react';
import { Link } from 'react-router-dom';

const Hero = () => {
  return (
    <div style={{ padding: '6rem 2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', background: 'var(--bg-card)' }}>
      
      <div style={{ background: '#eff6ff', color: 'var(--primary)', padding: '0.5rem 1rem', borderRadius: '999px', fontSize: '0.875rem', fontWeight: 600, marginBottom: '1.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
        <MessageSquare size={16} /> Now with WhatsApp AI Integration
      </div>
      
      <h1 style={{ fontSize: '3.5rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-1px', maxWidth: '800px', lineHeight: 1.1, marginBottom: '1.5rem' }}>
        The Operating System for Modern Local Clinics
      </h1>
      
      <p style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', maxWidth: '600px', marginBottom: '2.5rem' }}>
        Automate your front desk with a Hinglish-speaking AI receptionist that books appointments directly into your secure management dashboard.
      </p>
      
      <div style={{ display: 'flex', gap: '1rem' }}>
        <button className="btn btn-primary" style={{ padding: '0.875rem 1.5rem', fontSize: '1rem' }}>
          Get Started Free <ArrowRight size={18} style={{ marginLeft: '0.5rem' }} />
        </button>
        <Link to="/login" className="btn btn-outline" style={{ padding: '0.875rem 1.5rem', fontSize: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
          <Calendar size={18} /> View Dashboard
        </Link>
      </div>

      <div style={{ marginTop: '4rem', width: '100%', maxWidth: '1000px', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1rem', background: '#f8fafc', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)' }}>
        {/* Mockup of the dashboard interface */}
        <div style={{ background: 'white', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ background: '#f1f5f9', padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', gap: '0.5rem' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444' }}></div>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b' }}></div>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981' }}></div>
          </div>
          <div style={{ padding: '2rem', display: 'flex', gap: '2rem', textAlign: 'left' }}>
             <div style={{ width: '200px', background: '#f8fafc', borderRadius: '6px', padding: '1rem' }}>
                <div style={{ height: '20px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '1rem', width: '60%' }}></div>
                <div style={{ height: '16px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '0.5rem' }}></div>
                <div style={{ height: '16px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '0.5rem' }}></div>
             </div>
             <div style={{ flex: 1 }}>
                <div style={{ height: '24px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '1.5rem', width: '40%' }}></div>
                <div style={{ height: '40px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '0.5rem' }}></div>
                <div style={{ height: '40px', background: '#e2e8f0', borderRadius: '4px', marginBottom: '0.5rem' }}></div>
                <div style={{ height: '40px', background: '#e2e8f0', borderRadius: '4px' }}></div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hero;
