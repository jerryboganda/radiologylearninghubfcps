import { error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { completeLogin } from '$lib/server/auth';

export const GET: RequestHandler = async ({ cookies, url }) => {
  if (url.searchParams.has('error')) {
    throw redirect(303, `/?auth_error=${encodeURIComponent(url.searchParams.get('error') ?? 'login_failed')}`);
  }
  try {
    await completeLogin(url, cookies);
  } catch (cause) {
    console.error('OIDC callback failed', cause);
    throw error(401, 'Sign-in could not be completed. Please try again.');
  }
  throw redirect(303, '/');
};
