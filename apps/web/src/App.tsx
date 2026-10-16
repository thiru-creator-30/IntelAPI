import { useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { apiFetch, uploadSpec } from './services/api-client';

type User = { id: string; email: string; display_name?: string };
type Project = { id: string; name: string; description?: string };

function useUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    apiFetch<User>('/auth/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);
  return { user, loading, setUser };
}

function Shell({ user, onLogout }: { user: User | null; onLogout: () => void }) {
  return (
    <div className="shell">
      <header>
        <h1>IntelAPI</h1>
        <nav>
          <Link to="/projects">Projects</Link>
        </nav>
        <div className="spacer" />
        {user ? (
          <>
            <span className="muted">{user.email}</span>
            <button onClick={onLogout}>Logout</button>
          </>
        ) : (
          <Link to="/login">Sign in</Link>
        )}
      </header>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const nav = useNavigate();
  const [token, setToken] = useState('');
  const [clientId, setClientId] = useState('');
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    apiFetch<{ client_id: string }>('/auth/google/config').then((c) => setClientId(c.client_id)).catch(() => {});
  }, []);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const u = await apiFetch<User>('/auth/google/session', {
        method: 'POST',
        body: JSON.stringify({ id_token: token }),
      });
      onLogin(u);
      nav('/projects');
    } catch (e: any) {
      setErr(e?.message ?? 'Sign-in failed');
    }
  }
  return (
    <div className="card">
      <h2>Sign in</h2>
      <p className="muted">Client ID: {clientId || '(not configured)'}</p>
      <form onSubmit={submit} className="stack">
        <label>
          Google ID token (paste a token obtained via Google OAuth in a real deployment)
          <textarea value={token} onChange={(e) => setToken(e.target.value)} rows={4} />
        </label>
        {err && <p className="err">{err}</p>}
        <button type="submit">Sign in</button>
      </form>
    </div>
  );
}

function Projects({ user }: { user: User }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('');
  async function load() {
    const page = await apiFetch<{ items: Project[] }>('/projects');
    setProjects(page.items);
  }
  useEffect(() => { load(); }, []);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    await apiFetch('/projects', { method: 'POST', body: JSON.stringify({ name }) });
    setName(''); load();
  }
  return (
    <div>
      <h2>Projects</h2>
      <form onSubmit={create} className="row">
        <input placeholder="New project name" value={name} onChange={(e) => setName(e.target.value)} />
        <button>Create</button>
      </form>
      <ul className="list">
        {projects.map((p) => (
          <li key={p.id} className="card">
            <Link to={`/projects/${p.id}`}><strong>{p.name}</strong></Link>
            <p className="muted">{p.description || ''}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProjectDetail() {
  const { projectId } = useParams();
  const [tab, setTab] = useState<'workspace' | 'explorer' | 'campaigns' | 'findings' | 'health'>('workspace');
  return (
    <div>
      <h2>Project {projectId}</h2>
      <div className="tabs">
        {(['workspace', 'explorer', 'health', 'campaigns', 'findings'] as const).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      {tab === 'workspace' && <WorkspacePanel projectId={projectId!} />}
      {tab === 'explorer' && <ExplorerPanel projectId={projectId!} />}
      {tab === 'health' && <HealthPanel projectId={projectId!} />}
      {tab === 'campaigns' && <CampaignsPanel projectId={projectId!} />}
      {tab === 'findings' && <FindingsPanel projectId={projectId!} />}
    </div>
  );
}

function WorkspacePanel({ projectId }: { projectId: string }) {
  const [requests, setRequests] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [method, setMethod] = useState('GET');
  const [url, setUrl] = useState('https://');
  const [body, setBody] = useState('');
  const [result, setResult] = useState<any>(null);
  async function load() {
    const page = await apiFetch<{ items: any[] }>(`/projects/${projectId}/requests`);
    setRequests(page.items);
  }
  useEffect(() => { load(); }, [projectId]);
  async function saveAndSend(e: React.FormEvent) {
    e.preventDefault();
    const created = await apiFetch<any>(`/projects/${projectId}/requests`, {
      method: 'POST',
      body: JSON.stringify({ name, method, url, headers: {}, body: body || null }),
    });
    const exec = await apiFetch<any>(`/requests/execute`, {
      method: 'POST',
      body: JSON.stringify({ saved_request_id: created.id, method, url, headers: {} }),
    });
    setResult(exec); load();
  }
  return (
    <div className="stack">
      <form onSubmit={saveAndSend} className="card stack">
        <h3>Send request</h3>
        <div className="row">
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => <option key={m}>{m}</option>)}
          </select>
          <input style={{ flex: 1 }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com" />
        </div>
        <input placeholder="Request name" value={name} onChange={(e) => setName(e.target.value)} />
        <textarea placeholder="Body (optional)" value={body} onChange={(e) => setBody(e.target.value)} rows={5} />
        <button>Save & execute</button>
      </form>
      {result && (
        <div className="card">
          <h4>Result: {result.outcome} {result.status_code ?? ''} ({result.duration_ms ?? '?'}ms)</h4>
          <pre>{JSON.stringify(result.response_headers, null, 2)}</pre>
          <pre>{(result.response_body_excerpt || '').slice(0, 4000)}</pre>
        </div>
      )}
      <h3>Saved requests</h3>
      <ul className="list">
        {requests.map((r) => <li key={r.id} className="card"><code>{r.method}</code> {r.name} — <span className="muted">{r.url}</span></li>)}
      </ul>
    </div>
  );
}

function ExplorerPanel({ projectId }: { projectId: string }) {
  const [specs, setSpecs] = useState<any[]>([]);
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [ops, setOps] = useState<any[]>([]);
  const [candidates, setCandidates] = useState<any[] | null>(null);
  async function load() {
    const page = await apiFetch<{ items: any[] }>(`/projects/${projectId}/specifications`);
    setSpecs(page.items);
  }
  useEffect(() => { load(); }, [projectId]);
  async function doImport(e: React.FormEvent) {
    e.preventDefault();
    await uploadSpec(projectId, file, url || null);
    setUrl(''); setFile(null); load();
  }
  async function openSpec(id: string) {
    setSelected(id); setCandidates(null);
    const page = await apiFetch<{ items: any[] }>(`/specifications/${id}/operations`);
    setOps(page.items);
  }
  async function preview(opId: string) {
    const res = await apiFetch<{ items: any[] }>(`/operations/${opId}/candidates/preview`, { method: 'POST' });
    setCandidates(res.items);
  }
  return (
    <div className="stack">
      <form onSubmit={doImport} className="card stack">
        <h3>Import OpenAPI</h3>
        <input placeholder="URL (must pass SSRF policy)" value={url} onChange={(e) => setUrl(e.target.value)} />
        <input type="file" accept="application/json,.yaml,.yml" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button>Import</button>
      </form>
      <h3>Specifications</h3>
      <ul className="list">
        {specs.map((s) => <li key={s.id}><button onClick={() => openSpec(s.id)}>{s.title || s.id}</button> <span className="muted">{s.size_bytes} bytes</span></li>)}
      </ul>
      {selected && (
        <div className="card">
          <h4>Operations</h4>
          <ul className="list">
            {ops.map((o) => (
              <li key={o.id}>
                <code>{o.method}</code> {o.path}
                <button onClick={() => preview(o.id)}>Preview candidates</button>
              </li>
            ))}
          </ul>
          {candidates && (
            <details open>
              <summary>{candidates.length} candidates (non-persisting preview)</summary>
              <pre>{JSON.stringify(candidates.slice(0, 20), null, 2)}{candidates.length > 20 ? `\n... +${candidates.length - 20} more` : ''}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

function HealthPanel({ projectId }: { projectId: string }) {
  const [checks, setChecks] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('https://');
  const [lastRun, setLastRun] = useState<any>(null);
  async function load() {
    const page = await apiFetch<{ items: any[] }>(`/projects/${projectId}/health-checks`);
    setChecks(page.items);
  }
  useEffect(() => { load(); }, [projectId]);
  async function create() {
    await apiFetch(`/projects/${projectId}/health-checks`, {
      method: 'POST',
      body: JSON.stringify({ name, request: { method: 'GET', url, headers: {} }, assertions: [{ type: 'status_code', expect: { in: [200, 204] } }] }),
    });
    setName(''); setUrl('https://'); load();
  }
  async function run(id: string) {
    const r = await apiFetch<any>(`/health-checks/${id}/run`, { method: 'POST' });
    setLastRun(r);
  }
  return (
    <div className="stack">
      <div className="card stack">
        <h3>Create health check</h3>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="URL" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button onClick={create}>Create</button>
      </div>
      <ul className="list">
        {checks.map((c) => (
          <li key={c.id} className="card">
            <strong>{c.name}</strong> <span className="muted">{c.request_definition?.url}</span>
            <button onClick={() => run(c.id)}>Run</button>
          </li>
        ))}
      </ul>
      {lastRun && <pre className="card">{JSON.stringify(lastRun, null, 2)}</pre>}
    </div>
  );
}

function CampaignsPanel({ projectId }: { projectId: string }) {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [specId, setSpecId] = useState('');
  const [report, setReport] = useState<any>(null);
  async function load() {
    const page = await apiFetch<{ items: any[] }>(`/projects/${projectId}/campaigns`);
    setCampaigns(page.items);
  }
  useEffect(() => { load(); }, [projectId]);
  async function create(e: React.FormEvent) {
    e.preventDefault();
    await apiFetch(`/projects/${projectId}/campaigns`, {
      method: 'POST',
      body: JSON.stringify({ name, source_specification_id: specId || null, budget_executions: 50 }),
    });
    setName(''); load();
  }
  async function openReport(id: string) {
    const r = await apiFetch<any>(`/campaigns/${id}/report`);
    setReport(r);
  }
  async function cancel(id: string) {
    await apiFetch(`/campaigns/${id}/cancel`, { method: 'POST' });
    load(); openReport(id);
  }
  return (
    <div className="stack">
      <form onSubmit={create} className="card row">
        <input placeholder="Campaign name" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Specification ID" value={specId} onChange={(e) => setSpecId(e.target.value)} />
        <button>Create (202)</button>
      </form>
      <ul className="list">
        {campaigns.map((c) => (
          <li key={c.id} className="card">
            <strong>{c.name}</strong> state={c.state} used={c.executions_used}/{c.budget_executions}
            <button onClick={() => openReport(c.id)}>Report</button>
            <button onClick={() => cancel(c.id)}>Cancel</button>
          </li>
        ))}
      </ul>
      {report && <pre className="card">{JSON.stringify(report, null, 2)}</pre>}
    </div>
  );
}

function FindingsPanel({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { apiFetch<{ items: any[] }>(`/projects/${projectId}/findings`).then((p) => setItems(p.items)); }, [projectId]);
  return (
    <ul className="list">
      {items.map((f) => (
        <li key={f.id} className="card">
          <strong>{f.category}</strong> <span className={`sev sev-${f.machine_severity}`}>{f.machine_severity}</span>
          <p>{f.title}</p>
          <p className="muted">{f.summary}</p>
        </li>
      ))}
      {items.length === 0 && <p className="muted">No findings yet.</p>}
    </ul>
  );
}

export default function App() {
  const { user, loading, setUser } = useUser();
  const nav = useNavigate();
  async function logout() {
    await apiFetch('/auth/logout', { method: 'POST' });
    setUser(null); nav('/login');
  }
  if (loading) return <p>Loading…</p>;
  return (
    <div>
      <Shell user={user} onLogout={logout} />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/login" element={user ? <Navigate to="/projects" replace /> : <Login onLogin={setUser} />} />
          <Route path="/projects" element={user ? <Projects user={user} /> : <Navigate to="/login" replace />} />
          <Route path="/projects/:projectId" element={user ? <ProjectDetail /> : <Navigate to="/login" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}

function NotFound() {
  return <h2>404</h2>;
}
