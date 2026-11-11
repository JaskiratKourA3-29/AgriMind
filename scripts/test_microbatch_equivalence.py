"""
Comprehensive Numerical Equivalence & Chunk Slicing Verification:
1. Tests device-safe contiguous slicing (no numpy indexing on device tensors).
2. Tests small batch edge cases where total_samples < requested_chunks (N = 3, 2, 1).
3. Verifies full-batch vs micro-batch loss and gradients from IDENTICAL model state and inputs.
"""
import numpy as np

def verify_full_equivalence():
    np.random.seed(42)
    
    # PlantVillage class weights
    w = np.array([0.7891, 1.6788, 0.8795], dtype=np.float64)
    C = 3
    d = 5
    
    print("=== TEST 1: CHUNK BOUNDARY & SMALL BATCH SAFETY ===")
    for total_samples in [32, 31, 7, 3, 2, 1]:
        for requested_chunks in [1, 2, 4]:
            effective_chunks = min(requested_chunks, total_samples)
            # Contiguous slice boundaries (start, end)
            chunk_size = (total_samples + effective_chunks - 1) // effective_chunks
            slices = []
            for start in range(0, total_samples, chunk_size):
                end = min(start + chunk_size, total_samples)
                slices.append((start, end))
            
            # Guarantees:
            assert sum(end - start for start, end in slices) == total_samples
            assert all(end > start for start, end in slices)
            assert len(slices) <= requested_chunks
            print(f"N={total_samples:2d}, requested={requested_chunks} -> effective={len(slices)} chunks: {slices}")
            
    print("\n=== TEST 2: LOSS & GRADIENT EQUIVALENCE ON IDENTICAL MODEL STATE ===")
    # Batch size N=31, split into uneven slices
    N = 31
    X = np.random.randn(N, d)
    y = np.random.choice([0, 1, 2], size=N, p=[0.5, 0.2, 0.3])
    
    # Identical initial model state (theta)
    theta_initial = np.random.randn(d, C)
    
    # 1. Full batch execution
    theta_full = theta_initial.copy()
    logits_full = X @ theta_full
    exp_f = np.exp(logits_full - np.max(logits_full, axis=1, keepdims=True))
    probs_f = exp_f / np.sum(exp_f, axis=1, keepdims=True)
    
    sample_losses_f = -np.log(probs_f[np.arange(N), y])
    sample_weights_f = w[y]
    W_full = np.sum(sample_weights_f)
    
    loss_full = np.sum(sample_weights_f * sample_losses_f) / W_full
    
    grad_logits_f = probs_f.copy()
    grad_logits_f[np.arange(N), y] -= 1.0
    grad_logits_f = grad_logits_f * (sample_weights_f[:, None] / W_full)
    grad_full = X.T @ grad_logits_f
    
    # 2. Micro-batch execution using identical model state theta_initial
    theta_micro = theta_initial.copy()
    assert np.array_equal(theta_full, theta_micro), "Model states must be identical!"
    
    slices_to_test = [(0, 16), (16, 31)]
    accumulated_loss = 0.0
    accumulated_grad = np.zeros_like(theta_micro)
    
    for start, end in slices_to_test:
        X_chunk = X[start:end]
        y_chunk = y[start:end]
        
        logits_c = X_chunk @ theta_micro
        exp_c = np.exp(logits_c - np.max(logits_c, axis=1, keepdims=True))
        probs_c = exp_c / np.sum(exp_c, axis=1, keepdims=True)
        
        losses_c = -np.log(probs_c[np.arange(len(y_chunk)), y_chunk])
        w_c = w[y_chunk]
        W_chunk = np.sum(w_c)
        
        # Standard mean-reduced loss
        loss_mean_c = np.sum(w_c * losses_c) / W_chunk
        
        # Weight-ratio scaling
        scaled_loss_c = loss_mean_c * (W_chunk / W_full)
        accumulated_loss += scaled_loss_c
        
        # Gradient on chunk
        grad_logits_c = probs_c.copy()
        grad_logits_c[np.arange(len(y_chunk)), y_chunk] -= 1.0
        grad_logits_c = grad_logits_c * (w_c[:, None] / W_full)
        accumulated_grad += X_chunk.T @ grad_logits_c
        
    loss_error = abs(loss_full - accumulated_loss)
    grad_max_error = np.max(np.abs(grad_full - accumulated_grad))
    
    print(f"Full batch loss:           {loss_full:.14f}")
    print(f"Micro-batch accum loss:    {accumulated_loss:.14f}")
    print(f"Absolute loss error:       {loss_error:.2e}")
    print(f"Max absolute grad error:   {grad_max_error:.2e}")
    
    assert loss_error < 1e-14, f"Loss error too high: {loss_error}"
    assert grad_max_error < 1e-14, f"Grad error too high: {grad_max_error}"
    print("\nALL VERIFICATIONS PASSED: Perfect equivalence verified from identical model state!")

if __name__ == "__main__":
    verify_full_equivalence()
