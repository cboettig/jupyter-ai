import * as React from 'react';
import { HarnessInfo } from '../types';

export interface HarnessBadgeProps {
  harness: HarnessInfo;
}

export const HarnessBadge: React.FC<HarnessBadgeProps> = ({ harness }) => (
  <div className="jp-acp-bridge-badge" title={harness.display_name}>
    <img src={harness.icon} width={16} height={16} alt="" />
    <span>{harness.display_name}</span>
  </div>
);
