from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from yolov8 import YOLOv8
from yolov8.utils import class_names
from config import MODEL_PATH, MONGO_DB_ADDRESS

import cv2
import numpy as np
from pymongo import MongoClient

conn = MongoClient(MONGO_DB_ADDRESS)

# Initialize YOLOv8 model
yolov8_detector = YOLOv8(MODEL_PATH, conf_thres=0.4, iou_thres=0.5)

class Box(BaseModel):
    xmin : float
    ymin : float
    xmax : float
    ymax : float

    
class Results(BaseModel):
    box : Box
    score : float
    class_id : int
    name : str

# Initialize the FastAPI app
app = FastAPI(
    title="Custom YOLOv8 Object Detector API",
    description="Vehicle Number Plate Detection using Custom yolov8s model on onnxruntime inference session",
    version="0.1.0"
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _prepare_image(contents : str | bytes) -> np.ndarray:
    """_summary_

    Args:
        contents (str | bytes): buffer image

    Returns:
        np.ndarray: numpy image array
    """
    nparr : np.ndarray = np.fromstring(contents, np.uint8,sep="")
    
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def _prepare_output(boxes: np.ndarray, scores: np.ndarray, class_ids: np.ndarray)-> list[Results]:
    """
    Prepare output
    Args:
        boxes : np.ndarray
        scores : np.ndarray 
        class_ids: np.ndarray

    Returns:
        list[Results]
    """
    result = []

    for class_id, box, score in zip(class_ids, boxes, scores):
        box = {
            "xmin":float(box[0]),
            "ymin": float(box[1]),
            "xmax":float(box[2]),
            "ymax":float(box[3]),
            }
        result.append(
            {"box": box,
            "score" : float(score),
            "class_id": int(class_id),
            "name" : class_names[class_id]
            }
        )
    return result


@app.get('/')
def get_health() -> dict[str, str]:
    return dict(msg="Vehicle Number Plate Detection using Custom yolov8s model on onnxruntime inference session")


@app.post("/object-to-json")
async def detect_object_return_json(file: UploadFile = File(...)) -> dict[str | None,list[Results]] | dict[str| None, None]:
    try:
        contents= await file.read()
        # preparing image as np array
        img = _prepare_image(contents)
        boxes, scores, class_ids = yolov8_detector(img)
        
        if not scores.tolist():
            return {file.filename : None}
        
        result = _prepare_output(boxes.tolist(), scores, class_ids)
        # saving results in mongo database
        object = conn.object_detection.detection.insert_many(result)
        
        return {file.filename : result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@app.post("/object-to-img")
async def detect_object_return_image(file : UploadFile = File(...))  -> Response:
    try:
        contents = await file.read()
        # preparing image as np array
        img = _prepare_image(contents)

        boxes, scores, class_ids = yolov8_detector(img)
        result = _prepare_output(boxes, scores, class_ids) if scores is not None else []
        combined_img = yolov8_detector.draw_detections(img)

        filename = file.filename if not None else "image.jpeg"

        cv2.imwrite(f"data/output/masked_{filename}", combined_img)
        _, im_png = cv2.imencode(".png", combined_img)

        # return FileResponse(f"data/output/masked_{filename}")
        return Response(content=im_png.tobytes(), media_type="image/png",
                        headers={'Content-Disposition': 'inline; output: "%s"' %(result,)})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")