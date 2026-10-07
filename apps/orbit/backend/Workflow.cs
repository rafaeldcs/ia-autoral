using System.Text.Json.Nodes;

// Reference implementation authored by Codex. Local model proposals are not executed.
public static class Workflow
{
    public static Task Upgrade(Store db) => db.Execute("""
        BEGIN;
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS method text NOT NULL DEFAULT 'scrum' CHECK(method IN ('scrum','kanban'));
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS wip_limit int NOT NULL DEFAULT 3 CHECK(wip_limit BETWEEN 1 AND 100);
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS workflow_version int NOT NULL DEFAULT 1;
        ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_simulation boolean NOT NULL DEFAULT false;
        CREATE INDEX IF NOT EXISTS flow_events_project_time ON issue_events(project_id,recorded_at);
        CREATE INDEX IF NOT EXISTS comments_issue ON comments(issue_id);
        CREATE OR REPLACE FUNCTION enforce_workflow() RETURNS trigger AS $$
        DECLARE mode text; capacity int;
        BEGIN
          SELECT method,wip_limit INTO mode,capacity FROM projects WHERE id=NEW.project_id FOR UPDATE;
          IF mode='kanban' THEN
            IF NEW.sprint_id IS NOT NULL AND (TG_OP='INSERT' OR NEW.sprint_id IS DISTINCT FROM OLD.sprint_id) THEN
              RAISE EXCEPTION 'Kanban usa fluxo contínuo. Não associe novas tarefas a sprints.' USING ERRCODE='P0001';
            END IF;
            IF NOT NEW.archived AND NEW.status IN ('progress','review') THEN
              IF TG_OP='INSERT' OR OLD.archived OR OLD.status NOT IN ('progress','review') THEN
                IF (SELECT count(*) FROM issues WHERE project_id=NEW.project_id AND NOT archived AND status IN ('progress','review') AND id<>NEW.id)>=capacity THEN
                  RAISE EXCEPTION 'Limite de trabalho em andamento atingido. Conclua um item antes de iniciar outro.' USING ERRCODE='P0001';
                END IF;
              END IF;
            END IF;
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
        DROP TRIGGER IF EXISTS workflow_guard ON issues;
        CREATE TRIGGER workflow_guard BEFORE INSERT OR UPDATE ON issues FOR EACH ROW EXECUTE FUNCTION enforce_workflow();
        CREATE OR REPLACE FUNCTION enforce_sprint_method() RETURNS trigger AS $$
        BEGIN
          PERFORM 1 FROM projects WHERE id=NEW.project_id AND method='scrum' FOR UPDATE;
          IF NOT FOUND THEN RAISE EXCEPTION 'Sprints estão disponíveis em projetos Scrum.' USING ERRCODE='P0001'; END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
        DROP TRIGGER IF EXISTS sprint_method_guard ON sprints;
        CREATE TRIGGER sprint_method_guard BEFORE INSERT OR UPDATE ON sprints FOR EACH ROW EXECUTE FUNCTION enforce_sprint_method();
        CREATE OR REPLACE FUNCTION configure_workflow(target uuid,mode text,capacity int,expected int) RETURNS boolean AS $$
        BEGIN
          PERFORM 1 FROM projects WHERE id=target AND workflow_version=expected FOR UPDATE;
          IF NOT FOUND THEN RETURN false; END IF;
          IF mode='kanban' THEN
            IF EXISTS(SELECT 1 FROM sprints WHERE project_id=target AND state<>'closed') THEN
              RAISE EXCEPTION 'Encerre as sprints planejadas ou ativas antes de mudar para Kanban.' USING ERRCODE='P0001';
            END IF;
            IF (SELECT count(*) FROM issues WHERE project_id=target AND NOT archived AND status IN ('progress','review'))>capacity THEN
              RAISE EXCEPTION 'O limite não pode ser menor que o trabalho já em andamento.' USING ERRCODE='P0001';
            END IF;
          END IF;
          UPDATE projects SET method=mode,wip_limit=capacity,workflow_version=workflow_version+1 WHERE id=target;
          RETURN true;
        END $$ LANGUAGE plpgsql;
        COMMIT;
        """);

    public static void Map(WebApplication app)
    {
        app.MapPut("/api/projects/{project:guid}/workflow", async (Guid project, WorkflowInput input, Store db, HttpContext context) =>
        {
            if (!Accounts.Manage(context)) return Results.Json(new { error = "Apenas gestores configuram o método." }, statusCode: 403);
            if (!WorkflowRules.IsValid(input.Method, input.WipLimit, input.Version))
                return Results.BadRequest(new { error = "Escolha Scrum ou Kanban e um limite entre 1 e 100." });
            var changed = await db.Query("SELECT configure_workflow($1,$2,$3,$4)::text", project, input.Method, input.WipLimit, input.Version);
            if (!changed.GetValue<bool>()) return Results.Conflict(new { error = "Configuração alterada. Atualize o projeto antes de salvar." });
            await Accounts.Audit(db, context, $"Configurou {input.Method}, limite {input.WipLimit}, projeto {project}");
            return Results.Ok(new { method = input.Method, wipLimit = input.WipLimit, workflowVersion = input.Version + 1 });
        });
        app.MapGet("/api/projects/{project:guid}/flow", async (Guid project, Store db) => Results.Json(await db.Query("""
          WITH items AS (SELECT * FROM issues WHERE project_id=$1 AND NOT archived),
          lifetimes AS (
            SELECT i.id,i.status,i.created_at,
              min(e.recorded_at) FILTER(WHERE e.status='progress' AND NOT e.baseline) AS started,
              max(e.recorded_at) FILTER(WHERE e.status='done' AND e.previous_status IS DISTINCT FROM 'done' AND NOT e.baseline) AS finished
            FROM items i LEFT JOIN issue_events e ON e.issue_id=i.id GROUP BY i.id,i.status,i.created_at
          ), completed AS (
            SELECT extract(epoch FROM finished-started)/3600 AS hours FROM lifetimes
            WHERE status='done' AND started IS NOT NULL AND finished>=started
          ), days AS (SELECT generate_series((now() AT TIME ZONE 'UTC')::date-13,(now() AT TIME ZONE 'UTC')::date,interval '1 day') AS day),
          snapshots AS (
            SELECT d.day,h.status FROM days d CROSS JOIN items i
            JOIN LATERAL (SELECT e.status FROM issue_events e WHERE e.issue_id=i.id
              AND e.recorded_at<((d.day+interval '1 day') AT TIME ZONE 'UTC') ORDER BY e.recorded_at DESC,e.id DESC LIMIT 1) h ON true
          )
          SELECT json_build_object(
            'isSimulation',(SELECT is_simulation FROM projects WHERE id=$1),
            'wip',(SELECT count(*) FROM items WHERE status IN ('progress','review')),
            'throughput14Days',(SELECT count(DISTINCT e.issue_id) FROM issue_events e JOIN items i ON i.id=e.issue_id
              WHERE e.status='done' AND e.previous_status IS DISTINCT FROM 'done' AND NOT e.baseline
              AND e.recorded_at>=(((now() AT TIME ZONE 'UTC')::date-13) AT TIME ZONE 'UTC')),
            'cycleMedianHours',(SELECT percentile_cont(0.5) WITHIN GROUP(ORDER BY hours) FROM completed),
            'cycleP85Hours',(SELECT percentile_cont(0.85) WITHIN GROUP(ORDER BY hours) FROM completed),
            'cycleSamples',(SELECT count(*) FROM completed),
            'oldestAgeHours',(SELECT max(extract(epoch FROM now()-started)/3600) FROM lifetimes WHERE status IN ('progress','review')),
            'daily',(SELECT json_agg(r ORDER BY r.day) FROM (SELECT d.day::date AS day,
              count(s.status) FILTER(WHERE s.status='backlog') AS backlog,
              count(s.status) FILTER(WHERE s.status='todo') AS todo,
              count(s.status) FILTER(WHERE s.status='progress') AS progress,
              count(s.status) FILTER(WHERE s.status='review') AS review,
              count(s.status) FILTER(WHERE s.status='done') AS done
              FROM days d LEFT JOIN snapshots s ON s.day=d.day GROUP BY d.day) r)
          )::text
          """, project)));
    }
}
public sealed record WorkflowInput(string Method, int WipLimit, int Version);
