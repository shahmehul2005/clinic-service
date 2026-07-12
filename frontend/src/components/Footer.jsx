import { Link } from 'react-router-dom';
import { HeartPulse, Mail, Phone, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const Footer = () => {
  const { t } = useTranslation();

  return (
    <footer style={{ 
      background: 'var(--bg-page)', 
      borderTop: '1px solid var(--border-color)',
      padding: '4rem 2rem 2rem'
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '3rem',
        marginBottom: '3rem'
      }}>
        
        {/* Brand Column */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <div style={{ background: 'var(--v0-blue)', color: 'white', padding: '0.5rem', borderRadius: '8px' }}>
              <HeartPulse size={24} />
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
              Sanwariya Tech
            </div>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
            {t('footer.desc')}
          </p>
        </div>

        {/* Quick Links */}
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '1.5rem' }}>{t('footer.platform')}</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <li><Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>{t('footer.home')}</Link></li>
            <li><Link to="/login" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>{t('footer.dashboardLogin')}</Link></li>
          </ul>
        </div>

        {/* Legal Links (Required for Meta) */}
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '1.5rem' }}>{t('footer.legalTitle')}</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <li><Link to="/privacy" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>{t('footer.privacy')}</Link></li>
            <li><Link to="/terms" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>{t('footer.terms')}</Link></li>
            <li><Link to="/data-deletion" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.9rem' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>{t('footer.dataDeletion')}</Link></li>
          </ul>
        </div>

        {/* Contact Info (Required for Meta) */}
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '1.5rem' }}>Contact Us</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <li style={{ display: 'flex', gap: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem', alignItems: 'flex-start' }}>
              <Mail size={16} style={{ marginTop: '3px', flexShrink: 0, color: 'var(--v0-blue)' }} />
              <a href="mailto:support@sanwariyatech.dev" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }} onMouseOver={(e) => e.target.style.color='var(--v0-blue)'} onMouseOut={(e) => e.target.style.color='var(--text-secondary)'}>
                support@sanwariyatech.dev
              </a>
            </li>
            <li style={{ display: 'flex', gap: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem', alignItems: 'flex-start' }}>
              <Phone size={16} style={{ marginTop: '3px', flexShrink: 0, color: 'var(--v0-blue)' }} />
              <span>+1 (555) 123-4567</span>
            </li>

          </ul>
        </div>
      </div>

      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto', 
        paddingTop: '2rem', 
        borderTop: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          &copy; {new Date().getFullYear()} Sanwariya Tech. All rights reserved.
        </p>
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Verified WhatsApp Business Partner
        </div>
      </div>
    </footer>
  );
};

export default Footer;
