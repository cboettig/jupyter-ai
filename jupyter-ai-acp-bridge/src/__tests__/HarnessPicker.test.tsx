import '@testing-library/jest-dom';
import * as React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

jest.mock('../api', () => ({
  listHarnesses: jest.fn().mockResolvedValue([
    { id: 'claude-code', display_name: 'Claude Code', icon: 'x.svg' },
    { id: 'opencode', display_name: 'OpenCode', icon: 'y.svg' }
  ]),
  bindHarness: jest.fn().mockResolvedValue({ harness_id: 'claude-code' })
}));

import { HarnessPicker } from '../components/HarnessPicker';
import { listHarnesses, bindHarness } from '../api';

test('renders harness buttons after fetch', async () => {
  render(<HarnessPicker chatId="chat-1" onBound={() => undefined} />);
  expect(await screen.findByText('Claude Code')).toBeInTheDocument();
  expect(await screen.findByText('OpenCode')).toBeInTheDocument();
});

test('clicking a button calls bindHarness and onBound', async () => {
  const onBound = jest.fn();
  render(<HarnessPicker chatId="chat-1" onBound={onBound} />);
  const btn = await screen.findByText('Claude Code');
  fireEvent.click(btn);
  await waitFor(() => {
    expect(bindHarness).toHaveBeenCalledWith('chat-1', 'claude-code');
    expect(onBound).toHaveBeenCalledWith('claude-code');
  });
});
