/** Reference-only TypeScript headless client for AEM Content Fragment GraphQL.
 * Requires persisted query + proper AEM Publish/Dispatcher configuration.
 * Public editorial content ONLY. Never place API credentials or customer data here.
 */
export interface CampaignContent {
  title: string;
  eyebrow: string;
  description: string;
  ctaLabel: string;
  ctaUrl: string;
  segment: string;
}
export async function fetchPublishedCampaigns(
  publishOrigin: string,
  persistedQueryPath: string,
  signal?: AbortSignal
): Promise<CampaignContent[]> {
  const base = new URL(publishOrigin);
  if (!/^https?:$/.test(base.protocol)) throw new Error('Invalid AEM origin');
  if (!/^\/graphql\/execute\.json\/[a-z0-9_/-]+$/i.test(persistedQueryPath))
    throw new Error('Expected a known persisted-query path');
  const url = new URL(persistedQueryPath, base);
  const response = await fetch(url.toString(), { method: 'GET', signal, headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`AEM delivery status ${response.status}`);
  const payload = await response.json();
  // The precise generated GraphQL data shape depends on the customer CF model.
  // Do not pretend this field exists until the AEM Content Fragment Model is deployed.
  const entries = payload?.data?.campaignList?.items;
  if (!Array.isArray(entries)) throw new Error('Unexpected CF GraphQL payload');
  return entries.map((x: Record<string, unknown>) => ({
    title: String(x.title ?? ''), eyebrow: String(x.eyebrow ?? ''),
    description: String(x.description ?? ''), ctaLabel: String(x.ctaLabel ?? ''),
    ctaUrl: String(x.ctaUrl ?? ''), segment: String(x.segment ?? 'all')
  }));
}
