namespace Orbit.Testing.Reference;

// Teaching reference authored by Codex, not by the local model.
public class BoundaryTests
{
    private static bool Valid(int value,int max)=>value>=0 && value<=max;
    private static bool UpperMutant(int value,int max)=>value>=0 && value<max;
    private static bool LowerMutant(int value,int max)=>value<=max;
    [Theory]
    [InlineData(-1,8,false)]
    [InlineData(0,8,true)]
    [InlineData(4,8,true)]
    [InlineData(8,8,true)]
    [InlineData(9,8,false)]
    public void Range_respects_both_boundaries(int value,int max,bool expected)
    {
        var actual=Valid(value,max);
        Assert.Equal(expected,actual);
    }
    [Fact]
    public void Upper_boundary_case_detects_less_than_mutation()
    {
        Assert.True(Valid(8,8));
        Assert.False(UpperMutant(8,8));
    }
    [Fact]
    public void Negative_case_detects_missing_lower_bound()
    {
        Assert.False(Valid(-1,8));
        Assert.True(LowerMutant(-1,8));
    }
    [Fact]
    public void Happy_path_alone_does_not_detect_boundary_defect()
    {
        Assert.Equal(Valid(4,8),UpperMutant(4,8));
    }
}
