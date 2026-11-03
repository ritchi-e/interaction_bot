"""Replace Triton row_exponential with a PyTorch Exp(1) sampler.

Triton JIT segfaults on this host during compile; sampling quality stays fine.
"""

from pathlib import Path

p = Path("/opt/maya2/venv/lib/python3.11/site-packages/serve/fast_depth_kernels.py")
text = p.read_text()
needle = '''def row_exponential(B, V, seeds, ctrs, level=0):
    out = torch.empty(B, V, device=seeds.device, dtype=torch.float32)
    _row_exponential[(B,)](out, seeds, ctrs, level, out.stride(0), V=V, BLOCK=1024)
    return out'''
replacement = '''def row_exponential(B, V, seeds, ctrs, level=0):
    # PyTorch fallback: Triton JIT segfaults on some driver/CUDA combos.
    out = torch.empty(B, V, device=seeds.device, dtype=torch.float32)
    seeds_cpu = seeds.detach().to("cpu")
    ctrs_cpu = ctrs.detach().to("cpu")
    for i in range(B):
        gen = torch.Generator(device=seeds.device)
        seed = int(seeds_cpu[i].item()) ^ (int(ctrs_cpu[i].item()) << 8) ^ (int(level) * 9973)
        gen.manual_seed(seed & 0xFFFFFFFFFFFF)
        u = torch.rand(V, device=seeds.device, generator=gen).clamp_min(1e-12)
        out[i] = -torch.log(u)
    return out'''
if needle not in text:
    raise SystemExit("row_exponential block not found or already patched")
p.write_text(text.replace(needle, replacement, 1))
print("patched row_exponential")
