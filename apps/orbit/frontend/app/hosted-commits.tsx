import React from 'react';

interface HostedCommitsProps {
  commits: { sha: string; subject: string }[];
  issues: { id: string; key: string }[];
  onOpen: (id: string) => void;
}

const HostedCommits: React.FC<HostedCommitsProps> = ({ commits, issues, onOpen }) => {
  if (commits.length === 0) {
    return <h4>Ainda não há commits.</h4>;
  }

  return (
    <div>
      <h4>Commits e tarefas</h4>
      {commits.map(commit => (
        <div key={commit.sha} className="hosted-commit">
          <div className="code">{commit.sha.substring(0, 8)}</div>
          <div className="subject">{commit.subject}</div>
          {issues.map(issue => {
            const regex = new RegExp(`\\b${issue.key}\\b`);
            if (regex.test(commit.subject)) {
              return (
                <button key={issue.id} onClick={() => onOpen(issue.id)}>
                  {issue.key}
                </button>
              );
            }
            return null;
          })}
        </div>
      ))}
    </div>
  );
};

export { HostedCommits };
