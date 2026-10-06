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
  const [error, setError] = useState<string>('');

  const load = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await api<Data>(`/projects/${project}/repository`);
      setData(result);
      setUrl(result.clonePath ? window.location.origin + result.clonePath : '');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
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
      <p>Código privado hospedado no próprio Orbit. Admins/gestores criam; colaboradores enviam; leitores consultam. GitHub continua abaixo.</p>
      <button onClick={load} disabled={busy}>
        Atualizar repositório hospedado
      </button>
      {error && <p role="alert">{error}</p>}
      {!data.exists ? (
        <button onClick={create} disabled={busy} style={{ display: account.role === 'admin' || account.role === 'manager' ? 'inline-block' : 'none' }}>
          Criar repositório
        </button>
      ) : (
        <>
          <textarea aria-label="URL para clone" value={url} readOnly />
          <p>git clone {url}</p>
          <p>Branch: {data.branch}</p>
          <p>Head: {data.head || 'Faça o primeiro commit e use git push origin main.'}</p>
          <p>Branches: {data.branches?.join(', ')}</p>
          <p>Limite de 20 MiB por push.</p>
          <HostedSource project={project} initial={data.entries || []} />
          <HostedCommits commits={data.commits || []} issues={issues} onOpen={onOpen} />
          <HostedToken project={project} account={account} />
        </>
      )}
    </div>
  );
}
