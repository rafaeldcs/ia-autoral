'use client';
import { useState } from 'react';
import {api} from './client';
import type { GitRepository } from './git-types';

export function GitConfig({ project, repository, onSaved }: { project: string; repository: GitRepository | null; onSaved: () => void }) {
  const [url, setUrl] = useState(repository?.url || 'https://github.com/rafaeldcs/ia-autoral.git');
  const [branch, setBranch] = useState(repository?.branch || 'codex/local-learning-execution');
  const [autoDeploy, setAutoDeploy] = useState(repository?.autoDeploy || false);
  const [token, setToken] = useState('');
  const [clear, setClear] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError('');
  setBusy(true);
  try {
    await api('/projects/' + project + '/git', 'POST', {
      url,
      branch,
      workflow: 'orbit-hml.yml',
      autoDeploy,
      token: clear ? '' : token || null
    });
    setToken('');
    setClear(false);
    onSaved();
  } catch (err) {
    setError((err as Error).message);
  } finally {
    setBusy(false);
  }
};

return (
  <form onSubmit={handleSubmit} style={{display:'grid',gap:12,maxWidth:720}}>
    <label className="field"><span>Repositório GitHub (HTTPS)</span><input type="text" required value={url} onChange={(e)=>setUrl(e.target.value)} /></label>
    <label className="field"><span>Branch</span><input type="text" required value={branch} onChange={(e)=>setBranch(e.target.value)} /></label>
    <label className="field"><span>Token GitHub (opcional)</span><input type="password" autoComplete="new-password" value={token} onChange={(e)=>setToken(e.target.value)} /></label>
    <p>Deixe o token vazio para preservar o salvo. Publicação automática disponível somente para o Orbit.</p>
    <label className="field"><input type="checkbox" checked={clear} onChange={(e)=>setClear(e.target.checked)} /> <span>Remover token salvo</span></label>
    <label className="field"><input type="checkbox" checked={autoDeploy} onChange={(e)=>setAutoDeploy(e.target.checked)} /> <span>Publicar automaticamente após push</span></label>
    <div role="alert" style={{color:'red'}}>{error}</div>
    <button className="button primary" disabled={busy} type="submit">
      {busy ? 'Salvando...' : 'Salvar repositório'}
    </button>
  </form>
);

}
