import { Shield, Zap, Globe, MessageCircle } from 'lucide-react';

const Features = () => {
  const features = [
    {
      icon: <MessageCircle size={24} style={{ color: 'var(--primary)' }} />,
      title: 'WhatsApp AI Agent',
      description: 'Your patient can text your clinic 24/7. Our Hinglish AI understands them naturally and books slots automatically.'
    },
    {
      icon: <Zap size={24} style={{ color: 'var(--primary)' }} />,
      title: 'Real-Time Sync',
      description: 'The moment an appointment is booked on WhatsApp, it appears instantly on the receptionist dashboard.'
    },
    {
      icon: <Shield size={24} style={{ color: 'var(--primary)' }} />,
      title: 'Double-Booking Protection',
      description: 'Built on PostgreSQL with strict unique constraints. Two patients can never book the same slot at the exact same time.'
    },
    {
      icon: <Globe size={24} style={{ color: 'var(--primary)' }} />,
      title: 'Cloud Dashboard',
      description: 'Access your clinic queue from anywhere. Simple, flat, and extremely fast web interface built for speed.'
    }
  ];

  return (
    <div id="features" style={{ padding: '6rem 2rem', background: 'var(--bg-page)' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>
            Built for Local Businesses
          </h2>
          <p style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto' }}>
            Everything you need to automate your front desk and manage your queue without any technical expertise.
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
