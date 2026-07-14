import { configureStore, createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE_URL = 'http://localhost:8000/api';

// --- Async Thunks ---

export const fetchHCPs = createAsyncThunk('hcps/fetchHCPs', async (search = '') => {
  const url = search ? `${API_BASE_URL}/hcps?search=${encodeURIComponent(search)}` : `${API_BASE_URL}/hcps`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch HCPs');
  return await response.json();
});

export const fetchInteractions = createAsyncThunk('interactions/fetchInteractions', async (hcpId = null) => {
  const url = hcpId ? `${API_BASE_URL}/interactions?hcp_id=${hcpId}` : `${API_BASE_URL}/interactions`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch interactions');
  return await response.json();
});

export const logNewInteraction = createAsyncThunk('interactions/logNewInteraction', async (interactionData) => {
  const response = await fetch(`${API_BASE_URL}/interactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(interactionData),
  });
  if (!response.ok) {
    const errData = await response.json();
    throw new Error(errData.detail || 'Failed to log interaction');
  }
  return await response.json();
});

export const updateExistingInteraction = createAsyncThunk('interactions/updateExistingInteraction', async ({ id, data }) => {
  const response = await fetch(`${API_BASE_URL}/interactions/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errData = await response.json();
    throw new Error(errData.detail || 'Failed to update interaction');
  }
  return await response.json();
});

export const sendChatMessage = createAsyncThunk('chat/sendChatMessage', async ({ message, history, hcpId }, { dispatch }) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, hcp_id: hcpId }),
  });
  if (!response.ok) throw new Error('Failed to chat with agent');
  const data = await response.json();
  
  // If the agent returned extracted data, we automatically populate the active form in Redux!
  if (data.extracted_data) {
    dispatch(populateActiveForm(data.extracted_data));
  }
  
  // If the agent successfully logged a new interaction or updated one via tools, we re-fetch history
  const containsLogTool = data.tools_triggered?.some(t => t.name === 'log_interaction' || t.name === 'edit_interaction' || t.name === 'schedule_followup');
  if (containsLogTool) {
    setTimeout(() => {
      dispatch(fetchInteractions(hcpId));
      dispatch(fetchHCPs()); // refresh last interaction date
    }, 500);
  }
  
  return data;
});

export const resetAndSeedDatabase = createAsyncThunk('hcps/resetAndSeedDatabase', async (_, { dispatch }) => {
  const response = await fetch(`${API_BASE_URL}/seed`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to reset and seed database');
  const data = await response.json();
  dispatch(fetchHCPs());
  dispatch(fetchInteractions());
  return data;
});

// --- Slices ---

const hcpSlice = createSlice({
  name: 'hcps',
  initialState: {
    list: [],
    selectedHcp: null,
    loading: false,
    error: null,
  },
  reducers: {
    selectHcp: (state, action) => {
      state.selectedHcp = action.payload;
    },
    clearSelectedHcp: (state) => {
      state.selectedHcp = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHCPs.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchHCPs.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
        // Keep selected HCP updated if it's already selected
        if (state.selectedHcp) {
          const updated = action.payload.find(h => h.id === state.selectedHcp.id);
          if (updated) state.selectedHcp = updated;
        }
      })
      .addCase(fetchHCPs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  }
});

const defaultFormState = {
  hcp_id: '',
  date: new Date().toISOString().split('T')[0],
  channel: 'In-Person',
  topics: '',
  sentiment: 'Neutral',
  notes: '',
  follow_up_date: '',
  next_step: '',
};

const interactionSlice = createSlice({
  name: 'interactions',
  initialState: {
    list: [],
    activeForm: defaultFormState,
    editingInteractionId: null, // If set, we are editing this log
    loading: false,
    saving: false,
    error: null,
    // Store fields highlighted by AI extraction to trigger flash animations
    extractedFields: [],
  },
  reducers: {
    updateFormField: (state, action) => {
      const { field, value } = action.payload;
      state.activeForm[field] = value;
    },
    populateActiveForm: (state, action) => {
      const data = action.payload;
      const fieldsToHighlight = [];
      
      // Update form fields with keys matching form state
      Object.keys(defaultFormState).forEach(field => {
        if (data[field] !== undefined && data[field] !== null) {
          // Map lists/comma strings safely
          state.activeForm[field] = data[field];
          fieldsToHighlight.push(field);
        }
      });
      state.extractedFields = fieldsToHighlight;
    },
    clearFormHighlight: (state) => {
      state.extractedFields = [];
    },
    resetForm: (state) => {
      state.activeForm = {
        ...defaultFormState,
        hcp_id: state.activeForm.hcp_id || '', // keep current HCP ID
      };
      state.editingInteractionId = null;
      state.extractedFields = [];
    },
    startEditingInteraction: (state, action) => {
      const interaction = action.payload;
      state.editingInteractionId = interaction.id;
      state.activeForm = {
        hcp_id: interaction.hcp_id,
        date: interaction.date,
        channel: interaction.channel,
        topics: interaction.topics,
        sentiment: interaction.sentiment,
        notes: interaction.notes,
        follow_up_date: interaction.follow_up_date || '',
        next_step: interaction.next_step || '',
      };
      state.extractedFields = [];
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch interactions
      .addCase(fetchInteractions.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      // Log interaction
      .addCase(logNewInteraction.pending, (state) => {
        state.saving = true;
      })
      .addCase(logNewInteraction.fulfilled, (state, action) => {
        state.saving = false;
        state.list.unshift(action.payload);
        state.activeForm = { ...defaultFormState, hcp_id: state.activeForm.hcp_id };
        state.extractedFields = [];
      })
      .addCase(logNewInteraction.rejected, (state, action) => {
        state.saving = false;
        state.error = action.error.message;
      })
      // Update interaction
      .addCase(updateExistingInteraction.pending, (state) => {
        state.saving = true;
      })
      .addCase(updateExistingInteraction.fulfilled, (state, action) => {
        state.saving = false;
        state.editingInteractionId = null;
        const index = state.list.findIndex(i => i.id === action.payload.id);
        if (index !== -1) {
          state.list[index] = action.payload;
        }
        state.activeForm = { ...defaultFormState, hcp_id: state.activeForm.hcp_id };
        state.extractedFields = [];
      })
      .addCase(updateExistingInteraction.rejected, (state, action) => {
        state.saving = false;
        state.error = action.error.message;
      });
  }
});

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        role: 'assistant',
        content: 'Welcome to your AI CRM Copilot. Select a Healthcare Professional (HCP) on the left and tell me about your interaction (e.g. "Called Dr. Sarah Jenkins, sentiment was positive, discussed trial results") or ask me to retrieve history.',
      }
    ],
    lastToolsTriggered: [],
    loading: false,
    error: null,
  },
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload);
    },
    clearChat: (state) => {
      state.messages = [
        {
          role: 'assistant',
          content: 'Chat history cleared. How can I help you manage your HCP interactions today?',
        }
      ];
      state.lastToolsTriggered = [];
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state, action) => {
        state.loading = true;
        // Optimistically add user message if not already added
        const userMsg = action.meta.arg.message;
        if (state.messages[state.messages.length - 1].content !== userMsg) {
          state.messages.push({ role: 'user', content: userMsg });
        }
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.loading = false;
        const { reply, tools_triggered } = action.payload;
        state.messages.push({ role: 'assistant', content: reply, tool_calls: tools_triggered });
        state.lastToolsTriggered = tools_triggered || [];
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
        state.messages.push({ 
          role: 'assistant', 
          content: `Sorry, I encountered an error communicating with the agent: ${action.error.message}` 
        });
      });
  }
});

// Export Reducers
export const { selectHcp, clearSelectedHcp } = hcpSlice.actions;
export const { updateFormField, populateActiveForm, clearFormHighlight, resetForm, startEditingInteraction } = interactionSlice.actions;
export const { addMessage, clearChat } = chatSlice.actions;

// Configure Store
export const store = configureStore({
  reducer: {
    hcps: hcpSlice.reducer,
    interactions: interactionSlice.reducer,
    chat: chatSlice.reducer,
  },
});
