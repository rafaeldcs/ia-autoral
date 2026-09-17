namespace Laboratory;

// Projeto de laboratório; não representa código ou dados de clientes.
public sealed class Product
{
    public string Name { get; }
    public int Quantity { get; private set; }

    public Product(string name, int quantity)
    {
        if (string.IsNullOrWhiteSpace(name))
            throw new ArgumentException("Nome obrigatório.", nameof(name));
        Name = name;
        SetQuantity(quantity);
    }

    public void SetQuantity(int quantity)
    {
        if (quantity < 0)
            throw new ArgumentOutOfRangeException(nameof(quantity), "Estoque não pode ser negativo.");
        Quantity = quantity;
    }
}
