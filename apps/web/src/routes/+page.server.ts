import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';
import { authEnabled } from '$lib/server/auth';

export const load: PageServerLoad = async ({ fetch, locals, url }) => {
  const apiBase = env.API_INTERNAL_URL ?? 'http://localhost:8000';
  let apiStatus = 'unavailable';
  try {
    const response = await fetch(`${apiBase}/health/live`, {
      signal: AbortSignal.timeout(1500)
    });
    if (response.ok) apiStatus = 'ready';
  } catch {
    // The web shell remains usable while application infrastructure is offline.
  }

  return {
    user: locals.user,
    authEnabled: authEnabled(),
    apiStatus,
    authError: url.searchParams.get('auth_error')
  };
};
