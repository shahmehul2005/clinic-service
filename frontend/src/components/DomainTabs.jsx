import { useState } from 'react';

const DomainTabs = () => {
  const [activeTab, setActiveTab] = useState('clinic');

  const tabs = [
    { id: 'clinic', label: 'For Clinics' },
    { id: 'school', label: 'For Schools' },
    { id: 'coaching', label: 'For Coaching' },
    { id: 'exporter', label: 'For Exporters' }
  ];

  const content = {
    clinic: {
      title: 'Revolutionize Patient Care',
      desc: 'Our clinic management system provides end-to-end automation. From appointment scheduling to electronic health records (EHR) and billing.'
    },
    school: {
      title: 'Empower Next-Gen Learning',
      desc: 'A complete ERP for schools. Manage admissions, fee collection, attendance, and parent-teacher communication in one dashboard.'
    },
    coaching: {
      title: 'Scale Your Institute',
      desc: 'Deliver online classes, distribute DRM-protected study materials, and conduct AI-proctored mock tests.'
    },
    exporter: {
      title: 'Global Trade Made Easy',
      desc: 'Handle complex export documentation, track shipments in real-time, and manage multi-currency finances without the headache.'
    }
  };

  return (
    <section id="solutions" className="container" style={{ padding: '4rem 1.5rem', marginBottom: '4rem' }}>
      <div className="glass" style={{ padding: '1rem', borderRadius: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', overflowX: 'auto', paddingBottom: '1rem', borderBottom: '1px solid var(--glass-border)' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? 'rgba(255,255,255,0.1)' : 'transparent',
                color: activeTab === tab.id ? 'white' : 'hsl(var(--text-secondary))',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
                transition: 'all 0.2s',
                whiteSpace: 'nowrap'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        
        <div style={{ padding: '3rem 2rem', minHeight: '250px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <h3 style={{ fontSize: '2rem', marginBottom: '1rem', color: 'white' }}>
            {content[activeTab].title}
          </h3>
          <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '1.1rem', maxWidth: '800px', lineHeight: 1.6 }}>
            {content[activeTab].desc}
          </p>
          <div style={{ marginTop: '2rem' }}>
            <button className="btn btn-primary hover-lift">Learn More</button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DomainTabs;
