import type { Handle } from '@sveltejs/kit';
import { readSession } from '$lib/server/auth';

export const handle: Handle = async ({ event, resolve }) => {
  event.locals.user = await readSession(event.cookies);
  return resolve(event);
};
