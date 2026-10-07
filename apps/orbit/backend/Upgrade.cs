public static class Upgrade
{
    public static Task Run(Store db) => db.Execute("""
        BEGIN;
        CREATE TABLE IF NOT EXISTS users (
          id uuid PRIMARY KEY, name varchar(80) NOT NULL, email varchar(160) UNIQUE NOT NULL,
          password_hash text NOT NULL, role text NOT NULL CHECK(role IN ('admin','manager','member','viewer')),
          active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now());
        ALTER TABLE users ADD COLUMN IF NOT EXISTS bootstrap boolean NOT NULL DEFAULT false;
        CREATE UNIQUE INDEX IF NOT EXISTS one_bootstrap_user ON users(bootstrap) WHERE bootstrap;
        CREATE OR REPLACE FUNCTION configure_user(actor uuid,target uuid,new_role text,new_active boolean) RETURNS boolean AS $$
        BEGIN
          LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE;
          IF actor=target OR NOT EXISTS(SELECT 1 FROM users WHERE id=actor AND role='admin' AND active) THEN
            RAISE EXCEPTION 'Forbidden' USING ERRCODE='42501';
          END IF;
          UPDATE users SET role=new_role,active=new_active WHERE id=target;
          IF NOT FOUND THEN RETURN false; END IF;
          IF NOT EXISTS(SELECT 1 FROM users WHERE role='admin' AND active) THEN
            RAISE EXCEPTION 'Last administrator' USING ERRCODE='23514';
          END IF;
          DELETE FROM sessions WHERE user_id=target;
          RETURN true;
        END $$ LANGUAGE plpgsql;
        CREATE TABLE IF NOT EXISTS sessions (hash text PRIMARY KEY,user_id uuid REFERENCES users(id) ON DELETE CASCADE,expires_at timestamptz NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, actor text NOT NULL, action text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now());
        CREATE TABLE IF NOT EXISTS sprints (
          id uuid PRIMARY KEY,project_id uuid NOT NULL REFERENCES projects(id),name varchar(100) NOT NULL,goal text NOT NULL DEFAULT '',
          start_date date NOT NULL,end_date date NOT NULL CHECK(end_date>=start_date AND end_date<=start_date+90),
          state text NOT NULL DEFAULT 'planned' CHECK(state IN ('planned','active','closed')),
          started_at timestamptz,closed_at timestamptz,committed_points int NOT NULL DEFAULT 0,
          completed_points int NOT NULL DEFAULT 0,committed_count int NOT NULL DEFAULT 0,completed_count int NOT NULL DEFAULT 0,
          UNIQUE(id,project_id));
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_sprint ON sprints(project_id) WHERE state='active';
        ALTER TABLE issues ADD COLUMN IF NOT EXISTS sprint_id uuid;
        DO $$ BEGIN
          IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='issue_sprint_project') THEN
            ALTER TABLE issues ADD CONSTRAINT issue_sprint_project FOREIGN KEY(sprint_id,project_id) REFERENCES sprints(id,project_id);
          END IF;
        END $$;
        CREATE TABLE IF NOT EXISTS issue_events (
          id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,issue_id uuid NOT NULL REFERENCES issues(id),project_id uuid NOT NULL,
          sprint_id uuid,status text NOT NULL,points int NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          previous_status text,baseline boolean NOT NULL DEFAULT false);
        CREATE INDEX IF NOT EXISTS issue_events_history ON issue_events(project_id,issue_id,recorded_at DESC,id DESC);
        CREATE OR REPLACE FUNCTION capture_issue_event() RETURNS trigger AS $$
        BEGIN
          IF NEW.sprint_id IS NOT NULL AND (TG_OP='INSERT' OR NEW.sprint_id IS DISTINCT FROM OLD.sprint_id OR NEW.status IS DISTINCT FROM OLD.status OR NEW.story_points IS DISTINCT FROM OLD.story_points) THEN
            PERFORM 1 FROM sprints WHERE id=NEW.sprint_id AND project_id=NEW.project_id AND state<>'closed' FOR SHARE;
            IF NOT FOUND THEN RAISE EXCEPTION 'Sprint closed or invalid' USING ERRCODE='23514'; END IF;
          END IF;
          IF TG_OP='INSERT' THEN
            INSERT INTO issue_events(issue_id,project_id,sprint_id,status,points) VALUES(NEW.id,NEW.project_id,NEW.sprint_id,NEW.status,coalesce(NEW.story_points,0));
          ELSE
            IF NEW.status IS DISTINCT FROM OLD.status OR NEW.story_points IS DISTINCT FROM OLD.story_points OR NEW.sprint_id IS DISTINCT FROM OLD.sprint_id THEN
              INSERT INTO issue_events(issue_id,project_id,sprint_id,status,points,previous_status) VALUES(NEW.id,NEW.project_id,NEW.sprint_id,NEW.status,coalesce(NEW.story_points,0),OLD.status);
            END IF;
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
        DROP TRIGGER IF EXISTS issue_event ON issues;
        CREATE TRIGGER issue_event AFTER INSERT OR UPDATE ON issues FOR EACH ROW EXECUTE FUNCTION capture_issue_event();
        INSERT INTO issue_events(issue_id,project_id,sprint_id,status,points,baseline)
          SELECT id,project_id,sprint_id,status,coalesce(story_points,0),true FROM issues i WHERE NOT EXISTS(SELECT 1 FROM issue_events e WHERE e.issue_id=i.id);
        CREATE OR REPLACE FUNCTION start_sprint(target uuid) RETURNS boolean AS $$
        BEGIN
          LOCK TABLE issues IN SHARE ROW EXCLUSIVE MODE;
          UPDATE sprints SET state='active',started_at=clock_timestamp(),
            committed_points=(SELECT coalesce(sum(story_points),0) FROM issues WHERE sprint_id=target),
            committed_count=(SELECT count(*) FROM issues WHERE sprint_id=target)
            WHERE id=target AND state='planned' AND end_date>=CURRENT_DATE;
          RETURN FOUND;
        END $$ LANGUAGE plpgsql;
        CREATE OR REPLACE FUNCTION finish_sprint(target uuid) RETURNS boolean AS $$
        BEGIN
          LOCK TABLE issues IN SHARE ROW EXCLUSIVE MODE;
          UPDATE sprints SET state='closed',closed_at=clock_timestamp(),
            completed_points=(SELECT coalesce(sum(story_points),0) FROM issues WHERE sprint_id=target AND status='done'),
            completed_count=(SELECT count(*) FROM issues WHERE sprint_id=target AND status='done')
            WHERE id=target AND state='active';
          IF NOT FOUND THEN RETURN false; END IF;
          WITH moved AS (UPDATE issues SET sprint_id=null,status='backlog',version=version+1,updated_at=now()
            WHERE sprint_id=target AND status<>'done' RETURNING id)
          INSERT INTO activity(issue_id,message) SELECT id,'Sprint encerrada: item pendente devolvido ao backlog' FROM moved;
          RETURN true;
        END $$ LANGUAGE plpgsql;
        COMMIT;
        """);
}
