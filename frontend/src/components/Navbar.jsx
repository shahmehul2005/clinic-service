import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav style={{ padding: '1.5rem 0', position: 'absolute', top: 0, width: '100%', zIndex: 10 }}>
      <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.5px' }}>
          Platform<span className="text-gradient">X</span>
        </div>
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <a href="#features" style={{ color: 'hsl(var(--text-secondary))', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color = 'white'} onMouseOut={(e) => e.target.style.color = 'hsl(var(--text-secondary))'}>Features</a>
          <a href="#solutions" style={{ color: 'hsl(var(--text-secondary))', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color = 'white'} onMouseOut={(e) => e.target.style.color = 'hsl(var(--text-secondary))'}>Solutions</a>
          <a href="#pricing" style={{ color: 'hsl(var(--text-secondary))', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color = 'white'} onMouseOut={(e) => e.target.style.color = 'hsl(var(--text-secondary))'}>Pricing</a>
          <Link to="/login" className="btn btn-glass" style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}>Login</Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
