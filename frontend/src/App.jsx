import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions, fetchHCPs, startEditingInteraction, resetAndSeedDatabase } from './store';
import HCPInsights from './components/HCPInsights';
import ChatCopilot from './components/ChatCopilot';
import InteractionForm from './components/InteractionForm';
import { Activity, Database, RefreshCw, User } from 'lucide-react';

function App() {
  const dispatch = useDispatch();
  const { selectedHcp, list: hcps } = useSelector((state) => state.hcps);
  const { list: interactions, loading } = useSelector((state) => state.interactions);

  // Initial load of interactions
  useEffect(() => {
    dispatch(fetchInteractions(selectedHcp?.id || null));
  }, [selectedHcp, dispatch]);

  const handleReseed = () => {
    if (window.confirm('Are you sure you want to reset and re-seed the database? This will clear all custom logs.')) {
      dispatch(resetAndSeedDatabase());
    }
  };

  const handleEditClick = (interaction) => {
    dispatch(startEditingInteraction(interaction));
  };

  // Find HCP name by ID
  const getHcpName = (id) => {
    const hcp = hcps.find(h => h.id === id);
    return hcp ? hcp.name : `HCP #${id}`;
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header glass-panel">
        <div className="app-header-left">
          <div className="logo-icon">
            <Activity size={20} />
          </div>
          <h1>Aivoa CRM — HCP Interaction Portal</h1>
        </div>
        <div className="app-header-right">
          <button onClick={handleReseed} className="header-btn">
            <Database size={14} />
            <span>Reset/Seed DB</span>
          </button>
        </div>
      </header>

      {/* HCP Profile Panel */}
      <section>
        <HCPInsights />
      </section>

      {/* Split Log Screen (Chat vs Form) */}
      <section className="workspace-grid">
        <ChatCopilot />
        <InteractionForm />
      </section>

      {/* Interactions History Log table */}
      <section className="history-section glass-panel">
        <div className="history-header">
          <h3>
            {selectedHcp 
              ? `Recent Visit History — ${selectedHcp.name}` 
              : 'All Recent HCP Visits'}
          </h3>
          {loading && <RefreshCw className="animate-spin text-muted" size={16} />}
        </div>

        <div className="table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th className="col-date">Date</th>
                {!selectedHcp && <th>HCP Name</th>}
                <th className="col-channel">Channel</th>
                <th className="col-topics">Topics Discussed</th>
                <th className="col-notes">Notes Summary</th>
                <th className="col-action">Next Action Step</th>
                <th>Follow-up</th>
                <th className="col-edit">Edit</th>
              </tr>
            </thead>
            <tbody>
              {interactions.map((i) => (
                <tr key={i.id} className="fade-in">
                  <td className="col-date">{i.date}</td>
                  {!selectedHcp && (
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500 }}>
                        <User size={12} className="text-secondary" />
                        {getHcpName(i.hcp_id)}
                      </div>
                    </td>
                  )}
                  <td className="col-channel">
                    <span className="text-secondary">{i.channel}</span>
                  </td>
                  <td className="col-topics">
                    <span className="text-secondary" title={i.topics}>{i.topics}</span>
                  </td>
                  <td className="col-notes">
                    <span className="text-secondary" title={i.notes}>{i.notes}</span>
                  </td>
                  <td className="col-action">
                    <span className="text-secondary">{i.next_step || '—'}</span>
                  </td>
                  <td>
                    {i.follow_up_date ? (
                      <span className="text-accent font-semibold">{i.follow_up_date}</span>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="col-edit">
                    <button onClick={() => handleEditClick(i)} className="table-edit-btn">
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
              {interactions.length === 0 && (
                <tr>
                  <td colSpan={selectedHcp ? 7 : 8} className="no-history-row">
                    No visit logs found for this context. Use the form or tell the AI copilot to log an interaction!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default App;
