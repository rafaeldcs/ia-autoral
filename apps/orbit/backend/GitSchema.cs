using System.Threading.Tasks;

public static class GitSchema
{
    public static Task<int> Upgrade(Store db) => db.Execute(@"
CREATE TABLE IF NOT EXISTS git_repositories (
    project_id uuid PRIMARY KEY REFERENCES projects(id),
    url text NOT NULL,
    branch text NOT NULL,
    workflow text NOT NULL DEFAULT 'orbit-hml.yml',
    auto_deploy bool NOT NULL DEFAULT false,
    credential text NOT NULL DEFAULT '',
    head text NOT NULL DEFAULT '',
    commits jsonb NOT NULL DEFAULT '[]',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS git_jobs (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES git_repositories(project_id),
    actor_id uuid NOT NULL REFERENCES users(id),
    action text NOT NULL CHECK (action IN ('pull', 'push', 'deploy')),
    status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    expected_head text NOT NULL DEFAULT '',
    head text NOT NULL DEFAULT '',
    message text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);

ALTER TABLE git_jobs ADD COLUMN IF NOT EXISTS phase text NOT NULL DEFAULT 'git';
CREATE UNIQUE INDEX IF NOT EXISTS git_one_job ON git_jobs(project_id) WHERE status IN ('queued', 'running');
");
}
