import { useAuth } from '../context/AuthContext';
import { LogOut, Home as HomeIcon, Settings, Users, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);

  useEffect(() => {
    const fetchAppointments = async () => {
      const { data, error } = await supabase
        .from('appointments')
        .select('*')
        .order('appointment_time', { ascending: true })
        .limit(20);
        
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
    } else {
      console.error("Error updating status:", error);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const getBadgeClass = (status) => {
    if (status === 'arrived') return 'badge badge-arrived';
    if (status === 'completed') return 'badge badge-completed';
    return 'badge badge-booked';
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-page)' }}>
      {/* Sidebar */}
      <aside className="card" style={{ width: '250px', padding: '2rem 1rem', display: 'flex', flexDirection: 'column', borderRadius: 0, borderTop: 'none', borderBottom: 'none', borderLeft: 'none' }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '3rem', paddingLeft: '1rem', color: 'var(--text-main)' }}>
          ClinicOS
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flexGrow: 1 }}>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: '#f1f5f9', color: 'var(--primary)', fontWeight: 500 }}>
            <HomeIcon size={20} /> Overview
          </a>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: 'var(--text-secondary)' }}>
            <Calendar size={20} /> Appointments
          </a>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: 'var(--text-secondary)' }}>
            <Users size={20} /> Patients
          </a>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: 'var(--text-secondary)' }}>
            <Settings size={20} /> Settings
          </a>
        </nav>

        <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ padding: '0.75rem 1rem', marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Logged in as</p>
            <p style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)', wordBreak: 'break-all' }}>{user?.email}</p>
          </div>
          <button onClick={handleLogout} className="btn btn-outline" style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flexGrow: 1, padding: '2rem 3rem', overflowY: 'auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <div>
            <h1 style={{ fontSize: '1.875rem', fontWeight: 600, color: 'var(--text-main)' }}>Receptionist Dashboard</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Manage today's patient queue and appointments.</p>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button className="btn btn-primary">+ New Appointment</button>
          </div>
        </header>

        {/* Stats Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
          <div className="card" style={{ padding: '1.5rem' }}>
            <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Appointments Today</h3>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-main)' }}>24</p>
          </div>
          <div className="card" style={{ padding: '1.5rem' }}>
            <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Pending Confirmations</h3>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-main)' }}>3</p>
          </div>
          <div className="card" style={{ padding: '1.5rem' }}>
            <h3 style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>AI Handled</h3>
            <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-main)' }}>18</p>
          </div>
        </div>

        {/* Data Table */}
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '1rem' }}>Live Patient Queue</h2>
        <div className="card" style={{ overflowX: 'auto' }}>
          {appointments.length === 0 ? (
             <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                No appointments currently in the queue.
             </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Patient Name</th>
                  <th>Phone Number</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((apt) => (
                  <tr key={apt.id}>
                    <td style={{ fontWeight: 500, color: 'var(--text-main)' }}>{apt.patient_name || 'Unknown'}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{apt.phone_number}</td>
                    <td>{new Date(apt.appointment_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                    <td>
                      <span className={getBadgeClass(apt.status)}>
                        {apt.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      {apt.status === 'booked' && (
                        <button 
                          onClick={() => handleUpdateStatus(apt.id, 'arrived')}
                          className="btn btn-outline" style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', color: '#059669', borderColor: '#34d399' }}>
                          Mark Arrived
                        </button>
                      )}
                      {(apt.status === 'booked' || apt.status === 'arrived') && (
                        <button 
                          onClick={() => handleUpdateStatus(apt.id, 'completed')}
                          className="btn btn-outline" style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', color: '#4f46e5', borderColor: '#818cf8' }}>
                          Complete
                        </button>
                      )}
                      {apt.status !== 'completed' && apt.status !== 'cancelled' && (
                        <button 
                          onClick={() => handleUpdateStatus(apt.id, 'cancelled')}
                          className="btn btn-outline" style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', color: '#dc2626', borderColor: '#f87171' }}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
