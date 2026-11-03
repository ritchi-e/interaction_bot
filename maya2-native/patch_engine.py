from pathlib import Path

p = Path("/opt/maya2/venv/lib/python3.11/site-packages/maya3/engine.py")
text = p.read_text()
old1 = """    use_graphs: bool = True
    fuse_proj: bool = False              # backbone: one GEMM for q|k|v and one for gate|up per layer
    fuse_rope: bool = True               # backbone: fused q/k RMSNorm + RoPE + KV-cache write (Triton; implies fuse_proj)
    fused_norm: bool = False             # backbone: F.rms_norm instead of the HF RMSNorm module
    fused_depth: bool = True             # depth: Triton add+LayerNorm and one-kernel top-k sampler"""
new1 = """    # Triton JIT segfaults on this host (driver 595 / CUDA 13.2 + triton 3.4).
    # Prefer the eager PyTorch paths so the OpenAI server stays usable.
    use_graphs: bool = False
    fuse_proj: bool = False              # backbone: one GEMM for q|k|v and one for gate|up per layer
    fuse_rope: bool = False              # backbone: fused q/k RMSNorm + RoPE + KV-cache write (Triton; implies fuse_proj)
    fused_norm: bool = False             # backbone: F.rms_norm instead of the HF RMSNorm module
    fused_depth: bool = False            # depth: Triton add+LayerNorm and one-kernel top-k sampler"""
if old1 not in text:
    raise SystemExit("block1 not found or already patched")
text = text.replace(old1, new1, 1)
old2 = 'attention="triton", use_graphs=cfg.use_graphs,'
new2 = 'attention="gather", use_graphs=cfg.use_graphs,'
if old2 not in text:
    raise SystemExit("attention line not found or already patched")
text = text.replace(old2, new2, 1)
p.write_text(text)
print("patched ok")
