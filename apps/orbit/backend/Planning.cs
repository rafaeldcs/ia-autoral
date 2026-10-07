public static class Planning
{
    public static void Map(WebApplication app) {
        app.MapGet("/api/projects/{project:guid}/sprints",async(Guid project,Store db)=>Results.Json(await db.Query("""
          SELECT coalesce(json_agg(s ORDER BY s."startDate" DESC),'[]')::text FROM (
          SELECT id,name,goal,state,start_date AS "startDate",end_date AS "endDate",committed_points AS "committedPoints",
          completed_points AS "completedPoints",committed_count AS "committedCount",completed_count AS "completedCount",
          (SELECT count(*) FROM issues WHERE sprint_id=s.id) AS "issueCount" FROM sprints s WHERE project_id=$1) s
          """,project)));
        app.MapPost("/api/projects/{project:guid}/sprints",async(Guid project,SprintInput input,Store db,HttpContext c)=>{
            if(!Accounts.Manage(c))return Results.Json(new{error="Apenas gestores criam sprints."},statusCode:403);
            if(string.IsNullOrWhiteSpace(input.Name)||input.Name.Length>100||(input.Goal?.Length??0)>2000||input.EndDate<input.StartDate||input.EndDate.DayNumber-input.StartDate.DayNumber>90)return Results.BadRequest(new{error="Informe nome e período de até 90 dias."});
            var id=Guid.NewGuid();await db.Execute("INSERT INTO sprints(id,project_id,name,goal,start_date,end_date) VALUES($1,$2,$3,$4,$5,$6)",id,project,input.Name.Trim(),input.Goal??"",input.StartDate,input.EndDate);
            await Accounts.Audit(db,c,"Criou sprint "+input.Name);return Results.Created("/api/sprints/"+id,new{id});
        });
        app.MapPost("/api/sprints/{id:guid}/start",async(Guid id,Store db,HttpContext c)=>{
            if(!Accounts.Manage(c))return Results.Json(new{error="Apenas gestores iniciam sprints."},statusCode:403);
            var result=await db.Query("SELECT start_sprint($1)::text",id);
            if(!result.GetValue<bool>())return Results.Conflict(new{error="Sprint inexistente, iniciada ou com período vencido."});
            await Accounts.Audit(db,c,"Iniciou sprint "+id);return Results.Ok(new{ok=true});
        });
        app.MapPost("/api/sprints/{id:guid}/complete",async(Guid id,Store db,HttpContext c)=>{
            if(!Accounts.Manage(c))return Results.Json(new{error="Apenas gestores encerram sprints."},statusCode:403);
            var result=await db.Query("SELECT finish_sprint($1)::text",id);
            if(!result.GetValue<bool>())return Results.Conflict(new{error="Somente sprints ativas podem ser encerradas."});
            await Accounts.Audit(db,c,"Encerrou sprint "+id+"; pendências devolvidas ao backlog");return Results.Ok(new{ok=true});
        });
        app.MapGet("/api/projects/{project:guid}/stats",async(Guid project,Store db)=>Results.Json(await db.Query("""
          SELECT json_build_object(
            'total',(SELECT count(*) FROM issues WHERE project_id=$1),
            'done',(SELECT count(*) FROM issues WHERE project_id=$1 AND status='done'),
            'overdue',(SELECT count(*) FROM issues WHERE project_id=$1 AND status<>'done' AND due_date<CURRENT_DATE),
            'unestimated',(SELECT count(*) FROM issues WHERE project_id=$1 AND story_points IS NULL),
            'completedLast30Days',(SELECT count(DISTINCT issue_id) FROM issue_events WHERE project_id=$1 AND status='done' AND previous_status IS DISTINCT FROM 'done' AND NOT baseline AND recorded_at>=now()-interval '30 days'),
            'statuses',(SELECT coalesce(json_agg(r),'[]') FROM (SELECT status,count(*) AS count FROM issues WHERE project_id=$1 GROUP BY status) r),
            'assignees',(SELECT coalesce(json_agg(r),'[]') FROM (SELECT coalesce(nullif(assignee,''),'Não atribuído') AS name,count(*) AS count,coalesce(sum(story_points),0) AS points FROM issues WHERE project_id=$1 AND status<>'done' GROUP BY assignee ORDER BY count(*) DESC) r),
            'daily',(SELECT json_agg(r ORDER BY r.day) FROM (SELECT d::date AS day,
              (SELECT count(*) FROM issues WHERE project_id=$1 AND created_at>=d AND created_at<d+interval '1 day') AS created,
              (SELECT count(DISTINCT issue_id) FROM issue_events WHERE project_id=$1 AND status='done' AND previous_status IS DISTINCT FROM 'done' AND NOT baseline AND recorded_at>=d AND recorded_at<d+interval '1 day') AS completed
              FROM generate_series(CURRENT_DATE-13,CURRENT_DATE,interval '1 day') d) r),
            'velocity',(SELECT coalesce(json_agg(r ORDER BY r."closedAt"),'[]') FROM (SELECT name,committed_points AS committed,completed_points AS completed,closed_at AS "closedAt" FROM sprints WHERE project_id=$1 AND state='closed' ORDER BY closed_at DESC LIMIT 10) r),
            'trackingSince',(SELECT min(recorded_at) FROM issue_events WHERE project_id=$1)
          )::text
          """,project)));
        app.MapGet("/api/sprints/{id:guid}/burndown",async(Guid id,Store db)=>Results.Json(await db.Query("""
          SELECT coalesce(json_agg(r ORDER BY r.day),'[]')::text FROM (
            SELECT d::date AS day,coalesce(sum(h.points) FILTER(WHERE h.sprint_id=s.id AND h.status<>'done'),0) AS remaining,
              count(h.issue_id) FILTER(WHERE h.sprint_id=s.id AND h.status<>'done') AS tasks,
              s.committed_points AS committed
            FROM sprints s CROSS JOIN LATERAL generate_series(s.started_at::date,least(CURRENT_DATE,coalesce(s.closed_at::date,CURRENT_DATE)),interval '1 day') d
            LEFT JOIN LATERAL (SELECT DISTINCT ON(issue_id) issue_id,sprint_id,status,points FROM issue_events
              WHERE project_id=s.project_id AND recorded_at<least(d+interval '1 day',coalesce(s.closed_at,'infinity'::timestamptz))
              ORDER BY issue_id,recorded_at DESC,id DESC) h ON true
            WHERE s.id=$1 GROUP BY d,s.id) r
          """,id)));
    }
}
public sealed record SprintInput(string Name,string? Goal,DateOnly StartDate,DateOnly EndDate);
