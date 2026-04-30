import * as React from 'react';
import { useEffect, useState } from 'react';

import { ChatBridgeState, SessionMode } from '../types';
import { getState, setMode } from '../api';

export interface ModeSelectorProps {
  chatId: string;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({ chatId }) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);

  useEffect(() => {
    getState(chatId).then(setStateLocal).catch(console.error);
  }, [chatId]);

  if (!state || !state.session_modes || state.session_modes.length === 0) {
    return null;
  }
  return (
    <select
      className="jp-acp-bridge-mode-selector"
      value={state.selected_mode_id ?? ''}
      onChange={async e => {
        const value = e.target.value;
        await setMode(chatId, value);
        setStateLocal({ ...state, selected_mode_id: value });
      }}
      title="Mode"
    >
      {state.session_modes.map((m: SessionMode) => (
        <option key={m.id} value={m.id}>
          {m.name}
        </option>
      ))}
    </select>
  );
};
