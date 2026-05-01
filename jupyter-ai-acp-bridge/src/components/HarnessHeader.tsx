import * as React from 'react';
import { useEffect, useState } from 'react';

import { HarnessInfo, ChatBridgeState } from '../types';
import { getState, listHarnesses } from '../api';
import { HarnessBadge } from './HarnessBadge';
import { ModelSelector } from './ModelSelector';
import { ModeSelector } from './ModeSelector';
import { ConfigOptionsSelector } from './ConfigOptionsSelector';

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
  if (!matched) {
    return null;
  }
  // Zed-style row: model → mode → config-options → harness label.
  // The badge sits at the end as a read-only identity tag, distinct
  // from the peer dropdowns so users don't try to click it (mid-thread
  // harness switching isn't supported). Each child self-fetches state
  // and renders nothing when the agent doesn't advertise its
  // capability — a harness that exposes only models shows just model
  // + label, an "everything" harness shows all four.
  return (
    <span className="jp-acp-bridge-bound-row">
      <ModelSelector chatId={chatId} />
      <ModeSelector chatId={chatId} />
      <ConfigOptionsSelector chatId={chatId} />
      <HarnessBadge harness={matched} />
    </span>
  );
};
