import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Features from './components/Features';
import DomainTabs from './components/DomainTabs';
import Footer from './components/Footer';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';
import DataDeletion from './pages/DataDeletion';
import Demo from './pages/Demo';
import Admin from './pages/Admin';

const ProtectedRoute = ({ children }) => {
  // We will implement auth check here later
  return children;
};

const Home = () => (
  <>
    <Navbar />
    <Hero />
    <DomainTabs />
    <Features />
    <Footer />
  </>
);

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/demo" element={<Demo />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/data-deletion" element={<DataDeletion />} />
      <Route path="/secret-admin-onboard" element={<Admin />} />
    </Routes>
  );
}

export default App;
