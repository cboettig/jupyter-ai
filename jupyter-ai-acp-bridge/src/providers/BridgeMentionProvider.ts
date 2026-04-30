import { IChatCommandProvider, IInputModel, ChatCommand } from '@jupyter/chat';
import { Contents } from '@jupyterlab/services';

const PROVIDER_ID = '@jupyter-ai/acp-bridge:mention-provider';

export class BridgeMentionProvider implements IChatCommandProvider {
  public id = PROVIDER_ID;
  _regex = /@([\w./-]*)/g;

  constructor(private contents: Contents.IManager) {}

  async listCommandCompletions(
    inputModel: IInputModel
  ): Promise<ChatCommand[]> {
    const word = inputModel.currentWord || '';
    if (!word.startsWith('@')) {
      return [];
    }
    const fragment = word.slice(1);
    if (!fragment) {
      return [];
    }
    try {
      const listing = await this.contents.get('', { content: true });
      if (!listing.content) {
        return [];
      }
      const items = (listing.content as Contents.IModel[])
        .filter(m => m.name.startsWith(fragment))
        .slice(0, 10);
      return items.map(m => ({
        name: `@${m.name}`,
        providerId: this.id,
        description: m.path,
        spaceOnAccept: true
      }));
    } catch {
      return [];
    }
  }

  async onSubmit(_inputModel: IInputModel): Promise<void> {
    return;
  }
}
