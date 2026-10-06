using System.Text.Json.Nodes;
using Npgsql;

public sealed class Store(NpgsqlDataSource source)
{
    public async Task<JsonNode> Query(string sql, params object?[] values)
    {
        await using var command = source.CreateCommand(sql);
        foreach (var value in values) command.Parameters.AddWithValue(value ?? DBNull.Value);
        var result = await command.ExecuteScalarAsync();
        return JsonNode.Parse(result?.ToString() ?? "null")!;
    }
    public async Task<int> Execute(string sql, params object?[] values)
    {
        await using var command = source.CreateCommand(sql);
        foreach (var value in values) command.Parameters.AddWithValue(value ?? DBNull.Value);
        return await command.ExecuteNonQueryAsync();
    }
    public const string IssueColumns = """
        i.id, i.project_id AS "projectId", p.key || '-' || i.number AS key,
        i.sprint_id AS "sprintId", i.title, i.description, i.status, i.priority, i.type, i.assignee, i.labels,
        i.due_date AS "dueDate", i.story_points AS "storyPoints", i.version,
        i.created_at AS "createdAt", i.updated_at AS "updatedAt",
        (SELECT count(*) FROM comments c WHERE c.issue_id=i.id) AS "commentCount"
        """;
    public Task<JsonNode> Issue(Guid id) => Query($"SELECT row_to_json(r)::text FROM (SELECT {IssueColumns} FROM issues i JOIN projects p ON p.id=i.project_id WHERE i.id=$1 AND NOT i.archived) r", id);
    public async Task Initialize()
    {
        await Execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id uuid PRIMARY KEY, key varchar(10) NOT NULL UNIQUE, name varchar(100) NOT NULL,
                description text NOT NULL DEFAULT '', color varchar(20) NOT NULL DEFAULT '#6658d9', next_number int NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS issues (
                id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id), number int NOT NULL,
                title varchar(180) NOT NULL CHECK(length(trim(title))>0), description text NOT NULL DEFAULT '',
                status varchar(20) NOT NULL CHECK(status IN ('backlog','todo','progress','review','done')),
                priority varchar(20) NOT NULL CHECK(priority IN ('low','medium','high','urgent')),
                type varchar(20) NOT NULL CHECK(type IN ('task','story','bug')),
                assignee varchar(80) NOT NULL DEFAULT '', labels text[] NOT NULL DEFAULT '{}', due_date date,
                story_points int CHECK(story_points BETWEEN 0 AND 100), version int NOT NULL DEFAULT 1,
                archived boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE(project_id,number));
            CREATE INDEX IF NOT EXISTS ix_issues_project ON issues(project_id,status);
            CREATE TABLE IF NOT EXISTS comments (
                id uuid PRIMARY KEY, issue_id uuid NOT NULL REFERENCES issues(id), author varchar(80) NOT NULL,
                body text NOT NULL CHECK(length(trim(body)) BETWEEN 1 AND 4000), created_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS activity (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, issue_id uuid NOT NULL REFERENCES issues(id),
                message text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
            """);
        await Upgrade.Run(this);
        await Workflow.Upgrade(this);
        var count = await Query("SELECT count(*)::text FROM projects");
        if (count!.GetValue<int>() != 0) return;
        var project = Guid.Parse("af1042ec-b2e7-4430-a310-825c355603f1");
        await Execute("INSERT INTO projects(id,key,name,description) VALUES($1,'ORB','Plataforma Orbit','Um espaço para transformar ideias em entregas.') ON CONFLICT DO NOTHING",project);
        var seeds = new (string Title, string Status, string Priority, string Type, string Person, string Label, int Points)[] {
            ("Desenhar a experiência de boas-vindas","todo","high","story","Ana Lima","Design",5),
            ("Definir os critérios de aceite do cadastro","todo","medium","task","Pedro Costa","Produto",3),
            ("Preparar ambiente de homologação","todo","medium","task","Lucas Souza","Infra",3),
            ("Construir o painel de projetos","progress","high","story","Rafael","Frontend",8),
            ("Criar endpoints de tarefas","progress","high","task","Pedro Costa","Backend",5),
            ("Ajustar contraste dos botões","progress","low","bug","Ana Lima","Design",2),
            ("Revisar fluxo de mudança de status","review","medium","task","Rafael","Produto",3),
            ("Validar persistência no PostgreSQL","review","high","task","Lucas Souza","Backend",5),
            ("Organizar o backlog inicial","done","medium","task","Rafael","Produto",2),
            ("Definir identidade visual","done","low","story","Ana Lima","Design",3),
            ("Adicionar filtros por responsável","backlog","medium","story","Pedro Costa","Frontend",5),
            ("Investigar notificações de vencimento","backlog","low","task","","Pesquisa",3)
        };
        foreach(var seed in seeds) await Create(project,new IssueInput(seed.Title,"Contexto\nEste item faz parte da demonstração inicial. Ajuste a descrição e os critérios de aceite para o seu projeto.\n\nCritérios de aceite\n• Comportamento revisado\n• Resultado validado no ambiente local",seed.Status,seed.Priority,seed.Type,seed.Person,[seed.Label],null,seed.Points,null));
    }
    public async Task<Guid> Create(Guid project, IssueInput input)
    {
        await using var connection=await source.OpenConnectionAsync();
        await using var transaction=await connection.BeginTransactionAsync();
        await using var numberCommand=new NpgsqlCommand("UPDATE projects SET next_number=next_number+1 WHERE id=$1 RETURNING next_number-1",connection,transaction);
        numberCommand.Parameters.AddWithValue(project);
        var number=await numberCommand.ExecuteScalarAsync();
        if(number is null) throw new KeyNotFoundException("Projeto não encontrado.");
        var id=Guid.NewGuid();
        await using var command=new NpgsqlCommand("""
            WITH inserted AS (
                INSERT INTO issues(id,project_id,number,title,description,status,priority,type,assignee,labels,due_date,story_points,sprint_id)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::date,$12::int,$13::uuid) RETURNING id)
            INSERT INTO activity(issue_id,message) SELECT id,'Tarefa criada' FROM inserted
            """,connection,transaction);
        object?[] values=[id,project,number,input.Title!.Trim(),input.Description??"",input.Status??"todo",input.Priority??"medium",input.Type??"task",input.Assignee??"",input.Labels??[],input.DueDate,input.StoryPoints,input.SprintId];
        foreach(var value in values) command.Parameters.AddWithValue(value??DBNull.Value);
        await command.ExecuteNonQueryAsync();
        await transaction.CommitAsync();
        return id;
    }
}
public sealed record IssueInput(string? Title,string? Description,string? Status,string? Priority,string? Type,string? Assignee,string[]? Labels,DateOnly? DueDate,int? StoryPoints,int? Version,Guid? SprintId=null);
public sealed record ProjectInput(string? Name,string? Key,string? Description);
public sealed record CommentInput(string? Body,string? Author);
