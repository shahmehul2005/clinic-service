import { ArrowRight } from 'lucide-react';

const Hero = () => {
  return (
    <section className="container" style={{ paddingTop: '8rem', paddingBottom: '4rem', textAlign: 'center' }}>
      <div className="animate-fade-in opacity-0" style={{ animationDelay: '0.1s' }}>
        <h1 style={{ fontSize: '3.5rem', marginBottom: '1.5rem', fontWeight: 800 }}>
          The Ultimate Platform for <br/>
          <span className="text-gradient">Every Business Domain</span>
        </h1>
        <p style={{ fontSize: '1.25rem', color: 'hsl(var(--text-secondary))', maxWidth: '600px', margin: '0 auto 2.5rem', lineHeight: 1.6 }}>
          Whether you run a Clinic, a School, a Coaching Institute, or an Export Business, we have tailored tools to help you scale effortlessly.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button className="btn btn-primary hover-lift">
            Get Started
            <ArrowRight size={20} style={{ marginLeft: '0.5rem' }} />
          </button>
          <button className="btn btn-glass hover-lift">
            View Live Demo
          </button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
