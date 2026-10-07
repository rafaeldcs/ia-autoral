import { useState, useEffect } from 'react';
import { api } from './client';
import type { Account } from './client';

type Token = {
  id: string;
  label: string;
  write: boolean;
  expiresAt: string;
  revoked: boolean;
};

export type HostedTokenProps = {
  project: string;
  account: Account;
};

const HostedToken: React.FC<HostedTokenProps> = ({ project, account }) => {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [secret, setSecret] = useState<string>('');
  const [showSecret, setShowSecret] = useState<boolean>(false);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const reload = async () => {
    try {
      const res = await api<Token[]>(`/projects/${project}/repository/tokens`, 'GET');
      setTokens(res);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    setSecret('');
    setShowSecret(false);
    reload();
  }, [project]);

  const createToken = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const label = formData.get('label') as string;
    const write = formData.get('write') === 'on';

    if (!label) return;

    setBusy(true);
    setError('');

    try {
      const res = await api<{ id: string; token: string }>(
        `/projects/${project}/repository/tokens`,
        'POST',
        { label, write }
      );
      setSecret(res.token);
      setShowSecret(false);
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const revokeToken = async (id: string) => {
    setBusy(true);
    setError('');
    try {
      await api<void>(`/projects/${project}/repository/tokens/${id}/revoke`, 'POST');
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const toggleSecret = () => setShowSecret(!showSecret);
  const clearSecret = () => {
    setSecret('');
    setShowSecret(false);
  };

  return (
    <div className="hosted-token">
      <form onSubmit={createToken}>
        <div className="form-group">
          <label htmlFor="label">Nome do token</label>
          <input type="text" id="label" name="label" maxLength={80} required />
        </div>
        <div className="form-group">
          <label>
            <input type="checkbox" name="write" disabled={busy || account.role === 'viewer'} />
            Permitir push
          </label>
        </div>
        <button type="submit" disabled={busy}>
          Criar token Git
        </button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="token-list">
        {tokens.map((token) => (
          <div key={token.id} className="hosted-token-item">
            <div>
              <strong>{token.label}</strong>
              <span>{token.write ? 'Escrita' : 'Leitura'}</span>
              <span>{new Date(token.expiresAt).toLocaleDateString('pt-BR')}</span>
              <span>{token.revoked ? 'Revogado' : 'Ativo'}</span>
            </div>
            <button onClick={() => revokeToken(token.id)} disabled={token.revoked || busy}>
              Revogar {token.label}
            </button>
          </div>
        ))}
      </div>
      {secret && (
        <div>
          <input
            type={showSecret ? 'text' : 'password'}
            value={secret}
            readOnly
            aria-label="Token Git gerado"
          />
          <button onClick={toggleSecret}>
            {showSecret ? 'Ocultar' : 'Mostrar token'}
          </button>
          <button onClick={clearSecret}>Ocultar e descartar token</button>
        </div>
      )}
      <p>
        <strong>Nota:</strong> Este token é válido por 30 dias e é associado a um único projeto.
      </p>
    </div>
  );
};

export { HostedToken };
