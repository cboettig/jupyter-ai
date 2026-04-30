import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

export { HarnessPicker } from './components/HarnessPicker';
export { HarnessBadge } from './components/HarnessBadge';
export { HarnessHeader } from './components/HarnessHeader';
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

export default plugin;
