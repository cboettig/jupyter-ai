import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo, ChatBridgeState } from '../types';
import { getState, listHarnesses } from '../api';
import { HarnessBadge } from './HarnessBadge';

export interface HarnessHeaderProps {
  chatId: string;
}

/**
 * In-chat harness display. Read-only — selecting a harness happens at
 * chat-creation time via the launcher cards (see `src/launcher.ts`), not
 * here. Bound chats show the agent badge; unbound chats (legacy or
 * created via the standard `Chat` launcher card) show a hint pointing
 * to the launcher.
 */
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
      <span className="jp-acp-bridge-unbound-hint" title="No agent bound">
        No agent — start a new chat from the Launcher.
      </span>
    );
  }
  const matched = harnesses.find(h => h.id === state.harness_id);
  return matched ? <HarnessBadge harness={matched} /> : null;
};
