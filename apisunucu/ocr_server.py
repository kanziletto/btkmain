# ocr_server.py
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from rapidocr_onnxruntime import RapidOCR
import uvicorn
import shutil
import os
import uuid

app = FastAPI()

# --- Resim Hosting Ayarları ---
UPLOAD_DIR = "public_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")
# ------------------------------------

# RapidOCR başlatılıyor
# Detay: 1 OCPU için GPU kullanımı kapalı (False) kalmalı
ocr_engine = RapidOCR(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False)

@app.post("/ocr")
def read_captcha(file: UploadFile = File(...)):
    """
    Görseldeki metni okur.
    'async' kaldırıldığı için FastAPI bunu Thread havuzunda çalıştırır.
    Böylece aynı anda gelen çoklu istekler paralel işlenir.
    """
    temp_filename = f"temp_{uuid.uuid4()}.png"
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
        
        # Sadece harf ve rakamları al
        clean_text = "".join(filter(str.isalnum, full_text))
        return {"status": "success", "text": clean_text}

    except Exception as e:
        return {"status": "error", "text": ""}
    finally:
        # Temizlik
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.post("/upload")
def upload_image(request: Request, file: UploadFile = File(...)):
    """
    Kanıt görselini kaydeder ve URL döner.
    Paralel yüklemeleri destekler.
    """
    try:
        # Dosya uzantısını koru
        ext = os.path.splitext(file.filename)[1]
        if not ext: ext = ".png"
        
        # Benzersiz isim
        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Dosyayı kaydet
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Public URL oluştur
        base_url = str(request.base_url).rstrip("/")
        file_url = f"{base_url}/images/{filename}"
        
        return {"url": file_url}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # workers=1 idealdir çünkü ThreadPool ile paralellik sağlıyoruz
    uvicorn.run(app, host="0.0.0.0", port=8000)
