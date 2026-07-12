import { Shield, Zap, Globe, MessageCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const Features = () => {
  const { t } = useTranslation();

  const features = [
    {
      icon: <MessageCircle size={24} style={{ color: 'var(--primary)' }} />,
      title: t('features.f1Title'),
      description: t('features.f1Desc')
    },
    {
      icon: <Zap size={24} style={{ color: 'var(--primary)' }} />,
      title: t('features.f2Title'),
      description: t('features.f2Desc')
    },
    {
      icon: <Shield size={24} style={{ color: 'var(--primary)' }} />,
      title: t('features.f3Title'),
      description: t('features.f3Desc')
    },
    {
      icon: <Globe size={24} style={{ color: 'var(--primary)' }} />,
      title: t('features.f4Title'),
      description: t('features.f4Desc')
    }
  ];

  return (
    <div id="features" style={{ padding: '6rem 2rem', background: 'var(--bg-page)' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>
            {t('features.title')}
          </h2>
          <p style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
            {t('features.subtitle')}
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
          {features.map((feature, index) => (
            <div key={index} className="card" style={{ padding: '2rem' }}>
              <div style={{ width: '48px', height: '48px', background: '#eff6ff', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem' }}>
                {feature.icon}
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.75rem' }}>
                {feature.title}
              </h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {feature.description}
              </p>
            </div>
          ))}
        </div>
        
      </div>
    </div>
  );
};

export default Features;
