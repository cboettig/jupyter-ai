import { Dialog } from '@jupyterlab/apputils';
import { Widget } from '@lumino/widgets';

import { HarnessInfo } from './types';

export interface NewChatChoice {
  name: string;
  harnessId: string;
}

/**
 * Vanilla-DOM body for the augmented "Create a new chat" dialog. One form
 * with both name and agent fields so users pick the harness at creation
 * time instead of after the fact (the bridge can't rebind an existing
 * chat).
 */
class NewChatDialogBody extends Widget implements Dialog.IBodyWidget<NewChatChoice> {
  private readonly _nameInput: HTMLInputElement;
  private readonly _harnessSelect: HTMLSelectElement;

  constructor(harnesses: HarnessInfo[], defaultHarnessId?: string) {
    super();
    this.addClass('jp-acp-bridge-new-chat-body');

    const form = document.createElement('div');
    form.className = 'jp-acp-bridge-new-chat-form';

    this._nameInput = document.createElement('input');
    this._nameInput.type = 'text';
    this._nameInput.placeholder = 'untitled';
    this._nameInput.className = 'jp-mod-styled';

    this._harnessSelect = document.createElement('select');
    this._harnessSelect.className = 'jp-mod-styled';
    for (const h of harnesses) {
      const opt = document.createElement('option');
      opt.value = h.id;
      opt.textContent = h.display_name;
      this._harnessSelect.appendChild(opt);
    }
    if (defaultHarnessId) {
      this._harnessSelect.value = defaultHarnessId;
    }

    const nameRow = document.createElement('label');
    nameRow.appendChild(document.createTextNode('Name'));
    nameRow.appendChild(this._nameInput);

    const harnessRow = document.createElement('label');
    harnessRow.appendChild(document.createTextNode('Agent'));
    harnessRow.appendChild(this._harnessSelect);

    form.appendChild(nameRow);
    form.appendChild(harnessRow);
    this.node.appendChild(form);
  }

  getValue(): NewChatChoice {
    return {
      name: this._nameInput.value,
      harnessId: this._harnessSelect.value
    };
  }

  protected onAfterAttach(): void {
    // Focus the name field so the user can just type and hit Enter.
    setTimeout(() => this._nameInput.focus(), 0);
  }
}

export async function showNewChatDialog(
  harnesses: HarnessInfo[]
): Promise<NewChatChoice | null> {
  if (harnesses.length === 0) {
    return null;
  }
  const body = new NewChatDialogBody(harnesses);
  const dialog = new Dialog<NewChatChoice>({
    title: 'Create a new chat',
    body,
    buttons: [Dialog.cancelButton(), Dialog.okButton({ label: 'Create' })]
  });
  const result = await dialog.launch();
  if (!result.button.accept) {
    return null;
  }
  return result.value;
}
