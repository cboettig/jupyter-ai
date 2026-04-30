import * as React from 'react';
import { useEffect, useState } from 'react';

import { ChatBridgeState, ConfigOption } from '../types';
import { getState, setConfigOption } from '../api';

export interface ConfigOptionsSelectorProps {
  chatId: string;
}

export const ConfigOptionsSelector: React.FC<ConfigOptionsSelectorProps> = ({
  chatId
}) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);

  useEffect(() => {
    getState(chatId).then(setStateLocal).catch(console.error);
  }, [chatId]);

  if (!state || !state.config_options || state.config_options.length === 0) {
    return null;
  }
  return (
    <details className="jp-acp-bridge-config-options">
      <summary>Options</summary>
      {state.config_options.map((o: ConfigOption) => (
        <label key={o.id} className="jp-acp-bridge-config-option">
          {o.name}
          <input
            type="text"
            defaultValue={String(o.value ?? '')}
            onBlur={e => setConfigOption(chatId, o.id, e.target.value)}
          />
        </label>
      ))}
    </details>
  );
};
