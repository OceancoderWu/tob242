# Harbor and Docker run on the local CPU host. Training runs only on the SSH server.
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates coreutils openssh-client python3 tar && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 researcher && mkdir -p /workspace/output /workspace/solution /workspace/tests /workspace/environment/public_assets
WORKDIR /workspace
COPY public_assets /workspace/environment/public_assets
COPY starter /workspace/environment/starter
COPY Dockerfile /workspace/environment/Dockerfile
COPY public_runner /workspace/tests
COPY known_hosts /workspace/environment/known_hosts
COPY starter/method.py /workspace/solution/method.py
COPY starter/solve.sh /workspace/solution/solve.sh
COPY instruction.md /workspace/instruction.md
RUN chmod -R a-w /workspace/tests /workspace/environment /workspace/instruction.md && \
    chown -R researcher:researcher /workspace/output /workspace/solution && \
    chown root:root /workspace/solution/solve.sh && \
    chmod 0755 /workspace/solution && chmod 0555 /workspace/solution/solve.sh && \
    chmod 0644 /workspace/solution/method.py
USER researcher
CMD ["bash"]
