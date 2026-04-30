import * as React from 'react';
import { useEffect, useRef, useState } from 'react';

import { HarnessInfo } from '../types';
import { listHarnesses, bindHarness } from '../api';

export interface HarnessPickerProps {
  chatId: string;
  onBound: (harnessId: string) => void;
}

/**
 * Single-button dropdown that lets the user pick which ACP harness to bind to
 * the current chat. Modeled on Zed's "agent picker" — one button collapses
 * to a popover, click an item to bind. The popover dismisses on click-outside
 * or after a successful bind.
 */
export const HarnessPicker: React.FC<HarnessPickerProps> = ({
  chatId,
  onBound
}) => {
  const [harnesses, setHarnesses] = useState<HarnessInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listHarnesses().then(setHarnesses).catch(console.error);
  }, []);

  // Close on outside click while open. The handler runs on mousedown so a
  // click that lands on a menu item still fires its onClick before the menu
  // closes.
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
    try {
      await bindHarness(chatId, id);
      onBound(id);
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="jp-acp-bridge-picker" ref={containerRef}>
      <button
        type="button"
        className="jp-acp-bridge-picker-toggle"
        onClick={() => setOpen(o => !o)}
        disabled={busy}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        Pick agent ▾
      </button>
      {open && (
        <ul role="menu" className="jp-acp-bridge-picker-menu">
          {harnesses.length === 0 ? (
            <li className="jp-acp-bridge-picker-empty">Loading agents…</li>
          ) : (
            harnesses.map(h => (
              <li
                key={h.id}
                role="menuitem"
                tabIndex={0}
                className="jp-acp-bridge-picker-item"
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
