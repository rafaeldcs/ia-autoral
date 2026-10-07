using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Security.Cryptography;
using System.Threading;

public static class HostedSchema
{
    public static Task<int> Upgrade(Store db) => db.Execute(@"
        CREATE TABLE IF NOT EXISTS hosted_repositories(
            project_id uuid PRIMARY KEY REFERENCES projects(id),
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS hosted_tokens(
            id uuid PRIMARY KEY,
            project_id uuid NOT NULL REFERENCES hosted_repositories(project_id),
            user_id uuid NOT NULL REFERENCES users(id),
            hash text NOT NULL UNIQUE,
            label varchar(80) NOT NULL,
            write_access boolean NOT NULL DEFAULT false,
            expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
            revoked boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    ");
}
