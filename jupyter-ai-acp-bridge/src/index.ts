import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import {
  IChatCommandRegistry,
  IInputToolbarRegistryFactory,
  InputToolbarRegistry
} from '@jupyter/chat';

import { BridgeSlashCommandProvider } from './providers/BridgeSlashCommandProvider';
import { BridgeMentionProvider } from './providers/BridgeMentionProvider';
import { HarnessToolbarItem } from './components/HarnessToolbarItem';
import { augmentChatCreateCommand } from './augmentCreate';

export { HarnessPicker } from './components/HarnessPicker';
export { HarnessBadge } from './components/HarnessBadge';
export { HarnessHeader } from './components/HarnessHeader';
export { HarnessToolbarItem } from './components/HarnessToolbarItem';
export { ModelSelector } from './components/ModelSelector';
export { ModeSelector } from './components/ModeSelector';
export { ConfigOptionsSelector } from './components/ConfigOptionsSelector';
export { showNewChatDialog } from './newChatDialog';
export { bindWithRetry } from './newChat';
export * from './types';
export * as bridgeApi from './api';

const PLUGIN_ID = '@jupyter-ai/acp-bridge:plugin';

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  description: 'Per-thread ACP harness binding for Jupyter AI.',
  autoStart: true,
  activate: (_app: JupyterFrontEnd) => {
    console.log('jupyter-ai-acp-bridge loaded');
  }
};

const slashPlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:slash',
  description: 'Slash command completion for the bound harness.',
  autoStart: true,
  requires: [IChatCommandRegistry],
  activate: (_app: JupyterFrontEnd, registry: IChatCommandRegistry) => {
    registry.addProvider(new BridgeSlashCommandProvider());
  }
};

const mentionPlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:mention',
  description: '@-mention completion for files in the workspace.',
  autoStart: true,
  requires: [IChatCommandRegistry],
  activate: (app: JupyterFrontEnd, registry: IChatCommandRegistry) => {
    registry.addProvider(new BridgeMentionProvider(app.serviceManager.contents));
  }
};

const toolbarPlugin: JupyterFrontEndPlugin<IInputToolbarRegistryFactory> = {
  id: '@jupyter-ai/acp-bridge:toolbar',
  description:
    'Provides an input toolbar registry that hosts the harness picker/badge.',
  autoStart: true,
  provides: IInputToolbarRegistryFactory,
  activate: (_app: JupyterFrontEnd) => ({
    create: () => {
      const registry = InputToolbarRegistry.defaultToolbarRegistry();
      registry.addItem('harness', {
        element: HarnessToolbarItem,
        position: 1
      });
      return registry;
    }
  })
};

const augmentCreatePlugin: JupyterFrontEndPlugin<void> = {
  id: '@jupyter-ai/acp-bridge:augment-create',
  description:
    'Replaces the standard "Create a new chat" dialog with one that asks ' +
    'for both name and harness in a single step. Hits every chat-creation ' +
    'entry point (sidebar +, launcher card, command palette).',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    // Wait for all extensions to register their commands before we
    // override the chat extension's create command.
    void app.restored.then(() =>
      augmentChatCreateCommand(app).catch(err =>
        console.error('[acp-bridge] augment-create failed:', err)
      )
    );
  }
};

export default [
  plugin,
  slashPlugin,
  mentionPlugin,
  toolbarPlugin,
  augmentCreatePlugin
];
