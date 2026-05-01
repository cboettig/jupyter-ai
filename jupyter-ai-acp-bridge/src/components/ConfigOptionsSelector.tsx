import * as React from 'react';
import { useEffect, useState } from 'react';

import { ChatBridgeState, ConfigOption } from '../types';
import { getState, setConfigOption } from '../api';

export interface ConfigOptionsSelectorProps {
  chatId: string;
}

/**
 * Renders any agent-advertised config options OTHER than the ones with
 * `category: 'model'` or `category: 'mode'`. Those two categories are
 * mirrored by `available_models` / `session_modes` and rendered by the
 * dedicated ModelSelector / ModeSelector — surfacing them again here
 * would double-display them.
 *
 * `claude-agent-acp` actually advertises both forms (dedicated fields
 * AND duplicated config_options). Zed's `config_state()` picks one or
 * the other; we pick the dedicated fields and skip the duplicates here.
 */
export const ConfigOptionsSelector: React.FC<ConfigOptionsSelectorProps> = ({
  chatId
}) => {
  const [state, setStateLocal] = useState<ChatBridgeState | null>(null);

  useEffect(() => {
    getState(chatId).then(setStateLocal).catch(console.error);
  }, [chatId]);

  if (!state || !state.config_options) {
    return null;
  }
  const visible = state.config_options.filter(
    o => o.category !== 'model' && o.category !== 'mode'
  );
  if (visible.length === 0) {
    return null;
  }

  const updateLocal = (id: string, value: unknown): void => {
    setStateLocal({
      ...state,
      config_options: (state.config_options ?? []).map(o =>
        o.id === id ? { ...o, value } : o
      )
    });
  };

  return (
    <>
      {visible.map(o => (
        <ConfigOptionControl
          key={o.id}
          chatId={chatId}
          option={o}
          onChange={value => updateLocal(o.id, value)}
        />
      ))}
    </>
  );
};

interface ConfigOptionControlProps {
  chatId: string;
  option: ConfigOption;
  onChange: (value: unknown) => void;
}

const ConfigOptionControl: React.FC<ConfigOptionControlProps> = ({
  chatId,
  option,
  onChange
}) => {
  if (option.kind === 'boolean') {
    return (
      <label className="jp-acp-bridge-config-bool" title={option.name}>
        <input
          type="checkbox"
          checked={Boolean(option.value)}
          onChange={async e => {
            const value = e.target.checked;
            await setConfigOption(chatId, option.id, value);
            onChange(value);
          }}
        />
        {option.name}
      </label>
    );
  }
  // Default to a select for `kind === 'select'` (and unknown kinds with
  // a non-empty `options` list).
  if (option.options && option.options.length > 0) {
    return (
      <select
        className="jp-acp-bridge-config-select"
        value={String(option.value ?? '')}
        title={option.name}
        onChange={async e => {
          const value = e.target.value;
          await setConfigOption(chatId, option.id, value);
          onChange(value);
        }}
      >
        {option.options.map(c => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    );
  }
  // Free-text fallback.
  return (
    <label className="jp-acp-bridge-config-text" title={option.name}>
      {option.name}
      <input
        type="text"
        defaultValue={String(option.value ?? '')}
        onBlur={async e => {
          const value = e.target.value;
          await setConfigOption(chatId, option.id, value);
          onChange(value);
        }}
      />
    </label>
  );
};
