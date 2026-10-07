'use client';

import { useState, useEffect } from 'react';
import { api } from './client';
import type { Account } from './client';
import { HostedToken } from './hosted-token';
import { HostedSource } from './hosted-source';
import { HostedCommits } from './hosted-commits';

import { HostedEntry } from './hosted-source';

type Data = {
  exists: boolean;
  head?: string;
  branch?: string;
  branches?: string[];
  commits?: { sha: string; subject: string }[];
  entries?: HostedEntry[];
  clonePath?: string;
};

export function HostedRepositoryPanel({
  project,
  account,
  issues,
  onOpen
}: {
  project: string;
  account: Account;
  issues: { id: string; key: string }[];
  onOpen: (id: string) => void;
}) {
  const [data, setData] = useState<Data>({ exists: false });
  const [url, setUrl] = useState<string>('');
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>(''); const [loaded, setLoaded] = useState<boolean>(false);
  const [section, setSection] = useState<'files' | 'history' | 'access'>('files');

  const load = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await api<Data>(`/projects/${project}/repository`);
      setData(result); setLoaded(true);
      setUrl(result.clonePath ? window.location.origin + result.clonePath : '');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    setSection('files');
    setLoaded(false);
    setData({ exists: false });
    load();
  }, [project]);

  const create = async () => {
    setBusy(true);
    setError('');
    try {
      await api<void>(`/projects/${project}/repository`, 'POST', {});
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="hosted-repository list-panel">
      <h3>Repositório do Orbit</h3>
      <p>Código privado hospedado no próprio Orbit. Admins/gestores criam; colaboradores enviam; leitores consultam.</p>
      <button onClick={load} disabled={busy}>
        Atualizar repositório hospedado
      </button>
      {error && <p role="alert">{error}</p>}
      {busy ? <span role="status">Carregando repositório…</span> : loaded && (!data.exists ? (
<>
  <p>Este projeto ainda não possui um repositório.</p>
  {(account.role === 'admin' || account.role === 'manager') && (
    <button onClick={create} disabled={busy}>
      Criar repositório
    </button>
  )}
</>

      ) : (
        <>
          <p className="git-summary">Branch: {data.branch} · Commit: {data.head ? <span title={data.head}>{data.head.slice(0,8)}</span> : 'Primeiro commit pendente'}</p>
          <details className="git-settings">
            <summary>Clonar repositório</summary>
            <textarea aria-label="URL para clone" value={url} readOnly />
            <p>git clone {url}</p>
            <p>Branch: {data.branch}</p>
            <p>Head: {data.head || 'Faça o primeiro commit e use git push origin main.'}</p>
            <p>Branches: {data.branches?.join(', ')}</p>
            <p>Limite de 20 MiB por push.</p>
          </details>
          <nav className="git-area-nav" aria-label="Conteúdo do repositório">
            <button
              type="button"
              aria-pressed={section === 'files'}
              onClick={() => setSection('files')}
            >
              Arquivos
            </button>
            <button
              type="button"
              aria-pressed={section === 'history'}
              onClick={() => setSection('history')}
            >
              Histórico
            </button>
            <button
              type="button"
              aria-pressed={section === 'access'}
              onClick={() => setSection('access')}
            >
              Acesso Git
            </button>
          </nav>
          {section === 'files' && (data.entries?.length ? <HostedSource project={project} initial={data.entries} /> : <p>Nenhum arquivo encontrado. Faça o primeiro commit para começar.</p>)}
          {section === 'history' && (
            data.commits?.length ? <HostedCommits commits={data.commits || []} issues={issues} onOpen={onOpen} /> : <p>Nenhum commit ainda. Faça o primeiro envio de código.</p>
          )}
          {section === 'access' && <section aria-label="Acesso Git">Crie um token pessoal para clonar e enviar código neste projeto.<HostedToken project={project} account={account} /></section>}
        </>
      ))}
    </div>
  );
}
