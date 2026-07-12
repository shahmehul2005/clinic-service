import { useState } from 'react';
import { Stethoscope, GraduationCap, Building2, Briefcase } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const DomainTabs = () => {
  const [activeTab, setActiveTab] = useState('clinics');
  const { t } = useTranslation();

  const domains = [
    { id: 'clinics', label: t('domains.t1Tab'), icon: <Stethoscope size={18} /> },
    { id: 'schools', label: t('domains.t2Tab'), icon: <GraduationCap size={18} /> },
    { id: 'coachings', label: t('domains.t3Tab'), icon: <Building2 size={18} /> },
    { id: 'exporters', label: t('domains.t4Tab'), icon: <Briefcase size={18} /> }
  ];

  return (
    <div style={{ padding: '6rem 2rem', background: 'var(--bg-card)', borderTop: '1px solid var(--border-color)', borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>
            {t('domains.title')}
          </h2>
          <p style={{ fontSize: '1.125rem', color: 'var(--text-secondary)' }}>
            {t('domains.subtitle')}
          </p>
        </div>

        {/* Tabs Navigation */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '3rem' }}>
          {domains.map(domain => (
            <button
              key={domain.id}
              onClick={() => setActiveTab(domain.id)}
              style={{
                padding: '0.75rem 1.5rem',
                borderRadius: '999px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontWeight: 600,
                fontSize: '0.9rem',
                transition: 'all 0.2s ease',
                background: activeTab === domain.id ? 'var(--primary)' : '#f1f5f9',
                color: activeTab === domain.id ? 'white' : 'var(--text-secondary)',
                border: activeTab === domain.id ? '1px solid var(--primary)' : '1px solid transparent'
              }}
            >
              {domain.icon} {domain.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="card" style={{ padding: '3rem', textAlign: 'center', minHeight: '300px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
          {activeTab === 'clinics' && (
            <>
              <div style={{ width: '64px', height: '64px', background: '#eff6ff', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', marginBottom: '1.5rem' }}>
                <Stethoscope size={32} />
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>{t('domains.t1Title')}</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
                {t('domains.t1Desc')}
              </p>
            </>
          )}
          {activeTab === 'schools' && (
            <>
              <div style={{ width: '64px', height: '64px', background: '#eff6ff', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', marginBottom: '1.5rem' }}>
                <GraduationCap size={32} />
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>{t('domains.t2Title')}</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
                {t('domains.t2Desc')}
              </p>
            </>
          )}
          {activeTab === 'coachings' && (
            <>
              <div style={{ width: '64px', height: '64px', background: '#eff6ff', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', marginBottom: '1.5rem' }}>
                <Building2 size={32} />
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>{t('domains.t3Title')}</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
                {t('domains.t3Desc')}
              </p>
            </>
          )}
          {activeTab === 'exporters' && (
            <>
              <div style={{ width: '64px', height: '64px', background: '#eff6ff', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', marginBottom: '1.5rem' }}>
                <Briefcase size={32} />
              </div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>{t('domains.t4Title')}</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
                {t('domains.t4Desc')}
              </p>
            </>
          )}
        </div>

      </div>
    </div>
  );
};

export default DomainTabs;
