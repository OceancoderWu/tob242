# Separate local CPU verifier; trusted CUDA grading is delegated to remote root.
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates coreutils openssh-client python3 tar && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /workspace/output /workspace/solution /workspace/tests /workspace/environment/public_assets
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
COPY verifier_env/known_hosts /workspace/environment/known_hosts
COPY . /tests
RUN chmod -R a-w /workspace/tests /workspace/environment /workspace/instruction.md /tests && \
    chmod 0700 /tests/benchmark_data && \
    find /tests/benchmark_data -type f -exec chmod 0600 {} + && \
    if [ -f /tests/anchors.json ]; then chmod 0600 /tests/anchors.json; fi && \
    chmod 0755 /workspace/solution && chmod 0555 /workspace/solution/solve.sh
USER root
CMD ["bash"]
