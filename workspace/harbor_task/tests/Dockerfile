# Harbor 0.23 builds a separate verifier from tests/ as its Docker context.
# The submitted method is transferred as a declared artifact after the agent ends.
FROM pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime
ENV OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY verifier_env/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir torch-scatter==2.1.2+pt21cu118 torch-sparse==0.6.18+pt21cu118 -f https://data.pyg.org/whl/torch-2.1.0+cu118.html
RUN useradd -m -u 1000 researcher && \
    mkdir -p /workspace/output /workspace/solution /workspace/tests /workspace/environment/public_assets
WORKDIR /workspace
COPY verifier_env/public_assets /workspace/environment/public_assets
COPY verifier_env/starter /workspace/environment/starter
COPY verifier_env/public_runner /workspace/environment/public_runner
COPY verifier_env/public_runner /workspace/tests
COPY verifier_env/agent_Dockerfile /workspace/environment/Dockerfile
COPY verifier_env/requirements.txt /workspace/environment/requirements.txt
COPY verifier_env/instruction.md /workspace/environment/instruction.md
COPY verifier_env/instruction.md /workspace/instruction.md
COPY verifier_env/starter/solve.sh /workspace/solution/solve.sh
COPY . /tests
RUN chmod -R a-w /workspace/tests /workspace/environment /workspace/instruction.md /tests && \
    chmod 0700 /tests/benchmark_data && \
    find /tests/benchmark_data -type f -exec chmod 0600 {} + && \
    if [ -f /tests/anchors.json ]; then chmod 0600 /tests/anchors.json; fi && \
    chown -R researcher:researcher /workspace/output && \
    chmod 0755 /workspace/solution && chmod 0555 /workspace/solution/solve.sh
USER root
CMD ["bash"]
