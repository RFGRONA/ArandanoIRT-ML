import os
import shutil
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv, set_key

from app.core.security import get_api_key
from app.schemas import ChatRequest, BatchIngestLogRequest, UpdateApiKeyRequest
from app.services.rag_service import rag_service
from app.services.chroma_service import chroma_service

load_dotenv()

app = FastAPI(title="ArandanoIRT-ML RAG API")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API RAG funcionando correctamente."}

@app.post("/chat", dependencies=[Depends(get_api_key)])
def chat_endpoint(request: ChatRequest):
    try:
        result = rag_service.process_chat(
            question=request.question, 
            iot_context=request.iot_context or "",
            expertise_level=request.expertise_level or "AGRONOMO"
        )
        return result
    except Exception as e:
        print(f"Error en chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar la consulta.")

@app.post("/ingest-logs", dependencies=[Depends(get_api_key)])
def ingest_logs_endpoint(request: BatchIngestLogRequest):
    try:
        ids = [log.observation_id for log in request.logs]
        texts = [log.text_content for log in request.logs]
        metadatas = [log.metadata for log in request.logs]
        
        chroma_service.ingest_logs_batch(ids=ids, texts=texts, metadatas=metadatas)
        return {"status": "success", "message": f"{len(request.logs)} logs vectorizados correctamente."}
    except Exception as e:
        print(f"Error en ingest_logs_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al vectorizar logs.")

@app.post("/update-papers", dependencies=[Depends(get_api_key)])
def update_papers_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .zip")
        
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        temp_file = tmp.name
        shutil.copyfileobj(file.file, tmp)
        
    try:
        success = chroma_service.replace_papers_db(temp_file)
        if success:
            return {"status": "success", "message": "Base de datos ChromaDB actualizada exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="Fallo interno al reemplazar la base de datos.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@app.get("/export-db", dependencies=[Depends(get_api_key)])
def export_db_endpoint(background_tasks: BackgroundTasks):
    try:
        zip_path = chroma_service.export_db_zip()
        background_tasks.add_task(os.remove, zip_path)
        return FileResponse(
            path=zip_path,
            filename="chroma_db_export.zip",
            media_type="application/zip"
        )
    except Exception as e:
        print(f"Error en export_db_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al exportar la base de datos.")

@app.post("/update-api-key", dependencies=[Depends(get_api_key)])
def update_api_key_endpoint(request: UpdateApiKeyRequest):
    """
    IMPORTANTE: Este endpoint permite sobrescribir permanentemente GOOGLE_API_KEY en disco 
    usando la X-API-KEY. En producción, considere deshabilitar este endpoint, restringirlo 
    a IPs específicas, o usar una clave de administrador separada.
    """
    try:
        # Reflejarla en el entorno del proceso actual sin intentar recargar
        # dependencias globales en caliente, ya que no es seguro con concurrencia
        # ni consistente en despliegues con múltiples workers.
        os.environ["GOOGLE_API_KEY"] = request.api_key
        # Persistir la clave para futuros arranques del servicio.
        set_key(".env", "GOOGLE_API_KEY", request.api_key)
        
        return {
            "status": "success", 
            "message": "API Key de Gemini actualizada y persistida correctamente. Reinicie el servicio para aplicar el cambio de forma segura."
        }
    except Exception as e:
        print(f"Error en update_api_key_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al actualizar la API Key.")
