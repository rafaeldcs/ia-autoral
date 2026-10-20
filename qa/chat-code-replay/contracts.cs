using System;
using System.Linq;
using Xunit;
using GerenciadorDeTarefas;

// Frozen independent assertions. These are evaluator code, not model output.
public class IndependentTaskContracts
{
    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void InvalidTitleIsRejected(string? title) =>
        Assert.Throws<ArgumentException>(() => new Tarefa(1, title!));

    [Fact]
    public void ConstructorPreservesValues()
    {
        var task = new Tarefa(7, "Ação e revisão 😀");
        Assert.Equal(7, task.Id);
        Assert.Equal("Ação e revisão 😀", task.Titulo);
        Assert.False(task.Concluida);
    }

    [Fact]
    public void CompletePreservesIdentityAndTitle()
    {
        var task = new Tarefa(7, "Ação");
        task.Concluir();
        Assert.True(task.Concluida);
        Assert.Equal(7, task.Id);
        Assert.Equal("Ação", task.Titulo);
    }

    [Fact]
    public void NewServiceIsEmpty() => Assert.Empty(new TarefaService().Listar());

    [Fact]
    public void AddPreservesAllTasksAndOrder()
    {
        var service = new TarefaService();
        service.Adicionar(9, "Primeira");
        service.Adicionar(2, "Segunda");
        Assert.Equal(new[] { 9, 2 }, service.Listar().Select(t => t.Id));
        Assert.Equal(new[] { "Primeira", "Segunda" }, service.Listar().Select(t => t.Titulo));
    }

    [Fact]
    public void DuplicateIdIsRejectedWithoutAppending()
    {
        var service = new TarefaService();
        service.Adicionar(1, "Original");
        Assert.ThrowsAny<ArgumentException>(() => service.Adicionar(1, "Duplicada"));
        Assert.Equal("Original", Assert.Single(service.Listar()).Titulo);
    }

    [Fact]
    public void MissingIdIsRejectedWithoutChangingTasks()
    {
        var service = new TarefaService();
        service.Adicionar(1, "Original");
        Assert.ThrowsAny<ArgumentException>(() => service.ConcluirPorId(99));
        Assert.False(Assert.Single(service.Listar()).Concluida);
    }

    [Fact]
    public void CompletionKeepsAllTasksAndChangesOnlySelected()
    {
        var service = new TarefaService();
        service.Adicionar(1, "Primeira");
        service.Adicionar(2, "Segunda");
        service.ConcluirPorId(2);
        var tasks = service.Listar();
        Assert.Equal(2, tasks.Count);
        Assert.False(tasks[0].Concluida);
        Assert.True(tasks[1].Concluida);
    }

    [Fact]
    public void ReturnedListCannotClearInternalList()
    {
        var service = new TarefaService();
        service.Adicionar(1, "Original");
        service.Listar().Clear();
        Assert.Single(service.Listar());
    }

    [Fact]
    public void InvalidAddDoesNotAppend()
    {
        var service = new TarefaService();
        Assert.Throws<ArgumentException>(() => service.Adicionar(1, "   "));
        Assert.Empty(service.Listar());
    }

    [Fact]
    public void ServicesAreIndependent()
    {
        var first = new TarefaService();
        first.Adicionar(1, "Original");
        Assert.Empty(new TarefaService().Listar());
    }
}
