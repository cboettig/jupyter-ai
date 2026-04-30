import * as React from 'react';
import { InputToolbarRegistry } from '@jupyter/chat';

import { HarnessHeader } from './HarnessHeader';

/**
 * A toolbar item that hosts the HarnessHeader inline in the chat input
 * toolbar. Reads the chat id from `props.model.chatContext.name`. Returns
 * null if the chat context isn't ready yet (briefly, on first render).
 *
 * Note: per `@jupyter/chat` docs, toolbar items are normally a single
 * `TooltippedButton`; rendering a multi-state component here is a deliberate
 * PoC choice — see the developer rationale doc and issue #1558.
 */
export const HarnessToolbarItem: React.FC<
  InputToolbarRegistry.IToolbarItemProps
> = ({ model }) => {
  const chatId = model?.chatContext?.name;
  if (!chatId) {
    return null;
  }
  return <HarnessHeader chatId={chatId} />;
};
