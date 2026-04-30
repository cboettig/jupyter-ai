import { JupyterFrontEnd } from '@jupyterlab/application';
import { ILauncher } from '@jupyterlab/launcher';

import { listHarnesses, bindHarness } from './api';

const NEW_CHAT_COMMAND = 'acp-bridge:new-chat';

/**
 * Polls the bind endpoint with backoff. The chat-init observer fires
 * asynchronously after `jupyterlab-chat:createAndOpen` resolves, so the
 * first bind attempt can race ahead of the persona-manager registering
 * the new room. ~1.5s of backoff covers the cold-init path.
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

export async function registerLauncherCards(
  app: JupyterFrontEnd,
  launcher: ILauncher
): Promise<void> {
  // Define the shared command once. Each card invokes it with a different
  // harness_id arg.
  if (!app.commands.hasCommand(NEW_CHAT_COMMAND)) {
    app.commands.addCommand(NEW_CHAT_COMMAND, {
      label: args => `New ${args.harness_name as string} chat`,
      execute: async args => {
        const harnessId = args.harness_id as string;
        const chatPath = (await app.commands.execute(
          'jupyterlab-chat:createAndOpen'
        )) as string | undefined;
        if (!chatPath) {
          console.error(
            'jupyterlab-chat:createAndOpen returned no path; cannot bind'
          );
          return;
        }
        try {
          await bindWithRetry(chatPath, harnessId);
        } catch (err) {
          console.error(
            `Failed to bind chat ${chatPath} to ${harnessId}:`,
            err
          );
        }
      }
    });
  }

  const harnesses = await listHarnesses();
  harnesses.forEach((h, i) => {
    launcher.add({
      command: NEW_CHAT_COMMAND,
      args: { harness_id: h.id, harness_name: h.display_name },
      category: 'ACP agents',
      rank: i
    });
  });
}
