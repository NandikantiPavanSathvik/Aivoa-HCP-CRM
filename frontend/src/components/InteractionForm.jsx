import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateFormField, logNewInteraction, updateExistingInteraction, resetForm, clearFormHighlight } from '../store';
import { Check, ClipboardList, AlertCircle, RefreshCw, X } from 'lucide-react';

const InteractionForm = () => {
  const dispatch = useDispatch();
  const { selectedHcp } = useSelector((state) => state.hcps);
  const { activeForm, editingInteractionId, saving, error, extractedFields } = useSelector((state) => state.interactions);

  // Set the selected HCP ID in the form when selectedHcp changes
  useEffect(() => {
    if (selectedHcp) {
      dispatch(updateFormField({ field: 'hcp_id', value: selectedHcp.id }));
    } else {
      dispatch(updateFormField({ field: 'hcp_id', value: '' }));
    }
  }, [selectedHcp, dispatch]);

  // Clear AI extraction highlights after 3 seconds
  useEffect(() => {
    if (extractedFields.length > 0) {
      const timer = setTimeout(() => {
        dispatch(clearFormHighlight());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [extractedFields, dispatch]);

  const handleFieldChange = (field, value) => {
    dispatch(updateFormField({ field, value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!activeForm.hcp_id) return;

    if (editingInteractionId) {
      dispatch(updateExistingInteraction({
        id: editingInteractionId,
        data: activeForm
      }));
    } else {
      dispatch(logNewInteraction(activeForm));
    }
  };

  const handleCancel = () => {
    dispatch(resetForm());
  };

  // Helper to check if field is extracted
  const isExtracted = (fieldName) => extractedFields.includes(fieldName) ? 'extracted-pulse' : '';

  return (
    <div className="interaction-form glass-panel">
      <div className="form-header">
        <ClipboardList size={18} className="text-accent" />
        <h3>{editingInteractionId ? `Edit Interaction #${editingInteractionId}` : 'Log Interaction Form'}</h3>
        {editingInteractionId && (
          <button onClick={handleCancel} className="cancel-edit-btn" title="Cancel Edit">
            <X size={14} />
          </button>
        )}
      </div>

      {!activeForm.hcp_id ? (
        <div className="form-warning">
          <AlertCircle size={20} className="text-warning" />
          <span>Please select an HCP from the list to enable logging.</span>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="form-grid">
          {/* Date */}
          <div className="input-group">
            <label>Interaction Date</label>
            <input
              type="date"
              value={activeForm.date}
              onChange={(e) => handleFieldChange('date', e.target.value)}
              className={`form-input ${isExtracted('date')}`}
              required
            />
          </div>

          {/* Channel */}
          <div className="input-group">
            <label>Channel</label>
            <select
              value={activeForm.channel}
              onChange={(e) => handleFieldChange('channel', e.target.value)}
              className={`form-input ${isExtracted('channel')}`}
              required
            >
              <option value="In-Person">In-Person Visit</option>
              <option value="Video Call">Video Call</option>
              <option value="Phone">Phone Call</option>
              <option value="Email">Email Exchange</option>
            </select>
          </div>

          {/* Topics */}
          <div className="input-group full-width">
            <label>Discussion Topics / Products</label>
            <input
              type="text"
              placeholder="e.g. CardioSphere-10mg, Clinical Trial, Safety profile"
              value={activeForm.topics}
              onChange={(e) => handleFieldChange('topics', e.target.value)}
              className={`form-input ${isExtracted('topics')}`}
              required
            />
          </div>

          {/* Sentiment */}
          <div className="input-group full-width">
            <label>HCP Sentiment Indicator</label>
            <div className="sentiment-radio-group">
              {['Positive', 'Neutral', 'Negative'].map((s) => (
                <label 
                  key={s} 
                  className={`sentiment-label ${s.toLowerCase()} ${activeForm.sentiment === s ? 'active' : ''} ${isExtracted('sentiment')}`}
                >
                  <input
                    type="radio"
                    name="sentiment"
                    value={s}
                    checked={activeForm.sentiment === s}
                    onChange={() => handleFieldChange('sentiment', s)}
                    className="hidden-radio"
                  />
                  <span>{s}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="input-group full-width">
            <label>Visit Summary / Discussion Notes</label>
            <textarea
              placeholder="Enter details of the conversation, concerns raised, or brochure requests..."
              value={activeForm.notes}
              onChange={(e) => handleFieldChange('notes', e.target.value)}
              className={`form-input text-area ${isExtracted('notes')}`}
              rows={4}
              required
            />
          </div>

          {/* Follow-up Date */}
          <div className="input-group">
            <label>Follow-up Date (Optional)</label>
            <input
              type="date"
              value={activeForm.follow_up_date}
              onChange={(e) => handleFieldChange('follow_up_date', e.target.value)}
              className={`form-input ${isExtracted('follow_up_date')}`}
            />
          </div>

          {/* Next Step */}
          <div className="input-group">
            <label>Action / Next Step (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Send clinical trial PDF"
              value={activeForm.next_step}
              onChange={(e) => handleFieldChange('next_step', e.target.value)}
              className={`form-input ${isExtracted('next_step')}`}
            />
          </div>

          {error && (
            <div className="error-message full-width">
              <span>{error}</span>
            </div>
          )}

          {/* Submit Actions */}
          <div className="form-actions full-width">
            {editingInteractionId && (
              <button 
                type="button" 
                onClick={handleCancel} 
                className="btn btn-secondary"
                disabled={saving}
              >
                Cancel Edit
              </button>
            )}
            <button 
              type="submit" 
              className={`btn btn-primary ${saving ? 'loading' : ''}`}
              disabled={saving}
            >
              {saving ? (
                <>
                  <RefreshCw className="animate-spin" size={16} />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check size={16} />
                  <span>{editingInteractionId ? 'Update Log' : 'Save Interaction Log'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default InteractionForm;
