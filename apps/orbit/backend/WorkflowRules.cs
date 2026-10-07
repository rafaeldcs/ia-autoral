public static class WorkflowRules
{
    public static bool IsValid(string? method, int wipLimit, int version) =>
        method is "scrum" or "kanban" && wipLimit is >= 1 and <= 100 && version >= 1;
}
