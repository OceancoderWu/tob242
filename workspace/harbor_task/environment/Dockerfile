# Build from tob242/workspace/harbor_task. Target Linux x86_64 with NVIDIA runtime.
FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime
ENV OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY environment/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir torch-scatter==2.1.2+pt21cu118 torch-sparse==0.6.18+pt21cu118 -f https://data.pyg.org/whl/torch-2.1.0+cu118.html
RUN useradd -m -u 1000 researcher && mkdir -p /workspace/output /opt/benchmark /logs/verifier
WORKDIR /workspace
COPY tests /workspace/tests
COPY environment/public_assets /workspace/environment/public_assets
COPY environment/starter /workspace/environment/starter
COPY solution /workspace/solution
COPY instruction.md /workspace/instruction.md
RUN chmod -R a-w /workspace/tests /workspace/environment /workspace/instruction.md && \
    chown -R researcher:researcher /workspace/output /logs/verifier && \
    chown researcher:researcher /workspace/solution/method.py && \
    chown root:root /workspace/solution /workspace/solution/solve.sh && \
    chmod 0555 /workspace/solution /workspace/solution/solve.sh && \
    chmod 0644 /workspace/solution/method.py
USER researcher
CMD ["bash"]
