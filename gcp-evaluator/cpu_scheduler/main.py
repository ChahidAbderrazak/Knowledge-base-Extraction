from google.cloud import bigquery
from datetime import datetime
import os

from common.config import BATCH_SIZE, BACKLOG_THRESHOLD

client = bigquery.Client()

DATASET = "evaluation"

def get_pending_count():
    query = f"""
    SELECT COUNT(*) as cnt
    FROM `{DATASET}.eval_requests`
    WHERE status = 'PENDING'
    """
    return list(client.query(query))[0].cnt


def lock_batch(limit=BATCH_SIZE):
    query = f"""
    UPDATE `{DATASET}.eval_requests`
    SET status = 'LOCKED',
        locked_by = 'scheduler',
        lock_time = CURRENT_TIMESTAMP()
    WHERE sample_id IN (
        SELECT sample_id
        FROM `{DATASET}.eval_requests`
        WHERE status = 'PENDING'
        LIMIT {limit}
    )
    """
    client.query(query).result()


def fetch_locked_batch():
    query = f"""
    SELECT *
    FROM `{DATASET}.eval_requests`
    WHERE status = 'LOCKED'
    AND locked_by = 'scheduler'
    """
    return client.query(query).to_dataframe()


def trigger_gpu(batch_df):
    # Placeholder for Cloud Run GPU call
    print(f"Sending batch of size {len(batch_df)} to GPU service")


def main():
    pending = get_pending_count()

    print("Pending:", pending)

    if pending == 0:
        return

    if pending >= BACKLOG_THRESHOLD or datetime.utcnow().hour == 18:
        lock_batch()
        batch = fetch_locked_batch()
        trigger_gpu(batch)


if __name__ == "__main__":
    main()
