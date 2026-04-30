import * as React from 'react';
import { useEffect, useRef, useState } from 'react';

import { JupyterFrontEnd } from '@jupyterlab/application';

import { HarnessInfo } from '../types';
import { listHarnesses } from '../api';
import { newChatWithHarness } from '../newChat';

export interface AgentMenuProps {
  app: JupyterFrontEnd;
}

/**
 * Persistent top-bar dropdown — Zed's "+ New chat with <agent> ▾" pattern.
 * Click the button → menu of harnesses → click → creates a new chat bound
 * to that harness. Replaces the in-chat picker entirely; switching agents
 * always starts a fresh chat.
 */
export const AgentMenu: React.FC<AgentMenuProps> = ({ app }) => {
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listHarnesses().then(setHarnesses).catch(console.error);
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onDocMouseDown = (e: MouseEvent): void => {
      const node = containerRef.current;
      if (node && !node.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [open]);

  const handlePick = async (id: string): Promise<void> => {
    setBusy(true);
    setOpen(false);
    try {
      await newChatWithHarness(app, id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="jp-acp-bridge-agent-menu" ref={containerRef}>
      <button
        type="button"
        className="jp-acp-bridge-agent-menu-toggle"
        onClick={() => setOpen(o => !o)}
        disabled={busy}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Start a new chat with an ACP agent"
      >
        New agent chat ▾
      </button>
      {open && (
        <ul role="menu" className="jp-acp-bridge-agent-menu-list">
          {harnesses.length === 0 ? (
            <li className="jp-acp-bridge-agent-menu-empty">Loading agents…</li>
          ) : (
            harnesses.map(h => (
              <li
                key={h.id}
                role="menuitem"
                tabIndex={0}
                className="jp-acp-bridge-agent-menu-item"
                onClick={() => !busy && handlePick(h.id)}
                onKeyDown={e => {
                  if ((e.key === 'Enter' || e.key === ' ') && !busy) {
                    e.preventDefault();
                    handlePick(h.id);
                  }
                }}
              >
                <img src={h.icon} width={16} height={16} alt="" />
                <span>{h.display_name}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
};
