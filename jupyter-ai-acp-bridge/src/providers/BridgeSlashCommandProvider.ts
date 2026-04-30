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
    return commands
      .filter(c => c.name.startsWith(word))
      .map(c => ({
        name: c.name,
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
