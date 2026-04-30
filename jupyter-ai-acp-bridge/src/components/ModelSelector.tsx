import * as React from 'react';
import { useEffect, useState } from 'react';

import { ChatBridgeState, ModelInfo } from '../types';
import { getState, setModel } from '../api';

export interface ModelSelectorProps {
  chatId: string;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({ chatId }) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);

  useEffect(() => {
    getState(chatId).then(setStateLocal).catch(console.error);
  }, [chatId]);

  if (!state || !state.available_models || state.available_models.length === 0) {
    return null;
  }
  return (
    <select
      className="jp-acp-bridge-model-selector"
      value={state.selected_model_id ?? ''}
      onChange={async e => {
        const value = e.target.value;
        await setModel(chatId, value);
        setStateLocal({ ...state, selected_model_id: value });
      }}
      title="Model"
    >
      {state.available_models.map((m: ModelInfo) => (
        <option key={m.id} value={m.id}>
          {m.name}
        </option>
      ))}
    </select>
  );
};
