import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { IChatCommandRegistry } from '@jupyter/chat';

import { BridgeSlashCommandProvider } from './providers/BridgeSlashCommandProvider';

export { HarnessPicker } from './components/HarnessPicker';
export { HarnessBadge } from './components/HarnessBadge';
export { HarnessHeader } from './components/HarnessHeader';
export { ModelSelector } from './components/ModelSelector';
export { ModeSelector } from './components/ModeSelector';
export { ConfigOptionsSelector } from './components/ConfigOptionsSelector';
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

export default [plugin, slashPlugin];
