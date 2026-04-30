import { JupyterFrontEnd } from '@jupyterlab/application';

import { HarnessInfo } from './types';
import { listHarnesses } from './api';
import { bindWithRetry } from './newChat';
import { showNewChatDialog } from './newChatDialog';

const CREATE_CHAT_COMMAND = 'jupyterlab-chat:create';

/**
 * Replace `jupyterlab-chat:create` with a wrapper that asks for both a
 * name AND a harness, then forwards to the original command (passing
 * `name` so its built-in name dialog is skipped) and finally binds the
 * created chat to the chosen harness.
 *
 * The override hits Lumino's private `_commands` map — there's no public
 * way to remove a command we didn't add. Stable as of @lumino/commands
 * 2.x; if a future version renames the field this falls back gracefully
 * (logs a warning, leaves the original command in place).
 */
export async function augmentChatCreateCommand(
  app: JupyterFrontEnd
): Promise<void> {
  // `_commands` is Lumino's private Map<id, ICommand> on the registry.
  // We `as any` past the private-field type ban; behavior verified
  // against @lumino/commands 2.3.x source.
  const reg: any = app.commands;
  const internal: Map<string, any> | undefined = reg._commands;
  if (!(internal instanceof Map)) {
    console.warn(
      '[acp-bridge] CommandRegistry._commands not a Map; cannot augment ' +
        `${CREATE_CHAT_COMMAND}. Standard chat-create flow will not ask ` +
        'for a harness.'
    );
    return;
  }
  const original = internal.get(CREATE_CHAT_COMMAND);
  if (!original) {
    console.warn(
      `[acp-bridge] ${CREATE_CHAT_COMMAND} not registered; chat extension ` +
        'may not have activated yet, or its command IDs changed.'
    );
    return;
  }

  let harnesses: HarnessInfo[];
  try {
    harnesses = await listHarnesses();
  } catch (err) {
    console.error('[acp-bridge] could not list harnesses:', err);
    return;
  }
  if (harnesses.length === 0) {
    return;
  }

  // Swap our wrapper in. We keep all of `original`'s metadata (label,
  // caption, icon, etc.) so any UI that referenced the command keeps
  // looking the same; only `execute` changes.
  internal.delete(CREATE_CHAT_COMMAND);
  app.commands.addCommand(CREATE_CHAT_COMMAND, {
    label: original.label,
    caption: original.caption,
    icon: original.icon,
    execute: async (args: any) => {
      // If a name is passed in, the caller is driving programmatically
      // (e.g. tests, or our own future flows) — let the original do its
      // thing without our dialog.
      if (args?.name) {
        return original.execute.call(reg, args);
      }
      const choice = await showNewChatDialog(harnesses);
      if (!choice) {
        // User cancelled — return null so callers like createAndOpen
        // bail out cleanly (matching the original's "user cancelled
        // the name dialog" behavior).
        return null;
      }
      const path = (await original.execute.call(reg, {
        ...(args ?? {}),
        name: choice.name
      })) as string | null | undefined;
      if (path && choice.harnessId) {
        bindWithRetry(path, choice.harnessId).catch(err =>
          console.error(`[acp-bridge] bind ${path} failed:`, err)
        );
      }
      return path;
    }
  });
}
