import '@testing-library/jest-dom';
import * as React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('../api', () => ({
  getState: jest.fn(),
  setModel: jest.fn()
}));

import { ModelSelector } from '../components/ModelSelector';
import { getState } from '../api';

const getStateMock = getState as jest.Mock;

beforeEach(() => getStateMock.mockReset());

test('renders nothing when no available_models', async () => {
  getStateMock.mockResolvedValue({ harness_id: 'x', available_models: [] });
  const { container } = render(<ModelSelector chatId="chat-1" />);
  await new Promise(r => setTimeout(r, 0));
  expect(container.firstChild).toBeNull();
});

test('renders models when present', async () => {
  getStateMock.mockResolvedValue({
    harness_id: 'x',
    selected_model_id: 'sonnet-4',
    available_models: [
      { id: 'sonnet-4', name: 'Sonnet 4' },
      { id: 'opus-4', name: 'Opus 4' }
    ]
  });
  render(<ModelSelector chatId="chat-1" />);
  expect(await screen.findByText('Sonnet 4')).toBeInTheDocument();
  expect(await screen.findByText('Opus 4')).toBeInTheDocument();
});
