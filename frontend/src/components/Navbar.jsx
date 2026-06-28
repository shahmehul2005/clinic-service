import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav style={{ padding: '1.25rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)', position: 'sticky', top: 0, zIndex: 100 }}>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
        ClinicOS
      </div>
      
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <a href="#features" style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500 }}>Features</a>
        <a href="#pricing" style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500 }}>Pricing</a>
        <Link to="/login" className="btn btn-outline">Log In</Link>
        <button className="btn btn-primary">Book a Demo</button>
      </div>
    </nav>
  );
};

export default Navbar;
