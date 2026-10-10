/** Same-origin gateway. Only this project's federated identity can invoke Cloud Run. */
import { getVercelOidcToken } from '@vercel/oidc';
const ROUTES = new Map([
  ['ready', { method: 'GET', upstream: '/ready' }],
  ['feedback', { method: 'POST', upstream: '/api/feedback' }],
  ['model-essay', { method: 'POST', upstream: '/api/model-essay' }],
]);
async function googleJson(url, options) {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error(`Cloud identity exchange returned ${response.status}`);
  return response.json();
}
async function backendToken(audience) {
  const subjectToken = await getVercelOidcToken();
  const exchange = await googleJson('https://sts.googleapis.com/v1/token', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      audience: process.env.GCP_WIF_AUDIENCE,
      grantType: 'urn:ietf:params:oauth:grant-type:token-exchange',
      requestedTokenType: 'urn:ietf:params:oauth:token-type:access_token',
      subjectTokenType: 'urn:ietf:params:oauth:token-type:jwt',
      subjectToken, scope: 'https://www.googleapis.com/auth/cloud-platform',
    }),
  });
  const identity = await googleJson(
    `https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${process.env.GCP_INVOKER_EMAIL}:generateIdToken`, {
      method: 'POST', headers: { Authorization: `Bearer ${exchange.access_token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ audience, includeEmail: true }),
    });
  return identity.token;
}
export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  const route = ROUTES.get(req.query.path);
  if (!route) return res.status(404).json({ detail: 'Unknown application route.' });
  if (req.method !== route.method) return res.status(405).json({ detail: 'Method not allowed.' });
  const upstream = process.env.STEPWISE_API_URL;
  if (!upstream || !process.env.GCP_WIF_AUDIENCE || !process.env.GCP_INVOKER_EMAIL)
    return res.status(503).json({ detail: 'The cloud connection is being configured. Please try again shortly.' });
  if (!/^https:\/\/[a-z0-9.-]+\.run\.app$/.test(upstream))
    return res.status(503).json({ detail: 'The cloud connection is unavailable.' });
  const body = route.method === 'POST' ? JSON.stringify(req.body) : undefined;
  if (body && Buffer.byteLength(body) > 50000)
    return res.status(413).json({ detail: 'Please shorten the essay or instructions.' });
  try {
    const token = await backendToken(upstream);
    const response = await fetch(upstream + route.upstream, {
      method: route.method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body, signal: AbortSignal.timeout(270000),
    });
    if (!response.headers.get('content-type')?.includes('application/json'))
      throw new Error(`Cloud backend returned ${response.status}`);
    const result = await response.json();
    return res.status(response.status).json(result);
  } catch (error) {
    // No request bodies, tokens, or private essays enter infrastructure logs.
    console.error('Stepwise gateway:', error.name, error.message);
    return res.status(503).json({ detail: 'The cloud assessment is temporarily unavailable. Please retry.' });
  }
}
