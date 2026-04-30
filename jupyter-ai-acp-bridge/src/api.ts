import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';
import {
  HarnessInfo,
  ChatBridgeState,
  AvailableCommand
} from './types';

const NAMESPACE = 'jupyter-ai-acp-bridge';

function url(path: string): string {
  const settings = ServerConnection.makeSettings();
  return URLExt.join(settings.baseUrl, NAMESPACE, path);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const settings = ServerConnection.makeSettings();
  const response = await ServerConnection.makeRequest(
    url(path),
    init ?? {},
    settings
  );
  if (!response.ok) {
    throw new Error(`Bridge request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listHarnesses(): Promise<HarnessInfo[]> {
  const data = await request<{ harnesses: HarnessInfo[] }>('harnesses');
  return data.harnesses;
}

export async function bindHarness(
  chatId: string,
  harnessId: string
): Promise<{ harness_id: string }> {
  return request(`chats/${chatId}/bind`, {
    method: 'POST',
    body: JSON.stringify({ harness_id: harnessId })
  });
}

export async function getState(chatId: string): Promise<ChatBridgeState> {
  return request<ChatBridgeState>(`chats/${chatId}/state`);
}

export async function setModel(
  chatId: string,
  modelId: string
): Promise<void> {
  await request(`chats/${chatId}/model`, {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId })
  });
}

export async function setMode(chatId: string, modeId: string): Promise<void> {
  await request(`chats/${chatId}/mode`, {
    method: 'POST',
    body: JSON.stringify({ mode_id: modeId })
  });
}

export async function setConfigOption(
  chatId: string,
  optionId: string,
  value: unknown
): Promise<void> {
  await request(`chats/${chatId}/config-option`, {
    method: 'POST',
    body: JSON.stringify({ option_id: optionId, value })
  });
}

export async function listCommands(
  chatId: string
): Promise<AvailableCommand[]> {
  const data = await request<{ commands: AvailableCommand[] }>(
    `chats/${chatId}/available-commands`
  );
  return data.commands;
}
