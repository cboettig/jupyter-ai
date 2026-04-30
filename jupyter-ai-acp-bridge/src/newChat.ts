import { bindHarness } from './api';

/**
 * Polls the bind endpoint with backoff. The chat-init observer fires
 * asynchronously after the chat opens, so a fast first bind attempt can
 * race ahead of the persona-manager registering the new room. ~1.5s of
 * backoff covers the cold-init path.
 */
export async function bindWithRetry(
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
