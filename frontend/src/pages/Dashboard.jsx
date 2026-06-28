import { useAuth } from '../context/AuthContext';
import { 
  Home as HomeIcon, Calendar, Users, 
  Search, Clock, CheckCircle2, User, XCircle, LifeBuoy, HeartPulse, Trash2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newPatientName, setNewPatientName] = useState('');
  const [newPatientPhone, setNewPatientPhone] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    const fetchAppointments = async () => {
      const { data, error } = await supabase
        .from('appointments')
        .select('*')
        .order('appointment_time', { ascending: true });
        
      if (!error && data) {
        setAppointments(data);
      }
    };
    fetchAppointments();
  }, []);

  const handleUpdateStatus = async (id, newStatus) => {
    const { error } = await supabase
      .from('appointments')
      .update({ status: newStatus })
      .eq('id', id);
      
    if (!error) {
      setAppointments(prev => prev.map(apt => apt.id === id ? { ...apt, status: newStatus } : apt));
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
    
    // Combine date and time into ISO string
    const appointmentDateTime = new Date(`${newDate}T${newTime}`).toISOString();
    
    const { data, error } = await supabase
      .from('appointments')
      .insert([
        {
          clinic_id: 1, // Default clinic ID for MVP
          phone_number: newPatientPhone,
          patient_name: newPatientName,
          appointment_time: appointmentDateTime,
          status: 'booked'
        }
      ])
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

  const getReason = (idx) => {
    const reasons = ["Annual check-up", "Follow-up visit", "Lab results", "Knee pain consult", "Prescription refill", "Skin check"];
    return reasons[idx % reasons.length];
  };

  const renderBadge = (status) => {
    if (status === 'booked') return <span className="badge badge-waiting"><Clock size={14}/> Waiting</span>;
    if (status === 'arrived') return <span className="badge badge-checked-in"><CheckCircle2 size={14}/> Checked In</span>;
    if (status === 'completed') return <span className="badge badge-seen"><CheckCircle2 size={14}/> Seen by Doctor</span>;
    if (status === 'cancelled') return <span className="badge badge-cancelled"><XCircle size={14}/> Cancelled</span>;
    return <span className="badge badge-waiting"><Clock size={14}/> {status}</span>;
  };

  // Stats calculation
  const stats = {
    waiting: appointments.filter(a => a.status === 'booked').length,
    checkedIn: appointments.filter(a => a.status === 'arrived').length,
    seen: appointments.filter(a => a.status === 'completed').length,
    total: appointments.length
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-page)', position: 'relative' }}>
      {/* Sidebar */}
      <aside style={{ width: '280px', padding: '1.5rem', display: 'flex', flexDirection: 'column', background: 'white', borderRight: '1px solid var(--border-color)' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem' }}>
          <div style={{ background: 'var(--v0-blue)', color: 'white', padding: '0.5rem', borderRadius: '8px' }}>
            <HeartPulse size={24} />
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>ClinicOS</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Reception Desk</div>
          </div>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flexGrow: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', background: 'var(--v0-blue)', color: 'white', cursor: 'pointer' }}>
            <HomeIcon size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', lineHeight: 1.2 }}>Overview</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>Today at a glance</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Calendar size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.2 }}>Appointments</div>
              <div style={{ fontSize: '0.75rem' }}>Upcoming visits</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.8rem 1rem', borderRadius: '12px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <Users size={20} /> 
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.2 }}>Patients</div>
              <div style={{ fontSize: '0.75rem' }}>Patient records</div>
            </div>
          </div>
        </nav>

        {/* Support Box */}
        <div style={{ background: '#f0f9ff', borderRadius: '12px', padding: '1.25rem', marginTop: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-main)', fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.9rem' }}>
            <LifeBuoy size={18} /> Need a hand?
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Call our friendly support team any time at <strong style={{ color: 'var(--text-main)' }}>1-800-555-0142</strong>.
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flexGrow: 1, padding: '2.5rem', overflowY: 'auto' }}>
        
        {/* Header */}
        <header style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--v0-blue)', fontWeight: 500, fontSize: '0.9rem', marginBottom: '0.5rem' }}>
              <Calendar size={18} /> Sunday, June 28
            </div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
              Good morning, Susan
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginTop: '0.25rem' }}>
              Here is everyone arriving at the clinic today.
            </p>
          </div>
          <button onClick={() => setIsModalOpen(true)} className="btn-primary" style={{ padding: '0.75rem 1.5rem', fontSize: '1rem' }}>
            + New Appointment
          </button>
        </header>

        {/* Stat Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
          <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.75rem', borderRadius: '50%' }}>
              <Clock size={24} />
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.waiting}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Still Waiting</div>
            </div>
          </div>
          <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ background: 'var(--v0-blue-light)', color: 'var(--v0-blue)', padding: '0.75rem', borderRadius: '50%' }}>
              <CheckCircle2 size={24} />
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.checkedIn}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Checked In</div>
            </div>
          </div>
          <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ color: 'var(--text-main)', padding: '0.75rem', borderRadius: '50%', border: '1px solid var(--border-color)' }}>
              <CheckCircle2 size={24} />
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.seen}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Seen by Doctor</div>
            </div>
          </div>
          <div className="card" style={{ padding: '1.5rem', display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ background: '#f1f5f9', color: 'var(--text-main)', padding: '0.75rem', borderRadius: '50%' }}>
              <Users size={24} />
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.2 }}>{stats.total}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Total Today</div>
            </div>
          </div>
        </div>

        {/* Data Table Area */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>Live Patient Queue</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Tap a button to check a patient in, mark them complete, or cancel.</p>
          </div>
          <div style={{ position: 'relative', width: '300px' }}>
            <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              placeholder="Search by name..." 
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
                <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Patient Name</th>
                <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Phone Number</th>
                <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Time</th>
                <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Status</th>
                <th style={{ padding: '1rem 1.5rem', fontSize: '0.75rem', fontWeight: 700, color: '#0369a1', textTransform: 'uppercase', letterSpacing: '0.5px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAppointments.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No matching patients found.</td>
                </tr>
              ) : (
                filteredAppointments.map((apt, index) => (
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
                          <CheckCircle2 size={16} /> Mark Arrived
                        </button>
                      )}
                      {(apt.status === 'booked' || apt.status === 'arrived') && (
                        <button onClick={() => handleUpdateStatus(apt.id, 'completed')} className="btn-action btn-v0-outline">
                          <CheckCircle2 size={16} /> Complete
                        </button>
                      )}
                      {apt.status !== 'completed' && apt.status !== 'cancelled' && (
                        <button onClick={() => handleUpdateStatus(apt.id, 'cancelled')} className="btn-action btn-v0-danger">
                          <XCircle size={16} /> Cancel
                        </button>
                      )}
                      {(apt.status === 'completed' || apt.status === 'cancelled') && (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No action needed</span>
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
      </main>

      {/* Add Appointment Modal */}
      {isModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '100%', maxWidth: '400px', padding: '2rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1.5rem' }}>Add New Patient</h2>
            
            {submitError && (
              <div style={{ padding: '0.75rem', background: 'var(--v0-red-light)', color: 'var(--v0-red)', borderRadius: '6px', fontSize: '0.875rem', marginBottom: '1rem', border: '1px solid #fecaca' }}>
                {submitError}
              </div>
            )}

            <form onSubmit={handleAddAppointment} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>Patient Name</label>
                <input type="text" required className="form-input" value={newPatientName} onChange={(e) => setNewPatientName(e.target.value)} placeholder="John Doe" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>Phone Number</label>
                <input type="text" required className="form-input" value={newPatientPhone} onChange={(e) => setNewPatientPhone(e.target.value)} placeholder="+1 (555) 000-0000" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>Date</label>
                <input type="date" required className="form-input" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem', color: 'var(--text-main)' }}>Time</label>
                <input type="time" required className="form-input" value={newTime} onChange={(e) => setNewTime(e.target.value)} />
              </div>
              
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-v0-outline" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px' }}>Cancel</button>
                <button type="submit" className="btn-v0-primary" style={{ flex: 1, padding: '0.65rem', borderRadius: '6px', border: 'none' }}>Book Slot</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
