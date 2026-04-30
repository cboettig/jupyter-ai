import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo, ChatBridgeState } from '../types';
import { getState, listHarnesses } from '../api';
import { HarnessPicker } from './HarnessPicker';
import { HarnessBadge } from './HarnessBadge';

export interface HarnessHeaderProps {
  chatId: string;
}

export const HarnessHeader: React.FC<HarnessHeaderProps> = ({ chatId }) => {
  const [state, setState] = useState<ChatBridgeState | null>(null);
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);

  useEffect(() => {
    Promise.all([getState(chatId), listHarnesses()])
      .then(([s, h]) => {
        setState(s);
        setHarnesses(h);
      })
      .catch(console.error);
  }, [chatId]);

  if (state === null) {
    return null;
  }
  if (state.harness_id === null) {
    return (
      <HarnessPicker
        chatId={chatId}
        onBound={(id: string) =>
          setState({ ...state, harness_id: id })
        }
      />
    );
  }
  const matched = harnesses.find(h => h.id === state.harness_id);
  return matched ? <HarnessBadge harness={matched} /> : null;
};
