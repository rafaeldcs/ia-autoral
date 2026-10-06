'use client';
import { useEffect, useState } from 'react';
import {api,type Account} from './client';
import {GitConfig} from './git-config';
import {GitHistory} from './git-history';
import {HostedRepositoryPanel} from './hosted-repository';
import type { GitState } from './git-types';

export function GitPanel({ project, account, issues, onOpen }: { project: string; account: Account; issues: { id: string; key: string }[]; onOpen: (id: string) => void }) {
  const [data, setData] = useState<GitState>({ repository: null, jobs: [] });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'push' | 'deploy' | ''>('');
  const [notice, setNotice] = useState('');
  const canManage = account.role==='admin'||account.role==='manager';
  const repo = data.repository;

  const load = async () => {
    try {
      const res = await api<GitState>(`/projects/${project}/git`);
      setData(res);
      setLoaded(true);
      setError(null);
    } catch (err) {
      setError('Erro ao carregar dados do repositório');
    }
  };

  useEffect(() => {
    if (project) {
      setLoaded(false);
      load();
    }
    return () => {
      // Cleanup if needed
    };
  }, [project]);

  useEffect(() => {
    if (data.jobs.some(job => job.status === 'queued' || job.status === 'running')) {
      const interval = setInterval(load, 3000);
      return () => clearInterval(interval);
    }
  }, [data.jobs]);

const executeAction = async (action: 'pull' | 'push' | 'deploy') => {
  if (!repo) return;
  setBusy(true);
  setError(null);
  setNotice('');
  try {
    await api('/projects/' + project + '/git/jobs', 'POST', { action, expectedHead: repo.head || '' });
    setConfirmAction('');
    setNotice('Operação adicionada à fila.');
    await load();
  } catch (err) {
    setError((err as Error).message);
  } finally {
    setBusy(false);
  }
};

  const handleConfirm = async () => {
    if (!confirmAction || !repo) return;
    setConfirmAction('');
    await executeAction(confirmAction);
  };

  const handleCancel = () => {
    setConfirmAction('');
  };

  const handleGitConfigSave = async () => {
    if (!repo) return;
    await load();
  };

const pending = data.jobs.some(j => j.status === 'queued' || j.status === 'running');

return (
  <section className="list-panel" style={{display: 'grid', gap: '1rem', padding: '1rem', overflowWrap: 'anywhere'}}>
    <h2>Código e entregas.</h2>
    <HostedRepositoryPanel
      project={project}
      account={account}
      issues={issues}
      onOpen={onOpen}
      key={project}
    />
    <h3>Conexão com GitHub</h3>
    {account.role === 'admin' && loaded && (
      <GitConfig
        key={project + (repo?.url || '')}
        project={project}
        repository={repo}
        onSaved={() => void load()}
      />
    )}
    {repo ? (
      <>
        <a href={repo.url.replace(/\.git$/, '')} target="_blank" rel="noopener noreferrer">
          {repo.url.replace(/\.git$/, '').split('/').pop()}
        </a>
        <span> - {repo?.branch} / {repo?.head}</span>
        {canManage && (
          <>
            <button
              className="button secondary"
              onClick={() => executeAction('pull')}
              disabled={busy || pending}
            >
              Atualizar código
            </button>
            <button
              className="button secondary"
              onClick={() => setConfirmAction('push')}
              disabled={busy || pending || !repo.head || !repo.hasCredential}
            >
              Enviar commits
            </button>
            <button
              className="button secondary"
              onClick={() => setConfirmAction('deploy')}
              disabled={busy || pending || !repo.head || !repo.autoDeploy || !repo.hasCredential}
            >
              Publicar homologação
            </button>
          </>
        )}
      </>
    ) : (
      <p>Configure um repositório para acompanhar entregas.</p>
    )}
    {confirmAction && canManage && (
      <section role="alert">
        <p>Revisão de {repo?.head} / {repo?.branch}</p>
        <button onClick={handleConfirm} disabled={busy || pending}>
          Confirmar
        </button>
        <button onClick={handleCancel}>
          Cancelar
        </button>
      </section>
    )}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
{canManage && repo && !repo.hasCredential && <p role="status">Para enviar commits ou publicar, peça ao administrador para configurar um token GitHub. Atualizar código de repositórios públicos não exige token.</p>}

    <GitHistory
      repository={repo}
      jobs={data.jobs}
      issues={issues}
      onOpen={onOpen}
    />

  </section>
);

}
