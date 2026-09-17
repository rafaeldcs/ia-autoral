import json
import tempfile
import threading
import unittest
from pathlib import Path
try:
    import numpy as np
    from localauthor.nn.tensor import Tensor, cross_entropy, layer_norm, gelu, no_grad
    from localauthor.nn.transformer import Transformer, ModelConfig
    from localauthor.nn.optimizer import AdamW
    from localauthor.nn.checkpoint import save_checkpoint, load_checkpoint
    from localauthor.nn.tokenizer import ByteTokenizer, BPETokenizer, tokenizer_from_dict
    from localauthor.nn.train import train
    NUMPY = True
except ImportError:
    NUMPY = False
from tests.helpers import make_dataset


@unittest.skipUnless(NUMPY,"NumPy ausente; instale requirements-training.txt para validar o motor.")
class NeuralTests(unittest.TestCase):
    def finite_gradient(self, fun, data, atol=2e-6):
        x = Tensor(data.copy(), True)
        loss = fun(x); loss.backward(); analytical = x.grad.copy()
        numerical = np.zeros_like(data)
        for index in np.ndindex(data.shape):
            plus, minus = data.copy(), data.copy()
            plus[index]+=1e-6; minus[index]-=1e-6
            numerical[index]=(float(fun(Tensor(plus)).data)-float(fun(Tensor(minus)).data))/2e-6
        np.testing.assert_allclose(analytical,numerical,atol=atol,rtol=2e-5)

    def test_add_multiply_power_gradients(self):
        self.finite_gradient(lambda x: ((x*x+2*x)**2).mean(),np.array([[0.2,-0.3],[0.5,0.7]]))

    def test_broadcast_gradient(self):
        other = Tensor(np.arange(24).reshape(2,3,4)/20)
        self.finite_gradient(lambda x:(other*x+x).sum(),np.array([0.1,0.2,0.3,0.4]))

    def test_batched_matmul_gradient(self):
        other = Tensor(np.arange(24).reshape(2,3,4)/20)
        self.finite_gradient(lambda x: (other@x).sum(),np.arange(8).reshape(4,2)/10.)

    def test_softmax_gradient(self):
        scale=Tensor(np.array([[1,2,4],[2,1,3]]))
        self.finite_gradient(lambda x:(x.softmax()*scale).sum(),np.array([[0.1,-0.3,0.5],[1.,0.2,-1.]]))

    def test_layernorm_gradient(self):
        self.finite_gradient(lambda x:(layer_norm(x,Tensor(np.ones(3)),Tensor(np.zeros(3)))**3).sum(),np.array([[0.1,-0.3,0.5],[1.,0.2,-1.]]))

    def test_gelu_gradient(self):
        self.finite_gradient(lambda x:gelu(x).sum(),np.array([[-1.,-0.1,0.3,2.]]))

    def test_crossentropy_gradient(self):
        self.finite_gradient(lambda x:cross_entropy(x,np.array([0,2])),np.array([[1.,0.5,-0.5],[-0.2,0.3,0.1]]))

    def test_embedding_repeated_indices_accumulate(self):
        x=Tensor(np.ones((4,2)),True)
        x.embedding(np.array([[1,1,2]])).sum().backward()
        np.testing.assert_array_equal(x.grad,np.array([[0,0],[2,2],[1,1],[0,0]]))

    def test_transpose_reshape_gradient(self):
        self.finite_gradient(lambda x:(x.reshape(2,2,2).transpose(1,0,2)**2).sum(),np.arange(8,dtype=float)/10)

    def test_tuple_reduction_gradient(self):
        self.finite_gradient(lambda x:(x.sum(axis=(0,2))**2).sum(),np.arange(8,dtype=float).reshape(2,2,2)/10)

    def test_no_grad_does_not_build_graph(self):
        x=Tensor([1.,2.],True)
        with no_grad(): y=(x*x).sum()
        self.assertFalse(y.requires_grad); self.assertEqual(y.parents,())

    def test_byte_tokenizer_round_trip(self):
        t=ByteTokenizer(); text="Olá, ação!\r\n\tC# 😀"
        self.assertEqual(t.decode(t.encode(text,special=True)),text)

    def test_bpe_round_trip_and_deterministic(self):
        docs=["produto estoque produto estoque "*10,"ação e código "*10]
        a=BPETokenizer.train(docs,280); b=BPETokenizer.train(docs,280)
        self.assertEqual(a.merges,b.merges)
        text="Produto 😀 ação\r\n  estoque"
        self.assertEqual(a.decode(a.encode(text,special=True)),text)
        restored=tokenizer_from_dict(a.to_dict())
        self.assertEqual(restored.encode(text),a.encode(text))

    def test_causal_attention_does_not_see_future(self):
        model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8))
        with no_grad():
            a=model.forward(np.array([[1,2,3,4]])).data
            b=model.forward(np.array([[1,2,99,98]])).data
        np.testing.assert_allclose(a[:,:2],b[:,:2],atol=1e-12)

    def test_parameter_count(self):
        model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8))
        self.assertEqual(model.parameter_count,3016)

    def test_transformer_parameter_gradient(self):
        model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8))
        x=np.array([[1,2,3,4]]); y=np.array([[2,3,4,5]])
        loss=model.loss(x,y); loss.backward()
        param=model.parameters["block.0.q.weight"]
        actual=param.grad[0,0]; old=param.data[0,0]
        with no_grad():
            param.data[0,0]=old+1e-5; plus=float(model.loss(x,y).data)
            param.data[0,0]=old-1e-5; minus=float(model.loss(x,y).data)
            param.data[0,0]=old
        self.assertAlmostEqual(actual,(plus-minus)/2e-5,delta=1e-6)

    def test_optimizer_and_model_learn_tiny_numeric_pattern(self):
        model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8,seed=7))
        opt=AdamW(model.parameters,lr=0.02,weight_decay=0.)
        x=np.array([[1,2,3,4,1,2,3,4],[2,3,4,1,2,3,4,1]])
        y=np.array([[2,3,4,1,2,3,4,1],[3,4,1,2,3,4,1,2]])
        initial=float(model.loss(x,y).data)
        for _ in range(90):
            loss=model.loss(x,y); loss.backward(); opt.step()
        final=float(model.loss(x,y).data)
        self.assertLess(final,initial*0.3)
        self.assertLess(final,0.8)

    def test_checkpoint_exact_forward_and_rng_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"model.npz"
            model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8))
            opt=AdamW(model.parameters); rng=np.random.default_rng(5)
            x=np.array([[1,2,3,4]]); y=np.array([[2,3,4,5]])
            model.loss(x,y).backward(); opt.step()
            save_checkpoint(path,model,opt,ByteTokenizer(),rng,{"unit_test":True})
            restored,ropt,_,rrng,meta=load_checkpoint(path)
            np.testing.assert_array_equal(model.forward(x).data,restored.forward(x).data)
            np.testing.assert_array_equal(rng.integers(0,100,10),rrng.integers(0,100,10))
            model.loss(x,y).backward(); opt.step(); restored.loss(x,y).backward(); ropt.step()
            for name in model.parameters: np.testing.assert_array_equal(model.parameters[name].data,restored.parameters[name].data)
            self.assertFalse(meta["programming_qualified"])

    def test_checkpoint_corruption_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"model.npz"
            model=Transformer(ModelConfig(dimension=8,heads=2,layers=1,context_length=8))
            save_checkpoint(path,model,AdamW(model.parameters),ByteTokenizer(),np.random.default_rng(1),{})
            path.write_bytes(path.read_bytes()+b"tamper")
            with self.assertRaises(ValueError): load_checkpoint(path)

    def test_large_configuration_rejected_before_allocation(self):
        with self.assertRaises(ValueError): Transformer(ModelConfig(dimension=256,layers=8,heads=8))

    def test_training_cancel_saves_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); manifest=make_dataset(root/"dataset")
            cancel=threading.Event(); cancel.set()
            result=train(manifest,root/"out",ModelConfig(dimension=8,heads=2,layers=1,context_length=8),steps=10,cancel=cancel)
            self.assertTrue(result["cancelled"])
            self.assertEqual(result["steps_this_run"],0)
            self.assertTrue((root/"out"/"latest.npz").exists())

    def test_end_to_end_training_manifest_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); manifest=make_dataset(root/"dataset")
            config=ModelConfig(dimension=8,heads=2,layers=1,context_length=8)
            first=train(manifest,root/"out",config,steps=4)
            resumed=train(manifest,root/"out",steps=3,resume=root/"out"/"latest.npz")
            self.assertEqual(resumed["total_steps"],7)
            self.assertFalse(resumed["programming_qualified"])
            self.assertEqual(resumed["test_records_never_used_by_trainer"],1)
