let access = sessionStorage.getItem('tf_access');
let refresh = sessionStorage.getItem('tf_refresh');
export function setTokens(tokens) {
  access = tokens?.access || null; refresh = tokens?.refresh || null;
  if (access) { sessionStorage.setItem('tf_access', access); sessionStorage.setItem('tf_refresh', refresh); }
  else { sessionStorage.removeItem('tf_access'); sessionStorage.removeItem('tf_refresh'); }
}
let refreshing;
export async function api(path, options = {}, retry = true) {
  const isForm = options.body instanceof FormData;
  const headers = { ...(isForm ? {} : { 'Content-Type': 'application/json' }), ...(access ? { Authorization: 'Bearer ' + access } : {}), ...options.headers };
  const response = await fetch('/api/' + path, { ...options, headers, body: options.body && !isForm ? JSON.stringify(options.body) : options.body });
  if (response.status === 401 && refresh && retry && !path.startsWith('auth/login')) {
    refreshing ||= fetch('/api/auth/refresh/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh }) }).then(async r => {
      if (!r.ok) { setTokens(null); throw new Error('Session expired. Please sign in again.'); }
      setTokens(await r.json());
    }).finally(() => { refreshing = null; });
    await refreshing;
    return api(path, options, false);
  }
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : Object.entries(data).map(([k,v]) => k + ': ' + (Array.isArray(v) ? v.join(', ') : JSON.stringify(v))).join(' • '));
  return data;
}
export async function logout() {
  try { if (refresh) await api('auth/logout/', { method: 'POST', body: { refresh } }); }
  finally { setTokens(null); }
}