import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchHCPs, selectHcp, fetchInteractions, resetForm } from '../store';
import { Search, User, MapPin, Mail, Phone, Calendar, RefreshCw, UserCheck } from 'lucide-react';

const HCPInsights = () => {
  const dispatch = useDispatch();
  const { list: hcps, selectedHcp, loading } = useSelector((state) => state.hcps);
  const { list: interactions } = useSelector((state) => state.interactions);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    dispatch(fetchHCPs());
  }, [dispatch]);

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
    dispatch(fetchHCPs(e.target.value));
  };

  const handleHcpSelect = (hcp) => {
    dispatch(selectHcp(hcp));
    dispatch(fetchInteractions(hcp.id));
    dispatch(resetForm()); // Clear form and sync to new HCP
  };

  // Get specialty color badge class
  const getSpecialtyClass = (spec) => {
    const s = spec.toLowerCase();
    if (s.includes('cardio')) return 'badge-cardio';
    if (s.includes('onco')) return 'badge-onco';
    if (s.includes('pedia')) return 'badge-pedia';
    if (s.includes('neuro')) return 'badge-neuro';
    if (s.includes('endo')) return 'badge-endo';
    return 'badge-default';
  };

  const activeFollowups = interactions.filter(i => i.follow_up_date && new Date(i.follow_up_date) >= new Date()).length;

  return (
    <div className="hcp-insights-container">
      {/* Sidebar List */}
      <div className="hcp-sidebar glass-panel">
        <div className="sidebar-header">
          <h3>Healthcare Professionals</h3>
          <p className="subtitle">Select HCP to manage interactions</p>
        </div>
        <div className="search-container">
          <Search className="search-icon" size={16} />
          <input
            type="text"
            placeholder="Search name, specialty..."
            value={searchTerm}
            onChange={handleSearchChange}
            className="search-input"
          />
        </div>

        {loading && hcps.length === 0 ? (
          <div className="loading-container">
            <RefreshCw className="animate-spin text-primary" size={24} />
            <span>Loading HCP list...</span>
          </div>
        ) : (
          <div className="hcp-list">
            {hcps.map((hcp) => (
              <div
                key={hcp.id}
                className={`hcp-item ${selectedHcp?.id === hcp.id ? 'active' : ''}`}
                onClick={() => handleHcpSelect(hcp)}
              >
                <div className="hcp-item-info">
                  <div className="hcp-item-title">
                    <User size={14} className="hcp-icon" />
                    <span className="hcp-name">{hcp.name}</span>
                  </div>
                  <span className="hcp-clinic">{hcp.clinic_name}</span>
                </div>
                <span className={`specialty-badge ${getSpecialtyClass(hcp.specialty)}`}>
                  {hcp.specialty}
                </span>
              </div>
            ))}
            {hcps.length === 0 && (
              <div className="empty-state">No HCPs found matching "{searchTerm}"</div>
            )}
          </div>
        )}
      </div>

      {/* Profile Details Panel */}
      <div className="hcp-profile-detail">
        {selectedHcp ? (
          <div className="profile-card glass-panel fade-in">
            <div className="profile-card-header">
              <div className="profile-title-row">
                <div className="avatar-placeholder">
                  {selectedHcp.name.split(' ').map(w => w[0]).join('')}
                </div>
                <div>
                  <h2 className="profile-name">{selectedHcp.name}</h2>
                  <span className={`specialty-badge ${getSpecialtyClass(selectedHcp.specialty)}`}>
                    {selectedHcp.specialty}
                  </span>
                </div>
              </div>
              <div className="profile-quick-stats">
                <div className="stat-box">
                  <span className="stat-value">{interactions.length}</span>
                  <span className="stat-label">Interactions</span>
                </div>
                <div className="stat-box">
                  <span className="stat-value text-accent">{activeFollowups}</span>
                  <span className="stat-label">Pending Follow-ups</span>
                </div>
              </div>
            </div>

            <div className="profile-details-grid">
              <div className="detail-item">
                <MapPin className="detail-icon" size={16} />
                <div>
                  <span className="detail-label">Clinic / Location</span>
                  <span className="detail-value">{selectedHcp.clinic_name}</span>
                </div>
              </div>
              <div className="detail-item">
                <Mail className="detail-icon" size={16} />
                <div>
                  <span className="detail-label">Email Address</span>
                  <span className="detail-value">{selectedHcp.email || 'N/A'}</span>
                </div>
              </div>
              <div className="detail-item">
                <Phone className="detail-icon" size={16} />
                <div>
                  <span className="detail-label">Phone Number</span>
                  <span className="detail-value">{selectedHcp.phone || 'N/A'}</span>
                </div>
              </div>
              <div className="detail-item">
                <Calendar className="detail-icon" size={16} />
                <div>
                  <span className="detail-label">Last Interaction</span>
                  <span className="detail-value">{selectedHcp.last_interaction_date || 'No recorded history'}</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="profile-placeholder glass-panel">
            <UserCheck size={48} className="placeholder-icon text-muted animate-pulse" />
            <h3>Select a Healthcare Professional</h3>
            <p>Select a doctor from the list to display their active profile details, quick KPIs, and interaction logs.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HCPInsights;
