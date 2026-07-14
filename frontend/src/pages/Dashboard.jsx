import { useAuth } from '../context/AuthContext';
import { 
  Home as HomeIcon, Calendar, Users, 
  Search, Clock, CheckCircle2, User, XCircle, LifeBuoy, HeartPulse, Trash2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import { useTranslation } from 'react-i18next';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  
  const [appointments, setAppointments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isTrialExpired, setIsTrialExpired] = useState(false);
  const [clinicName, setClinicName] = useState('Sanwariya Tech');
  const [activeTab, setActiveTab] = useState('overview');
  
  // Extract user's dynamic clinic ID, or default to mock for testing
  const clinicId = user?.user_metadata?.clinic_id || "00000000-0000-0000-0000-000000000001";
  
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newPatientName, setNewPatientName] = useState('');
  const [newPatientPhone, setNewPatientPhone] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    const fetchClinicData = async () => {
      const { data, error } = await supabase
        .from('clinics')
        .select('business_name, trial_end_date')
        .eq('id', clinicId)
        .single();
        
      if (!error && data) {
        setClinicName(data.business_name);
        if (data.trial_end_date && new Date() > new Date(data.trial_end_date)) {
          setIsTrialExpired(true);
        }
      }
    };
    
    const fetchAppointments = async () => {
      const { data, error } = await supabase
        .from('appointments')
        .select('*')
        .eq('clinic_id', clinicId)
        .order('appointment_time', { ascending: true });
        
      if (!error && data) {
        setAppointments(data);
      }
    };
    
    fetchClinicData();
    fetchAppointments();
  }, [clinicId]);

  const handleUpdateStatus = async (id, newStatus) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/appointments/${id}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.ok) {
        setAppointments(prev => prev.map(apt => apt.id === id ? { ...apt, status: newStatus } : apt));
      } else {
        const errorData = await response.json();
        alert("Failed to update status: " + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error("Status Update Error:", error);
      alert("Network error updating status. Make sure VITE_BACKEND_URL is set in Render.");
    }
  };

  const handleDeleteAppointment = async (id) => {
    if (!window.confirm("Are you sure you want to permanently delete this appointment?")) return;
    
    const { error } = await supabase
      .from('appointments')
      .delete()
      .eq('id', id);
      
    if (!error) {
      setAppointments(prev => prev.filter(apt => apt.id !== id));
    } else {
      alert("Error deleting appointment: " + error.message);
    }
  };

  const handleAddAppointment = async (e) => {
    e.preventDefault();
    setSubmitError('');
    
    const cleanPhone = newPatientPhone.replace(/\D/g, '');
    if (cleanPhone.length !== 10) {
      setSubmitError('Phone number must be exactly 10 digits.');
      return;
    }
    
    // Combine date and time into ISO string
    const appointmentDateTime = new Date(`${newDate}T${newTime}`).toISOString();
    
    // Construct payload based on updated schema
    const payload = {
      clinic_id: clinicId, // Dynamically use the logged in user's clinic ID
      phone_number: cleanPhone,
      patient_name: newPatientName,
      appointment_time: appointmentDateTime,
      status: 'booked'
    };
    
    const { data, error } = await supabase
      .from('appointments')
      .insert([payload])
      .select();
      
    if (error) {
      if (error.code === '23505') { // Postgres Unique Constraint Violation
        setSubmitError("Slot already booked! Please select a different time.");
      } else {
        setSubmitError(error.message);
      }
    } else if (data) {
      // Success
      setAppointments(prev => [...prev, data[0]].sort((a, b) => new Date(a.appointment_time) - new Date(b.appointment_time)));
      setIsModalOpen(false);
      setNewPatientName('');
      setNewPatientPhone('');
      setNewDate('');
      setNewTime('');
    }
  };

  const filteredAppointments = appointments.filter(apt => 
    apt.patient_name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    apt.phone_number?.includes(searchQuery)
  );

  const todayAppointments = filteredAppointments.filter(apt => {
    const aptDate = new Date(apt.appointment_time).toLocaleDateString();
    const today = new Date().toLocaleDateString();
    return aptDate === today;
  });

  const upcomingAppointments = filteredAppointments.filter(apt => {
    const aptDate = new Date(apt.appointment_time).toLocaleDateString();
    const today = new Date().toLocaleDateString();
    return aptDate !== today && new Date(apt.appointment_time) > new Date();
  });

  const uniquePatients = useMemo(() => {
    const map = new Map();
    appointments.forEach(apt => {
      if (!map.has(apt.phone_number)) {
        map.set(apt.phone_number, {
          name: apt.patient_name || 'Unknown',
          phone: apt.phone_number,
          visits: 1,
          lastVisit: apt.appointment_time
        });
      } else {
        const p = map.get(apt.phone_number);
        p.visits += 1;
        if (new Date(apt.appointment_time) > new Date(p.lastVisit)) {
          p.lastVisit = apt.appointment_time;
        }
      }
    });
    // Filter by search query if in patients tab
    return Array.from(map.values()).filter(p => 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
      p.phone.includes(searchQuery)
    ).sort((a, b) => new Date(b.lastVisit) - new Date(a.lastVisit));
  }, [appointments, searchQuery]);

  const getReason = (idx) => {
    const reasons = ["Annual check-up", "Follow-up visit", "Lab results", "Knee pain consult", "Prescription refill", "Skin check"];
    return reasons[idx % reasons.length];
  };

  const renderBadge = (status) => {
    if (status === 'booked') return <span className="badge badge-waiting"><Clock size={14}/> {t('dashboard.badgeWaiting')}</span>;
    if (status === 'arrived') return <span className="badge badge-checked-in"><CheckCircle2 size={14}/> {t('dashboard.badgeCheckedIn')}</span>;
    if (status === 'completed') return <span className="badge badge-seen"><CheckCircle2 size={14}/> {t('dashboard.badgeSeen')}</span>;
    if (status === 'cancelled') return <span className="badge badge-cancelled"><XCircle size={14}/> {t('dashboard.badgeCancelled')}</span>;
    return <span className="badge badge-waiting"><Clock size={14}/> {status}</span>;
  };

  // Stats calculation
  const stats = {
    waiting: appointments.filter(a => a.status === 'booked').length,
    checkedIn: appointments.filter(a => a.status === 'arrived').length,
    seen: appointments.filter(a => a.status === 'completed').length,
    total: appointments.length
  };

  if (isTrialExpired) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page)', padding: '1rem' }}>
        <div className="card" style={{ width: '100%', maxWidth: '500px', padding: '3rem', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', background: 'var(--v0-red-light)', color: 'var(--v0-red)', padding: '1rem', borderRadius: '50%', marginBottom: '1.5rem' }}>
            <Clock size={40} />
          </div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '1rem' }}>
            Trial Expired
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: 1.6, marginBottom: '2rem' }}>
            Your 7-day free trial of Sanwariya Tech has ended. To continue using the AI receptionist and managing your patients, please contact sales to upgrade to a paid plan.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button onClick={logout} className="btn-v0-outline" style={{ padding: '0.75rem 1.5rem', borderRadius: '8px' }}>
              Logout
            </button>
            <a href="mailto:support@sanwariyatech.dev" className="btn-v0-primary" style={{ padding: '0.75rem 1.5rem', borderRadius: '8px', textDecoration: 'none' }}>
              Contact Sales
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-page)', position: 'relative' }}>
      {/* Sidebar */}
      <aside style={{ width: '280px', padding: '1.5rem', display: 'flex', flexDirection: 'column', background: 'white', borderRight: '1px solid var(--border-color)' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem' }}>
          <div style={{ background: 'var(--v0-blue)', color: 'white', padding: '0.5rem', borderRadius: '8px' }}>
            <HeartPulse size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{clinicName}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{t('dashboard.poweredBy')}</div>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flexGrow: 1 }}>
          <div onClick={() => setActiveTab('overview')} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', background: activeTab === 'overview' ? 'var(--v0-blue)' : 'transparent', color: activeTab === 'overview' ? 'white' : 'var(--text-secondary)', cursor: 'pointer' }}>
            <HomeIcon size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: activeTab === 'overview' ? 'white' : 'var(--text-main)', lineHeight: 1.2 }}>{t('dashboard.overview')}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>{t('dashboard.overviewDesc')}</div>
            </div>
          </div>
          <div onClick={() => setActiveTab('upcoming')} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', background: activeTab === 'upcoming' ? 'var(--v0-blue)' : 'transparent', color: activeTab === 'upcoming' ? 'white' : 'var(--text-secondary)', cursor: 'pointer' }}>
            <Calendar size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: activeTab === 'upcoming' ? 'white' : 'var(--text-main)', lineHeight: 1.2 }}>{t('dashboard.appointments')}</div>
              <div style={{ fontSize: '0.75rem', opacity: activeTab === 'upcoming' ? 0.9 : 1 }}>Upcoming Schedules</div>
            </div>
          </div>
          <div onClick={() => setActiveTab('patients')} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', background: activeTab === 'patients' ? 'var(--v0-blue)' : 'transparent', color: activeTab === 'patients' ? 'white' : 'var(--text-secondary)', cursor: 'pointer' }}>
            <Users size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: activeTab === 'patients' ? 'white' : 'var(--text-main)', lineHeight: 1.2 }}>{t('dashboard.patients')}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>{t('dashboard.patientsDesc')}</div>
            </div>
          </div>
        </nav>

        {/* Support Box */}
        <div style={{ background: '#f0f9ff', borderRadius: '12px', padding: '1.25rem', marginTop: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.9rem' }}>
            <LifeBuoy size={18} /> {t('dashboard.supportLabel')}
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {t('dashboard.supportDesc1')} <strong style={{ color: 'var(--text-main)' }}>{t('dashboard.supportDesc2')}</strong>.
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flexGrow: 1, padding: '2.5rem', overflowY: 'auto' }}>
        
        {/* Header */}
        <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--v0-blue)', fontWeight: 500, fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              <Calendar size={18} /> {new Date().toLocaleDateString(i18n.language === 'hi' ? 'hi-IN' : 'en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
            </div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
              {t('dashboard.goodMorning')}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginTop: '0.25rem' }}>
              {t('dashboard.goodMorningSub')}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button onClick={() => i18n.changeLanguage(i18n.language === 'en' ? 'hi' : 'en')} className="btn-v0-outline" style={{ padding: '0.75rem 1.5rem', fontSize: '1rem', borderRadius: '8px' }}>
              {i18n.language === 'en' ? 'हिंदी' : 'English'}
            </button>
            <button onClick={() => setIsModalOpen(true)} className="btn-primary" style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}>
              {t('dashboard.newAppointmentBtn')}
            </button>
          </div>
        </header>

        {activeTab === 'overview' ? (
          <>
            {/* Stat Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
              <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.75rem', borderRadius: '50%' }}>
                  <Clock size={24} />
                </div>
                <div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.waiting}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('dashboard.statWaiting')}</div>
                </div>
              </div>
              <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.75rem', borderRadius: '50%' }}>
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.checkedIn}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('dashboard.statCheckedIn')}</div>
                </div>
              </div>
              <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{ color: 'var(--text-main)', padding: '0.75rem', borderRadius: '50%', border: '1px solid var(--border-color)' }}>
                  <CheckCircle2 size={24} />
                </div>
                <div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.seen}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('dashboard.statSeen')}</div>
                </div>
              </div>
              <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{ background: '#f1f5f9', color: 'var(--text-main)', padding: '0.75rem', borderRadius: '50%' }}>
                  <Users size={24} />
                </div>
                <div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.total}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{t('dashboard.statTotal')}</div>
                </div>
              </div>
            </div>

            {/* Data Table Area */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>{t('dashboard.liveQueue')}</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('dashboard.liveQueueSub')}</p>
              </div>
              <div style={{ position: 'relative', width: '300px' }}>
                <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input 
                  type="text" 
                  placeholder={t('dashboard.searchPh')} 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input" 
                  style={{ paddingLeft: '2.5rem', borderRadius: '999px' }} 
                />
              </div>
            </div>

            <div className="card" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f0f9ff', borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thName')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thPhone')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thTime')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thStatus')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>{t('dashboard.thActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAppointments.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No appointments today.</td>
                    </tr>
                  ) : (
                    todayAppointments.map((apt, index) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.5rem', borderRadius: '50%' }}>
                            <User size={20} />
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>{apt.patient_name || 'Unknown'}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{getReason(index)}</div>
                          </div>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 500 }}>{apt.phone_number}</td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 600 }}>{new Date(apt.appointment_time).toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'})}</td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          {renderBadge(apt.status)}
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center', height: '76px' }}>
                          {apt.status === 'booked' && (
                            <button onClick={() => handleUpdateStatus(apt.id, 'arrived')} className="btn-action btn-v0-primary">
                              <CheckCircle2 size={16} /> {t('dashboard.actionArrived')}
                            </button>
                          )}
                          {(apt.status === 'booked' || apt.status === 'arrived') && (
                            <button onClick={() => handleUpdateStatus(apt.id, 'completed')} className="btn-action btn-v0-outline">
                              <CheckCircle2 size={16} /> {t('dashboard.actionComplete')}
                            </button>
                          )}
                          {apt.status !== 'completed' && apt.status !== 'cancelled' && (
                            <button onClick={() => handleUpdateStatus(apt.id, 'cancelled')} className="btn-action btn-v0-danger">
                              <XCircle size={16} /> {t('dashboard.actionCancel')}
                            </button>
                          )}
                          {(apt.status === 'completed' || apt.status === 'cancelled') && (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{t('dashboard.actionNone')}</span>
                          )}
                          
                          {/* Delete Icon */}
                          <button onClick={() => handleDeleteAppointment(apt.id)} style={{ padding: '0.5rem', marginLeft: '0.5rem', color: 'var(--text-secondary)' }} title="Delete Record">
                            <Trash2 size={16} style={{ cursor: 'pointer' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--v0-red)'} onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : activeTab === 'upcoming' ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>Upcoming Appointments</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Schedules for tomorrow and beyond</p>
              </div>
              <div style={{ position: 'relative', width: '300px' }}>
                <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input 
                  type="text" 
                  placeholder={t('dashboard.searchPh')} 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input" 
                  style={{ paddingLeft: '2.5rem', borderRadius: '999px' }} 
                />
              </div>
            </div>

            <div className="card" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f0f9ff', borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Date</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thName')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thPhone')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thTime')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thStatus')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>{t('dashboard.thActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {upcomingAppointments.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No upcoming appointments.</td>
                    </tr>
                  ) : (
                    upcomingAppointments.map((apt, index) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 600 }}>
                          {new Date(apt.appointment_time).toLocaleDateString([], {month: 'short', day: 'numeric'})}
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>{apt.patient_name || 'Unknown'}</div>
                          </div>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 500 }}>{apt.phone_number}</td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 600 }}>{new Date(apt.appointment_time).toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'})}</td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          {renderBadge(apt.status)}
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center', height: '76px' }}>
                          {apt.status !== 'completed' && apt.status !== 'cancelled' && (
                            <button onClick={() => handleUpdateStatus(apt.id, 'cancelled')} className="btn-action btn-v0-danger">
                              <XCircle size={16} /> {t('dashboard.actionCancel')}
                            </button>
                          )}
                          <button onClick={() => handleDeleteAppointment(apt.id)} style={{ padding: '0.5rem', marginLeft: '0.5rem', color: 'var(--text-secondary)' }} title="Delete Record">
                            <Trash2 size={16} style={{ cursor: 'pointer' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--v0-red)'} onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'} />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <>
            {/* Patients Tab View */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>{t('dashboard.patientsViewTitle')}</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('dashboard.patientsViewSub')}</p>
              </div>
              <div style={{ position: 'relative', width: '300px' }}>
                <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                <input 
                  type="text" 
                  placeholder={t('dashboard.searchPh')} 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input" 
                  style={{ paddingLeft: '2.5rem', borderRadius: '999px' }} 
                />
              </div>
            </div>

            <div className="card" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f0f9ff', borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thName')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thPhone')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thTotalVisits')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thLastVisit')}</th>
                  </tr>
                </thead>
                <tbody>
                  {uniquePatients.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('dashboard.noPatients')}</td>
                    </tr>
                  ) : (
                    uniquePatients.map((apt, index) => (
                      <tr key={apt.phone} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.5rem', borderRadius: '50%' }}>
                            <User size={20} />
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>{apt.name}</div>
                          </div>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 500 }}>{apt.phone}</td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 500 }}>
                          <span style={{ background: '#f1f5f9', padding: '0.25rem 0.75rem', borderRadius: '1rem', fontSize: '0.8rem', fontWeight: 600 }}>{apt.visits}</span>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 500 }}>{new Date(apt.lastVisit).toLocaleDateString()}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>

      {/* Add Appointment Modal */}
      {isModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '100%', maxWidth: '400px', padding: '2rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1.5rem' }}>{t('dashboard.modalAddTitle')}</h2>
            
            {submitError && (
              <div style={{ padding: '0.75rem', background: 'var(--v0-red-light)', color: 'var(--v0-red)', borderRadius: '6px', fontSize: '0.875rem', marginBottom: '1rem', border: '1px solid #fecaca' }}>
                {submitError}
              </div>
            )}

            <form onSubmit={handleAddAppointment} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalName')}</label>
                <input type="text" required className="form-input" value={newPatientName} onChange={(e) => setNewPatientName(e.target.value)} placeholder="John Doe" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalPhone')}</label>
                <input 
                  type="text" 
                  required 
                  className="form-input" 
                  value={newPatientPhone} 
                  onChange={(e) => setNewPatientPhone(e.target.value.replace(/\D/g, '').slice(0, 10))} 
                  placeholder="10-digit phone number (e.g. 5551234567)" 
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalDate')}</label>
                <input type="date" required className="form-input" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalTime')}</label>
                <input type="time" required className="form-input" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              </div>
              
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-v0-outline" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px' }}>{t('dashboard.modalBtnCancel')}</button>
                <button type="submit" className="btn-v0-primary" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px', border: 'none' }}>{t('dashboard.modalBtnBook')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
