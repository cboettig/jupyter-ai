import { JupyterFrontEnd } from '@jupyterlab/application';

import { bindHarness } from './api';

/**
 * Polls the bind endpoint with backoff. The chat-init observer fires
 * asynchronously after the chat opens, so a fast first bind attempt can
 * race ahead of the persona-manager registering the new room. ~1.5s of
 * backoff covers the cold-init path.
 */
async function bindWithRetry(
  chatPath: string,
  harnessId: string,
  attempts = 6
): Promise<void> {
  for (let i = 0; i < attempts; i++) {
    try {
      await bindHarness(chatPath, harnessId);
      return;
    } catch (err) {
      if (i === attempts - 1) {
        throw err;
      }
      await new Promise(r => setTimeout(r, 100 * Math.pow(2, i)));
    }
  }
}

/**
 * Creates a new .chat file, opens it, and binds it to the requested
 * harness. The two-step `createChat` → `openChat` is intentional —
 * `jupyterlab-chat:createAndOpen` returns the opened widget, not the
 * file path, so we'd lose the binding target.
 */
export async function newChatWithHarness(
  app: JupyterFrontEnd,
  harnessId: string
): Promise<string | undefined> {
  const path = (await app.commands.execute('jupyterlab-chat:createChat')) as
    | string
    | undefined
    | null;
  if (!path) {
    // User cancelled the name dialog.
    return undefined;
  }
  // Open it. `openChat` is preferred (jupyterlab-chat does extra setup);
  // fall through to docmanager:open if it's not registered.
  if (app.commands.hasCommand('jupyterlab-chat:openChat')) {
    await app.commands.execute('jupyterlab-chat:openChat', { filepath: path });
  } else {
    await app.commands.execute('docmanager:open', { path, factory: 'Chat' });
  }
  try {
    await bindWithRetry(path, harnessId);
  } catch (err) {
    console.error(`Failed to bind chat ${path} to ${harnessId}:`, err);
  }
  return path;
}
