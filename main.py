import io
import pandas as pd
from fastapi import FastAPI, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import engine, Base, get_db
import models
import schemas
from services.llm_service import generate_product_metadata, LLMServiceError

app = FastAPI(title="Data Enrichment Pipeline")

def process_batch(batch_id: str):
    """
    Background task to process all pending products for a given batch.
    """
    db = next(get_db())
    try:
        # Fetch batch
        batch = db.query(models.UploadBatch).filter(models.UploadBatch.id == batch_id).first()
        if not batch:
            return

        batch.status = models.EnrichmentStatus.PROCESSING
        db.commit()

        # Fetch products for this batch
        products = db.query(models.Product).filter(
            models.Product.batch_id == batch_id,
            models.Product.status == models.EnrichmentStatus.PENDING
        ).all()

        for product in products:
            try:
                # Call LLM Service
                result = generate_product_metadata(product.raw_name)
                
                product.seo_description = result.get("seo_description", "")
                product.category_tags = result.get("category_tags", "")
                product.status = models.EnrichmentStatus.COMPLETED
            except Exception as e:
                print(f"Failed to process product {product.id}: {e}")
                product.status = models.EnrichmentStatus.FAILED
            
            # Commit after each product
            db.commit()
            
            # Update batch count
            batch.processed_rows += 1
            db.commit()
        
        batch.status = models.EnrichmentStatus.COMPLETED
        db.commit()

    except Exception as e:
        print(f"Error in batch processing: {e}")
        # Update batch status to failed if there's a fatal error
        db.rollback()
        batch = db.query(models.UploadBatch).filter(models.UploadBatch.id == batch_id).first()
        if batch:
            batch.status = models.EnrichmentStatus.FAILED
            db.commit()
    finally:
        db.close()


@app.post("/api/v1/upload", response_model=schemas.BatchResponse)
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
    
    # Read CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse CSV file.")
    
    # Assuming CSV has a column 'product_name' or we just take the first column
    if 'product_name' in df.columns:
        product_names = df['product_name'].dropna().tolist()
    else:
        # Fallback to first column
        product_names = df.iloc[:, 0].dropna().tolist()
    
    if not product_names:
        raise HTTPException(status_code=400, detail="No product names found in the CSV.")

    # Create batch record
    batch = models.UploadBatch(
        filename=file.filename,
        total_rows=len(product_names),
        status=models.EnrichmentStatus.PENDING
    )
    db.add(batch)
    db.flush() # To get batch.id
    
    # Create product records
    products_to_insert = [
        models.Product(
            batch_id=batch.id,
            raw_name=str(name),
            status=models.EnrichmentStatus.PENDING
        )
        for name in product_names
    ]
    db.add_all(products_to_insert)
    db.commit()
    db.refresh(batch)

    # Trigger background task
    background_tasks.add_task(process_batch, str(batch.id))

    return batch

@app.get("/api/v1/batches/{batch_id}", response_model=schemas.BatchResponse)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(models.UploadBatch).filter(models.UploadBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

@app.get("/api/v1/products", response_model=schemas.PaginatedProductsResponse)
def get_products(page: int = 1, size: int = 50, db: Session = Depends(get_db)):
    offset = (page - 1) * size
    total = db.query(models.Product).count()
    products = db.query(models.Product).order_by(models.Product.created_at.desc()).offset(offset).limit(size).all()
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "products": products
    }
