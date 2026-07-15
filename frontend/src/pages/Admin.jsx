import { useState } from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';

const Admin = () => {
  const [pin, setPin] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [password, setPassword] = useState('');
  const [bookingMode, setBookingMode] = useState('scheduled');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('21:00');
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  // Upgrade State
  const [upgradeClinicId, setUpgradeClinicId] = useState('');
  const [upgradeLoading, setUpgradeLoading] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState(null);
  const [upgradeError, setUpgradeError] = useState(null);

  const handleOnboard = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    setError(null);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/onboard`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pin,
          business_name: businessName,
          admin_email: adminEmail,
          password,
          booking_mode: bookingMode,
          working_hours: { start: startTime, end: endTime }
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(`Successfully onboarded! Clinic ID: ${data.clinic_id}. Trial ends: ${new Date(data.trial_end_date).toLocaleDateString()}`);
        setBusinessName('');
        setAdminEmail('');
        setPassword('');
        setBookingMode('scheduled');
      } else {
        setError(data.detail || data || "Failed to onboard clinic.");
      }
    } catch (err) {
      setError("Network error. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (e) => {
    e.preventDefault();
    setUpgradeLoading(true);
    setUpgradeMessage(null);
    setUpgradeError(null);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/upgrade`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pin,
          clinic_id: upgradeClinicId
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setUpgradeMessage("Clinic upgraded to permanent account successfully!");
        setUpgradeClinicId('');
      } else {
        setUpgradeError(data.detail || data || "Failed to upgrade clinic.");
      }
    } catch (err) {
      setUpgradeError("Network error. Is the backend running?");
    } finally {
      setUpgradeLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', background: 'var(--bg-page)', padding: '2rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: '600px', padding: '2.5rem', marginBottom: '2rem' }}>
        
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ display: 'inline-flex', background: 'var(--v0-red-light)', color: 'var(--v0-red)', padding: '1rem', borderRadius: '50%', marginBottom: '1rem' }}>
            <ShieldAlert size={32} />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '0.5rem' }}>
            Secret Admin Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Onboard new clinics for a 7-day trial.
          </p>
        </div>

        {message && (
          <div style={{ padding: '1rem', background: '#ecfdf5', color: '#059669', borderRadius: '8px', marginBottom: '1.5rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start', fontSize: '0.9rem' }}>
            <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{message}</div>
          </div>
        )}

        {error && (
          <div style={{ padding: '1rem', background: 'var(--v0-red-light)', color: 'var(--v0-red)', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem', border: '1px solid #fecaca' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleOnboard} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <label className="form-label" htmlFor="pin" style={{ color: 'var(--v0-red)', fontWeight: 600 }}>Master Admin PIN</label>
            <input 
              id="pin"
              type="password" 
              className="form-input"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              required 
              placeholder="••••••"
            />
          </div>

          <div>
            <label className="form-label" htmlFor="businessName">Clinic Business Name</label>
            <input 
              id="businessName"
              type="text" 
              className="form-input"
              value={businessName}
              onChange={(e) => setBusinessName(e.target.value)}
              required 
              placeholder="Dr. Smith Dental"
            />
          </div>
          
          <div>
            <label className="form-label" htmlFor="adminEmail">Clinic Admin Email (Login)</label>
            <input 
              id="adminEmail"
              type="email" 
              className="form-input"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              required 
              placeholder="admin@clinic.com"
            />
          </div>
          
          <div>
            <label className="form-label" htmlFor="password">Temporary Password</label>
            <input 
              id="password"
              type="text" 
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
              placeholder="Temp123!"
            />
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Must be at least 6 characters.</p>
          </div>

          <div>
            <label className="form-label" htmlFor="bookingMode">Clinic Workflow Type</label>
            <select 
              id="bookingMode"
              className="form-input"
              value={bookingMode}
              onChange={(e) => setBookingMode(e.target.value)}
              required
            >
              <option value="scheduled">Standard Time-Scheduled Appointments</option>
              <option value="token">Live Token Queue (First-Come First-Served)</option>
            </select>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>This permanently locks the UI into this workflow.</p>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label" htmlFor="startTime">Opening Time</label>
              <input 
                id="startTime"
                type="time" 
                className="form-input"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required 
              />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label" htmlFor="endTime">Closing Time</label>
              <input 
                id="endTime"
                type="time" 
                className="form-input"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                required 
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn btn-primary" style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'var(--v0-blue)', border: 'none', color: 'white', borderRadius: '8px', cursor: 'pointer' }}>
            {loading ? 'Creating Clinic...' : 'Create Clinic & Start Trial'}
          </button>
        </form>
      </div>

      {/* Upgrade Section */}
      <div className="card" style={{ width: '100%', maxWidth: '600px', padding: '2.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '1rem' }}>
          Upgrade Clinic to Permanent
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Remove the 7-day trial limit from a clinic account so they never expire.
        </p>

        {upgradeMessage && (
          <div style={{ padding: '1rem', background: '#ecfdf5', color: '#059669', borderRadius: '8px', marginBottom: '1.5rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start', fontSize: '0.9rem' }}>
            <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{upgradeMessage}</div>
          </div>
        )}

        {upgradeError && (
          <div style={{ padding: '1rem', background: 'var(--v0-red-light)', color: 'var(--v0-red)', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem', border: '1px solid #fecaca' }}>
            {upgradeError}
          </div>
        )}

        <form onSubmit={handleUpgrade} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label className="form-label" htmlFor="upgradeClinicId">Clinic ID (UUID)</label>
            <input 
              id="upgradeClinicId"
              type="text" 
              className="form-input"
              value={upgradeClinicId}
              onChange={(e) => setUpgradeClinicId(e.target.value)}
              required 
              placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
            />
          </div>
          <button type="submit" disabled={upgradeLoading} className="btn btn-primary" style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'var(--v0-green)', border: 'none', color: 'white', borderRadius: '8px', cursor: 'pointer' }}>
            {upgradeLoading ? 'Upgrading...' : 'Upgrade to Permanent'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Admin;
