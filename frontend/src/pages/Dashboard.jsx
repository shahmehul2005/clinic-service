import { useAuth } from '../context/AuthContext';
import { 
  Home as HomeIcon, Calendar, Users, 
  Search, Clock, CheckCircle2, User, XCircle, LifeBuoy, HeartPulse, Trash2,
  FileText, Star, Settings, Plus, Minus, Send
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import { useTranslation } from 'react-i18next';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/login');
  };
  
  const [appointments, setAppointments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isTrialExpired, setIsTrialExpired] = useState(false);
  const [clinicName, setClinicName] = useState('Sanwariya Tech');
  const [bookingMode, setBookingMode] = useState('scheduled');
  const [currentServingToken, setCurrentServingToken] = useState(0);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Report modal state
  const [reportModal, setReportModal] = useState(null);
  const [reportForm, setReportForm] = useState({
    patient_age: '', chief_complaint: '', diagnosis: '',
    followup_date: '', special_notes: '',
    medicines: [{ name: '', dosage: '', frequency: '', duration: '' }]
  });
  const [reportImageFile, setReportImageFile] = useState(null);
  const [reportSending, setReportSending] = useState(false);
  const [toast, setToast] = useState(null);

  // Settings state
  const [settings, setSettings] = useState({ google_review_link: '', doctor_name: '', clinic_address: '', consultation_fee: '', maps_link: '', clinic_phone: '' });
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  
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
        .select('business_name, trial_end_date, booking_mode, current_serving_token, google_review_link, doctor_name, clinic_address, consultation_fee, maps_link, clinic_phone')
        .eq('id', clinicId)
        .single();
        
      if (!error && data) {
        setClinicName(data.business_name);
        setBookingMode(data.booking_mode || 'scheduled');
        setCurrentServingToken(data.current_serving_token || 0);
        if (data.trial_end_date && new Date() > new Date(data.trial_end_date)) {
          setIsTrialExpired(true);
        }
        setSettings({
          google_review_link: data.google_review_link || '',
          doctor_name: data.doctor_name || '',
          clinic_address: data.clinic_address || '',
          consultation_fee: data.consultation_fee || '',
          maps_link: data.maps_link || '',
          clinic_phone: data.clinic_phone || '',
        });
        setSettingsLoaded(true);
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

    const channel = supabase
      .channel('custom-all-channel')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'appointments', filter: `clinic_id=eq.${clinicId}` }, (payload) => {
        fetchAppointments();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
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

  const handleCallNext = async () => {
    if (bookingMode === 'token' && todayAppointments.length === 0) {
      alert("No patients waiting in the live queue!");
      return;
    }
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/queue/call-next`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clinic_id: clinicId, current_token: currentServingToken })
    });
    
    if (response.ok) {
      setCurrentServingToken(currentServingToken + 1);
      setAppointments(prev => prev.map(apt => {
        if (apt.token_number === currentServingToken && new Date(apt.appointment_time).toLocaleDateString() === new Date().toLocaleDateString()) {
          return { ...apt, status: 'completed' };
        }
        return apt;
      }));
    } else {
      alert("Failed to update token counter and notify patients.");
    }
  };

  const handleCancelToken = async (aptId) => {
    if (!window.confirm("Are you sure you want to cancel this patient's token?")) return;
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/queue/cancel-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clinic_id: clinicId, appointment_id: aptId })
    });
    
    if (response.ok) {
      setAppointments(prev => prev.map(apt => apt.id === aptId ? { ...apt, status: 'cancelled' } : apt));
    } else {
      alert("Failed to cancel token and notify patient.");
    }
  };

  const handleCloseDay = async () => {
    if (!window.confirm("Are you sure you want to close the clinic for today? This will cancel all remaining appointments for today!")) return;
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/queue/close-day`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clinic_id: clinicId })
    });
    
    if (response.ok) {
      showToast("Clinic closed for today. Remaining appointments cancelled.", "success");
      if (window._fetchAppointments) window._fetchAppointments();
    } else {
      showToast("Failed to close clinic for today.", "error");
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
    
    let payload = {};
    if (bookingMode === 'token') {
      const today = new Date().toLocaleDateString();
      const todaysApts = appointments.filter(a => new Date(a.appointment_time).toLocaleDateString() === today);
      const maxToken = todaysApts.reduce((max, apt) => Math.max(max, apt.token_number || 0), 0);
      
      payload = {
        clinic_id: clinicId,
        phone_number: cleanPhone,
        patient_name: newPatientName,
        appointment_time: new Date().toISOString(),
        status: 'booked',
        token_number: maxToken + 1
      };
    } else {
      const appointmentDateTime = new Date(`${newDate}T${newTime}`).toISOString();
      payload = {
        clinic_id: clinicId,
        phone_number: cleanPhone,
        patient_name: newPatientName,
        appointment_time: appointmentDateTime,
        status: 'booked'
      };
    }
    
    const { data, error } = await supabase
      .from('appointments')
      .insert([payload])
      .select();
      
    if (error) {
      if (error.code === '23505') {
        setSubmitError("Slot already booked! Please select a different time.");
      } else {
        setSubmitError(error.message);
      }
    } else if (data) {
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
    if (aptDate !== today) return false;
    if (bookingMode === 'token') {
      return apt.status === 'booked' && (apt.token_number || 0) > currentServingToken;
    }
    return true;
  }).sort((a, b) => bookingMode === 'token' ? (a.token_number || 0) - (b.token_number || 0) : new Date(a.appointment_time) - new Date(b.appointment_time));

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

  // ---- Toast helper ----
  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  // ---- Report helpers ----
  const openReportModal = (apt) => {
    setReportModal(apt);
    setReportImageFile(null);
    setReportForm({
      patient_age: '', chief_complaint: '', diagnosis: '',
      followup_date: '', special_notes: '',
      medicines: [{ name: '', dosage: '', frequency: '', duration: '' }]
    });
  };

  const addMedicineRow = () => {
    setReportForm(f => ({ ...f, medicines: [...f.medicines, { name: '', dosage: '', frequency: '', duration: '' }] }));
  };

  const removeMedicineRow = (i) => {
    setReportForm(f => ({ ...f, medicines: f.medicines.filter((_, idx) => idx !== i) }));
  };

  const updateMedicineRow = (i, field, val) => {
    setReportForm(f => {
      const meds = [...f.medicines];
      meds[i] = { ...meds[i], [field]: val };
      return { ...f, medicines: meds };
    });
  };

  const handleSendReport = async (e) => {
    e.preventDefault();
    if (!reportModal) return;
    setReportSending(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // If an image was uploaded, use the image endpoint
      if (reportImageFile) {
        const formData = new FormData();
        formData.append('appointment_id', reportModal.id);
        formData.append('image', reportImageFile);
        const resp = await fetch(`${apiUrl}/api/reports/send-image`, {
          method: 'POST',
          body: formData,
        });
        const data = await resp.json();
        if (resp.ok) {
          showToast(`✅ Image report sent to ${reportModal.patient_name || 'patient'} on WhatsApp!`, 'success');
          setReportModal(null);
        } else {
          showToast(`❌ Failed: ${data.detail || 'Unknown error'}`, 'error');
        }
        return;
      }

      // Otherwise send typed report as PDF
      const resp = await fetch(`${apiUrl}/api/reports/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ appointment_id: reportModal.id, ...reportForm })
      });
      const data = await resp.json();
      if (resp.ok) {
        showToast(`✅ Report sent to ${reportModal.patient_name || 'patient'} on WhatsApp!`, 'success');
        setReportModal(null);
      } else {
        showToast(`❌ Failed: ${data.detail || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      showToast('❌ Network error. Check if backend is running.', 'error');
    } finally {
      setReportSending(false);
    }
  };

  // ---- Settings helpers ----
  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSettingsSaving(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const resp = await fetch(`${apiUrl}/api/clinics/${clinicId}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (resp.ok) {
        showToast('✅ Settings saved successfully!', 'success');
      } else {
        const d = await resp.json();
        showToast(`❌ Failed: ${d.detail || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      showToast('❌ Network error. Check if backend is running.', 'error');
    } finally {
      setSettingsSaving(false);
    }
  };

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

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flexGrow: 1 }}>
          {[
            ['overview', <HomeIcon size={20} />, t('dashboard.overview'), t('dashboard.overviewDesc')],
            ['upcoming', <Calendar size={20} />, t('dashboard.appointments'), 'Upcoming Schedules'],
            ['patients', <Users size={20} />, t('dashboard.patients'), t('dashboard.patientsDesc')],
            ['reports', <FileText size={20} />, t('dashboard.reports'), t('dashboard.reportsDesc')],
            ['settings', <Settings size={20} />, t('dashboard.settings'), t('dashboard.settingsDesc')],
          ].map(([tab, icon, label, desc]) => (
            <div key={tab} onClick={() => setActiveTab(tab)} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', background: activeTab === tab ? 'var(--v0-blue)' : 'transparent', color: activeTab === tab ? 'white' : 'var(--text-secondary)', cursor: 'pointer', transition: 'background 0.15s' }}>
              {icon}
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: activeTab === tab ? 'white' : 'var(--text-main)', lineHeight: 1.2 }}>{label}</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.85 }}>{desc}</div>
              </div>
            </div>
          ))}
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
            <button onClick={handleLogout} className="btn-v0-outline" style={{ padding: '0.75rem 1.5rem', fontSize: '1rem', borderRadius: '8px', color: 'var(--v0-red)', borderColor: 'var(--v0-red)' }}>
              Log Out
            </button>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>{t('dashboard.liveQueue')}</h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('dashboard.liveQueueSub')}</p>
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button onClick={handleCloseDay} className="btn-v0-danger" style={{ padding: '0.75rem 1.25rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: '8px' }}>
                  <XCircle size={18} /> {t('dashboard.closeDayBtn')}
                </button>
                <div style={{ position: 'relative', width: '300px' }}>
                  <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
                  <input 
                    type="text" 
                    placeholder={t('dashboard.searchPh')} 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-main)', color: 'var(--text-main)', outline: 'none', transition: 'border-color 0.2s' }}
                  />
                </div>
              </div>
            </div>

            {bookingMode === 'token' && (
              <div style={{ marginBottom: '3rem', background: 'white', borderRadius: '16px', padding: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}>
                <div>
                  <h3 style={{ color: 'var(--text-secondary)', fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Live Token Queue</h3>
                  <div style={{ fontSize: '3.5rem', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1, marginBottom: '0.5rem' }}>
                    CURRENTLY SERVING: <span style={{ color: 'var(--v0-blue)' }}>#{currentServingToken}</span>
                  </div>
                  <div style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                    Last Issued Token: #{todayAppointments.reduce((max, apt) => Math.max(max, apt.token_number || 0), 0)} • Patients Waiting: {Math.max(0, todayAppointments.reduce((max, apt) => Math.max(max, apt.token_number || 0), 0) - currentServingToken)}
                  </div>
                </div>
                <button onClick={handleCallNext} style={{ background: 'var(--v0-blue)', color: 'white', border: 'none', padding: '1.5rem 3rem', borderRadius: '12px', fontSize: '1.5rem', fontWeight: 700, cursor: 'pointer', boxShadow: '0 4px 14px 0 rgba(10, 102, 194, 0.39)', transition: 'all 0.2s' }}>
                  CALL NEXT PATIENT
                </button>
              </div>
            )}

            <div className="card" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f0f9ff', borderBottom: '1px solid var(--border-color)' }}>
                    {bookingMode === 'token' && <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Token #</th>}
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thName')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thPhone')}</th>
                    {bookingMode !== 'token' && <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thTime')}</th>}
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thStatus')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>{t('dashboard.thActions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAppointments.length === 0 ? (
                    <tr>
                    <td colSpan={bookingMode === 'token' ? "5" : "5"} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{bookingMode === 'token' ? t('dashboard.noPatientsQueue') : t('dashboard.noPatients')}</td>
                    </tr>
                  ) : (
                    todayAppointments.map((apt, index) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        {bookingMode === 'token' && (
                          <td style={{ padding: '1.25rem 1.5rem', color: 'var(--v0-blue)', fontSize: '1.2rem', fontWeight: 800 }}>
                            #{apt.token_number || '-'}
                          </td>
                        )}
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
                        {bookingMode !== 'token' && (
                          <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem', fontWeight: 600 }}>{new Date(apt.appointment_time).toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'})}</td>
                        )}
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          {renderBadge(apt.status)}
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', height: '76px' }}>
                          {bookingMode === 'token' ? (
                            <button onClick={() => handleCancelToken(apt.id)} className="btn-action btn-v0-danger">
                              <XCircle size={16} /> {t('dashboard.actionCancel')}
                            </button>
                          ) : (
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center', height: '100%' }}>
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
                            </div>
                          )}
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
                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right', height: '76px' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center', height: '100%' }}>
                            {apt.status !== 'completed' && apt.status !== 'cancelled' && (
                              <button onClick={() => handleUpdateStatus(apt.id, 'cancelled')} className="btn-action btn-v0-danger">
                                <XCircle size={16} /> {t('dashboard.actionCancel')}
                              </button>
                            )}
                            <button onClick={() => handleDeleteAppointment(apt.id)} style={{ padding: '0.5rem', marginLeft: '0.5rem', color: 'var(--text-secondary)' }} title="Delete Record">
                              <Trash2 size={16} style={{ cursor: 'pointer' }} onMouseOver={(e) => e.currentTarget.style.color = 'var(--v0-red)'} onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : activeTab === 'patients' ? (
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
        ) : activeTab === 'reports' ? (
          <>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>📋 {t('dashboard.reportsTitle')}</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('dashboard.reportsSub')}</p>
            </div>
            <div className="card" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#f0f9ff', borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thName')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thPhone')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thVisitDate')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{t('dashboard.thStatus')}</th>
                    <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>{t('dashboard.thAction')}</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.length === 0 ? (
                    <tr><td colSpan="5" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>{t('dashboard.noReports')}</td></tr>
                  ) : (
                    // Deduplicate: show only the most recent appointment per unique phone number
                    Object.values(
                      [...appointments]
                        .sort((a, b) => new Date(b.appointment_time) - new Date(a.appointment_time))
                        .reduce((acc, apt) => {
                          if (!acc[apt.phone_number]) acc[apt.phone_number] = apt;
                          return acc;
                        }, {})
                    ).map((apt) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1.25rem 1.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.4rem', borderRadius: '50%' }}><User size={18} /></div>
                            <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.95rem' }}>{apt.patient_name || 'Unknown'}</span>
                          </div>
                        </td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem' }}>{apt.phone_number}</td>
                        <td style={{ padding: '1.25rem 1.5rem', color: 'var(--text-main)', fontSize: '0.9rem' }}>{new Date(apt.appointment_time).toLocaleDateString()}</td>
                        <td style={{ padding: '1.25rem 1.5rem' }}>{renderBadge(apt.status)}</td>
                        <td style={{ padding: '1.25rem 1.5rem', textAlign: 'right' }}>
                          <button
                            onClick={() => openReportModal(apt)}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: '#0ea5e9', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer' }}
                          >
                            <FileText size={15} /> {t('dashboard.sendReportBtn')}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : activeTab === 'settings' ? (
          <>
            <div style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>⚙️ {t('dashboard.settingsTitle')}</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{t('dashboard.settingsSub')}</p>
            </div>
            <div className="card" style={{ maxWidth: '600px', padding: '2rem' }}>
              {!settingsLoaded ? (
                <p style={{ color: 'var(--text-secondary)' }}>{t('dashboard.settingsLoading')}</p>
              ) : (
                <form onSubmit={handleSaveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>{t('dashboard.settingsDoctorName')}</label>
                    <input type="text" className="form-input" value={settings.doctor_name} onChange={e => setSettings(s => ({ ...s, doctor_name: e.target.value }))} placeholder={t('dashboard.settingsDoctorNamePh')} />
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{t('dashboard.settingsDoctorNameHint')}</p>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>{t('dashboard.settingsAddress')}</label>
                    <input type="text" className="form-input" value={settings.clinic_address} onChange={e => setSettings(s => ({ ...s, clinic_address: e.target.value }))} placeholder={t('dashboard.settingsAddressPh')} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Star size={15} style={{ color: '#f59e0b' }} /> {t('dashboard.settingsReviewLink')}</span>
                    </label>
                    <input type="url" className="form-input" value={settings.google_review_link} onChange={e => setSettings(s => ({ ...s, google_review_link: e.target.value }))} placeholder={t('dashboard.settingsReviewLinkPh')} />
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{t('dashboard.settingsReviewLinkHint')} <strong>Completed</strong></p>
                    <div style={{ background: '#fefce8', border: '1px solid #fde047', borderRadius: '8px', padding: '0.75rem', marginTop: '0.5rem', fontSize: '0.8rem', color: '#713f12' }}>
                      {t('dashboard.settingsReviewLinkTip')}
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>💰 Consultation Fee (₹)</label>
                    <input type="text" className="form-input" value={settings.consultation_fee} onChange={e => setSettings(s => ({ ...s, consultation_fee: e.target.value }))} placeholder="e.g. 300" />
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Shown to patients on WhatsApp when they ask about fees</p>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>📍 Google Maps Link</label>
                    <input type="url" className="form-input" value={settings.maps_link} onChange={e => setSettings(s => ({ ...s, maps_link: e.target.value }))} placeholder="https://maps.app.goo.gl/..." />
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Sent to patients when they tap "Location / Maps" on WhatsApp</p>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.4rem', color: 'var(--text-main)' }}>📞 Clinic Contact Number</label>
                    <input type="tel" className="form-input" value={settings.clinic_phone} onChange={e => setSettings(s => ({ ...s, clinic_phone: e.target.value }))} placeholder="+91 98765 43210" />
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Sent to patients when they tap "📞 Call Clinic" on WhatsApp</p>
                  </div>
                  <button type="submit" disabled={settingsSaving} style={{ alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'var(--v0-blue)', color: 'white', border: 'none', padding: '0.75rem 1.75rem', borderRadius: '8px', fontSize: '0.95rem', fontWeight: 600, cursor: settingsSaving ? 'not-allowed' : 'pointer', opacity: settingsSaving ? 0.7 : 1 }}>
                    {settingsSaving ? t('dashboard.settingsSaving') : `💾 ${t('dashboard.settingsSaveBtn')}`}
                  </button>
                </form>
              )}
            </div>
          </>
        ) : null}
      </main>

      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: '2rem', right: '2rem', zIndex: 2000,
          background: toast.type === 'error' ? '#fee2e2' : '#dcfce7',
          color: toast.type === 'error' ? '#991b1b' : '#166534',
          border: `1px solid ${toast.type === 'error' ? '#fca5a5' : '#86efac'}`,
          padding: '0.9rem 1.4rem', borderRadius: '12px', fontWeight: 600,
          fontSize: '0.9rem', boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
          maxWidth: '360px'
        }}>
          {toast.msg}
        </div>
      )}

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
              {bookingMode === 'scheduled' && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalDate')}</label>
                    <input type="date" required className="form-input" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>{t('dashboard.modalTime')}</label>
                    <input type="time" required className="form-input" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
                  </div>
                </>
              )}
              
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-v0-outline" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px' }}>{t('dashboard.modalBtnCancel')}</button>
                <button type="submit" className="btn-v0-primary" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px', border: 'none' }}>{t('dashboard.modalBtnBook')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Send Report Modal */}
      {reportModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '1rem' }}>
          <div className="card" style={{ width: '100%', maxWidth: '640px', padding: '2rem', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>📋 Send Medical Report</h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>For: <strong>{reportModal.patient_name}</strong> · {reportModal.phone_number}</p>
              </div>
              <button onClick={() => setReportModal(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', fontSize: '1.4rem' }}>✕</button>
            </div>

            <form onSubmit={handleSendReport} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>

              {/* Image Upload Option */}
              <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '10px', padding: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 700, color: '#0369a1', marginBottom: '0.5rem' }}>
                  📷 Upload Lab Report / Scan Image (optional)
                </label>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                  Upload a photo or scan of a lab report or prescription image. It will be wrapped in a PDF and sent directly. If uploaded, the typed fields below are ignored.
                </p>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/jpg,image/webp"
                  onChange={e => setReportImageFile(e.target.files?.[0] || null)}
                  style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-main)' }}
                />
                {reportImageFile && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', background: '#dcfce7', border: '1px solid #86efac', borderRadius: '6px', padding: '0.4rem 0.7rem', fontSize: '0.82rem', color: '#166534' }}>
                    ✅ <strong>{reportImageFile.name}</strong> selected — will send as PDF
                    <button type="button" onClick={() => setReportImageFile(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#dc2626', fontSize: '1rem', lineHeight: 1 }}>✕</button>
                  </div>
                )}
              </div>

              {/* Divider */}
              {!reportImageFile && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border-color)' }} />
                  OR type the prescription below
                  <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border-color)' }} />
                </div>
              )}

              {/* Typed Report Fields — hidden when image is selected */}
              {!reportImageFile && (<>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-main)' }}>Patient Age</label>
                  <input type="text" className="form-input" placeholder="e.g. 35" value={reportForm.patient_age} onChange={e => setReportForm(f => ({ ...f, patient_age: e.target.value }))} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-main)' }}>Follow-up Date</label>
                  <input type="date" className="form-input" value={reportForm.followup_date} onChange={e => setReportForm(f => ({ ...f, followup_date: e.target.value }))} />
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-main)' }}>Chief Complaint / Symptoms</label>
                <textarea className="form-input" rows={2} placeholder="Patient's main complaints or symptoms" value={reportForm.chief_complaint} onChange={e => setReportForm(f => ({ ...f, chief_complaint: e.target.value }))} style={{ resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-main)' }}>Diagnosis</label>
                <textarea className="form-input" rows={2} placeholder="Clinical diagnosis" value={reportForm.diagnosis} onChange={e => setReportForm(f => ({ ...f, diagnosis: e.target.value }))} style={{ resize: 'vertical' }} />
              </div>

              {/* Medicines Table */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>Medicines / Prescription</label>
                  <button type="button" onClick={addMedicineRow} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', border: 'none', padding: '0.3rem 0.7rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}>
                    <Plus size={14} /> Add Row
                  </button>
                </div>
                <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: '#f0f9ff' }}>
                        {['Medicine', 'Dosage', 'Frequency', 'Duration', ''].map(h => (
                          <th key={h} style={{ padding: '0.5rem 0.6rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textAlign: 'left', textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {reportForm.medicines.map((m, i) => (
                        <tr key={i} style={{ borderTop: '1px solid var(--border-color)' }}>
                          {['name', 'dosage', 'frequency', 'duration'].map(field => (
                            <td key={field} style={{ padding: '0.35rem 0.4rem' }}>
                              <input
                                type="text"
                                value={m[field]}
                                onChange={e => updateMedicineRow(i, field, e.target.value)}
                                placeholder={field === 'name' ? 'Paracetamol' : field === 'dosage' ? '500mg' : field === 'frequency' ? '3x/day' : '5 days'}
                                style={{ width: '100%', padding: '0.3rem 0.5rem', border: '1px solid var(--border-color)', borderRadius: '5px', fontSize: '0.82rem', background: 'var(--bg-main)', color: 'var(--text-main)', outline: 'none' }}
                              />
                            </td>
                          ))}
                          <td style={{ padding: '0.35rem 0.4rem', textAlign: 'center' }}>
                            {reportForm.medicines.length > 1 && (
                              <button type="button" onClick={() => removeMedicineRow(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--v0-red)' }}><Minus size={15} /></button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem', color: 'var(--text-main)' }}>Special Instructions (optional)</label>
                <textarea className="form-input" rows={2} placeholder="Any special notes or instructions for the patient" value={reportForm.special_notes} onChange={e => setReportForm(f => ({ ...f, special_notes: e.target.value }))} style={{ resize: 'vertical' }} />
              </div>
              </>)}

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button type="button" onClick={() => setReportModal(null)} className="btn-v0-outline" style={{ flex: 1, padding: '0.75rem', borderRadius: '8px' }}>Cancel</button>
                <button type="submit" disabled={reportSending} style={{ flex: 2, padding: '0.75rem', borderRadius: '8px', background: '#0ea5e9', color: 'white', border: 'none', fontWeight: 700, fontSize: '0.95rem', cursor: reportSending ? 'not-allowed' : 'pointer', opacity: reportSending ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                  <Send size={16} /> {reportSending ? 'Sending…' : reportImageFile ? '📷 Send Image as PDF via WhatsApp' : 'Generate PDF & Send via WhatsApp'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
