import os
import json
import time
from log.logger import logger
from config.typesense_client import TS_CLIENT

# additional code for vector generation
from langchain_fireworks import FireworksEmbeddings

embedding_model = FireworksEmbeddings(api_key=os.getenv("FIREWORKS_AI_API_KEY", "fw_3ZmSsfu21ztf14QAbpRjTeDQ"), model = "accounts/fireworks/models/qwen3-embedding-8b")

with open(r'C:\Users\anas_\Downloads\canonical_products.json', mode="r", encoding="utf-8") as f:
    data = json.load(f)

if not data:
    raise ValueError("Bulk data to be inserted not found!")

logger.info(f"Loaded {len(data)} products from source file")
concatenated_strings_array = []
for product in data:
    sentence = f"{product.get('norm_name', '')}. {', '.join(product.get('companies', []))}. {', '.join(product.get('typical_uses', []))}. {', '.join(product.get('health_info',[]))}"
    concatenated_strings_array.append(sentence or "")

CHECKPOINT_PATH = "data/embeddings_checkpoint.jsonl"
# Create the data directory if it doesn't exist
os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)


def _embed_with_retry(batch, max_retries=3):
    """Embed one batch, retrying with backoff so a transient API blip doesn't kill the run."""
    for attempt in range(1, max_retries + 1):
        try:
            return embedding_model.embed_documents(batch)
        except Exception as e:
            logger.warning(f"Embedding batch failed (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            time.sleep(2 ** attempt)  # 2s, 4s backoff


embeddings_array = []
if concatenated_strings_array:
    total = len(concatenated_strings_array)
    BATCH_SIZE = 1000  # lower if the API rejects large batches

    # Resume: pick up embeddings a previous (crashed) run already checkpointed.
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as ckpt:
            embeddings_array = [json.loads(line) for line in ckpt if line.strip()]
        logger.info(f"Resuming from checkpoint: {len(embeddings_array)} embeddings already done")

    start_index = len(embeddings_array)  # skip the already-embedded prefix
    logger.info(f"Generating embeddings for {total} products in batches of {BATCH_SIZE} (starting at {start_index})...")
    for start in range(start_index, total, BATCH_SIZE):
        batch = concatenated_strings_array[start:start + BATCH_SIZE]
        batch_embeddings = _embed_with_retry(batch)
        # extend (not append) keeps embeddings_array aligned 1:1 with data
        embeddings_array.extend(batch_embeddings)
        # append-only checkpoint: writes just this batch, not the whole growing array
        with open(CHECKPOINT_PATH, "a", encoding="utf-8") as ckpt:
            ckpt.write("".join(json.dumps(v) + "\n" for v in batch_embeddings))
        logger.info(f"Embedded {min(start + BATCH_SIZE, total)}/{total} (checkpoint saved)")

    logger.info(f"Generated {len(embeddings_array)} embeddings")
    # Completed cleanly — drop the checkpoint so a fresh run doesn't resume stale data.
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)



new_product_array = []
if embeddings_array:
    for i,product in enumerate(data):
        product['embedding'] = embeddings_array[i]
        new_product_array.append(product)
with open("data/canonical_products.json", mode = "w", encoding="utf-8") as f:
    json.dump(new_product_array, f, indent=2, ensure_ascii=False)
# Add a confirmation message so you know it completed
logger.info(f"Saved {len(new_product_array)} products with embeddings to data/canonical_products.json")


def insert_bulk_docs(data: list[dict], collection_name: str):
    try:
        if not data:
            raise ValueError("Data to be inserted not found")
        if not collection_name:
            raise ValueError("No collection name given")
        logger.info(f"{'='*50} Initializing bulk documents insertion {'='*50}")
        logger.info(f"Inserting {len(data)} documents into collection '{collection_name}'...")
        results = TS_CLIENT.collections[collection_name].documents.import_(data, {'action': 'create'})

        # import_ returns one result per document, in the same order as `data`,
        # so a failed result at index i maps back to data[i]'s canonical_id.
        failed_ids = []
        for i, result in enumerate(results):
            if not result.get('success'):
                doc_id = data[i].get('canonical_id', f'<index {i}>')
                failed_ids.append(doc_id)
                logger.warning(f"Insertion failed for canonical_id={doc_id} | reason: {result.get('error')}")

        success_count = len(data) - len(failed_ids)
        logger.info(f"Bulk insertion finished: {success_count} succeeded, {len(failed_ids)} failed (out of {len(data)})")
        if failed_ids:
            logger.error(f"Failed insertions ({len(failed_ids)}) canonical_ids: {failed_ids}")
        else:
            logger.info("All documents inserted successfully!")
        return failed_ids
    except Exception as e:
        logger.error(f"Some error occured while bulk uploading documents, Error: {e}")

insert_bulk_docs(data, "halal_products")