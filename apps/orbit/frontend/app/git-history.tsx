'use client';

import type { GitRepository, GitJob } from './git-types';

export function GitHistory({ repository, jobs, issues, onOpen }: { repository: GitRepository | null; jobs: GitJob[]; issues: { id: string; key: string }[]; onOpen: (id: string) => void }) {
  const commits = repository?.commits || [];
  const formattedJobs = jobs.map(job => ({
    ...job,
    action: {
      'pull': 'Atualizar',
      'push': 'Enviar',
      'deploy': 'Publicar'
    }[job.action] || job.action,
    status: {
      'queued': 'Na fila',
      'running': 'Em andamento',
      'succeeded': 'Concluído',
      'failed': 'Falhou'
    }[job.status] || job.status
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Commits</h2>
      <div className="space-y-2">
        {commits.map(commit => {
          const repoUrl = repository?.url?.replace(/\.git$/, '');
          const commitUrl = repoUrl ? `${repoUrl}/commit/${commit.sha}` : '';

          const issueMatches = issues.filter(issue => {
            const regex = new RegExp(`\\b${issue.key}\\b`);
            return regex.test(commit.subject);
          });

          return (
            <div key={commit.sha} className="flex flex-wrap gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-500">{commit.sha.slice(0, 8)}</div>
                <div className="text-sm">{commit.subject}</div>
              </div>
              <a
                href={commitUrl}
                target="_blank"
                rel="noreferrer"
                className="text-blue-500 hover:underline"
              >
                Ver commit
              </a>
              {issueMatches.length > 0 && (
                <div className="mt-1">
                  {issueMatches.map(issue => (
                    <button
                      key={issue.id}
                      onClick={() => onOpen(issue.id)}
                      className="text-blue-500 hover:underline text-sm"
                    >
                      {issue.key}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <h2 className="text-xl font-semibold">Histórico de operações</h2>
      <div className="space-y-3">
        {formattedJobs.map(job => {
          const dateTime = new Date(job.createdAt);
          const formattedDate = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(dateTime);

          const message = job.message;
          const isPipelineUrl = message?.match(/^https:\/\/github\.com\/rafaeldcs\/ia-autoral\/actions\/runs\/[0-9]+$/);

          return (
            <div key={job.id} className="flex flex-wrap gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{job.action}</div>
                <div className="text-xs text-gray-500">{job.status}</div>
                <div className="text-xs text-gray-500">{formattedDate}</div>
              </div>
              <div className="mt-1">
                {isPipelineUrl ? (
                  <a
                    href={message}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-500 hover:underline text-sm"
                  >
                    Ver pipeline
                  </a>
                ) : (
                  <div className="text-sm">{message || 'Vazio'}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
