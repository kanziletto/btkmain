# ocr_server.py
from fastapi import FastAPI, UploadFile, File
from rapidocr_onnxruntime import RapidOCR
import uvicorn
import shutil
import os

app = FastAPI()

# RapidOCR başlatılıyor
ocr_engine = RapidOCR(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False)

@app.post("/ocr")
async def read_captcha(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    try:
        # Resmi kaydet
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Oku
        result, _ = ocr_engine(temp_filename)
        
        # Sonucu temizle
        full_text = ""
        if result:
            for line in result:
                if line and len(line) >= 2:
                    full_text += line[1]
        
        clean_text = "".join(filter(str.isalnum, full_text))
        return {"status": "success", "text": clean_text}

    except Exception as e:
        return {"status": "error", "text": ""}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
