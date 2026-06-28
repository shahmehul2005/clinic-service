import { Activity, BookOpen, Globe2, Lightbulb } from 'lucide-react';

const Features = () => {
  const features = [
    {
      icon: <Activity size={32} style={{ color: '#f472b6' }} />,
      title: 'Healthcare & Clinics',
      description: 'Manage patient records, appointments, and billing with our HIPAA-compliant modules.'
    },
    {
      icon: <BookOpen size={32} style={{ color: '#a78bfa' }} />,
      title: 'Schools & Education',
      description: 'Streamline admissions, track student performance, and connect with parents seamlessly.'
    },
    {
      icon: <Lightbulb size={32} style={{ color: '#38bdf8' }} />,
      title: 'Coaching Institutes',
      description: 'Host live classes, distribute study materials, and conduct online assessments.'
    },
    {
      icon: <Globe2 size={32} style={{ color: '#34d399' }} />,
      title: 'Exporters & Trade',
      description: 'Track international shipments, manage inventory, and handle multi-currency invoices.'
    }
  ];

  return (
    <section id="features" className="container" style={{ padding: '6rem 1.5rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Tailored for <span className="text-gradient">Your Industry</span></h2>
        <p style={{ color: 'hsl(var(--text-secondary))', maxWidth: '600px', margin: '0 auto' }}>
          Our platform adapts to your specific business needs, providing specialized tools right out of the box.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
        {features.map((feat, index) => (
          <div key={index} className="glass hover-lift" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.05)', width: '60px', height: '60px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {feat.icon}
            </div>
            <h3 style={{ fontSize: '1.25rem' }}>{feat.title}</h3>
            <p style={{ color: 'hsl(var(--text-secondary))', lineHeight: 1.6 }}>{feat.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default Features;
