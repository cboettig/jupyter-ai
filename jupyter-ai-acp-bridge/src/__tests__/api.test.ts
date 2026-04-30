jest.mock('@jupyterlab/services', () => ({
  ServerConnection: {
    makeSettings: () => ({ baseUrl: 'http://localhost:8888/' }),
    makeRequest: jest.fn()
  }
}));
jest.mock('@jupyterlab/coreutils', () => ({
  URLExt: { join: (...parts: string[]) => parts.join('/').replace(/\/+/g, '/') }
}));

import { ServerConnection } from '@jupyterlab/services';
import {
  listHarnesses,
  bindHarness,
  getState,
  setModel,
  listCommands
} from '../api';

const makeRequest = ServerConnection.makeRequest as jest.Mock;

beforeEach(() => makeRequest.mockReset());

function mockResponse(body: unknown, ok = true) {
  makeRequest.mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => body
  });
}

test('listHarnesses returns harnesses from response', async () => {
  mockResponse({ harnesses: [{ id: 'x', display_name: 'X', icon: 'x.svg' }] });
  const result = await listHarnesses();
  expect(result).toEqual([{ id: 'x', display_name: 'X', icon: 'x.svg' }]);
  expect(makeRequest).toHaveBeenCalledWith(
    expect.stringContaining('/jupyter-ai-acp-bridge/harnesses'),
    expect.any(Object),
    expect.any(Object)
  );
});

test('bindHarness POSTs harness_id', async () => {
  mockResponse({ harness_id: 'claude-code' });
  await bindHarness('chat-1', 'claude-code');
  const callArgs = makeRequest.mock.calls[0];
  expect(callArgs[0]).toContain('/chats/chat-1/bind');
  expect(callArgs[1].method).toBe('POST');
  expect(JSON.parse(callArgs[1].body)).toEqual({ harness_id: 'claude-code' });
});

test('getState returns state', async () => {
  mockResponse({ harness_id: 'claude-code', selected_model_id: 'sonnet' });
  const state = await getState('chat-1');
  expect(state.harness_id).toBe('claude-code');
});

test('setModel POSTs model_id', async () => {
  mockResponse({ ok: true });
  await setModel('chat-1', 'opus-4');
  const body = JSON.parse(makeRequest.mock.calls[0][1].body);
  expect(body).toEqual({ model_id: 'opus-4' });
});

test('listCommands returns commands array', async () => {
  mockResponse({ commands: [{ name: '/help', description: 'help' }] });
  const cmds = await listCommands('chat-1');
  expect(cmds).toEqual([{ name: '/help', description: 'help' }]);
});

test('non-OK response throws', async () => {
  mockResponse({ error: 'no' }, false);
  await expect(listHarnesses()).rejects.toThrow();
});
