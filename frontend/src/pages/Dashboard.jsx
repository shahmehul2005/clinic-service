import { useAuth } from '../context/AuthContext';
import { LogOut, Home as HomeIcon, Settings, Users, Activity, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);

  useEffect(() => {
    const fetchAppointments = async () => {
      // Fetch appointments from Supabase
      const { data, error } = await supabase
        .from('appointments')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(5);
        
      if (!error && data) {
        setAppointments(data);
      }
    };

    fetchAppointments();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'hsl(var(--bg-primary))' }}>
      {/* Sidebar */}
      <aside className="glass" style={{ width: '250px', padding: '2rem 1rem', display: 'flex', flexDirection: 'column', borderRadius: 0, borderRight: '1px solid var(--glass-border)', borderTop: 'none', borderBottom: 'none', borderLeft: 'none' }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.5px', marginBottom: '3rem', paddingLeft: '1rem' }}>
          Platform<span className="text-gradient">X</span>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flexGrow: 1 }}>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.1)', color: 'white' }}>
            <HomeIcon size={20} /> Overview
          </a>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: 'hsl(var(--text-secondary))' }}>
            <Calendar size={20} /> Appointments
          </a>
          <a href="#" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', color: 'hsl(var(--text-secondary))' }}>
            <Users size={20} /> Patients
          </a>
        </nav>

        <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--glass-border)' }}>
          <div style={{ padding: '0.75rem 1rem', marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.9rem', color: 'hsl(var(--text-secondary))' }}>Logged in as</p>
            <p style={{ fontWeight: 600 }}>{user?.email}</p>
          </div>
          <button onClick={handleLogout} className="btn btn-glass" style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
            <LogOut size={18} /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flexGrow: 1, padding: '2rem 3rem', overflowY: 'auto' }}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem' }}>
          <h1 style={{ fontSize: '2rem' }}>Receptionist Dashboard</h1>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button className="btn btn-primary">New Appointment</button>
          </div>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', marginBottom: '3rem' }}>
          <div className="glass" style={{ padding: '2rem' }}>
            <h3 style={{ color: 'hsl(var(--text-secondary))', marginBottom: '1rem' }}>Appointments Today</h3>
            <p style={{ fontSize: '2.5rem', fontWeight: 700 }}>24</p>
          </div>
          <div className="glass" style={{ padding: '2rem' }}>
            <h3 style={{ color: 'hsl(var(--text-secondary))', marginBottom: '1rem' }}>Pending Confirmations</h3>
            <p style={{ fontSize: '2.5rem', fontWeight: 700 }}>3</p>
          </div>
        </div>

        <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Recent Appointments (Live from Supabase)</h2>
        <div className="glass" style={{ padding: '2rem', borderRadius: '1rem' }}>
          {appointments.length === 0 ? (
             <p style={{ color: 'hsl(var(--text-secondary))' }}>No appointments found. (Ensure your Supabase keys are set and the 'appointments' table exists!)</p>
          ) : (
            <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--glass-border)' }}>
                  <th style={{ padding: '1rem', color: 'hsl(var(--text-secondary))' }}>Patient Name</th>
                  <th style={{ padding: '1rem', color: 'hsl(var(--text-secondary))' }}>Time</th>
                  <th style={{ padding: '1rem', color: 'hsl(var(--text-secondary))' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((apt, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '1rem' }}>{apt.patient_name || 'Unknown'}</td>
                    <td style={{ padding: '1rem' }}>{new Date(apt.created_at).toLocaleTimeString()}</td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{ padding: '0.25rem 0.75rem', borderRadius: '999px', background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', fontSize: '0.85rem' }}>
                        {apt.status || 'Scheduled'}
                      </span>
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
