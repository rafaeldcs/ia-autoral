# Operator supplies the pinned source tree as whisper_source. No weights/downloads.
FROM localauthor-cuda118-builder:1 AS build
USER root
COPY --from=whisper_source / /source/
RUN cmake -S /source -B /build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_SDL2=OFF -DGGML_CUDA=OFF && cmake --build /build --target whisper-cli -j 4
FROM localauthor-foundation-gguf:1
USER root
COPY --from=build /build/bin/whisper-cli /opt/voice/whisper-cli
COPY scripts/voice-worker.py /opt/voice/worker.py
USER 10001:10001
WORKDIR /tmp
ENTRYPOINT ["python3", "/opt/voice/worker.py"]
