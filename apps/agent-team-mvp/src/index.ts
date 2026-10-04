/**
 * 起動エントリポイント。
 *
 * 設定に不足があれば黙って劣化させず、起動時に落とす。
 */

import { buildApp } from './app.js';
import { buildServer } from './api/server.js';
import { loadConfig, validateConfig } from './config.js';

async function main(): Promise<void> {
  const config = loadConfig();
  const problems = validateConfig(config);
  if (problems.length > 0) {
    for (const problem of problems) console.error(`[設定エラー] ${problem}`);
    process.exitCode = 1;
    return;
  }

  const app = buildApp({ config });
  const server = buildServer(app);

  const shutdown = async (signal: string): Promise<void> => {
    server.log.info({ signal }, 'シャットダウンします');
    await server.close();
    await app.close();
  };
  process.on('SIGINT', () => void shutdown('SIGINT'));
  process.on('SIGTERM', () => void shutdown('SIGTERM'));

  await server.listen({ port: config.port, host: '0.0.0.0' });
  server.log.info(
    { chat: app.chat.name, llm: app.llm.name, store: config.store },
    'AIエージェントチームMVP を起動しました',
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
