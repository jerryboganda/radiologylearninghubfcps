import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { clearSession } from '$lib/server/auth';

export const POST: RequestHandler = ({ cookies, url }) => {
  clearSession(cookies, url.protocol === 'https:');
  throw redirect(303, '/');
};
