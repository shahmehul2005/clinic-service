import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import Features from '../components/Features';
import DomainTabs from '../components/DomainTabs';
import Footer from '../components/Footer';

const Home = () => {
  return (
    <div style={{ position: 'relative', minHeight: '100vh' }}>
      {/* Background decorations */}
      <div style={{ position: 'absolute', top: '-10%', left: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, hsla(var(--accent), 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: -1 }} />
      <div style={{ position: 'absolute', top: '20%', right: '-5%', width: '30%', height: '30%', background: 'radial-gradient(circle, hsla(38, 100%, 50%, 0.1) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: -1 }} />
      
      <Navbar />
      <main>
        <Hero />
        <Features />
        <DomainTabs />
      </main>
      
      <Footer />
    </div>
  );
};

export default Home;
