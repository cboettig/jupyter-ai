import * as React from 'react';
import { HarnessInfo } from '../types';

export interface HarnessBadgeProps {
  harness: HarnessInfo;
}

/**
 * Read-only label showing which ACP harness owns this chat. Sits in the
 * chat input toolbar alongside model/mode/config-options selectors but
 * deliberately styled as a flat label, not a button — it isn't
 * interactive (mid-thread harness switching isn't supported by ACP, and
 * the augmented `+ New chat` dialog covers selection at chat-creation
 * time).
 *
 * The icon attribute on `HarnessAdapter` is currently a hint string
 * (e.g. `"claude-code.svg"`) but we don't ship those assets — render
 * text only until we either bundle the icons or accept the
 * upstream `acp-client` ones.
 */
export const HarnessBadge: React.FC<HarnessBadgeProps> = ({ harness }) => (
  <span className="jp-acp-bridge-badge" title={harness.display_name}>
    {harness.display_name}
  </span>
);
