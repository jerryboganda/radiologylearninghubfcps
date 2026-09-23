import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { beginLogin } from '$lib/server/auth';

export const GET: RequestHandler = async ({ url, cookies }) => {
  throw redirect(303, await beginLogin(url, cookies));
};
