/**
 * HTTP サーバー(要件定義 §8「API・検証」)。
 *
 * Slack の署名検証には生のリクエストボディが必要なため、
 * パース前の文字列を必ず保持する。
 */

import Fastify, { type FastifyInstance } from 'fastify';
import type { App } from '../app.js';
import { registerAdminRoutes } from './admin-routes.js';
import { registerSlackRoutes } from './slack-routes.js';

export function buildServer(app: App): FastifyInstance {
  const server = Fastify({
    logger: { level: process.env.LOG_LEVEL ?? 'info' },
    // 秘密情報をログへ出さない。
    disableRequestLogging: false,
  });

  // Slack は application/x-www-form-urlencoded で送ってくる。
  // 署名検証のため、生の文字列を rawBody として保持したうえでパースする。
  server.addContentTypeParser(
    'application/x-www-form-urlencoded',
    { parseAs: 'string' },
    (request, body, done) => {
      (request as typeof request & { rawBody?: string }).rawBody = body as string;
      done(null, Object.fromEntries(new URLSearchParams(body as string)));
    },
  );

  server.addContentTypeParser('application/json', { parseAs: 'string' }, (request, body, done) => {
    (request as typeof request & { rawBody?: string }).rawBody = body as string;
    try {
      done(null, body === '' ? {} : JSON.parse(body as string));
    } catch (error) {
      done(error as Error, undefined);
    }
  });

  registerAdminRoutes(server, app);
  registerSlackRoutes(server, app);

  return server;
}
