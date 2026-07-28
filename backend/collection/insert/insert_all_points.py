import os
import json
import gc
from typing import List, Dict, Any
from dotenv import load_dotenv
from log.logger import logger
from config.typesense_client import TS_CLIENT
from langchain_fireworks import FireworksEmbeddings



load_dotenv()
# ==================== CONFIGURATION ====================
BATCH_SIZE = 50
INSERT_BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 2
START_BATCH = 518  # Continue from this batch (1-indexed)

# ==================== INITIALIZATION ====================
embedding_model = FireworksEmbeddings(
    api_key=os.getenv("FIREWORKS_AI_API_KEY"),
    model="accounts/fireworks/models/qwen3-embedding-8b"
)

# ==================== ERROR TRACKING ====================
failed_docs = []
failed_batches = []
checkpoint_file = "processing_checkpoint.json"

# ==================== HELPER FUNCTIONS ====================
def create_embedding_string(product: Dict) -> str:
    """Create concatenated string for embedding"""
    parts = [
        product.get('norm_name', ''),
        ', '.join(product.get('companies', [])),
        ', '.join(product.get('typical_uses', [])),
        ', '.join(product.get('health_info', []))
    ]
    non_empty_parts = [p for p in parts if p]
    return '. '.join(non_empty_parts)

def embed_batch_with_retry(texts: List[str], batch_num: int) -> List[List[float]]:
    """Embed a batch with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            embeddings = embedding_model.embed_documents(texts)
            logger.info(f"✅ Batch {batch_num}: Embedded {len(texts)} documents")
            return embeddings
        except Exception as e:
            logger.error(f"❌ Batch {batch_num}, Attempt {attempt+1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                import time
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                failed_batches.append({
                    'batch_num': batch_num,
                    'error': str(e),
                    'documents': texts
                })
                return []

def insert_batch_to_typesense(docs: List[Dict], batch_num: int):
    """Insert a batch to Typesense with error handling per document"""
    try:
        results = TS_CLIENT.collections["halal_products"].documents.import_(
            docs, {'action': 'create'}
        )
        
        for idx, result in enumerate(results):
            if 'error' in result:
                failed_docs.append({
                    'batch_num': batch_num,
                    'index': idx,
                    'document_id': docs[idx].get('id', 'unknown'),
                    'error': result['error'],
                    'document': docs[idx]
                })
                logger.warning(f"⚠️ Document {idx} in batch {batch_num} failed: {result['error']}")
        
        success_count = len(results) - len([r for r in results if 'error' in r])
        logger.info(f"✅ Typesense batch {batch_num}: {success_count}/{len(docs)} inserted")
        
    except Exception as e:
        failed_batches.append({
            'batch_num': batch_num,
            'error': str(e),
            'documents': docs
        })
        logger.error(f"❌ Entire Typesense batch {batch_num} failed: {e}")

def save_checkpoint(current_batch: int):
    """Save progress checkpoint"""
    checkpoint = {
        'last_completed_batch': current_batch,
        'failed_docs_count': len(failed_docs),
        'failed_batches_count': len(failed_batches),
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f, indent=2)
    logger.info(f"💾 Checkpoint saved at batch {current_batch}")

def load_previous_failures():
    """Load previously failed documents if any"""
    global failed_docs, failed_batches
    if os.path.exists("embedding_failures.json"):
        with open("embedding_failures.json", "r") as f:
            previous = json.load(f)
            failed_docs.extend(previous.get('failed_documents', []))
            failed_batches.extend(previous.get('failed_batches', []))
            logger.info(f"📂 Loaded {len(previous.get('failed_documents', []))} previous failures")

# ==================== MAIN PROCESSING ====================
def process_and_insert_batches_resume(data: List[Dict]):
    """Resume batch processing from where it left off"""
    
    total_docs = len(data)
    logger.info(f"📦 Resuming batch processing from batch {START_BATCH}")
    
    # Step 1: Prepare embedding strings (only for remaining batches)
    embedding_strings = []
    valid_products = []
    
    # Calculate starting index based on batch number
    start_index = (START_BATCH - 1) * BATCH_SIZE
    
    logger.info(f"📍 Starting from document index: {start_index}")
    
    # Only process remaining documents
    remaining_products = data[start_index:]
    
    for idx, product in enumerate(remaining_products):
        try:
            embedding_str = create_embedding_string(product)
            if embedding_str:
                embedding_strings.append(embedding_str)
                valid_products.append(product)
            else:
                failed_docs.append({
                    'batch_num': 'preprocessing_resume',
                    'index': start_index + idx,
                    'document_id': product.get('id', start_index + idx),
                    'error': 'Empty embedding string',
                    'document': product
                })
        except Exception as e:
            failed_docs.append({
                'batch_num': 'preprocessing_resume',
                'index': start_index + idx,
                'document_id': product.get('id', start_index + idx),
                'error': str(e),
                'document': product
            })
    
    logger.info(f"🔧 Preprocessed: {len(valid_products)} valid documents remaining")
    
    # Step 2: Process remaining batches
    total_batches = (len(valid_products) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_idx in range(total_batches):
        current_batch_num = START_BATCH + batch_idx
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, len(valid_products))
        
        batch_texts = embedding_strings[start_idx:end_idx]
        batch_products = valid_products[start_idx:end_idx]
        
        logger.info(f"🎯 Processing embedding batch {current_batch_num}/?")
        
        # Generate embeddings
        embeddings = embed_batch_with_retry(batch_texts, current_batch_num)
        
        if not embeddings:
            logger.error(f"❌ Skipping batch {current_batch_num} due to embedding failure")
            save_checkpoint(current_batch_num - 1)
            continue
        
        # Attach embeddings
        for i, product in enumerate(batch_products):
            product['embedding'] = embeddings[i]
        
        # Insert to Typesense in sub-batches
        total_insert_batches = (len(batch_products) + INSERT_BATCH_SIZE - 1) // INSERT_BATCH_SIZE
        
        for insert_batch_num in range(total_insert_batches):
            insert_start = insert_batch_num * INSERT_BATCH_SIZE
            insert_end = min(insert_start + INSERT_BATCH_SIZE, len(batch_products))
            insert_docs = batch_products[insert_start:insert_end]
            
            insert_batch_to_typesense(insert_docs, f"{current_batch_num}.{insert_batch_num+1}")
        
        # Save checkpoint every 10 batches
        if current_batch_num % 10 == 0:
            save_checkpoint(current_batch_num)
        
        # Force garbage collection after each batch
        gc.collect()
        
        logger.info(f"✅ Completed batch {current_batch_num}")
    
    # Final summary
    print("\n" + "="*60)
    print("📊 RESUME PROCESSING SUMMARY")
    print("="*60)
    print(f"✅ Documents processed in this run: {len(valid_products)}")
    print(f"❌ New failed documents: {len(failed_docs)}")
    print(f"❌ New failed batches: {len(failed_batches)}")
    
    # Save failures
    if failed_docs or failed_batches:
        failure_report = {
            'failed_documents': failed_docs,
            'failed_batches': failed_batches,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        with open("embedding_failures_resume.json", "w") as f:
            json.dump(failure_report, f, indent=2)
        print("\n📁 Failure report saved to: embedding_failures_resume.json")
    
    save_checkpoint(START_BATCH + total_batches - 1)

# ==================== EXECUTION ====================

# Load previous failures if any
load_previous_failures()

# Load data
logger.info("Loading data file...")
with open("data/canonical_products.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    raise ValueError("No data found to process!")

logger.info(f"Total documents in file: {len(data)}")

# Process remaining batches
process_and_insert_batches_resume(data)

print(f"\n✅ Resume processing complete! Started from batch {START_BATCH}")
print(f"📊 Checkpoint saved to: {checkpoint_file}")