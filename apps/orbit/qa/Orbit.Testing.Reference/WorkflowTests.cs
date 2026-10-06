namespace Orbit.Testing.Reference;

// Runs the actual production validation rule; database concurrency is tested by the simulation.
public class WorkflowTests
{
    [Theory]
    [InlineData("kanban", 1, 1, true)]
    [InlineData("scrum", 100, 1, true)]
    [InlineData("kanban", 0, 1, false)]
    [InlineData("kanban", 101, 1, false)]
    [InlineData("kanban", -1, 1, false)]
    [InlineData("kanban", 3, 0, false)]
    [InlineData("kanban", 3, -1, false)]
    [InlineData("kanban", 3, 2, true)]
    [InlineData(null, 3, 1, false)]
    [InlineData("", 3, 1, false)]
    [InlineData("scrumban", 3, 1, false)]
    [InlineData("Kanban", 3, 1, false)]
    public void Configuration_accepts_only_supported_methods_limits_and_versions(string? method, int limit, int version, bool expected)
    {
        Assert.Equal(expected, WorkflowRules.IsValid(method, limit, version));
    }
}
