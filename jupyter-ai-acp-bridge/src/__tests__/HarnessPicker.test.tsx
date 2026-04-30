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
import { bindHarness } from '../api';

test('toggle is closed by default and opens on click', async () => {
  render(<HarnessPicker chatId="chat-1" onBound={() => undefined} />);
  // Wait for the harness list fetch to settle (avoids "act()" warnings).
  await waitFor(() => expect(screen.getByText('Pick agent ▾')).toBeInTheDocument());
  expect(screen.queryByText('Claude Code')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Pick agent ▾'));
  expect(await screen.findByText('Claude Code')).toBeInTheDocument();
  expect(await screen.findByText('OpenCode')).toBeInTheDocument();
});

test('clicking a menu item calls bindHarness and onBound, then closes', async () => {
  const onBound = jest.fn();
  render(<HarnessPicker chatId="chat-1" onBound={onBound} />);
  fireEvent.click(await screen.findByText('Pick agent ▾'));
  fireEvent.click(await screen.findByText('Claude Code'));
  await waitFor(() => {
    expect(bindHarness).toHaveBeenCalledWith('chat-1', 'claude-code');
    expect(onBound).toHaveBeenCalledWith('claude-code');
  });
  // After bind the popover closes — list items should be gone.
  await waitFor(() => {
    expect(screen.queryByText('Claude Code')).not.toBeInTheDocument();
  });
});

test('clicking outside closes the popover', async () => {
  render(
    <div>
      <span data-testid="outside">outside</span>
      <HarnessPicker chatId="chat-1" onBound={() => undefined} />
    </div>
  );
  fireEvent.click(await screen.findByText('Pick agent ▾'));
  await screen.findByText('Claude Code');
  fireEvent.mouseDown(screen.getByTestId('outside'));
  await waitFor(() => {
    expect(screen.queryByText('Claude Code')).not.toBeInTheDocument();
  });
});
