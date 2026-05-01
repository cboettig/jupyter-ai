import { IChatCommandProvider, IInputModel, ChatCommand } from '@jupyter/chat';

import { listCommands } from '../api';

const PROVIDER_ID = '@jupyter-ai/acp-bridge:slash-command-provider';

export class BridgeSlashCommandProvider implements IChatCommandProvider {
  public id = PROVIDER_ID;
  _regex = /\/([\w-]*)/g;

  async listCommandCompletions(
    inputModel: IInputModel
  ): Promise<ChatCommand[]> {
    const word = inputModel.currentWord || '';
    if (!word.startsWith('/')) {
      return [];
    }
    if (!inputModel.chatContext) {
      return [];
    }
    const chatId = inputModel.chatContext.name;
    const commands = await listCommands(chatId);
    // ACP advertises command names without the leading slash (e.g.
    // `help`, `mode`); the user typed `word` *with* a leading `/`.
    // Match against the slash-stripped prefix and re-attach `/` in the
    // surfaced completion so the chat-input replaces `/he` with
    // `/help` rather than with `help`.
    const prefix = word.slice(1);
    return commands
      .filter(c => c.name.startsWith(prefix))
      .map(c => ({
        name: '/' + c.name,
        providerId: this.id,
        description: c.description,
        spaceOnAccept: true
      }));
  }

  async onSubmit(_inputModel: IInputModel): Promise<void> {
    // No-op: harness handles the slash command itself.
    return;
  }
}
