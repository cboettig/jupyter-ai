import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo } from '../types';
import { listHarnesses, bindHarness } from '../api';

export interface HarnessPickerProps {
  chatId: string;
  onBound: (harnessId: string) => void;
}

export const HarnessPicker: React.FC<HarnessPickerProps> = ({
  chatId,
  onBound
}) => {
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listHarnesses().then(setHarnesses).catch(console.error);
  }, []);

  const handlePick = async (id: string): Promise<void> => {
    setBusy(true);
    try {
      await bindHarness(chatId, id);
      onBound(id);
    } finally {
      setBusy(false);
    }
  };

  if (harnesses.length === 0) {
    return <div className="jp-acp-bridge-picker-empty">Loading agents…</div>;
  }

  return (
    <div className="jp-acp-bridge-picker">
      <span>Choose an agent:</span>
      {harnesses.map(h => (
        <button
          key={h.id}
          disabled={busy}
          onClick={() => handlePick(h.id)}
          className="jp-acp-bridge-picker-button"
        >
          {h.display_name}
        </button>
      ))}
    </div>
  );
};
