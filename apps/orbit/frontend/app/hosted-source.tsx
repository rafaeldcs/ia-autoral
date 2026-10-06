'use client';

import { useState, useEffect } from 'react';
import { api } from './client';

export type HostedEntry = {
  mode: string;
  type: string;
  sha: string;
  name: string;
};

export function HostedSource({ project, initial }: { project: string; initial: HostedEntry[] }) {
  const [entries, setEntries] = useState<HostedEntry[]>(initial);
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  useEffect(() => {
    setEntries(initial);
    setText(null);
    setError(null);
    setBusy(false);
  }, [initial]);

  const handleBackToRoot = () => {
    setEntries(initial);
    setText(null);
    setError(null);
  };

  const handleEntryClick = async (entry: HostedEntry) => {
    if (busy || entry.type !== 'tree' && entry.type !== 'blob') return;

    setBusy(true);
    setError(null);

    try {
      const response = await api<{ entries?: HostedEntry[]; text?: string }>(
        '/projects/' + project + '/repository/object',
        'POST',
        { sha: entry.sha, type: entry.type }
      );

      if (response.entries) {
        setEntries(response.entries);
setText(null);
      } else if (response.text !== undefined) {
        setText(response.text);
      } else {
        setError('Unexpected response');
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="hosted-source">
      <h4>Arquivos</h4>
      <button onClick={handleBackToRoot} disabled={busy}>
        Voltar à raiz
      </button>
      {error && <div role="alert">{error}</div>}
      <div className="hosted-file-list">
        {entries.map((entry) => (
          <button
            key={entry.name + entry.sha}
            onClick={() => handleEntryClick(entry)}
            disabled={busy || entry.type !== 'tree' && entry.type !== 'blob'}
          >
            {entry.type === 'tree' ? '📁 ' + entry.name : entry.name}
          </button>
        ))}
      </div>
      {text !== null && (
        <pre className="code-preview" style={{ whiteSpace: 'pre-wrap' }}>
          {text}
        </pre>
      )}
    </div>
  );
}
