export type GitRepository = {
  url: string;
  branch: string;
  workflow: string;
  autoDeploy: boolean;
  head: string;
  commits: {
    sha: string;
    subject: string;
  }[];
  hasCredential: boolean;
};

export type GitJob = {
  id: string;
  action: 'pull' | 'push' | 'deploy';
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  head: string;
  message: string;
  createdAt: string;
  finishedAt: string | null;
};

export type GitState = {
  repository: GitRepository | null;
  jobs: GitJob[];
};
