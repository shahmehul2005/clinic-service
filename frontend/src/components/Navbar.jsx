import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const Navbar = () => {
  const { t, i18n } = useTranslation();

  const changeLanguage = (e) => {
    i18n.changeLanguage(e.target.value);
  };

  return (
    <nav style={{ padding: '1.25rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)', position: 'sticky', top: 0, zIndex: 100 }}>
      <Link to="/" style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.5px', textDecoration: 'none' }}>
        Sanwariya Tech
      </Link>
      
      <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
        <select 
          onChange={changeLanguage} 
          defaultValue={i18n.language}
          style={{ 
            padding: '0.4rem 0.8rem', 
            borderRadius: '6px', 
            border: '1px solid var(--border-color)', 
            background: 'var(--bg-page)', 
            color: 'var(--text-main)',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          <option value="en">English</option>
          <option value="hi">हिंदी</option>
        </select>
        
        <a href="/#features" style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500 }}>Features</a>
        <a href="/#pricing" style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500 }}>Pricing</a>
        <Link to="/login" className="btn btn-outline">{t('navbar.login')}</Link>
        <Link to="/demo" className="btn btn-primary" style={{ textDecoration: 'none' }}>{t('navbar.bookDemo')}</Link>
      </div>
    </nav>
  );
};

export default Navbar;
