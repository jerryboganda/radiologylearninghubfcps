import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = () =>
  json({
    status: 'ok',
    service: 'web',
    environment: env.APP_ENV ?? 'development'
  });
