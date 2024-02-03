FROM python:3.10-slim-bookworm as base

ENV DEBIAN_FRONTEND=noninteractive
LABEL maintainer="Adipkumar Vishwakarma <adeepkumarv@gmail.com>"

RUN apt-get update \
    && apt-get install --yes libgl1 libgl1-mesa-glx libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt

# copy python scripts
COPY yolov8 /app/yolov8/

# copy fastapi script
COPY main.py config.py /app/

# copy the onnx model
COPY models/num_plate_detection_yolov8s.onnx /app/models/num_plate_detection_yolov8s.onnx

WORKDIR /app/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
