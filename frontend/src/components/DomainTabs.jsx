import { Stethoscope, Clock, MessageSquare, Star, FileText, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const DomainTabs = () => {
  const { t } = useTranslation();

  const features = [
    { icon: <MessageSquare size={24} />, title: 'WhatsApp Booking', desc: 'Patients book appointments 24/7 via WhatsApp — no calls, no forms.' },
    { icon: <Clock size={24} />, title: 'Token Queue System', desc: 'Issue live tokens and let patients track their position from their phone.' },
    { icon: <Star size={24} />, title: 'Google Review Requests', desc: 'Auto-send a Google review link after every completed visit.' },
    { icon: <FileText size={24} />, title: 'Digital Reports', desc: 'Send prescriptions and reports as PDFs or photos directly on WhatsApp.' },
    { icon: <Users size={24} />, title: 'Multi-staff Dashboard', desc: 'Receptionists manage the full patient queue from a clean web dashboard.' },
    { icon: <Stethoscope size={24} />, title: 'Made for Clinics', desc: 'Built specifically for doctors, hospitals, and medical facilities in India.' },
  ];

  return (
    <div style={{ padding: '5rem 1.5rem', background: 'var(--bg-card)', borderTop: '1px solid var(--border-color)' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
          <h2 style={{ fontSize: 'clamp(1.75rem, 4vw, 2.5rem)', fontWeight: 800, color: 'var(--text-main)', marginBottom: '1rem' }}>
            {t('domains.title')}
          </h2>
          <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', maxWidth: '560px', margin: '0 auto' }}>
            Everything your clinic needs to run smoothly — all in one place.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          {features.map(f => (
            <div key={f.title} className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ width: '48px', height: '48px', background: '#eff6ff', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', flexShrink: 0 }}>
                {f.icon}
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-main)', marginBottom: '0.4rem' }}>{f.title}</div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DomainTabs;
